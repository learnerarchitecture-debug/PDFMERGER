"""Generate the PDF Suite Pro application icon (app_icon.ico).

Modern flat design: rounded-square with the app's indigo -> violet gradient,
a white document with a folded corner and indigo text lines.

Run:  python make_icon.py
Outputs: app_icon.ico (multi-size Windows icon)
"""
import os
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_ICO = os.path.join(HERE, "app_icon.ico")

S = 1024            # master logical size
SS = 4              # supersample factor
M = S * SS          # working canvas

C1 = (0x5B, 0x7C, 0xFA)   # indigo (app accent)
C2 = (0x8B, 0x5C, 0xF6)   # violet (app accent 2)


def lerp(a, b, t):
    return int(round(a + (b - a) * t))


def grad_color(t):
    return tuple(lerp(C1[i], C2[i], t) for i in range(3))


def build_master():
    # ── background: vertical gradient masked to a rounded square ──
    g = Image.new("RGB", (1, M))
    for y in range(M):
        g.putpixel((0, y), grad_color(y / float(M - 1)))
    g = g.resize((M, M))
    mask = Image.new("L", (M, M), 0)
    md = ImageDraw.Draw(mask)
    md.rounded_rectangle([0, 0, M - 1, M - 1], radius=int(M * 0.22), fill=255)
    img = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    img.paste(g, (0, 0), mask)

    # ── soft top-left light ──
    hl = Image.new("L", (M, M), 0)
    hd = ImageDraw.Draw(hl)
    hd.ellipse([-M * 0.45, -M * 0.95, M * 1.45, M * 0.40], fill=64)
    hl = hl.filter(ImageFilter.GaussianBlur(M // 10))
    wh = Image.new("RGBA", (M, M), (255, 255, 255, 0))
    wh.putalpha(hl)
    img = Image.alpha_composite(img, wh)

    # ── document geometry ──
    dx0, dy0 = M * 0.275, M * 0.205
    dx1, dy1 = M * 0.725, M * 0.825
    rad = int(M * 0.055)
    fold = M * 0.145

    # drop shadow under the document
    sh = Image.new("L", (M, M), 0)
    sd = ImageDraw.Draw(sh)
    sd.rounded_rectangle([dx0, dy0 + M * 0.025, dx1, dy1 + M * 0.025],
                         radius=rad, fill=95)
    sh = sh.filter(ImageFilter.GaussianBlur(M * 0.028))
    shadow = Image.new("RGBA", (M, M), (8, 12, 28, 0))
    shadow.putalpha(sh)
    img = Image.alpha_composite(img, shadow)

    # white document with cut top-right corner
    doc = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    dd = ImageDraw.Draw(doc)
    dd.rounded_rectangle([dx0, dy0, dx1, dy1], radius=rad,
                         fill=(255, 255, 255, 255))
    dd.polygon([(dx1 - fold, dy0 - 2), (dx1 + 2, dy0 - 2), (dx1 + 2, dy0 + fold)],
               fill=(0, 0, 0, 0))
    # fold flap
    dd.polygon([(dx1 - fold, dy0), (dx1, dy0 + fold), (dx1 - fold, dy0 + fold)],
               fill=(0xC9, 0xD4, 0xF0, 255))
    img = Image.alpha_composite(img, doc)

    # ── text lines (indigo bars) ──
    lines = Image.new("RGBA", (M, M), (0, 0, 0, 0))
    ld = ImageDraw.Draw(lines)
    bar_h = M * 0.042
    r = int(bar_h / 2)
    x = dx0 + M * 0.055
    col = (C1[0], C1[1], C1[2], 255)
    for y, w in ((M * 0.415, 0.315), (M * 0.525, 0.250), (M * 0.635, 0.185)):
        ld.rounded_rectangle([x, y, x + M * w, y + bar_h], radius=r, fill=col)
    img = Image.alpha_composite(img, lines)
    return img


def main():
    master = build_master()
    master = master.resize((S, S), Image.Resampling.LANCZOS)
    sizes = [256, 128, 64, 48, 32, 24, 16]
    master.save(OUT_ICO, format="ICO", sizes=[(s, s) for s in sizes])
    print("Wrote", OUT_ICO)
    # preview (for humans; not part of the build)
    prev = Image.new("RGBA", (S + 40, S + 40), (16, 20, 30, 255))
    prev.alpha_composite(master.resize((S, S), Image.Resampling.LANCZOS), (20, 20))
    pv = os.path.join(HERE, "icon_preview.png")
    prev.resize((320, 320), Image.Resampling.LANCZOS).save(pv)
    print("Wrote", pv)


if __name__ == "__main__":
    main()
