"""Image feature engine - pure logic, no UI imports (used by app + CLI)."""
import os
from datetime import datetime
from PIL import Image, ImageEnhance, ImageOps, ImageDraw, ImageFont

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


def watermark_images(paths, outdir, text="PDF Suite Pro", position="bottom-right",
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

