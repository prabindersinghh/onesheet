# onesheet build kit

Everything needed to turn a page plan into a finished PDF. In the skill, this file lives at `references/BUILD-KIT.md`.

**Read sections 1 to 6.** Sections 7 and 8 are the code and starter files, which `scripts/setup_work.py` extracts for you. Read those only when you need to change the code.

Contents: 1 Set up · 2 Scene types · 3 layout.json · 4 Pitfalls · 5 What first versions get wrong · 6 What's been tested · 7 The files · 8 Starter files

The pipeline is:

```
specs/*.json -> render.html (three.js) -> renders/*.png + spot positions
page.html + layout.json + renders -> onepager.html -> PDF -> automated checks -> page images to review
```

## 1. Set up the work folder

Needs Python 3.10+, Node 18+, and Chrome or Edge. Create the work folder outside any downloaded repo:

```bash
python <skill folder>/scripts/setup_work.py work     # tools, a .venv and node_modules
```

Tools land in `work/`. Sample content lands in `work/starter/`, so write your real `page.html`, `layout.json`, `facts.md`, `diagram.py` and `specs/` fresh in `work/`, reading the starters for reference. To try the sample page instead, copy everything from `starter/` into `work/`, and expect the word count check to fail on its short copy.

The scripts use the installed Chrome or Edge. If neither is installed, stop and ask the user to install one.

Commands, all run from `work/`. `build.py` hands itself to `.venv` automatically, so any `python` works:

```bash
python build.py fonts Figtree 300 400 500 600 700   # static TTFs and fonts/fonts.css
python build.py render hero stack                   # renders specs, flat previews in out/<name>_flat.jpg
python diagram.py                                   # draws the vector diagram
python build.py page                                # builds the PDF and runs the checks
python build.py spots                               # each render's content box and spots, in page mm
python build.py zoom 13 150 90 60                   # 400 dpi crop of the PDF to out/zoom.png: x y w h in mm
```

Write long files with a file-writing tool. Large shell heredocs failed in all three test runs.

The three.js library loads from a CDN at a pinned version. Only the library request goes out, never repo content. If the machine must stay offline, run `npm i three@0.170.0` and point the import map in `render.html` to `node_modules/three`.

## 2. Scene types

Each `specs/<name>.json` makes `renders/<name>.png` (transparent background) and `renders/<name>.json` (spot positions from 0 to 1 across the image, plus clipping information).

Common fields:

```json
{
  "type": "plates | blocks | device | glb",
  "w": 1500, "h": 1650, "ss": 2,
  "font": "Figtree",
  "camera": { "az": -32, "el": 25, "fov": 18, "dist": 4.7, "ty": -0.06 },
  "env": { "room": 0.5, "strip": 1, "sheen": 0 },
  "shadow": { "opacity": 0.2 }
}
```

Render size: `w` is the printed width in mm / 25.4 x 300. Use `"ss": 1` and half the size for test renders, then `"ss": 2` for the final.

Camera: `az` turns around the object, `el` is height, `fov` is lens width (18 to 30 reads as product photography), `dist` multiplies the object's largest dimension, and `ty` and `tx` shift the framing. A negative `ty` moves the object up in the image. Because `dist` follows the largest dimension, widening a scene also shrinks it, so raise `w` to stay at 300 dpi.

Starting points that worked on real pages:

| Scene | `dist` | Others |
|---|---|---|
| Single stack of 4 plates | 3.95 | `az -30, el 24, fov 20, ty -0.1`, `gap 0.46` |
| Stack above a row of 4 tiles | 3.7 | `az 10, el 24, fov 18`, `gap 0.54`, tile `scale` 0.38 at 0.64 spacing |
| Staircase of 4 plates, input to output | 1.74 | `az 12, el 27, fov 18`, `gap 0.5`, `x` offsets of 1.24, `w 2560, h 1228` for 217 mm wide. Set `shadow.opacity` to 0, because a floor shadow smears across a staircase. |
| Wide screen with a plate behind it | 1.88 | `el 6, fov 18`. The default of 3.4 leaves this scene small. |

Lighting for dark glossy objects: `"room": 0.1, "strip": 0.12, "sheen": 0.5`. For metal, keep the defaults.

### plates: exploded layers

The best general-purpose shape. Use it for what makes up one request, one record, one prediction or one API call. Layers go bottom to top and get a thin rim in their own colour. Coordinates in `marks` are on a 1600 x 1000 canvas. Keep the important mark in the same spot on each layer so the stack reads as one thing pulled apart. Spots are named after each layer's `id` and sit on its right-hand corner.

```json
{
  "type": "plates", "w": 1500, "h": 1650, "ss": 2, "font": "Figtree", "gap": 0.5,
  "camera": { "az": -32, "el": 25, "fov": 18, "dist": 4.7, "ty": -0.06 },
  "shadow": { "opacity": 0.2 },
  "layers": [
    { "id": "base", "rim": "#f0b429", "opaque": true, "marks": [ { "kind": "image", "src": "assets/shot.jpg" } ] },
    { "id": "target", "rim": "#1a56e0", "marks": [ { "kind": "brackets", "x": 540, "y": 350, "w": 500, "h": 330, "color": "#1a56e0" } ] },
    { "id": "risk", "rim": "#e5484d", "marks": [ { "kind": "dash", "x": 350, "y": 36, "w": 760, "h": 276, "color": "#e5484d" } ] },
    { "id": "ok", "rim": "#12a06a", "marks": [ { "kind": "check", "x": 790, "y": 515, "r": 170, "color": "#12a06a" } ] },
    { "id": "words", "rim": "#0a1a3f", "marks": [ { "kind": "text", "x": 120, "y": 450, "size": 134, "color": "#0a1a3f", "lines": ["Short real text", "on the top plate."], "leading": 170 } ] }
  ]
}
```

Mark kinds: `image`, `brackets`, `dash`, `check`, `text`, `code` (monospace lines, using the spec's `mono` font), `fill`.

Each layer also gets spots named `<id>_left`, on its left-hand corner, and `<id>_front`, at the middle of its front edge, for vertical leaders. Optional layer fields: `level` (height in gaps, so several layers can share one), `x` and `z` (offset), `scale`, `tint` (plate colour) and `glass` (opacity). A row of layers at one level under a stack shows a pluggable part.

Optional spec fields: `thickness` (default 0.012, and 0.03 looks less like paper), `glass` (opacity of all plates), `rim` (rim thickness, while a layer's `rim` is its colour), `shadowInk` (hex, so the shadow matches your ink, in every scene type) and, inside `shadow`, `pad` and `blur`. If the shadow clips, lower `pad` and `blur`, and try `ty`.

Text on plates is foreshortened, so use short strings at 130 px or more. A long token may need about 110 px.

### blocks: isometric systems

For services, pipelines and infrastructure. Spots are named after each node's `id` and sit on its top centre.

```json
{
  "type": "blocks", "w": 1800, "h": 1100, "ss": 2, "font": "Figtree",
  "camera": { "az": -35, "el": 32, "fov": 18, "dist": 2.6 },
  "nodes": [
    { "id": "api", "x": -1.3, "z": 0, "w": 0.9, "d": 0.9, "h": 0.22, "color": "#1a56e0", "label": "API", "labelColor": "#ffffff" },
    { "id": "queue", "x": 0, "z": 0, "w": 0.9, "d": 0.9, "h": 0.12, "color": "#eef2fa", "label": "Queue", "labelColor": "#0a1a3f" },
    { "id": "store", "x": 1.3, "z": 0, "w": 0.9, "d": 0.9, "h": 0.34, "color": "#0a1a3f", "label": "Store", "labelColor": "#ffffff" }
  ],
  "edges": [ { "from": "api", "to": "queue", "color": "#1a56e0" }, { "from": "queue", "to": "store", "color": "#1a56e0" } ]
}
```

### device: real screens on a built-from-scratch body

`form` is `phone`, `window` or `laptop`. A `screen` has either an `image` (use a real screenshot), or `terminal` lines, which take one colour per line. For multi-coloured output, draw it to an image yourself. A screen is drawn 1400 px wide, so set `"px"` in the `screen` higher for a big screen at 300 dpi. `spots` take u, v positions on the screen from 0 to 1, so labels can point at parts of the interface.

```json
{
  "type": "device", "form": "window", "w": 1800, "h": 1300, "ss": 2,
  "screenW": 1.6, "screenH": 1.0, "rotate": [-6, -24, -3], "body": "#20283a",
  "camera": { "el": 6, "fov": 18, "dist": 3.4 },
  "screen": { "terminal": { "lines": [ { "t": "$ tool build ./src", "c": "#ffffff" }, { "t": "built 12 files", "c": "#2bd48f" } ] } },
  "spots": { "output": [0.3, 0.2] }
}
```

### glb: a real 3D model

Only for models from the repo or supplied by the user. First print the model's material names, then override them. In `materials`, `glass` and `drop`, names match by substring. `glass` gives clear lenses with a soft diagonal reflection. `drop` removes parts such as logos. `hotspots` are model coordinates. `screen` puts an image on a flat part.

```json
{
  "type": "glb", "src": "assets/product.glb", "w": 2800, "h": 1400, "ss": 2,
  "env": { "room": 0.1, "strip": 0.12, "sheen": 0.5 },
  "camera": { "az": -34, "el": 9, "fov": 26, "dist": 1.72, "ty": -0.05 },
  "drop": ["LOGO"],
  "glass": ["Lens"],
  "materials": { "Frame": { "color": "#090d18", "roughness": 0.5, "clearcoat": 0.6, "clearcoatRoughness": 0.42, "envMapIntensity": 0.62 } },
  "hotspots": { "camera": [23.0, 2.8, 15.5] },
  "shadow": { "type": "ellipse", "rx": 0.56, "rz": 0.3, "lift": 0.3, "opacity": 0.11 }
}
```

To list materials, open `render.html?spec=<name>` and read the `materials` list in `renders/<name>.json`.

### Layered screens

To show a transformation, put the input behind its result with `extras`. This hero from the Glow trial is the pattern to copy. Offsets are in scene units: positive x is right, negative z is behind. Use `"mono"` for a monospace font, loaded with `build.py fonts`. For code and terminal text, match the real output, and caption anything you reconstructed.

An extra can have its own `spots`, so leaders can land on it. Set `x` and `y` in a `terminal` to place its text in canvas pixels, which keeps text clear of the part hidden by the front screen.

```json
{
  "type": "device", "form": "window", "w": 1900, "h": 2150, "ss": 2, "mono": "IBM Plex Mono",
  "screenW": 0.92, "screenH": 1.576, "radius": 0.022, "bezel": 0.012, "rotate": [-4, -20, -2], "body": "#2a2a30",
  "camera": { "el": 5, "fov": 20, "dist": 3.5, "tx": 0.012 },
  "screen": { "image": "assets/shot.png" },
  "extras": [ { "offset": [0.66, 0.14, -0.34], "screenH": 1.2, "body": "#c9cfdb",
    "screen": { "terminal": { "bg": "#fbfbfd", "dots": false, "size": 42, "lines": [ { "t": "# Source text", "c": "#6b5cff" } ] } } } ],
  "spots": { "table": [0.012, 0.6] },
  "shadow": { "rx": 0.62, "rz": 0.34, "lift": 0.03, "opacity": 0.13 }
}
```

## Vector diagrams

Draw the "how it works" diagram with `diagram.py` (section 8). It writes real vector lines and real text in mm, which `{{DIAGRAM}}` in `page.html` picks up, so it stays razor sharp and searchable.

Rules that make a diagram good:

- Trace it from the code, and show only branches that really exist.
- Read left to right: inputs, steps, outputs. Show a route that skips steps as its own line.
- Use accent colour only for the main path. Secondary routes stay grey.
- Give each box a bold name and one short line. Use the real command as the second line when you can.
- Fill one box lightly to mark the step that matters most.
- Align columns to the page grid, and space boxes evenly.

`text()` takes `mono=True` for code, and escapes its text, so `<|en|>` is safe. `line()` points its arrowhead along the last segment in any direction. The build checks diagram text for size, overflow from its box and collisions.

## 3. layout.json

All positions are in mm from the page's top left. A negative `x` lets the hero bleed past the page edge. Image height comes from the render's proportions.

```json
{
  "title": "Project: what it does",
  "author": "Name",
  "subject": "One-page brief",
  "pdf": "out/project-one-pager.pdf",
  "size": "A4",
  "url": "https://example.com",
  "banned": ["internal-name"],
  "images": { "hero": { "x": -12, "y": 9.4, "w": 234 } },
  "leaders": [
    { "image": "hero", "spot": "camera", "to": [190, 39.4], "color": "#1a56e0" },
    { "image": "hero", "at": [0.86, 0.36], "to": [190, 39.4], "color": "#1a56e0", "toDot": true }
  ]
}
```

Use `spot` for a position from the render, and `at` for one you read off the image. Set `url` to null for no QR code. `pdf` is relative to `work/`, so `"../name.pdf"` puts it beside the folder.

For an image that deliberately runs off the page, name the sides: `"bleed": ["right"]`. Other sides stay checked for clipping, and the build fails if a bled side stops short of the page edge. `"bleed": true` means all sides.

Keep each label's position in step with its spot: `build.py spots` prints the values to use after every camera change.

Level leader lines look cleanest. Set `"to": [x, null]`, and the build prints the y of each line. Then set the label's top to that y minus about 1.5 mm.

## 4. Pitfalls already paid for

| Symptom | Cause | Fix |
|---|---|---|
| Spot positions far outside 0 to 1 | Camera matrices were stale when projecting | Call `cam.updateMatrixWorld()` first. The kit does. |
| Speckles or blotches on inner edges | Depth precision too low, or low-poly facets in sharp reflections | Keep near and far close to the object. Raise roughness and lower `envMapIntensity`. |
| Glass renders black or as a flat fill | Transmission samples an empty background, and flat lenses reflect one tone | Don't use transmission. Use the kit's `glass` material. |
| Glossy frame looks like chrome | Bright side strips reflected directly | `"room": 0.1, "strip": 0.12` |
| Frame looks like a flat cutout | Nothing for it to reflect | Add `"sheen": 0.5` |
| A hard-edged band under an object | Shadow wider than the image, so it's clipped | Shrink `rx` and `rz`, or enlarge the canvas. The build's clipping warning catches this. |
| A square-looking shadow | The silhouette of a U-shaped object | Use the `ellipse` shadow |
| Render looks black in an image viewer | Some viewers show transparency as black | Check the alpha value, or flatten on white before judging |
| An ugly model colour or a brand logo | It came with the model | Override it in `materials`, remove it with `drop` |
| Blurry photo on a plate | Crop too small for the plate | Crop from the largest source, and check it at 200 dpi |
| Text on 3D plates can't be read | Too small after foreshortening | Use 130 px or more on the 1600 px canvas, in two short lines |
| Second blank PDF page | The page is a hair too tall | Keep `.sheet` at 296.9 mm for A4 |
| Colours missing in the PDF | Backgrounds dropped when printing | `print-color-adjust: exact`, and `printBackground` in the print call |
| Fuzzy text in Acrobat | Variable fonts can embed poorly | Use static TTFs from `build.py fonts` |
| Rasterized shadows bloat the PDF | CSS `filter` and `box-shadow` | Keep soft effects in the renders. CSS stays flat. |
| Text fits in HTML, overflows in the PDF | Real line lengths differ from your estimate | Always check the printed page |
| Canvas text in the wrong font | The font hadn't loaded | The kit waits for it, if `font` is set in the spec |
| `<\|` or `->` turns into a symbol in code | Font ligatures, in JetBrains Mono for one | The kit turns them off on canvases and in the starter CSS. Set `font-variant-ligatures: none` on your own code styles. |
| Mono text in the diagram renders in the sans | A CSS rule on `svg text` overrides the `font-family` attribute | Use `text(..., mono=True)`, which sets an inline style |
| An opaque plate prints lighter than its `tint` | Clearcoat and studio light add brightness: `#b4541f` came out near `#ef7d4e` | Choose a darker tint, and compare in the flat preview |
| A repo's SVG logo prints black or disappears | It uses `currentColor`, which an `<img>` can't inherit | Replace the fill in your copy in `work/assets/` |
| A figure sits only in a chart image | Many SVG charts store text as paths, so there's nothing to search | Rasterize it through an `<img>` wrapper, so nothing in the file runs, read it at high zoom, and say so in the ledger |
| You need numpy or an audio library to process a repo's data file | The `.venv` has only the build tools | `.venv/Scripts/python -m pip install numpy soundfile` |
| Text-on-box check fires on a label inside a panel | The label is a separate `.a` element placed on the panel | Nest the label inside the panel element |

## 5. What the first version got wrong, and why it matters

These were real problems on earlier pages. Later rounds fixed them, so expect similar ones:

- The headline ran into the intro text. Reduce its size or move the intro.
- Callouts wrapped onto the object. Make them one line, in a box wider than the text, aligned against the leader line.
- Body text overlapped the top of a 3D stack. Reduce the text, and shrink and move the render.
- A 3D object sat on top of a source line. Check the tilted corners, since they reach further than you expect.
- Captions overran the rule below. Inline elements with a larger size push the line box, so set `line-height: 0` on them.
- Hand-placed boxes on a figure looked like real output. Add a caption saying they are illustrative.
- A leader dot covered the first letter of the text it pointed to. Aim just left of the text.
- A headline ran under a 3D object while every text check passed. The build now tests text against the render's real pixels.

Lighting and camera took about four rounds of comparing renders side by side. That is normal, and worth it. When a render is clipped on one side, change `tx` in small steps: 0.01 moved the Glow hero about 18 px, and a lower value moved it right.

## 6. What has and hasn't been tested

Tested on Windows 11 with Chrome, Python 3.12 and Node 24. Every scene type rendered, except `glb` in the latest kit, and each check has been shown to fail on a deliberately broken page.

The whole workflow has run on five real repos: an app, a CLI, a web app, a library and an ML project, including one Letter page and one custom `--audience`.

Not yet tested: macOS and Linux, private repos, very large repos, `--no-internals`, a `glb` hero, and skeleton C.

## 7. The files

<!-- file: build.py -->
```python
#!/usr/bin/env python3
"""onesheet build: fonts, 3D renders, PDF and checks. Run from the work folder."""
import http.server
import json
import os
import pathlib
import re
import subprocess
import sys
import threading
import urllib.request

ROOT = pathlib.Path.cwd()
PAGE_MM = {"A4": (210, 297), "Letter": (215.9, 279.4)}
WORD_BUDGET = (220, 320)
BANNED = ["seamless", "powerful", "robust", "leverage", "revolutionary", "next-generation", "\u2014"]
MIN_DPI = 299  # 300, less rounding when a render's width is worked out from its printed size

# The packages live in .venv, so hand over to it, whichever python started this.
VENV_PY = ROOT / (".venv/Scripts/python.exe" if os.name == "nt" else ".venv/bin/python")
if VENV_PY.exists() and pathlib.Path(sys.prefix).resolve() != VENV_PY.parent.parent.resolve():
    sys.exit(subprocess.run([str(VENV_PY), *sys.argv]).returncode)


class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        m = re.fullmatch(r"/save/([\w.-]+\.(?:png|json))", self.path)
        if not m:
            self.send_error(404)
            return
        body = self.rfile.read(int(self.headers["Content-Length"]))
        (ROOT / "renders").mkdir(exist_ok=True)
        (ROOT / "renders" / m.group(1)).write_bytes(body)
        self.send_response(204)
        self.end_headers()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, *args):
        pass


def serve():
    """Local only, and on a free port, so several builds can run at once."""
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{srv.server_address[1]}"


def node(base, *args, capture=False):
    env = {**os.environ, "BASE": base}
    return subprocess.run(["node", "tools.mjs", *args], cwd=ROOT, env=env, check=True, text=True,
                          capture_output=capture, encoding="utf-8").stdout


def cmd_fonts(family, *weights):
    """Static TrueType files: a plain client gets these from the older Google Fonts API."""
    (ROOT / "fonts").mkdir(exist_ok=True)
    url = f"https://fonts.googleapis.com/css?family={family.replace(' ', '+')}:{','.join(weights)}"
    css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "onesheet"})).read().decode()
    out = []
    for w, src in re.findall(r"font-weight:\s*(\d+);.*?url\((https://[^)]+\.ttf)\)", css, re.S):
        name = f"{family.replace(' ', '')}-{w}.ttf"
        (ROOT / "fonts" / name).write_bytes(urllib.request.urlopen(src).read())
        out.append(f"@font-face {{ font-family: '{family}'; font-weight: {w}; src: url({name}); }}")
    if not out:
        sys.exit(f"No static fonts found for {family}. Check the family name and weights on Google Fonts.")
    css_file = ROOT / "fonts/fonts.css"  # keep other families, so a page can use a sans and a mono
    kept = [l for l in css_file.read_text(encoding="utf-8").splitlines() if f"'{family}'" not in l] if css_file.exists() else []
    css_file.write_text("\n".join(kept + out) + "\n", encoding="utf-8")
    print("fonts:", len(out), "weights of", family)


def cmd_render(*names):
    from PIL import Image
    names = names or [p.stem for p in (ROOT / "specs").glob("*.json")]
    node(serve(), "render", *names)
    (ROOT / "out").mkdir(exist_ok=True)
    for n in names:
        meta = json.loads((ROOT / "renders" / f"{n}.json").read_text(encoding="utf-8"))
        print(f"{n}: spots {list(meta.get('spots', {}))}, content box {meta.get('bbox')}, preview out/{n}_flat.jpg")
        with Image.open(ROOT / "renders" / f"{n}.png") as im:  # transparency shows as black in some viewers
            flat = Image.new("RGB", im.size, "white")
            flat.paste(im, mask=im.getchannel("A"))
        flat.thumbnail((1400, 1400))
        flat.save(ROOT / "out" / f"{n}_flat.jpg", quality=88)
        cut = {k: v for k, v in meta.get("edges", {}).items() if v > 8}
        if cut:
            print(f"  NOTE {n}: content reaches the image edge {cut}. Fine on a side you bleed off the page. Otherwise move the camera back or shrink the shadow.")


def image_boxes(layout):
    from PIL import Image
    boxes = {}
    for name, b in layout.get("images", {}).items():
        with Image.open(ROOT / "renders" / f"{name}.png") as im:
            px = im.size
        meta = ROOT / "renders" / f"{name}.json"
        info = json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else {}
        boxes[name] = {**b, "h": b["w"] * px[1] / px[0], "px": px, "info": info, "spots": info.get("spots", {})}
    return boxes


def cmd_spots():
    """Print where each render's content and spots land on the page, in mm."""
    layout = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
    for name, b in image_boxes(layout).items():
        k = b["w"] / b["px"][0]
        x0, y0, x1, y1 = b["info"].get("bbox", [0, 0, *b["px"]])
        print(f"{name}: content x {b['x'] + x0 * k:.1f} to {b['x'] + x1 * k:.1f}, y {b['y'] + y0 * k:.1f} to {b['y'] + y1 * k:.1f} mm, {b['px'][0] / (b['w'] / 25.4):.0f} dpi")
        for s, p in b["spots"].items():
            print(f"  {s}: x {b['x'] + p['x'] * b['w']:.1f}, y {b['y'] + p['y'] * b['h']:.1f} mm")


def cmd_zoom(x, y, w, h):
    """Crop the finished PDF at 400 dpi, to judge detail. Arguments are in mm."""
    import pypdfium2
    layout = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
    doc = pypdfium2.PdfDocument(str(ROOT / layout.get("pdf", "out/one-pager.pdf")))
    k = 400 / 25.4
    x, y, w, h = float(x), float(y), float(w), float(h)
    (ROOT / "out").mkdir(exist_ok=True)
    doc[0].render(scale=400 / 72).to_pil().convert("RGB").crop((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k))).save(ROOT / "out/zoom.png")
    doc.close()
    print("wrote out/zoom.png")


def leaders_svg(layout, boxes):
    parts = []

    def dot(x, y, col, r=0.62):
        parts.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="{r + 0.3:.2f}" fill="#fff"/><circle cx="{x:.2f}" cy="{y:.2f}" r="{r}" fill="{col}"/>')

    for item in layout.get("leaders", []):
        b = boxes[item["image"]]
        if "spot" in item:
            if item["spot"] not in b["spots"]:
                sys.exit(f"Leader asks for spot '{item['spot']}', but {item['image']} has {list(b['spots'])}")
            sp = b["spots"][item["spot"]]
            fx, fy = sp["x"], sp["y"]
        else:
            fx, fy = item["at"]
        x, y = b["x"] + fx * b["w"], b["y"] + fy * b["h"]
        col = item.get("color", "#1a56e0")
        tx, ty = item["to"]
        if ty is None:  # a level line: put the label's top about 1.5 mm above the printed y
            ty = y
            print(f"leader {item.get('spot', item.get('at'))}: level at y = {y:.1f} mm")
        parts.append(f'<polyline points="{x:.2f},{y:.2f} {tx:.2f},{ty:.2f}" stroke="{col}" stroke-width="{item.get("width", 0.2)}"/>')
        dot(x, y, col)
        if item.get("toDot"):
            parts.append(f'<circle cx="{tx:.2f}" cy="{ty:.2f}" r=".5" fill="{col}"/>')
    return "".join(parts)


SECRETS = [r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}", r"github_pat_\w{20,}", r"sk-[A-Za-z0-9_-]{20,}", r"xox[bap]-[A-Za-z0-9-]{10,}",
           r"-----BEGIN [A-Z ]*PRIVATE KEY", r"(?i)(password|passwd|api[_-]?key|secret)\s*[=:]\s*\S{6,}"]


def check_numbers(text):
    """Every number on the page should appear, whole, in the ledger's Fact or Value column. Sources don't count: they're full of line numbers."""
    number = r"\d+(?:,\d{3})*(?:\.\d+)?"
    ledger = (ROOT / "facts.md").read_text(encoding="utf-8") if (ROOT / "facts.md").exists() else ""
    cells = [c for row in ledger.splitlines() if row.lstrip().startswith("|") for c in row.split("|")[1:3]]
    return sorted(set(re.findall(number, text)) - set(re.findall(number, " ".join(cells))))


def text_over_renders(text_boxes, boxes):
    """Test each line of text against the render's real pixels, so soft shadows and empty corners don't count."""
    from PIL import Image
    hits = set()
    for name, b in boxes.items():
        alpha = Image.open(ROOT / "renders" / f"{name}.png").getchannel("A")
        k = alpha.width / b["w"]
        for label, x, y, w, h in text_boxes:
            area = ((x - b["x"]) * k, (y - b["y"]) * k, (x + w - b["x"]) * k, (y + h - b["y"]) * k)
            area = tuple(int(v) for v in (max(0, area[0]), max(0, area[1]), min(alpha.width, area[2]), min(alpha.height, area[3])))
            if area[2] <= area[0] or area[3] <= area[1]:
                continue
            if alpha.crop(area).getextrema()[1] > 110:
                hits.add(f'"{label}" sits on {name}')
    return sorted(hits)


def cmd_page():
    import pypdfium2
    from PIL import Image
    from pypdf import PdfReader, PdfWriter

    layout = json.loads((ROOT / "layout.json").read_text(encoding="utf-8"))
    (ROOT / "out").mkdir(exist_ok=True)
    pdf = ROOT / layout.get("pdf", "out/one-pager.pdf")
    size = layout.get("size", "A4")
    w_mm, h_mm = PAGE_MM[size]
    boxes, imgs, clipped, short_bleed, low_dpi = image_boxes(layout), [], [], [], []
    for name, b in boxes.items():
        h = b["h"]
        edges = b["info"].get("edges", {})
        bleed = b.get("bleed") or []
        bleed = ["left", "top", "right", "bottom"] if bleed is True else bleed
        touching = [s for s, v in edges.items() if v > 8]
        clipped += [f"{name} ({s})" for s in touching if s not in bleed]
        reach = {"left": b["x"] <= 0, "top": b["y"] <= 0, "right": b["x"] + b["w"] >= w_mm, "bottom": b["y"] + h >= h_mm}
        short_bleed += [f"{name} ({s})" for s in touching if s in bleed and not reach[s]]
        dpi = b["px"][0] / (b["w"] / 25.4)
        if dpi < MIN_DPI:
            low_dpi.append(f"{name} at {dpi:.0f} dpi")
        imgs.append(f'<img class="a" src="renders/{name}.png" alt="{b.get("alt", "")}" style="left:{b["x"]}mm; top:{b["y"]}mm; width:{b["w"]}mm; height:{h:.3f}mm;" />')

    base = serve()
    url = layout.get("url")
    qr = node(base, "qr", url, layout.get("qrColor", "#0a1a3f"), capture=True) if url else ""
    html = (ROOT / "page.html").read_text(encoding="utf-8")
    frag = ROOT / "diagram.svgfrag"
    subs = {"IMAGES": "".join(imgs), "LEADERS": leaders_svg(layout, boxes), "QR": qr, "URL": url or "",
            "DIAGRAM": frag.read_text(encoding="utf-8") if frag.exists() else "",
            "TITLE": layout["title"], "PAGE_W": w_mm, "PAGE_H": h_mm, "SHEET_H": round(h_mm - 0.1, 1)}
    for k, v in subs.items():
        html = html.replace("{{" + k + "}}", str(v))
    left = re.findall(r"{{\w+}}", html)
    if left:
        sys.exit(f"Unfilled placeholders in page.html: {left}")
    (ROOT / "onepager.html").write_text(html, encoding="utf-8")

    raw = ROOT / "out/raw.pdf"
    issues = json.loads(node(base, "pdf", str(raw), capture=True))
    issues["text over a 3D object"] = text_over_renders(issues.pop("_boxes"), boxes)

    w = PdfWriter(clone_from=PdfReader(raw))
    w.add_metadata({"/Title": layout["title"], "/Author": layout.get("author", ""), "/Subject": layout.get("subject", "")})
    w.write(pdf)
    raw.unlink()

    r = PdfReader(pdf)
    text = r.pages[0].extract_text()
    mm = [round(float(v) / 72 * 25.4, 1) for v in r.pages[0].mediabox[2:]]
    fails = []
    words = len(text.split())
    print(f"file: {pdf}\npages: {len(r.pages)}, {os.path.getsize(pdf) / 1048576:.2f} MB, {mm} mm, {words} words")
    if abs(mm[0] - w_mm) > 1 or abs(mm[1] - h_mm) > 1:
        fails.append(f"page is {mm} mm, expected {size} ({w_mm} x {h_mm})")
    if not WORD_BUDGET[0] <= words <= WORD_BUDGET[1]:
        fails.append(f"{words} words on the page, including diagrams and code. The budget is {WORD_BUDGET[0]} to {WORD_BUDGET[1]}.")
    if low_dpi:
        fails.append(f"under 300 dpi as printed: {low_dpi}. Fine for a test render. Raise w and h for the final.")
    if short_bleed:
        fails.append(f"bleed stops short of the page edge: {short_bleed}. Move or widen the image.")
    if len(r.pages) != 1:
        fails.append(f"{len(r.pages)} pages, must be 1")
    if os.path.getsize(pdf) > 8 * 1048576:
        fails.append("over 8 MB")
    if clipped:
        fails.append(f"render content cut off at the image edge: {clipped}. Fix it, or name that side in the image's \"bleed\" if the crop is deliberate.")
    for kind, items in issues.items():
        for it in items:
            fails.append(f"{kind}: {it}")
    banned = [b for b in layout.get("banned", []) + BANNED if b.lower() in text.lower()]
    if banned:
        fails.append(f"banned words on the page: {banned}")
    hits = [p for p in SECRETS if re.search(p, text)]
    if hits:
        fails.append(f"secret-like text on the page, matching: {hits}")
    missing = check_numbers(text)
    if missing:
        print("numbers not in facts.md, check each by hand:", missing)
    links = [a.get_object()["/A"]["/URI"] for a in (r.pages[0].get("/Annots") or []) if "/A" in a.get_object()]
    print("links:", links)

    doc = pypdfium2.PdfDocument(str(pdf))
    page = doc[0].render(scale=200 / 72).to_pil().convert("RGB")
    page.save(ROOT / "out/page.png")
    page.resize((page.width * 110 // 200, page.height * 110 // 200), Image.LANCZOS).save(ROOT / "out/page_small.jpg", quality=90)
    page.crop((0, 0, page.width, page.height // 2)).save(ROOT / "out/z_top.png")
    page.crop((0, page.height // 2, page.width, page.height)).save(ROOT / "out/z_bottom.png")
    if url:
        doc[0].render(scale=300 / 72).to_pil().convert("RGB").save(ROOT / "out/page300.png")
        got = node(base, "qrcheck", str(ROOT / "out/page300.png"), capture=True).strip()
        (ROOT / "out/page300.png").unlink()
        print("QR decodes to:", got)
        if got.rstrip("/") != url.rstrip("/"):
            fails.append(f"QR decodes to '{got}', expected {url}")
    doc.close()
    print("CHECKS FAILED:\n  " + "\n  ".join(fails) if fails else "All automated checks passed. Now look at out/page_small.jpg, out/z_top.png and out/z_bottom.png.")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    cmds = {"fonts": cmd_fonts, "render": cmd_render, "page": cmd_page, "spots": cmd_spots, "zoom": cmd_zoom}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit("usage: build.py fonts <Family> <weights...> | render [spec ...] | page | spots | zoom <x> <y> <w> <h>")
    cmds[sys.argv[1]](*sys.argv[2:])
```

<!-- file: tools.mjs -->
```javascript
// Browser jobs for build.py: render 3D specs, print the PDF, make and read the QR code.
import fs from 'node:fs';
import { chromium } from 'playwright';
import QRCode from 'qrcode';
import jsQR from 'jsqr';
import { PNG } from 'pngjs';

const [cmd, ...args] = process.argv.slice(2);
const BASE = process.env.BASE;

async function launch() {
  const gl = ['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'];
  for (const channel of ['chrome', 'msedge', undefined]) {
    try { return await chromium.launch({ channel, headless: true, args: gl }); } catch { /* try the next browser */ }
  }
  throw new Error('No browser found. Install Chrome or Edge, then run the command again.');
}

async function render(names) {
  const b = await launch();
  for (const name of names) {
    const page = await b.newPage();
    const errs = [];
    page.on('pageerror', (e) => errs.push(String(e)));
    await page.goto(`${BASE}/render.html?spec=${encodeURIComponent(name)}`);
    await page.waitForFunction(() => window.__done || window.__failed, null, { timeout: 600000 }).catch(() => errs.push('timed out'));
    const failed = await page.evaluate(() => window.__failed || null);
    if (failed || errs.length) throw new Error(`${name}: ${failed || errs.join('; ')}`);
    await page.close();
  }
  await b.close();
}

// Finds real collisions from the laid-out text, not from element boxes.
function findLayoutIssues() {
  const sheet = document.querySelector('.sheet').getBoundingClientRect();
  const mm = 96 / 25.4; // CSS pixels per mm
  const margin = 7 * mm;
  const blocks = [...document.querySelectorAll('.sheet .a')].filter((el) => el.tagName !== 'IMG' && el.tagName !== 'svg' && el.textContent.trim());
  const rects = blocks.map((el) => {
    const r = document.createRange(); r.selectNodeContents(el);
    return { el, rs: [...r.getClientRects()].filter((c) => c.width > 0.5 && c.height > 0.5) };
  });
  const label = (el) => el.textContent.trim().replace(/\s+/g, ' ').slice(0, 42);
  const collisions = [], outside = [];
  rects.forEach((a, i) => {
    for (const c of a.rs) {
      if (c.left < sheet.left + margin || c.right > sheet.right - margin || c.top < sheet.top + margin || c.bottom > sheet.bottom - margin) {
        outside.push(label(a.el)); break;
      }
    }
    for (let j = i + 1; j < rects.length; j++) {
      const b = rects[j];
      if (a.el.contains(b.el) || b.el.contains(a.el)) continue;
      const hit = a.rs.some((p) => b.rs.some((q) => p.left < q.right - 0.5 && q.left < p.right - 0.5 && p.top < q.bottom - 1 && q.top < p.bottom - 1));
      if (hit) collisions.push(`"${label(a.el)}" touches "${label(b.el)}"`);
    }
  });
  const overlap = (p, q) => p.left < q.right - 0.5 && q.left < p.right - 0.5 && p.top < q.bottom - 0.5 && q.top < p.bottom - 0.5;

  // Text sitting on a filled box or a rule it isn't part of: the text checks above can't see these.
  const onBox = [];
  const filled = [...document.querySelectorAll('.sheet .a')].filter((el) => el.tagName !== 'IMG' && el.tagName !== 'svg' && !/rgba\(0, 0, 0, 0\)|transparent/.test(getComputedStyle(el).backgroundColor));
  for (const f of filled) {
    const box = f.getBoundingClientRect();
    for (const a of rects) {
      if (a.el === f || a.el.contains(f) || f.contains(a.el)) continue;
      if (a.rs.some((c) => overlap(c, box))) onBox.push(`"${label(a.el)}" sits on "${label(f) || 'a rule or filled box'}"`);
    }
  }

  // Diagram text. Glyph boxes are taller than the glyphs, so trim them before comparing.
  const trim = (r) => { const d = r.height * 0.18; return { left: r.left, right: r.right, top: r.top + d, bottom: r.bottom - d, width: r.width, height: r.height - 2 * d }; };
  const svgText = [...document.querySelectorAll('.sheet svg text')].map((el) => ({ el, r: trim(el.getBoundingClientRect()), s: el.textContent.trim().slice(0, 42) }));
  const svgBoxes = [...document.querySelectorAll('.sheet svg rect')].map((el) => el.getBoundingClientRect()).filter((r) => r.width > 2 && r.height > 2);
  const overflow = [];
  svgText.forEach((t, i) => {
    for (const f of filled) if (overlap(t.r, f.getBoundingClientRect())) onBox.push(`"${t.s}" sits on "${label(f) || 'a rule or filled box'}"`);
    if (t.r.left < sheet.left + margin || t.r.right > sheet.right - margin || t.r.top < sheet.top + margin || t.r.bottom > sheet.bottom - margin) outside.push(t.s);
    for (const b of svgBoxes) {
      const inside = t.r.left >= b.left - 0.5 && t.r.right <= b.right + 0.5 && t.r.top >= b.top - 0.5 && t.r.bottom <= b.bottom + 0.5;
      if (overlap(t.r, b) && !inside) { overflow.push(`"${t.s}" crosses a diagram box edge`); break; }
    }
    for (let j = i + 1; j < svgText.length; j++) if (overlap(t.r, svgText[j].r)) collisions.push(`"${t.s}" touches "${svgText[j].s}"`);
    for (const a of rects) if (a.rs.some((c) => overlap(t.r, c))) collisions.push(`"${t.s}" touches "${label(a.el)}"`);
  });

  // Type sizes, as printed. Limits are from the skill: 6.2 pt for page text, 5.8 pt in diagrams.
  const small = new Set();
  const pt = (el) => parseFloat(getComputedStyle(el).fontSize) * 0.75;
  const walker = document.createTreeWalker(document.querySelector('.sheet'), NodeFilter.SHOW_TEXT);
  while (walker.nextNode()) {
    const n = walker.currentNode, el = n.parentElement;
    if (!n.textContent.trim() || el.closest('svg')) continue;
    if (pt(el) < 6.19) small.add(`${pt(el).toFixed(2)} pt: "${n.textContent.trim().slice(0, 30)}"`);
  }
  for (const t of svgText) {
    const svg = t.el.ownerSVGElement, scale = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
    const size = pt(t.el) * scale;
    if (size < 5.79) small.add(`${size.toFixed(2)} pt in the diagram: "${t.s}"`);
  }

  // Text boxes in mm, so build.py can test them against the renders' actual pixels.
  const toMm = (l, c) => [l, (c.left - sheet.left) / mm, (c.top - sheet.top) / mm, c.width / mm, c.height / mm];
  const boxes = [...rects.flatMap((a) => a.rs.map((c) => toMm(label(a.el), c))), ...svgText.map((t) => toMm(t.s, t.r))];
  return { 'text collision': [...new Set(collisions)], 'text on a box': [...new Set(onBox)], 'diagram text overflow': [...new Set(overflow)], 'type too small': [...small], 'outside the margins': [...new Set(outside)], _boxes: boxes };
}

async function pdf(path) {
  const b = await launch();
  const page = await b.newPage();
  await page.goto(`${BASE}/onepager.html`, { waitUntil: 'networkidle' });
  await page.evaluate(() => document.fonts.ready);
  await page.emulateMedia({ media: 'print' });
  const issues = await page.evaluate(findLayoutIssues);
  await page.pdf({ path, preferCSSPageSize: true, printBackground: true });
  await b.close();
  process.stdout.write(JSON.stringify(issues));
}

if (cmd === 'render') await render(args);
else if (cmd === 'pdf') await pdf(args[0]);
else if (cmd === 'qr') {
  const svg = await QRCode.toString(args[0], { type: 'svg', errorCorrectionLevel: 'M', margin: 0, color: { dark: args[1], light: '#0000' } });
  process.stdout.write(svg.slice(svg.indexOf('<svg')));
} else if (cmd === 'qrcheck') {
  const p = PNG.sync.read(fs.readFileSync(args[0]));
  const r = (jsQR.default || jsQR)(new Uint8ClampedArray(p.data), p.width, p.height);
  process.stdout.write(r ? r.data : 'NOT READABLE');
} else throw new Error('unknown command ' + cmd);
```

<!-- file: render.html -->
```html
<!doctype html>
<meta charset="utf-8" />
<title>onesheet render</title>
<link rel="stylesheet" href="fonts/fonts.css" />
<style>body { margin: 0; background: #fff; } canvas { max-width: 100%; height: auto; display: block; }</style>
<script type="importmap">
{ "imports": {
  "three": "https://unpkg.com/three@0.170.0/build/three.module.js",
  "three/addons/": "https://unpkg.com/three@0.170.0/examples/jsm/"
} }
</script>
<script type="module">
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';

const name = new URLSearchParams(location.search).get('spec');
let INK = '10,26,63';
let spec, W, H, SS, renderer, scene;
const deg = THREE.MathUtils.degToRad;

function setup() {
  W = spec.w; H = spec.h; SS = spec.ss ?? 2;
  if (spec.shadowInk) { const c = new THREE.Color(spec.shadowInk).convertLinearToSRGB(); INK = [c.r, c.g, c.b].map((v) => Math.round(v * 255)).join(','); }
  renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, preserveDrawingBuffer: true });
  renderer.setPixelRatio(1);
  renderer.setSize(W * SS, H * SS, false);
  renderer.setClearColor(0x000000, 0);
  renderer.toneMapping = THREE.NeutralToneMapping;
  renderer.toneMappingExposure = spec.exposure ?? 1;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  scene = new THREE.Scene();
  scene.environment = studio(spec.env || {});
}

/* Photo studio lighting: a grey room with bright soft boxes, so glossy parts get long clean highlights. */
function studio({ room = 0.5, strip = 1, sheen = 0 }) {
  const s = new THREE.Scene();
  s.add(new THREE.Mesh(new THREE.BoxGeometry(30, 30, 30),
    new THREE.MeshBasicMaterial({ color: new THREE.Color(room, room, room * 1.04), side: THREE.BackSide })));
  const panel = (w, h, p, i) => {
    const m = new THREE.Mesh(new THREE.PlaneGeometry(w, h),
      new THREE.MeshBasicMaterial({ color: new THREE.Color(i, i, i * 1.02), side: THREE.DoubleSide }));
    m.position.set(...p); m.lookAt(0, 0, 0); s.add(m);
  };
  panel(16, 7, [0, 11, 3], 7);
  panel(2.4, 16, [-11, 2, 6], 9 * strip);
  panel(2.4, 16, [11, 2, 6], 6 * strip);
  if (sheen) panel(18, 9, [0, 7, 13], sheen);
  panel(12, 1.4, [0, 5, 12], 5);
  panel(14, 2, [0, -8, 7], 1.6);
  return new THREE.PMREMGenerator(renderer).fromScene(s, 0.012).texture;
}

function camera(target, size, defaults) {
  const c = { ...defaults, ...(spec.camera || {}) };
  const t = target.clone();
  t.y += (c.ty || 0) * size.y; t.x += (c.tx || 0) * size.x;
  const radius = Math.max(size.x, size.y, size.z) * c.dist;
  const cam = new THREE.PerspectiveCamera(c.fov, W / H, radius / 4, radius * 4);
  const a = deg(c.az ?? 0), e = deg(c.el ?? 0);
  cam.position.set(t.x + radius * Math.cos(e) * Math.sin(a), t.y + radius * Math.sin(e), t.z + radius * Math.cos(e) * Math.cos(a));
  cam.lookAt(t);
  cam.updateMatrixWorld(); // projections are wrong without this
  return cam;
}

/* A soft shadow on an invisible floor. */
function ellipseShadow(cx, y, cz, rx, rz, opacity) {
  const S = 1024, cv = document.createElement('canvas'); cv.width = cv.height = S;
  const g = cv.getContext('2d');
  const r = g.createRadialGradient(S / 2, S / 2, 0, S / 2, S / 2, S / 2);
  r.addColorStop(0, `rgba(${INK},1)`); r.addColorStop(0.35, `rgba(${INK},.62)`); r.addColorStop(0.7, `rgba(${INK},.14)`); r.addColorStop(1, `rgba(${INK},0)`);
  g.fillStyle = r; g.fillRect(0, 0, S, S);
  const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace;
  const m = new THREE.Mesh(new THREE.PlaneGeometry(rx * 2, rz * 2),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity, depthWrite: false, toneMapped: false }));
  m.rotation.x = -Math.PI / 2; m.position.set(cx, y, cz); m.renderOrder = -1; scene.add(m);
}

/* A top-down silhouette of the object, blurred and laid flat. Best for flat stacks and blocks. */
function contactShadow(root, floorY, { pad = 0.5, blur = 40, opacity = 0.2, res = 1000 } = {}) {
  const box = new THREE.Box3().setFromObject(root);
  const size = box.getSize(new THREE.Vector3()), c = box.getCenter(new THREE.Vector3());
  const side = Math.max(size.x, size.z) * (1 + pad * 2);
  const cam = new THREE.OrthographicCamera(-side / 2, side / 2, side / 2, -side / 2, 0.001, (size.y + 10) * 4);
  cam.position.set(c.x, box.max.y + 1, c.z); cam.up.set(0, 0, -1); cam.lookAt(c.x, floorY, c.z);
  const rt = new THREE.WebGLRenderTarget(res, res, { samples: 4 });
  scene.overrideMaterial = new THREE.MeshBasicMaterial({ color: 0x000000 });
  const env = scene.environment; scene.environment = null;
  const tm = renderer.toneMapping; renderer.toneMapping = THREE.NoToneMapping;
  renderer.setRenderTarget(rt); renderer.setClearColor(0xffffff, 0); renderer.clear(); renderer.render(scene, cam);
  const px = new Uint8Array(res * res * 4); renderer.readRenderTargetPixels(rt, 0, 0, res, res, px);
  renderer.setRenderTarget(null); renderer.setClearColor(0x000000, 0); renderer.toneMapping = tm;
  scene.overrideMaterial = null; scene.environment = env;
  const raw = document.createElement('canvas'); raw.width = raw.height = res;
  raw.getContext('2d').putImageData(new ImageData(new Uint8ClampedArray(px), res, res), 0, 0);
  const out = document.createElement('canvas'); out.width = out.height = res;
  const g = out.getContext('2d');
  g.filter = `blur(${blur}px)`; g.drawImage(raw, 0, 0); g.filter = 'none';
  g.globalCompositeOperation = 'source-in'; g.fillStyle = `rgb(${INK})`; g.fillRect(0, 0, res, res);
  const tex = new THREE.CanvasTexture(out); tex.flipY = false; tex.colorSpace = THREE.SRGBColorSpace;
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(side, side),
    new THREE.MeshBasicMaterial({ map: tex, transparent: true, opacity, depthWrite: false, toneMapped: false }));
  plane.rotation.x = -Math.PI / 2; plane.position.set(c.x, floorY, c.z); plane.renderOrder = -1; scene.add(plane);
}

function project(cam, v) {
  const p = v.clone().project(cam);
  return { x: +(p.x * 0.5 + 0.5).toFixed(4), y: +(0.5 - p.y * 0.5).toFixed(4) };
}

async function save(cam, meta) {
  renderer.render(scene, cam);
  const out = document.createElement('canvas'); out.width = W; out.height = H;
  const g = out.getContext('2d', { willReadFrequently: true }); g.imageSmoothingQuality = 'high';
  g.drawImage(renderer.domElement, 0, 0, W, H);
  document.body.appendChild(out);
  // Report the content box, and any content cut off by the image edge.
  const d = g.getImageData(0, 0, W, H).data;
  let x0 = W, y0 = H, x1 = 0, y1 = 0;
  const edges = { left: 0, top: 0, right: 0, bottom: 0 };
  for (let y = 0; y < H; y++) for (let x = 0; x < W; x++) {
    const a = d[(y * W + x) * 4 + 3];
    if (a > 24) { x0 = Math.min(x0, x); x1 = Math.max(x1, x); y0 = Math.min(y0, y); y1 = Math.max(y1, y); }
    if (x === 0) edges.left = Math.max(edges.left, a);
    if (y === 0) edges.top = Math.max(edges.top, a);
    if (x === W - 1) edges.right = Math.max(edges.right, a);
    if (y === H - 1) edges.bottom = Math.max(edges.bottom, a);
  }
  const blob = await new Promise((r) => out.toBlob(r, 'image/png'));
  await fetch(`/save/${name}.png`, { method: 'POST', body: blob });
  await fetch(`/save/${name}.json`, { method: 'POST', body: JSON.stringify({ w: W, h: H, edges, bbox: [x0, y0, x1, y1], ...meta }) });
  window.__done = true;
}

const loadImg = (url) => new Promise((res, rej) => { const i = new Image(); i.onload = () => res(i); i.onerror = () => rej(new Error('Could not load ' + url)); i.src = url; });
const rr = (g, x, y, w, h, r) => { g.beginPath(); g.roundRect(x, y, w, h, r); };

function cover(g, img, W_, H_) {
  const k = Math.max(W_ / img.width, H_ / img.height);
  g.imageSmoothingQuality = 'high';
  g.drawImage(img, (W_ - img.width * k) / 2, (H_ - img.height * k) / 2, img.width * k, img.height * k);
}

const monoFont = () => `${spec.mono ? `"${spec.mono}", ` : ''}Consolas, Menlo, "DejaVu Sans Mono", monospace`;

function terminalScreen(g, CW, CH, t) {
  g.fillStyle = t.bg || '#0b1020'; g.fillRect(0, 0, CW, CH);
  if (t.dots !== false) ['#ff5f57', '#febc2e', '#28c840'].forEach((c, i) => { g.fillStyle = c; g.beginPath(); g.arc(50 + i * 44, 46, 13, 0, 7); g.fill(); });
  const size = t.size || Math.round(CW / 34);
  g.font = `500 ${size}px ${monoFont()}`; g.textBaseline = 'alphabetic'; g.textRendering = 'optimizeSpeed'; // no ligatures: <| must stay <|
  t.lines.forEach((l, i) => { g.fillStyle = l.c || '#e6ebf5'; g.fillText(l.t, t.x ?? 50, (t.y ?? 130) + i * size * 1.5); });
}

/* ---------------------------------------------------------------- plates */
const PW = 1.6, PD = 1.0, PR = 0.07;

function plateShape() {
  const s = new THREE.Shape(), x = -PW / 2, y = -PD / 2, r = PR;
  s.moveTo(x + r, y); s.lineTo(x + PW - r, y); s.quadraticCurveTo(x + PW, y, x + PW, y + r);
  s.lineTo(x + PW, y + PD - r); s.quadraticCurveTo(x + PW, y + PD, x + PW - r, y + PD);
  s.lineTo(x + r, y + PD); s.quadraticCurveTo(x, y + PD, x, y + PD - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  return s;
}

async function drawMarks(marks) {
  const CW = 1600, CH = 1000;
  const cv = document.createElement('canvas'); cv.width = CW * 2; cv.height = CH * 2; // drawn at 2x, so text stays sharp at print size
  const g = cv.getContext('2d'); g.scale(2, 2); g.lineCap = 'round'; g.lineJoin = 'round';
  const font = spec.font || 'sans-serif';
  for (const m of marks || []) {
    g.save();
    if (m.kind === 'image') {
      rr(g, 0, 0, CW, CH, 70); g.clip(); cover(g, await loadImg(m.src), CW, CH);
    } else if (m.kind === 'brackets') {
      const l = m.len || 96; g.strokeStyle = m.color; g.lineWidth = m.width || 15; g.beginPath();
      [[m.x, m.y, 1, 1], [m.x + m.w, m.y, -1, 1], [m.x + m.w, m.y + m.h, -1, -1], [m.x, m.y + m.h, 1, -1]].forEach(([a, b, dx, dy]) => {
        g.moveTo(a + dx * l, b); g.lineTo(a, b); g.lineTo(a, b + dy * l);
      });
      g.stroke(); g.globalAlpha = 0.1; g.fillStyle = m.color; g.fillRect(m.x, m.y, m.w, m.h);
    } else if (m.kind === 'dash') {
      g.strokeStyle = m.color; g.lineWidth = m.width || 12; g.setLineDash([46, 30]);
      rr(g, m.x, m.y, m.w, m.h, 26); g.stroke(); g.setLineDash([]); g.globalAlpha = 0.08; g.fillStyle = m.color; g.fill();
    } else if (m.kind === 'fill') {
      g.fillStyle = m.color; g.globalAlpha = m.alpha ?? 1; rr(g, m.x, m.y, m.w, m.h, m.r ?? 20); g.fill();
    } else if (m.kind === 'check') {
      g.strokeStyle = m.color; g.lineWidth = 16; g.beginPath(); g.arc(m.x, m.y, m.r, 0, 7); g.stroke();
      const k = m.r / 170; g.lineWidth = 20; g.beginPath();
      g.moveTo(m.x - 78 * k, m.y + 4 * k); g.lineTo(m.x - 16 * k, m.y + 64 * k); g.lineTo(m.x + 88 * k, m.y - 62 * k); g.stroke();
    } else if (m.kind === 'text' || m.kind === 'code') {
      const size = m.size || 130;
      g.fillStyle = m.color || '#0a1a3f'; g.textBaseline = 'alphabetic';
      g.font = m.kind === 'code' ? `500 ${size}px ${monoFont()}` : `600 ${size}px "${font}", sans-serif`;
      if (m.kind === 'code') g.textRendering = 'optimizeSpeed'; // no ligatures: <| must stay <|
      m.lines.forEach((t, i) => g.fillText(t, m.x, m.y + i * (m.leading || size * 1.27)));
    }
    g.restore();
  }
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16;
  return t;
}

async function plates() {
  const stack = new THREE.Group(); scene.add(stack);
  const gap = spec.gap ?? 0.5, T = spec.thickness ?? 0.012;
  const geo = new THREE.ExtrudeGeometry(plateShape(), { depth: T, bevelEnabled: false, curveSegments: 12 }); geo.rotateX(-Math.PI / 2);
  const flat = new THREE.ShapeGeometry(plateShape(), 12); flat.rotateX(-Math.PI / 2);
  const pos = flat.attributes.position, uv = flat.attributes.uv;
  for (let i = 0; i < pos.count; i++) uv.setXY(i, (pos.getX(i) + PW / 2) / PW, 1 - (pos.getZ(i) + PD / 2) / PD);
  const rimCurve = new THREE.CatmullRomCurve3(plateShape().getPoints(10).map((p) => new THREE.Vector3(p.x, 0, -p.y)), true, 'catmullrom', 0.02);
  const corners = {};
  for (const [i, l] of spec.layers.entries()) {
    const y = (l.level ?? i) * gap, k = l.scale ?? 1, lx = l.x ?? 0, lz = l.z ?? 0;
    const layer = new THREE.Group(); layer.position.set(lx, y, lz); layer.scale.setScalar(k); stack.add(layer);
    const body = new THREE.Mesh(geo, new THREE.MeshPhysicalMaterial({
      color: l.tint ?? 0xe8effc, transparent: true, opacity: l.opaque ? 1 : (l.glass ?? spec.glass ?? 0.42),
      roughness: 0.16, clearcoat: 1, clearcoatRoughness: 0.1, envMapIntensity: 0.9, depthWrite: false }));
    body.renderOrder = i * 3 + 1; layer.add(body);
    const art = new THREE.Mesh(flat, new THREE.MeshBasicMaterial({ map: await drawMarks(l.marks), transparent: true, toneMapped: false, depthWrite: false }));
    art.position.y = T + 0.0015; art.renderOrder = i * 3 + 2; layer.add(art);
    const rim = new THREE.Mesh(new THREE.TubeGeometry(rimCurve, 220, spec.rim ?? 0.0055, 8, true), new THREE.MeshBasicMaterial({ color: l.rim, toneMapped: false }));
    rim.position.y = T + 0.002; rim.renderOrder = i * 3 + 3; layer.add(rim);
    corners[l.id] = new THREE.Vector3(lx + (PW / 2 - 0.02) * k, y + T * k, lz + (PD / 2 - 0.02) * k);
    corners[`${l.id}_left`] = new THREE.Vector3(lx - (PW / 2 - 0.02) * k, y + T * k, lz + (PD / 2 - 0.02) * k);
    corners[`${l.id}_front`] = new THREE.Vector3(lx, y + T * k, lz + PD / 2 * k);
  }
  const box = new THREE.Box3().setFromObject(stack);
  const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
  if ((spec.shadow?.opacity ?? 0.2) > 0) contactShadow(stack, box.min.y - 0.2, spec.shadow);
  const cam = camera(c, s, { az: -32, el: 25, fov: 18, dist: 6.2, ty: -0.06 });
  const spots = {};
  for (const [k, v] of Object.entries(corners)) spots[k] = project(cam, v);
  await save(cam, { spots });
}

/* ---------------------------------------------------------------- blocks */
function labelTexture(text, color) {
  const cv = document.createElement('canvas'); cv.width = 1024; cv.height = 1024;
  const g = cv.getContext('2d');
  g.fillStyle = color; g.textAlign = 'center'; g.textBaseline = 'middle';
  let size = 170; g.font = `600 ${size}px "${spec.font || 'sans-serif'}", sans-serif`;
  while (g.measureText(text).width > 860 && size > 60) { size -= 10; g.font = `600 ${size}px "${spec.font || 'sans-serif'}", sans-serif`; }
  g.fillText(text, 512, 512);
  const t = new THREE.CanvasTexture(cv); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 16;
  return t;
}

async function blocks() {
  const root = new THREE.Group(); scene.add(root);
  const tops = {};
  for (const n of spec.nodes) {
    const y0 = n.y || 0, h = n.h || 0.2;
    const r = Math.min(0.04, h * 0.3);
    const m = new THREE.Mesh(new RoundedBoxGeometry(n.w, h, n.d, 5, r),
      new THREE.MeshPhysicalMaterial({ color: n.color, roughness: 0.42, metalness: 0, clearcoat: 0.5, clearcoatRoughness: 0.36, envMapIntensity: 0.6 }));
    m.position.set(n.x, y0 + h / 2, n.z); root.add(m);
    tops[n.id] = new THREE.Vector3(n.x, y0 + h, n.z);
    if (n.label) {
      const size = Math.min(n.w, n.d) * 0.92;
      const p = new THREE.Mesh(new THREE.PlaneGeometry(size, size),
        new THREE.MeshBasicMaterial({ map: labelTexture(n.label, n.labelColor || '#ffffff'), transparent: true, toneMapped: false, depthWrite: false }));
      p.rotation.x = -Math.PI / 2; p.position.set(n.x, y0 + h + 0.002, n.z); root.add(p);
    }
  }
  const byId = Object.fromEntries(spec.nodes.map((n) => [n.id, n]));
  for (const e of spec.edges || []) {
    const a = byId[e.from], b = byId[e.to], y = 0.05;
    const pts = a.x === b.x || a.z === b.z
      ? [new THREE.Vector3(a.x, y, a.z), new THREE.Vector3(b.x, y, b.z)]
      : [new THREE.Vector3(a.x, y, a.z), new THREE.Vector3(b.x, y, a.z), new THREE.Vector3(b.x, y, b.z)];
    const path = new THREE.CurvePath();
    for (let i = 0; i < pts.length - 1; i++) path.add(new THREE.LineCurve3(pts[i], pts[i + 1]));
    const tube = new THREE.Mesh(new THREE.TubeGeometry(path, 64, spec.edgeWidth ?? 0.012, 8, false), new THREE.MeshBasicMaterial({ color: e.color || '#1a56e0', toneMapped: false }));
    tube.renderOrder = -0.5; root.add(tube);
  }
  const box = new THREE.Box3().setFromObject(root);
  const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
  contactShadow(root, box.min.y - 0.02, { pad: 0.2, blur: 34, opacity: 0.22, ...(spec.shadow || {}) });
  const cam = camera(c, s, { az: -35, el: 32, fov: 18, dist: 2.6 });
  const spots = {};
  for (const [k, v] of Object.entries(tops)) spots[k] = project(cam, v);
  await save(cam, { spots });
}

/* ---------------------------------------------------------------- device */
function slab(w, h, depth, r, material) {
  const s = new THREE.Shape(), x = -w / 2, y = -h / 2;
  s.moveTo(x + r, y); s.lineTo(x + w - r, y); s.quadraticCurveTo(x + w, y, x + w, y + r);
  s.lineTo(x + w, y + h - r); s.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
  s.lineTo(x + r, y + h); s.quadraticCurveTo(x, y + h, x, y + h - r);
  s.lineTo(x, y + r); s.quadraticCurveTo(x, y, x + r, y);
  const bevel = depth * 0.22;
  const g = new THREE.ExtrudeGeometry(s, { depth: depth - bevel * 2, bevelEnabled: true, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 5, curveSegments: 24 });
  g.translate(0, 0, -depth + bevel);
  return new THREE.Mesh(g, material);
}

async function device() {
  const form = spec.form || 'window';
  const SW = spec.screenW ?? (form === 'phone' ? 0.46 : 1.6), SH = spec.screenH ?? 1.0;
  const bez = (spec.bezel ?? (form === 'phone' ? 0.018 : 0.03));
  const radius = spec.radius ?? (form === 'phone' ? 0.07 : 0.035);
  const depth = form === 'phone' ? 0.045 : 0.035;
  const pivot = new THREE.Group(); scene.add(pivot);
  const metal = (color) => new THREE.MeshPhysicalMaterial({ color, metalness: 0.95, roughness: 0.32, clearcoat: 0.6, clearcoatRoughness: 0.2 });
  const bodyMat = metal(spec.body || '#20283a');
  // One screen on a body. `extras` adds more in the same scene: a source file behind its result, say.
  async function addScreen(cfg, w, h, body, offset = [0, 0, 0]) {
    const group = new THREE.Group(); group.position.set(...offset); pivot.add(group);
    group.add(slab(w + bez * 2, h + bez * 2, depth, radius + bez * 0.6, body));
    const CW = cfg.px || 1400, CH = Math.round(CW * h / w);
    const cv = document.createElement('canvas'); cv.width = CW; cv.height = CH;
    const g = cv.getContext('2d');
    rr(g, 0, 0, CW, CH, CW * (radius / w)); g.clip();
    if (cfg.image) cover(g, await loadImg(cfg.image), CW, CH);
    else if (cfg.terminal) terminalScreen(g, CW, CH, cfg.terminal);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 16;
    const mesh = new THREE.Mesh(new THREE.PlaneGeometry(w, h), new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false }));
    mesh.position.z = 0.002; group.add(mesh);
    return mesh;
  }
  const screen = await addScreen(spec.screen || {}, SW, SH, bodyMat);
  const onExtras = [];
  for (const x of spec.extras || []) {
    const w = x.screenW ?? SW, h = x.screenH ?? SH;
    const m = await addScreen(x.screen, w, h, metal(x.body || spec.body || '#20283a'), x.offset);
    if (x.spots) onExtras.push([m, w, h, x.spots]);
  }
  if (form === 'laptop') {
    const base = slab(SW + bez * 2, SH * 0.72, 0.03, 0.03, bodyMat);
    base.rotation.x = -Math.PI / 2 + deg(4);
    base.position.set(0, -SH / 2 - bez - 0.005, SH * 0.36);
    pivot.add(base);
  }
  const [rx, ry, rz] = spec.rotate || [-6, -24, -3];
  pivot.rotation.set(deg(rx), deg(ry), deg(rz));
  pivot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(pivot);
  const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
  const sh = { rx: 0.62, rz: 0.4, lift: 0.04, opacity: 0.2, ...(spec.shadow || {}) };
  ellipseShadow(c.x, box.min.y - s.y * sh.lift, c.z, s.x * sh.rx, s.x * sh.rz, sh.opacity);
  const cam = camera(c, s, { az: 0, el: 6, fov: 18, dist: 3.4 });
  const spots = {};
  for (const [k, [u, v]] of Object.entries(spec.spots || {})) {
    spots[k] = project(cam, screen.localToWorld(new THREE.Vector3((u - 0.5) * SW, (0.5 - v) * SH, 0)));
  }
  for (const [m, w, h, list] of onExtras) for (const [k, [u, v]] of Object.entries(list)) {
    spots[k] = project(cam, m.localToWorld(new THREE.Vector3((u - 0.5) * w, (0.5 - v) * h, 0)));
  }
  await save(cam, { spots });
}

/* ---------------------------------------------------------------- glb */
function lensMaterial() {
  const m = new THREE.MeshBasicMaterial({ color: spec.glassColor || '#b9cdf2', transparent: true, depthWrite: false, side: THREE.DoubleSide, toneMapped: false });
  const f = (spec.bandF ?? 0.16).toFixed(3), ph = (spec.bandP ?? 0.6).toFixed(3), base = (spec.lens ?? 0.05).toFixed(3), band = (spec.band ?? 0.3).toFixed(3);
  m.onBeforeCompile = (sh) => {
    sh.vertexShader = sh.vertexShader.replace('#include <common>', `#include <common>
varying vec3 vP;`).replace('#include <project_vertex>', `#include <project_vertex>
vP = mvPosition.xyz;`);
    sh.fragmentShader = sh.fragmentShader.replace('#include <common>', `#include <common>
varying vec3 vP;`).replace('#include <opaque_fragment>', `#include <opaque_fragment>
float d = dot(vP.xy, normalize(vec2(0.62, 1.0))) * ${f} + ${ph};
float b = pow(0.5 + 0.5 * sin(d), 5.0);
gl_FragColor.a = ${base} + ${band} * b;`);
  };
  return m;
}

async function glb() {
  const gltf = await new Promise((res, rej) => new GLTFLoader().load(spec.src, res, undefined, () => rej(new Error('Could not load ' + spec.src))));
  const root = gltf.scene, drop = [], names = new Set();
  const has = (list, n) => (list || []).some((x) => n.includes(x));
  let screenMesh = null;
  root.traverse((o) => {
    if (!o.isMesh) return;
    const n = o.material.name || ''; names.add(n);
    if (has(spec.drop, n)) { drop.push(o); return; }
    if (spec.screen && n.includes(spec.screen.material)) screenMesh = o;
    if (has(spec.glass, n)) { o.material = lensMaterial(); return; }
    const key = Object.keys(spec.materials || {}).find((k) => n.includes(k));
    if (key) o.material = new THREE.MeshPhysicalMaterial(spec.materials[key]);
  });
  drop.forEach((o) => o.parent.remove(o));
  const pivot = new THREE.Group(); scene.add(pivot); pivot.add(root);
  if (spec.screen && screenMesh) {
    const gb = new THREE.Box3().setFromObject(screenMesh), rootBox = new THREE.Box3().setFromObject(root);
    const gs = gb.getSize(new THREE.Vector3()), gc = gb.getCenter(new THREE.Vector3());
    const CW = 1100, CH = Math.round(CW * gs.y / gs.x);
    const cv = document.createElement('canvas'); cv.width = CW; cv.height = CH;
    const g = cv.getContext('2d'); rr(g, 0, 0, CW, CH, CW * (spec.screen.radius ?? 0.14)); g.clip();
    cover(g, await loadImg(spec.screen.image), CW, CH);
    const tex = new THREE.CanvasTexture(cv); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 16;
    const p = new THREE.Mesh(new THREE.PlaneGeometry(gs.x, gs.y), new THREE.MeshBasicMaterial({ map: tex, transparent: true, toneMapped: false }));
    p.position.set(gc.x, gc.y, rootBox.max.z + (spec.screen.offset ?? rootBox.getSize(new THREE.Vector3()).z * 0.003));
    root.add(p);
  }
  const [rx, ry, rz] = spec.rotate || [0, 0, 0];
  pivot.rotation.set(deg(rx), deg(ry), deg(rz));
  pivot.updateMatrixWorld(true);
  const box = new THREE.Box3().setFromObject(pivot);
  const c = box.getCenter(new THREE.Vector3()), s = box.getSize(new THREE.Vector3());
  const sh = { rx: 0.56, rz: 0.3, lift: 0.3, opacity: 0.12, ...(spec.shadow || {}) };
  ellipseShadow(c.x, box.min.y - s.y * sh.lift, box.max.z - s.z * 0.28, s.x * sh.rx, s.z * sh.rz, sh.opacity);
  const cam = camera(c, s, { az: 24, el: 9, fov: 24, dist: 2 });
  const spots = {};
  for (const [k, v] of Object.entries(spec.hotspots || {})) spots[k] = project(cam, root.localToWorld(new THREE.Vector3(...v)));
  await save(cam, { spots, materials: [...names] });
}

(async () => {
  spec = await (await fetch(`specs/${name}.json`)).json();
  setup();
  if (spec.font) await document.fonts.load(`600 100px "${spec.font}"`);
  if (spec.mono) await document.fonts.load(`500 40px "${spec.mono}"`);
  await ({ plates, blocks, device, glb })[spec.type]();
})().catch((e) => { window.__failed = String((e && e.stack) || e); console.error(e); });
</script>
```

<!-- file: page.html -->
```html
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>{{TITLE}}</title>
<link rel="stylesheet" href="fonts/fonts.css" />
<style>
  /* Starter for skeleton A. Change the tokens and the copy, then move the blocks to suit the project. */
  :root {
    --font: Figtree;
    --ink: #0a1a3f; --text: #3d4c6b; --muted: #6a7893; --line: #dce4f2; --accent: #1a56e0;
    --ok: #2bd48f; --bad: #ff5a5f; --warn: #f5b83d;
  }
  @page { size: {{PAGE_W}}mm {{PAGE_H}}mm; margin: 0; }
  * { box-sizing: border-box; margin: 0; padding: 0; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  html, body { width: {{PAGE_W}}mm; height: {{SHEET_H}}mm; background: #fff; }
  code, pre { font-variant-ligatures: none; }
  body { font-family: var(--font), sans-serif; color: var(--text); font-size: 8.2pt; line-height: 11.4pt; font-kerning: normal; }
  .sheet { position: relative; width: {{PAGE_W}}mm; height: {{SHEET_H}}mm; overflow: hidden; background: #fff; }
  .a { position: absolute; }
  img { display: block; }
  b { font-weight: 600; color: var(--ink); }

  .brand { left: 13mm; top: 9.2mm; display: flex; align-items: center; gap: 1.7mm; }
  .brand img { height: 6.2mm; width: auto; }
  .brand span { font-size: 14.5pt; line-height: 1; font-weight: 700; color: var(--ink); letter-spacing: -.012em; }
  .kicker { right: 13mm; top: 10.6mm; font-size: 8.6pt; line-height: 1; font-weight: 500; color: var(--ink); }
  h1 { left: 13mm; top: 18.4mm; width: 106mm; font-size: 34.5pt; line-height: 36pt; font-weight: 600; color: var(--ink); letter-spacing: -.03em; }
  .lede { left: 124mm; width: 73mm; top: 19.6mm; font-size: 9.2pt; line-height: 12.8pt; }
  .call b { display: block; font-size: 7.8pt; line-height: 10pt; }
  .call i { display: block; font-style: normal; font-size: 7.5pt; line-height: 9.4pt; color: var(--muted); }
  .note { font-size: 6.4pt; line-height: 8pt; color: var(--muted); }

  h2 { font-size: 15pt; line-height: 17.6pt; font-weight: 600; color: var(--ink); letter-spacing: -.016em; }
  .mode { font-size: 21pt; line-height: 22pt; font-weight: 600; color: var(--ink); letter-spacing: -.024em; }
  .sub { font-size: 9pt; line-height: 11.6pt; font-weight: 500; color: var(--accent); }
  .divider { width: .2mm; background: var(--line); }
  .rule { left: 13mm; right: 13mm; height: .2mm; background: var(--line); }

  .steps { list-style: none; counter-reset: s; }
  .steps li { position: relative; padding-left: 4.3mm; font-size: 7.75pt; line-height: 10pt; margin-bottom: 1.5mm; counter-increment: s; }
  .steps li::before { content: counter(s); position: absolute; left: 0; top: 0; font-weight: 600; color: var(--accent); }
  .lab b { display: block; font-size: 7.7pt; line-height: 9.4pt; }
  .lab i { display: block; font-style: normal; font-size: 7.5pt; line-height: 8.8pt; color: var(--muted); }
  .tag { display: inline-flex; align-items: center; gap: 1mm; background: var(--ink); color: #fff; border-radius: .9mm; padding: .55mm 1.25mm; font-size: 6.7pt; line-height: 8pt; font-weight: 500; }
  .tag::before { content: ''; width: 1.25mm; height: 1.25mm; border-radius: 50%; background: var(--c); }

  .nums { left: 13mm; right: 13mm; display: grid; grid-template-columns: repeat(4, 1fr); column-gap: 6mm; }
  .num em { display: block; font-style: normal; font-size: 30pt; line-height: 30pt; font-weight: 300; color: var(--accent); letter-spacing: -.035em; }
  .num em u { text-decoration: none; line-height: 0; font-size: 11pt; font-weight: 500; letter-spacing: -.005em; margin-left: .9mm; color: var(--ink); }
  .num p { margin-top: .9mm; font-size: 7.5pt; line-height: 9.4pt; }

  .spec { left: 13mm; right: 37mm; display: grid; grid-template-columns: repeat(4, 1fr); column-gap: 4.6mm; row-gap: 1.8mm; }
  .spec div { font-size: 7.5pt; line-height: 9.2pt; }
  .spec b { display: block; font-size: 7.5pt; line-height: 9.2pt; }

  .qr { right: 13mm; width: 18.4mm; text-decoration: none; color: var(--ink); display: block; }
  .qr .box { position: relative; width: 18.4mm; height: 18.4mm; padding: 1.5mm; }
  .qr svg { width: 100%; height: 100%; display: block; }
  .qr .c { position: absolute; width: 2.6mm; height: 2.6mm; border: 0 solid var(--accent); }
  .qr .tl { left: 0; top: 0; border-width: .3mm 0 0 .3mm; } .qr .tr { right: 0; top: 0; border-width: .3mm .3mm 0 0; }
  .qr .bl { left: 0; bottom: 0; border-width: 0 0 .3mm .3mm; } .qr .br { right: 0; bottom: 0; border-width: 0 .3mm .3mm 0; }
  .qr span.t { display: block; text-align: center; margin-top: .5mm; font-size: 6.9pt; line-height: 8.4pt; font-weight: 600; }
  .foot { left: 13mm; right: 13mm; bottom: 11mm; display: flex; justify-content: space-between; font-size: 6.2pt; line-height: 8pt; color: var(--muted); }
</style>
</head>
<body>
<div class="sheet">
  {{IMAGES}}
  <svg class="a" style="left:0; top:0; width:{{PAGE_W}}mm; height:{{PAGE_H}}mm;" viewBox="0 0 {{PAGE_W}} {{PAGE_H}}" fill="none" aria-hidden="true">{{LEADERS}}{{DIAGRAM}}</svg>

  <div class="a brand"><span>Sample</span></div>
  <div class="a kicker">What it is, in five words</div>
  <h1 class="a">A headline that says something.</h1>
  <p class="a lede">One or two plain sentences: what the project does, for whom, and the idea that makes it different.</p>

  <div class="a mode" style="left:13mm; top:128mm;">How it works</div>
  <div class="a sub" style="left:13mm; top:136mm;">The central idea, in one line.</div>
  <div class="a note" style="left:13mm; top:calc({{PAGE_H}}mm - 82mm);">Illustration of how the parts fit together</div>

  <div class="a rule" style="top:calc({{PAGE_H}}mm - 75mm);"></div>
  <div class="a nums" style="top:calc({{PAGE_H}}mm - 71mm);">
    <div class="num"><em>120<u>tests</u></em><p>Counted from the repo</p></div>
    <div class="num"><em>3<u>platforms</u></em><p>Covered in CI</p></div>
    <div class="num"><em>40<u>ms</u></em><p>Median, from the repo's own benchmark</p></div>
    <div class="num"><em>MIT</em><p>License</p></div>
  </div>

  <div class="a rule" style="top:calc({{PAGE_H}}mm - 46mm);"></div>
  <div class="a spec" style="top:calc({{PAGE_H}}mm - 42mm);">
    <div><b>Input</b>What goes in</div>
    <div><b>Output</b>What comes out</div>
    <div><b>Install</b>The real command</div>
    <div><b>Status</b>What works, and what doesn't yet</div>
  </div>
  <a class="a qr" href="{{URL}}" style="top:calc({{PAGE_H}}mm - 43mm);">
    <div class="box"><i class="c tl"></i><i class="c tr"></i><i class="c bl"></i><i class="c br"></i>{{QR}}</div>
    <span class="t">See the repo</span>
  </a>
  <div class="a foot"><span>Sample project</span><span>Generated from the repository. Figures come from the repo's own files.</span></div>
</div>
</body>
</html>
```

## 8. Starter files for a first test

These make a complete page with the starter `page.html`. Delete them once you have real content.

<!-- file: diagram.py -->
```python
"""A vector diagram in mm. Edit the content at the bottom, then run: python diagram.py"""
import html
import math
import pathlib
import textwrap

ACC, INK, TEXT, MUTED, LINE = "#1a56e0", "#0a1a3f", "#3d4c6b", "#6a7893", "#cfd6e4"
MONO = "'IBM Plex Mono', monospace"
out = []


def text(x, y, s, size=2.55, color=TEXT, weight=400, mono=False):
    """Sizes are in mm: 2.05 is the 5.8 pt minimum. mono uses an inline style, because CSS on svg text beats an attribute."""
    style = f' style="font-family:{MONO}"' if mono else ""
    out.append(f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{color}" font-weight="{weight}"{style}>{html.escape(s)}</text>')


def box(x, y, w, h, fill="#fff", stroke=LINE, sw=0.22):
    out.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{w}" height="{h}" rx="1.1" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')


def line(pts, color=LINE, sw=0.28, arrow=True):
    d = "M" + " L".join(f"{x:.2f},{y:.2f}" for x, y in pts)
    out.append(f'<path d="{d}" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round"/>')
    if arrow:  # the head follows the last segment, in any direction
        (x0, y0), (x, y) = pts[-2], pts[-1]
        n = math.hypot(x - x0, y - y0) or 1
        ux, uy = (x - x0) / n, (y - y0) / n
        out.append(f'<path d="M{x - 1.3 * ux + .75 * uy:.2f},{y - 1.3 * uy - .75 * ux:.2f} L{x:.2f},{y:.2f} L{x - 1.3 * ux - .75 * uy:.2f},{y - 1.3 * uy + .75 * ux:.2f}" stroke="{color}" stroke-width="{sw}" stroke-linejoin="round" stroke-linecap="round"/>')


def step(x, y, w, h, name, note, chars=17, strong=False):
    box(x, y, w, h, "#f4f7fe" if strong else "#fff", ACC if strong else LINE, 0.3 if strong else 0.22)
    text(x + 1.8, y + 4.4, name, 2.7, INK, 600)
    for i, l in enumerate(textwrap.wrap(note, chars)):
        text(x + 1.8, y + 8.3 + i * 3, l, 2.15)


# Sample content: replace with the project's real flow.
Y, W, H = 146, 30, 22
names = [("Read", "Loads the input from a real source."), ("Build", "Does the project's main work."), ("Check", "Confirms that it worked.")]
for i, (name, note) in enumerate(names):
    x = 13 + i * 36
    step(x, Y, W, H, name, note, 22, strong=i == 1)
    if i < 2:
        line([(x + W, Y + H / 2), (x + 36, Y + H / 2)], ACC)

pathlib.Path("diagram.svgfrag").write_text("".join(out), encoding="utf-8")
```

<!-- file: specs/hero.json -->
```json
{
  "type": "device", "form": "window", "w": 2000, "h": 1300, "ss": 2, "font": "Figtree",
  "screenW": 1.6, "screenH": 1.0, "rotate": [-6, -24, -3],
  "camera": { "el": 6, "fov": 18, "dist": 3.4 },
  "screen": { "terminal": { "lines": [ { "t": "$ sample build ./src", "c": "#ffffff" }, { "t": "reading 12 files", "c": "#9fb0d0" }, { "t": "built in 40 ms", "c": "#2bd48f" } ] } },
  "spots": { "output": [0.2, 0.28] }
}
```

<!-- file: specs/stack.json -->
```json
{
  "type": "plates", "w": 1500, "h": 1650, "ss": 2, "font": "Figtree",
  "shadow": { "opacity": 0.2 },
  "layers": [
    { "id": "input", "rim": "#f0b429", "marks": [ { "kind": "fill", "x": 540, "y": 350, "w": 500, "h": 330, "color": "#f0b429", "alpha": 0.2 } ] },
    { "id": "parse", "rim": "#1a56e0", "marks": [ { "kind": "brackets", "x": 540, "y": 350, "w": 500, "h": 330, "color": "#1a56e0" } ] },
    { "id": "check", "rim": "#12a06a", "marks": [ { "kind": "check", "x": 790, "y": 515, "r": 170, "color": "#12a06a" } ] },
    { "id": "output", "rim": "#0a1a3f", "marks": [ { "kind": "text", "x": 120, "y": 450, "size": 134, "lines": ["Short real text", "on the top plate."] } ] }
  ]
}
```

<!-- file: specs/system.json -->
```json
{
  "type": "blocks", "w": 1800, "h": 1100, "ss": 2, "font": "Figtree",
  "nodes": [
    { "id": "api", "x": -1.3, "z": 0, "w": 0.9, "d": 0.9, "h": 0.22, "color": "#1a56e0", "label": "API", "labelColor": "#ffffff" },
    { "id": "queue", "x": 0, "z": 0, "w": 0.9, "d": 0.9, "h": 0.12, "color": "#eef2fa", "label": "Queue", "labelColor": "#0a1a3f" },
    { "id": "store", "x": 1.3, "z": 0, "w": 0.9, "d": 0.9, "h": 0.34, "color": "#0a1a3f", "label": "Store", "labelColor": "#ffffff" }
  ],
  "edges": [ { "from": "api", "to": "queue" }, { "from": "queue", "to": "store" } ]
}
```

<!-- file: layout.json -->
```json
{
  "title": "Sample: a starter page",
  "author": "",
  "subject": "One-page brief",
  "pdf": "out/sample-one-pager.pdf",
  "size": "A4",
  "url": "https://example.com",
  "banned": ["internal-name"],
  "images": {
    "hero": { "x": 20, "y": 34, "w": 145, "alt": "A terminal window, in 3D" },
    "stack": { "x": 128, "y": 126, "w": 62, "alt": "An exploded stack of four layers" }
  },
  "leaders": [
    { "image": "hero", "spot": "output", "to": [175, 62], "color": "#1a56e0", "toDot": true }
  ]
}
```

<!-- file: facts.md -->
```markdown
| Fact | Value | Source | Status |
|---|---|---|---|
| Tests | 120 | tests/ | verified in code |
| Speed | 40 ms | docs/bench.md:12 | measured, by the repo |
```
