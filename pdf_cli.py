"""PDF Suite Pro - command line companion (built as PDFSuiteCLI.exe).

Examples:
  PDFSuiteCLI.exe merge a.pdf b.pdf -o merged.pdf
  PDFSuiteCLI.exe compress big.pdf --target 5
  PDFSuiteCLI.exe recipe -r myrecipe.json -d "C:\\Scans" -o "C:\\Out"
  PDFSuiteCLI.exe watch -d "C:\\Scans" -r myrecipe.json -o "C:\\Out"
  PDFSuiteCLI.exe schedule --name NightRun --recipe myrecipe.json -d "C:\\Scans" -o "C:\\Out" --time 23:00
"""
import argparse
import os
import sys
import time

import features_pdf as fp
import features_image as fi
import automation as au


def _p(msg):
    print(msg, flush=True)


def _progress(i, n):
    if n:
        pct = int(100.0 * i / n)
        sys.stdout.write("\r  %3d%%" % pct)
        sys.stdout.flush()
        if i >= n:
            sys.stdout.write("\n")


def _ensure_dir(d):
    if d and not os.path.isdir(d):
        os.makedirs(d, exist_ok=True)
    return d


def _default_out(path, suffix, ext=".pdf"):
    base, _ = os.path.splitext(path)
    return base + suffix + ext


def _outdir(a, *paths):
    return _ensure_dir(a.out or (os.path.dirname(paths[0]) if paths else ".") or ".")


def _img_batch(a, runner):
    outs = runner()
    bad = 0
    for src, dst, err in outs:
        if err:
            bad += 1
            _p("ERR %s: %s" % (src, err))
        else:
            _p("OK  %s" % dst)
    return 0 if not bad else 2


# ───────────────────────── command handlers ─────────────────────────
def cmd_merge(a):
    files = [{"path": p, "pages": a.pages or "all"} for p in a.inputs]
    out = a.out or _default_out(a.inputs[0], "_merged")
    fp.merge_pdfs(files, out, compress=not a.no_compress, progress=_progress)
    _p("Merged %d file(s) -> %s" % (len(files), out))
    return 0


def cmd_compress(a):
    if a.target:
        out, mode = fp.compress_to_target(a.input, a.out or _default_out(a.input, "_compressed"),
                                          target_mb=a.target, progress=_progress)
        _p("Compressed (%s) -> %s" % (mode, out))
    else:
        out = fp.compress_pdf(a.input, a.out or _default_out(a.input, "_compressed"),
                              level=a.level, progress=_progress)
        _p("Compressed (%s) -> %s" % (a.level, out))
    return 0


def cmd_grayscale(a):
    out = fp.pdf_grayscale(a.input, a.out or _default_out(a.input, "_gray"), progress=_progress)
    _p("Grayscale -> %s" % out)
    return 0


def cmd_protect(a):
    out = fp.protect_pdf(a.input, a.out or _default_out(a.input, "_locked"), a.password)
    _p("Protected -> %s" % out)
    return 0


def cmd_unlock(a):
    out = fp.unlock_pdf(a.input, a.out or _default_out(a.input, "_unlocked"), a.password)
    _p("Unlocked -> %s" % out)
    return 0


def cmd_pdf2img(a):
    outdir = _outdir(a, a.input)
    outs = fp.pdf_to_images(a.input, outdir, fmt=a.fmt, dpi=a.dpi, progress=_progress)
    _p("Exported %d image(s) -> %s" % (len(outs), outdir))
    return 0


def cmd_img2pdf(a):
    out = a.out or _default_out(a.inputs[0], "_images")
    fi.images_to_pdf(a.inputs, out, page=a.page, progress=_progress)
    _p("Created -> %s" % out)
    return 0


def cmd_watermark(a):
    out = fp.watermark_pdf(a.input, a.out or _default_out(a.input, "_wm"),
                           text=a.text, opacity=a.opacity, rotation=a.rotation,
                           tiled=a.tiled, progress=_progress)
    _p("Watermark -> %s" % out)
    return 0


def cmd_headerfooter(a):
    out = fp.header_footer_pdf(a.input, a.out or _default_out(a.input, "_hf"),
                               fmt=a.format, position=a.position, progress=_progress)
    _p("Header/footer -> %s" % out)
    return 0


def cmd_bates(a):
    out = fp.bates_pdf(a.input, a.out or _default_out(a.input, "_bates"), prefix=a.prefix,
                       start=a.start, digits=a.digits, position=a.position, progress=_progress)
    _p("Bates -> %s" % out)
    return 0


def cmd_normalize(a):
    out = fp.normalize_pages(a.input, a.out or _default_out(a.input, "_%s" % a.size.lower()),
                             size=a.size, orientation=a.orientation, progress=_progress)
    _p("Normalized -> %s" % out)
    return 0


def cmd_nup(a):
    out = fp.nup_pdf(a.input, a.out or _default_out(a.input, "_nup"), n=a.n,
                     orientation=a.orientation, page_size=a.size, progress=_progress)
    _p("N-up -> %s" % out)
    return 0


def cmd_trim(a):
    out = fp.trim_margins(a.input, a.out or _default_out(a.input, "_trim"), progress=_progress)
    _p("Trimmed -> %s" % out)
    return 0


def cmd_crop(a):
    out = fp.crop_margins(a.input, a.out or _default_out(a.input, "_crop"),
                          left=a.left, right=a.right, top=a.top, bottom=a.bottom,
                          progress=_progress)
    _p("Cropped -> %s" % out)
    return 0


def cmd_redact(a):
    names = [x.strip() for x in (a.patterns or "").split(",") if x.strip()]
    out = fp.auto_redact(a.input, a.out or _default_out(a.input, "_redacted"),
                         pattern_names=names, custom=a.custom, progress=_progress)
    _p("Redacted -> %s" % out)
    return 0


def cmd_sanitize(a):
    out = fp.sanitize_pdf(a.input, a.out or _default_out(a.input, "_clean"))
    _p("Sanitized -> %s" % out)
    return 0


def cmd_repair(a):
    out = fp.repair_pdf(a.input, a.out or _default_out(a.input, "_repaired"))
    _p("Rebuilt -> %s" % out)
    return 0


def cmd_split_size(a):
    outdir = _outdir(a, a.input)
    outs = fp.split_by_size(a.input, outdir, max_mb=a.mb, progress=_progress)
    for o in outs:
        _p("OK  %s" % o)
    _p("Split into %d part(s) -> %s" % (len(outs), outdir))
    return 0


def cmd_metadata(a):
    if a.show:
        md = fp.get_metadata(a.input)
        for k in ("title", "author", "subject", "keywords", "creator", "producer"):
            _p("%-12s %s" % (k + ":", md.get(k) or ""))
        return 0
    meta = {}
    for k in ("title", "author", "subject", "keywords"):
        v = getattr(a, k)
        if v is not None:
            meta[k] = v
    if not meta:
        _p("Nothing to set. Use --title/--author/--subject/--keywords or --show.")
        return 1
    out = fp.set_metadata(a.input, a.out or _default_out(a.input, "_meta"), meta)
    _p("Metadata updated -> %s" % out)
    return 0


def cmd_bookmarks(a):
    if a.list:
        toc = fp.get_bookmarks(a.input)
        for lvl, title, page in toc:
            _p("%s%s  (p.%s)" % ("  " * (lvl - 1), title, page))
        if not toc:
            _p("(no bookmarks)")
        return 0
    out = a.out or _default_out(a.input, "_bm")
    res = fp.auto_bookmarks(a.input, out, max_level=a.level, progress=_progress)
    if res:
        _p("Auto bookmarks -> %s" % out)
        return 0
    _p("No heading-like text found; nothing written.")
    return 1


def cmd_sign(a):
    out = fp.place_signature_pdf(a.input, a.out or _default_out(a.input, "_signed"), a.sig,
                                 cx=a.cx, cy=a.cy, width_frac=a.width, page_index=a.page)
    _p("Signed -> %s" % out)
    return 0


def cmd_qr(a):
    out = fp.qr_stamp_pdf(a.input, a.out or _default_out(a.input, "_qr"), a.data,
                          position=a.position, size_mm=a.size, progress=_progress)
    _p("QR stamp -> %s" % out)
    return 0


# ───────────────────────── image commands ─────────────────────────
def cmd_img_compress(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.compress_images(a.inputs, outdir, quality=a.quality,
                                                    progress=_progress))


def cmd_img_convert(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.convert_images(a.inputs, outdir, fmt=a.format,
                                                   quality=a.quality, progress=_progress))


def cmd_img_resize(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.resize_images(a.inputs, outdir, width=a.width,
                                                  height=a.height, percent=a.percent,
                                                  progress=_progress))


def cmd_img_grayscale(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.grayscale_images(a.inputs, outdir, progress=_progress))


def cmd_img_watermark(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.watermark_images(a.inputs, outdir, text=a.text,
                                                     position=a.position, opacity=a.opacity,
                                                     progress=_progress))


def cmd_img_adjust(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.adjust_images(a.inputs, outdir, brightness=a.brightness,
                                                  contrast=a.contrast, saturation=a.saturation,
                                                  progress=_progress))


def cmd_img_exif(a):
    outdir = _ensure_dir(a.out)
    return _img_batch(a, lambda: fi.strip_exif(a.inputs, outdir, progress=_progress))


def cmd_img_border(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.add_border(a.inputs, outdir, width=a.width, color=a.color,
                                               progress=_progress))


def cmd_img_ico(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.to_ico(a.inputs, outdir, progress=_progress))


def cmd_img_trim(a):
    outdir = _outdir(a, *a.inputs)
    return _img_batch(a, lambda: fi.trim_images(a.inputs, outdir, progress=_progress))


def cmd_img_rename(a):
    if a.dry_run:
        for src, dst in fi.rename_plan(a.inputs, a.pattern, a.start, a.pad):
            _p("%s  ->  %s" % (os.path.basename(src), os.path.basename(dst)))
        return 0
    return _img_batch(a, lambda: fi.rename_batch(a.inputs, a.pattern, a.start, a.pad,
                                                 progress=_progress))


# ───────────────────────── automation commands ─────────────────────────
_EXTS = ".pdf,.jpg,.jpeg,.png,.webp,.bmp,.tif,.tiff"


def cmd_recipe(a):
    recipe = au.load_recipe(a.recipe)
    files = list(a.inputs or [])
    if a.folder:
        exts = [x.strip() for x in (a.ext or _EXTS).split(",") if x.strip()]
        files += au.list_input_files(a.folder, exts)
    if not files:
        _p("No input files.")
        return 1
    outdir = _ensure_dir(a.out or a.folder or os.path.dirname(files[0]) or ".")
    _p("Recipe: %s | %d file(s)" % (recipe.get("name", "?"), len(files)))
    rows = au.batch_run(recipe, files, outdir, recipe_name=recipe.get("name", ""),
                        progress=_progress, log=_p)
    report = au.append_report(rows, os.path.join(outdir, "automation_report.csv"))
    ok = sum(1 for r in rows if r["status"] == "ok")
    _p("Done: %d ok, %d failed. Report: %s" % (ok, len(rows) - ok, report))
    return 0 if ok == len(rows) else 2


def cmd_watch(a):
    recipe = au.load_recipe(a.recipe)
    exts = tuple(x.strip() for x in (a.ext or _EXTS).split(",") if x.strip())
    outdir = _ensure_dir(a.out or a.folder)
    w = au.Watcher(a.folder, recipe, outdir, exts=exts, poll=a.interval,
                   move_done=not a.keep, delete_src=a.delete, log=_p,
                   recipe_name=recipe.get("name", ""))
    w.start()
    _p("Watching %s (Ctrl+C to stop)" % a.folder)
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        w.stop()
        _p("Stopped. Processed: %d, errors: %d" % (w.count, w.errors))
    return 0


def cmd_schedule(a):
    recipe = os.path.abspath(a.recipe)
    folder = os.path.abspath(a.folder)
    out = os.path.abspath(a.out or a.folder)
    if getattr(sys, "frozen", False):
        exe = sys.executable
        args = 'recipe -r "%s" -d "%s" -o "%s"' % (recipe, folder, out)
    else:
        exe = sys.executable
        args = '"%s" recipe -r "%s" -d "%s" -o "%s"' % (
            os.path.abspath(__file__), recipe, folder, out)
    info = au.create_task(a.name, exe, args, when=a.when, time_str=a.time)
    _p(info)
    _p("Task scheduled: %s (%s at %s)" % (a.name, a.when, a.time))
    return 0


def cmd_ops(a):
    for key, label in au.ops_table():
        _p("%-16s %s" % (key, label))
    return 0


# ───────────────────────── parser ─────────────────────────
def build_parser():
    ap = argparse.ArgumentParser(prog="PDFSuiteCLI",
                                 description="PDF Suite Pro command line tool")
    sub = ap.add_subparsers(dest="cmd")
    sub.required = True

    def out_p(p, metavar="PDF"):
        p.add_argument("input", metavar=metavar, help="input file")

    def out_o(p, default=None):
        p.add_argument("-o", "--out", default=default, help="output file/folder")

    p = sub.add_parser("merge", help="merge PDFs")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--pages", default="all", help="page range applied to each input")
    p.add_argument("--no-compress", action="store_true")
    p.set_defaults(fn=cmd_merge)

    p = sub.add_parser("compress", help="compress a PDF")
    out_p(p)
    out_o(p)
    p.add_argument("--level", default="medium", choices=["low", "medium", "high", "max"])
    p.add_argument("--target", type=float, default=None, help="target size in MB (rasterizes)")
    p.set_defaults(fn=cmd_compress)

    p = sub.add_parser("grayscale", help="convert PDF to grayscale")
    out_p(p)
    out_o(p)
    p.set_defaults(fn=cmd_grayscale)

    for name, fn, helptext in (("protect", cmd_protect, "add password"),
                               ("unlock", cmd_unlock, "remove password")):
        p = sub.add_parser(name, help=helptext)
        out_p(p)
        out_o(p)
        p.add_argument("--password", required=True)
        p.set_defaults(fn=fn)

    p = sub.add_parser("pdf2img", help="export PDF pages as images")
    out_p(p)
    out_o(p, ".")
    p.add_argument("--dpi", type=int, default=150)
    p.add_argument("--fmt", default="png", choices=["png", "jpg", "webp"])
    p.set_defaults(fn=cmd_pdf2img)

    p = sub.add_parser("img2pdf", help="convert images to a single PDF")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--page", default="fit", choices=["fit", "A4", "Letter"])
    p.set_defaults(fn=cmd_img2pdf)

    p = sub.add_parser("watermark", help="text watermark")
    out_p(p)
    out_o(p)
    p.add_argument("--text", default="CONFIDENTIAL")
    p.add_argument("--opacity", type=float, default=0.3)
    p.add_argument("--rotation", type=int, default=35)
    p.add_argument("--tiled", action="store_true")
    p.set_defaults(fn=cmd_watermark)

    p = sub.add_parser("headerfooter", help="header/footer or page numbers")
    out_p(p)
    out_o(p)
    p.add_argument("--format", default="{page} / {total}")
    p.add_argument("--position", default="bottom-center")
    p.set_defaults(fn=cmd_headerfooter)

    p = sub.add_parser("bates", help="Bates numbering")
    out_p(p)
    out_o(p)
    p.add_argument("--prefix", default="")
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--digits", type=int, default=6)
    p.add_argument("--position", default="bottom-right")
    p.set_defaults(fn=cmd_bates)

    p = sub.add_parser("normalize", help="resize pages to A4/Letter")
    out_p(p)
    out_o(p)
    p.add_argument("--size", default="A4", choices=["A4", "Letter"])
    p.add_argument("--orientation", default="auto",
                   choices=["auto", "portrait", "landscape"])
    p.set_defaults(fn=cmd_normalize)

    p = sub.add_parser("nup", help="pages per sheet")
    out_p(p)
    out_o(p)
    p.add_argument("--n", type=int, default=2, choices=[2, 4, 6])
    p.add_argument("--orientation", default="portrait", choices=["portrait", "landscape"])
    p.add_argument("--size", default="A4", choices=["A4", "Letter"])
    p.set_defaults(fn=cmd_nup)

    p = sub.add_parser("trim", help="auto-trim white margins")
    out_p(p)
    out_o(p)
    p.set_defaults(fn=cmd_trim)

    p = sub.add_parser("crop", help="crop margins (mm)")
    out_p(p)
    out_o(p)
    for side in ("left", "right", "top", "bottom"):
        p.add_argument("--" + side, type=float, default=0)
    p.set_defaults(fn=cmd_crop)

    p = sub.add_parser("redact", help="regex auto-redaction")
    out_p(p)
    out_o(p)
    p.add_argument("--patterns", default="emails,phones,cards",
                   help="comma list: emails,phones,cards,aadhaar,pan,ifsc")
    p.add_argument("--custom", default="", help="custom regex")
    p.set_defaults(fn=cmd_redact)

    p = sub.add_parser("sanitize", help="remove JS/embedded files")
    out_p(p)
    out_o(p)
    p.set_defaults(fn=cmd_sanitize)

    p = sub.add_parser("repair", help="rebuild a PDF")
    out_p(p)
    out_o(p)
    p.set_defaults(fn=cmd_repair)

    p = sub.add_parser("split-size", help="split by maximum size")
    out_p(p)
    out_o(p, ".")
    p.add_argument("--mb", type=float, default=10)
    p.set_defaults(fn=cmd_split_size)

    p = sub.add_parser("metadata", help="show or set metadata")
    out_p(p)
    out_o(p)
    p.add_argument("--show", action="store_true")
    for k in ("title", "author", "subject", "keywords"):
        p.add_argument("--" + k, default=None)
    p.set_defaults(fn=cmd_metadata)

    p = sub.add_parser("bookmarks", help="list or auto-generate bookmarks")
    out_p(p)
    out_o(p)
    p.add_argument("--list", action="store_true")
    p.add_argument("--level", type=int, default=2)
    p.set_defaults(fn=cmd_bookmarks)

    p = sub.add_parser("sign", help="place signature image")
    out_p(p)
    out_o(p)
    p.add_argument("--sig", required=True, help="signature PNG (transparent)")
    p.add_argument("--cx", type=float, default=0.75)
    p.add_argument("--cy", type=float, default=0.9)
    p.add_argument("--width", type=float, default=0.3)
    p.add_argument("--page", type=int, default=-1)
    p.set_defaults(fn=cmd_sign)

    p = sub.add_parser("qr", help="add QR code stamp")
    out_p(p)
    out_o(p)
    p.add_argument("--data", required=True)
    p.add_argument("--position", default="bottom-right")
    p.add_argument("--size", type=float, default=28, help="size in mm")
    p.set_defaults(fn=cmd_qr)

    p = sub.add_parser("img-compress", help="compress images to JPEG")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--quality", type=int, default=60)
    p.set_defaults(fn=cmd_img_compress)

    p = sub.add_parser("img-convert", help="convert image formats")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--format", default="PNG")
    p.add_argument("--quality", type=int, default=90)
    p.set_defaults(fn=cmd_img_convert)

    p = sub.add_parser("img-resize", help="resize images")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--percent", type=int, default=None)
    p.add_argument("--width", type=int, default=None)
    p.add_argument("--height", type=int, default=None)
    p.set_defaults(fn=cmd_img_resize)

    p = sub.add_parser("img-grayscale", help="convert images to grayscale")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.set_defaults(fn=cmd_img_grayscale)

    p = sub.add_parser("img-watermark", help="watermark images")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--text", default="PDF Suite Pro")
    p.add_argument("--position", default="bottom-right")
    p.add_argument("--opacity", type=float, default=0.55)
    p.set_defaults(fn=cmd_img_watermark)

    p = sub.add_parser("img-adjust", help="brightness/contrast/saturation")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--brightness", type=float, default=1.0)
    p.add_argument("--contrast", type=float, default=1.0)
    p.add_argument("--saturation", type=float, default=1.0)
    p.set_defaults(fn=cmd_img_adjust)

    p = sub.add_parser("img-exif", help="strip EXIF/metadata")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.set_defaults(fn=cmd_img_exif)

    p = sub.add_parser("img-border", help="add a border/frame")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.add_argument("--width", type=int, default=24)
    p.add_argument("--color", default="#ffffff")
    p.set_defaults(fn=cmd_img_border)

    p = sub.add_parser("img-ico", help="convert to .ico")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.set_defaults(fn=cmd_img_ico)

    p = sub.add_parser("img-trim", help="auto-trim image borders")
    p.add_argument("inputs", nargs="+")
    out_o(p)
    p.set_defaults(fn=cmd_img_trim)

    p = sub.add_parser("img-rename", help="batch rename images")
    p.add_argument("inputs", nargs="+")
    p.add_argument("--pattern", default="{name}_{n}")
    p.add_argument("--start", type=int, default=1)
    p.add_argument("--pad", type=int, default=3)
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_img_rename)

    p = sub.add_parser("recipe", help="run a recipe on files/folder")
    p.add_argument("-r", "--recipe", required=True)
    p.add_argument("-i", "--inputs", nargs="*", default=[])
    p.add_argument("-d", "--folder", default=None)
    out_o(p)
    p.add_argument("--ext", default=_EXTS)
    p.set_defaults(fn=cmd_recipe)

    p = sub.add_parser("watch", help="watch a folder and run a recipe")
    p.add_argument("-d", "--folder", required=True)
    p.add_argument("-r", "--recipe", required=True)
    out_o(p)
    p.add_argument("--ext", default=_EXTS)
    p.add_argument("--interval", type=int, default=5)
    p.add_argument("--keep", action="store_true", help="do not move processed files")
    p.add_argument("--delete", action="store_true", help="delete source after success")
    p.set_defaults(fn=cmd_watch)

    p = sub.add_parser("schedule", help="create a daily/weekly Windows task")
    p.add_argument("--name", required=True)
    p.add_argument("-r", "--recipe", required=True)
    p.add_argument("-d", "--folder", required=True)
    out_o(p)
    p.add_argument("--time", default="18:00")
    p.add_argument("--when", default="DAILY", choices=["DAILY", "WEEKLY"])
    p.set_defaults(fn=cmd_schedule)

    p = sub.add_parser("ops", help="list recipe operations")
    p.set_defaults(fn=cmd_ops)

    return ap


def main(argv=None):
    ap = build_parser()
    args = ap.parse_args(argv)
    try:
        return args.fn(args)
    except Exception as e:
        _p("ERROR: %s" % e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
