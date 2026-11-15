#!/usr/bin/env python3
"""Create a onesheet work folder from references/BUILD-KIT.md.

usage: python setup_work.py <work-folder>

Tools go straight into the folder. Starter content goes into <work-folder>/starter/, so a
real page is written fresh instead of over a sample, and `build.py render` doesn't pick up
sample specs. Keep the work folder outside any downloaded repo.
"""
import os
import pathlib
import re
import shutil
import subprocess
import sys

TOOLS = {"build.py", "tools.mjs", "render.html"}
PIP = ["pillow==13.0.0", "pypdf==6.21.4", "pypdfium2==5.14.0"]
NPM = ["playwright@1.49.1", "qrcode@1.5.3", "jsqr@1.4.0", "pngjs@7.0.0", "three@0.170.0"]


def main(work):
    kit = (pathlib.Path(__file__).resolve().parent.parent / "references" / "BUILD-KIT.md").read_text(encoding="utf-8")
    files = re.findall(r"<!-- file: (\S+) -->\s*```\w*\n(.*?)\n```", kit, re.S)
    if not files:
        sys.exit("No files found in BUILD-KIT.md")
    work.mkdir(parents=True, exist_ok=True)
    (work / "specs").mkdir(exist_ok=True)
    for name, body in files:
        path = work / name if name in TOOLS else work / "starter" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body + "\n", encoding="utf-8")
    print(f"wrote {len(files)} files to {work}")

    py = work / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not py.exists():
        subprocess.run([sys.executable, "-m", "venv", str(work / ".venv")], check=True)
    subprocess.run([str(py), "-m", "pip", "install", "-q", "--disable-pip-version-check", *PIP], check=True)

    npm = shutil.which("npm")
    if not npm:
        sys.exit("npm not found. Install Node 18 or newer.")
    if not (work / "package.json").exists():
        subprocess.run([npm, "init", "-y"], cwd=work, check=True, capture_output=True)
    subprocess.run([npm, "i", "--silent", *NPM], cwd=work, check=True)
    print(f"ready. From {work}, run: python build.py fonts <Family> 300 400 500 600 700")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(pathlib.Path(sys.argv[1]).resolve())
