"""Automation engine: recipes, batch runs, watch folders, scheduling, reports."""
import os
import csv
import json
import time
import shutil
import smtplib
import tempfile
import threading
import subprocess
from datetime import datetime
from email.mime.text import MIMEText

import features_pdf as fp
import features_image as fi


def _o(path, outdir, suffix, ext=".pdf"):
    base = os.path.splitext(os.path.basename(path))[0]
    return os.path.join(outdir, base + suffix + ext)


# ───────────────────────── operation registry ─────────────────────────
OPS = {}


def _reg(name, label, params, fn):
    OPS[name] = {"label": label, "params": params, "fn": fn}


def _pdf_compress(p, outdir, prm):
    return fp.compress_pdf(p, _o(p, outdir, "_compressed"), prm.get("level", "medium"))


def _pdf_target(p, outdir, prm):
    out, _mode = fp.compress_to_target(p, _o(p, outdir, "_target"),
                                       prm.get("target_mb", 5))
    return out


def _pdf_grayscale(p, outdir, prm):
    return fp.pdf_grayscale(p, _o(p, outdir, "_gray"))


def _pdf_watermark(p, outdir, prm):
    return fp.watermark_pdf(p, _o(p, outdir, "_wm"), text=prm.get("text", "CONFIDENTIAL"),
                            opacity=prm.get("opacity", 0.3),
                            rotation=prm.get("rotation", 35),
                            tiled=bool(prm.get("tiled")))


def _pdf_headerfooter(p, outdir, prm):
    return fp.header_footer_pdf(p, _o(p, outdir, "_hf"), fmt=prm.get("fmt", "{page} / {total}"),
                                position=prm.get("position", "bottom-center"))


def _pdf_bates(p, outdir, prm):
    return fp.bates_pdf(p, _o(p, outdir, "_bates"), prefix=prm.get("prefix", ""),
                        start=prm.get("start", 1), digits=prm.get("digits", 6),
                        position=prm.get("position", "bottom-right"))


def _pdf_normalize(p, outdir, prm):
    return fp.normalize_pages(p, _o(p, outdir, "_%s" % prm.get("size", "A4").lower()),
                              size=prm.get("size", "A4"), orientation=prm.get("orientation", "auto"))


def _pdf_nup(p, outdir, prm):
    return fp.nup_pdf(p, _o(p, outdir, "_nup"), n=prm.get("n", 2),
                      orientation=prm.get("orientation", "portrait"),
                      page_size=prm.get("size", "A4"))


def _pdf_trim(p, outdir, prm):
    return fp.trim_margins(p, _o(p, outdir, "_trim"))


def _pdf_protect(p, outdir, prm):
    return fp.protect_pdf(p, _o(p, outdir, "_locked"), str(prm.get("password", "")))


def _pdf_unlock(p, outdir, prm):
    return fp.unlock_pdf(p, _o(p, outdir, "_unlocked"), str(prm.get("password", "")))


def _pdf_redact(p, outdir, prm):
    names = [n for n in ("emails", "phones", "cards", "aadhaar", "pan", "ifsc") if prm.get(n)]
    return fp.auto_redact(p, _o(p, outdir, "_redacted"), pattern_names=names,
                          custom=prm.get("custom", ""))


def _pdf_sanitize(p, outdir, prm):
    return fp.sanitize_pdf(p, _o(p, outdir, "_clean"))


def _pdf_repair(p, outdir, prm):
    return fp.repair_pdf(p, _o(p, outdir, "_repaired"))


def _pdf_to_images(p, outdir, prm):
    fp.pdf_to_images(p, outdir, fmt=prm.get("fmt", "png"), dpi=prm.get("dpi", 150))
    return outdir


def _pdf_split_size(p, outdir, prm):
    outs = fp.split_by_size(p, outdir, max_mb=prm.get("mb", 10))
    return outs[0] if outs else ""


def _img_compress(p, outdir, prm):
    res = fi.compress_images([p], outdir, quality=prm.get("quality", 60))
    return _res1(res)


def _img_convert(p, outdir, prm):
    res = fi.convert_images([p], outdir, fmt=prm.get("fmt", "PNG"))
    return _res1(res)


def _img_resize(p, outdir, prm):
    res = fi.resize_images([p], outdir, percent=prm.get("percent", 50))
    return _res1(res)


def _img_watermark(p, outdir, prm):
    res = fi.watermark_images([p], outdir, text=prm.get("text", "PageDeck"),
                              opacity=prm.get("opacity", 0.55))
    return _res1(res)


def _img_grayscale(p, outdir, prm):
    res = fi.grayscale_images([p], outdir)
    return _res1(res)


def _img_adjust(p, outdir, prm):
    res = fi.adjust_images([p], outdir, brightness=prm.get("brightness", 1.0),
                           contrast=prm.get("contrast", 1.0),
                           saturation=prm.get("saturation", 1.0))
    return _res1(res)


def _img_exif(p, outdir, prm):
    res = fi.strip_exif([p], outdir)
    return _res1(res)


def _img_ico(p, outdir, prm):
    res = fi.to_ico([p], outdir)
    return _res1(res)


def _rename(p, outdir, prm):
    res = fi.rename_batch([p], pattern=prm.get("pattern", "{name}_{n}"),
                          start=prm.get("start", 1), pad=prm.get("pad", 3))
    return _res1(res)


# ── v5.0 operations ──
def _pdf_ocr(p, outdir, prm):
    return fp.ocr_pdf(p, _o(p, outdir, "_ocr"), lang=prm.get("lang", "eng"),
                      dpi=prm.get("dpi", 200), mode="pdf")


def _pdf_highlight(p, outdir, prm):
    out, _n = fp.highlight_text(p, _o(p, outdir, "_highlight"), prm.get("phrase", ""))
    return out


def _pdf_replace(p, outdir, prm):
    out, _n = fp.search_replace(p, _o(p, outdir, "_replaced"), prm.get("find", ""),
                                prm.get("replace", ""),
                                match_case=bool(prm.get("match_case")),
                                whole_word=bool(prm.get("whole_word")))
    return out


def _pdf_typewriter(p, outdir, prm):
    return fp.typewriter_text(p, _o(p, outdir, "_text"), prm.get("text", ""),
                              max(0, int(prm.get("page", 1)) - 1),
                              prm.get("x", 0.1), prm.get("y", 0.1),
                              fontsize=prm.get("size", 12))


def _pdf_attach(p, outdir, prm):
    src = prm.get("file", "")
    if not src or not os.path.isfile(src):
        raise ValueError("Attachment file not found: %s" % src)
    return fp.add_attachment(p, _o(p, outdir, "_attached"), src)


def _pdf_split_keyword(p, outdir, prm):
    outs = fp.split_by_keyword(p, outdir, prm.get("keyword", ""))
    return outs[0] if outs else ""


def _pdf_split_blank(p, outdir, prm):
    outs = fp.split_at_blank_pages(p, outdir)
    return outs[0] if outs else ""


def _office_pdf(p, outdir, prm):
    outs = fp.office_to_pdf([p], outdir)
    return outs[0] if outs else ""


def _img_scan(p, outdir, prm):
    fmt = fi._ext_format(p)
    out = fi._out_path(p, outdir, "_scan", fi.ext_for(fmt))
    return fi.scan_cleanup(p, out, whiten=bool(prm.get("whiten", True)),
                           despeckle=bool(prm.get("despeckle", True)))


def _img_nobg(p, outdir, prm):
    out = fi._out_path(p, outdir, "_nobg", ".png")
    return fi.remove_background(p, out, tolerance=prm.get("tolerance", 40))


def _img_social(p, outdir, prm):
    label = prm.get("preset", "")
    size, tag = (1080, 1080), "social"
    for name, w, h in fi.SOCIAL_PRESETS:
        if name == label:
            size, tag = (w, h), "%dx%d" % (w, h)
            break
    res = fi.social_export([p], outdir, size=size, mode=prm.get("mode", "fill"), label=tag)
    return _res1(res)


def _img_filter(p, outdir, prm):
    res = fi.apply_filter([p], outdir, preset=prm.get("preset", "B&W"))
    return _res1(res)


def _img_upscale(p, outdir, prm):
    res = fi.upscale([p], outdir, factor=prm.get("factor", 2))
    return _res1(res)


def _img_crop_batch(p, outdir, prm):
    res = fi.batch_crop([p], outdir, left=prm.get("left", 0), top=prm.get("top", 0),
                        right=prm.get("right", 0), bottom=prm.get("bottom", 0))
    return _res1(res)


def _img_nogps(p, outdir, prm):
    fmt = fi._ext_format(p)
    return fi.exif_remove_gps(p, fi._out_path(p, outdir, "_nogps", fi.ext_for(fmt)))


def _res1(results):
    if not results:
        return ""
    src, dst, err = results[0]
    if err:
        raise RuntimeError(err)
    return dst or ""


_POS_OPTS = ["bottom-right", "bottom-center", "bottom-left", "top-right",
             "top-center", "top-left", "middle"]

_reg("pdf_compress", "Compress PDF", [
    {"key": "level", "label": "Level", "type": "combo", "default": "medium",
     "options": ["low", "medium", "high", "max"]}], _pdf_compress)
_reg("pdf_target", "Compress to target size", [
    {"key": "target_mb", "label": "Target (MB)", "type": "float", "default": 5.0}], _pdf_target)
_reg("pdf_grayscale", "PDF to grayscale", [], _pdf_grayscale)
_reg("pdf_watermark", "Add text watermark", [
    {"key": "text", "label": "Text", "type": "text", "default": "CONFIDENTIAL"},
    {"key": "opacity", "label": "Opacity (0-1)", "type": "float", "default": 0.3},
    {"key": "rotation", "label": "Rotation", "type": "int", "default": 35},
    {"key": "tiled", "label": "Tiled", "type": "check", "default": False}], _pdf_watermark)
_reg("pdf_headerfooter", "Header / footer", [
    {"key": "fmt", "label": "Format", "type": "text", "default": "{page} / {total}"},
    {"key": "position", "label": "Position", "type": "combo",
     "default": "bottom-center", "options": _POS_OPTS}], _pdf_headerfooter)
_reg("pdf_bates", "Bates numbering", [
    {"key": "prefix", "label": "Prefix", "type": "text", "default": ""},
    {"key": "start", "label": "Start at", "type": "int", "default": 1},
    {"key": "digits", "label": "Digits", "type": "int", "default": 6},
    {"key": "position", "label": "Position", "type": "combo",
     "default": "bottom-right", "options": _POS_OPTS}], _pdf_bates)
_reg("pdf_normalize", "Normalize page size", [
    {"key": "size", "label": "Page size", "type": "combo", "default": "A4",
     "options": ["A4", "Letter"]},
    {"key": "orientation", "label": "Orientation", "type": "combo",
     "default": "auto", "options": ["auto", "portrait", "landscape"]}], _pdf_normalize)
_reg("pdf_nup", "Pages per sheet (N-up)", [
    {"key": "n", "label": "Pages per sheet", "type": "combo", "default": "2",
     "options": ["2", "4", "6"]},
    {"key": "orientation", "label": "Orientation", "type": "combo",
     "default": "portrait", "options": ["portrait", "landscape"]},
    {"key": "size", "label": "Page size", "type": "combo", "default": "A4",
     "options": ["A4", "Letter"]}], _pdf_nup)
_reg("pdf_trim", "Auto-trim white margins", [], _pdf_trim)
_reg("pdf_protect", "Password protect", [
    {"key": "password", "label": "Password", "type": "text", "default": ""}], _pdf_protect)
_reg("pdf_unlock", "Remove password", [
    {"key": "password", "label": "Password", "type": "text", "default": ""}], _pdf_unlock)
_reg("pdf_redact", "Auto-redact patterns", [
    {"key": "emails", "label": "Emails", "type": "check", "default": True},
    {"key": "phones", "label": "Phone numbers", "type": "check", "default": True},
    {"key": "cards", "label": "Card numbers", "type": "check", "default": True},
    {"key": "aadhaar", "label": "Aadhaar numbers", "type": "check", "default": True},
    {"key": "pan", "label": "PAN codes", "type": "check", "default": True},
    {"key": "ifsc", "label": "IFSC codes", "type": "check", "default": False},
    {"key": "custom", "label": "Custom regex", "type": "text", "default": ""}], _pdf_redact)
_reg("pdf_sanitize", "Sanitize (remove JS / embedded)", [], _pdf_sanitize)
_reg("pdf_repair", "Repair / rebuild", [], _pdf_repair)
_reg("pdf_to_images", "PDF -> images (DPI)", [
    {"key": "fmt", "label": "Format", "type": "combo", "default": "png",
     "options": ["png", "jpg", "webp"]},
    {"key": "dpi", "label": "DPI", "type": "int", "default": 150}], _pdf_to_images)
_reg("pdf_split_size", "Split by size (MB)", [
    {"key": "mb", "label": "Max size (MB)", "type": "float", "default": 10.0}], _pdf_split_size)
_reg("img_compress", "Compress image", [
    {"key": "quality", "label": "Quality (1-95)", "type": "int", "default": 60}], _img_compress)
_reg("img_convert", "Convert image format", [
    {"key": "fmt", "label": "Format", "type": "combo", "default": "PNG",
     "options": ["JPEG", "PNG", "WEBP", "BMP", "TIFF"]}], _img_convert)
_reg("img_resize", "Resize image (%)", [
    {"key": "percent", "label": "Percent", "type": "int", "default": 50}], _img_resize)
_reg("img_watermark", "Watermark image", [
    {"key": "text", "label": "Text", "type": "text", "default": "PageDeck"},
    {"key": "opacity", "label": "Opacity (0-1)", "type": "float", "default": 0.55}], _img_watermark)
_reg("img_grayscale", "Image to grayscale", [], _img_grayscale)
_reg("img_adjust", "Enhance image (light/contrast/sat)", [
    {"key": "brightness", "label": "Brightness", "type": "float", "default": 1.1},
    {"key": "contrast", "label": "Contrast", "type": "float", "default": 1.1},
    {"key": "saturation", "label": "Saturation", "type": "float", "default": 1.1}], _img_adjust)
_reg("img_exif", "Strip EXIF / metadata", [], _img_exif)
_reg("img_ico", "Convert to icon (.ico)", [], _img_ico)
_reg("rename", "Rename (pattern)", [
    {"key": "pattern", "label": "Pattern", "type": "text", "default": "{name}_{n}"},
    {"key": "start", "label": "Start at", "type": "int", "default": 1},
    {"key": "pad", "label": "Pad digits", "type": "int", "default": 3}], _rename)

# ── v5.0 registrations ──
_reg("pdf_ocr", "OCR - make searchable", [
    {"key": "lang", "label": "Language(s)", "type": "text", "default": "eng"},
    {"key": "dpi", "label": "DPI", "type": "int", "default": 200}], _pdf_ocr)
_reg("pdf_highlight", "Highlight a phrase", [
    {"key": "phrase", "label": "Phrase", "type": "text", "default": ""}], _pdf_highlight)
_reg("pdf_replace", "Find and replace text", [
    {"key": "find", "label": "Find", "type": "text", "default": ""},
    {"key": "replace", "label": "Replace with", "type": "text", "default": ""},
    {"key": "match_case", "label": "Match case", "type": "check", "default": False},
    {"key": "whole_word", "label": "Whole words", "type": "check", "default": False}], _pdf_replace)
_reg("pdf_typewriter", "Typewriter text on a page", [
    {"key": "text", "label": "Text", "type": "text", "default": ""},
    {"key": "page", "label": "Page number", "type": "int", "default": 1},
    {"key": "x", "label": "X (0-1)", "type": "float", "default": 0.1},
    {"key": "y", "label": "Y (0-1)", "type": "float", "default": 0.1},
    {"key": "size", "label": "Font size", "type": "int", "default": 12}], _pdf_typewriter)
_reg("pdf_attach", "Attach a file inside PDF", [
    {"key": "file", "label": "File to attach", "type": "text", "default": ""}], _pdf_attach)
_reg("pdf_split_keyword", "Split at keyword", [
    {"key": "keyword", "label": "Keyword", "type": "text", "default": ""}], _pdf_split_keyword)
_reg("pdf_split_blank", "Split at blank pages", [], _pdf_split_blank)
_reg("office_pdf", "Word/Excel/PPT to PDF (LibreOffice)", [], _office_pdf)
_reg("img_scan", "Scan cleanup (whiten / despeckle)", [
    {"key": "whiten", "label": "Whiten", "type": "check", "default": True},
    {"key": "despeckle", "label": "Despeckle", "type": "check", "default": True}], _img_scan)
_reg("img_nobg", "Remove background", [
    {"key": "tolerance", "label": "Tolerance (0-120)", "type": "int", "default": 40}], _img_nobg)
_reg("img_social", "Social media export", [
    {"key": "preset", "label": "Size", "type": "combo", "default": fi.SOCIAL_PRESETS[0][0],
     "options": [n for n, _w, _h in fi.SOCIAL_PRESETS]},
    {"key": "mode", "label": "Mode", "type": "combo", "default": "fill",
     "options": ["fill", "fit"]}], _img_social)
_reg("img_filter", "Apply filter / look", [
    {"key": "preset", "label": "Filter", "type": "combo", "default": "B&W",
     "options": list(fi.FILTERS)}], _img_filter)
_reg("img_upscale", "Upscale image (2x - 4x)", [
    {"key": "factor", "label": "Scale", "type": "combo", "default": "2",
     "options": ["2", "3", "4"]}], _img_upscale)
_reg("img_crop_batch", "Crop same margins (%)", [
    {"key": "left", "label": "Left %", "type": "float", "default": 0},
    {"key": "top", "label": "Top %", "type": "float", "default": 0},
    {"key": "right", "label": "Right %", "type": "float", "default": 0},
    {"key": "bottom", "label": "Bottom %", "type": "float", "default": 0}], _img_crop_batch)
_reg("img_nogps", "Remove GPS location (EXIF)", [], _img_nogps)


def ops_table():
    return [(k, v["label"]) for k, v in sorted(OPS.items(), key=lambda kv: kv[1]["label"])]


def _coerce(params, spec):
    out = {}
    for prm in spec["params"]:
        k = prm["key"]
        v = params.get(k, prm.get("default"))
        t = prm.get("type", "text")
        try:
            if t == "int":
                v = int(float(v))
            elif t == "float":
                v = float(v)
            elif t == "check":
                v = bool(v)
            else:
                v = "" if v is None else str(v)
        except (TypeError, ValueError):
            v = prm.get("default")
        out[k] = v
    return out


def new_recipe(name="My Recipe"):
    return {"name": name, "steps": []}


def load_recipe(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_recipe(recipe, path):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(recipe, fh, indent=2)
    return path


def run_step(step, path, outdir, log=None):
    op = step.get("op")
    spec = OPS.get(op)
    if not spec:
        raise ValueError("Unknown step: %s" % op)
    prm = _coerce(step.get("params", {}), spec)
    if log:
        log("-> %s" % spec["label"])
    return spec["fn"](path, outdir, prm)


def run_recipe(recipe, path, outdir, log=None):
    steps = recipe.get("steps", [])
    if not steps:
        raise ValueError("Recipe has no steps")
    cur = path
    tmpdir = None
    try:
        for i, step in enumerate(steps):
            last = (i == len(steps) - 1)
            if last:
                step_out = outdir
            else:
                if tmpdir is None:
                    tmpdir = tempfile.mkdtemp(prefix="pagedeck_")
                step_out = tmpdir
            cur = run_step(step, cur, step_out, log=log)
            if not cur:
                raise ValueError("Step produced no output: %s" % step.get("op"))
        return cur
    finally:
        if tmpdir:
            shutil.rmtree(tmpdir, ignore_errors=True)


def batch_run(recipe, files, outdir, recipe_name="", progress=None, log=None):
    rows = []
    total = len(files)
    for i, f in enumerate(files):
        out, err, status = "", "", "ok"
        try:
            out = run_recipe(recipe, f, outdir, log=log)
            if log:
                log("OK  %s -> %s" % (os.path.basename(f), os.path.basename(out)))
        except Exception as e:
            err, status = str(e), "error"
            if log:
                log("ERR %s: %s" % (os.path.basename(f), err))
        rows.append({"time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                     "recipe": recipe_name, "file": f, "status": status,
                     "output": out or "", "error": err})
        if progress:
            progress(i + 1, total)
    return rows


REPORT_FIELDS = ["time", "recipe", "file", "status", "output", "error"]


def append_report(rows, path):
    new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=REPORT_FIELDS)
        if new:
            w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in REPORT_FIELDS})
    return path


def list_input_files(folder, exts):
    out = []
    exts = tuple(e.lower() for e in exts)
    if os.path.isdir(folder):
        for name in sorted(os.listdir(folder)):
            full = os.path.join(folder, name)
            if os.path.isfile(full) and os.path.splitext(name)[1].lower() in exts:
                out.append(full)
    return out


# ───────────────────────── settings ─────────────────────────
def settings_dir():
    base = os.environ.get("APPDATA") or os.path.expanduser("~")
    d = os.path.join(base, "PageDeck")
    old = os.path.join(base, "PDFSuitePro")
    try:
        if (not os.path.isfile(os.path.join(d, "settings.json"))
                and os.path.isfile(os.path.join(old, "settings.json"))):
            os.makedirs(d, exist_ok=True)
            shutil.copy2(os.path.join(old, "settings.json"),
                         os.path.join(d, "settings.json"))
    except OSError:
        pass
    try:
        os.makedirs(d, exist_ok=True)
    except OSError:
        pass
    return d


def settings_path():
    return os.path.join(settings_dir(), "settings.json")


def load_settings():
    try:
        with open(settings_path(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return {}


def save_settings(s):
    try:
        with open(settings_path(), "w", encoding="utf-8") as fh:
            json.dump(s, fh, indent=2)
        return True
    except Exception:
        return False


# ───────────────────────── watch folders ─────────────────────────
class Watcher(object):
    """Polls a folder and runs a recipe on new, unchanged files."""

    def __init__(self, folder, recipe, outdir, exts=(".pdf",), poll=5,
                 move_done=True, delete_src=False, log=None, email_cfg=None,
                 recipe_name=""):
        self.folder = folder
        self.recipe = recipe
        self.recipe_name = recipe_name or recipe.get("name", "recipe")
        self.outdir = outdir
        self.exts = tuple(e.lower() for e in exts)
        self.poll = max(2, int(poll))
        self.move_done = move_done
        self.delete_src = delete_src
        self.log = log
        self.email_cfg = email_cfg or {}
        self._stop = threading.Event()
        self._seen = {}
        self._thread = None
        self.count = 0
        self.errors = 0

    def is_running(self):
        return self._thread is not None and self._thread.is_alive()

    def start(self):
        if self.is_running():
            return False
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self._log("watching %s (every %ds)" % (self.folder, self.poll))
        return True

    def stop(self):
        self._stop.set()
        self._log("stop requested")

    def _log(self, msg):
        if self.log:
            self.log("[%s] %s" % (datetime.now().strftime("%H:%M:%S"), msg))

    def _loop(self):
        while not self._stop.is_set():
            try:
                self._scan()
            except Exception as e:
                self._log("watch error: %s" % e)
            self._stop.wait(self.poll)
        self._log("stopped")

    def _scan(self):
        if not os.path.isdir(self.folder):
            return
        for name in sorted(os.listdir(self.folder)):
            full = os.path.join(self.folder, name)
            if os.path.isdir(full):
                continue
            if os.path.splitext(name)[1].lower() not in self.exts:
                continue
            try:
                size = os.path.getsize(full)
            except OSError:
                continue
            if self._seen.get(full) != size:
                self._seen[full] = size
                continue
            self._seen.pop(full, None)
            self._process(full)

    def _process(self, full):
        self._log("new file: %s" % os.path.basename(full))
        try:
            os.makedirs(self.outdir, exist_ok=True)
        except OSError:
            pass
        rows = batch_run(self.recipe, [full], self.outdir,
                         recipe_name=self.recipe_name, log=self._log)
        row = rows[0]
        if row["status"] == "ok":
            self.count += 1
        else:
            self.errors += 1
        try:
            append_report(rows, os.path.join(self.outdir, "automation_report.csv"))
        except OSError as e:
            self._log("report failed: %s" % e)
        self._archive(full, row["status"] == "ok")
        cfg = self.email_cfg
        if cfg.get("enabled") and cfg.get("host") and cfg.get("to"):
            try:
                body = "File: %s\nStatus: %s\nOutput: %s\n%s" % (
                    full, row["status"], row["output"], row["error"])
                send_email(cfg, "[PageDeck] %s" % self.recipe_name, body)
                self._log("report emailed to %s" % cfg.get("to"))
            except Exception as e:
                self._log("email failed: %s" % e)

    def _archive(self, full, ok):
        try:
            if self.delete_src:
                os.remove(full)
                return
            if not self.move_done:
                return
            dest_dir = os.path.join(self.folder, "processed" if ok else "failed")
            os.makedirs(dest_dir, exist_ok=True)
            dest = os.path.join(dest_dir, os.path.basename(full))
            n = 1
            stem, ext = os.path.splitext(os.path.basename(full))
            while os.path.exists(dest):
                dest = os.path.join(dest_dir, "%s_%d%s" % (stem, n, ext))
                n += 1
            shutil.move(full, dest)
        except Exception as e:
            self._log("archive failed: %s" % e)


# ───────────────────────── email reports ─────────────────────────
def send_email(cfg, subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = cfg.get("user") or cfg.get("to", "")
    msg["To"] = cfg.get("to", "")
    host = cfg.get("host", "")
    port = int(cfg.get("port") or 587)
    server = smtplib.SMTP(host, port, timeout=25)
    try:
        server.ehlo()
        try:
            server.starttls()
            server.ehlo()
        except smtplib.SMTPException:
            pass
        if cfg.get("user"):
            server.login(cfg["user"], cfg.get("password", ""))
        server.send_message(msg)
    finally:
        try:
            server.quit()
        except Exception:
            pass
    return True


# ───────────────────────── Windows task scheduler ─────────────────────────
def create_task(name, exe, args, when="DAILY", time_str="18:00", weekday="MON"):
    tr = ('"%s"' % exe) if not args else ('"%s" %s' % (exe, args))
    cmd = ["schtasks", "/Create", "/F", "/TN", "PageDeck\\" + name,
           "/TR", tr, "/SC", when, "/ST", time_str]
    if when == "WEEKLY":
        cmd += ["/D", weekday]
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out = (r.stdout or b"").decode("oem", "replace") + (r.stderr or b"").decode("oem", "replace")
    if r.returncode != 0:
        raise RuntimeError(out.strip() or "schtasks failed")
    return out.strip()


def delete_task(name):
    subprocess.run(["schtasks", "/Delete", "/F", "/TN", "PageDeck\\" + name],
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return True
