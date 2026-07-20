# Adding and updating tools

## Structure

```
/                     repo root, served at tools.scienceofsurfing.com
  index.html          landing page (lists the tools)
  CNAME               custom domain
  .nojekyll           tells GitHub Pages to serve files as-is
  LICENSE             AGPL-3.0 (code)
  favicon.png, apple-touch-icon.png
  <tool-name>/
    index.html        the tool, one self-contained file
    README.md         what the tool is + data/references
    og-image.png      1200x630 social preview (optional)
```

One folder per tool. Each tool is a single self-contained `index.html` (inline CSS/JS, data as
data: URIs). No build step, no dependencies.

## Add a tool

1. Create a folder, e.g. `refraction/`, and drop its self-contained `index.html` in.
2. Add a short `README.md` (what it does, data sources, references) and an `og-image.png`.
3. Keep the license header comment at the top of the `index.html` and a credit/copyright line in
   the page footer (copy the pattern from `swell-window/`).
4. Add one row to the table in the root `index.html` linking the new tool.

## Deploy / update

GitHub Pages serves the `main` branch from the repo root. There is no build.

- Replace a file (drag-drop in the GitHub web UI, or `git push`) and commit. Pages redeploys on its own.
- Keep `.nojekyll` and `CNAME` at the root, or the custom domain / static serving breaks.
- Every version is in git history, so a bad change is one revert away.
