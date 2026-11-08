"""Kit self-test: fresh setup, new render features, and every new check shown to fail on a broken page.
usage: python dev/kit_selftest.py <empty-folder outside the repo>"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

SKILL = pathlib.Path(__file__).resolve().parent.parent / "skills" / "onesheet"
T = pathlib.Path(sys.argv[1]).resolve()
subprocess.run([sys.executable, str(SKILL / "scripts/setup_work.py"), str(T)], check=True)
ok = True


def run(*a):
    # Plain system-style python on purpose: build.py must hand itself over to .venv.
    r = subprocess.run([sys.executable, "build.py", *a], cwd=T, capture_output=True, text=True, encoding="utf-8")
    return r.returncode, r.stdout + r.stderr


def check(name, cond, detail=""):
    global ok
    ok = ok and bool(cond)
    print(("PASS " if cond else "FAIL ") + name, "" if cond else f"\n     {detail[-600:]}")


assert (T / "build.py").exists() and not (T / "page.html").exists() and (T / "starter/page.html").exists()
check("setup puts tools in work and samples in starter", True)
shutil.copytree(T / "starter", T, dirs_exist_ok=True)
run("fonts", "Figtree", "300", "400", "500", "600", "700")
code, out = run("fonts", "JetBrains Mono", "500")
check("fonts", code == 0, out)

specs = {
    "hero": {"type": "device", "form": "window", "w": 700, "h": 460, "ss": 1, "font": "Figtree", "mono": "JetBrains Mono", "screenW": 1.6, "screenH": 1.0,
             "shadowInk": "#102a2c", "rotate": [-6, -24, -3], "camera": {"el": 6, "fov": 18, "dist": 2.9},
             "screen": {"terminal": {"x": 70, "y": 180, "lines": [{"t": "<|en|> -> != result", "c": "#ffffff"}]}},
             "extras": [{"offset": [0.7, 0.1, -0.3], "screenH": 0.8, "spots": {"back": [0.8, 0.3]}, "screen": {"terminal": {"bg": "#fbfbfd", "dots": False, "lines": [{"t": "source", "c": "#000"}]}}}],
             "spots": {"output": [0.2, 0.28]}},
    "stack": {"type": "plates", "w": 700, "h": 700, "ss": 1, "font": "Figtree", "mono": "JetBrains Mono", "gap": 0.5, "shadowInk": "#102a2c",
              "camera": {"az": 10, "el": 24, "fov": 18, "dist": 3.6}, "shadow": {"opacity": 0.15, "blur": 20, "pad": 0.2},
              "layers": [{"id": "a", "level": 0, "x": -0.9, "scale": 0.5, "tint": "#ffd9c7", "opaque": True},
                         {"id": "b", "level": 0, "x": 0.9, "scale": 0.5, "glass": 0.8},
                         {"id": "top", "level": 1, "rim": "#0a1a3f", "marks": [{"kind": "code", "x": 120, "y": 450, "size": 120, "lines": ["<|en|> -> !="]}]}]},
    "system": json.loads((T / "starter/specs/system.json").read_text(encoding="utf-8")),
}
for n, s in specs.items():
    (T / "specs" / f"{n}.json").write_text(json.dumps(s), encoding="utf-8")
code, out = run("render", "hero", "stack", "system")
check("device, plates and blocks render with the new options", code == 0, out)
meta = json.loads((T / "renders/stack.json").read_text(encoding="utf-8"))
check("plates have left and right spots", {"a", "a_left", "top_left"} <= set(meta["spots"]), str(meta["spots"]))
herometa = json.loads((T / "renders/hero.json").read_text(encoding="utf-8"))
check("extras have spots", "back" in herometa["spots"], str(herometa["spots"]))
check("edges reported per side", set(herometa["edges"]) == {"left", "top", "right", "bottom"}, str(herometa))
check("flat previews written", (T / "out/hero_flat.jpg").exists())

layout = json.loads((T / "starter/layout.json").read_text(encoding="utf-8"))
page0 = (T / "starter/page.html").read_text(encoding="utf-8")
filler = " ".join(["word"] * 190)
body = page0.replace("</div>\n</body>", f'  <p class="a note" style="left:13mm; right:13mm; top:176mm;">{filler}</p>\n</div>\n</body>')
(T / "starter_diagram_ok").write_text("", encoding="utf-8")
subprocess.run([sys.executable, "diagram.py"], cwd=T, check=True)


def build(page=body, lay=None, frag=None):
    (T / "page.html").write_text(page, encoding="utf-8")
    (T / "layout.json").write_text(json.dumps(lay or layout), encoding="utf-8")
    if frag is not None:
        (T / "diagram.svgfrag").write_text(frag, encoding="utf-8")
    return run("page")


good_frag = (T / "diagram.svgfrag").read_text(encoding="utf-8")
code, out = build()
unrelated = [l for l in out.splitlines() if "dpi" not in l and l.startswith("  ")]
check("A4 starter: only the low-res test renders fail", code == 1 and not unrelated and "under 300 dpi" in out, out)
print("   ", [l for l in out.splitlines() if l.startswith("pages")])

letter = {**layout, "size": "Letter"}
code, out = build(lay=letter)
unrelated = [l for l in out.splitlines() if "dpi" not in l and l.startswith("  ")]
check("Letter starter: same, and Letter size", "[215.9, 279.4]" in out and not unrelated, out)

# Each broken page must fail for the stated reason.
code, out = build(page=page0)
check("catches a page under the word budget", "words on the page" in out, out)
long = body.replace(filler, " ".join(["word"] * 330))
code, out = build(page=long)
check("catches a page over the word budget", "words on the page" in out, out)
tiny = body.replace("</div>\n</body>", '<p class="a" style="left:60mm; top:20mm; font-size:5pt; line-height:6pt;">tiny text</p></div>\n</body>')
code, out = build(page=tiny)
check("catches type under the minimum", "type too small" in out, out)
over = good_frag + '<rect x="13" y="176" width="10" height="6" fill="#fff" stroke="#000"/><text x="14" y="180" font-size="2.6">far too long for this box</text>'
code, out = build(frag=over)
check("catches diagram text leaving its box", "crosses a diagram box edge" in out, out)
smallsvg = good_frag + '<text x="14" y="190" font-size="1.5">tiny diagram text</text>'
code, out = build(frag=smallsvg)
check("catches small diagram text", "in the diagram" in out, out)
clash = good_frag + '<text x="14" y="195" font-size="2.6">first label</text><text x="15" y="195" font-size="2.6">second label</text>'
code, out = build(frag=clash)
check("catches diagram text touching diagram text", "touches" in out, out)
build(frag=good_frag)
panel = body.replace("</div>\n</body>", '<div class="a" style="left:20mm; top:30mm; width:60mm; height:20mm; background:#111;"></div><p class="a" style="left:22mm; top:33mm; color:#fff;">caption on it</p></div>\n</body>')
code, out = build(page=panel)
check("catches text on a filled box", "text on a box" in out, out)
nested = body.replace("</div>\n</body>", '<div class="a" style="left:125mm; top:60mm; width:60mm; height:20mm; background:#111; color:#fff;">inside it</div></div>\n</body>')
code, out = build(page=nested)
check("no false alarm for text nested in its box", "text on a box" not in out, out)

meta = json.loads((T / "renders/hero.json").read_text(encoding="utf-8"))
meta["edges"]["right"] = 255
(T / "renders/hero.json").write_text(json.dumps(meta), encoding="utf-8")
code, out = build()
check("catches clipping on an edge with no bleed", "cut off at the image edge" in out, out)
b = json.loads(json.dumps(layout))
b["images"]["hero"]["bleed"] = ["right"]
code, out = build(lay=b)
check("named bleed that stops short of the page fails", "stops short" in out, out)
b["images"]["hero"].update(x=120, w=95)
code, out = build(lay=b)
check("named bleed reaching the page passes", "stops short" not in out and "cut off" not in out, out)
meta["edges"].update(right=0, left=255)
(T / "renders/hero.json").write_text(json.dumps(meta), encoding="utf-8")
code, out = build(lay=b)
check("a bleed on one side doesn't excuse another", "hero (left)" in out, out)
meta["edges"].update(left=0)
(T / "renders/hero.json").write_text(json.dumps(meta), encoding="utf-8")

(T / "facts.md").write_text("| Fact | Value | Source | Status |\n|---|---|---|---|\n| Tests | 401 | tests.py:777 | verified |\n", encoding="utf-8")
num = body.replace("</div>\n</body>", '<p class="a" style="left:20mm; top:30mm;">Got 401, then 777 and 5.</p></div>\n</body>')
code, out = build(page=num)
line = next((l for l in out.splitlines() if l.startswith("numbers not in")), "")
check("number check: trailing comma fine, source column doesn't count, one digit counts",
      "'401'" not in line and "401," not in line and "'777'" in line and "'5'" in line, line)

code, out = run("spots")
check("spots prints mm", "mm" in out and "output:" in out, out)
code, out = run("zoom", "13", "20", "60", "40")
check("zoom writes a crop", (T / "out/zoom.png").exists(), out)
# Iteration-2 fixes
build(frag=good_frag)
code, out = build(page=body.replace("--font: Figtree;", "--font: Figtree; --other: 1;"))
check("no --page-w token is needed", "NoneType" not in out and "pages: 1" in out, out)
code, out = build(page=body.replace("</div>\n</body>", '<p class="a" style="left:125mm; top:60mm;">a powerful tool</p></div>\n</body>'))
check("catches a default banned word with an empty banned list", "powerful" in out and "banned words" in out, out)
rule = good_frag + '<text x="14" y="223" font-size="2.6">label on the rule</text>'
ruled = body.replace('<div class="a rule" style="top:calc({{PAGE_H}}mm - 75mm);"></div>', '<div class="a rule" style="top:222mm;"></div>')
code, out = build(page=ruled, frag=rule)
check("catches diagram text on a rule", "label on the rule" in out and "text on a box" in out, out)
build(frag=good_frag)
s2 = specs["stack"]; s2["thickness"] = 0.03; s2["shadow"] = {"opacity": 0}
(T / "specs/stack.json").write_text(json.dumps(s2), encoding="utf-8")
code, out = run("render", "stack")
meta = json.loads((T / "renders/stack.json").read_text(encoding="utf-8"))
check("thickness and shadow off render, and front spots exist", code == 0 and "top_front" in meta["spots"], out)
print("\nALL PASS" if ok else "\nSOME FAILED")
sys.exit(0 if ok else 1)
