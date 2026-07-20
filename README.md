# Science of Surfing — interactive tools

Static site for the **First Order** series. One folder per tool.
Currently: `swell-window/` (the Swell Window Explorer).

Live target: **https://tools.scienceofsurfing.com/**
The explorer: **https://tools.scienceofsurfing.com/swell-window/**

------------------------------------------------------------------
## Deploy on GitHub Pages (free, versioned)

### 1. Make the repo
- New GitHub repo, e.g. `sos-tools`. **Public** is simplest
  (private repos need GitHub Pro for Pages).
- Upload everything in this folder to the repo root, keeping the
  structure: `index.html`, `CNAME`, and `swell-window/index.html`.
  (Web UI works: "Add file → Upload files", drag them in, commit.)

### 2. Turn on Pages
- Repo → **Settings → Pages**.
- Source: **Deploy from a branch**, branch **main**, folder **/ (root)**. Save.
- It builds in a minute. The `CNAME` file already tells Pages the
  custom domain is `tools.scienceofsurfing.com`.

### 3. Point the subdomain (Porkbun)
- Porkbun → scienceofsurfing.com → **DNS Records**.
- Add one record:
  - **Type:** CNAME
  - **Host:** `tools`
  - **Answer:** `<your-github-username>.github.io`   (no https://, no trailing slash)
- Leave every other record alone. `www` and the apex (your Substack) are untouched.

### 4. Lock in HTTPS
- Back in Settings → Pages, the custom domain should show
  `tools.scienceofsurfing.com`. Wait for the DNS check to pass
  (minutes to an hour), then tick **Enforce HTTPS**.

Done. The explorer is live at
`https://tools.scienceofsurfing.com/swell-window/`.

------------------------------------------------------------------
## Updating the tool later
Replace `swell-window/index.html` in the repo (drag-drop in the web
UI or `git push`) and commit. Pages redeploys on its own.
Every version is in the repo history, so a bad change is one revert away.

## Adding the next tool
New folder (e.g. `refraction/`), drop its `index.html` in, add one line
to the landing page (`index.html`) linking it. Same subdomain, same repo.

------------------------------------------------------------------
## Files
- `index.html` — branded landing page listing the tools
- `swell-window/index.html` — the Swell Window Explorer (self-contained)
- `CNAME` — custom domain for GitHub Pages (`tools.scienceofsurfing.com`)
