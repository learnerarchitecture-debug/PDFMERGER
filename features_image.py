"""Image feature engine - pure logic, no UI imports (used by app + CLI)."""
import os
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont, ImageFilter

IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif", ".ico")

_FORMAT_ALIAS = {"JPG": "JPEG", "TIF": "TIFF"}


def norm_format(fmt):
    f = str(fmt or "").upper().lstrip(".")
    return _FORMAT_ALIAS.get(f, f)


def ext_for(fmt):
    f = norm_format(fmt)
    return {"JPEG": ".jpg", "TIFF": ".tif"}.get(f, "." + f.lower())


def _ext_format(path):
    e = os.path.splitext(path)[1].lower().lstrip(".")
    f = norm_format(e)
    return f if f else "PNG"


def _out_path(path, outdir, suffix="", ext=None):
    base = os.path.splitext(os.path.basename(path))[0]
    ex = ext or os.path.splitext(path)[1]
    if not ex.startswith("."):
        ex = "." + ex
    return os.path.join(outdir, base + suffix + ex)


def _run_batch(paths, fn, progress=None):
    results = []
    total = len(paths)
    for i, p in enumerate(paths):
        try:
            results.append((p, fn(p), None))
        except Exception as e:
            results.append((p, None, str(e)))
        if progress:
            progress(i + 1, total)
    return results


def _flatten(img, color=(255, 255, 255)):
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, color)
        bg.paste(img, mask=img.split()[-1])
        return bg
    if img.mode != "RGB":
        return img.convert("RGB")
    return img


def _save(img, out, fmt, quality=90):
    fmt = norm_format(fmt)
    if fmt == "JPEG":
        _flatten(img).save(out, "JPEG", quality=int(quality), optimize=True,
                           progressive=True)
    elif fmt == "WEBP":
        img.save(out, "WEBP", quality=int(quality))
    elif fmt == "PNG":
        img.save(out, "PNG", optimize=True)
    elif fmt == "TIFF":
        img.save(out, "TIFF", compression="tiff_deflate")
    elif fmt == "GIF":
        img.convert("P", palette=Image.Palette.ADAPTIVE).save(out, "GIF", optimize=True)
    elif fmt == "BMP":
        _flatten(img).save(out, "BMP")
    elif fmt == "ICO":
        _flatten(img).save(out, "ICO", sizes=[(16, 16), (24, 24), (32, 32),
                                              (48, 48), (64, 64), (128, 128),
                                              (256, 256)])
    else:
        img.save(out, fmt)


# ───────────────────────── core image operations ─────────────────────────
def compress_images(paths, outdir, quality=60, progress=None):
    def do(p):
        with Image.open(p) as img:
            out = _out_path(p, outdir, "_compressed", ".jpg")
            _save(ImageOps.exif_transpose(img), out, "JPEG", quality)
            return out
    return _run_batch(paths, do, progress)


def convert_images(paths, outdir, fmt="PNG", quality=90, progress=None):
    fmt = norm_format(fmt)
    ex = ext_for(fmt)

    def do(p):
        with Image.open(p) as img:
            out = _out_path(p, outdir, "", ex)
            _save(ImageOps.exif_transpose(img), out, fmt, quality)
            return out
    return _run_batch(paths, do, progress)


def resize_images(paths, outdir, width=None, height=None, percent=None,
                  keep_aspect=True, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            if percent:
                sc = float(percent) / 100.0
                nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
            elif width and height:
                if keep_aspect:
                    sc = min(float(width) / w, float(height) / h)
                    nw, nh = max(1, int(w * sc)), max(1, int(h * sc))
                else:
                    nw, nh = int(width), int(height)
            elif width:
                nw = int(width)
                nh = max(1, int(h * float(width) / w)) if keep_aspect else h
            elif height:
                nh = int(height)
                nw = max(1, int(w * float(height) / h)) if keep_aspect else w
            else:
                nw, nh = w, h
            out = _out_path(p, outdir, "_%dx%d" % (nw, nh), ext_for(fmt))
            _save(img.resize((nw, nh), Image.Resampling.LANCZOS), out, fmt, 90)
            return out
    return _run_batch(paths, do, progress)


def rotate_images(paths, outdir, angle=90, flip="none", progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            if angle:
                img = img.rotate(-float(angle), expand=True)
            if flip == "horizontal":
                img = ImageOps.mirror(img)
            elif flip == "vertical":
                img = ImageOps.flip(img)
            out = _out_path(p, outdir, "_rot%d" % int(angle or 0), ext_for(fmt))
            _save(img, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def grayscale_images(paths, outdir, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            gray = ImageOps.grayscale(img)
            out = _out_path(p, outdir, "_gray", ext_for(fmt))
            _save(gray, out, fmt, 90)
            return out
    return _run_batch(paths, do, progress)


def adjust_images(paths, outdir, brightness=1.0, contrast=1.0, saturation=1.0,
                  sharpness=1.0, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            if float(brightness) != 1.0:
                img = ImageEnhance.Brightness(img).enhance(float(brightness))
            if float(contrast) != 1.0:
                img = ImageEnhance.Contrast(img).enhance(float(contrast))
            if float(saturation) != 1.0:
                img = ImageEnhance.Color(img).enhance(float(saturation))
            if float(sharpness) != 1.0:
                img = ImageEnhance.Sharpness(img).enhance(float(sharpness))
            out = _out_path(p, outdir, "_enhanced", ext_for(fmt))
            _save(img, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


_POS = {
    "top-left": ("left", "top"), "top-center": ("center", "top"),
    "top-right": ("right", "top"), "middle": ("center", "middle"),
    "bottom-left": ("left", "bottom"), "bottom-center": ("center", "bottom"),
    "bottom-right": ("right", "bottom"),
}


def watermark_images(paths, outdir, text="PageDeck", position="bottom-right",
                     opacity=0.55, fontsize=None, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            base = img.convert("RGBA")
            w, h = base.size
            fs = int(fontsize or max(14, w // 26))
            try:
                font = ImageFont.truetype("segoeui.ttf", fs)
            except Exception:
                font = ImageFont.load_default()
            layer = Image.new("RGBA", base.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(layer)
            bbox = d.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            ha, va = _POS.get(position, _POS["bottom-right"])
            margin = max(10, w // 45)
            if ha == "left":
                x = margin
            elif ha == "right":
                x = w - tw - margin
            else:
                x = (w - tw) // 2
            if va == "top":
                y = margin
            elif va == "bottom":
                y = h - th - margin
            else:
                y = (h - th) // 2
            d.text((x - bbox[0], y - bbox[1]), text, font=font,
                   fill=(255, 255, 255, int(255 * float(opacity))),
                   stroke_width=max(1, fs // 16),
                   stroke_fill=(0, 0, 0, int(210 * float(opacity))))
            out_img = Image.alpha_composite(base, layer)
            out = _out_path(p, outdir, "_wm", ext_for(fmt))
            _save(out_img, out, fmt, 95)
            return out
    return _run_batch(paths, do, progress)


def trim_images(paths, outdir, threshold=245, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            rgb = _flatten(ImageOps.exif_transpose(img))
            gray = rgb.convert("L").point(lambda v: 0 if v >= threshold else 255)
            bbox = gray.getbbox()
            if bbox and bbox[2] - bbox[0] > 4 and bbox[3] - bbox[1] > 4:
                m = 4
                box = (max(0, bbox[0] - m), max(0, bbox[1] - m),
                       min(rgb.width, bbox[2] + m), min(rgb.height, bbox[3] + m))
                rgb = rgb.crop(box)
            out = _out_path(p, outdir, "_trimmed", ext_for(fmt))
            _save(rgb, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def strip_exif(paths, outdir=None, autorotate=True, progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            if autorotate:
                img = ImageOps.exif_transpose(img)
            clean = img.copy()
            out = _out_path(p, outdir or os.path.dirname(p), "_clean", ext_for(fmt))
            _save(clean, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def add_border(paths, outdir, width=24, color="#ffffff", progress=None):
    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            pad = ImageOps.expand(img, border=int(width), fill=color)
            out = _out_path(p, outdir, "_border", ext_for(fmt))
            _save(pad, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def to_ico(paths, outdir, progress=None):
    sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    def do(p):
        with Image.open(p) as img:
            base = _flatten(ImageOps.exif_transpose(img))
            out = _out_path(p, outdir, "", ".ico")
            base.save(out, "ICO", sizes=sizes)
            return out
    return _run_batch(paths, do, progress)


# ───────────────────────── images -> PDF ─────────────────────────
def images_to_pdf(paths, out, page="fit", bg=(255, 255, 255), dpi=150, progress=None):
    """page: 'fit' (page follows image size) or 'A4' / 'Letter'."""
    pages = []
    total = len(paths)
    for i, p in enumerate(paths):
        with Image.open(p) as img:
            rgb = _flatten(ImageOps.exif_transpose(img), bg)
            if str(page) == "fit":
                pages.append(rgb.copy())
            else:
                if str(page).upper() == "A4":
                    pw, ph = int(8.27 * dpi), int(11.69 * dpi)
                else:
                    pw, ph = int(8.5 * dpi), int(11 * dpi)
                margin = int(0.4 * dpi)
                canvas = Image.new("RGB", (pw, ph), bg)
                avail_w, avail_h = pw - 2 * margin, ph - 2 * margin
                sc = min(avail_w / float(rgb.width), avail_h / float(rgb.height))
                nw, nh = max(1, int(rgb.width * sc)), max(1, int(rgb.height * sc))
                small = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                canvas.paste(small, ((pw - nw) // 2, (ph - nh) // 2))
                pages.append(canvas)
        if progress:
            progress(i + 1, total)
    if not pages:
        raise ValueError("No images provided")
    res = 72.0 if str(page) == "fit" else float(dpi)
    pages[0].save(out, "PDF", resolution=res, save_all=True, append_images=pages[1:])
    return out


# ───────────────────────── batch rename ─────────────────────────
def rename_plan(paths, pattern="{name}_{n}", start=1, pad=3):
    plan = []
    for i, p in enumerate(paths):
        d = os.path.dirname(p)
        stem = os.path.splitext(os.path.basename(p))[0]
        ext = os.path.splitext(p)[1]
        name = (str(pattern or "{name}_{n}")
                .replace("{name}", stem)
                .replace("{n}", str(start + i).zfill(int(pad or 0)))
                .replace("{date}", datetime.now().strftime("%Y%m%d")))
        plan.append((p, os.path.join(d, name + ext)))
    return plan


def rename_batch(paths, pattern="{name}_{n}", start=1, pad=3, progress=None):
    plan = rename_plan(paths, pattern, start, pad)
    tmps = []
    results = [None] * len(plan)
    for i, (src, dst) in enumerate(plan):
        if os.path.abspath(src) == os.path.abspath(dst):
            tmps.append(None)
            results[i] = (src, dst, None)
            continue
        t = "%s.__tmp%d" % (dst, i)
        try:
            os.rename(src, t)
            tmps.append(t)
        except OSError as e:
            tmps.append(None)
            results[i] = (src, None, str(e))
    for i, (src, dst) in enumerate(plan):
        t = tmps[i]
        if results[i] is not None:
            continue
        try:
            os.rename(t, dst)
            results[i] = (src, dst, None)
        except OSError as e:
            try:
                os.rename(t, src)
            except OSError:
                pass
            results[i] = (src, None, str(e))
        if progress:
            progress(i + 1, len(plan))
    return results


# ═══════════════════ v5.0 additions ═══════════════════

def _hex_rgb(color, default=(255, 255, 255)):
    try:
        c = str(color or "").strip().lstrip("#")
        if len(c) == 3:
            c = "".join(ch * 2 for ch in c)
        if len(c) == 6:
            return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    except Exception:
        pass
    return default


def scan_cleanup(path, out, corners=None, whiten=True, despeckle=True):
    """Straighten a photographed/scanned page.

    corners: 4 (fx, fy) fractions in TL, TR, BR, BL order (0..1).
    Applies a perspective correction, whitening and light despeckling.
    """
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
        if corners:
            w, h = img.size
            pts = [(max(0.0, min(1.0, fx)) * w, max(0.0, min(1.0, fy)) * h)
                   for fx, fy in corners]
            if len(pts) == 4:
                tl, tr, br, bl = pts
                flat = [tl[0], tl[1], bl[0], bl[1], br[0], br[1], tr[0], tr[1]]
                img = img.transform((w, h), Image.Transform.QUAD, flat,
                                    Image.Resampling.BICUBIC)
        if whiten:
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Brightness(img).enhance(1.03)
        if despeckle:
            if img.width * img.height <= 16_000_000:
                img = img.filter(ImageFilter.MedianFilter(size=3))
            img = img.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=4))
        fmt = _ext_format(path)
        out = out or _out_path(path, os.path.dirname(path), "_scan", ext_for(fmt))
        _save(img, out, fmt, 92)
        return out


def remove_background(path, out, tolerance=40, progress=None):
    """Remove a solid background starting from the image borders (transparent PNG)."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGBA")
        w, h = img.size
        mx, my = max(1, w // 2), max(1, h // 2)
        for xy in [(0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1),
                   (mx, 0), (0, my), (mx, h - 1), (w - 1, my)]:
            try:
                ImageDraw.floodfill(img, xy, (0, 0, 0, 0), thresh=int(tolerance))
            except Exception:
                pass
        out = out or _out_path(path, os.path.dirname(path), "_nobg", ".png")
        _save(img, out, "PNG")
        return out


SOCIAL_PRESETS = [
    ("Instagram post 1080x1080", 1080, 1080),
    ("Instagram portrait 1080x1350", 1080, 1350),
    ("Story / Reels 1080x1920", 1080, 1920),
    ("YouTube thumbnail 1280x720", 1280, 720),
    ("Facebook cover 820x312", 820, 312),
    ("Twitter/X 1600x900", 1600, 900),
    ("WhatsApp status 1080x1920", 1080, 1920),
    ("LinkedIn post 1200x1200", 1200, 1200),
]


def social_export(paths, outdir, size=(1080, 1080), mode="fill", bg=(255, 255, 255),
                  label="social", progress=None):
    """Export images at social-media sizes. mode: 'fill' (center-crop) or 'fit' (pad)."""
    os.makedirs(outdir, exist_ok=True)
    tw, th = int(size[0]), int(size[1])

    def do(p):
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            rgb = _flatten(img, bg)
            if str(mode) == "fill":
                sc = max(tw / float(rgb.width), th / float(rgb.height))
                nw, nh = max(1, int(rgb.width * sc)), max(1, int(rgb.height * sc))
                rs = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                left = (nw - tw) // 2
                top = (nh - th) // 2
                canvas = rs.crop((left, top, left + tw, top + th))
            else:
                sc = min(tw / float(rgb.width), th / float(rgb.height))
                nw, nh = max(1, int(rgb.width * sc)), max(1, int(rgb.height * sc))
                rs = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
                canvas = Image.new("RGB", (tw, th), bg)
                canvas.paste(rs, ((tw - nw) // 2, (th - nh) // 2))
            out = _out_path(p, outdir, "_%s" % label, ".jpg")
            _save(canvas, out, "JPEG", 92)
            return out
    return _run_batch(paths, do, progress)


def collage(paths, out, cols=0, rows=0, cell=600, spacing=12, bg="#ffffff",
            radius=0, progress=None):
    """Build a grid collage from images."""
    if not paths:
        raise ValueError("No images provided")
    _d = os.path.dirname(out)
    if _d:
        os.makedirs(_d, exist_ok=True)
    n = len(paths)
    cols = int(cols or 0)
    rows = int(rows or 0)
    if cols <= 0 and rows <= 0:
        cols = int(n ** 0.5)
        if cols * cols < n:
            cols += 1
        rows = (n + cols - 1) // cols
    elif cols <= 0:
        cols = (n + rows - 1) // rows
    elif rows <= 0:
        rows = (n + cols - 1) // cols
    cell = max(64, int(cell))
    spacing = max(0, int(spacing))
    radius = max(0, int(radius))
    bg_rgb = _hex_rgb(bg, (255, 255, 255))
    W = cols * cell + (cols + 1) * spacing
    H = rows * cell + (rows + 1) * spacing
    canvas = Image.new("RGB", (W, H), bg_rgb)
    total = n
    for i, p in enumerate(paths):
        r, c = divmod(i, cols)
        if r >= rows:
            break
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            rgb = _flatten(img, (255, 255, 255))
            sc = max(cell / float(rgb.width), cell / float(rgb.height))
            nw, nh = max(1, int(rgb.width * sc)), max(1, int(rgb.height * sc))
            rs = rgb.resize((nw, nh), Image.Resampling.LANCZOS)
            left = (nw - cell) // 2
            top = (nh - cell) // 2
            tile = rs.crop((left, top, left + cell, top + cell)).convert("RGBA")
            if radius > 0:
                mask = Image.new("L", (cell * 4, cell * 4), 0)
                ImageDraw.Draw(mask).rounded_rectangle(
                    [0, 0, cell * 4 - 1, cell * 4 - 1], radius=radius * 4, fill=255)
                mask = mask.resize((cell, cell), Image.Resampling.LANCZOS)
                tile.putalpha(mask)
            x = spacing + c * (cell + spacing)
            y = spacing + r * (cell + spacing)
            canvas.paste(tile, (x, y), tile)
        if progress:
            progress(i + 1, total)
    fmt = _ext_format(out)
    _save(canvas, out, fmt, 92)
    return out


def _vignette(img, strength=0.45):
    w, h = img.size
    mask = Image.new("L", (w, h), 0)
    d = ImageDraw.Draw(mask)
    d.ellipse([-w * 0.25, -h * 0.25, w * 1.25, h * 1.25], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(max(w, h) / 12.0))
    dark = Image.new("RGB", (w, h), (0, 0, 0))
    return Image.composite(img, Image.blend(img, dark, strength), mask)


def _channel_shift(img, r=1.0, g=1.0, b=1.0):
    rr, gg, bb = img.split()
    rr = rr.point(lambda v: min(255, int(v * r)))
    gg = gg.point(lambda v: min(255, int(v * g)))
    bb = bb.point(lambda v: min(255, int(v * b)))
    return Image.merge("RGB", (rr, gg, bb))


FILTERS = ["B&W", "Warm", "Cool", "Vintage", "Vignette", "Clarity"]


def apply_filter(paths, outdir, preset="B&W", progress=None):
    """Apply a quick look. preset: B&W, Warm, Cool, Vintage, Vignette, Clarity."""
    os.makedirs(outdir, exist_ok=True)
    preset = str(preset)

    def do(p):
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img).convert("RGB")
            if preset == "B&W":
                img = ImageOps.autocontrast(ImageOps.grayscale(img)).convert("RGB")
            elif preset == "Warm":
                img = _channel_shift(img, 1.08, 1.0, 0.90)
            elif preset == "Cool":
                img = _channel_shift(img, 0.90, 1.0, 1.10)
            elif preset == "Vintage":
                img = ImageEnhance.Contrast(img).enhance(0.92)
                img = _channel_shift(img, 1.10, 1.0, 0.82)
                img = _vignette(img, 0.40)
            elif preset == "Vignette":
                img = _vignette(img, 0.5)
            elif preset == "Clarity":
                img = img.filter(ImageFilter.UnsharpMask(radius=3, percent=140, threshold=4))
            fmt = _ext_format(p)
            out = _out_path(p, outdir, "_" + preset.replace("&", "").replace(" ", "").lower(),
                            ext_for(fmt))
            _save(img, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def exif_read(path):
    """[(label, value)] readable EXIF tags."""
    out = []
    try:
        with Image.open(path) as img:
            exif = img.getexif()
            if exif:
                for k, v in exif.items():
                    try:
                        from PIL.ExifTags import TAGS
                        label = TAGS.get(k, "Tag%s" % k)
                    except Exception:
                        label = "Tag%s" % k
                    if isinstance(v, bytes):
                        v = "<%d bytes>" % len(v)
                    out.append((str(label), str(v)))
    except Exception:
        pass
    return out


def exif_remove_gps(path, out=None):
    """Strip GPS coordinates but keep the other EXIF data (JPEG/TIFF)."""
    with Image.open(path) as img:
        fmt = _ext_format(path)
        exif = None
        try:
            exif = img.getexif()
            if 34853 in exif:
                del exif[34853]
        except Exception:
            exif = None
        out = out or _out_path(path, os.path.dirname(path), "_nogps", ext_for(fmt))
        if norm_format(fmt) in ("JPEG", "TIFF") and exif is not None:
            data = None
            try:
                data = exif.tobytes()
            except Exception:
                data = None
            if norm_format(fmt) == "JPEG":
                _flatten(ImageOps.exif_transpose(img)).save(
                    out, "JPEG", quality=92, exif=data or b"")
            else:
                img.save(out, "TIFF", compression="tiff_deflate", exif=data or b"")
        else:
            img.save(out, fmt)
        return out


def upscale(paths, outdir, factor=2, max_pixels=40_000_000, progress=None):
    """Simple high-quality enlargement (Lanczos + sharpen)."""
    os.makedirs(outdir, exist_ok=True)

    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            f = float(factor or 2)
            px = img.width * img.height
            if px * f * f > max_pixels:
                f = max(1.0, (max_pixels / float(px)) ** 0.5)
            nw = max(1, int(img.width * f))
            nh = max(1, int(img.height * f))
            big = img.resize((nw, nh), Image.Resampling.LANCZOS)
            big = big.filter(ImageFilter.UnsharpMask(radius=1.6, percent=90, threshold=3))
            out = _out_path(p, outdir, "_%dx" % int(round(f)), ext_for(fmt))
            _save(big, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def batch_crop(paths, outdir, left=0, top=0, right=0, bottom=0, progress=None):
    """Crop the same percentage off each side of every image."""
    os.makedirs(outdir, exist_ok=True)
    left = max(0.0, min(45.0, float(left or 0)))
    top = max(0.0, min(45.0, float(top or 0)))
    right = max(0.0, min(45.0, float(right or 0)))
    bottom = max(0.0, min(45.0, float(bottom or 0)))

    def do(p):
        fmt = _ext_format(p)
        with Image.open(p) as img:
            img = ImageOps.exif_transpose(img)
            w, h = img.size
            x0 = int(w * left / 100.0)
            y0 = int(h * top / 100.0)
            x1 = w - int(w * right / 100.0)
            y1 = h - int(h * bottom / 100.0)
            if x1 - x0 < 10 or y1 - y0 < 10:
                raise ValueError("Crop leaves nothing - reduce the percentages")
            cropped = img.crop((x0, y0, x1, y1))
            out = _out_path(p, outdir, "_cropped", ext_for(fmt))
            _save(cropped, out, fmt, 92)
            return out
    return _run_batch(paths, do, progress)


def annotate_image(path, out, ops):
    """Draw annotations. ops: [{type: rect|arrow|text|blur|highlight, ...}] with
    fractional coordinates (0..1). Blur boxes are pixelated for privacy."""
    with Image.open(path) as img:
        img = ImageOps.exif_transpose(img).convert("RGB")
        w, h = img.size
        stroke = max(2, int(round(min(w, h) / 300.0)))

        def box_of(op):
            x0, y0, x1, y1 = op["box"]
            return (int(min(x0, x1) * w), int(min(y0, y1) * h),
                    int(max(x0, x1) * w), int(max(y0, y1) * h))

        for op in ops or []:
            t = str(op.get("type", "")).lower()
            color = _hex_rgb(op.get("color", "#ff3b30"), (255, 59, 48))
            width = int(op.get("width") or stroke)
            if t == "rect":
                ImageDraw.Draw(img).rectangle(box_of(op), outline=color, width=width)
            elif t == "highlight":
                region = box_of(op)
                overlay = img.crop(region).convert("RGBA")
                tint = Image.new("RGBA", overlay.size, color + (90,))
                overlay = Image.alpha_composite(overlay, tint)
                img.paste(overlay.convert("RGB"), (region[0], region[1]))
            elif t == "blur":
                region = box_of(op)
                patch = img.crop(region)
                small = max(8, int(min(patch.size) / 12))
                bw, bh = max(1, patch.width // small), max(1, patch.height // small)
                patch = patch.resize((bw, bh), Image.Resampling.NEAREST)
                patch = patch.resize((region[2] - region[0], region[3] - region[1]),
                                     Image.Resampling.NEAREST)
                img.paste(patch, (region[0], region[1]))
            elif t == "arrow":
                x0, y0, x1, y1 = op.get("points", (0, 0, 0, 0))
                p0 = (int(x0 * w), int(y0 * h))
                p1 = (int(x1 * w), int(y1 * h))
                d = ImageDraw.Draw(img)
                d.line([p0, p1], fill=color, width=width)
                import math
                ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
                hl = max(10, width * 4)
                for da in (0.5, -0.5):
                    d.line([p1, (int(p1[0] - hl * math.cos(ang + da)),
                                 int(p1[1] - hl * math.sin(ang + da)))],
                           fill=color, width=width)
            elif t == "text":
                x, y = op.get("at", (0.05, 0.05))
                text = str(op.get("text", ""))
                size = int(op.get("size") or max(16, h // 28))
                font = None
                for fp_name in ("arial.ttf", "segoeui.ttf", "calibri.ttf"):
                    try:
                        font = ImageFont.truetype(fp_name, size)
                        break
                    except Exception:
                        continue
                if font is None:
                    font = ImageFont.load_default()
                d = ImageDraw.Draw(img)
                pt = (int(x * w), int(y * h))
                if op.get("shadow", True):
                    d.text((pt[0] + 2, pt[1] + 2), text, font=font, fill=(0, 0, 0))
                d.text(pt, text, font=font, fill=color)
        fmt = _ext_format(out)
        _save(img, out, fmt, 92)
        return out

