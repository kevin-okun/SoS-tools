#!/usr/bin/env python3
"""
run_cases_v1.py — Headless Celeris-WebGPU case runner for the canyon-focus
tool. A Linux/Playwright port of the stock Selenium harness
(celeris-webgpu/automation/run_WebGPU.py): same page (index_headless.html),
same element IDs (configFile / bathymetryFile / waveFile /
start-simulation-btn), same trigger keys in config.json, same
completed.txt / current_time*.txt protocol. Only the browser plumbing
differs (manually-launched Chromium + CDP; downloads routed per case via
Browser.setDownloadBehavior).

Usage:
  python3 run_cases_v1.py --celeris /path/to/celeris-webgpu \
      --case CASE_DIR [--case CASE_DIR2 ...] \
      [--bathy /path/to/bathy.txt]  # else CASE_DIR/bathy.txt \
      [--out-root OUT_ROOT]         # else CASE_DIR/output \
      [--timeout-min 120] [--headful] [--keep-all]

Each CASE_DIR must contain config.json and waves.txt (and bathy.txt unless
--bathy). Results land in OUT_ROOT/<case_name>/ with run_result.json.
By default only the needed exports are kept (dx/dy/nx/ny, bathytopo, Hs,
Hrms, FSmean); --keep-all keeps every surface.
"""

import argparse
import glob
import json
import os
import shutil
import socket
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

CHROMIUM = os.environ.get("CELERIS_CHROMIUM", "/opt/pw-browsers/chromium")
KEEP_FILES = {"dx.txt", "dy.txt", "nx.txt", "ny.txt",
              "current_bathytopo.bin", "current_Hs.bin",
              "current_Hrms.bin", "current_FSmean.bin", "completed.txt"}
CHROME_FLAGS = ["--headless=new", "--no-sandbox", "--disable-gpu-sandbox",
                "--enable-unsafe-webgpu", "--enable-features=WebGPU"]
# On machines without a hardware GPU, force the SwiftShader CPU fallback:
if os.environ.get("CELERIS_SWIFTSHADER", "auto") != "0" and not os.path.exists("/dev/dri"):
    CHROME_FLAGS.append("--use-webgpu-adapter=swiftshader")


def free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    return port


def wait_for_completion(out_dir, expect_t_end, timeout_s, log):
    t0 = time.time()
    prev_t, prev_wall = 0.0, t0
    completed = os.path.join(out_dir, "completed.txt")
    while not os.path.exists(completed):
        if time.time() - t0 > timeout_s:
            log("TIMEOUT waiting for completed.txt")
            return False
        time.sleep(10)
        cur_files = glob.glob(os.path.join(out_dir, "current_time*"))
        if cur_files:
            newest = max(cur_files, key=os.path.getmtime)
            try:
                cur_t = float(open(newest).read().strip())
                now = time.time()
                ratio = (cur_t - prev_t) / max(1e-6, now - prev_wall)
                eta_min = ((expect_t_end - cur_t) / max(1e-6, ratio)) / 60.0
                log(f"  sim t={cur_t:8.1f}/{expect_t_end:.0f} s  "
                    f"speed={ratio:5.2f}x realtime  ETA {eta_min:6.1f} min")
                prev_t, prev_wall = cur_t, now
            except ValueError:
                pass
            for f in cur_files:
                try:
                    os.remove(f)
                except OSError:
                    pass
    return True


def verify_outputs(out_dir, width, height, log):
    ok = True
    expected_bytes = width * height * 4
    for name in ("current_Hs.bin", "current_bathytopo.bin"):
        p = os.path.join(out_dir, name)
        if not os.path.exists(p):
            log(f"MISSING output {name}")
            ok = False
        elif os.path.getsize(p) != expected_bytes:
            log(f"BAD SIZE {name}: {os.path.getsize(p)} != {expected_bytes}")
            ok = False
    for name in ("nx.txt", "ny.txt"):
        p = os.path.join(out_dir, name)
        if os.path.exists(p):
            val = int(float(open(p).read().strip()))
            want = width if name == "nx.txt" else height
            if val != want:
                log(f"BAD {name}: {val} != {want}")
                ok = False
    return ok


def run_case(ctx, browser_cdp, base_url, case_dir, bathy_path, out_dir,
             timeout_min, keep_all, log):
    config = json.load(open(os.path.join(case_dir, "config.json")))
    width, height = config["WIDTH"], config["HEIGHT"]
    t_end = config["trigger_writeWaveHeight_time"]
    os.makedirs(out_dir, exist_ok=True)

    browser_cdp.send("Browser.setDownloadBehavior",
                     {"behavior": "allow", "downloadPath": out_dir,
                      "eventsEnabled": True})
    page = ctx.new_page()
    console_log = []
    page.on("console", lambda m: console_log.append(f"[{m.type}] {m.text}")
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: console_log.append(f"[pageerror] {e}"))
    result = {"case": os.path.basename(case_dir), "ok": False,
              "t_end": t_end, "started": time.strftime("%F %T")}
    try:
        page.goto(base_url + "/index_headless.html", timeout=60000)
        page.wait_for_timeout(3000)
        page.set_input_files("#configFile",
                             os.path.join(case_dir, "config.json"))
        page.set_input_files("#bathymetryFile", bathy_path)
        page.set_input_files("#waveFile", os.path.join(case_dir, "waves.txt"))
        page.wait_for_timeout(1000)
        page.click("#start-simulation-btn")
        log(f"case {result['case']}: started (grid {width}x{height}, "
            f"to t={t_end:.0f} s)")
        ok = wait_for_completion(out_dir, t_end, timeout_min * 60, log)
        if ok:
            time.sleep(10)  # let final downloads land
            ok = verify_outputs(out_dir, width, height, log)
        result["ok"] = ok
    except Exception as exc:
        log(f"case {result['case']}: EXCEPTION {exc}")
        result["error"] = str(exc)
    finally:
        page.close()
        result["finished"] = time.strftime("%F %T")
        result["console_tail"] = console_log[-20:]
        for f in glob.glob(os.path.join(out_dir, "current_time*")):
            try:
                os.remove(f)
            except OSError:
                pass
        if not keep_all and result["ok"]:
            for f in os.listdir(out_dir):
                if f not in KEEP_FILES:
                    try:
                        os.remove(os.path.join(out_dir, f))
                    except OSError:
                        pass
        with open(os.path.join(out_dir, "run_result.json"), "w") as fh:
            json.dump(result, fh, indent=2)
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--celeris", required=True)
    ap.add_argument("--case", action="append", required=True)
    ap.add_argument("--bathy", default=None)
    ap.add_argument("--out-root", default=None)
    ap.add_argument("--timeout-min", type=float, default=120)
    ap.add_argument("--headful", action="store_true")
    ap.add_argument("--keep-all", action="store_true")
    args = ap.parse_args()

    http_port, cdp_port = free_port(), free_port()
    profile = os.path.join("/tmp", f"celeris-profile-{cdp_port}")
    http = subprocess.Popen([sys.executable, "-m", "http.server",
                             str(http_port)], cwd=args.celeris,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)
    flags = [f for f in CHROME_FLAGS if not (args.headful and "headless" in f)]
    chrome = subprocess.Popen([CHROMIUM, *flags,
                               f"--remote-debugging-port={cdp_port}",
                               f"--user-data-dir={profile}"],
                              stdout=subprocess.DEVNULL,
                              stderr=subprocess.DEVNULL)
    time.sleep(5)

    def log(msg):
        print(f"{time.strftime('%H:%M:%S')} {msg}", flush=True)

    results = []
    try:
        with sync_playwright() as p:
            b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{cdp_port}")
            cdp = b.new_browser_cdp_session()
            ctx = b.contexts[0] if b.contexts else b.new_context()
            for case_dir in args.case:
                case_dir = os.path.abspath(case_dir)
                bathy = args.bathy or os.path.join(case_dir, "bathy.txt")
                out_root = args.out_root or case_dir
                out_dir = os.path.join(out_root, "output") if out_root == case_dir \
                    else os.path.join(out_root, os.path.basename(case_dir))
                results.append(run_case(ctx, cdp, f"http://127.0.0.1:{http_port}",
                                        case_dir, bathy, out_dir,
                                        args.timeout_min, args.keep_all, log))
            b.close()
    finally:
        chrome.terminate()
        http.terminate()
        shutil.rmtree(profile, ignore_errors=True)

    n_ok = sum(r["ok"] for r in results)
    log(f"DONE: {n_ok}/{len(results)} cases ok")
    for r in results:
        log(f"  {'OK ' if r['ok'] else 'FAIL'} {r['case']}")
    sys.exit(0 if n_ok == len(results) else 1)


if __name__ == "__main__":
    main()
