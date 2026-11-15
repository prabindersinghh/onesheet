"""onesheet lite: build the one-page PDF with Python only, for sandboxes with no browser, such as claude.ai chat.

Needs reportlab and pillow. pypdf and pypdfium2 are used when present. A page is a short Python script:

    import sys; sys.path.insert(0, "<skill folder>/scripts")
    from sheet import Page
    p = Page("out/page.pdf", size="A4", accent="#1a56e0")
    p.text(13, 18, 110, "A headline that says something.", size=34, weight=600, leading=36)
    ...
    p.save()

All positions are in mm from the page's top left. save() runs the checks and writes previews to out/.
"""
import io
import math
import pathlib
import re
import shutil
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as rlcanvas

MM = 72 / 25.4
FONTS = pathlib.Path(__file__).resolve().parent.parent / "assets" / "fonts"
SIZES = {"A4": (210, 297), "Letter": (215.9, 279.4)}
WORD_BUDGET = (220, 320)
BANNED = ["seamless", "powerful", "robust", "leverage", "revolutionary", "next-generation", "—"]
SECRETS = [r"AKIA[0-9A-Z]{16}", r"ghp_[A-Za-z0-9]{20,}", r"github_pat_\w{20,}", r"sk-[A-Za-z0-9_-]{20,}", r"xox[bap]-[A-Za-z0-9-]{10,}",
           r"-----BEGIN [A-Z ]*PRIVATE KEY", r"(?i)(password|passwd|api[_-]?key|secret)\s*[=:]\s*\S{6,}"]
MIN_PT = {"body": 6.2, "diagram": 5.8}
NUMBER = r"\d+(?:,\d{3})*(?:\.\d+)?"


def _fonts():
    if "Sans-400" in pdfmetrics.getRegisteredFontNames():
        return
    for w in (300, 400, 600, 700):
        pdfmetrics.registerFont(TTFont(f"Sans-{w}", str(FONTS / f"IBMPlexSans-{w}.ttf")))
    for w in (400, 500):
        pdfmetrics.registerFont(TTFont(f"Mono-{w}", str(FONTS / f"IBMPlexMono-{w}.ttf")))


def font(weight=400, mono=False):
    if mono:
        return "Mono-500" if weight >= 500 else "Mono-400"
    return f"Sans-{min((300, 400, 600, 700), key=lambda w: abs(w - weight))}"


def _overlap(a, b, pad=0.25):
    return a[0] < b[0] + b[2] - pad and b[0] < a[0] + a[2] - pad and a[1] < b[1] + b[3] - pad and b[1] < a[1] + a[3] - pad


def _inside(a, b, pad=0.3):
    return a[0] >= b[0] - pad and a[1] >= b[1] - pad and a[0] + a[2] <= b[0] + b[2] + pad and a[1] + a[3] <= b[1] + b[3] + pad


def _in_poly(x, y, poly):
    hit = False
    for i in range(len(poly)):
        (x1, y1), (x2, y2) = poly[i], poly[i - 1]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            hit = not hit
    return hit


def _rect_hits_poly(r, poly):
    x, y, w, h = r
    pts = [(x + w * i / 4, y + h * j / 2) for i in range(5) for j in range(3)]
    return any(_in_poly(px, py, poly) for px, py in pts)


class Page:
    def __init__(self, path, size="A4", ledger="facts.md", banned=(), title="", author="", subject="One-page brief",
                 ink="#0a1a3f", text_color="#3d4c6b", muted="#6a7893", line="#dce4f2", accent="#1a56e0", margin=7):
        _fonts()
        self.path = pathlib.Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.size = size
        self.W, self.H = SIZES[size]
        self.ledger, self.banned, self.margin = pathlib.Path(ledger), list(banned), margin
        self.ink, self.text_color, self.muted, self.line_color, self.accent = ink, text_color, muted, line, accent
        self.c = rlcanvas.Canvas(str(self.path), pagesize=(self.W * MM, self.H * MM))
        self.c.setTitle(title); self.c.setAuthor(author); self.c.setSubject(subject)
        self.c.setLineCap(1); self.c.setLineJoin(1)
        self.texts, self.fills, self.solids, self.images, self.notes = [], [], [], [], []

    # ------------------------------------------------------------------ basics
    def X(self, x): return x * MM
    def Y(self, y): return (self.H - y) * MM

    def _fill(self, color, alpha=1):
        self.c.setFillColor(HexColor(color)); self.c.setFillAlpha(alpha)

    def _stroke(self, color, width_mm=0.2, alpha=1):
        self.c.setStrokeColor(HexColor(color)); self.c.setLineWidth(width_mm * MM); self.c.setStrokeAlpha(alpha)

    def rect(self, x, y, w, h, fill=None, stroke=None, sw=0.2, r=0, alpha=1, label=""):
        """A box in mm. A filled box is an obstacle: text may sit on it only if it was drawn with parent= this box."""
        if fill: self._fill(fill, alpha)
        if stroke: self._stroke(stroke, sw)
        if r: self.c.roundRect(self.X(x), self.Y(y + h), w * MM, h * MM, r * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        else: self.c.rect(self.X(x), self.Y(y + h), w * MM, h * MM, stroke=1 if stroke else 0, fill=1 if fill else 0)
        self.c.setFillAlpha(1)
        box = (x, y, w, h)
        if fill: self.fills.append((box, label or "a filled box"))
        return box

    def rule(self, x, y, w, color=None, sw=0.2):
        """A hairline. Text crossing it fails the check."""
        self.line([(x, y), (x + w, y)], color or self.line_color, sw)
        self.fills.append(((x, y - sw / 2, w, sw), "a rule"))

    def line(self, pts, color=None, sw=0.2, arrow=False, dash=None):
        c = self.c
        self._stroke(color or self.line_color, sw)
        if dash: c.setDash([d * MM for d in dash])
        p = c.beginPath(); p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]: p.lineTo(self.X(x), self.Y(y))
        c.drawPath(p, stroke=1, fill=0)
        if dash: c.setDash([])
        if arrow:  # the head follows the last segment
            (x0, y0), (x1, y1) = pts[-2], pts[-1]
            n = math.hypot(x1 - x0, y1 - y0) or 1
            ux, uy = (x1 - x0) / n, (y1 - y0) / n
            a = (x1 - 1.3 * ux + .75 * uy, y1 - 1.3 * uy - .75 * ux)
            b = (x1 - 1.3 * ux - .75 * uy, y1 - 1.3 * uy + .75 * ux)
            p = c.beginPath(); p.moveTo(self.X(a[0]), self.Y(a[1])); p.lineTo(self.X(x1), self.Y(y1)); p.lineTo(self.X(b[0]), self.Y(b[1]))
            c.drawPath(p, stroke=1, fill=0)

    def dot(self, x, y, color=None, r=0.62):
        self._fill("#ffffff"); self.c.circle(self.X(x), self.Y(y), (r + 0.3) * MM, stroke=0, fill=1)
        self._fill(color or self.accent); self.c.circle(self.X(x), self.Y(y), r * MM, stroke=0, fill=1)

    def leader(self, frm, to, color=None, end_dot=False):
        """A thin line from a spot on the hero to a label. Use to=(x, None) for a level line."""
        tx, ty = to
        ty = frm[1] if ty is None else ty
        self.line([frm, (tx, ty)], color or self.accent, 0.2)
        self.dot(*frm, color=color)
        if end_dot: self._fill(color or self.accent); self.c.circle(self.X(tx), self.Y(ty), 0.5 * MM, stroke=0, fill=1)
        return ty

    # ------------------------------------------------------------------ text
    def _words(self, s, weight, mono):
        """Split into words, each a list of (text, (weight, mono)) pieces, so "**bold**," stays one word."""
        words, cur = [], []
        for part in re.split(r"(\*\*.+?\*\*|`.+?`)", s):
            if not part: continue
            if part.startswith("**"): style, part = (min(weight + 200, 700), mono), part[2:-2]
            elif part.startswith("`"): style, part = (500 if weight >= 600 else 400, True), part[1:-1]
            else: style = (weight, mono)
            for tok in re.split(r"( +)", part):
                if not tok: continue
                if tok.isspace():
                    if cur: words.append(cur); cur = []
                else:
                    cur.append((tok, style))
        if cur: words.append(cur)
        return words

    def text(self, x, y, w, s, size=8.2, weight=400, color=None, leading=None, mono=False, kind="body", align="left", parent=None):
        """Wrapped text whose top sits at y. **bold** and `code` work inline. Returns the y of its bottom, in mm.
        kind is "body" (6.2 pt minimum) or "diagram" (5.8 pt). parent is a box the text is allowed to sit on."""
        c, size_mm = self.c, size / MM
        leading_mm = (leading or size * 1.32) / MM
        lines, cur, cur_w = [], [], 0.0
        space = pdfmetrics.stringWidth(" ", font(weight, mono), size) / MM
        for paragraph in s.split("\n"):
            for word in self._words(paragraph, weight, mono):
                ww = sum(pdfmetrics.stringWidth(t, font(*st), size * (0.94 if st[1] and not mono else 1)) for t, st in word) / MM
                if cur and cur_w + space + ww > w:
                    lines.append((cur, cur_w)); cur, cur_w = [], 0.0
                cur_w += (space if cur else 0) + ww; cur.append(word)
            lines.append((cur, cur_w)); cur, cur_w = [], 0.0
        rects = []
        for i, (words, lw) in enumerate(lines):
            base = y + size_mm * 0.80 + i * leading_mm
            lx = x + (w - lw if align == "right" else (w - lw) / 2 if align == "center" else 0)
            cx = lx
            for j, word in enumerate(words):
                if j: cx += space
                for t, (wt, mn) in word:
                    sz = size * (0.94 if mn and not mono else 1)
                    c.setFont(font(wt, mn), sz); self._fill(color or self.text_color)
                    c.drawString(self.X(cx), self.Y(base), t)
                    cx += pdfmetrics.stringWidth(t, font(wt, mn), sz) / MM
            if words: rects.append((lx, base - size_mm * 0.78, lw, size_mm * 1.0))
        if len(lines) > 1 and lines[-1][0] and len(lines[-1][0]) == 1 and kind == "body":
            self.notes.append(f'orphan word at the end of "{s[:40]}"')
        self.texts.append({"s": re.sub(r"\*\*|`", "", s), "rects": rects, "size": size, "kind": kind, "parent": parent})
        return y + len(lines) * leading_mm

    def label(self, x, y, title, sub="", w=60, align="left", color=None):
        """A leader-line label: a bold line and a muted line."""
        b = self.text(x, y, w, title, size=7.8, weight=600, color=self.ink, align=align, leading=10)
        return self.text(x, b, w, sub, size=7.5, color=color or self.muted, align=align, leading=9.6) if sub else b

    def code(self, x, y, w, lines, size=7.8, bg="#101827", fg="#e6ebf5", pad=3.2, leading=None):
        """A dark command block. Each line is a string or a list of (text, color) pieces."""
        lead = (leading or size * 1.45) / MM
        h = pad * 2 + lead * len(lines) - (lead - size / MM)
        box = self.rect(x, y, w, h, fill=bg, r=1.2, label="the code block")
        for i, ln in enumerate(lines):
            cx, base = x + pad, y + pad + size / MM * 0.8 + i * lead
            for t, col in ([(ln, fg)] if isinstance(ln, str) else ln):
                self.c.setFont("Mono-400", size); self._fill(col); self.c.drawString(self.X(cx), self.Y(base), t)
                cx += pdfmetrics.stringWidth(t, "Mono-400", size) / MM
            self.texts.append({"s": "".join(t for t, _ in ([(ln, fg)] if isinstance(ln, str) else ln)),
                               "rects": [(x + pad, base - size / MM * .78, cx - x - pad, size / MM)], "size": size, "kind": "body", "parent": box})
        return y + h

    # ------------------------------------------------------------------ diagram
    def step(self, x, y, w, h, name, note="", strong=False, mono_note=False, color=None):
        """A diagram box: a bold name and a short note. Its text must stay inside it."""
        acc = color or self.accent
        box = self.rect(x, y, w, h, fill="#f4f7fe" if strong else "#ffffff", stroke=acc if strong else "#cfd6e4", sw=.3 if strong else .22, r=1.1, label=name)
        b = self.text(x + 1.8, y + 1.9, w - 3.6, name, size=7.6, weight=600, color=self.ink, kind="diagram", parent=box, leading=9.4)
        if note: self.text(x + 1.8, b + 0.4, w - 3.6, note, size=6.2, color=self.text_color, mono=mono_note, kind="diagram", parent=box, leading=7.8)
        return box

    # ------------------------------------------------------------------ images and QR
    def image(self, x, y, w, path, h=None, label="an image"):
        im = Image.open(path)
        h = h or w * im.height / im.width
        dpi = im.width / (w / 25.4)
        self.c.drawImage(ImageReader(im), self.X(x), self.Y(y + h), w * MM, h * MM, mask="auto")
        self.images.append((label, dpi))
        self.solids.append(([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], label))
        return y + h

    def qr(self, x, y, size, url, color=None):
        from reportlab.graphics import renderPDF
        from reportlab.graphics.barcode.qr import QrCodeWidget
        from reportlab.graphics.shapes import Drawing
        wdg = QrCodeWidget(url); wdg.barFillColor = HexColor(color or self.ink); wdg.barBorder = 0
        b = wdg.getBounds(); bw, bh = b[2] - b[0], b[3] - b[1]
        d = Drawing(size * MM, size * MM, transform=[size * MM / bw, 0, 0, size * MM / bh, 0, 0]); d.add(wdg)
        renderPDF.draw(d, self.c, self.X(x), self.Y(y + size))
        self.c.linkURL(url, (self.X(x), self.Y(y + size), self.X(x + size), self.Y(y)), relative=0)
        self.solids.append(([(x, y), (x + size, y), (x + size, y + size), (x, y + size)], "the QR code"))
        self.qr_url = url

    # ------------------------------------------------------------------ 3D, drawn as vector art
    def view(self, cx, cy, scale, az=-32, el=25):
        """A camera. (cx, cy) is where the scene's origin lands on the page, scale is mm per scene unit."""
        return View(self, cx, cy, scale, az, el)

    def _shadow(self, poly, blur=3.0, opacity=0.16, color=None):
        """A soft shadow under a footprint, rasterized at 300 dpi, since vector PDFs can't blur."""
        xs, ys = [p[0] for p in poly], [p[1] for p in poly]
        x0, y0, x1, y1 = min(xs) - blur * 3, min(ys) - blur * 3, max(xs) + blur * 3, max(ys) + blur * 3
        k = 300 / 25.4
        W, H = max(1, int((x1 - x0) * k)), max(1, int((y1 - y0) * k))
        m = Image.new("L", (W, H), 0)
        ImageDraw.Draw(m).polygon([((px - x0) * k, (py - y0) * k) for px, py in poly], fill=int(255 * opacity))
        m = m.filter(ImageFilter.GaussianBlur(blur * k))
        col = HexColor(color or self.ink)
        rgba = Image.new("RGBA", (W, H), (int(col.red * 255), int(col.green * 255), int(col.blue * 255), 0)); rgba.putalpha(m)
        self.c.drawImage(ImageReader(rgba), self.X(x0), self.Y(y1), (x1 - x0) * MM, (y1 - y0) * MM, mask="auto")

    def _plane(self, O, R, F, cw, ch):
        """Map a cw x ch canvas (y down) onto the projected plane O (top left), R (top right), F (bottom left)."""
        a = (R[0] - O[0]) / cw * MM; b = -(R[1] - O[1]) / cw * MM
        c = (F[0] - O[0]) / ch * MM; d = -(F[1] - O[1]) / ch * MM
        self.c.transform(a, b, c, d, self.X(O[0]), self.Y(O[1]))

    def _poly(self, pts, fill=None, stroke=None, sw=0.25, alpha=1):
        p = self.c.beginPath(); p.moveTo(self.X(pts[0][0]), self.Y(pts[0][1]))
        for x, y in pts[1:]: p.lineTo(self.X(x), self.Y(y))
        p.close()
        if fill: self._fill(fill, alpha)
        if stroke: self._stroke(stroke, sw)
        self.c.drawPath(p, stroke=1 if stroke else 0, fill=1 if fill else 0)
        self.c.setFillAlpha(1)

    def _marks(self, marks, cw, ch, mono_size_scale=1.0):
        """Draw marks on a plane already mapped with _plane. Units are canvas pixels, y down."""
        c = self.c
        for m in marks or []:
            k = m.get("kind")
            c.saveState()
            if k in ("text", "code"):
                fnt = font(m.get("weight", 600 if k == "text" else 500), k == "code")
                self._fill(m.get("color", self.ink))
                for i, t in enumerate(m["lines"]):
                    c.saveState(); c.translate(m["x"], m["y"] + i * m.get("leading", m.get("size", 130) * 1.27)); c.scale(1, -1)
                    if isinstance(t, str): t = [(t, m.get("color", self.ink))]
                    cx = 0
                    for piece, col in t:
                        c.setFont(fnt, m.get("size", 130)); self._fill(col); c.drawString(cx, 0, piece)
                        cx += pdfmetrics.stringWidth(piece, fnt, m.get("size", 130))
                    c.restoreState()
            elif k == "fill":
                self._fill(m["color"], m.get("alpha", 1)); c.roundRect(m["x"], m["y"], m["w"], m["h"], m.get("r", 20), stroke=0, fill=1)
            elif k == "brackets":
                L = m.get("len", 96); c.setStrokeColor(HexColor(m["color"])); c.setLineWidth(m.get("width", 15))
                for ax, ay, dx, dy in [(m["x"], m["y"], 1, 1), (m["x"] + m["w"], m["y"], -1, 1), (m["x"] + m["w"], m["y"] + m["h"], -1, -1), (m["x"], m["y"] + m["h"], 1, -1)]:
                    p = c.beginPath(); p.moveTo(ax + dx * L, ay); p.lineTo(ax, ay); p.lineTo(ax, ay + dy * L); c.drawPath(p, stroke=1, fill=0)
                self._fill(m["color"], 0.1); c.rect(m["x"], m["y"], m["w"], m["h"], stroke=0, fill=1)
            elif k == "dash":
                c.setStrokeColor(HexColor(m["color"])); c.setLineWidth(m.get("width", 12)); c.setDash([46, 30])
                c.roundRect(m["x"], m["y"], m["w"], m["h"], 26, stroke=1, fill=0)
            elif k == "check":
                r = m["r"]; s = r / 170; c.setStrokeColor(HexColor(m["color"])); c.setLineWidth(16); c.circle(m["x"], m["y"], r, stroke=1, fill=0)
                c.setLineWidth(20); p = c.beginPath(); p.moveTo(m["x"] - 78 * s, m["y"] + 4 * s); p.lineTo(m["x"] - 16 * s, m["y"] + 64 * s); p.lineTo(m["x"] + 88 * s, m["y"] - 62 * s); c.drawPath(p, stroke=1, fill=0)
            elif k == "image":
                x, y, w, h = m.get("x", 0), m.get("y", 0), m.get("w", cw), m.get("h", ch)
                im = Image.open(m["src"]).convert("RGB")
                sc = max(w / im.width, h / im.height); iw, ih = im.width * sc, im.height * sc
                p = c.beginPath(); p.roundRect(x, y, w, h, m.get("r", 0)); c.clipPath(p, stroke=0, fill=0)
                c.translate(x + (w - iw) / 2, y + (h - ih) / 2 + ih); c.scale(1, -1)
                c.drawImage(ImageReader(im), 0, 0, iw, ih)
            c.restoreState()

    def save(self):
        """Write the PDF, run the checks, render previews. Exits with status 1 if a check fails."""
        self.c.showPage(); self.c.save()
        text = self._extract()
        fails, words = [], len(text.split())
        print(f"file: {self.path}\npage: {self.size} {self.W} x {self.H} mm, {self.path.stat().st_size / 1048576:.2f} MB, {words} words")
        if not WORD_BUDGET[0] <= words <= WORD_BUDGET[1]:
            fails.append(f"{words} words on the page, including diagrams and code. The budget is {WORD_BUDGET[0]} to {WORD_BUDGET[1]}.")
        bad = [b for b in self.banned + BANNED if b.lower() in text.lower()]
        if bad: fails.append(f"banned words on the page: {bad}")
        hits = [p for p in SECRETS if re.search(p, text)]
        if hits: fails.append(f"secret-like text on the page, matching: {hits}")
        T, m = self.texts, self.margin
        lab = lambda t: t["s"][:42].replace("\n", " ")
        for i, a in enumerate(T):
            lim = MIN_PT.get(a["kind"], 6.2)
            if a["size"] < lim - 0.01: fails.append(f'type too small: {a["size"]} pt "{lab(a)}", minimum {lim}')
            for r in a["rects"]:
                if r[0] < m or r[1] < m or r[0] + r[2] > self.W - m or r[1] + r[3] > self.H - m: fails.append(f'outside the margins: "{lab(a)}"'); break
                if a["parent"] and not _inside(r, a["parent"]): fails.append(f'"{lab(a)}" runs out of its box'); break
            for b in T[i + 1:]:
                if any(_overlap(r, q) for r in a["rects"] for q in b["rects"]): fails.append(f'"{lab(a)}" touches "{lab(b)}"')
            for box, name in self.fills:
                if box == a["parent"]: continue
                if any(_overlap(r, box, 0.15) for r in a["rects"]): fails.append(f'"{lab(a)}" sits on {name}')
            for poly, name in self.solids:
                if any(_rect_hits_poly(r, poly) for r in a["rects"]): fails.append(f'"{lab(a)}" sits on {name}')
        for name, dpi in self.images:
            if dpi < 299: fails.append(f"{name} is {dpi:.0f} dpi as printed, under 300")
        missing = self._numbers(text)
        if missing: print("numbers not in facts.md, check each by hand:", missing)
        for n in self.notes: print("note:", n)
        self._previews()
        fails = list(dict.fromkeys(fails))
        print("CHECKS FAILED:\n  " + "\n  ".join(fails) if fails else "All automated checks passed. Now look at out/page_small.jpg, out/z_top.png and out/z_bottom.png.")
        if fails: sys.exit(1)

    def _extract(self):
        try:
            from pypdf import PdfReader
            return PdfReader(str(self.path)).pages[0].extract_text()
        except Exception:
            return "\n".join(t["s"] for t in self.texts)

    def _numbers(self, text):
        led = self.ledger.read_text(encoding="utf-8") if self.ledger.exists() else ""
        cells = [c for row in led.splitlines() if row.lstrip().startswith("|") for c in row.split("|")[1:3]]
        return sorted(set(re.findall(NUMBER, text)) - set(re.findall(NUMBER, " ".join(cells))))

    def _previews(self):
        out = self.path.parent
        img = rasterize(self.path, 200)
        if img is None:
            print("note: no PDF rasterizer here (pypdfium2, PyMuPDF or pdftoppm), so no previews. Say so in the delivery message.")
            return
        img.save(out / "page.png")
        img.resize((img.width * 110 // 200, img.height * 110 // 200), Image.LANCZOS).save(out / "page_small.jpg", quality=90)
        img.crop((0, 0, img.width, img.height // 2)).save(out / "z_top.png")
        img.crop((0, img.height // 2, img.width, img.height)).save(out / "z_bottom.png")


class View:
    """An orthographic camera: az turns around the object, el looks down. Projections are exact, so spots are exact."""

    def __init__(self, page, cx, cy, scale, az, el):
        self.p, self.cx, self.cy, self.s = page, cx, cy, scale
        self.a, self.e = math.radians(az), math.radians(el)

    def proj(self, x, y, z):
        x1 = x * math.cos(self.a) + z * math.sin(self.a)
        z1 = -x * math.sin(self.a) + z * math.cos(self.a)
        up = y * math.cos(self.e) - z1 * math.sin(self.e)
        return (self.cx + x1 * self.s, self.cy - up * self.s)

    def depth(self, x, y, z):
        z1 = -x * math.sin(self.a) + z * math.cos(self.a)
        return z1 * math.cos(self.e) + y * math.sin(self.e)

    def plates(self, layers, size=(1.6, 1.0), gap=0.5, thickness=0.03, shadow=0.16, edge="#c9d2e3"):
        """An exploded stack, bottom layer first. Layer fields: id, rim, tint, glass, level, x, z, scale, marks.
        Marks use a 1600 x 1000 canvas per plate, y down, like the full kit. Returns spots in page mm:
        <id> (right corner), <id>_left, <id>_front."""
        P, PW, PD, spots = self.p, size[0], size[1], {}
        CW, CH = 1600, 1000
        items = []
        for i, l in enumerate(layers):
            k, lx, lz = l.get("scale", 1), l.get("x", 0), l.get("z", 0)
            y = l.get("level", i) * gap
            hw, hd, T = PW / 2 * k, PD / 2 * k, thickness * k
            items.append((l, k, lx, lz, y, hw, hd, T))
        floor = min(it[4] for it in items) - 0.2
        foot = [self.proj(it[2] + sx * it[5], floor, it[3] + sz * it[6]) for it in items for sx, sz in [(-1, -1), (1, -1), (1, 1), (-1, 1)]]
        if shadow:
            hull = _hull(foot)
            P._shadow(hull, blur=self.s * 0.08, opacity=shadow)
        for l, k, lx, lz, y, hw, hd, T in sorted(items, key=lambda it: (it[4], self.depth(it[2], it[4], it[3]))):
            corner = lambda sx, sz, yy: self.proj(lx + sx * hw, yy, lz + sz * hd)
            top = [corner(-1, -1, y + T), corner(1, -1, y + T), corner(1, 1, y + T), corner(-1, 1, y + T)]
            bot = [corner(-1, -1, y), corner(1, -1, y), corner(1, 1, y), corner(-1, 1, y)]
            mid = self.depth(lx, y, lz)
            sides = {(3, 2): (0, 1), (2, 1): (1, 0), (0, 3): (-1, 0), (1, 0): (0, -1)}  # face -> outward (x, z)
            for (a, b), (nx, nz) in sides.items():  # only the faces turned towards the camera
                if self.depth(lx + nx * hw, y, lz + nz * hd) > mid:
                    P._poly([top[a], top[b], bot[b], bot[a]], fill=edge)
            P._poly(top, fill=l.get("tint", "#eef3fc"), alpha=1 if l.get("opaque") else l.get("glass", 0.86))
            P.c.saveState(); P._plane(top[0], top[1], top[3], CW, CH)
            p = P.c.beginPath(); p.rect(0, 0, CW, CH); P.c.clipPath(p, stroke=0, fill=0)
            P._marks(l.get("marks"), CW, CH)
            P.c.restoreState()
            P._poly(top, stroke=l.get("rim", P.ink), sw=0.3)
            P.solids.append((top, f'the {l["id"]} plate'))
            inset = 0.02 * k
            spots[l["id"]] = self.proj(lx + hw - inset, y + T, lz + hd - inset)
            spots[f'{l["id"]}_left'] = self.proj(lx - hw + inset, y + T, lz + hd - inset)
            spots[f'{l["id"]}_front'] = self.proj(lx, y + T, lz + hd)
        return spots

    def screen(self, w, h, image=None, terminal=None, body="#20283a", yaw=-22, pitch=-4, offset=(0, 0, 0), bezel=0.03,
               depth=0.035, spots=None, shadow=0.14, px=1400):
        """A window or phone: a screen on a slab, turned by yaw and pitch. Give image= (a path) or terminal=
        {"bg", "lines": [str or [(text, color), ...]], "size", "x", "y", "dots"}. spots are (u, v) from 0 to 1 on the screen.
        Call it for the back screen first when layering one behind another."""
        P = self.p
        ya, pa = math.radians(yaw), math.radians(pitch)

        def world(u, v, d=0.0):
            x, y, z = u, v, d
            y, z = y * math.cos(pa) - z * math.sin(pa), y * math.sin(pa) + z * math.cos(pa)
            x, z = x * math.cos(ya) + z * math.sin(ya), -x * math.sin(ya) + z * math.cos(ya)
            return self.proj(x + offset[0], y + offset[1], z + offset[2])

        W2, H2 = w / 2 + bezel, h / 2 + bezel
        front = [world(-W2, H2), world(W2, H2), world(W2, -H2), world(-W2, -H2)]
        back = [world(-W2, H2, -depth), world(W2, H2, -depth), world(W2, -H2, -depth), world(-W2, -H2, -depth)]
        if shadow:
            floor = [self.proj(*_floor_pt(ya, offset, sx * W2, -H2 - 0.05, sz)) for sx, sz in [(-1, -0.25), (1, -0.25), (1, 0.25), (-1, 0.25)]]
            P._shadow(floor, blur=self.s * 0.06, opacity=shadow)
        for a, b in [(0, 1), (1, 2), (2, 3), (3, 0)]:
            P._poly([front[a], front[b], back[b], back[a]], fill=body)
        P._poly(front, fill=body)
        tl, tr, bl = world(-w / 2, h / 2, 0.001), world(w / 2, h / 2, 0.001), world(-w / 2, -h / 2, 0.001)
        CW, CH = px, round(px * h / w)
        c = P.c
        c.saveState(); P._plane(tl, tr, bl, CW, CH)
        p = c.beginPath(); p.rect(0, 0, CW, CH); c.clipPath(p, stroke=0, fill=0)
        if image:
            P._marks([{"kind": "image", "src": image}], CW, CH)
        elif terminal:
            t = terminal
            P._fill(t.get("bg", "#0b1020")); c.rect(0, 0, CW, CH, stroke=0, fill=1)
            if t.get("dots", True):
                for i, col in enumerate(["#ff5f57", "#febc2e", "#28c840"]):
                    P._fill(col); c.circle(50 + i * 44, 46, 13, stroke=0, fill=1)
            size = t.get("size", round(CW / 34))
            P._marks([{"kind": "code", "x": t.get("x", 50), "y": t.get("y", 130), "size": size, "leading": size * 1.5,
                       "lines": t["lines"], "color": t.get("color", "#e6ebf5")}], CW, CH)
        c.restoreState()
        P.solids.append((front, "the screen"))
        return {k: world(-w / 2 + u * w, h / 2 - v * h, 0.001) for k, (u, v) in (spots or {}).items()}

    def blocks(self, nodes, edges=(), shadow=0.14):
        """Isometric blocks for systems. Node fields: id, x, z, w, d, h, color, label, labelColor. Spots are top centres."""
        P, spots = self.p, {}
        for e in edges:
            a = next(n for n in nodes if n["id"] == e["from"]); b = next(n for n in nodes if n["id"] == e["to"])
            pts = [self.proj(a["x"], 0.02, a["z"]), self.proj(b["x"], 0.02, a["z"]), self.proj(b["x"], 0.02, b["z"])]
            P.line(pts, e.get("color", P.accent), 0.35)
        if shadow:
            hull = _hull([self.proj(n["x"] + sx * n["w"] / 2, 0, n["z"] + sz * n["d"] / 2) for n in nodes for sx in (-1, 1) for sz in (-1, 1)])
            P._shadow(hull, blur=self.s * 0.05, opacity=shadow)
        for n in sorted(nodes, key=lambda n: self.depth(n["x"], 0, n["z"])):
            hw, hd, h, col = n["w"] / 2, n["d"] / 2, n.get("h", 0.2), HexColor(n["color"])
            C = lambda sx, yy, sz: self.proj(n["x"] + sx * hw, yy, n["z"] + sz * hd)
            top = [C(-1, h, -1), C(1, h, -1), C(1, h, 1), C(-1, h, 1)]
            shade = lambda f: "#%02x%02x%02x" % tuple(int(v * 255 * f) for v in (col.red, col.green, col.blue))
            P._poly([C(-1, h, 1), C(1, h, 1), C(1, 0, 1), C(-1, 0, 1)], fill=shade(0.82))
            P._poly([C(1, h, -1), C(1, h, 1), C(1, 0, 1), C(1, 0, -1)], fill=shade(0.68))
            P._poly(top, fill=n["color"])
            if n.get("label"):
                P.c.saveState(); P._plane(top[0], top[1], top[3], 1000, 1000 * n["d"] / n["w"])
                lbl, size = n["label"], 170
                while pdfmetrics.stringWidth(lbl, "Sans-600", size) > 860 and size > 60: size -= 10
                P._marks([{"kind": "text", "x": (1000 - pdfmetrics.stringWidth(lbl, "Sans-600", size)) / 2, "y": 500 * n["d"] / n["w"] + size * 0.35,
                           "size": size, "lines": [lbl], "color": n.get("labelColor", "#ffffff")}], 1000, 1000)
                P.c.restoreState()
            P.solids.append(([C(-1, h, -1), C(1, h, -1), C(1, 0, -1), C(1, 0, 1), C(-1, 0, 1), C(-1, h, 1)], f'the {n["id"]} block'))
            spots[n["id"]] = self.proj(n["x"], h, n["z"])
        return spots


def _floor_pt(ya, offset, x, y, z):
    return (x * math.cos(ya) + z * math.sin(ya) + offset[0], y + offset[1], -x * math.sin(ya) + z * math.cos(ya) + offset[2])


def _hull(points):
    pts = sorted(set(points))
    if len(pts) < 3: return pts
    cross = lambda o, a, b: (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0: lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0: hi.pop()
        hi.append(p)
    return lo[:-1] + hi[:-1]


def rasterize(pdf, dpi=200):
    """The page as a PIL image, from whichever renderer this machine has."""
    try:
        import pypdfium2
        doc = pypdfium2.PdfDocument(str(pdf)); img = doc[0].render(scale=dpi / 72).to_pil().convert("RGB"); doc.close(); return img
    except Exception:
        pass
    try:
        import fitz
        pix = fitz.open(str(pdf))[0].get_pixmap(dpi=dpi); return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    except Exception:
        pass
    exe = shutil.which("pdftoppm")
    if exe:
        out = pathlib.Path(pdf).with_suffix("")
        subprocess.run([exe, "-r", str(dpi), "-png", "-singlefile", str(pdf), str(out)], check=True)
        return Image.open(str(out) + ".png").convert("RGB")
    return None


def zoom(pdf, x, y, w, h, out="out/zoom.png"):
    """A 400 dpi crop of the PDF, in mm, to judge detail."""
    img = rasterize(pdf, 400)
    if img is None: return print("no rasterizer here")
    k = 400 / 25.4
    img.crop((int(x * k), int(y * k), int((x + w) * k), int((y + h) * k))).save(out); print("wrote", out)


if __name__ == "__main__" and len(sys.argv) == 6 and sys.argv[1].endswith(".pdf"):
    zoom(sys.argv[1], *map(float, sys.argv[2:]))
