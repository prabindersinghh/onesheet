# onesheet

A Claude Code skill that turns a repository into a single printable page: a 3D hero, a diagram traced from the code, real numbers with sources, and the command to try it.

In film, a one-sheet is the single poster that sells a movie. This is that, for a repo.

| Library | Web app | ML project | CLI |
|---|---|---|---|
| ![One-pager for the HTTPX library](skills/onesheet/benchmark/httpx.jpg) | ![One-pager for the Memos web app](skills/onesheet/benchmark/memos.jpg) | ![One-pager for the Whisper ML project](skills/onesheet/benchmark/whisper.jpg) | ![One-pager for the Glow CLI](skills/onesheet/benchmark/glow.jpg) |

Each example was made by the skill from the public repo alone. They're unofficial summaries, not documents from those projects. The full PDFs are attached to the [latest release](https://github.com/prabindersinghh/onesheet/releases/latest).

## Install

In Claude Code:

```
/plugin marketplace add prabindersinghh/onesheet
/plugin install onesheet@onesheet
```

Or copy [`skills/onesheet`](skills/onesheet/) into `~/.claude/skills/` to use it as a personal skill.

## Use

Open your project in Claude Code and type:

```
/onesheet
```

That's it. You get `<repo>-one-pager.pdf` in the folder. To make a page for a public repo you don't have open, give its URL: `/onesheet https://github.com/owner/repo`.

You can also just ask, for example "make a one-pager for this repo". If another command already uses the name, type `/onesheet:onesheet`.

| Option | Default | Effect |
|---|---|---|
| repo | the project you have open | A local folder, or a public GitHub URL or `owner/name` |
| `--audience "..."` | technical peers new to the project | Sets the vocabulary and what gets explained |
| `--no-internals` | off | Describes behaviour and hides model names, vendors, stack and hosting |
| `--letter` | A4 | US Letter |
| `--out path` | `<repo>-one-pager.pdf` in the current folder | Where the PDF goes |

## What it does

1. Reads the repo: README, manifests, entry points, tests, licence and history. It never runs the repo's code or install scripts.
2. Writes a fact ledger. Every number and claim on the page has to trace to a file and line, and claims the code doesn't back are printed as "the README reports" or left out.
3. Writes 220 to 320 words of copy before any design.
4. Renders a 3D hero with three.js in headless Chrome and draws the flow diagram as vector SVG.
5. Prints the PDF and runs automated checks: one page, word budget, type sizes, collisions, text on renders, image resolution, banned words, secret-like strings, numbers missing from the ledger, and a QR code that decodes.
6. Critiques the rasterized page and fixes it, scoring it on ten lines. It delivers only at 44/50 with no line below 4.

The delivery message lists README claims the code contradicted, what it didn't read, what is labelled as illustration, and its score.

## Where it runs

onesheet picks one of two builds by itself, and tells you which:

| | Full build | Lite build |
|---|---|---|
| Where | Claude Code, or Cowork on your computer | claude.ai, Claude Desktop chat, and anywhere without a browser |
| Needs | Python 3.10+, Node 18+, Chrome or Edge, internet | Python with reportlab and pillow |
| Hero | A photographic 3D render, made in headless Chrome | Exact vector 3D: plates, screens and blocks drawn in perspective |
| Checks | Layout, type, words, facts, banned words, secrets, resolution, QR decode | The same, except the QR decode |

Both builds keep the same fact ledger, rules and quality bar. Compare them on the same repos: [hyperfine](docs/compare-hyperfine.jpg) and [HTTPX](docs/compare-httpx.jpg).

In claude.ai, turn on **Code execution and file creation** in Settings. If the sandbox can't download a repo, upload it as a zip, which GitHub gives you under **Code > Download ZIP**.

## What it runs and fetches

Everything runs on your machine.

- **The repo:** the project you have open, a folder you name, or `git clone --depth 50` of a public GitHub URL. It never uses your logins. For a private repo, clone it yourself and run `/onesheet` inside it. The repo's code is read, never run, and its install scripts are never run.
- **Its own work folder:** `.onesheet/<repo>/work` in your home folder, about 150 MB of tools, kept outside your project so the page can be edited later. Your project only gets the PDF.
- **Lite build:** only reportlab and pillow, plus pypdf and pypdfium2 when present. Its fonts, IBM Plex Sans and Mono under the SIL Open Font License, ship with the skill, so it fetches nothing else.
- **Full build tools, installed into `work/`:** a Python virtual environment with pillow 13.0.0, pypdf 6.21.4 and pypdfium2 5.14.0 from PyPI, and playwright 1.49.1, qrcode 1.5.3, jsqr 1.4.0, pngjs 7.0.0 and three.js 0.170.0 from npm. three.js renders the 3D hero and is loaded from `work/`, not from a CDN. Playwright uses your installed Chrome or Edge.
- **Fonts:** static font files from Google Fonts, chosen per page.
- **A local web server:** `build.py` serves `work/` on 127.0.0.1, on a free port, while it renders and prints. It stops when the command ends.
- **Public counts, sometimes:** the skill may read figures such as GitHub stars or Docker pulls from those services' public APIs. The page names the source and date.

Nothing from the repo, the page or your machine is sent anywhere else. Requests to Google Fonts, PyPI and npm carry only what they need to serve the files.

## Cost and status

A page takes about 15 to 30 minutes and 210,000 to 265,000 tokens. That's about twice a plain attempt, spent on the critique rounds.

The full build is tested on Windows 11 with Chrome, on a web app, a library, an ML project and two CLIs. The lite build is tested on a CLI and a library in a Python-only setup that mimics a chat sandbox, but not yet inside claude.ai itself. Not yet tested: macOS or Linux, private or very large repos, `--no-internals`, and heroes built from a repo's own 3D model. Reports are welcome.

## Develop

`dev/kit_selftest.py` sets up a work folder, renders every scene type, and builds pages that each break one check, to prove each check fails. Run it from the repo root with a scratch folder outside the repo:

```
python dev/kit_selftest.py ../onesheet-selftest
```

`dev/evals.json` holds the three end-to-end test prompts.

## License

[MIT](LICENSE)
