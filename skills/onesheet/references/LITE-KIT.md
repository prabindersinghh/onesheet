# onesheet lite kit

The build for places with no browser, such as claude.ai chat and the Claude desktop chat. It needs Python with reportlab and pillow, nothing else. The page is vector from end to end, and the 3D hero is drawn with exact orthographic projection, so leader lines land precisely and the text on plates stays sharp at any zoom.

Everything in SKILL.md still applies: the fact ledger, the copy budget, the rules, the score and the critique. Only Step 6, the build, changes.

## 1. Set up

Work in a folder outside the repo. Check the tools once:

```bash
python -c "import reportlab, PIL; print('ok')"
```

If either is missing, try `pip install reportlab pillow`. For previews you also need one of pypdfium2, PyMuPDF or `pdftoppm`. If none is present, try `pip install pypdfium2`. If nothing installs, build anyway and tell the user you couldn't look at the page.

The skill's fonts are bundled: IBM Plex Sans in weights 300, 400, 600 and 700, and IBM Plex Mono in 400 and 500. Vary colour between projects instead of the family.

## 2. Write page.py

A page is one Python script. All positions are in mm from the top left. Use the 12-column grid from SKILL.md Step 5.

```python
import sys
sys.path.insert(0, "SKILL_DIR/scripts")   # this skill's folder
from sheet import Page

INK, ACC = "#0a1a3f", "#1a56e0"
p = Page("out/name-one-pager.pdf", size="A4", accent=ACC, ink=INK, ledger="facts.md",
         title="Name: what it does", banned=["internal-name"])

p.text(13, 18, 106, "A headline that says something.", size=34, weight=600, color=INK, leading=36)
p.text(124, 20, 73, "One or two plain sentences. **Bold** and `code` work inline.", size=9.2, leading=12.8)

v = p.view(cx=72, cy=96, scale=40, az=-30, el=26)      # where the scene sits, mm per unit, camera
spots = v.plates([...], gap=0.5, thickness=0.03)        # returns spot positions in mm
y = p.leader(spots["out"], (130, None))                  # a level line; returns its y
p.label(131.5, y - 1.7, "Timed text comes out", "In the language spoken", w=60)
p.text(13, 150, 120, "Illustration, not a real run.", size=6.4, color="#6a7893")

p.rule(13, 160, 184)
for i, (name, note) in enumerate(steps):
    p.step(13 + i * 31.3, 172, 27, 20, name, note, strong=i == 2)
p.line([(40, 182), (44.3, 182)], ACC, 0.28, arrow=True)

p.code(13, 250, 110, ["$ pip install tool", [("$ ", "#9fb0d0"), ("tool run", "#ffffff")]])
p.qr(178.6, 250, 18.4, "https://github.com/owner/repo")
p.save()
```

Run it with `python page.py`. `save()` writes the PDF, runs the checks, and writes `page_small.jpg`, `z_top.png` and `z_bottom.png` beside the PDF, so build into `out/` and copy the finished PDF to where the user can download it. For a 400 dpi crop: `python SKILL_DIR/scripts/sheet.py out/name-one-pager.pdf x y w h`.

## 3. The calls

| Call | What it draws |
|---|---|
| `text(x, y, w, s, size, weight, color, leading, mono, kind, align, parent)` | Wrapped text with its top at y. Returns its bottom. `kind="diagram"` allows 5.8 pt. `parent=box` lets it sit on that box. |
| `label(x, y, title, sub, w, align)` | A bold line and a muted line, for leaders |
| `rect(x, y, w, h, fill, stroke, sw, r)` | A box. A filled box blocks text unless the text names it as `parent`. |
| `rule(x, y, w)` | A 0.2 mm hairline. Text crossing it fails. |
| `line(points, color, sw, arrow, dash)` | A path. The arrowhead follows the last segment. |
| `step(x, y, w, h, name, note, strong, mono_note)` | A diagram box. Its text must stay inside. |
| `code(x, y, w, lines)` | A dark command block. A line can be a list of `(text, colour)` pieces. |
| `image(x, y, w, path)` | A raster image, checked for 300 dpi as printed |
| `qr(x, y, size, url)` | A vector QR code that links |
| `leader(spot, (x, y or None), color, end_dot)` | A leader line with a dot on the hero |
| `view(cx, cy, scale, az, el)` | A camera for the 3D scenes below |

## 4. Scenes

**`v.plates(layers, size, gap, thickness, shadow)`** is the exploded stack. Layers go bottom to top, with the fields `id`, `rim`, `tint`, `glass`, `opaque`, `level`, `x`, `z`, `scale` and `marks`. Marks use the same 1600 x 1000 canvas, y down, as the full kit: `text`, `code`, `fill`, `brackets`, `dash`, `check` and `image`. A `code` or `text` line can be a list of `(text, colour)` pieces. Spots: `<id>` is the right corner, `<id>_left` the left corner and `<id>_front` the middle of the front edge.

**`v.screen(w, h, image, terminal, body, yaw, pitch, offset, spots)`** is a window or phone. Use a real screenshot as `image`, or `terminal={"lines": [...], "bg", "size", "x", "y", "dots"}`. For the layered-screens hero, draw the back screen first with an `offset` such as `(0.6, 0.1, -0.35)` and `shadow=0`, then the front one. `spots` take `(u, v)` from 0 to 1 on the screen.

**`v.blocks(nodes, edges)`** is isometric blocks for systems, with the node fields `id`, `x`, `z`, `w`, `d`, `h`, `color`, `label` and `labelColor`.

Starting cameras: a plate stack at `az -30, el 26`, with scale about 40 mm per unit for a hero 130 mm wide. A screen at `az 0, el 6`, with `yaw -20`.

## 5. Lessons from real pages

- **Characters:** the bundled fonts have Latin letters, digits, common punctuation and ±, but no Greek letters and no arrows. Write "std. dev." for σ, and "to" or a drawn arrow for →. The build fails on any character the font lacks, because it would print as an empty box.
- **Plates hide each other:** an upper plate covers the back of the one below. Keep each plate's content in its front two thirds, or raise `gap`.
- **The QR code isn't decoded**, since there's no decoder in a sandbox. It's generated from the exact URL, so check that string instead.
- **Ignore full-build steps:** `build.py`, `setup_work.py` and `build.py spots` belong to the full build. Here, spots come back from `plates`, `screen` and `blocks` already in page mm.

## 6. What it can't do

- No photographic lighting or reflections. The hero is clean vector art, so give it a strong idea instead: layered plates with real content, or a screen with a real screenshot.
- No rounded plate corners and no glass reflections.
- Fonts are limited to the bundled family.

Caption the hero as an illustration, exactly as in the full build.
