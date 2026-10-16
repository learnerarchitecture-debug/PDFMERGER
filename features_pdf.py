"""PDF feature engine - pure logic, no UI imports (used by app + CLI)."""
import os, re, io, csv, tempfile, difflib
from datetime import datetime
import fitz

MM = 72 / 25.4  # mm -> points


# ───────────────────────── helpers ─────────────────────────
def parse_page_range(text, total):
    if not text or text.strip() == "all":
        return list(range(1, total + 1))
    result = set()
    for part in text.replace(" ", "").split(","):
        if not part:
            continue
        if "-" in part:
            a, b = part.split("-", 1)
            s, e = int(a), int(b)
            if s < 1 or e > total:
                raise ValueError("Range %s out of bounds (1-%d)" % (part, total))
            result.update(range(s, e + 1))
        else:
            v = int(part)
            if v < 1 or v > total:
                raise ValueError("Page %d out of bounds (1-%d)" % (v, total))
            result.add(v)
    return sorted(result)


def _save(doc, out, compress=True, password=None):
    doc.save(out,
        encryption=fitz.PDF_ENCRYPT_AES_256 if password else 0,
        user_pw=password or None, owner_pw=password or None,
        garbage=4 if compress else 1, deflate=compress)


def _outdir_path(path, outdir, suffix="", ext=".pdf"):
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(outdir, base + suffix + ext)


def _font(fontsize, fontname="helv"):
    return fontname, fontsize


def _text_png_bytes(text, fontsize=40, color=(0.6, 0.6, 0.6), opacity=0.30,
                    rotation=35, size=(900, 700), tiled=False):
    """Render watermark text onto a transparent RGBA PNG (bytes)."""
    from PIL import Image, ImageDraw, ImageFont
    rgb = tuple(int(255 * c) for c in color[:3])
    alpha = max(0, min(255, int(255 * opacity)))
    try:
        font = ImageFont.truetype("segoeui.ttf", fontsize)
    except Exception:
        font = ImageFont.load_default()
    probe = Image.new("RGBA", (10, 10))
    d0 = ImageDraw.Draw(probe)
    bbox = d0.textbbox((0, 0), text, font=font)
    tw, th = max(1, bbox[2] - bbox[0]), max(1, bbox[3] - bbox[1])
    tile = Image.new("RGBA", (tw + 24, th + 24), (0, 0, 0, 0))
    td = ImageDraw.Draw(tile)
    td.text((12 - bbox[0], 12 - bbox[1]), text, font=font, fill=rgb + (alpha,))
    if rotation:
        tile = tile.rotate(rotation, expand=True, resample=Image.Resampling.BICUBIC)
    img = Image.new("RGBA", size, (0, 0, 0, 0))
    if tiled:
        step_x, step_y = tile.width + 40, tile.height + 40
        for y in range(0, size[1] + step_y, step_y):
            for x in range(0, size[0] + step_x, step_x):
                img.alpha_composite(tile, (x, y))
    else:
        img.alpha_composite(tile, ((size[0] - tile.width) // 2, (size[1] - tile.height) // 2))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


_POS_RECTS = {
    # (h_align, v_align): fraction of page for box placement
    "top-left": (0.02, 0.02, "left", "top"),
    "top-center": (0.5, 0.03, "center", "top"),
    "top-right": (0.98, 0.02, "right", "top"),
    "middle": (0.5, 0.5, "center", "middle"),
    "bottom-left": (0.02, 0.97, "left", "bottom"),
    "bottom-center": (0.5, 0.97, "center", "bottom"),
    "bottom-right": (0.98, 0.97, "right", "bottom"),
}


def _align_rect(page_rect, position, box_w, box_h, margin=24):
    fx, fy, ha, va = _POS_RECTS.get(position, _POS_RECTS["bottom-center"])
    if ha == "left":
        x0 = margin
    elif ha == "right":
        x0 = page_rect.width - box_w - margin
    else:
        x0 = (page_rect.width - box_w) / 2
    if va == "top":
        y0 = margin
    elif va == "bottom":
        y0 = page_rect.height - box_h - margin
    else:
        y0 = (page_rect.height - box_h) / 2
    return fitz.Rect(x0, y0, x0 + box_w, y0 + box_h)


def _insert_text_stamp(page, text, position="bottom-center", fontsize=10,
                       color=(0.2, 0.2, 0.2), margin=24):
    r = page.rect
    box_w, box_h = r.width - 2 * margin, fontsize * 2.2
    rect = _align_rect(r, position, box_w, box_h, margin)
    align = fitz.TEXT_ALIGN_CENTER
    if position.endswith("left"):
        align = fitz.TEXT_ALIGN_LEFT
    elif position.endswith("right"):
        align = fitz.TEXT_ALIGN_RIGHT
    page.insert_textbox(rect, text, fontsize=fontsize, fontname="helv",
                        color=color, align=align)


# ───────────────────────── core operations ─────────────────────────
def merge_pdfs(files, out, compress=True, password=None, progress=None):
    """files: list of dicts {path, pages} (pages='all' or '1-3,5')."""
    writer = fitz.open()
    try:
        for idx, f in enumerate(files):
            src = fitz.open(f["path"])
            if src.is_encrypted:
                raise ValueError("Encrypted file: %s" % f["path"])
            pgs = parse_page_range(f.get("pages", "all"), len(src))
            for p in pgs:
                writer.insert_pdf(src, from_page=p - 1, to_page=p - 1)
            src.close()
            if progress:
                progress(idx + 1, len(files))
        _save(writer, out, compress, password)
        return out
    finally:
        writer.close()


def pdf_grayscale(path, out, dpi=150, progress=None):
    """Rasterize to grayscale JPEG pages (true grayscale output)."""
    from PIL import Image
    src = fitz.open(path)
    nd = fitz.open()
    try:
        total = len(src)
        for i in range(total):
            pix = src[i].get_pixmap(dpi=dpi, colorspace=fitz.csGRAY)
            img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=85, optimize=True)
            page = nd.new_page(width=src[i].rect.width, height=src[i].rect.height)
            page.insert_image(page.rect, stream=buf.getvalue())
            if progress:
                progress(i + 1, total)
        nd.save(out, garbage=4, deflate=True)
        return out
    finally:
        src.close()
        nd.close()


def protect_pdf(path, out, password):
    doc = fitz.open(path)
    try:
        doc.save(out, encryption=fitz.PDF_ENCRYPT_AES_256,
                 user_pw=password, owner_pw=password, garbage=4, deflate=True)
        return out
    finally:
        doc.close()


def unlock_pdf(path, out, password):
    doc = fitz.open(path)
    try:
        if doc.is_encrypted:
            if doc.authenticate(password) == 0:
                raise ValueError("Incorrect password")
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def compress_pdf(path, out, level="medium", progress=None):
    """level: low | medium | high | max"""
    doc = fitz.open(path)
    try:
        if level == "low":
            opts = dict(garbage=4, deflate=False)
        elif level == "max":
            opts = dict(garbage=4, deflate=True, clean=True)
        else:
            opts = dict(garbage=4, deflate=True)
        doc.save(out, **opts)
        return out
    finally:
        doc.close()


def pdf_to_images(path, outdir, fmt="png", dpi=150, progress=None):
    from PIL import Image
    doc = fitz.open(path)
    base = os.path.splitext(os.path.basename(path))[0]
    outs = []
    try:
        total = len(doc)
        for i in range(total):
            pix = doc[i].get_pixmap(dpi=dpi)
            name = "%s_p%03d.%s" % (base, i + 1, fmt.lower())
            fp = os.path.join(outdir, name)
            if fmt.lower() in ("jpg", "jpeg"):
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                img.save(fp, "JPEG", quality=88, optimize=True)
            elif fmt.lower() == "webp":
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                img.save(fp, "WEBP", quality=88)
            else:
                pix.save(fp)
            outs.append(fp)
            if progress:
                progress(i + 1, total)
        return outs
    finally:
        doc.close()


def print_pdf(path):
    os.startfile(path, "print")


# ───────────────────────── stamps & watermarks ─────────────────────────
def watermark_pdf(path, out, text="CONFIDENTIAL", fontsize=40, opacity=0.30,
                  rotation=35, tiled=False, image_path=None, image_scale=0.35,
                  progress=None):
    doc = fitz.open(path)
    try:
        total = len(doc)
        for i in range(total):
            page = doc[i]
            if image_path:
                from PIL import Image as _I
                with _I.open(image_path) as im:
                    ar = im.height / float(im.width)
                w = page.rect.width * image_scale
                h = w * ar
                rect = fitz.Rect((page.rect.width - w) / 2, (page.rect.height - h) / 2,
                                 (page.rect.width + w) / 2, (page.rect.height + h) / 2)
                page.insert_image(rect, filename=image_path, overlay=True)
            else:
                png = _text_png_bytes(text, fontsize=fontsize, opacity=opacity,
                                      rotation=rotation,
                                      size=(int(page.rect.width) or 900,
                                            int(page.rect.height) or 700),
                                      tiled=tiled)
                page.insert_image(page.rect, stream=png, overlay=True)
            if progress:
                progress(i + 1, total)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def header_footer_pdf(path, out, fmt="{page} / {total}", position="bottom-center",
                      fontsize=10, progress=None):
    doc = fitz.open(path)
    try:
        total = len(doc)
        fname = os.path.splitext(os.path.basename(path))[0]
        today = datetime.now().strftime("%Y-%m-%d")
        for i in range(total):
            text = (fmt.replace("{page}", str(i + 1)).replace("{total}", str(total))
                       .replace("{date}", today).replace("{filename}", fname))
            _insert_text_stamp(doc[i], text, position, fontsize)
            if progress:
                progress(i + 1, total)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def bates_pdf(path, out, prefix="", start=1, digits=6, position="bottom-right",
              fontsize=9, progress=None):
    doc = fitz.open(path)
    try:
        total = len(doc)
        for i in range(total):
            text = "%s%0*d" % (prefix, digits, start + i)
            _insert_text_stamp(doc[i], text, position, fontsize)
            if progress:
                progress(i + 1, total)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def qr_stamp_pdf(path, out, data, position="bottom-right", size_mm=28,
                 margin=24, progress=None):
    from PIL import Image
    import qrcode as _qr
    q = _qr.QRCode(border=1)
    q.add_data(data)
    q.make(fit=True)
    mat = q.get_matrix()
    n = len(mat)
    img = Image.new("RGB", (n, n), "white")
    px = img.load()
    for y, row in enumerate(mat):
        for x, val in enumerate(row):
            if val:
                px[x, y] = (0, 0, 0)
    img = img.resize((max(n * 8, 240), max(n * 8, 240)), Image.Resampling.NEAREST)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    png = buf.getvalue()
    doc = fitz.open(path)
    try:
        total = len(doc)
        for i in range(total):
            side = size_mm * MM
            rect = _align_rect(doc[i].rect, position, side, side, margin)
            doc[i].insert_image(rect, stream=png, overlay=True)
            if progress:
                progress(i + 1, total)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


# ───────────────────────── signature placement ─────────────────────────
def render_page_image(path, page_index, width=700):
    """Return (png_bytes, page_w_pt, page_h_pt) preview of one page."""
    doc = fitz.open(path)
    try:
        idx = max(0, min(page_index, len(doc) - 1))
        page = doc[idx]
        zoom = width / page.rect.width
        pix = page.get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png"), page.rect.width, page.rect.height
    finally:
        doc.close()


def place_signature_pdf(path, out, sig_png, cx=0.75, cy=0.90, width_frac=0.30,
                        page_index=-1):
    from PIL import Image
    with Image.open(sig_png) as im:
        ar = im.height / float(im.width)
    doc = fitz.open(path)
    try:
        total = len(doc)
        idx = total - 1 if page_index in (-1, None) else max(0, min(int(page_index), total - 1))
        page = doc[idx]
        w = page.rect.width * max(0.05, min(0.9, float(width_frac)))
        h = w * ar
        x0 = page.rect.width * float(cx) - w / 2
        y0 = page.rect.height * float(cy) - h / 2
        x0 = max(4, min(page.rect.width - w - 4, x0))
        y0 = max(4, min(page.rect.height - h - 4, y0))
        page.insert_image(fitz.Rect(x0, y0, x0 + w, y0 + h), filename=sig_png, overlay=True)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


# ───────────────────────── page geometry ─────────────────────────
A4 = (595.28, 841.89)
LETTER = (612.0, 792.0)


def normalize_pages(path, out, size="A4", orientation="auto", progress=None):
    w, h = A4 if str(size).upper() == "A4" else LETTER
    src = fitz.open(path)
    nd = fitz.open()
    try:
        total = len(src)
        for i in range(total):
            r = src[i].rect
            landscape = (orientation == "landscape") or (orientation == "auto" and r.width > r.height)
            pw, ph = (h, w) if landscape else (w, h)
            page = nd.new_page(width=pw, height=ph)
            sc = min(pw / r.width, ph / r.height)
            tw, th = r.width * sc, r.height * sc
            target = fitz.Rect((pw - tw) / 2, (ph - th) / 2, (pw + tw) / 2, (ph + th) / 2)
            page.show_pdf_page(target, src, i)
            if progress:
                progress(i + 1, total)
        nd.save(out, garbage=4, deflate=True)
        return out
    finally:
        src.close()
        nd.close()


def trim_margins(path, out, threshold=247, progress=None):
    from PIL import Image
    src = fitz.open(path)
    try:
        total = len(src)
        for i in range(total):
            page = src[i]
            pix = page.get_pixmap(dpi=80)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples).convert("L")
            inv = img.point(lambda p: 0 if p >= threshold else 255)
            bbox = inv.getbbox()
            if bbox and (bbox[2] - bbox[0] > 4) and (bbox[3] - bbox[1] > 4):
                sx = page.rect.width / pix.width
                sy = page.rect.height / pix.height
                m = 6
                r = fitz.Rect(max(0, bbox[0] - m) * sx, max(0, bbox[1] - m) * sy,
                              min(pix.width, bbox[2] + m) * sx, min(pix.height, bbox[3] + m) * sy)
                r = r & page.rect
                if r.width > 20 and r.height > 20:
                    page.set_cropbox(r)
            if progress:
                progress(i + 1, total)
        _save(src, out, True)
        return out
    finally:
        src.close()


def crop_margins(path, out, left=0, right=0, top=0, bottom=0, progress=None):
    doc = fitz.open(path)
    try:
        for i, page in enumerate(doc):
            r = page.rect
            nr = fitz.Rect(r.x0 + left * MM, r.y0 + top * MM,
                           r.x1 - right * MM, r.y1 - bottom * MM)
            if nr.width > 10 and nr.height > 10:
                page.set_cropbox(nr)
            if progress:
                progress(i + 1, len(doc))
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def nup_pdf(path, out, n=2, orientation="portrait", page_size="A4", gap=6, progress=None):
    w, h = A4 if str(page_size).upper() == "A4" else LETTER
    if orientation == "landscape":
        w, h = h, w
    if n == 2:
        rows, cols = (1, 2) if w > h else (2, 1)
    elif n == 6:
        rows, cols = 3, 2
    else:
        rows, cols, n = 2, 2, 4
    cw = (w - gap * (cols + 1)) / cols
    ch = (h - gap * (rows + 1)) / rows
    src = fitz.open(path)
    nd = fitz.open()
    try:
        total = len(src)
        for start in range(0, total, n):
            page = nd.new_page(width=w, height=h)
            for k in range(n):
                idx = start + k
                if idx >= total:
                    break
                r_, c_ = divmod(k, cols)
                x0 = gap + c_ * (cw + gap)
                y0 = gap + r_ * (ch + gap)
                sr = src[idx].rect
                sc = min(cw / sr.width, ch / sr.height)
                tw, th = sr.width * sc, sr.height * sc
                target = fitz.Rect(x0 + (cw - tw) / 2, y0 + (ch - th) / 2,
                                   x0 + (cw + tw) / 2, y0 + (ch + th) / 2)
                page.show_pdf_page(target, src, idx)
            if progress:
                progress(min(start + n, total), total)
        nd.save(out, garbage=4, deflate=True)
        return out
    finally:
        src.close()
        nd.close()


# ───────────────────────── bookmarks & metadata ─────────────────────────
def page_count(path):
    doc = fitz.open(path)
    try:
        return len(doc)
    finally:
        doc.close()


def file_has_forms(path):
    doc = fitz.open(path)
    try:
        for page in doc:
            for _w in page.widgets():
                return True
        return False
    finally:
        doc.close()


def get_bookmarks(path):
    doc = fitz.open(path)
    try:
        return doc.get_toc(simple=True)
    finally:
        doc.close()


def set_bookmarks(path, out, toc):
    doc = fitz.open(path)
    try:
        doc.set_toc(toc)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def auto_bookmarks(path, out, max_level=2, progress=None):
    """Detect heading-like lines by font size and create bookmarks."""
    doc = fitz.open(path)
    try:
        total = len(doc)
        sizes = []
        for i in range(min(total, 30)):
            d = doc[i].get_text("dict")
            for b in d.get("blocks", []):
                for ln in b.get("lines", []):
                    for sp in ln.get("spans", []):
                        if sp.get("text", "").strip():
                            sizes.append(round(sp["size"], 1))
        if not sizes:
            return None
        sizes.sort()
        body = sizes[len(sizes) // 2]
        toc, seen = [], set()
        for i in range(total):
            d = doc[i].get_text("dict")
            for b in d.get("blocks", []):
                for ln in b.get("lines", []):
                    parts, mx = [], 0.0
                    for sp in ln.get("spans", []):
                        t = sp.get("text", "")
                        if t.strip():
                            parts.append(t)
                            mx = max(mx, sp["size"])
                    text = "".join(parts).strip()
                    if not text or len(text) > 90:
                        continue
                    level = 0
                    if body > 0 and mx >= body * 1.45:
                        level = 1
                    elif body > 0 and mx >= body * 1.18:
                        level = 2 if max_level >= 2 else 1
                    key = (text.lower(), i)
                    if level and level <= max_level and key not in seen:
                        seen.add(key)
                        toc.append([level, text, i + 1])
            if progress:
                progress(i + 1, total)
        if not toc:
            return None
        doc.set_toc(toc)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def get_metadata(path):
    doc = fitz.open(path)
    try:
        return doc.metadata or {}
    finally:
        doc.close()


def set_metadata(path, out, meta):
    doc = fitz.open(path)
    try:
        md = doc.metadata or {}
        for k in ("title", "author", "subject", "keywords"):
            if k in meta:
                md[k] = meta[k]
        doc.set_metadata(md)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def remove_metadata(path, out):
    doc = fitz.open(path)
    try:
        doc.set_metadata({"title": "", "author": "", "subject": "", "keywords": "",
                          "creator": "PDF Suite Pro", "producer": "PDF Suite Pro"})
        _save(doc, out, True)
        return out
    finally:
        doc.close()


# ───────────────────────── compare / sanitize / repair ─────────────────────────
def compare_pdfs(a, b, progress=None):
    """Return (summary, diff_lines)."""
    da, db = fitz.open(a), fitz.open(b)
    try:
        lines = []
        na, nb = len(da), len(db)
        summary = "Pages: A=%d, B=%d" % (na, nb)
        lines.append(summary)
        if na != nb:
            lines.append("! Page count differs")
        same = 0
        for i in range(max(na, nb)):
            ta = da[i].get_text().strip() if i < na else ""
            tb = db[i].get_text().strip() if i < nb else ""
            if ta == tb:
                same += 1
            else:
                lines.append("")
                lines.append("── Page %d differs ──" % (i + 1))
                d = difflib.unified_diff(ta.splitlines(), tb.splitlines(),
                                         "A p%d" % (i + 1), "B p%d" % (i + 1), lineterm="")
                for ln in list(d)[:40]:
                    lines.append(ln)
                if len(lines) > 3000:
                    lines.append("... (truncated)")
                    break
            if progress:
                progress(i + 1, max(na, nb))
        lines.insert(1, "Identical text on %d of %d compared pages" % (same, min(na, nb)))
        if len(lines) <= 2 and na == nb:
            lines.append("No text differences found (visual differences may still exist).")
        return summary, lines
    finally:
        da.close()
        db.close()


def sanitize_pdf(path, out):
    doc = fitz.open(path)
    try:
        try:
            doc.scrub(metadata=False, xml_metadata=True, attached_files=True,
                      embedded_files=True, javascript=True, reset_fields=False)
        except TypeError:
            doc.scrub()
        except AttributeError:
            for name in list(doc.embfile_names()):
                doc.embfile_del(name)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


def repair_pdf(path, out):
    doc = fitz.open(path)
    try:
        _save(doc, out, True)
        return out
    finally:
        doc.close()


# ───────────────────────── split by size / smart compress ─────────────────────────
def split_by_size(path, outdir, max_mb=10, prefix=None, progress=None):
    limit = max_mb * 1024 * 1024
    src = fitz.open(path)
    base = prefix or os.path.splitext(os.path.basename(path))[0]
    outs = []
    part = 1
    chunk = fitz.open()

    def flush():
        nonlocal chunk, part
        if len(chunk) == 0:
            return
        fpath = os.path.join(outdir, "%s_part%02d.pdf" % (base, part))
        chunk.save(fpath, garbage=4, deflate=True)
        outs.append(fpath)
        chunk.close()
        chunk = fitz.open()
        part += 1

    try:
        total = len(src)
        for i in range(total):
            chunk.insert_pdf(src, from_page=i, to_page=i)
            if len(chunk) > 1 and len(chunk.tobytes(garbage=4, deflate=True)) > limit:
                chunk.delete_page(len(chunk) - 1)
                flush()
                chunk.insert_pdf(src, from_page=i, to_page=i)
                if len(chunk.tobytes(garbage=4, deflate=True)) > limit:
                    flush()
            if progress:
                progress(i + 1, total)
        flush()
        return outs
    finally:
        src.close()
        try:
            chunk.close()
        except Exception:
            pass


def compress_to_target(path, out, target_mb=5, progress=None):
    """Try lossless first, then rasterize at decreasing DPI. Returns (out, mode)."""
    target = target_mb * 1024 * 1024
    doc = fitz.open(path)
    try:
        best = doc.tobytes(garbage=4, deflate=True)
        if len(best) <= target:
            with open(out, "wb") as fh:
                fh.write(best)
            return out, "lossless"
    finally:
        doc.close()
    from PIL import Image
    for dpi, q in ((150, 70), (120, 65), (96, 60), (72, 55)):
        src = fitz.open(path)
        nd = fitz.open()
        try:
            for i in range(len(src)):
                pix = src[i].get_pixmap(dpi=dpi)
                img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
                buf = io.BytesIO()
                img.save(buf, "JPEG", quality=q, optimize=True)
                page = nd.new_page(width=src[i].rect.width, height=src[i].rect.height)
                page.insert_image(page.rect, stream=buf.getvalue())
                if progress:
                    progress(i + 1, len(src))
            data = nd.tobytes(garbage=4, deflate=True)
            if len(data) <= target:
                with open(out, "wb") as fh:
                    fh.write(data)
                return out, "rasterized @ %d dpi" % dpi
        finally:
            src.close()
            nd.close()
    src = fitz.open(path)
    nd = fitz.open()
    try:
        for i in range(len(src)):
            pix = src[i].get_pixmap(dpi=60)
            img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=45, optimize=True)
            page = nd.new_page(width=src[i].rect.width, height=src[i].rect.height)
            page.insert_image(page.rect, stream=buf.getvalue())
        data = nd.tobytes(garbage=4, deflate=True)
        with open(out, "wb") as fh:
            fh.write(data)
        return out, "rasterized @ 60 dpi (lowest)"
    finally:
        src.close()
        nd.close()


# ───────────────────────── regex redaction ─────────────────────────
PATTERN_PRESETS = {
    "emails": r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}",
    "phones": r"(?:\+\d{1,3}[\s\-.()]?)?(?:\(?\d{3,5}\)?[\s\-.])?\d{3}[\s\-.]?\d{3,4}",
    "cards": r"\b(?:\d[ \-]?){13,19}\b",
    "aadhaar": r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    "pan": r"\b[A-Z]{5}\d{4}[A-Z]\b",
    "ifsc": r"\b[A-Z]{4}0[A-Z0-9]{6}\b",
}


def auto_redact(path, out, pattern_names=None, custom=None, fill=(0, 0, 0),
                progress=None):
    pats = []
    for name in (pattern_names or []):
        rx = PATTERN_PRESETS.get(name)
        if rx:
            pats.append(re.compile(rx))
    if custom:
        try:
            pats.append(re.compile(custom))
        except re.error:
            pass
    if not pats:
        raise ValueError("No patterns selected")
    doc = fitz.open(path)
    try:
        total = len(doc)
        for i in range(total):
            page = doc[i]
            text = page.get_text()
            found = set()
            for rx in pats:
                for m in rx.finditer(text):
                    s = m.group(0).strip()
                    if s and len(s) > 3 and "\n" not in s:
                        found.add(s)
            count = 0
            for s in found:
                for rect in page.search_for(s):
                    page.add_redact_annot(rect, fill=fill)
                    count += 1
            if count:
                page.apply_redactions()
            if progress:
                progress(i + 1, total)
        _save(doc, out, True)
        return out
    finally:
        doc.close()


# ───────────────────────── CSV mail merge ─────────────────────────
def _lookup(row, name):
    if name is None:
        return None
    nm = name.strip().lower().replace(" ", "_")
    for k, v in row.items():
        if k and k.strip().lower().replace(" ", "_") == nm:
            return str(v) if v is not None else ""
    return None


def mail_merge(template, csv_path, outdir, progress=None, log=None):
    """Fill PDF form fields and {{field}} placeholders from CSV rows."""
    with open(csv_path, "r", encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.DictReader(fh))
    if not rows:
        raise ValueError("CSV has no data rows")
    outs = []
    total = len(rows)
    for ri, row in enumerate(rows):
        doc = fitz.open(template)
        try:
            for page in doc:
                for w in (page.widgets() or []):
                    val = _lookup(row, w.field_name)
                    if val is not None:
                        try:
                            w.field_value = val
                            w.update()
                        except Exception:
                            pass
            placements = []
            for page in doc:
                for key in row.keys():
                    if key is None:
                        continue
                    for pat in ("{{%s}}" % key, "<<%s>>" % key):
                        for rect in page.search_for(pat):
                            placements.append((page, rect, str(row.get(key) or "")))
            for page, rect, val in placements:
                page.add_redact_annot(rect, fill=(1, 1, 1))
            for page in doc:
                page.apply_redactions()
            for page, rect, val in placements:
                fs = min(11, max(6, rect.height * 0.75))
                page.insert_textbox(rect + (-1, -1, 1, 1), val, fontsize=fs,
                                    fontname="helv", color=(0, 0, 0))
            out = _outdir_path(template, outdir, suffix="_%03d" % (ri + 1))
            _save(doc, out, True)
            outs.append(out)
            if log:
                log("Mail-merged %d/%d: %s" % (ri + 1, total, os.path.basename(out)))
            if progress:
                progress(ri + 1, total)
        finally:
            doc.close()
    return outs
