# onesheet blueprint

How to build the page. This skill ships no program. Instead, you write a small page builder for this run, `work/sheet.py`, from the specification below, then a short `work/page.py` that uses it. The specification is exact where exactness decides quality: units, text measurement, the 3D projection, and the checks. Follow it closely. A builder that skips the checks produces pages that look fine at a glance and fail on paper.

Everything runs in Python with reportlab and pillow, so it works the same in Claude Code, Cowork, claude.ai and the Claude desktop app.

## 1. Set up

Work in a folder outside the repo: `~/.onesheet/<repo>/work` on a computer, or a fresh folder in a chat sandbox. Check the libraries once:

```bash
python -c "import reportlab, PIL; print('ok')"
python -c "import pypdf, pypdfium2; print('ok')"
```

reportlab and pillow are required. pypdf (text extraction) and pypdfium2 (previews) are strongly wanted. If any are missing, tell the user which, then `pip install reportlab pillow pypdf pypdfium2`. If previews still can't be made, build anyway and say in the delivery message that you couldn't look at the page, because the critique in SKILL.md Step 7 depends on seeing it.

**Fonts.** The page uses IBM Plex Sans at weights 300, 400, 600 and 700, and IBM Plex Mono at 400 and 500, free under the SIL Open Font License. Fetch them once into `work/fonts/` from the Google Fonts CSS API, which serves static TrueType files to a plain client:

```python
url = "https://fonts.googleapis.com/css?family=IBM+Plex+Sans:300,400,600,700|IBM+Plex+Mono:400,500"
css = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "onesheet"})).read().decode()
for family, weight, src in re.findall(r"font-family: '([^']+)';.*?font-weight: (\d+);.*?url\((https://[^)]+\.ttf)\)", css, re.S):
    # save to work/fonts/<IBMPlexSans|IBMPlexMono>-<weight>.ttf
```

Each file must start with the bytes `00 01 00 00`. If the download fails, as it can in a sandbox with limited internet, fall back in this order and tell the user which you used:

1. DejaVu Sans and DejaVu Sans Mono from the system (`/usr/share/fonts/truetype/dejavu/`) or from matplotlib's `mpl-data/fonts/ttf/`, if either is present. Map weights 300 and 400 to the regular face, and 600 and 700 to bold.
2. reportlab's built-in Helvetica, Helvetica-Bold, Courier and Courier-Bold, which need no files. They cover Latin-1 only, so the glyph check becomes: every character encodes in cp1252.

Vary colour between projects, not the family.

## 2. What to write

Write `work/sheet.py` once per page. It holds:

- constants and helpers (section 3)
- a `Page` class: drawing calls that also record geometry (sections 4 to 6)
- a `View` class: an orthographic camera and three scenes (sections 7 and 8)
- `Page.save()`: writes the PDF, runs every check, writes previews (sections 9 and 10)

Then write `work/page.py`, which imports it and lays out the page (section 11). Build into `work/out/`.

Before the real page, run a smoke test: a page with one text block, one step box and one plate stack. Confirm the PDF opens, the preview renders, and that a deliberately overlapping text pair fails the check. Fix the builder until it does. Testing the checks is not optional: in development, a check with a sign error passed every page.

The public API the rest of this skill assumes:

| Call | What it draws and records |
|---|---|
| `Page(path, size, ledger, banned, title, ink, text_color, muted, line, accent)` | A4 or Letter canvas. Title goes into the PDF metadata. |
| `text(x, y, w, s, size, weight, color, leading, mono, kind, align, parent)` | Wrapped text with its top at y. Returns its bottom. |
| `label(x, y, title, sub, w, align)` | A leader label: a 7.8 pt weight 600 line in ink, then a 7.5 pt muted line |
| `rect(x, y, w, h, fill, stroke, sw, r, alpha, label)` | A box. A filled box is an obstacle for text. |
| `rule(x, y, w)` | A 0.2 mm hairline. Text crossing it fails. |
| `line(points, color, sw, arrow, dash, block)` | A path. With `block=True`, text it crosses fails. |
| `dot(x, y, color)` | A marker dot with a white halo |
| `leader(spot, (x, y or None), color)` | A thin accent line from a spot on the hero to a label. Returns the label's y. |
| `code(x, y, w, lines)` | A dark command block |
| `step(x, y, w, h, name, note, strong)` | A diagram box |
| `image(x, y, w, path)` | A raster image, with its printed dpi recorded |
| `qr(x, y, size, url)` | A vector QR code that also links |
| `view(cx, cy, scale, az, el)` | A camera for `plates`, `screen` and `blocks` |
| `save(strict=True)` | PDF, checks, previews. Returns the list of failures. With `strict=True`, exits with status 1 if there are any, so the smoke test passes `strict=False` to inspect them. |

All positions are in millimetres from the page's top left, y down.

## 3. Units, fonts and colours

```python
MM = 72 / 25.4                       # points per mm
SIZES = {"A4": (210, 297), "Letter": (215.9, 279.4)}
X = lambda x: x * MM                 # mm from left  -> PDF points
Y = lambda y: (H - y) * MM           # mm from top   -> PDF points (PDF y runs up)
```

Register the six fonts from `work/fonts/` with `reportlab.pdfbase.ttfonts.TTFont` as `Sans-300`, `Sans-400`, `Sans-600`, `Sans-700`, `Mono-400` and `Mono-500`. Map a requested weight to the nearest registered sans weight. Plex Mono's advance is 0.6 em for every character, so a mono run of n characters at size s is exactly `0.6 * n * s` points wide, which is what lets you aim a leader at a terminal column. For mono, use 500 when the weight is 500 or more, else 400.

Set `setLineCap(1)` and `setLineJoin(1)` once, so hairlines end round and joins look drawn, not cut.

Default palette, to change per project: ink `#0a1a3f`, text `#3d4c6b`, muted `#6a7893`, hairline `#dce4f2`, accent `#1a56e0`. Always write colours with six hex digits: reportlab's `HexColor` misreads the three-digit form.

## 4. Text

Text decides whether the page reads as designed. Measure every word with `pdfmetrics.stringWidth(text, font, size)` and wrap yourself. Never estimate widths.

**Inline styles.** Split each paragraph on `(\*\*.+?\*\*|`.+?`)`. `**bold**` raises the weight by 200, capped at 700, and is drawn in ink, whatever the colour of the text around it. `` `code` `` is mono, at 0.94 of the size when the surrounding text is sans, and weight 500 when the surrounding weight is 600 or more. A word is a run of pieces between spaces, so `**bold**,` stays one word and never wraps apart.

**Wrapping.** Greedy: add words while `line_width + space + word_width <= w`. A `\n` starts a new paragraph line. The space width is the width of `" "` in the base font.

**Placement.** Line i has its baseline at `y + 0.80 * size_mm + i * leading_mm`, where `size_mm = size / MM` and leading defaults to `1.32 * size` points. Alignment shifts each line by `w - line_width` (right) or half that (centre).

**Record every line** as a rectangle for the checks: `(line_x, baseline - 0.78 * size_mm, line_width, size_mm)`. Store per text block: its plain string, its rectangles, its size, its kind (`body` or `diagram`) and its parent box, if any. Record each glyph drawn, per font, for the missing-glyph check.

**Orphans.** If a block wraps to two or more lines and its last line holds one word, add a note. Only the block's last line counts, in body and diagram text alike. Notes print but don't fail; fix them anyway during the critique.

Return `y + lines * leading_mm`, so the next block can sit under this one.

## 5. Shapes

- **rect:** `roundRect` when r is set. A filled rect is recorded as an obstacle, labelled with its name, and text may sit on it only if that text names it as `parent`.
- **rule:** a 0.2 mm line in the hairline colour, recorded as an obstacle `(x, y - 0.1, w, 0.2)` named "a rule". It doesn't record itself as a crossing line, since the obstacle covers it.
- **line:** a stroked path. With `block=True`, each segment is recorded for the line-through-text check. The arrowhead follows the last segment: with unit direction (ux, uy), draw an open V from `(x1 - 1.3ux + 0.75uy, y1 - 1.3uy - 0.75ux)` to the tip to `(x1 - 1.3ux - 0.75uy, y1 - 1.3uy + 0.75ux)`, in mm.
- **dot:** a white circle of radius r + 0.3 mm, then a coloured circle of radius r = 0.62 mm.
- **leader:** a 0.2 mm accent line with `block=False`, from the spot to `(x, y)`, where y defaults to the spot's y for a level line, then a dot on the spot. Record the segment separately as a leader, minus its last 2.5 mm, where its own label sits. The checks fail a leader that crosses any text.
- **label:** the title at 7.8 pt, weight 600, ink, leading 10 pt. The sub line starts right at the title's bottom, at 7.5 pt, muted, leading 9.6 pt. Put the label's top 1.7 mm above the leader's level, so the line runs just under the title's first line.
- **code:** a filled box in `#101827`, radius 1.2 mm, padding 3.2 mm, Mono 400 at 7.8 pt with leading 1.45, text `#e6ebf5`. Its height is `2 * pad + n * lead - (lead - size_mm)` for n lines. A line may be a list of `(text, colour)` pieces, such as a muted `#9fb0d0` `$ ` prompt. Each line is recorded as one body text record whose parent is the box, never one record per coloured piece, or the pieces collide with each other, so it may go down to 6.2 pt, though 6.8 pt or more reads better.
- **step:** a box of radius 1.1 mm: white with a `#cfd6e4` stroke of 0.22 mm, or, when `strong`, the accent mixed 6% into white with an accent stroke of 0.3 mm. Inside, 1.8 mm in from the left and 1.9 mm from the top: the name at 7.6 pt weight 600 in ink, leading 9.4, then 0.4 mm lower the note at 6.2 pt in text colour, leading 7.8. Both are `kind="diagram"` with the box as parent.
- **image:** draw with `ImageReader`. Record `dpi = pixel_width / (printed_width_mm / 25.4)` and the image's outline as a solid that text may not sit on.
- **qr:** `reportlab.graphics.barcode.qr.QrCodeWidget(url)` with `barBorder = 0` and `barFillColor` set to ink. Scale it by its `getBounds()` into a `Drawing` of the given size, rendered with `renderPDF.draw`, plus `canvas.linkURL` over the same square. Record it as a solid.

## 6. Soft shadows

PDF vectors can't blur, so a shadow is a small raster. For a footprint polygon in mm:

1. Pad its bounding box by three times the blur radius.
2. Draw the polygon into a greyscale image at 300 dpi (`k = 300 / 25.4` pixels per mm), filled with `255 * opacity`.
3. Apply `GaussianBlur(blur * k)`.
4. Use it as the alpha of an RGBA image in the ink colour and draw it with `mask="auto"`.
5. Record the shadow's extent, the footprint grown by two blur radii, which is where the haze is still visible, for the shadow-on-rule check.

Typical opacity is 0.14 to 0.16.

## 7. The camera

The hero is exact orthographic 3D. Exact matters: leader dots land on the true corners, and text on plates stays vector.

```python
def proj(x, y, z):                    # scene units -> page mm; y is up
    x1 = x * cos(az) + z * sin(az)
    z1 = -x * sin(az) + z * cos(az)
    up = y * cos(el) - z1 * sin(el)
    return (cx + x1 * scale, cy - up * scale)

def depth(x, y, z):                   # larger is nearer the viewer
    z1 = -x * sin(az) + z * cos(az)
    return z1 * cos(el) + y * sin(el)
```

`az` turns around the object and `el` looks down, both in degrees converted to radians. `(cx, cy)` is where the scene origin lands on the page, and `scale` is mm per scene unit.

**Drawing flat content onto a projected plane.** This is what makes text and screenshots sit on a tilted plate. Map a canvas of `cw x ch` units, y down, onto the projected quad whose top left is O, top right R and bottom left F:

```python
a = (R[0] - O[0]) / cw * MM;  b = -(R[1] - O[1]) / cw * MM
c = (F[0] - O[0]) / ch * MM;  d = -(F[1] - O[1]) / ch * MM
canvas.saveState()
canvas.transform(a, b, c, d, X(O[0]), Y(O[1]))
# clip to rect(0, 0, cw, ch), draw marks in canvas units, then:
canvas.restoreState()
```

Inside this mapping, y runs down the canvas, so text must be drawn flipped back: `translate(x, y)`, then `scale(1, -1)`, then `drawString(0, 0, text)`.

**Filled polygons:** build a path from projected points, close it, and fill or stroke it. Reset fill alpha to 1 afterwards.

**The shadow footprint** of a scene is the convex hull (monotone chain) of its projected floor corners.

**Plan before you draw.** `proj` is pure, so call it in `page.py` before drawing to find where corners and spots will land, and adjust `cx`, `cy` and `scale` until spots fall where the labels belong on the grid. At az −30, +x moves right and down the page, and +z moves left and down, so a staircase of plates offset in x needs a `gap` large enough to rise anyway.

## 8. Scenes

Every scene records each visible top face or screen as a solid, so no page text may sit on the hero, and returns named spots in page mm for leaders.

**Marks** are drawn on a mapped plane, in canvas units, y down:

| Kind | Fields | Drawn as |
|---|---|---|
| `text` | x, y, lines, size (130), weight (600), color (ink), leading (1.27 × size) | Sans lines. A line may be a list of `(text, colour)` pieces. |
| `code` | the same, weight 500 | Mono lines |

For `text` and `code` marks, `y` is the top of the first line, and its baseline is at `y + 0.8 × size`, as in section 4.
| `fill` | x, y, w, h, color, alpha, r (20) | A rounded filled box |
| `brackets` | x, y, w, h, color, len (96), width (15) | Four corner brackets and a 10% tint inside |
| `dash` | x, y, w, h, color, width (12) | A dashed rounded outline, dash 46 and gap 30 |
| `check` | x, y, r, color | A circle with a tick |
| `image` | src, x, y, w, h, r | An image covering the box, centred and clipped |

### plates(layers, size=(1.6, 1.0), gap=0.5, thickness=0.03, shadow=0.16, edge="#c9d2e3", shadow_mode="stack")

An exploded stack, bottom layer first. Layer fields: `id`, `rim` (outline colour), `tint` (face colour), `glass` (face alpha, default 0.86), `opaque`, `level` (default its index), `x`, `z`, `scale` and `marks`. The marks canvas is 1600 × 1000 per plate.

1. For each layer, y = level × gap, half width = size[0] / 2 × scale, half depth = size[1] / 2 × scale, and thickness × scale.
2. Shadow, with blur 0.08 × scale. With `shadow_mode="stack"`, one shadow: the hull of every layer's four corners projected at the floor height, 0.2 below the lowest layer. That suits a vertical stack. With `shadow_mode="each"`, each plate gets its own shadow, its corners projected 0.15 below its own level, drawn just before the plate. Use `each` for a staircase or a row of plates, where one shared hull smears a diagonal band under the labels.
3. Draw layers sorted by (y, depth of the centre), lowest and farthest first.
4. For each layer: of the four side faces, draw only those whose outward midpoint has greater depth than the centre, filled with `edge`. Then fill the top face with the tint at the glass alpha. Map the 1600 × 1000 canvas onto it with O, R and F at the corners (−x, −z), (+x, −z) and (−x, +z), clip, and draw the marks. Then stroke the top face's outline in the rim colour at 0.3 mm.
5. Spots: `<id>` at the corner (+x, +z) on the top face, moved 0.02 scene units × the layer's scale towards the centre on both axes; `<id>_left` at (−x, +z), moved the same; and `<id>_front` at the middle of the (+z) edge.

### screen(w, h, image=None, terminal=None, body="#20283a", yaw=-22, pitch=-4, offset=(0,0,0), bezel=0.03, depth=0.035, spots=None, shadow=0.14, px=1400)

A window or phone: a screen on a slab. In the screen's local frame, u runs right, v runs up and d runs out of the screen towards the viewer, with the screen's centre at the scene origin. A local point (u, v, d) is turned by pitch, then by yaw, then offset, then projected:

```python
v, d = v * cos(pitch) - d * sin(pitch), v * sin(pitch) + d * cos(pitch)
u, d = u * cos(yaw) + d * sin(yaw), -u * sin(yaw) + d * cos(yaw)
return proj(u + off[0], v + off[1], d + off[2])
```

With the default camera, a negative yaw turns the screen's right edge away from the viewer.

1. The front face is the screen grown by the bezel. The back face is the same at d = −depth.
2. Shadow: a floor quad under the bottom edge, 0.05 below it, spanning the full width and d from −0.25 to 0.25, turned by yaw only, with blur 0.06 × scale.
3. Fill the four sides between front and back in the body colour, then the front face.
4. Map a canvas `px` wide (height in proportion) onto the screen itself, at d = 0.001.
5. Draw either the image, recording its dpi across the projected width, or a terminal, a dict with the keys `lines`, `bg` (`#0b1020`), `color` (`#e6ebf5`), `size` (px / 34), `x` (50), `y` (130), `leading` (1.5) and `dots` (true). It draws a background fill, then three window dots at 50, 94 and 138 px across and 46 px down (`#ff5f57`, `#febc2e`, `#28c840`, radius 13), then the mono lines, each a string or a list of `(text, colour)` pieces. px / 34 fits about 54 columns. For wider real output, lower `size` to fit (px / (0.6 × columns + 4)), or raise `px`. A light `bg` with a dark `color` makes a file or document panel.
6. Spots are given as fractions from 0 to 1, measured across and down from the screen's top left, so a spot (a, b) is the local point (−w/2 + a·w, h/2 − b·h, 0.001). To aim at terminal row i (from 0) and column c, use a = (x + 0.6 × size × c) / px and b = (y + i × leading × size + 0.45 × size) / ch, where ch is the canvas height. That lands on the middle of the row's text. Then check the landing in a 400 dpi zoom, since no check can tell a dot is one row off.

For layered screens, draw the back one first, with an offset such as (0.6, 0.1, −0.35) and no shadow.

### blocks(nodes, edges=(), shadow=0.14)

Isometric blocks for systems. Node fields: `id`, `x`, `z`, `w`, `d`, `h` (0.2), `color`, `label` and `labelColor` (white).

1. Edges first, as accent lines at 0.35 mm along the floor: from a to (b.x, a.z) to b.
2. Shadow: the hull of all footprints, blur 0.05 × scale.
3. Draw nodes sorted by depth, farthest first: the front face shaded to 0.82 of the colour, the side face to 0.68, then the top.
4. A label is fitted to the top face, mapped as a canvas 1000 wide and 1000 × d / w tall: start at 170 units, shrink in steps of 10 until it fits 860 wide, centre it across, and put its baseline at half the canvas height plus 0.35 × size.
5. Spots are the top centres.

## 9. The checks in save()

Close the page, then extract its text with pypdf for the banned-word and secret scans. Count words and numbers from the recorded strings instead: pypdf splits text drawn in pieces, so `client` + `.get(url)` would count twice. Run every check and collect failures. Print the file, page size, megabytes and word count, then either "All automated checks passed" or each failure. Return the failures, and exit with status 1 if there are any and `strict` is true.

| Check | Rule |
|---|---|
| Words | Join every recorded string, including diagram, label, code and plate text, and count tokens matching `\S*[A-Za-z0-9]\S*`. Must be 220 to 320, including diagrams and code. |
| Banned words | Case-insensitive: seamless, powerful, robust, leverage, revolutionary, next-generation, the em dash, plus the page's own banned list |
| Secrets | Fail on text that looks like an AWS key, a GitHub token, an `sk-` key, a Slack token, a private key header, or a password or API key assignment |
| Type size | Body text 6.2 pt or more, diagram text 5.8 pt or more |
| Page margin | Every text line inside 7 mm of each page edge |
| Objects in margins | Every code block, step box, image and QR code inside the 13 mm side margins and the 7 mm top and bottom margins. A hero may bleed off an edge only when the page script says so for that edge. |
| Grid | Every text line with no parent inside the 13 mm side margins, with 0.5 mm tolerance |
| Parent | Text with a parent stays inside it, with 0.3 mm tolerance |
| Collisions | No two text lines from different blocks overlap. Rects a and b collide when `a.x < b.x + b.w - 0.25` and `b.x < a.x + a.w - 0.25`, and the same in y. |
| Text on fills | No text overlaps a filled box or rule unless the box is its parent, with 0.15 mm padding |
| Text on the hero | No text line touches a solid (plate, screen, block, image, QR). Sample 15 points per line (5 across, 3 down) with an even-odd point-in-polygon test. |
| Lines through text | No blocking line segment or leader crosses a text line shrunk by 0.2 mm. Sample along the segment every 0.4 mm. |
| Missing glyphs | Every drawn character exists in its font's `face.charToGlyph`. A missing one prints as an empty box. |
| Shadows | No soft shadow's extent overlaps a rule |
| Image sharpness | Every image and screen image at 299 dpi or more as printed |
| Numbers | Print, without failing, every number on the page (`\d+(?:,\d{3})*(?:\.\d+)?`) that doesn't appear as a whole token in the first two columns of the ledger. Compare token sets, never substrings. Check each by hand, single digits included. |
| Column edges | Note, without failing, each text block with no parent whose left edge isn't within 0.5 mm of a column start (13 + 15.67n on A4, 13 + 16.16n on Letter) |

Print notes, such as orphans, after the checks.

## 10. Previews

Rasterize page 1 at 200 dpi with pypdfium2 (`PdfDocument(path)[0].render(scale=200/72).to_pil()`). Fall back to PyMuPDF, then `pdftoppm`. Write, beside the PDF:

- `page.png`: the full page at 200 dpi
- `page_small.jpg`: the same at 110 dpi, for the whole view
- `z_top.png` and `z_bottom.png`: the top and bottom halves at 200 dpi, for detail

Also write a `zoom(pdf, x, y, w, h)` helper: a 400 dpi crop in mm, for judging leader landings and small type.

## 11. The page script

```python
import sys; sys.path.insert(0, ".")
from sheet import Page

INK, ACC = "#0a1a3f", "#1a56e0"
p = Page("out/name-one-pager.pdf", size="A4", accent=ACC, ink=INK, ledger="facts.md",
         title="Name: what it does", banned=["internal-name"])
p.text(13, 18, 106, "A headline that says something.", size=34, weight=600, color=INK, leading=36)
p.text(124, 20, 73, "One or two plain sentences. **Bold** and `code` work inline.", size=9.2, leading=12.8)

v = p.view(cx=72, cy=96, scale=40, az=-30, el=26)
spots = v.plates([...], gap=0.5, thickness=0.03)
y = p.leader(spots["out"], (130, None))
p.label(131.5, y - 1.7, "Timed text comes out", "In the language spoken", w=60)
p.text(13, 150, 120, "Illustration, not a real run.", size=6.4, color="#6a7893")
...
p.save()
```

Starting cameras: a plate stack at az −30 and el 26, with a scale of about 40 mm per unit for a hero 130 mm wide. A screen at az 0 and el 6, with yaw −20.

## 12. Lessons from real pages

- **Characters:** the fonts have Latin letters, digits, common punctuation and ±, but no Greek letters and no arrow glyphs. Write "std. dev." for σ, and "to" or a drawn arrow for →. When real output you're quoting contains such a character, spell it out the same way and say so in the caption, such as "σ written as std. dev.".
- **Hero text counts as words.** Every word on a plate or screen counts towards the 320. A faithful terminal can take 70 words, so show the few lines that tell the story, and cut columns the reader doesn't need.
- **Plates hide each other:** an upper plate covers the back of the one below. Keep each plate's content in its front two thirds, or raise `gap`.
- **Text on plates is foreshortened:** use short strings at 130 units or more.
- **The QR code isn't decoded:** it's generated from the exact URL, so check that string instead.
- **Previews are the truth:** the checks find collisions and sizes. Only the rendered page shows that a hero looks flat or a section feels empty.

## 13. What this build can't do

- No photographic lighting or reflections. The hero is clean vector art, so give it a strong idea: layered plates with real content, or a screen with a real screenshot.
- No rounded plate corners.
- Fonts are limited to IBM Plex, or the fallbacks in section 1.

Caption the hero as an illustration.
