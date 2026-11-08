# onesheet

A Claude Code skill that turns a repository into a single printable page: a 3D hero, a diagram traced from the code, real numbers with sources, and the command to try it.

In film, a one-sheet is the single poster that sells a movie. This is that, for a repo.

<p>
<img src="skills/onesheet/benchmark/httpx.jpg" width="24%" alt="One-pager for the HTTPX library" />
<img src="skills/onesheet/benchmark/memos.jpg" width="24%" alt="One-pager for the Memos web app" />
<img src="skills/onesheet/benchmark/whisper.jpg" width="24%" alt="One-pager for the Whisper ML project" />
<img src="skills/onesheet/benchmark/glow.jpg" width="24%" alt="One-pager for the Glow CLI" />
</p>

Each example was made by the skill from the public repo alone. They're unofficial summaries, not documents from those projects. Full PDFs are in [`skills/onesheet/benchmark/`](skills/onesheet/benchmark/).

## Install

In Claude Code:

```
/plugin marketplace add prabindersinghh/onesheet
/plugin install onesheet@onesheet
```

Or copy [`skills/onesheet`](skills/onesheet/) into `~/.claude/skills/` to use it as a personal skill.

## Use

```
/onesheet:onesheet https://github.com/owner/repo
```

You can also just ask, for example "make a one-pager for this repo". If you copied the folder in, the command is `/onesheet`.

| Option | Default | Effect |
|---|---|---|
| repo | the current folder | A local path, a GitHub URL, or `owner/name` |
| `--audience "..."` | technical peers new to the project | Sets the vocabulary and what gets explained |
| `--no-internals` | off | Describes behaviour and hides model names, vendors, stack and hosting |
| `--letter` | A4 | US Letter |
| `--out path` | `<repo>-one-pager.pdf` | Where the PDF goes. The editable `work/` folder goes beside it. |

## What it does

1. Reads the repo: README, manifests, entry points, tests, licence and history. It never runs the repo's code or install scripts.
2. Writes a fact ledger. Every number and claim on the page has to trace to a file and line, and claims the code doesn't back are printed as "the README reports" or left out.
3. Writes 220 to 320 words of copy before any design.
4. Renders a 3D hero with three.js in headless Chrome and draws the flow diagram as vector SVG.
5. Prints the PDF and runs automated checks: one page, word budget, type sizes, collisions, text on renders, image resolution, banned words, secret-like strings, numbers missing from the ledger, and a QR code that decodes.
6. Critiques the rasterized page and fixes it, scoring it on ten lines. It delivers only at 44/50 with no line below 4.

The delivery message lists README claims the code contradicted, what it didn't read, what is labelled as illustration, and its score.

## Requirements

- Claude Code
- Python 3.10 or newer, Node 18 or newer, and Chrome or Edge
- Internet access, for fonts and the three.js library. Nothing from the repo is sent anywhere.

## Cost and status

A page takes about 15 to 30 minutes and 210,000 to 265,000 tokens. That's about twice a plain attempt, spent on the critique rounds.

Tested on Windows 11 with Chrome, on a web app, a library, an ML project and two CLIs. Not yet tested on macOS or Linux, private or very large repos, `--no-internals`, or heroes built from a repo's own 3D model. Reports from those are welcome.

## Develop

`dev/kit_selftest.py` sets up a work folder, renders every scene type, and builds pages that each break one check, to prove each check fails. Run it from the repo root with a scratch folder outside the repo:

```
python dev/kit_selftest.py ../onesheet-selftest
```

`dev/evals.json` holds the three end-to-end test prompts.

## License

[MIT](LICENSE)
