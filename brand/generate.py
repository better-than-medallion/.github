"""Generator for the Better Than Medallion brand kit.

All text is outlined to SVG paths (fontTools + HarfBuzz shaping), so the SVGs
render identically on GitHub, which shows README SVGs as images without fonts.
"""
import math
import os
import random
import sys

import cairosvg
import uharfbuzz as hb
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONTS = os.path.join(HERE, "fonts")
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "out")
PREVIEW = os.path.join(HERE, "preview")
os.makedirs(OUT, exist_ok=True)
os.makedirs(PREVIEW, exist_ok=True)

# ---------------------------------------------------------------- palette
INK = "#0A1214"        # primary neutral, dark
INK_2 = "#152126"      # raised surface on ink
PAPER = "#EEF0EA"      # primary neutral, light
PAPER_2 = "#DCE1D8"    # rule / surface on paper
SLATE = "#667479"      # gridlines, separators
MUTED_LT = "#5A6467"   # secondary text on paper
MUTED_DK = "#93A3A6"   # secondary text on ink
AMBER = "#FF9F1C"      # bid / up / our P&L, on ink
AMBER_DEEP = "#CC7000" # amber graphics on paper
AMBER_TXT = "#9A5600"  # amber for text on paper
TEAL = "#007385"       # ask / down / benchmark, on paper
TEAL_LT = "#4FD0E0"    # teal on ink

# ---------------------------------------------------------------- fonts
ARCHIVO = os.path.join(FONTS, "Archivo%5Bwdth,wght%5D.ttf")
MONO = os.path.join(FONTS, "IBMPlexMono-Medium.ttf")
SANS = os.path.join(FONTS, "IBMPlexSans%5Bwdth,wght%5D.ttf")

_cache = {}


def _font(path, loc):
    key = (path, tuple(sorted((loc or {}).items())))
    if key not in _cache:
        tt = TTFont(path)
        gs = tt.getGlyphSet(location=loc) if loc else tt.getGlyphSet()
        blob = hb.Blob.from_file_path(path)
        face = hb.Face(blob)
        f = hb.Font(face)
        if loc:
            f.set_variations(loc)
        _cache[key] = (tt, gs, f, tt["head"].unitsPerEm)
    return _cache[key]


def text_width(text, size, font=ARCHIVO, loc=None, tracking=0.0):
    tt, gs, f, upem = _font(font, loc)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f, buf, {"kern": True, "liga": True})
    s = size / upem
    adv = sum(p.x_advance for p in buf.glyph_positions) * s
    return adv + tracking * size * (len(buf.glyph_infos) - 1)


def text_path(text, size, x, y, font=ARCHIVO, loc=None, tracking=0.0, anchor="start"):
    """Return an SVG path 'd' for text with baseline at y. tracking is in em."""
    tt, gs, f, upem = _font(font, loc)
    buf = hb.Buffer()
    buf.add_str(text)
    buf.guess_segment_properties()
    hb.shape(f, buf, {"kern": True, "liga": True})
    order = tt.getGlyphOrder()
    s = size / upem
    w = text_width(text, size, font, loc, tracking)
    if anchor == "middle":
        x -= w / 2
    elif anchor == "end":
        x -= w
    pen = SVGPathPen(gs, ntos=lambda v: f"{v:.1f}".rstrip("0").rstrip("."))
    cx = 0.0
    for info, pos in zip(buf.glyph_infos, buf.glyph_positions):
        name = order[info.codepoint]
        ox = x + (cx + pos.x_offset) * s
        oy = y - pos.y_offset * s
        gs[name].draw(TransformPen(pen, (s, 0, 0, -s, ox, oy)))
        cx += pos.x_advance + tracking * upem
    return pen.getCommands()


DISPLAY = {"wght": 800, "wdth": 112}
SANS_LOC = {"wght": 500, "wdth": 100}

# ---------------------------------------------------------------- curves


def equity_curves(n=420, seed=None):
    """Seeded GBM strategy (with drift + a real drawdown) and a calmer benchmark."""

    def run(sd):
        r = random.Random(sd)
        strat, bench = [1.0], [1.0]
        for i in range(n - 1):
            # regime: a rough patch in the middle third
            rough = n * 0.38 < i < n * 0.52
            mu = -0.0012 if rough else 0.0024
            sig = 0.016 if rough else 0.011
            strat.append(strat[-1] * math.exp(mu + sig * r.gauss(0, 1)))
            bench.append(bench[-1] * math.exp(0.0006 + 0.007 * r.gauss(0, 1)))
        return strat, bench

    def mdd(xs):
        peak, worst = xs[0], 0
        for v in xs:
            peak = max(peak, v)
            worst = max(worst, 1 - v / peak)
        return worst

    if seed is None:
        for sd in range(1, 5000):
            s, b = run(sd)
            early_cross = any(s[i] < b[i] for i in range(20, n // 4))
            if (2.1 < s[-1] < 2.8 and 1.1 < b[-1] < 1.35 and 0.14 < mdd(s) < 0.22
                    and early_cross and s[-1] >= 0.97 * max(s)):
                seed = sd
                break
    s, b = run(seed)
    return seed, s, b, mdd(s)


def to_points(series, x0, y0, w, h, lo, hi, step=1):
    n = len(series)
    pts = []
    for i in range(0, n, step):
        v = series[i]
        pts.append((x0 + w * i / (n - 1), y0 + h - h * (v - lo) / (hi - lo)))
    if (n - 1) % step:
        v = series[-1]
        pts.append((x0 + w, y0 + h - h * (v - lo) / (hi - lo)))
    return pts


def poly(pts):
    return "M" + " L".join(f"{x:.1f} {y:.1f}" for x, y in pts)


def tri(cx, cy, size, up=True):
    h = size * 0.866
    if up:
        return f"M{cx - size / 2:.1f} {cy + h / 2:.1f} L{cx + size / 2:.1f} {cy + h / 2:.1f} L{cx:.1f} {cy - h / 2:.1f} Z"
    return f"M{cx - size / 2:.1f} {cy - h / 2:.1f} L{cx + size / 2:.1f} {cy - h / 2:.1f} L{cx:.1f} {cy + h / 2:.1f} Z"


# ---------------------------------------------------------------- the mark
# 64-unit grid. Medal disc + two ribbon tails (teal = benchmark side,
# amber = our side). An amber equity curve starts under a dashed
# benchmark, dips, crosses it and breaks out through the medal's edge.

CURVE = [(13, 34), (22, 27.5), (28.5, 31.5), (38, 19), (51, 8)]


def mark_group(variant="light", tx=0, ty=0, scale=1.0):
    disc = INK if variant == "light" else PAPER
    dash = PAPER if variant == "light" else INK
    left_tail = TEAL if variant == "light" else TEAL_LT
    ours = AMBER_DEEP if variant == "light" else AMBER
    cid = f"disc-{variant}-{int(tx)}-{int(ty)}"
    curve = poly(CURVE)
    ex, ey = CURVE[-1]
    return f"""<g transform="translate({tx} {ty}) scale({scale})">
  <defs><clipPath id="{cid}"><circle cx="32" cy="26" r="21"/></clipPath></defs>
  <path d="M17 34 L29.5 41 L24.5 63 L19.5 57.5 L12 61 Z" fill="{left_tail}"/>
  <path d="M47 34 L34.5 41 L39.5 63 L44.5 57.5 L52 61 Z" fill="{ours}"/>
  <circle cx="32" cy="26" r="21" fill="{disc}"/>
  <g clip-path="url(#{cid})">
    <path d="M13.5 26.5 H50.5" stroke="{dash}" stroke-width="3.5" stroke-dasharray="5 3" stroke-opacity="0.55" fill="none"/>
  </g>
  <path d="{curve}" stroke="{ours}" stroke-width="5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
  <circle cx="{ex}" cy="{ey}" r="4.6" fill="{ours}"/>
</g>"""


def svg(w, h, body, title, bg=None, desc=None):
    bgr = f'<rect width="{w}" height="{h}" fill="{bg}"/>' if bg else ""
    d = f"<desc>{desc}</desc>" if desc else ""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
            f'viewBox="0 0 {w} {h}" role="img" aria-label="{title}">'
            f"<title>{title}</title>{d}{bgr}{body}</svg>\n")


def write(name, content, png=None, png_w=None):
    p = os.path.join(OUT, name)
    with open(p, "w") as fh:
        fh.write(content)
    if png:
        cairosvg.svg2png(bytestring=content.encode(), write_to=png, output_width=png_w)
    return p


def preview(name, content, w=None):
    cairosvg.svg2png(bytestring=content.encode(), write_to=os.path.join(PREVIEW, name), output_width=w)


# ---------------------------------------------------------------- build
def build_mark():
    s = svg(64, 64, mark_group("light"), "Better Than Medallion mark")
    write("logo-mark.svg", s)
    sd = svg(64, 64, mark_group("dark"), "Better Than Medallion mark (dark backgrounds)")
    write("logo-mark-dark.svg", sd)
    for px in (16, 32, 64, 256):
        preview(f"mark-{px}.png", svg(64, 64, mark_group("light"), "m", bg=PAPER), px)
        preview(f"mark-dark-{px}.png", svg(64, 64, mark_group("dark"), "m", bg=INK), px)


def build_avatar():
    # mark occupies the central ~62%: crop-safe for rounded squares and circles
    size = 500
    sc = 5.5
    m = 64 * sc
    body = mark_group("dark", tx=(size - m) / 2, ty=(size - m) / 2 + 2, scale=sc)
    s = svg(size, size, body, "Better Than Medallion avatar", bg=INK)
    write("avatar.svg", s, png=os.path.join(OUT, "avatar.png"), png_w=size)
    preview("avatar-40.png", s, 40)


def chart(x0, y0, w, h, dark, seed, s, b, label=True, area=True):
    lo = min(min(s), min(b)) * 0.96
    hi = max(max(s), max(b)) * 1.03
    sp = to_points(s, x0, y0, w, h, lo, hi, step=2)
    bp = to_points(b, x0, y0, w, h, lo, hi, step=3)
    grid = SLATE
    bench = TEAL_LT if dark else TEAL
    ours = AMBER if dark else AMBER_DEEP
    out = []
    for i in range(4):
        gy = y0 + h * i / 3
        out.append(f'<path d="M{x0} {gy:.1f} H{x0 + w}" stroke="{grid}" stroke-opacity="{0.28 if dark else 0.35}" stroke-width="1.5" fill="none"/>')
    if area:
        gid = "fade-dark" if dark else "fade-light"
        out.append(f'<defs><linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1">'
                   f'<stop offset="0" stop-color="{ours}" stop-opacity="{0.30 if dark else 0.22}"/>'
                   f'<stop offset="1" stop-color="{ours}" stop-opacity="0"/></linearGradient></defs>')
        out.append(f'<path d="{poly(sp)} L{x0 + w} {y0 + h} L{x0} {y0 + h} Z" fill="url(#{gid})"/>')
    out.append(f'<path d="{poly(bp)}" stroke="{bench}" stroke-width="3" stroke-dasharray="8 7" stroke-linecap="round" fill="none"/>')
    out.append(f'<path d="{poly(sp)}" stroke="{ours}" stroke-width="4" stroke-linejoin="round" stroke-linecap="round" fill="none"/>')
    ex, ey = sp[-1]
    out.append(f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="7" fill="{ours}"/>')
    bx, by = bp[-1]
    return "\n".join(out), (ex, ey), (bx, by)


def build_banner(dark):
    W, H = 1280, 320
    bg = INK if dark else PAPER
    fg = PAPER if dark else INK
    muted = MUTED_DK if dark else MUTED_LT
    bench_c = TEAL_LT if dark else TEAL
    pers_txt = AMBER if dark else AMBER_TXT
    seed, s, b, dd = SERIES
    parts = []
    # mark
    parts.append(mark_group("dark" if dark else "light", tx=64, ty=70, scale=2.6))
    # wordmark, stacked
    tx = 64 + 64 * 2.6 + 32
    parts.append(f'<path d="{text_path("Better Than", 60, tx, 132, loc=DISPLAY, tracking=-0.01)}" fill="{fg}"/>')
    parts.append(f'<path d="{text_path("Medallion", 60, tx, 198, loc=DISPLAY, tracking=-0.01)}" fill="{fg}"/>')
    parts.append(f'<path d="{text_path("Low latency, high hopes.", 26, tx, 252, font=SANS, loc=SANS_LOC)}" fill="{muted}"/>')
    # chart, right
    cx0, cy0, cw, ch = 712, 56, 352, 196
    c, (ex, ey), (bx, by) = chart(cx0, cy0, cw, ch, dark, seed, s, b)
    parts.append(c)
    # labels at line ends
    ret_s = (s[-1] - 1) * 100
    ret_b = (b[-1] - 1) * 100
    parts.append(f'<path d="{tri(ex + 24, ey, 14, True)}" fill="{AMBER if dark else AMBER_DEEP}"/>')
    parts.append(f'<path d="{text_path(f"BTM +{ret_s:.0f}%", 20, ex + 36, ey + 7, font=MONO)}" fill="{pers_txt}"/>')
    parts.append(f'<path d="{text_path(f"BENCH +{ret_b:.0f}%", 20, bx + 18, by + 7, font=MONO)}" fill="{bench_c}"/>')
    parts.append(f'<path d="{text_path("BACKTEST · NOT ADVICE · DEFINITELY OVERFIT", 17, cx0, cy0 + ch + 42, font=MONO, tracking=0.03)}" fill="{muted}"/>')
    name = "banner-dark.svg" if dark else "banner-light.svg"
    content = svg(W, H, "\n".join(parts), "Better Than Medallion. Low latency, high hopes.", bg=bg)
    write(name, content)
    preview(name.replace(".svg", ".png"), content, W)
    preview(name.replace(".svg", "-830.png"), content, 830)


def build_divider():
    W, H, FS = 1280, 32, 16
    items = [("BTM", True, "+2.14%"), ("SHARPE", True, "1.87"), ("LATENCY", False, "3.2µs"),
             ("DRAWDOWN", False, "-0.8%"), ("COFFEE", True, "+14%"), ("ALPHA", True, "0.42"),
             ("SLEEP", False, "-6h"), ("OVERFIT", False, "0.00")]
    widths = [text_width(a, FS, MONO, None, 0.04) + 10 + 18 + text_width(c, FS, MONO) for a, _, c in items]
    margin = 24
    gap = (W - 2 * margin - sum(widths)) / (len(items) - 1)
    parts = [f'<rect width="{W}" height="{H}" fill="{INK}"/>']
    x = margin
    for i, ((sym, up, val), w) in enumerate(zip(items, widths)):
        col = AMBER if up else TEAL_LT
        parts.append(f'<path d="{text_path(sym, FS, x, 21.8, font=MONO, tracking=0.04)}" fill="{PAPER}"/>')
        tx = x + text_width(sym, FS, MONO, None, 0.04) + 10
        parts.append(f'<path d="{tri(tx + 6, 16, 11, up)}" fill="{col}"/>')
        parts.append(f'<path d="{text_path(val, FS, tx + 18, 21.8, font=MONO)}" fill="{col}"/>')
        x += w + gap
        if i < len(items) - 1:
            parts.append(f'<rect x="{x - gap / 2 - 1:.1f}" y="11" width="2" height="10" fill="{SLATE}"/>')
    content = svg(W, H, "\n".join(parts), "Ticker tape divider")
    write("divider.svg", content)
    preview("divider.png", content, W)
    preview("divider-830.png", content, 830)
    return gap


def build_social():
    W, H = 1280, 640
    seed, s, b, dd = SERIES
    parts = []
    c, (ex, ey), (bx, by) = chart(0, 372, W - 200, 268, True, seed, s, b)
    parts.append(c)
    parts.append(f'<path d="{tri(ex + 26, ey, 16, True)}" fill="{AMBER}"/>')
    parts.append(f'<path d="{text_path(f"BTM +{(s[-1] - 1) * 100:.0f}%", 24, ex + 42, ey + 8, font=MONO)}" fill="{AMBER}"/>')
    parts.append(f'<path d="{text_path(f"BENCH +{(b[-1] - 1) * 100:.0f}%", 24, bx + 20, by + 8, font=MONO)}" fill="{TEAL_LT}"/>')
    parts.append(mark_group("dark", tx=88, ty=84, scale=3.2))
    tx = 88 + 64 * 3.2 + 44
    parts.append(f'<path d="{text_path("Better Than", 78, tx, 164, loc=DISPLAY, tracking=-0.01)}" fill="{PAPER}"/>')
    parts.append(f'<path d="{text_path("Medallion", 78, tx, 250, loc=DISPLAY, tracking=-0.01)}" fill="{PAPER}"/>')
    parts.append(f'<path d="{text_path("Low latency, high hopes.", 34, tx, 318, font=SANS, loc=SANS_LOC)}" fill="{MUTED_DK}"/>')
    parts.append(f'<path d="{text_path("github.com/better-than-medallion", 20, W - 64, 76, font=MONO, anchor="end")}" fill="{MUTED_DK}"/>')
    content = svg(W, H, "\n".join(parts), "Better Than Medallion", bg=INK)
    cairosvg.svg2png(bytestring=content.encode(), write_to=os.path.join(OUT, "social-preview.png"), output_width=W)
    with open(os.path.join(PREVIEW, "social-preview.svg"), "w") as fh:
        fh.write(content)


if __name__ == "__main__":
    SERIES = equity_curves()
    print("seed", SERIES[0], "strat", round(SERIES[1][-1], 3), "bench", round(SERIES[2][-1], 3), "mdd", round(SERIES[3], 3))
    print("wordmark width", text_width("Better Than", 60, ARCHIVO, DISPLAY, -0.01))
    build_mark()
    build_avatar()
    build_banner(True)
    build_banner(False)
    print("divider gap", build_divider())
    build_social()
