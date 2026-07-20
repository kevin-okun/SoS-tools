# Science of Surfing — Tools

Interactive tools for the **First Order** series at [Science of Surfing](https://scienceofsurfing.com).
Each tool takes one question surfers argue about and answers it in layers you can see and drag.

Live: **https://tools.scienceofsurfing.com/**

## Tools

| Tool | What it answers | Live |
|------|-----------------|------|
| [Swell Window Explorer](swell-window/) | Which swell directions can actually reach a break, for ten Southern California spots | [open](https://tools.scienceofsurfing.com/swell-window/) |

Each tool lives in its own folder with a `README.md` describing it and its data sources.

## How it is served

A plain static site on GitHub Pages, custom domain `tools.scienceofsurfing.com` (`CNAME`),
Jekyll disabled (`.nojekyll`). No build step: every tool is a single self-contained `index.html`.

## License and credits

- **Code** is licensed under the [GNU Affero General Public License v3.0](LICENSE) (AGPL-3.0).
  You may study, share, and build on it, provided you keep the notices and publish your source
  if you host a modified version.
- The **"Science of Surfing" name and logo**, and all **article text and figures**, are
  © Kevin Okun and are **not** covered by that license.
- **Data and scientific sources** are credited in each tool's own README and on the tool page.

To add a tool, see [CONTRIBUTING.md](CONTRIBUTING.md).
