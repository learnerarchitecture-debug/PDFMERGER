import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os, json, re, tempfile, threading, queue, subprocess, webbrowser
import urllib.request, urllib.error
from pathlib import Path
from datetime import datetime
import sys
import fitz
import customtkinter as ctk

import features_pdf as fp
import features_image as fi
import automation as au

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    DND_OK = True
except Exception:
    DND_OK = False

# Windows version check - support Windows 7 to 11
def check_windows_version():
    """Check if Windows version is supported (7 through 11)"""
    if sys.platform != "win32":
        return True
    try:
        import win32api
        version = win32api.GetVersion()
        # win32api.GetVersion returns version in format: major.minor*256
        # Windows 7: 6.1, Windows 8: 6.2, Windows 8.1: 6.3, Windows 10: 10.0, Windows 11: 10.0
        major = version & 0xFF
        minor = version >> 8
        if major == 6 and minor < 1:
            messagebox.showerror("Unsupported Windows Version",
                "This application requires Windows 7 or later.\n"
                "Your current Windows version is not supported.")
            sys.exit(1)
        elif major == 10:
            # Windows 10/11 - both have major=10
            # We'll allow both but show advisory for Win 11 features
            pass
        return True
    except ImportError:
        # win32api not available, proceed with basic check
        try:
            import platform
            win_ver = platform.win32_ver()
            version_str = win_ver[0]
            # Parse version
            if "6." in version_str and int(version_str.split(".")[1]) < 1:
                messagebox.showerror("Unsupported Windows Version",
                    "This application requires Windows 7 or later.\n"
                    "Your current Windows version is not supported.")
                sys.exit(1)
        except Exception:
            pass
    return True

check_windows_version()

APP_NAME = "PDF Suite Pro"
APP_VERSION = "4.1"
SETTINGS_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THUMB_W, THUMB_H = 130, 170
MAX_RECENT = 15

# ─── GitHub auto-update ───
GITHUB_REPO = "learnerarchitecture-debug/PDFMERGER"
UPDATE_API = "https://api.github.com/repos/%s/releases/latest" % GITHUB_REPO
RELEASES_PAGE = "https://github.com/%s/releases" % GITHUB_REPO


def resource_path(name):
    """Path to a bundled data file (works in source and PyInstaller onefile)."""
    base = getattr(sys, "_MEIPASS", None) or os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base, name)


def version_tuple(v):
    parts = []
    for x in re.findall(r"\d+", str(v or ""))[:3]:
        try:
            parts.append(int(x))
        except ValueError:
            pass
    parts += [0] * (3 - len(parts))
    return tuple(parts[:3])


def fetch_latest_release():
    """Return the latest GitHub release dict (raises on network/API errors)."""
    req = urllib.request.Request(UPDATE_API, headers={
        "User-Agent": "PDFSuitePro-%s" % APP_VERSION,
        "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))

# ─── Modern dark theme (2026 design) ───
THEME = {
    "bg": "#0b0e14",          # window background
    "surface": "#10141d",     # cards
    "surface2": "#171c28",    # inputs / wells
    "hover": "#1e2536",       # hover state
    "border": "#232b3b",      # subtle 1px borders
    "fg": "#e7ebf3",          # primary text
    "muted": "#8a93a8",       # secondary text
    "accent": "#5b7cfa",      # primary accent (indigo-blue)
    "accent_h": "#7391ff",    # accent hover
    "accent2": "#8b5cf6",     # violet secondary
    "success": "#22c55e",
    "warning": "#f59e0b",
    "danger": "#ef4444",
    "canvas_bg": "#0c1017",   # thumbnail area
    "selection": "#233052",
    # aliases kept for internal compatibility
    "entry": "#171c28", "frame": "#10141d", "button": "#171c28",
    "button_hover": "#1e2536", "tab_bg": "#171c28", "tab_fg": "#e7ebf3",
    "tab_sel": "#5b7cfa", "notebook_bg": "#0b0e14", "sub_bg": "#0c1017",
    "shadow": "#05070b",
}
FONT = ("Segoe UI", 11)
FONT_BOLD = ("Segoe UI", 11, "bold")
FONT_SM = ("Segoe UI", 10)
FONT_LARGE = ("Segoe UI", 13, "bold")
FONT_TITLE = ("Segoe UI", 20, "bold")


# ─── Modern UI widget helpers ───
def modern_card(parent, **kw):
    """Rounded card surface."""
    opts = dict(fg_color=THEME["surface"], corner_radius=14,
                border_width=1, border_color=THEME["border"])
    opts.update(kw)
    return ctk.CTkFrame(parent, **opts)


def primary_btn(parent, text, command, width=140, height=36, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
        fg_color=THEME["accent"], hover_color=THEME["accent_h"], text_color="#ffffff",
        corner_radius=9, font=FONT_BOLD, **kw)


def ghost_btn(parent, text, command, width=90, height=32, **kw):
    return ctk.CTkButton(parent, text=text, command=command, width=width, height=height,
        fg_color=THEME["surface2"], hover_color=THEME["hover"], text_color=THEME["fg"],
        border_width=1, border_color=THEME["border"], corner_radius=9, font=FONT, **kw)


def accent_entry(parent, **kw):
    opts = dict(height=34, corner_radius=9, fg_color=THEME["surface2"],
                border_color=THEME["border"], text_color=THEME["fg"], font=FONT)
    opts.update(kw)
    return ctk.CTkEntry(parent, **opts)


def dark_check(parent, text, variable, **kw):
    opts = dict(text=text, variable=variable, font=FONT, onvalue=True, offvalue=False,
                checkbox_width=20, checkbox_height=20, corner_radius=6,
                fg_color=THEME["accent"], hover_color=THEME["accent_h"],
                border_color=THEME["border"], text_color=THEME["fg"])
    opts.update(kw)
    return ctk.CTkCheckBox(parent, **opts)


def v_sep(parent, padx=8):
    s = ctk.CTkFrame(parent, width=1, height=22, fg_color=THEME["border"])
    s.pack(side="left", fill="y", padx=padx)
    return s


def modern_combo(parent, values, width=160, height=32):
    return ctk.CTkComboBox(parent, values=list(values), state="readonly",
        width=width, height=height, corner_radius=9,
        fg_color=THEME["surface2"], border_color=THEME["border"],
        button_color=THEME["surface2"], button_hover_color=THEME["hover"],
        dropdown_fg_color=THEME["surface2"], dropdown_hover_color=THEME["hover"],
        text_color=THEME["fg"], font=FONT)


def modern_slider(parent, from_=0.0, to=1.0, steps=50):
    return ctk.CTkSlider(parent, from_=from_, to=to, number_of_steps=steps, height=18,
        fg_color=THEME["surface2"], progress_color=THEME["accent"],
        button_color=THEME["accent"], button_hover_color=THEME["accent_h"])


SIGNATURE_FILE = SETTINGS_DIR / "signature.png"

# Windows DPI awareness for high-resolution screens
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


FEEDBACK_FILE = SETTINGS_DIR / "feedback.json"


def load_feedback():
    if FEEDBACK_FILE.exists():
        try: return json.loads(FEEDBACK_FILE.read_text())
        except: pass
    return {"rating": 0, "review": "", "submitted": False}


def save_feedback(data):
    try: FEEDBACK_FILE.write_text(json.dumps(data, indent=2))
    except: pass


class RatingDialog:
    def __init__(self, parent):
        self.parent = parent
        self.rating = 0
        self.star_btns = []
        self.data = load_feedback()

        self.top = ctk.CTkToplevel(parent)
        self.top.title("Rate & Review")
        self.top.geometry("460x430")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])

        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(card, text="Rate PDF Suite Pro", font=("Segoe UI", 16, "bold"),
                     text_color=THEME["fg"]).pack(pady=(18, 2))
        ctk.CTkLabel(card, text="Your feedback helps improve the app", font=FONT_SM,
                     text_color=THEME["muted"]).pack()

        sf = ctk.CTkFrame(card, fg_color="transparent")
        sf.pack(pady=12)
        for i in range(5):
            btn = ctk.CTkButton(sf, text="\u2606", width=56, height=56, corner_radius=16,
                fg_color=THEME["surface2"], hover_color=THEME["hover"],
                text_color=THEME["muted"], font=("Segoe UI", 26),
                command=lambda v=i + 1: self.set_star(v))
            btn.pack(side="left", padx=4)
            self.star_btns.append(btn)

        self.rating_lbl = ctk.CTkLabel(card, text="Tap a star to rate", font=FONT_BOLD,
                                       text_color=THEME["fg"])
        self.rating_lbl.pack()

        ctk.CTkLabel(card, text="Leave a review (optional)", font=FONT_SM,
                     text_color=THEME["muted"]).pack(anchor="w", padx=18, pady=(14, 2))
        self.review_text = ctk.CTkTextbox(card, height=90, corner_radius=10,
            fg_color=THEME["surface2"], border_width=1, border_color=THEME["border"],
            text_color=THEME["fg"], font=FONT)
        self.review_text.pack(fill="x", padx=18)

        if self.data["submitted"]:
            self.set_star(self.data["rating"], animate=False)
            self.review_text.insert("1.0", self.data.get("review", ""))
            self.review_text.configure(state="disabled")

        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=18, pady=(14, 16))
        primary_btn(bf, "Submit", self.submit, width=110, height=34).pack(side="left")
        ghost_btn(bf, "GitHub issues", self.open_github, width=124).pack(side="left", padx=8)
        ghost_btn(bf, "Close", self.top.destroy, width=90).pack(side="right")

    def set_star(self, v, animate=True):
        self.rating = v
        labels = {1: "Poor", 2: "Below Average", 3: "Average", 4: "Good", 5: "Excellent"}
        self.rating_lbl.configure(text="%d / 5  \u2014  %s" % (v, labels.get(v, "")))
        for i, btn in enumerate(self.star_btns):
            if i < v:
                btn.configure(text="\u2605", text_color="#f5b301", fg_color=THEME["surface2"])
            else:
                btn.configure(text="\u2606", text_color=THEME["muted"], fg_color=THEME["surface2"])

    def submit(self):
        if self.rating == 0:
            messagebox.showerror("Error", "Please select a rating.", parent=self.top)
            return
        self.data["rating"] = self.rating
        self.data["review"] = self.review_text.get("1.0", "end-1c").strip()
        self.data["submitted"] = True
        save_feedback(self.data)
        self.review_text.configure(state="disabled")
        messagebox.showinfo("Thank You",
            "Thank you for your rating (%d/5)!\n\nYour feedback helps improve the app."
            % self.rating, parent=self.top)

    def open_github(self):
        import webbrowser
        webbrowser.open("https://github.com/learnerarchitecture-debug/PDFMERGER/issues")


def load_settings():
    if SETTINGS_FILE.exists():
        try: return json.loads(SETTINGS_FILE.read_text())
        except: pass
    return {"recent_files": []}


def save_settings(data):
    try: SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except: pass


def parse_page_range(text, total):
    if not text or text.strip() == "all":
        return list(range(1, total + 1))
    result = set()
    for part in text.replace(" ", "").split(","):
        if not part: continue
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


def safe_save(doc, path, compress=True, password=None):
    doc.save(path,
        encryption=fitz.PDF_ENCRYPT_AES_256 if password else 0,
        user_pw=password or None, owner_pw=password or None,
        garbage=4 if compress else 1, deflate=compress)


class ProgressDlg:
    def __init__(self, parent, title, maxval):
        self.maxval = max(1, int(maxval))
        self.cur = 0
        self.top = ctk.CTkToplevel(parent)
        self.top.title(title)
        self.top.geometry("400x140")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text=title, font=FONT_BOLD,
                     text_color=THEME["fg"]).pack(anchor="w", padx=16, pady=(14, 2))
        self.pb = ctk.CTkProgressBar(card, height=10, corner_radius=5,
            fg_color=THEME["surface2"], progress_color=THEME["accent"])
        self.pb.set(0)
        self.pb.pack(fill="x", padx=16, pady=(10, 6))
        self.lbl = ctk.CTkLabel(card, text="0 / %d" % self.maxval, font=FONT_SM,
                                text_color=THEME["muted"])
        self.lbl.pack(anchor="w", padx=16)
        self.top.update()

    def step(self, val=None):
        if val is not None:
            self.cur = val
        else:
            self.cur += 1
        try:
            self.pb.set(min(1.0, max(0.0, self.cur / float(self.maxval))))
        except Exception:
            pass
        self.lbl.configure(text="%d / %d" % (self.cur, self.maxval))
        self.top.update()
        for w in self.top.winfo_children():
            try: w.update()
            except: pass

    def close(self):
        try: self.top.destroy()
        except: pass


# ─── Reorder Listbox ───
class ReorderListbox(tk.Listbox):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.bind("<Button-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self._drag = {"index": None, "y": 0}
        self.on_move = None  # optional callback(a, b) when an item is reordered

    def on_press(self, e):
        idx = self.nearest(e.y)
        if idx in self.curselection():
            self._drag = {"index": idx, "y": e.y}
        else:
            self.selection_clear(0, "end")
            self.selection_set(idx)
            self.activate(idx)
            self._drag = {"index": idx, "y": e.y}

    def on_drag(self, e):
        idx = self._drag["index"]
        if idx is None or abs(e.y - self._drag["y"]) < 20: return
        new = self.nearest(e.y)
        if new != idx:
            self.move_item(idx, new)
            self._drag["index"] = new
            self._drag["y"] = e.y

    def on_release(self, e):
        self._drag = {"index": None, "y": 0}

    def move_item(self, a, b):
        """Move item at index a to index b, and notify on_move so the
        underlying data list (merge order) stays in sync."""
        items = list(self.get(0, "end"))
        if not (0 <= a < len(items)) or not (0 <= b < len(items)): return
        item = items.pop(a)
        items.insert(b, item)
        self.delete(0, "end")
        for it in items: self.insert("end", it)
        self.selection_clear(0, "end")
        self.selection_set(b)
        self.activate(b)
        if self.on_move:
            self.on_move(a, b)


# ═══════════════════════ MAIN APP ═══════════════════════
class PDFSuite:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME + " — v" + APP_VERSION)
        try:
            sw = self.root.winfo_screenwidth(); sh = self.root.winfo_screenheight()
        except Exception:
            sw, sh = 1280, 800
        w, h = min(1240, sw - 40), min(800, sh - 70)
        self.root.geometry("%dx%d" % (w, h))
        self.root.minsize(980, 620)
        self.root.configure(fg_color=THEME["bg"])

        self.settings = load_settings()
        self.recent_files = self.settings.get("recent_files", [])
        self._update_dlg = None

        self._build_menu()
        self._build_header()

        self.tabview = ctk.CTkTabview(root, fg_color=THEME["bg"], corner_radius=16, border_width=0,
            anchor="nw",
            segmented_button_fg_color=THEME["surface2"],
            segmented_button_selected_color=THEME["accent"],
            segmented_button_selected_hover_color=THEME["accent_h"],
            segmented_button_unselected_color=THEME["surface2"],
            segmented_button_unselected_hover_color=THEME["hover"],
            text_color=THEME["fg"])
        self.tabview.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        self.tab_merge = self.tabview.add("Merge")
        self.tab_split = self.tabview.add("Split & Edit")
        self.tab_tools = self.tabview.add("PDF Tools")
        self.tab_img = self.tabview.add("Image Tools")
        self.tab_auto = self.tabview.add("Automation")

        self.merge_ui = MergeUI(self.tab_merge, self)
        self.split_ui = SplitUI(self.tab_split, self)
        self.tools_ui = ToolsUI(self.tab_tools, self)
        self.img_ui = ImageToolsUI(self.tab_img, self)
        self.auto_ui = AutomationUI(self.tab_auto, self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)
        self._setup_dnd()
        self._setup_shortcuts()

        # silent update check a few seconds after startup
        if (self.settings or {}).get("auto_update_check", True):
            self.root.after(3500, lambda: self.check_updates(silent=True))

    def _build_header(self):
        """Modern header banner"""
        hdr = modern_card(self.root, corner_radius=16)
        hdr.pack(fill="x", padx=16, pady=(16, 12))
        inner = ctk.CTkFrame(hdr, fg_color="transparent")
        inner.pack(fill="x", padx=16, pady=14)

        badge = ctk.CTkFrame(inner, fg_color=THEME["accent"], corner_radius=12,
                             width=46, height=46)
        badge.pack(side="left")
        badge.pack_propagate(False)
        ctk.CTkLabel(badge, text="PDF", font=("Segoe UI", 13, "bold"),
                     text_color="#ffffff").place(relx=0.5, rely=0.5, anchor="center")

        tf = ctk.CTkFrame(inner, fg_color="transparent")
        tf.pack(side="left", padx=(14, 0))
        ctk.CTkLabel(tf, text=APP_NAME, font=FONT_TITLE,
                     text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(tf, text="Merge  ·  Split & Edit  ·  PDF Tools  ·  Image Tools  ·  Automation",
                     font=FONT_SM, text_color=THEME["muted"]).pack(anchor="w")

        chip2 = ctk.CTkFrame(inner, fg_color=THEME["surface2"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        chip2.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(chip2, text="★  60+ tools", font=FONT_SM,
                     text_color=THEME["accent_h"]).pack(padx=12, pady=5)
        chip1 = ctk.CTkFrame(inner, fg_color=THEME["surface2"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        chip1.pack(side="right")
        ctk.CTkLabel(chip1, text="v" + APP_VERSION, font=FONT_SM,
                     text_color=THEME["muted"]).pack(padx=12, pady=5)

    def _build_menu(self):
        mb = tk.Menu(self.root, bg=THEME["frame"], fg=THEME["fg"], activebackground=THEME["accent"])
        self.root.config(menu=mb)
        fm = tk.Menu(mb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        mb.add_cascade(label="File", menu=fm)
        fm.add_command(label="Open PDF...", command=lambda: self.split_ui.open_pdf())
        fm.add_command(label="Add PDFs to Merge...", command=lambda: self.merge_ui.add_files())
        fm.add_command(label="Add Images...", command=lambda: self.img_ui.add_images())
        fm.add_separator()
        fm.add_command(label="Print PDF...", command=lambda: self.split_ui.print_doc())
        fm.add_separator()
        self.rec_menu = tk.Menu(fm, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        fm.add_cascade(label="Recent Files", menu=self.rec_menu)
        self._refresh_recents()
        fm.add_separator()
        fm.add_command(label="Exit", command=self.on_close)
        em = tk.Menu(mb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        mb.add_cascade(label="Edit", menu=em)
        em.add_command(label="Insert Blank Pages", command=lambda: self.split_ui.insert_blank())
        em.add_command(label="Duplicate Pages", command=lambda: self.split_ui.dup_pgs())
        em.add_command(label="Mirror / Flip Pages", command=lambda: self.split_ui.mirror_pages())
        em.add_command(label="Convert to Grayscale", command=lambda: self.split_ui.to_grayscale())
        em.add_separator()
        em.add_command(label="Remove Metadata", command=lambda: self.tools_ui.remove_metadata())
        em.add_command(label="Redact Text", command=lambda: self.tools_ui.redact_text())
        tm = tk.Menu(mb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        mb.add_cascade(label="Split", menu=tm)
        tm.add_command(label="Split by Page Count", command=lambda: self.split_ui.split_by_count())
        tm.add_command(label="Split Even/Odd Pages", command=lambda: self.split_ui.split_even_odd())
        tm.add_command(label="Extract All Images", command=lambda: self.split_ui.extract_images())
        tm.add_command(label="Extract All Text", command=lambda: self.split_ui.extract_text())
        vm = tk.Menu(mb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        mb.add_cascade(label="View", menu=vm)
        vm.add_command(label="Search in PDF", command=lambda: self.split_ui.search_pdf())
        vm.add_command(label="Go to Page...", command=lambda: self.split_ui.goto_page())
        hm = tk.Menu(mb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"])
        mb.add_cascade(label="Help", menu=hm)
        hm.add_command(label="Check for Updates", command=self.check_updates)
        hm.add_separator()
        hm.add_command(label="Rate & Review", command=self.open_rating)
        hm.add_separator()
        hm.add_command(label="About", command=self.show_about)

    def _refresh_recents(self):
        self.rec_menu.delete(0, "end")
        for f in self.recent_files:
            self.rec_menu.add_command(label=f, command=lambda p=f: self.load_recent(p))
        if not self.recent_files:
            self.rec_menu.add_command(label="(no recent files)", state="disabled")

    def load_recent(self, path):
        if not os.path.isfile(path):
            self.recent_files = [f for f in self.recent_files if f != path]
            self._refresh_recents()
            return
        self.split_ui.load_pdf(path)

    def add_recent(self, path):
        path = os.path.abspath(path)
        self.recent_files = [f for f in self.recent_files if f != path]
        self.recent_files.insert(0, path)
        if len(self.recent_files) > MAX_RECENT: self.recent_files = self.recent_files[:MAX_RECENT]
        self._refresh_recents()

    def on_close(self):
        self.settings["recent_files"] = self.recent_files
        save_settings(self.settings)
        try:
            self.auto_ui.stop_all()
        except Exception:
            pass
        self.root.destroy()

    def open_rating(self):
        RatingDialog(self.root)

    def show_about(self):
        messagebox.showinfo("About PDF Suite Pro",
            "PDF Suite Pro v" + APP_VERSION + "\n\nCreator: AYUSH GUPTA\n\n"
            "PDF Tools: merge, split, sign, watermark, header/footer, Bates,\n"
            "N-up, normalize, crop, bookmarks, metadata, compare, repair,\n"
            "sanitize, redaction, passwords, compress, QR stamps, mail merge.\n\n"
            "Image Tools: compress, convert, resize, crop/trim, rotate, filter,\n"
            "watermark, EXIF strip, borders, icons, images to PDF, PDF to images.\n\n"
            "Automation: recipes, batch queue, watch folders, scheduler,\n"
            "email reports and a command line companion (PDFSuiteCLI.exe).")

    # ── drag & drop ──
    def _setup_dnd(self):
        if not DND_OK:
            return
        try:
            import types
            from tkinterdnd2.TkinterDnD import DnDWrapper
            TkinterDnD._require(self.root)
            self.root.drop_target_register = types.MethodType(
                DnDWrapper.drop_target_register, self.root)
            self.root.dnd_bind = types.MethodType(DnDWrapper.dnd_bind, self.root)
            self.root._dnd_bind = types.MethodType(DnDWrapper._dnd_bind, self.root)
            self.root._substitute_dnd = types.MethodType(
                DnDWrapper._substitute_dnd, self.root)
            self.root._subst_format_str_dnd = DnDWrapper._subst_format_str_dnd
            self.root.drop_target_register(DND_FILES)
            self.root.dnd_bind("<<Drop>>", self._on_drop_files)
        except Exception:
            pass

    def _on_drop_files(self, event):
        import re
        raw = str(event.data)
        try:
            paths = list(self.root.tk.splitlist(raw))
        except Exception:
            paths = []
        tokens = []
        for m in re.finditer(r"\{([^}]*)\}|\"([^\"]*)\"|([^\s]+)", raw):
            tok = m.group(1) or m.group(2) or m.group(3)
            if tok:
                tokens.append(tok.strip('"'))
        seen = set()
        all_paths = []
        for p in list(paths) + tokens:
            p = p.strip('"').strip()
            if p and p not in seen:
                seen.add(p)
                all_paths.append(p)
        pdfs = [p for p in all_paths
                if p.lower().endswith(".pdf") and os.path.isfile(p)]
        imgs = [p for p in all_paths
                if os.path.splitext(p)[1].lower() in fi.IMG_EXTS and os.path.isfile(p)]
        if pdfs:
            self.merge_ui.add_files_to_merge(pdfs)
        if imgs:
            self.img_ui.add_images_to_list(imgs)
        if pdfs or imgs:
            self.tabview.set("Merge" if pdfs else "Image Tools")
        return "copy"

    # ── keyboard shortcuts ──
    def _setup_shortcuts(self):
        r = self.root
        r.bind("<Control-o>", lambda e: self.split_ui.open_pdf())
        r.bind("<Control-m>", lambda e: self.merge_ui.add_files())
        r.bind("<Control-p>", lambda e: self.split_ui.print_doc())
        r.bind("<Control-s>", lambda e: self.split_ui.save_as())
        r.bind("<Control-f>", lambda e: self.split_ui.search_pdf())

    # ── background jobs with progress ──
    def run_bg(self, work, title="Working…", on_done=None, maxval=100):
        """Run work(progress_cb) in a thread with a progress dialog.
        progress_cb(i, total) updates the bar; exceptions show a messagebox."""
        q = queue.Queue()
        dlg = ProgressDlg(self.root, title, maxval)

        def worker():
            try:
                res = work(lambda i, total=None: q.put(("p", i, total)))
                q.put(("done", res))
            except Exception as e:
                q.put(("err", e))

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                while True:
                    item = q.get_nowait()
                    if item[0] == "p":
                        if item[2]:
                            dlg.maxval = max(1, int(item[2]))
                        dlg.step(item[1])
                    elif item[0] == "done":
                        dlg.close()
                        if on_done:
                            on_done(item[1])
                        return
                    else:
                        dlg.close()
                        messagebox.showerror("Error", str(item[1]))
                        return
            except queue.Empty:
                pass
            self.root.after(120, poll)

        self.root.after(120, poll)

    # ── update checker ──
    def check_updates(self, silent=False):
        """Check GitHub for a newer release and offer to download + install."""
        def worker():
            res = {"ok": True, "rel": None, "err": None}
            try:
                res["rel"] = fetch_latest_release()
            except urllib.error.HTTPError as e:
                if e.code != 404:
                    res["ok"] = False
                    res["err"] = "GitHub error %s" % e.code
            except Exception as e:
                res["ok"] = False
                res["err"] = str(e)
            try:
                self.root.after(0, lambda: self._update_result(res, silent))
            except Exception:
                pass

        threading.Thread(target=worker, daemon=True).start()

    def _update_result(self, res, silent):
        if not res["ok"]:
            if not silent:
                messagebox.showwarning("Check for updates",
                    "Could not check for updates right now.\n%s" % res["err"])
            return
        data = res["rel"]
        if not data:
            if not silent:
                messagebox.showinfo("Check for updates",
                    "No releases have been published yet on GitHub.")
            return
        latest = (data.get("tag_name") or "").lstrip("vV")
        if not latest or version_tuple(latest) <= version_tuple(APP_VERSION):
            if not silent:
                messagebox.showinfo("Check for updates",
                    "You are running the latest version (v%s)." % APP_VERSION)
            return
        if silent and (self.settings or {}).get("skip_version") == latest:
            return
        dlg = getattr(self, "_update_dlg", None)
        if dlg is not None and dlg.winfo_exists():
            if not silent:
                try:
                    dlg.lift()
                    dlg.focus_force()
                except Exception:
                    pass
            return
        self._update_dlg = UpdateDialog(self.root, self, data, latest)


# ═══════════════════════ MERGE UI ═══════════════════════
class MergeUI:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.files = []
        self.var_pw = tk.StringVar()
        self.var_compress = tk.BooleanVar(value=True)
        self._task_queue = queue.Queue()
        self._progress = None
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self.parent, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=14, pady=14)

        # ── toolbar ──
        tb = modern_card(f, corner_radius=12); tb.pack(fill="x", pady=(0, 10))
        t = ctk.CTkFrame(tb, fg_color="transparent"); t.pack(fill="x", padx=10, pady=10)
        primary_btn(t, "+  Add PDFs", self.add_files, width=126, height=34).pack(side="left")
        ghost_btn(t, "Remove", self.rem_sel, width=84).pack(side="left", padx=(8, 0))
        ghost_btn(t, "Duplicate", self.dup_sel, width=88).pack(side="left", padx=(8, 0))
        ghost_btn(t, "Clear", self.clear_all, width=70).pack(side="left", padx=(8, 0))

        v_sep(t, padx=10)
        ctk.CTkLabel(t, text="Reorder", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(0, 6))
        for t_, c_ in [("↑", self.move_file_up), ("↓", self.move_file_down),
                       ("⇡", self.move_file_top), ("⇣", self.move_file_bottom)]:
            ghost_btn(t, t_, c_, width=38).pack(side="left", padx=2)

        v_sep(t, padx=10)
        ctk.CTkLabel(t, text="Page range", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(0, 6))
        self.rng_var = tk.StringVar(value="all")
        accent_entry(t, textvariable=self.rng_var, width=110, height=32).pack(side="left")
        ghost_btn(t, "Apply", self.apply_range, width=70).pack(side="left", padx=(8, 0))

        # ── file list card ──
        lc = modern_card(f); lc.pack(fill="both", expand=True, pady=(0, 10))
        hdr = ctk.CTkFrame(lc, fg_color="transparent"); hdr.pack(fill="x", padx=14, pady=(12, 6))
        ctk.CTkLabel(hdr, text="Merge order", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(side="left")
        ctk.CTkLabel(hdr, text="Drag rows to reorder — the merged PDF follows this list",
                     font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(10, 0))
        self.info_lbl = ctk.CTkLabel(hdr, text="0 files", font=FONT_SM,
                                     text_color=THEME["muted"])
        self.info_lbl.pack(side="right")

        lw = ctk.CTkFrame(lc, fg_color="transparent"); lw.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.lb = ReorderListbox(lw, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0, height=12)
        sc = ctk.CTkScrollbar(lw, command=self.lb.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.lb.configure(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y", padx=(8, 0))
        self.lb.bind("<<ListboxSelect>>", self.on_sel)
        self.lb.on_move = self._on_files_reordered
        self._menu = tk.Menu(self.lb, tearoff=0, bg=THEME["frame"], fg=THEME["fg"],
                             activebackground=THEME["accent"], activeforeground="#ffffff")
        self._menu.add_command(label="Remove", command=self.rem_sel)
        self._menu.add_command(label="Duplicate", command=self.dup_sel)
        self._menu.add_separator()
        self._menu.add_command(label="Move to top", command=self.move_file_top)
        self._menu.add_command(label="Move to bottom", command=self.move_file_bottom)
        self._menu.add_separator()
        self._menu.add_command(label="Open file location", command=self._open_loc)
        self.lb.bind("<Button-3>", self._ctx_menu)

        # ── output card ──
        out = modern_card(f, corner_radius=12); out.pack(fill="x", pady=(0, 10))
        o = ctk.CTkFrame(out, fg_color="transparent"); o.pack(fill="x", padx=10, pady=10)
        primary_btn(o, "Merge PDFs", self.merge, width=150, height=38).pack(side="right")
        dark_check(o, "Compress", self.var_compress).pack(side="right", padx=(0, 16))
        self.pw_e = accent_entry(o, textvariable=self.var_pw, width=150, height=34)
        self.pw_e.configure(show="*")
        self.pw_e.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(o, text="Password", font=FONT_SM, text_color=THEME["muted"]).pack(side="right", padx=(16, 0))
        ctk.CTkLabel(o, text="Output", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        self.out_var = tk.StringVar(value="merged.pdf")
        accent_entry(o, textvariable=self.out_var, height=34).pack(side="left", fill="x", expand=True, padx=(0, 8))

        # ── advanced card ──
        adv = modern_card(f, corner_radius=12); adv.pack(fill="x")
        a = ctk.CTkFrame(adv, fg_color="transparent"); a.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(a, text="Advanced", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        ghost_btn(a, "Insert PDF at page…", self.insert_at_page, width=150).pack(side="left", padx=2)
        ghost_btn(a, "Add cover page…", self.add_cover, width=140).pack(side="left", padx=2)
        self.alt_var = tk.BooleanVar(value=False)
        dark_check(a, "Alternate (interleave all)", self.alt_var).pack(side="right")

    def add_files(self):
        ps = filedialog.askopenfilenames(title="Select PDFs", filetypes=[("PDF", "*.pdf")])
        for p in ps:
            if not any(f["path"] == p for f in self.files):
                self.files.append({"path": p, "pages": "all"})
                self.lb.insert("end", os.path.basename(p) + "  [all]")
                self.app.add_recent(p)
        self._upd_info()

    def add_files_to_merge(self, paths):
        for p in paths:
            if not any(f["path"] == p for f in self.files):
                self.files.append({"path": p, "pages": "all"})
                self.lb.insert("end", os.path.basename(p) + "  [all]")
                self.app.add_recent(p)
        self._upd_info()

    def _ctx_menu(self, e):
        idx = self.lb.nearest(e.y)
        self.lb.selection_clear(0, "end")
        self.lb.selection_set(idx)
        self.lb.activate(idx)
        try:
            self._menu.tk_popup(e.x_root, e.y_root)
        finally:
            try:
                self._menu.grab_release()
            except Exception:
                pass

    def _open_loc(self):
        s = self.lb.curselection()
        if not s:
            return
        p = self.files[s[0]]["path"]
        try:
            os.startfile(os.path.dirname(os.path.abspath(p)))
        except Exception:
            pass

    def rem_sel(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i); del self.files[i]
        self._upd_info()

    def clear_all(self):
        self.lb.delete(0, "end"); self.files.clear(); self._upd_info()

    def on_sel(self, e):
        s = self.lb.curselection()
        self.rng_var.set(self.files[s[0]]["pages"] if s else "all")

    def apply_range(self):
        s = self.lb.curselection()
        if not s: return
        i = s[0]; r = self.rng_var.get().strip() or "all"
        self.files[i]["pages"] = r
        self.lb.delete(i)
        self.lb.insert(i, os.path.basename(self.files[i]["path"]) + "  [%s]" % r)
        self.lb.selection_set(i)

    def _upd_info(self):
        self.info_lbl.configure(text="%d file(s)  —  drag to reorder" % len(self.files))

    def _on_files_reordered(self, a, b):
        """Keep self.files in sync when the user drag-reorders the list,
        so the merge output follows the visible order."""
        if 0 <= a < len(self.files) and 0 <= b < len(self.files):
            f = self.files.pop(a)
            self.files.insert(b, f)

    def dup_sel(self):
        for i in reversed(self.lb.curselection()):
            f = self.files[i]
            self.files.insert(i + 1, dict(f))
            self.lb.insert(i + 1, os.path.basename(f["path"]) + "  [%s]" % f["pages"])

    def _move_file(self, direction):
        """Move selected file by direction (-1 = up, 1 = down)"""
        sel = self.lb.curselection()
        if not sel or not self.files: return
        i = sel[0]
        new_i = i + direction
        if new_i < 0 or new_i >= len(self.files): return
        self.files[i], self.files[new_i] = self.files[new_i], self.files[i]
        item_i = self.lb.get(i)
        item_j = self.lb.get(new_i)
        self.lb.delete(i)
        self.lb.insert(i, item_j)
        self.lb.delete(new_i)
        self.lb.insert(new_i, item_i)
        self.lb.selection_set(new_i)
        self.lb.activate(new_i)

    def move_file_up(self):
        self._move_file(-1)

    def move_file_down(self):
        self._move_file(1)

    def move_file_top(self):
        sel = self.lb.curselection()
        if not sel or not self.files: return
        i = sel[0]
        if i == 0: return
        item = self.lb.get(i)
        f = self.files[i]
        self.files.pop(i)
        self.lb.delete(i)
        self.files.insert(0, f)
        self.lb.insert(0, item)
        self.lb.selection_set(0)
        self.lb.activate(0)

    def move_file_bottom(self):
        sel = self.lb.curselection()
        if not sel or not self.files: return
        i = sel[0]
        if i == len(self.files) - 1: return
        item = self.lb.get(i)
        f = self.files[i]
        self.files.pop(i)
        self.lb.delete(i)
        self.files.append(f)
        self.lb.insert("end", item)
        self.lb.selection_set("end")
        self.lb.activate("end")

    def insert_at_page(self):
        if not self.files:
            messagebox.showerror("Error", "Add files first.")
            return
        path = filedialog.askopenfilename(title="Select PDF to insert", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pg = simpledialog.askinteger("Insert At", "Insert at position (0-based, 0=beginning):", minvalue=0, initialvalue=1)
        if pg is None: return
        pos = min(pg, len(self.files))
        self.files.insert(pos, {"path": path, "pages": "all"})
        self.lb.insert(pos, os.path.basename(path) + "  [all]")
        self._upd_info()

    def add_cover(self):
        path = filedialog.askopenfilename(title="Select cover page PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        self.files.insert(0, {"path": path, "pages": "all"})
        self.lb.insert(0, "★ " + os.path.basename(path) + "  [cover]")
        self._upd_info()

    def merge(self):
        if len(self.files) < 1:
            messagebox.showerror("Error", "Add at least 1 PDF file.")
            return
        out = self.out_var.get().strip() or "merged.pdf"
        if not out.endswith(".pdf"): out += ".pdf"
        if not os.path.dirname(out):
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=out)
            if not out: return
        pw = self.var_pw.get().strip()
        comp = self.var_compress.get()
        alt = self.alt_var.get()
        self._progress = None
        self._merge_cancel = False
        d = {"out": out, "pw": pw, "comp": comp, "alt": alt,
             "files": list(self.files)}
        threading.Thread(target=self._merge_worker, args=(d,), daemon=True).start()
        self._poll_merge_queue()

    def _poll_merge_queue(self):
        try:
            while True:
                cmd, data = self._task_queue.get_nowait()
                if cmd == "progress_init":
                    title, mx = data
                    self._progress = ProgressDlg(self.parent, title, mx)
                elif cmd == "progress":
                    self._progress.step(data)
                elif cmd == "progress_close":
                    if self._progress: self._progress.close(); self._progress = None
                elif cmd == "done":
                    out = data
                    messagebox.showinfo("Success", "Merged into:\n%s" % out)
                    try: os.startfile(os.path.dirname(os.path.abspath(out)))
                    except: pass
                elif cmd == "error":
                    messagebox.showerror("Error", "Merge failed:\n%s" % data)
        except queue.Empty:
            pass
        self.parent.after(200, self._poll_merge_queue)

    def _merge_worker(self, d):
        q = self._task_queue
        try:
            if d["alt"]:
                pages_by_file = []
                for f in d["files"]:
                    src = fitz.open(f["path"])
                    if src.is_encrypted:
                        q.put(("error", "Cannot merge encrypted:\n%s" % f["path"]))
                        src.close(); return
                    pgs = parse_page_range(f["pages"], len(src))
                    pages_by_file.append((src, pgs))
                max_pgs = max(len(p[1]) for p in pages_by_file) if pages_by_file else 0
                writer = fitz.open()
                q.put(("progress_init", ("Merging (alternate)...", max_pgs * len(pages_by_file))))
                cnt = 0
                for i in range(max_pgs):
                    for src, pgs in pages_by_file:
                        if i < len(pgs):
                            writer.insert_pdf(src, from_page=pgs[i] - 1, to_page=pgs[i] - 1)
                            cnt += 1; q.put(("progress", cnt))
                for src, _ in pages_by_file: src.close()
                q.put(("progress_close", None))
                safe_save(writer, d["out"], d["comp"], d["pw"]); writer.close()
            else:
                writer = fitz.open()
                q.put(("progress_init", ("Merging...", len(d["files"]))))
                for idx, f in enumerate(d["files"]):
                    src = fitz.open(f["path"])
                    if src.is_encrypted:
                        q.put(("error", "Cannot merge encrypted:\n%s" % f["path"]))
                        src.close(); writer.close(); q.put(("progress_close", None)); return
                    pgs = parse_page_range(f["pages"], len(src))
                    for p in pgs: writer.insert_pdf(src, from_page=p - 1, to_page=p - 1)
                    src.close(); q.put(("progress", idx + 1))
                safe_save(writer, d["out"], d["comp"], d["pw"]); writer.close()
                q.put(("progress_close", None))
            q.put(("done", d["out"]))
        except Exception as e:
            q.put(("error", str(e)))
            try: q.put(("progress_close", None))
            except: pass


# ═══════════════════════ SPLIT UI ═══════════════════════
class SplitUI:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.doc = None; self.doc_path = None
        self.page_images = []; self.page_rots = {}; self.page_del = set()
        self._sel = set(); self._search_highlights = set()
        self._undo_stack = []; self._redo_stack = []
        self.var_pw = tk.StringVar()
        self.var_compress = tk.BooleanVar(value=True)
        self._temp_files = []
        self._task_queue = queue.Queue()
        self._last_cols = None
        self._build()

    def _build(self):
        f = ctk.CTkFrame(self.parent, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=14, pady=14)

        # ── top bar ──
        top = modern_card(f, corner_radius=12); top.pack(fill="x", pady=(0, 10))
        t = ctk.CTkFrame(top, fg_color="transparent"); t.pack(fill="x", padx=10, pady=10)
        primary_btn(t, "Open PDF", self.open_pdf, width=112, height=34).pack(side="left")
        self.file_lbl = ctk.CTkLabel(t, text="No file loaded", font=FONT_BOLD,
                                     text_color=THEME["muted"])
        self.file_lbl.pack(side="left", padx=(14, 6))
        self.pg_lbl = ctk.CTkLabel(t, text="", font=FONT_SM, text_color=THEME["muted"])
        self.pg_lbl.pack(side="left")
        ghost_btn(t, "Unlock", self.unlock, width=84).pack(side="right")
        self.pw_e = accent_entry(t, textvariable=self.var_pw, width=130, height=32)
        self.pw_e.configure(show="*")
        self.pw_e.pack(side="right", padx=(8, 8))
        ctk.CTkLabel(t, text="Password", font=FONT_SM, text_color=THEME["muted"]).pack(side="right")

        # ── thumbnail area ──
        view = modern_card(f); view.pack(fill="both", expand=True, pady=(0, 10))
        inner = ctk.CTkFrame(view, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=10, pady=10)
        inner.grid_rowconfigure(0, weight=1); inner.grid_columnconfigure(0, weight=1)
        self.canvas = tk.Canvas(inner, bg=THEME["canvas_bg"], highlightthickness=0)
        vs = ctk.CTkScrollbar(inner, command=self.canvas.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        hs = ctk.CTkScrollbar(inner, orientation="horizontal", command=self.canvas.xview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        vs.grid(row=0, column=1, sticky="ns", padx=(6, 0))
        hs.grid(row=1, column=0, sticky="ew", pady=(6, 0))
        self.tc = tk.Frame(self.canvas, bg=THEME["canvas_bg"])
        self.cw = self.canvas.create_window((0, 0), window=self.tc, anchor="nw")
        self.tc.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, e):
        self.canvas.itemconfig(self.cw, width=e.width)
        cols = max(1, e.width // (THUMB_W + 32))
        if self.doc and cols != self._last_cols:
            self.parent.after(30, self._render_thumbs)

        # ── actions card ──
        act = modern_card(f, corner_radius=12); act.pack(fill="x", pady=(0, 10))
        r1 = ctk.CTkFrame(act, fg_color="transparent"); r1.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(r1, text="Page order", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        for t_, c_ in [("↑ Up", self.move_up), ("↓ Down", self.move_down),
                       ("⇡ Top", self.move_top), ("⇣ Bottom", self.move_bottom)]:
            ghost_btn(r1, t_, c_, width=76).pack(side="left", padx=2)
        v_sep(r1, padx=8)
        ctk.CTkLabel(r1, text="Transform", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        for t_, c_ in [("Rotate CW", self.rot_cw), ("Rotate CCW", self.rot_ccw),
                       ("Mirror", self.mirror_pages), ("Grayscale", self.to_grayscale)]:
            ghost_btn(r1, t_, c_, width=92).pack(side="left", padx=2)
        ghost_btn(r1, "Print", self.print_doc, width=70).pack(side="left", padx=2)
        self.redo_btn = ghost_btn(r1, "Redo ↷", self.redo, width=76)
        self.redo_btn.pack(side="right", padx=(4, 0))
        self.undo_btn = ghost_btn(r1, "Undo ↶", self.undo, width=76)
        self.undo_btn.pack(side="right", padx=4)
        self._update_undo_buttons()

        r2 = ctk.CTkFrame(act, fg_color="transparent"); r2.pack(fill="x", padx=10, pady=(4, 10))
        ctk.CTkLabel(r2, text="Pages", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        ghost_btn(r2, "Delete", self.del_sel, width=76).pack(side="left", padx=2)
        ghost_btn(r2, "Restore", self.restore, width=82).pack(side="left", padx=2)
        ghost_btn(r2, "Insert blank", self.insert_blank, width=100).pack(side="left", padx=2)
        ghost_btn(r2, "Duplicate", self.dup_pgs, width=88).pack(side="left", padx=2)
        v_sep(r2, padx=8)
        ctk.CTkLabel(r2, text="Export", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(2, 8))
        self.ext_var = tk.StringVar()
        accent_entry(r2, textvariable=self.ext_var, width=110, height=32).pack(side="left", padx=(0, 6))
        ghost_btn(r2, "Extract", self.extract_range, width=78).pack(side="left", padx=2)
        ghost_btn(r2, "Split all", self.split_all, width=84).pack(side="left", padx=2)
        ghost_btn(r2, "Bookmarks", self.split_bookmarks, width=96).pack(side="left", padx=2)
        dark_check(r2, "Compress", self.var_compress).pack(side="right")
        primary_btn(r2, "Save As", self.save_as, width=100, height=34).pack(side="right", padx=(0, 14))

    def open_pdf(self):
        p = filedialog.askopenfilename(title="Open PDF", filetypes=[("PDF", "*.pdf")])
        if p: self.load_pdf(p)

    def load_pdf(self, path):
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                self._clear_thumbs(); self.doc = doc; self.doc_path = path
                self.file_lbl.configure(text=os.path.basename(path), text_color=THEME["warning"])
                self.pg_lbl.configure(text="(encrypted)"); self.app.add_recent(path); return
            self._set_doc(doc, path); self.app.add_recent(path)
        except Exception as e:
            messagebox.showerror("Error", "Cannot open:\n%s" % e)

    def unlock(self):
        if not self.doc or not self.doc.is_encrypted: return
        result = self.doc.authenticate(self.var_pw.get())
        if result == 0:
            messagebox.showerror("Error", "Incorrect password"); return
        try:
            _ = self.doc.page_count
        except Exception:
            messagebox.showerror("Error", "Incorrect password - cannot read content"); return
        self._set_doc(self.doc, self.doc_path)

    def _set_doc(self, doc, path):
        self.doc = doc; self.doc_path = path
        self.page_rots.clear(); self.page_del.clear(); self._sel.clear()
        self._search_highlights.clear()
        self._undo_stack.clear(); self._redo_stack.clear(); self._update_undo_buttons()
        self.file_lbl.configure(text=os.path.basename(path), text_color=THEME["fg"])
        self.pg_lbl.configure(text="%d page(s)" % len(doc))
        self._render_thumbs()

    def _clear_thumbs(self):
        for w in self.tc.winfo_children(): w.destroy()
        self.page_images.clear()
        for tmp in self._temp_files:
            try: os.unlink(tmp)
            except: pass
        self._temp_files.clear()

    def _render_thumbs(self):
        self._clear_thumbs()
        if not self.doc:
            self._last_cols = None
            holder = tk.Frame(self.tc, bg=THEME["canvas_bg"])
            holder.pack(pady=60)
            tk.Label(holder, text="Open a PDF to see page thumbnails here",
                     font=FONT, bg=THEME["canvas_bg"], fg=THEME["muted"]).pack()
            return
        cols = max(1, self.canvas.winfo_width() // (THUMB_W + 32))
        self._last_cols = cols
        self._thumb_frames = []
        rf = None; rc = 0
        for i in range(len(self.doc)):
            if rc % cols == 0:
                rf = tk.Frame(self.tc, bg=THEME["canvas_bg"]); rf.pack(fill="x", pady=6)
            rc += 1
            sel = i in self._sel; hilite = i in self._search_highlights
            deleted = i in self.page_del
            if deleted:
                wrap_bg, border, cap = "#2a1216", THEME["danger"], THEME["danger"]
            elif sel:
                wrap_bg, border, cap = "#1b2340", THEME["accent"], THEME["accent_h"]
            elif hilite:
                wrap_bg, border, cap = "#2a2212", THEME["warning"], THEME["warning"]
            else:
                wrap_bg, border, cap = THEME["canvas_bg"], THEME["border"], THEME["muted"]
            f2 = tk.Frame(rf, bg=wrap_bg, highlightthickness=2, highlightbackground=border)
            f2.pack(side="left", padx=8, pady=4)
            self._thumb_frames.append((f2, i))
            f2.bind("<ButtonPress-1>", lambda e, idx=i: self._thumb_drag_start(idx, e))
            f2.bind("<B1-Motion>", self._thumb_drag_motion)
            f2.bind("<ButtonRelease-1>", self._thumb_drag_end)
            pg = self.doc[i]
            mat = fitz.Matrix(THUMB_W / pg.rect.width, THUMB_H / pg.rect.height)
            pix = pg.get_pixmap(matrix=mat)
            tmp = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)
            tmp.write(pix.tobytes("ppm")); tmp.close()
            self._temp_files.append(tmp.name)
            photo = tk.PhotoImage(file=tmp.name)
            self.page_images.append(photo)
            f2.configure(highlightbackground=border, highlightcolor=border)
            lbl = tk.Label(f2, image=photo, relief="flat", bd=0, bg=wrap_bg)
            lbl.pack(padx=3, pady=(3, 2))
            lbl.bind("<ButtonPress-1>", lambda e, idx=i: self._thumb_drag_start(idx, e))
            lbl.bind("<B1-Motion>", self._thumb_drag_motion)
            lbl.bind("<ButtonRelease-1>", self._thumb_drag_end)
            # Page label with status
            status = ""
            if deleted:
                status = " · Deleted"
            elif sel:
                status = " · Selected"
            elif hilite:
                status = " · Match"
            rot = self.page_rots.get(i, 0)
            if rot:
                status += " · %d°" % rot
            tk.Label(f2, text="Page %d%s" % (i + 1, status), font=FONT_SM,
                    bg=wrap_bg, fg=cap).pack(pady=(0, 4), padx=4)

    def _pg_label(self, i):
        parts = ["Page %d" % (i + 1)]
        if i in self.page_del: parts.append("[DEL]")
        rot = self.page_rots.get(i, 0)
        if rot: parts.append("%d\xb0" % rot)
        return " ".join(parts)

    def _toggle(self, idx):
        if idx in self._sel: self._sel.discard(idx)
        else: self._sel.add(idx)
        self.parent.after(50, self._render_thumbs)

    # ── drag to reorder pages (thumbnails) ──
    def _thumb_drag_start(self, idx, e):
        self._tdrag = {"from": idx, "x": e.x_root, "y": e.y_root, "active": False}

    def _thumb_drag_motion(self, e):
        d = getattr(self, "_tdrag", None)
        if not d:
            return
        if not d["active"] and abs(e.y_root - d["y"]) + abs(e.x_root - d["x"]) > 14:
            d["active"] = True
            try:
                self.canvas.configure(cursor="fleur")
            except Exception:
                pass

    def _thumb_drag_end(self, e):
        d = getattr(self, "_tdrag", None)
        self._tdrag = None
        try:
            self.canvas.configure(cursor="")
        except Exception:
            pass
        if not d or not self.doc:
            return
        if not d["active"]:
            self._toggle(d["from"])
            return
        target = self._thumb_at(e.x_root, e.y_root)
        if target is None or target == d["from"]:
            return
        order = list(range(len(self.doc)))
        item = order.pop(d["from"])
        order.insert(target, item)
        self._save_state()
        self._reorder_document(order)

    def _thumb_at(self, x, y):
        for w, idx in getattr(self, "_thumb_frames", []):
            try:
                wx, wy = w.winfo_rootx(), w.winfo_rooty()
                if wx <= x <= wx + w.winfo_width() and wy <= y <= wy + w.winfo_height():
                    return idx
            except Exception:
                continue
        return None

    def print_doc(self):
        if not self.doc or not self.doc_path:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        try:
            fp.print_pdf(self.doc_path)
            messagebox.showinfo("Print", "Sent to the default printer:\n%s"
                                % os.path.basename(self.doc_path))
        except Exception as e:
            messagebox.showerror("Error", "Printing failed:\n%s" % e)

    # ── undo / redo ──
    def _save_state(self):
        self._undo_stack.append({
            "rots": dict(self.page_rots),
            "del": set(self.page_del),
            "sel": set(self._sel),
        })
        self._redo_stack.clear()
        self._update_undo_buttons()

    def _update_undo_buttons(self):
        self.undo_btn.configure(state="normal" if self._undo_stack else "disabled")
        self.redo_btn.configure(state="normal" if self._redo_stack else "disabled")

    def undo(self):
        if not self._undo_stack: return
        self._redo_stack.append({
            "rots": dict(self.page_rots),
            "del": set(self.page_del),
            "sel": set(self._sel),
        })
        state = self._undo_stack.pop()
        self.page_rots = state["rots"]
        self.page_del = state["del"]
        self._sel = state["sel"]
        self._render_thumbs()
        self._update_undo_buttons()

    def redo(self):
        if not self._redo_stack: return
        self._undo_stack.append({
            "rots": dict(self.page_rots),
            "del": set(self.page_del),
            "sel": set(self._sel),
        })
        state = self._redo_stack.pop()
        self.page_rots = state["rots"]
        self.page_del = state["del"]
        self._sel = state["sel"]
        self._render_thumbs()
        self._update_undo_buttons()

    # ── page actions ──
    def rot_cw(self):
        if not self._sel or not self.doc: return
        self._save_state()
        for i in list(self._sel):
            self.page_rots[i] = (self.page_rots.get(i, 0) + 90) % 360
        self._sel.clear(); self._render_thumbs()

    def rot_ccw(self):
        if not self._sel or not self.doc: return
        self._save_state()
        for i in list(self._sel):
            self.page_rots[i] = (self.page_rots.get(i, 0) - 90) % 360
        self._sel.clear(); self._render_thumbs()

    def del_sel(self):
        if not self._sel: return
        self._save_state()
        self.page_del.update(self._sel)
        self._sel.clear(); self._render_thumbs()

    def restore(self):
        if not self.page_rots and not self.page_del: return
        self._save_state()
        self.page_rots.clear(); self.page_del.clear(); self._sel.clear(); self._render_thumbs()

    def dup_pgs(self):
        idxs = sorted(self._sel)
        if not idxs: return
        self._undo_stack.clear(); self._redo_stack.clear(); self._update_undo_buttons()
        new = fitz.open()
        for i in range(len(self.doc)):
            if i not in self.page_del:
                new.insert_pdf(self.doc, from_page=i, to_page=i)
                if i in idxs:
                    new.insert_pdf(self.doc, from_page=i, to_page=i)
        self.doc.close(); self._set_doc(new, self.doc_path)

    def _move_pages(self, direction):
        """Move selected pages up (-1) or down (+1)"""
        if not self._sel or not self.doc: return
        self._save_state()
        idxs = sorted(self._sel)
        total = len(self.doc)
        
        if direction == -1:
            if idxs[0] == 0: return
            new_order = list(range(total))
            for idx in idxs:
                new_order[idx], new_order[idx - 1] = new_order[idx - 1], new_order[idx]
        else:
            if idxs[-1] == total - 1: return
            new_order = list(range(total))
            for idx in reversed(idxs):
                new_order[idx], new_order[idx + 1] = new_order[idx + 1], new_order[idx]
        
        self._reorder_document(new_order)

    def move_up(self):
        self._move_pages(-1)

    def move_down(self):
        self._move_pages(1)

    def move_top(self):
        if not self._sel or not self.doc: return
        self._save_state()
        idxs = sorted(self._sel)
        if idxs[0] == 0: return
        total = len(self.doc)
        new_order = list(range(total))
        for i, idx in enumerate(idxs):
            new_order.pop(idx - i)
        for i, idx in enumerate(idxs):
            new_order.insert(i, idx)
        self._reorder_document(new_order)

    def move_bottom(self):
        if not self._sel or not self.doc: return
        self._save_state()
        idxs = sorted(self._sel)
        if idxs[-1] == len(self.doc) - 1: return
        total = len(self.doc)
        new_order = list(range(total))
        for idx in reversed(idxs):
            new_order.pop(idx)
        for idx in reversed(idxs):
            new_order.append(idx)
        self._reorder_document(new_order)

    def _reorder_document(self, new_order):
        """Reorder document pages based on new_order list"""
        new = fitz.open()
        for i in new_order:
            if i not in self.page_del:
                new.insert_pdf(self.doc, from_page=i, to_page=i)
                new_rot = self.page_rots.get(i)
                if new_rot and len(new) > 0:
                    new[-1].set_rotation(new_rot)
        
        new_rots = {}
        new_del = set()
        new_sel = set()
        for new_idx, old_idx in enumerate(new_order):
            if old_idx in self.page_del:
                new_del.add(new_idx)
            if old_idx in self.page_rots:
                new_rots[new_idx] = self.page_rots[old_idx]
            if old_idx in self._sel:
                new_sel.add(new_idx)
        
        self.page_rots = new_rots
        self.page_del = new_del
        self._sel = new_sel
        
        self.doc.close()
        self._set_doc(new, self.doc_path)

    def insert_blank(self):
        if not self.doc: return
        pos = simpledialog.askinteger("Insert Blank", "Insert after page (0 = beginning):", minvalue=0, maxvalue=len(self.doc), initialvalue=1)
        if pos is None: return
        cnt = simpledialog.askinteger("Insert Blank", "How many blank pages?", minvalue=1, maxvalue=100, initialvalue=1)
        if cnt is None: return
        self._save_state()
        new = fitz.open()
        w, h = self.doc[0].rect.width, self.doc[0].rect.height
        for i in range(len(self.doc)):
            if i == pos:
                for _ in range(cnt): new.new_page(width=w, height=h)
            if i not in self.page_del:
                new.insert_pdf(self.doc, from_page=i, to_page=i)
        if pos == len(self.doc):
            for _ in range(cnt): new.new_page(width=w, height=h)
        self.doc.close(); self._set_doc(new, self.doc_path)

    def mirror_pages(self):
        if not self._sel: return
        self._save_state()
        for i in list(self._sel):
            if i in self.page_del: continue
            pg = self.doc[i]
            r = pg.rect
            pg.add_transform(fitz.Matrix(-1, 1, 0, 0, r.width, 0))
        self._sel.clear(); self._render_thumbs()

    def to_grayscale(self):
        if not self.doc: return
        choice = messagebox.askyesnocancel("Grayscale",
            "Save as new file? (Yes=new file, No=overwrite current, Cancel=abort)")
        if choice is None: return
        path = None
        if choice:
            path = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="grayscale.pdf")
            if not path: return
        else:
            path = self.doc_path
        try:
            nd = fitz.open()
            for i in range(len(self.doc)):
                if i in self.page_del: continue
                nd.insert_pdf(self.doc, from_page=i, to_page=i)
            nd.save(path, garbage=4, deflate=True, colorspace=fitz.csGRAY)
            nd.close()
            if choice:
                messagebox.showinfo("Done", "Saved grayscale PDF to:\n%s" % path)
            else:
                self.doc.close(); self._set_doc(fitz.open(path), path)
                messagebox.showinfo("Done", "Document converted to grayscale in-place.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def search_pdf(self):
        if not self.doc: return
        q = simpledialog.askstring("Search", "Search text:")
        if not q: return
        self._search_highlights.clear(); self._render_thumbs()
        try:
            threading.Thread(target=self._search_worker, args=(q,), daemon=True).start()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _search_worker(self, q):
        results = []
        highlights = set()
        for i in range(len(self.doc)):
            if i in self.page_del: continue
            insts = self.doc[i].search_for(q)
            if insts:
                highlights.add(i)
                for r in insts:
                    ctx = self.doc[i].get_text("text", clip=r).strip()
                    snippet = ctx[:100] if ctx else "(found at %s)" % r
                    results.append("Page %d: ...%s..." % (i + 1, snippet))
        self._search_highlights = highlights
        self.parent.after(0, self._render_thumbs)
        if results:
            self.parent.after(0, lambda: self._show_search_results(results))
        else:
            self.parent.after(0, lambda: messagebox.showinfo("Search", "No results found."))

    def _show_search_results(self, results):
        top = ctk.CTkToplevel(self.parent)
        top.title("Search Results")
        top.geometry("560x420")
        top.transient(self.parent)
        top.configure(fg_color=THEME["bg"])
        f = ctk.CTkFrame(top, fg_color="transparent"); f.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(f, text="%d result(s)" % len(results), font=FONT_BOLD,
                     text_color=THEME["fg"]).pack(anchor="w")
        txt = ctk.CTkTextbox(f, corner_radius=10, fg_color=THEME["surface2"],
            border_width=1, border_color=THEME["border"], text_color=THEME["fg"], font=FONT)
        txt.pack(fill="both", expand=True, pady=(8, 10))
        txt.insert("1.0", "\n".join(results))
        txt.configure(state="disabled")
        ghost_btn(f, "Close", top.destroy, width=100).pack(anchor="e")

    def goto_page(self):
        if not self.doc: return
        n = simpledialog.askinteger("Go to Page", "Page number (1-%d):" % len(self.doc), minvalue=1, maxvalue=len(self.doc), initialvalue=1)
        if not n: return
        # Scroll canvas to make the nth thumbnail visible
        target_y = ((n - 1) // max(1, self.canvas.winfo_width() // (THUMB_W + 24))) * (THUMB_H + 50)
        self.canvas.yview_moveto(target_y / max(1, self.canvas.bbox("all")[3] - self.canvas.winfo_height()))

    def extract_range(self):
        if not self.doc: return
        t = self.ext_var.get().strip()
        if not t: messagebox.showerror("Error", "Enter page range e.g. 1,3,5-7"); return
        try:
            pgs = parse_page_range(t, len(self.doc))
        except Exception as e:
            messagebox.showerror("Error", str(e)); return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="extracted.pdf")
        if not out: return
        try:
            nd = fitz.open()
            for p in pgs: nd.insert_pdf(self.doc, from_page=p - 1, to_page=p - 1)
            safe_save(nd, out, self.var_compress.get()); nd.close()
            messagebox.showinfo("Success", "Extracted %d page(s)" % len(pgs))
        except Exception as e:
            messagebox.showerror("Error", "Extraction failed:\n%s" % e)

    def split_all(self):
        if not self.doc: return
        d = filedialog.askdirectory(title="Select output folder")
        if not d: return
        try:
            total = len(self.doc); kept = 0
            progress = ProgressDlg(self.parent, "Splitting...", total)
            for i in range(total):
                if i in self.page_del: continue
                nd = fitz.open()
                nd.insert_pdf(self.doc, from_page=i, to_page=i)
                r = self.page_rots.get(i, 0)
                if r and len(nd): nd[0].set_rotation(r)
                nd.save(os.path.join(d, "page_%03d.pdf" % (i + 1)), garbage=1); nd.close()
                kept += 1; progress.step(i + 1)
            progress.close()
            messagebox.showinfo("Success", "Split %d pages into:\n%s" % (kept, d))
        except Exception as e:
            messagebox.showerror("Error", "Split failed:\n%s" % e)

    def split_bookmarks(self):
        if not self.doc: return
        toc = self.doc.get_toc()
        if not toc: messagebox.showinfo("Info", "No bookmarks found."); return
        d = filedialog.askdirectory(title="Select folder for chapters")
        if not d: return
        try:
            chs = []
            for item in toc:
                if item[0] == 1:
                    safe = "".join(c for c in item[1] if c.isalnum() or c in " _-") or "chapter"
                    chs.append({"title": safe, "start": item[2], "end": None})
            total = len(self.doc)
            for i in range(len(chs)):
                chs[i]["end"] = chs[i + 1]["start"] - 1 if i + 1 < len(chs) else total
            for ch in chs:
                s, e = max(1, ch["start"]), min(total, ch["end"])
                if s > e: continue
                nd = fitz.open()
                nd.insert_pdf(self.doc, from_page=s - 1, to_page=e - 1)
                safe_save(nd, os.path.join(d, ch["title"] + ".pdf"), self.var_compress.get()); nd.close()
            messagebox.showinfo("Success", "Split %d chapters" % len(chs))
        except Exception as e:
            messagebox.showerror("Error", "Bookmark split failed:\n%s" % e)

    def split_by_count(self):
        if not self.doc: return
        n = simpledialog.askinteger("Split by Count", "Pages per file:", minvalue=1, maxvalue=100, initialvalue=10)
        if not n: return
        d = filedialog.askdirectory(title="Select output folder")
        if not d: return
        try:
            total = len(self.doc); cnt = 0; fn = 1
            for start in range(0, total, n):
                end = min(start + n - 1, total - 1)
                nd = fitz.open()
                for i in range(start, end + 1):
                    if i not in self.page_del:
                        nd.insert_pdf(self.doc, from_page=i, to_page=i)
                if len(nd):
                    safe_save(nd, os.path.join(d, "part_%02d.pdf" % fn), self.var_compress.get()); nd.close()
                    fn += 1; cnt += 1
            messagebox.showinfo("Success", "Split into %d files" % cnt)
        except Exception as e:
            messagebox.showerror("Error", "Split failed:\n%s" % e)

    def split_even_odd(self):
        if not self.doc: return
        d = filedialog.askdirectory(title="Select output folder")
        if not d: return
        try:
            for name, parity in [("even", 1), ("odd", 0)]:
                nd = fitz.open()
                for i in range(len(self.doc)):
                    if i not in self.page_del and (i % 2) == parity:
                        nd.insert_pdf(self.doc, from_page=i, to_page=i)
                if len(nd):
                    safe_save(nd, os.path.join(d, "%s_pages.pdf" % name), self.var_compress.get()); nd.close()
            messagebox.showinfo("Success", "Even/odd saved to:\n%s" % d)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_images(self):
        if not self.doc: return
        d = filedialog.askdirectory(title="Output folder for images")
        if not d: return
        try:
            cnt = 0
            for pgnum in range(len(self.doc)):
                if pgnum in self.page_del: continue
                for img in self.doc[pgnum].get_images():
                    try:
                        xref = img[0]
                        pix = fitz.Pixmap(self.doc, xref)
                        if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                        pix.save(os.path.join(d, "img_p%02d_%04d.png" % (pgnum + 1, cnt)))
                        cnt += 1
                    except Exception:
                        continue
            messagebox.showinfo("Success", "Extracted %d images" % cnt)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def extract_text(self):
        if not self.doc: return
        out = filedialog.asksaveasfilename(defaultextension=".txt", filetypes=[("Text", "*.txt")], initialfile="extracted_text.txt")
        if not out: return
        try:
            with open(out, "w", encoding="utf-8") as f:
                for i in range(len(self.doc)):
                    if i in self.page_del: continue
                    f.write("--- Page %d ---\n" % (i + 1))
                    f.write(self.doc[i].get_text())
                    f.write("\n\n")
            messagebox.showinfo("Success", "Text extracted to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_as(self):
        if not self.doc: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="output.pdf")
        if not out: return
        try:
            nd = fitz.open()
            for i in range(len(self.doc)):
                if i in self.page_del: continue
                nd.insert_pdf(self.doc, from_page=i, to_page=i)
                r = self.page_rots.get(i, 0)
                if r and len(nd): nd[-1].set_rotation(r)
            safe_save(nd, out, self.var_compress.get()); nd.close()
            messagebox.showinfo("Success", "Saved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", "Save failed:\n%s" % e)


# ═══════════════════════ TOOLS UI (legacy) ═══════════════════════
class LegacyToolsUI:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.image_paths = []
        self._build()

    def _build(self):
        main = ctk.CTkScrollableFrame(self.parent, fg_color="transparent",
            scrollbar_fg_color="transparent", scrollbar_button_color="#2a3247",
            scrollbar_button_hover_color="#3a4560")
        main.pack(fill="both", expand=True, padx=(14, 8), pady=14)
        main.grid_columnconfigure(0, weight=1, uniform="tools")
        main.grid_columnconfigure(1, weight=1, uniform="tools")
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, 7))
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=(7, 7))

        # ── Left column ──
        sig = modern_card(left); sig.pack(fill="x", pady=(0, 12))
        s = ctk.CTkFrame(sig, fg_color="transparent"); s.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(s, text="Digital signature", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(s, text="Add a signature block to any PDF", font=FONT_SM,
                     text_color=THEME["muted"]).pack(anchor="w", pady=(0, 10))
        ctk.CTkLabel(s, text="Signer", font=FONT_SM, text_color=THEME["muted"]).pack(anchor="w")
        self.signer_var = tk.StringVar(value="AYUSH GUPTA")
        accent_entry(s, textvariable=self.signer_var, font=("Segoe UI", 12, "bold")).pack(fill="x", pady=(2, 8))
        sf = ctk.CTkFrame(s, fg_color="transparent"); sf.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(sf, text="Position", font=FONT_SM, text_color=THEME["muted"]).pack(side="left")
        self.sig_pos = ctk.CTkComboBox(sf, values=["Bottom-Right", "Bottom-Left", "Top-Right", "Top-Left", "Center"],
            state="readonly", width=140, height=32, corner_radius=9,
            fg_color=THEME["surface2"], border_color=THEME["border"], button_color=THEME["surface2"],
            button_hover_color=THEME["hover"], dropdown_fg_color=THEME["surface2"],
            dropdown_hover_color=THEME["hover"], text_color=THEME["fg"], font=FONT)
        self.sig_pos.set("Bottom-Right"); self.sig_pos.pack(side="left", padx=(8, 16))
        ctk.CTkLabel(sf, text="Page", font=FONT_SM, text_color=THEME["muted"]).pack(side="left")
        self.sig_page = tk.StringVar(value="last")
        accent_entry(sf, textvariable=self.sig_page, width=64, height=32).pack(side="left", padx=(8, 6))
        ctk.CTkLabel(sf, text="(1 / last)", font=FONT_SM, text_color=THEME["muted"]).pack(side="left")
        primary_btn(s, "Sign PDF", self.sign_pdf, height=36).pack(fill="x")

        imgc = modern_card(left); imgc.pack(fill="x", pady=(0, 12))
        i2 = ctk.CTkFrame(imgc, fg_color="transparent"); i2.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(i2, text="Image compression", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(i2, text="Shrink JPG/PNG images with a quality slider", font=FONT_SM,
                     text_color=THEME["muted"]).pack(anchor="w", pady=(0, 10))
        ifrow = ctk.CTkFrame(i2, fg_color="transparent"); ifrow.pack(fill="x")
        ghost_btn(ifrow, "Add images", self.add_images, width=110).pack(side="left")
        self.img_lbl = ctk.CTkLabel(ifrow, text="0 images added", font=FONT_SM,
                                    text_color=THEME["muted"])
        self.img_lbl.pack(side="left", padx=10)
        qf = ctk.CTkFrame(i2, fg_color="transparent"); qf.pack(fill="x", pady=(10, 4))
        ctk.CTkLabel(qf, text="Quality", font=FONT_SM, text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.img_q = ctk.CTkSlider(qf, from_=1, to=100, number_of_steps=99, command=self._on_img_q,
            height=18, fg_color=THEME["surface2"], progress_color=THEME["accent"],
            button_color=THEME["accent"], button_hover_color=THEME["accent_h"])
        self.img_q.set(60); self.img_q.pack(side="left", fill="x", expand=True)
        self.img_q_lbl = ctk.CTkLabel(qf, text="60", font=FONT_BOLD, text_color=THEME["fg"], width=36)
        self.img_q_lbl.pack(side="left", padx=(8, 0))
        ghost_btn(i2, "Compress images", self.compress_images).pack(fill="x", pady=(10, 0))

        pdfc = modern_card(left); pdfc.pack(fill="x")
        p2 = ctk.CTkFrame(pdfc, fg_color="transparent"); p2.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(p2, text="PDF compression", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(p2, text="Reduce file size with different optimization levels", font=FONT_SM,
                     text_color=THEME["muted"]).pack(anchor="w", pady=(0, 10))
        lvls = ["Low (garbage)", "Medium (deflate)", "High (deflate+images)", "Max (full optimize)"]
        self.pdf_comp_lvl = ctk.CTkComboBox(p2, values=lvls, state="readonly", height=32, corner_radius=9,
            fg_color=THEME["surface2"], border_color=THEME["border"], button_color=THEME["surface2"],
            button_hover_color=THEME["hover"], dropdown_fg_color=THEME["surface2"],
            dropdown_hover_color=THEME["hover"], text_color=THEME["fg"], font=FONT)
        self.pdf_comp_lvl.set("Medium (deflate)"); self.pdf_comp_lvl.pack(fill="x", pady=(0, 10))
        ghost_btn(p2, "Compress PDF…", self.compress_pdf).pack(fill="x")

        # ── Right column ──
        conv = modern_card(right); conv.pack(fill="x", pady=(0, 12))
        c1 = ctk.CTkFrame(conv, fg_color="transparent"); c1.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c1, text="Convert & extract", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w", pady=(0, 8))
        ghost_btn(c1, "Images to PDF…", self.images_to_pdf).pack(fill="x", pady=3)
        self._btn(c1, "Extract text from PDF…", lambda: self._run_split("extract_text"))
        self._btn(c1, "Extract images from PDF…", lambda: self._run_split("extract_images"))
        self._btn(c1, "Convert to grayscale…", lambda: self._run_split("to_grayscale"))

        sec = modern_card(right); sec.pack(fill="x", pady=(0, 12))
        c2 = ctk.CTkFrame(sec, fg_color="transparent"); c2.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c2, text="Security & cleanup", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w", pady=(0, 8))
        ghost_btn(c2, "Redact text…", self.redact_text).pack(fill="x", pady=3)
        ghost_btn(c2, "Remove metadata", self.remove_metadata).pack(fill="x", pady=3)
        ghost_btn(c2, "Password protect PDF…", self.password_protect).pack(fill="x", pady=3)
        ghost_btn(c2, "Remove password from PDF…", self.remove_password).pack(fill="x", pady=3)

        misc = modern_card(right); misc.pack(fill="x")
        c3 = ctk.CTkFrame(misc, fg_color="transparent"); c3.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c3, text="Miscellaneous", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w", pady=(0, 8))
        ghost_btn(c3, "Add page numbers", self.add_page_numbers).pack(fill="x", pady=3)
        ghost_btn(c3, "Flatten PDF (annotations)", self.flatten_pdf).pack(fill="x", pady=3)
        self._btn(c3, "Clone open PDF x2", lambda: self._run_split("dup_pgs"))
        ctk.CTkFrame(c3, height=1, fg_color=THEME["border"]).pack(fill="x", pady=8)
        ctk.CTkButton(c3, text="★  Rate & Review", command=self.open_rating, height=36,
            fg_color=THEME["accent2"], hover_color="#9d74ff", text_color="#ffffff",
            corner_radius=9, font=FONT_BOLD).pack(fill="x")

    def _on_img_q(self, v):
        self.img_q_lbl.configure(text=str(int(round(float(v)))))

    def _btn(self, parent, text, cmd):
        ghost_btn(parent, text, cmd, width=140).pack(fill="x", pady=3)

    def open_rating(self):
        RatingDialog(self.parent)

    def _run_split(self, method):
        su = self.app.split_ui
        if not su.doc:
            messagebox.showerror("Error", "Open a PDF in the Split tab first.")
            return
        getattr(su, method)()

    def sign_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF to sign", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="signed.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            signer = self.signer_var.get().strip() or "AYUSH GUPTA"
            pos = self.sig_pos.get()
            pg_text = self.sig_page.get().strip()
            target_pg = len(doc) - 1 if pg_text.lower() == "last" else max(0, int(pg_text) - 1)
            target_pg = min(target_pg, len(doc) - 1)

            pg = doc[target_pg]
            rect = pg.rect
            w, h = rect.width, rect.height
            positions = {
                "Bottom-Right": (w - 260, h - 60, w - 20, h - 20),
                "Bottom-Left": (20, h - 60, 240, h - 20),
                "Top-Right": (w - 260, 20, w - 20, 60),
                "Top-Left": (20, 20, 240, 60),
                "Center": (w / 2 - 120, h / 2 - 20, w / 2 + 120, h / 2 + 20),
            }
            x0, y0, x1, y1 = positions.get(pos, positions["Bottom-Right"])

            shape = pg.new_shape()
            shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
            shape.finish(color=(0.1, 0.3, 0.6), fill=(0.95, 0.95, 1), width=1.5)
            shape.insert_text(fitz.Point(x0 + 12, y0 + 28), "Digitally Signed", fontsize=10, color=(0.3, 0.3, 0.3))
            shape.insert_text(fitz.Point(x0 + 12, y0 + 48), signer, fontsize=14, color=(0.1, 0.3, 0.6))
            shape.insert_text(fitz.Point(x0 + 12, y0 + 64), datetime.now().strftime("%Y-%m-%d %H:%M"), fontsize=8, color=(0.5, 0.5, 0.5))
            shape.commit()
            safe_save(doc, out, True)
            doc.close()
            messagebox.showinfo("Success", "PDF signed by %s" % signer)
        except Exception as e:
            messagebox.showerror("Error", "Sign failed:\n%s" % e)

    def add_images(self):
        ps = filedialog.askopenfilenames(title="Select images", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        self.image_paths.extend(ps)
        self.img_lbl.configure(text="%d image(s) added" % len(self.image_paths))

    def compress_images(self):
        if not self.image_paths:
            messagebox.showerror("Error", "Add images first."); return
        q = int(round(float(self.img_q.get())))
        d = filedialog.askdirectory(title="Output folder")
        if not d: return
        try:
            from PIL import Image as PILImg
        except ImportError:
            messagebox.showerror("Error", "Pillow required: pip install Pillow"); return
        try:
            for path in self.image_paths:
                img = PILImg.open(path)
                name = os.path.splitext(os.path.basename(path))[0] + "_compressed.jpg"
                out = os.path.join(d, name)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(out, "JPEG", quality=q, optimize=True)
            messagebox.showinfo("Success", "Compressed %d images" % len(self.image_paths))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def images_to_pdf(self):
        ps = filedialog.askopenfilenames(title="Select images", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        if not ps: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="images.pdf")
        if not out: return
        try:
            doc = fitz.open()
            for p in ps:
                img = fitz.open(p)
                rect = img[0].rect
                page = doc.new_page(width=rect.width, height=rect.height)
                page.insert_image(rect, filename=p)
                img.close()
            doc.save(out, garbage=4); doc.close()
            messagebox.showinfo("Success", "Created PDF with %d images" % len(ps))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def compress_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF to compress", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="compressed.pdf")
        if not out: return
        lvl = self.pdf_comp_lvl.get()
        try:
            doc = fitz.open(path)
            opts = {"garbage": 4, "deflate": True}
            if "Low" in lvl: opts = {"garbage": 4, "deflate": False}
            elif "Max" in lvl: opts = {"garbage": 4, "deflate": True, "linear": True}
            doc.save(out, **opts)
            orig = os.path.getsize(path)
            comp = os.path.getsize(out)
            pct = (1 - comp / orig) * 100 if orig else 0
            doc.close()
            messagebox.showinfo("Success",
                "Reduced %.1f MB \u2192 %.1f MB (%.0f%%)\n%s" % (orig / 1e6, comp / 1e6, pct, out))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def redact_text(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        txt = simpledialog.askstring("Redact Text", "Text to redact (case-sensitive):")
        if not txt: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="redacted.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            for pgnum in range(len(doc)):
                pg = doc[pgnum]
                for r in pg.search_for(txt):
                    pg.add_redact_annot(r)
                    pg.apply_redactions()
            safe_save(doc, out, True); doc.close()
            messagebox.showinfo("Success", "Redacted '%s'" % txt)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_metadata(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="cleaned.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            doc.set_metadata({})
            safe_save(doc, out, True); doc.close()
            messagebox.showinfo("Success", "Metadata removed")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def password_protect(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pw = simpledialog.askstring("Password", "Enter password to encrypt:", show="*")
        if not pw or not pw.strip(): return
        pw = pw.strip()
        pw2 = simpledialog.askstring("Password", "Confirm password:", show="*")
        if pw != pw2: messagebox.showerror("Error", "Passwords don't match"); return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="protected.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            doc.save(out, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=pw, owner_pw=pw, garbage=4, deflate=True)
            doc.close()
            messagebox.showinfo("Success", "PDF encrypted")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_password(self):
        path = filedialog.askopenfilename(title="Select encrypted PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pw = simpledialog.askstring("Password", "Enter current password:", show="*")
        if pw is None: return
        pw = pw if pw else ""
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="decrypted.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                result = doc.authenticate(pw)
                if result == 0:
                    messagebox.showerror("Error", "Incorrect password"); doc.close(); return
                try:
                    _ = doc.page_count
                except Exception:
                    messagebox.showerror("Error", "Incorrect password - cannot read"); doc.close(); return
            else:
                messagebox.showinfo("Info", "This PDF is not encrypted."); doc.close(); return
            safe_save(doc, out, True)
            doc.close()
            messagebox.showinfo("Success", "Password removed")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_page_numbers(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="numbered.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            for i in range(len(doc)):
                pg = doc[i]; r = pg.rect
                shape = pg.new_shape()
                shape.insert_text(fitz.Point(r.width / 2 - 15, r.height - 20),
                    "- %d -" % (i + 1), fontsize=10, color=(0.4, 0.4, 0.4))
                shape.commit()
            safe_save(doc, out, True); doc.close()
            messagebox.showinfo("Success", "Page numbers added")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def flatten_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="flattened.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            for pgnum in range(len(doc)):
                pg = doc[pgnum]
                for annot in pg.annots():
                    pg.delete_annot(annot)
            safe_save(doc, out, True); doc.close()
            messagebox.showinfo("Success", "Annotations flattened")
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ═══════════════════════ v4.0 DIALOGS ═══════════════════════
class SimpleFormDialog:
    """Small parameter form. fields: [(key, label, type, default[, options])]
    type: text | int | float | check | combo → result dict (None if cancelled)."""

    def __init__(self, parent, title, fields, intro=""):
        self.result = None
        self.fields = fields
        self.vars = {}
        self.top = ctk.CTkToplevel(parent)
        self.top.title(title)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text=title, font=("Segoe UI", 14, "bold"),
                     text_color=THEME["fg"]).pack(anchor="w", padx=16, pady=(14, 2))
        if intro:
            ctk.CTkLabel(card, text=intro, font=FONT_SM, text_color=THEME["muted"],
                         wraplength=400, justify="left").pack(anchor="w", padx=16, pady=(0, 4))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16, pady=(8, 0))
        for spec in fields:
            key, label, typ, default = spec[0], spec[1], spec[2], spec[3]
            opts = spec[4] if len(spec) > 4 else None
            if typ == "check":
                var = tk.BooleanVar(value=bool(default))
                dark_check(body, label, var).pack(anchor="w", pady=4)
                self.vars[key] = var
                continue
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, font=FONT_SM, text_color=THEME["muted"],
                         width=150, anchor="w").pack(side="left")
            if typ == "combo":
                w = modern_combo(row, opts or [], width=170)
                w.set("" if default is None else str(default))
                w.pack(side="left", fill="x", expand=True)
                self.vars[key] = w
            else:
                var = tk.StringVar(value="" if default is None else str(default))
                accent_entry(row, textvariable=var, height=32).pack(side="left", fill="x",
                                                                    expand=True)
                self.vars[key] = var
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(12, 14))
        primary_btn(bf, "OK", self._ok, width=100, height=34).pack(side="left")
        ghost_btn(bf, "Cancel", self.top.destroy, width=90).pack(side="right")
        self.top.update_idletasks()
        try:
            self.top.geometry("+%d+%d" % (parent.winfo_rootx() + 80,
                                          parent.winfo_rooty() + 80))
        except Exception:
            pass
        self.top.wait_window()

    def _ok(self):
        out = {}
        for spec in self.fields:
            key, typ = spec[0], spec[2]
            w = self.vars.get(key)
            try:
                if typ == "check":
                    out[key] = bool(w.get())
                elif typ == "combo":
                    out[key] = w.get()
                elif typ == "int":
                    out[key] = int(float(str(w.get()).strip() or 0))
                elif typ == "float":
                    out[key] = float(str(w.get()).strip() or 0)
                else:
                    out[key] = str(w.get()).strip()
            except Exception:
                out[key] = spec[3]
        self.result = out
        self.top.destroy()


class SignatureStudio:
    """Create a transparent signature PNG: draw with the mouse or type a name."""

    CW, CH = 520, 190

    def __init__(self, parent, source=None):
        self.strokes = []
        self._cur = None
        self._tmp = None
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Signature studio")
        self.top.geometry("600x445")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text="Signature studio", font=("Segoe UI", 14, "bold"),
                     text_color=THEME["fg"]).pack(anchor="w", padx=16, pady=(14, 2))
        ctk.CTkLabel(card, text="Draw below with the mouse, or type a name and press Render.",
                     font=FONT_SM, text_color=THEME["muted"]).pack(anchor="w", padx=16)
        self.cv = tk.Canvas(card, width=self.CW, height=self.CH, bg="#ffffff",
                            highlightthickness=1, highlightbackground=THEME["border"],
                            cursor="pencil")
        self.cv.pack(padx=16, pady=10)
        self.cv.bind("<ButtonPress-1>", self._press)
        self.cv.bind("<B1-Motion>", self._drag)
        self.cv.bind("<ButtonRelease-1>", self._release)
        row = ctk.CTkFrame(card, fg_color="transparent")
        row.pack(fill="x", padx=16)
        ctk.CTkLabel(row, text="Type name", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        default_name = ""
        try:
            default_name = source.signer_var.get()
        except Exception:
            pass
        self.name_var = tk.StringVar(value=default_name)
        accent_entry(row, textvariable=self.name_var, width=200, height=32).pack(side="left", padx=8)
        ghost_btn(row, "Render", self._render_text, width=90).pack(side="left")
        ghost_btn(row, "Clear", self._clear, width=80).pack(side="right")
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(12, 14))
        primary_btn(bf, "Save signature", self._save, width=140, height=34).pack(side="left")
        ghost_btn(bf, "Delete saved", self._delete_saved, width=110).pack(side="left", padx=8)
        self.status = ctk.CTkLabel(bf, text="", font=FONT_SM, text_color=THEME["success"])
        self.status.pack(side="right")
        self.top.update_idletasks()
        try:
            self.top.geometry("+%d+%d" % (parent.winfo_rootx() + 80,
                                          parent.winfo_rooty() + 60))
        except Exception:
            pass

    def _press(self, e):
        self._cur = [(e.x, e.y)]
        self.strokes.append(self._cur)

    def _drag(self, e):
        if self._cur is None:
            return
        self._cur.append((e.x, e.y))
        if len(self._cur) > 1:
            x1, y1 = self._cur[-2]
            self.cv.create_line(x1, y1, e.x, e.y, fill="#0f173c", width=3,
                                capstyle="round", smooth=True)

    def _release(self, e):
        self._cur = None

    def _clear(self):
        self.strokes = []
        self.cv.delete("all")

    def _render_text(self):
        name = self.name_var.get().strip()
        if not name:
            messagebox.showwarning("Signature", "Type a name first.", parent=self.top)
            return
        self._clear()
        from PIL import Image, ImageDraw, ImageFont
        img = Image.new("RGBA", (self.CW, self.CH), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        font = None
        for fname in ("segoesc.ttf", "segoeuii.ttf", "segoeui.ttf"):
            try:
                font = ImageFont.truetype(fname, 58)
                break
            except Exception:
                continue
        if font is None:
            font = ImageFont.load_default()
        bbox = d.textbbox((0, 0), name, font=font)
        tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
        d.text(((self.CW - tw) / 2 - bbox[0], (self.CH - th) / 2 - bbox[1]),
               name, font=font, fill=(15, 23, 60, 255))
        self._show_img(img)

    def _show_img(self, img):
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        img.save(tmp.name)
        tmp.close()
        self._tmp = tmp.name
        self._photo = tk.PhotoImage(file=tmp.name)
        self.cv.delete("all")
        self.cv.create_image(self.CW // 2, self.CH // 2, image=self._photo)

    def _rasterize(self):
        from PIL import Image, ImageDraw
        img = Image.new("RGBA", (self.CW, self.CH), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        drew = False
        for stroke in self.strokes:
            if len(stroke) > 1:
                d.line(stroke, fill=(15, 23, 60, 255), width=3, joint="curve")
                drew = True
            elif stroke:
                x, y = stroke[0]
                d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(15, 23, 60, 255))
                drew = True
        return img, drew

    def _save(self):
        try:
            img, drew = self._rasterize()
            from PIL import Image
            if drew:
                img.save(str(SIGNATURE_FILE))
            elif self._tmp and os.path.exists(self._tmp):
                Image.open(self._tmp).save(str(SIGNATURE_FILE))
            else:
                messagebox.showwarning("Signature", "Draw or render something first.",
                                       parent=self.top)
                return
            messagebox.showinfo("Signature saved",
                "Saved to:\n%s\n\nSign PDF will use it automatically." % SIGNATURE_FILE,
                parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)

    def _delete_saved(self):
        try:
            if os.path.exists(str(SIGNATURE_FILE)):
                os.remove(str(SIGNATURE_FILE))
            self.status.configure(text="Saved signature deleted")
        except Exception as e:
            self.status.configure(text=str(e))


class SignPreviewDialog:
    """Click on a rendered page to choose the signature position."""

    def __init__(self, parent, pdf_path, page_index=0):
        self.result = None
        self.cx = None
        self.cy = None
        png, _pw, _ph = fp.render_page_image(pdf_path, page_index, width=520)
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
        tmp.write(png)
        tmp.close()
        self._tmp = tmp.name
        self.photo = tk.PhotoImage(file=tmp.name)
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Click to place the signature")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text="Click on the page — the click point is the signature centre",
                     font=FONT_BOLD, text_color=THEME["fg"]).pack(anchor="w", padx=16,
                                                                 pady=(14, 2))
        self.cv = tk.Canvas(card, width=self.photo.width(), height=self.photo.height(),
                            highlightthickness=1, highlightbackground=THEME["border"],
                            cursor="crosshair")
        self.cv.pack(padx=16, pady=10)
        self.cv.create_image(0, 0, anchor="nw", image=self.photo)
        self.cv.bind("<Button-1>", self._click)
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(4, 14))
        self.lbl = ctk.CTkLabel(bf, text="No position chosen", font=FONT_SM,
                                text_color=THEME["muted"])
        self.lbl.pack(side="left")
        primary_btn(bf, "Use this position", self._ok, width=150, height=34).pack(side="right")
        ghost_btn(bf, "Cancel", self._close, width=90).pack(side="right", padx=8)
        self.top.protocol("WM_DELETE_WINDOW", self._close)
        self.top.update_idletasks()
        try:
            self.top.geometry("+%d+%d" % (parent.winfo_rootx() + 60,
                                          parent.winfo_rooty() + 30))
        except Exception:
            pass
        self.top.wait_window()

    def _click(self, e):
        x = max(0, min(e.x, self.photo.width()))
        y = max(0, min(e.y, self.photo.height()))
        self.cx = x / float(self.photo.width())
        self.cy = y / float(self.photo.height())
        self.cv.delete("m")
        self.cv.create_line(x - 14, y, x + 14, y, fill="#ef4444", width=2, tags="m")
        self.cv.create_line(x, y - 14, x, y + 14, fill="#ef4444", width=2, tags="m")
        self.lbl.configure(text="x %.0f%%   y %.0f%%" % (self.cx * 100, self.cy * 100))

    def _ok(self):
        if self.cx is None:
            messagebox.showwarning("Pick a spot", "Click on the page first.", parent=self.top)
            return
        self.result = (self.cx, self.cy)
        self._close()

    def _close(self):
        try:
            os.unlink(self._tmp)
        except Exception:
            pass
        self.top.destroy()


class BookmarkEditor:
    """Edit PDF bookmarks (TOC): add, rename, delete, indent, reorder, save."""

    def __init__(self, parent, path):
        self.parent = parent
        self.path = path
        self.out = None
        self.doc = fitz.open(path)
        self.total = len(self.doc)
        self.toc = self.doc.get_toc(simple=True)
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Bookmark editor — " + os.path.basename(path))
        self.top.geometry("640x560")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        hdr = ctk.CTkFrame(card, fg_color="transparent")
        hdr.pack(fill="x", padx=16, pady=(14, 4))
        ctk.CTkLabel(hdr, text="Bookmarks", font=("Segoe UI", 14, "bold"),
                     text_color=THEME["fg"]).pack(side="left")
        self.count_lbl = ctk.CTkLabel(hdr, text="", font=FONT_SM, text_color=THEME["muted"])
        self.count_lbl.pack(side="right")
        lw = ctk.CTkFrame(card, fg_color="transparent")
        lw.pack(fill="both", expand=True, padx=16)
        self.lb = tk.Listbox(lw, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0)
        sc = ctk.CTkScrollbar(lw, command=self.lb.yview, width=12, fg_color="transparent",
                              button_color="#2a3247", button_hover_color="#3a4560")
        self.lb.configure(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y", padx=(8, 0))
        self.lb.bind("<Double-Button-1>", lambda e: self.rename())
        btns = ctk.CTkFrame(card, fg_color="transparent")
        btns.pack(fill="x", padx=16, pady=(10, 4))
        ghost_btn(btns, "+ Add", self.add, width=80).pack(side="left", padx=2)
        ghost_btn(btns, "Rename", self.rename, width=90).pack(side="left", padx=2)
        ghost_btn(btns, "Delete", self.delete, width=80).pack(side="left", padx=2)
        ghost_btn(btns, "↑", lambda: self.move(-1), width=44).pack(side="left", padx=2)
        ghost_btn(btns, "↓", lambda: self.move(1), width=44).pack(side="left", padx=2)
        ghost_btn(btns, "Promote", lambda: self.level(-1), width=90).pack(side="left", padx=2)
        ghost_btn(btns, "Demote", lambda: self.level(1), width=90).pack(side="left", padx=2)
        ghost_btn(btns, "Auto-generate", self.auto_gen, width=120).pack(side="right", padx=2)
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(6, 14))
        primary_btn(bf, "Save As…", self.save, width=120, height=34).pack(side="left")
        ghost_btn(bf, "Close", self.top.destroy, width=90).pack(side="right")
        self._refresh()

    def _refresh(self):
        self.lb.delete(0, "end")
        for lvl, title, page in self.toc:
            self.lb.insert("end", "%s%s   — p.%s" % ("    " * max(0, lvl - 1), title, page))
        self.count_lbl.configure(text="%d item(s) · %d page(s)" % (len(self.toc), self.total))

    def _sel(self):
        s = self.lb.curselection()
        return s[0] if s else None

    def add(self):
        i = self._sel()
        title = simpledialog.askstring("Add bookmark", "Title:", parent=self.top)
        if not title:
            return
        page = simpledialog.askinteger("Add bookmark", "Page number (1-%d):" % self.total,
                                       minvalue=1, maxvalue=self.total, initialvalue=1,
                                       parent=self.top)
        if not page:
            return
        lvl = 1
        pos = len(self.toc)
        if i is not None:
            lvl = self.toc[i][0]
            pos = i + 1
        self.toc.insert(pos, [lvl, title.strip(), page])
        self._refresh()

    def rename(self):
        i = self._sel()
        if i is None:
            return
        title = simpledialog.askstring("Rename bookmark", "Title:",
                                       initialvalue=self.toc[i][1], parent=self.top)
        if not title:
            return
        self.toc[i][1] = title.strip()
        self._refresh()

    def delete(self):
        i = self._sel()
        if i is None:
            return
        del self.toc[i]
        self._refresh()

    def move(self, d):
        i = self._sel()
        if i is None:
            return
        j = i + d
        if j < 0 or j >= len(self.toc):
            return
        self.toc[i], self.toc[j] = self.toc[j], self.toc[i]
        self._refresh()
        self.lb.selection_set(j)

    def level(self, d):
        i = self._sel()
        if i is None:
            return
        self.toc[i][0] = max(1, min(6, self.toc[i][0] + d))
        self._refresh()
        self.lb.selection_set(i)

    def auto_gen(self):
        tmp = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        tmp.close()
        try:
            res = fp.auto_bookmarks(self.path, tmp.name, max_level=2)
            if not res:
                messagebox.showinfo("Auto bookmarks", "No heading-like text found.",
                                    parent=self.top)
            else:
                doc = fitz.open(tmp.name)
                self.toc = doc.get_toc(simple=True)
                doc.close()
                self._refresh()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)
        finally:
            try:
                os.unlink(tmp.name)
            except Exception:
                pass

    def save(self):
        out = filedialog.asksaveasfilename(parent=self.top, defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(self.path))[0] + "_bookmarks.pdf")
        if not out:
            return
        try:
            fp.set_bookmarks(self.path, out, self.toc)
            self.out = out
            messagebox.showinfo("Saved", "Bookmarks saved to:\n%s" % out, parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)


class MetadataDialog:
    """View/edit PDF metadata."""

    def __init__(self, parent, path):
        self.path = path
        self.saved = None
        md = fp.get_metadata(path)
        self.top = ctk.CTkToplevel(parent)
        self.top.title("Metadata — " + os.path.basename(path))
        self.top.geometry("560x430")
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(fg_color=THEME["bg"])
        card = modern_card(self.top)
        card.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(card, text="Document metadata", font=("Segoe UI", 14, "bold"),
                     text_color=THEME["fg"]).pack(anchor="w", padx=16, pady=(14, 6))
        body = ctk.CTkFrame(card, fg_color="transparent")
        body.pack(fill="x", padx=16)
        self.vars = {}
        for key, label in (("title", "Title"), ("author", "Author"),
                           ("subject", "Subject"), ("keywords", "Keywords")):
            row = ctk.CTkFrame(body, fg_color="transparent")
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=label, font=FONT_SM, text_color=THEME["muted"],
                         width=100, anchor="w").pack(side="left")
            var = tk.StringVar(value=md.get(key) or "")
            self.vars[key] = var
            accent_entry(row, textvariable=var, height=32).pack(side="left", fill="x",
                                                                expand=True)
        ctk.CTkLabel(card, text="Creator: %s\nProducer: %s"
                     % (md.get("creator") or "-", md.get("producer") or "-"),
                     font=FONT_SM, text_color=THEME["muted"], justify="left").pack(
                         anchor="w", padx=16, pady=(10, 0))
        bf = ctk.CTkFrame(card, fg_color="transparent")
        bf.pack(fill="x", padx=16, pady=(14, 16))
        primary_btn(bf, "Save As…", self.save, width=120, height=34).pack(side="left")
        ghost_btn(bf, "Remove all fields", self.clear_all, width=140).pack(side="left", padx=8)
        ghost_btn(bf, "Cancel", self.top.destroy, width=90).pack(side="right")
        self.top.update_idletasks()
        try:
            self.top.geometry("+%d+%d" % (parent.winfo_rootx() + 90,
                                          parent.winfo_rooty() + 70))
        except Exception:
            pass

    def clear_all(self):
        for v in self.vars.values():
            v.set("")

    def save(self):
        out = filedialog.asksaveasfilename(parent=self.top, defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(self.path))[0] + "_meta.pdf")
        if not out:
            return
        try:
            meta = {k: v.get() for k, v in self.vars.items()}
            fp.set_metadata(self.path, out, meta)
            self.saved = out
            messagebox.showinfo("Saved", "Metadata saved to:\n%s" % out, parent=self.top)
            self.top.destroy()
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self.top)


# ═══════════════════════ PDF TOOLS (v4) ═══════════════════════
class ToolsUI:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.signer_var = tk.StringVar(value="AYUSH GUPTA")
        self._build()

    def _build(self):
        main = ctk.CTkScrollableFrame(self.parent, fg_color="transparent",
            scrollbar_fg_color="transparent", scrollbar_button_color="#2a3247",
            scrollbar_button_hover_color="#3a4560")
        main.pack(fill="both", expand=True, padx=(14, 8), pady=14)
        main.grid_columnconfigure(0, weight=1, uniform="tools")
        main.grid_columnconfigure(1, weight=1, uniform="tools")
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, 7))
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=(7, 7))

        # ── left column ──
        c = self._card(left, "Sign & stamps",
                       "Signature, watermark, header/footer, Bates, QR codes")
        ctk.CTkLabel(c, text="Signer name (for text-block signing)", font=FONT_SM,
                     text_color=THEME["muted"]).pack(anchor="w", pady=(2, 2))
        accent_entry(c, textvariable=self.signer_var).pack(fill="x", pady=(0, 6))
        r = ctk.CTkFrame(c, fg_color="transparent"); r.pack(fill="x", pady=2)
        primary_btn(r, "Sign PDF", self.sign_pdf, width=110, height=34).pack(side="left")
        ghost_btn(r, "Signature studio…", self.signature_studio, width=150).pack(side="left", padx=6)
        ghost_btn(r, "QR stamp…", self.qr_stamp, width=104).pack(side="right")
        self._r(c, "Text watermark…", self.watermark_pdf)
        self._r(c, "Header & footer / page numbers…", self.header_footer)
        self._r(c, "Bates numbering…", self.bates_numbering)

        c = self._card(left, "Organize & pages", "Resize, trim, arrange")
        self._r(c, "Normalize page size (A4 / Letter)…", self.normalize_pages)
        self._r(c, "Auto-trim white margins", self.trim_white)
        self._r(c, "Crop margins (mm)…", self.crop_margins)
        self._r(c, "Pages per sheet (N-up)…", self.nup_pages)
        self._r(c, "Split by size (MB)…", self.split_by_size)
        self._r(c, "Print PDF…", self.print_pdf)

        c = self._card(left, "Compress & optimize", "Lossless levels or a target size")
        self._r(c, "Compress PDF…", self.compress_pdf)
        self._r(c, "Compress to target size (MB)…", self.compress_target)

        c = self._card(left, "Convert & extract", "")
        self._r(c, "PDF → images at DPI…", self.pdf_to_images)
        self._r(c, "Extract text from PDF…", lambda: self._run_split("extract_text"))
        self._r(c, "Extract images from PDF…", lambda: self._run_split("extract_images"))
        self._r(c, "Convert to grayscale…", lambda: self._run_split("to_grayscale"))

        c = self._card(left, "Compare & repair", "")
        self._r(c, "Compare two PDFs…", self.compare_pdfs)
        self._r(c, "Repair / rebuild PDF…", self.repair_doc)
        self._r(c, "Sanitize (strip JS & embedded files)…", self.sanitize_doc)

        # ── right column ──
        c = self._card(right, "Security & redaction", "")
        self._r(c, "Redact text…", self.redact_text)
        self._r(c, "Auto-redact patterns (email / phone / card / Aadhaar / PAN)…",
                self.auto_redact)
        self._r(c, "Password protect PDF…", self.password_protect)
        self._r(c, "Remove password from PDF…", self.remove_password)
        self._r(c, "Edit metadata…", self.edit_metadata)
        self._r(c, "Remove metadata", self.remove_metadata)

        c = self._card(right, "Bookmarks", "")
        self._r(c, "Bookmark editor…", self.bookmark_editor)
        self._r(c, "Auto-generate from headings", self.auto_bookmarks)

        c = self._card(right, "Miscellaneous", "")
        self._r(c, "Add page numbers", self.add_page_numbers)
        self._r(c, "Flatten PDF (annotations)", self.flatten_pdf)
        self._r(c, "Clone open PDF x2", lambda: self._run_split("dup_pgs"))
        ctk.CTkFrame(c, height=1, fg_color=THEME["border"]).pack(fill="x", pady=8)
        ctk.CTkButton(c, text="★  Rate & Review", command=self.open_rating, height=36,
            fg_color=THEME["accent2"], hover_color="#9d74ff", text_color="#ffffff",
            corner_radius=9, font=FONT_BOLD).pack(fill="x")

    # ── layout helpers ──
    def _card(self, parent, title, sub=""):
        f = modern_card(parent); f.pack(fill="x", pady=(0, 12))
        c = ctk.CTkFrame(f, fg_color="transparent"); c.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c, text=title, font=FONT_LARGE, text_color=THEME["fg"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(c, text=sub, font=FONT_SM,
                         text_color=THEME["muted"]).pack(anchor="w", pady=(0, 4))
        return c

    def _r(self, parent, text, cmd):
        ghost_btn(parent, text, cmd).pack(fill="x", pady=3)

    def open_rating(self):
        RatingDialog(self.parent)

    def _run_split(self, method):
        su = self.app.split_ui
        if not su.doc:
            messagebox.showerror("Error", "Open a PDF in the Split tab first.")
            return
        getattr(su, method)()

    def _done(self, title, out, extra="", open_dir=True):
        if isinstance(out, (list, tuple)):
            out = out[0] if out else ""
        msg = title
        if out:
            msg += "\n\n%s" % out
        if extra:
            msg += "\n" + extra
        messagebox.showinfo("Done", msg)
        if open_dir and out and os.path.isfile(out):
            try:
                os.startfile(os.path.dirname(os.path.abspath(out)))
            except Exception:
                pass

    def _run_file_op(self, title, worker, form_fields=None, suffix="_out", intro=""):
        path = filedialog.askopenfilename(title="Select PDF — " + title,
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return None
        prm = {}
        if form_fields:
            dlg = SimpleFormDialog(self.parent, title, form_fields, intro=intro)
            if dlg.result is None:
                return None
            prm = dlg.result
        base = os.path.splitext(os.path.basename(path))[0]
        out = filedialog.asksaveasfilename(title="Save output — " + title,
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=base + suffix + ".pdf")
        if not out:
            return None
        self.app.run_bg(lambda pr: worker(path, out, prm, pr), title + "…",
                        on_done=lambda r: self._done(title, r))
        return out

    # ── signing ──
    def signature_studio(self):
        SignatureStudio(self.parent, self)

    def sign_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF to sign",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        sig = str(SIGNATURE_FILE)
        if os.path.exists(sig):
            self._sign_with_image(path, sig)
        else:
            self._sign_with_text(path)

    def _sign_with_image(self, path, sig):
        try:
            total = fp.page_count(path)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return
        fields = [("page", "Page (1-%d or 'last')" % total, "text", "last"),
                  ("place", "Position", "combo", "Bottom-Right",
                   ["Bottom-Right", "Bottom-Left", "Top-Right", "Top-Left", "Center",
                    "Custom (click preview)"]),
                  ("width", "Width (% of page)", "float", 30.0)]
        dlg = SimpleFormDialog(self.parent, "Sign PDF — saved signature", fields,
            intro="Using the signature from the Signature studio.")
        if dlg.result is None:
            return
        prm = dlg.result
        pg_txt = str(prm["page"]).strip().lower()
        try:
            idx = total - 1 if pg_txt == "last" else max(0, min(int(float(pg_txt)) - 1, total - 1))
        except Exception:
            idx = total - 1
        preset = {"Bottom-Right": (0.80, 0.92), "Bottom-Left": (0.22, 0.92),
                  "Top-Right": (0.80, 0.08), "Top-Left": (0.22, 0.08),
                  "Center": (0.5, 0.5)}
        if str(prm.get("place")).startswith("Custom"):
            d = SignPreviewDialog(self.parent, path, idx)
            if d.result is None:
                return
            cx, cy = d.result
        else:
            cx, cy = preset.get(prm.get("place"), preset["Bottom-Right"])
        wf = max(0.05, min(0.9, float(prm.get("width") or 30) / 100.0))
        out = filedialog.asksaveasfilename(
            defaultextension=".pdf", filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(path))[0] + "_signed.pdf")
        if not out:
            return
        self.app.run_bg(
            lambda pr: fp.place_signature_pdf(path, out, sig, cx=cx, cy=cy,
                                              width_frac=wf, page_index=idx),
            "Signing…", on_done=lambda r: self._done("Signed", r))

    def _sign_with_text(self, path):
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="signed.pdf")
        if not out:
            return
        try:
            doc = fitz.open(path)
            signer = self.signer_var.get().strip() or "AYUSH GUPTA"
            target_pg = len(doc) - 1
            pg = doc[target_pg]
            rect = pg.rect
            w, h = rect.width, rect.height
            x0, y0, x1, y1 = w - 260, h - 60, w - 20, h - 20
            shape = pg.new_shape()
            shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
            shape.finish(color=(0.1, 0.3, 0.6), fill=(0.95, 0.95, 1), width=1.5)
            shape.insert_text(fitz.Point(x0 + 12, y0 + 28), "Digitally Signed",
                              fontsize=10, color=(0.3, 0.3, 0.3))
            shape.insert_text(fitz.Point(x0 + 12, y0 + 48), signer, fontsize=14,
                              color=(0.1, 0.3, 0.6))
            shape.insert_text(fitz.Point(x0 + 12, y0 + 64),
                              datetime.now().strftime("%Y-%m-%d %H:%M"), fontsize=8,
                              color=(0.5, 0.5, 0.5))
            shape.commit()
            safe_save(doc, out, True)
            doc.close()
            self._done("PDF signed by %s\n\nTip: use the Signature studio to create a "
                       "hand-drawn signature for image signing." % signer, out)
        except Exception as e:
            messagebox.showerror("Error", "Sign failed:\n%s" % e)


    # ── stamps ──
    def watermark_pdf(self):
        fields = [("text", "Text", "text", "CONFIDENTIAL"),
                  ("opacity", "Opacity (0.05 - 1)", "float", 0.3),
                  ("rotation", "Angle", "int", 35),
                  ("tiled", "Tile across page", "check", False)]
        self._run_file_op("Add watermark",
            lambda path, out, prm, pr: fp.watermark_pdf(path, out, text=prm["text"],
                opacity=prm["opacity"], rotation=prm["rotation"], tiled=prm["tiled"],
                progress=pr), fields, suffix="_wm")

    def header_footer(self):
        fields = [("fmt", "Format", "text", "{page} / {total}"),
                  ("position", "Position", "combo", "bottom-center",
                   ["bottom-center", "bottom-right", "bottom-left",
                    "top-center", "top-right", "top-left"])]
        self._run_file_op("Header & footer",
            lambda path, out, prm, pr: fp.header_footer_pdf(path, out, fmt=prm["fmt"],
                position=prm["position"], progress=pr), fields, suffix="_hf",
            intro="Placeholders: {page}  {total}  {date}  {filename}")

    def bates_numbering(self):
        fields = [("prefix", "Prefix", "text", "DOC-"),
                  ("start", "Start at", "int", 1),
                  ("digits", "Digits", "int", 6),
                  ("position", "Position", "combo", "bottom-right",
                   ["bottom-right", "bottom-center", "top-right", "top-left"])]
        self._run_file_op("Bates numbering",
            lambda path, out, prm, pr: fp.bates_pdf(path, out, prefix=prm["prefix"],
                start=prm["start"], digits=prm["digits"], position=prm["position"],
                progress=pr), fields, suffix="_bates")

    def qr_stamp(self):
        fields = [("data", "QR data (URL / text)", "text", "https://"),
                  ("position", "Position", "combo", "bottom-right",
                   ["bottom-right", "bottom-left", "top-right", "top-left"]),
                  ("size_mm", "Size (mm)", "float", 28.0)]
        self._run_file_op("QR stamp",
            lambda path, out, prm, pr: fp.qr_stamp_pdf(path, out, prm["data"],
                position=prm["position"], size_mm=prm["size_mm"], progress=pr),
            fields, suffix="_qr")

    # ── pages ──
    def normalize_pages(self):
        fields = [("size", "Page size", "combo", "A4", ["A4", "Letter"]),
                  ("orientation", "Orientation", "combo", "auto",
                   ["auto", "portrait", "landscape"])]
        self._run_file_op("Normalize page size",
            lambda path, out, prm, pr: fp.normalize_pages(path, out, size=prm["size"],
                orientation=prm["orientation"], progress=pr), fields, suffix="_a4")

    def trim_white(self):
        self._run_file_op("Auto-trim margins",
            lambda path, out, prm, pr: fp.trim_margins(path, out, progress=pr),
            None, suffix="_trim")

    def crop_margins(self):
        fields = [("left", "Left (mm)", "float", 0), ("right", "Right (mm)", "float", 0),
                  ("top", "Top (mm)", "float", 0), ("bottom", "Bottom (mm)", "float", 0)]
        self._run_file_op("Crop margins",
            lambda path, out, prm, pr: fp.crop_margins(path, out, left=prm["left"],
                right=prm["right"], top=prm["top"], bottom=prm["bottom"], progress=pr),
            fields, suffix="_crop")

    def nup_pages(self):
        fields = [("n", "Pages per sheet", "combo", "2", ["2", "4", "6"]),
                  ("orientation", "Orientation", "combo", "portrait",
                   ["portrait", "landscape"]),
                  ("size", "Page size", "combo", "A4", ["A4", "Letter"])]
        self._run_file_op("N-up",
            lambda path, out, prm, pr: fp.nup_pdf(path, out, n=int(prm["n"]),
                orientation=prm["orientation"], page_size=prm["size"], progress=pr),
            fields, suffix="_nup")

    def split_by_size(self):
        path = filedialog.askopenfilename(title="Select PDF — split by size",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        dlg = SimpleFormDialog(self.parent, "Split by size",
                               [("mb", "Max size per part (MB)", "float", 10.0)])
        if dlg.result is None:
            return
        d = filedialog.askdirectory(title="Output folder for parts")
        if not d:
            return
        mb = dlg.result["mb"]
        self.app.run_bg(lambda pr: fp.split_by_size(path, d, max_mb=mb, progress=pr),
                        "Splitting…",
                        on_done=lambda r: self._done(
                            "Split into %d part(s)" % (len(r) if r else 0),
                            r[-1] if r else ""))

    def print_pdf(self):
        path = filedialog.askopenfilename(title="Print PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            fp.print_pdf(path)
            messagebox.showinfo("Print", "Sent to the default printer:\n%s" % path)
        except Exception as e:
            messagebox.showerror("Error", "Printing failed:\n%s" % e)

    # ── compression ──
    def compress_pdf(self):
        lvls = ["Low (garbage)", "Medium (deflate)", "High (deflate+images)",
                "Max (full optimize)"]
        path = filedialog.askopenfilename(title="Select PDF to compress",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        dlg = SimpleFormDialog(self.parent, "Compress PDF",
                               [("level", "Level", "combo", lvls[1], lvls)])
        if dlg.result is None:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(path))[0] + "_compressed.pdf")
        if not out:
            return
        lvl = {"Low (garbage)": "low", "Medium (deflate)": "medium",
               "High (deflate+images)": "high", "Max (full optimize)": "max"}.get(
                   dlg.result["level"], "medium")

        def done(res):
            try:
                orig = os.path.getsize(path)
                comp = os.path.getsize(res)
                pct = (1 - comp / orig) * 100 if orig else 0
                extra = "%.1f MB → %.1f MB  (%.0f%% smaller)" % (orig / 1e6, comp / 1e6, pct)
            except Exception:
                extra = ""
            self._done("Compressed", res, extra=extra)

        self.app.run_bg(lambda pr: fp.compress_pdf(path, out, level=lvl, progress=pr),
                        "Compressing…", on_done=done)

    def compress_target(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        dlg = SimpleFormDialog(self.parent, "Compress to target size",
            [("mb", "Target size (MB)", "float", 5.0)],
            intro="Tries lossless first; if still too big, rasterizes pages at decreasing DPI.")
        if dlg.result is None:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=os.path.splitext(os.path.basename(path))[0] + "_target.pdf")
        if not out:
            return
        mb = dlg.result["mb"]

        def done(res):
            file_out, mode = res
            try:
                size_mb = os.path.getsize(file_out) / 1e6
                extra = "%s  (%.2f MB)" % (mode, size_mb)
            except Exception:
                extra = mode
            self._done("Compressed to target", file_out, extra=extra)

        self.app.run_bg(lambda pr: fp.compress_to_target(path, out, target_mb=mb,
                                                         progress=pr),
                        "Compressing…", on_done=done)

    # ── convert / compare / repair ──
    def pdf_to_images(self):
        path = filedialog.askopenfilename(title="Select PDF to export",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        dlg = SimpleFormDialog(self.parent, "PDF to images",
            [("fmt", "Format", "combo", "png", ["png", "jpg", "webp"]),
             ("dpi", "DPI", "int", 150)])
        if dlg.result is None:
            return
        d = filedialog.askdirectory(title="Output folder for images")
        if not d:
            return
        self.app.run_bg(lambda pr: fp.pdf_to_images(path, d, fmt=dlg.result["fmt"],
                                                    dpi=dlg.result["dpi"], progress=pr),
                        "Exporting pages…",
                        on_done=lambda r: self._done("Exported %d image(s)"
                                                     % (len(r) if r else 0), d))

    def compare_pdfs(self):
        a = filedialog.askopenfilename(title="Select FIRST PDF", filetypes=[("PDF", "*.pdf")])
        if not a:
            return
        b = filedialog.askopenfilename(title="Select SECOND PDF", filetypes=[("PDF", "*.pdf")])
        if not b:
            return
        self.app.run_bg(lambda pr: fp.compare_pdfs(a, b, progress=pr), "Comparing…",
                        on_done=self._show_compare)

    def _show_compare(self, res):
        _summary, lines = res
        top = ctk.CTkToplevel(self.parent)
        top.title("Compare result")
        top.geometry("720x540")
        top.transient(self.parent)
        top.configure(fg_color=THEME["bg"])
        f = ctk.CTkFrame(top, fg_color="transparent")
        f.pack(fill="both", expand=True, padx=14, pady=14)
        ctk.CTkLabel(f, text="Text differences (per page)", font=FONT_BOLD,
                     text_color=THEME["fg"]).pack(anchor="w")
        txt = ctk.CTkTextbox(f, corner_radius=10, fg_color=THEME["surface2"],
            border_width=1, border_color=THEME["border"], text_color=THEME["fg"], font=FONT)
        txt.pack(fill="both", expand=True, pady=(8, 10))
        txt.insert("1.0", "\n".join(lines))
        txt.configure(state="disabled")
        ghost_btn(f, "Close", top.destroy, width=100).pack(anchor="e")

    def repair_doc(self):
        self._run_file_op("Repair PDF",
            lambda path, out, prm, pr: fp.repair_pdf(path, out), None, suffix="_repaired")

    def sanitize_doc(self):
        self._run_file_op("Sanitize PDF",
            lambda path, out, prm, pr: fp.sanitize_pdf(path, out), None, suffix="_clean")

    # ── security ──
    def auto_redact(self):
        fields = [("emails", "Emails", "check", True),
                  ("phones", "Phone numbers", "check", True),
                  ("cards", "Card numbers", "check", True),
                  ("aadhaar", "Aadhaar numbers", "check", True),
                  ("pan", "PAN codes", "check", True),
                  ("ifsc", "IFSC codes", "check", False),
                  ("custom", "Custom regex", "text", "")]

        def worker(path, out, prm, pr):
            names = [n for n in ("emails", "phones", "cards", "aadhaar", "pan", "ifsc")
                     if prm.get(n)]
            if not names and not prm.get("custom"):
                raise ValueError("Select at least one pattern.")
            return fp.auto_redact(path, out, pattern_names=names,
                                  custom=prm.get("custom", ""), progress=pr)

        self._run_file_op("Auto-redact patterns", worker, fields, suffix="_redacted")

    def edit_metadata(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        MetadataDialog(self.parent, path)

    def bookmark_editor(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        BookmarkEditor(self.parent, path)

    def auto_bookmarks(self):
        def worker(path, out, prm, pr):
            res = fp.auto_bookmarks(path, out, max_level=prm["level"], progress=pr)
            if not res:
                raise RuntimeError("No heading-like text found in this PDF.")
            return res

        self._run_file_op("Auto bookmarks", worker, [("level", "Max levels", "int", 2)],
                          suffix="_bookmarks")

    # ── ported v3 tools ──
    def redact_text(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        txt = simpledialog.askstring("Redact Text", "Text to redact (case-sensitive):")
        if not txt:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="redacted.pdf")
        if not out:
            return
        try:
            doc = fitz.open(path)
            for pgnum in range(len(doc)):
                pg = doc[pgnum]
                for r in pg.search_for(txt):
                    pg.add_redact_annot(r)
                    pg.apply_redactions()
            safe_save(doc, out, True)
            doc.close()
            self._done("Redacted '%s'" % txt, out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def password_protect(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        pw = simpledialog.askstring("Password", "Enter password to encrypt:", show="*")
        if not pw or not pw.strip():
            return
        pw = pw.strip()
        pw2 = simpledialog.askstring("Password", "Confirm password:", show="*")
        if pw != pw2:
            messagebox.showerror("Error", "Passwords don't match")
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="protected.pdf")
        if not out:
            return
        try:
            fp.protect_pdf(path, out, pw)
            self._done("PDF encrypted", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_password(self):
        path = filedialog.askopenfilename(title="Select encrypted PDF",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        pw = simpledialog.askstring("Password", "Enter current password:", show="*")
        if pw is None:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="decrypted.pdf")
        if not out:
            return
        try:
            fp.unlock_pdf(path, out, pw or "")
            self._done("Password removed", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_metadata(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="cleaned.pdf")
        if not out:
            return
        try:
            fp.remove_metadata(path, out)
            self._done("Metadata removed", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def add_page_numbers(self):
        self._run_file_op("Add page numbers",
            lambda path, out, prm, pr: fp.header_footer_pdf(path, out,
                fmt="{page} / {total}", position="bottom-center", progress=pr),
            None, suffix="_numbered")

    def flatten_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="flattened.pdf")
        if not out:
            return
        try:
            doc = fitz.open(path)
            for pgnum in range(len(doc)):
                pg = doc[pgnum]
                for annot in pg.annots():
                    pg.delete_annot(annot)
            safe_save(doc, out, True)
            doc.close()
            self._done("Annotations flattened", out)
        except Exception as e:
            messagebox.showerror("Error", str(e))


# ═══════════════════════ IMAGE TOOLS (v4) ═══════════════════════
class ImageToolsUI:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.images = []
        self._build()

    def _build(self):
        main = ctk.CTkScrollableFrame(self.parent, fg_color="transparent",
            scrollbar_fg_color="transparent", scrollbar_button_color="#2a3247",
            scrollbar_button_hover_color="#3a4560")
        main.pack(fill="both", expand=True, padx=(14, 8), pady=14)
        main.grid_columnconfigure(0, weight=1, uniform="imgtools")
        main.grid_columnconfigure(1, weight=1, uniform="imgtools")
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, 7))
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=(7, 7))

        # ── left column ──
        c = self._card(left, "Images", "Every tool below works on this list")
        lw = ctk.CTkFrame(c, fg_color="transparent")
        lw.pack(fill="x")
        self.lb = ReorderListbox(lw, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0, height=7)
        sc = ctk.CTkScrollbar(lw, command=self.lb.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.lb.configure(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y", padx=(8, 0))
        self.lb.on_move = self._on_reorder
        rr = ctk.CTkFrame(c, fg_color="transparent")
        rr.pack(fill="x", pady=(8, 0))
        ghost_btn(rr, "Add images", self.add_images, width=104).pack(side="left")
        ghost_btn(rr, "Add folder", self.add_folder, width=96).pack(side="left", padx=6)
        ghost_btn(rr, "Remove", self.remove_sel, width=80).pack(side="left")
        ghost_btn(rr, "Clear", self.clear_all, width=70).pack(side="right")
        self.count_lbl = ctk.CTkLabel(c, text="0 image(s)", font=FONT_SM,
                                      text_color=THEME["muted"])
        self.count_lbl.pack(anchor="w", pady=(6, 0))

        c = self._card(left, "Compress & convert", "JPEG compression or format change")
        qf = ctk.CTkFrame(c, fg_color="transparent")
        qf.pack(fill="x")
        ctk.CTkLabel(qf, text="JPG quality", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.q = modern_slider(qf, 1, 100, 99)
        self.q.set(60)
        self.q.pack(side="left", fill="x", expand=True)
        self.q_lbl = ctk.CTkLabel(qf, text="60", width=32, font=FONT_BOLD,
                                  text_color=THEME["fg"])
        self.q_lbl.pack(side="left", padx=(8, 0))
        self.q.configure(command=lambda v: self.q_lbl.configure(
            text=str(int(round(float(v))))))
        self._r(c, "Compress images → JPEG", self.compress_images)
        fr = ctk.CTkFrame(c, fg_color="transparent")
        fr.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(fr, text="Format", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.fmt_combo = modern_combo(fr, ["JPEG", "PNG", "WEBP", "BMP", "TIFF", "GIF"],
                                      width=120)
        self.fmt_combo.set("PNG")
        self.fmt_combo.pack(side="left")
        self._r(c, "Convert to selected format", self.convert_images)
        self._r(c, "Create .ICO icon", self.make_ico)

        c = self._card(left, "Resize & transform", "")
        rf = ctk.CTkFrame(c, fg_color="transparent")
        rf.pack(fill="x")
        ctk.CTkLabel(rf, text="Percent", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        self.pct_var = tk.StringVar(value="50")
        accent_entry(rf, textvariable=self.pct_var, width=56, height=30).pack(side="left", padx=6)
        ctk.CTkLabel(rf, text="Width", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        self.w_var = tk.StringVar(value="")
        accent_entry(rf, textvariable=self.w_var, width=64, height=30).pack(side="left", padx=6)
        ctk.CTkLabel(rf, text="Height", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        self.h_var = tk.StringVar(value="")
        accent_entry(rf, textvariable=self.h_var, width=64, height=30).pack(side="left", padx=6)
        self._r(c, "Resize (percent, or width/height)", self.resize_images)
        tr = ctk.CTkFrame(c, fg_color="transparent")
        tr.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(tr, text="Rotate", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        self.rot_combo = modern_combo(tr, ["90", "-90", "180"], width=80)
        self.rot_combo.set("90")
        self.rot_combo.pack(side="left", padx=6)
        ctk.CTkLabel(tr, text="Flip", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left")
        self.flip_combo = modern_combo(tr, ["none", "horizontal", "vertical"], width=110)
        self.flip_combo.set("none")
        self.flip_combo.pack(side="left", padx=6)
        self._r(c, "Apply rotation / flip", self.rotate_images)
        self._r(c, "Grayscale", self.grayscale_images)

        # ── right column ──
        c = self._card(right, "Enhance & filters", "1.0 = unchanged")
        self.sliders = {}
        for key, label, lo, hi, dflt in (
                ("brightness", "Brightness", 0.5, 1.5, 1.0),
                ("contrast", "Contrast", 0.5, 1.5, 1.0),
                ("saturation", "Saturation", 0.0, 2.0, 1.0),
                ("sharpness", "Sharpness", 0.0, 2.0, 1.0)):
            row = ctk.CTkFrame(c, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=FONT_SM, text_color=THEME["muted"],
                         width=90, anchor="w").pack(side="left")
            s = modern_slider(row, lo, hi, max(2, int((hi - lo) * 20)))
            s.set(dflt)
            s.pack(side="left", fill="x", expand=True)
            vl = ctk.CTkLabel(row, text="%.1f" % dflt, width=36, font=FONT_SM,
                              text_color=THEME["fg"])
            vl.pack(side="left", padx=(8, 0))
            s.configure(command=lambda v, l=vl: l.configure(text="%.2f" % float(v)))
            self.sliders[key] = s
        self._r(c, "Apply adjustments", self.adjust_images)
        self._r(c, "Auto-trim borders", self.trim_images)
        self._r(c, "Strip EXIF / metadata", self.exif_strip)
        self._r(c, "Add border / frame…", self.add_border)

        c = self._card(right, "Watermark images", "")
        wf = ctk.CTkFrame(c, fg_color="transparent")
        wf.pack(fill="x")
        ctk.CTkLabel(wf, text="Text", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.wm_var = tk.StringVar(value="PDF Suite Pro")
        accent_entry(wf, textvariable=self.wm_var, height=30).pack(side="left", fill="x",
                                                                  expand=True)
        pf = ctk.CTkFrame(c, fg_color="transparent")
        pf.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(pf, text="Position", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.wm_pos = modern_combo(pf, ["bottom-right", "bottom-center", "bottom-left",
                                        "top-right", "top-center", "top-left", "middle"],
                                   width=130)
        self.wm_pos.set("bottom-right")
        self.wm_pos.pack(side="left")
        ctk.CTkLabel(pf, text="Opacity", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(12, 8))
        self.wm_op = modern_slider(pf, 0.05, 1.0, 19)
        self.wm_op.set(0.55)
        self.wm_op.pack(side="left", fill="x", expand=True)
        self._r(c, "Apply watermark", self.watermark_images)

        c = self._card(right, "Create PDF / export", "")
        xf = ctk.CTkFrame(c, fg_color="transparent")
        xf.pack(fill="x")
        ctk.CTkLabel(xf, text="PDF page", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.pdf_page = modern_combo(xf, ["Fit image", "A4 (fit)", "Letter (fit)"], width=130)
        self.pdf_page.set("A4 (fit)")
        self.pdf_page.pack(side="left")
        self._r(c, "Images → PDF…", self.images_to_pdf)
        self._r(c, "PDF → images (DPI)…", self.pdf_to_images)

        c = self._card(right, "Batch rename", "Placeholders: {name} {n} {date}")
        nf = ctk.CTkFrame(c, fg_color="transparent")
        nf.pack(fill="x")
        ctk.CTkLabel(nf, text="Pattern", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 6))
        self.pat_var = tk.StringVar(value="{name}_{n}")
        accent_entry(nf, textvariable=self.pat_var, height=30).pack(side="left", fill="x",
                                                                    expand=True)
        nf2 = ctk.CTkFrame(c, fg_color="transparent")
        nf2.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(nf2, text="Start", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 6))
        self.start_var = tk.StringVar(value="1")
        accent_entry(nf2, textvariable=self.start_var, width=56, height=30).pack(side="left")
        ctk.CTkLabel(nf2, text="Pad", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(10, 6))
        self.pad_var = tk.StringVar(value="3")
        accent_entry(nf2, textvariable=self.pad_var, width=56, height=30).pack(side="left")
        nr = ctk.CTkFrame(c, fg_color="transparent")
        nr.pack(fill="x", pady=(8, 0))
        ghost_btn(nr, "Preview", self.rename_preview, width=100).pack(side="left")
        ghost_btn(nr, "Rename in place", self.rename_apply, width=140).pack(side="left", padx=8)

    # ── layout helpers ──
    def _card(self, parent, title, sub=""):
        f = modern_card(parent)
        f.pack(fill="x", pady=(0, 12))
        c = ctk.CTkFrame(f, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c, text=title, font=FONT_LARGE, text_color=THEME["fg"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(c, text=sub, font=FONT_SM,
                         text_color=THEME["muted"]).pack(anchor="w", pady=(0, 4))
        return c

    def _r(self, parent, text, cmd):
        ghost_btn(parent, text, cmd).pack(fill="x", pady=3)

    # ── list management ──
    def add_images(self):
        ps = filedialog.askopenfilenames(title="Select images",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff *.gif *.ico"),
                       ("All files", "*.*")])
        if ps:
            self.add_images_to_list(ps)

    def add_images_to_list(self, paths):
        added = 0
        for p in paths:
            if p and p not in self.images:
                self.images.append(p)
                self.lb.insert("end", os.path.basename(p))
                added += 1
        self._upd_count()
        return added

    def add_folder(self):
        d = filedialog.askdirectory(title="Select image folder")
        if not d:
            return
        try:
            from glob import glob
            paths = []
            for ext in fi.IMG_EXTS:
                paths.extend(glob(os.path.join(d, "*" + ext)))
                paths.extend(glob(os.path.join(d, "*" + ext.upper())))
            n = self.add_images_to_list(sorted(set(paths)))
            if not n:
                messagebox.showinfo("Add folder", "No images found in that folder.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def remove_sel(self):
        for i in reversed(self.lb.curselection()):
            self.lb.delete(i)
            del self.images[i]
        self._upd_count()

    def clear_all(self):
        self.lb.delete(0, "end")
        self.images = []
        self._upd_count()

    def _on_reorder(self, a, b):
        if 0 <= a < len(self.images) and 0 <= b < len(self.images):
            item = self.images.pop(a)
            self.images.insert(b, item)

    def _upd_count(self):
        self.count_lbl.configure(text="%d image(s)" % len(self.images))

    def _refresh_list(self):
        self.lb.delete(0, "end")
        for p in self.images:
            self.lb.insert("end", os.path.basename(p))
        self._upd_count()

    def _done_results(self, outdir, results, title="Done"):
        results = results or []
        bad = [r for r in results if r[2]]
        ok = len(results) - len(bad)
        msg = "%s\n%d of %d succeeded" % (outdir, ok, len(results))
        if bad:
            msg += "\n\nFirst error:\n%s" % bad[0][2]
        messagebox.showinfo(title, msg)
        try:
            os.startfile(outdir)
        except Exception:
            pass

    def _img_op(self, title, worker, form_fields=None):
        if not self.images:
            messagebox.showerror("Error", "Add images first.")
            return
        prm = {}
        if form_fields:
            dlg = SimpleFormDialog(self.parent, title, form_fields)
            if dlg.result is None:
                return
            prm = dlg.result
        d = filedialog.askdirectory(title="Output folder — " + title)
        if not d:
            return
        self.app.run_bg(lambda pr: worker(list(self.images), d, prm, pr), title + "…",
                        on_done=lambda res: self._done_results(d, res, title))

    # ── operations ──
    def compress_images(self):
        q = int(round(float(self.q.get())))
        self._img_op("Compress images",
            lambda paths, d, prm, pr: fi.compress_images(paths, d, quality=q, progress=pr))

    def convert_images(self):
        fmt = self.fmt_combo.get()
        self._img_op("Convert format",
            lambda paths, d, prm, pr: fi.convert_images(paths, d, fmt=fmt, progress=pr))

    def make_ico(self):
        self._img_op("Create ICO", lambda paths, d, prm, pr: fi.to_ico(paths, d, progress=pr))

    def resize_images(self):
        pct = self.pct_var.get().strip()
        w = self.w_var.get().strip()
        h = self.h_var.get().strip()
        try:
            percent = float(pct) if pct else None
            width = int(float(w)) if w else None
            height = int(float(h)) if h else None
        except ValueError:
            messagebox.showerror("Error", "Enter numeric values.")
            return
        if not percent and not width and not height:
            messagebox.showerror("Error", "Enter a percent or width/height.")
            return
        self._img_op("Resize images",
            lambda paths, d, prm, pr: fi.resize_images(paths, d, percent=percent,
                width=width, height=height, progress=pr))

    def rotate_images(self):
        try:
            angle = int(float(self.rot_combo.get()))
        except ValueError:
            angle = 90
        flip = self.flip_combo.get()
        self._img_op("Rotate / flip",
            lambda paths, d, prm, pr: fi.rotate_images(paths, d, angle=angle, flip=flip,
                                                       progress=pr))

    def grayscale_images(self):
        self._img_op("Grayscale",
            lambda paths, d, prm, pr: fi.grayscale_images(paths, d, progress=pr))


    def adjust_images(self):
        vals = {k: float(s.get()) for k, s in self.sliders.items()}
        self._img_op("Adjust images",
            lambda paths, d, prm, pr: fi.adjust_images(paths, d,
                brightness=vals["brightness"], contrast=vals["contrast"],
                saturation=vals["saturation"], sharpness=vals["sharpness"], progress=pr))

    def trim_images(self):
        self._img_op("Trim borders",
            lambda paths, d, prm, pr: fi.trim_images(paths, d, progress=pr))

    def exif_strip(self):
        self._img_op("Strip EXIF",
            lambda paths, d, prm, pr: fi.strip_exif(paths, d, progress=pr))

    def add_border(self):
        self._img_op("Add border",
            lambda paths, d, prm, pr: fi.add_border(paths, d, width=prm.get("width", 24),
                color=prm.get("color", "#ffffff"), progress=pr),
            [("width", "Border width (px)", "int", 24),
             ("color", "Colour (name or #hex)", "text", "#ffffff")])

    def watermark_images(self):
        text = self.wm_var.get().strip() or "PDF Suite Pro"
        pos = self.wm_pos.get()
        op = float(self.wm_op.get())
        self._img_op("Watermark images",
            lambda paths, d, prm, pr: fi.watermark_images(paths, d, text=text,
                position=pos, opacity=op, progress=pr))

    def images_to_pdf(self):
        if not self.images:
            messagebox.showerror("Error", "Add images first.")
            return
        page = {"Fit image": "fit", "A4 (fit)": "A4", "Letter (fit)": "Letter"}.get(
            self.pdf_page.get(), "A4")
        out = filedialog.asksaveasfilename(defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")], initialfile="images.pdf")
        if not out:
            return

        def done(r):
            messagebox.showinfo("Done", "PDF created:\n%s" % r)
            try:
                os.startfile(os.path.dirname(os.path.abspath(r)))
            except Exception:
                pass

        self.app.run_bg(lambda pr: fi.images_to_pdf(list(self.images), out, page=page,
                                                   progress=pr),
                        "Creating PDF…", on_done=done)

    def pdf_to_images(self):
        path = filedialog.askopenfilename(title="Select PDF to export",
                                          filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        dlg = SimpleFormDialog(self.parent, "PDF to images",
            [("fmt", "Format", "combo", "png", ["png", "jpg", "webp"]),
             ("dpi", "DPI", "int", 150)])
        if dlg.result is None:
            return
        d = filedialog.askdirectory(title="Output folder for images")
        if not d:
            return

        def done(r):
            messagebox.showinfo("Done", "Exported %d image(s) to:\n%s" % (len(r or []), d))
            try:
                os.startfile(d)
            except Exception:
                pass

        self.app.run_bg(lambda pr: fp.pdf_to_images(path, d, fmt=dlg.result["fmt"],
                                                    dpi=dlg.result["dpi"], progress=pr),
                        "Exporting pages…", on_done=done)

    def rename_preview(self):
        if not self.images:
            messagebox.showerror("Error", "Add images first.")
            return
        try:
            start = int(float(self.start_var.get() or 1))
            pad = int(float(self.pad_var.get() or 3))
        except ValueError:
            start, pad = 1, 3
        plan = fi.rename_plan(self.images, self.pat_var.get(), start, pad)
        lines = ["%s  →  %s" % (os.path.basename(s), os.path.basename(d))
                 for s, d in plan[:25]]
        if len(plan) > 25:
            lines.append("… and %d more" % (len(plan) - 25))
        messagebox.showinfo("Rename preview", "\n".join(lines) or "Nothing to rename")

    def rename_apply(self):
        if not self.images:
            messagebox.showerror("Error", "Add images first.")
            return
        if not messagebox.askyesno("Rename",
                                   "Rename %d file(s) in place?" % len(self.images)):
            return
        try:
            start = int(float(self.start_var.get() or 1))
            pad = int(float(self.pad_var.get() or 3))
        except ValueError:
            start, pad = 1, 3
        results = fi.rename_batch(self.images, self.pat_var.get(), start, pad)
        ok = 0
        bad = []
        new_list = []
        for src, dst, err in results:
            if err:
                bad.append("%s: %s" % (os.path.basename(src), err))
                new_list.append(src)
            else:
                ok += 1
                new_list.append(dst)
        self.images = new_list
        self._refresh_list()
        msg = "%d renamed" % ok
        if bad:
            msg += "\n%d failed:\n%s" % (len(bad), "\n".join(bad[:5]))
        messagebox.showinfo("Rename", msg)


# ═══════════════════════ AUTOMATION (v4) ═══════════════════════
class AutomationUI:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.recipe = None
        self.recipe_file = None
        self.recipe_files = {}
        self.watches = []
        self._logq = queue.Queue()
        self._build()
        self._poll_log()

    def _build(self):
        main = ctk.CTkScrollableFrame(self.parent, fg_color="transparent",
            scrollbar_fg_color="transparent", scrollbar_button_color="#2a3247",
            scrollbar_button_hover_color="#3a4560")
        main.pack(fill="both", expand=True, padx=(14, 8), pady=14)
        main.grid_columnconfigure(0, weight=1, uniform="auto")
        main.grid_columnconfigure(1, weight=1, uniform="auto")
        left = ctk.CTkFrame(main, fg_color="transparent")
        left.grid(row=0, column=0, sticky="new", padx=(0, 7))
        right = ctk.CTkFrame(main, fg_color="transparent")
        right.grid(row=0, column=1, sticky="new", padx=(7, 7))

        # ── recipes ──
        c = self._card(left, "Recipes",
                       "A recipe is a list of steps applied to every input file")
        lw = ctk.CTkFrame(c, fg_color="transparent")
        lw.pack(fill="x")
        self.recipe_lb = tk.Listbox(lw, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0, height=4)
        sc = ctk.CTkScrollbar(lw, command=self.recipe_lb.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.recipe_lb.configure(yscrollcommand=sc.set)
        self.recipe_lb.pack(side="left", fill="both", expand=True)
        sc.pack(side="right", fill="y", padx=(8, 0))
        self.recipe_lb.bind("<<ListboxSelect>>", self._on_recipe_select)
        rr = ctk.CTkFrame(c, fg_color="transparent")
        rr.pack(fill="x", pady=(8, 0))
        ghost_btn(rr, "New", self.new_recipe, width=70).pack(side="left")
        ghost_btn(rr, "Load…", self.load_recipe_dlg, width=80).pack(side="left", padx=6)
        ghost_btn(rr, "Save as…", self.save_recipe_dlg, width=92).pack(side="left")
        ghost_btn(rr, "Remove", self.delete_recipe, width=84).pack(side="right")
        self.cur_lbl = ctk.CTkLabel(c, text="No recipe loaded", font=FONT_SM,
                                    text_color=THEME["accent_h"], wraplength=380,
                                    justify="left")
        self.cur_lbl.pack(anchor="w", pady=(8, 0))

        # ── steps ──
        c = self._card(left, "Steps", "Chain operations — output of one feeds the next")
        sf = ctk.CTkFrame(c, fg_color="transparent")
        sf.pack(fill="x")
        self._op_map = {}
        labels = []
        for key, label in au.ops_table():
            labels.append(label)
            self._op_map[label] = key
        self.op_combo = modern_combo(sf, labels, width=240)
        if labels:
            self.op_combo.set(labels[0])
        self.op_combo.pack(side="left", fill="x", expand=True)
        ghost_btn(sf, "Add step", self.add_step, width=90).pack(side="left", padx=6)
        lw2 = ctk.CTkFrame(c, fg_color="transparent")
        lw2.pack(fill="x", pady=(8, 0))
        self.step_lb = tk.Listbox(lw2, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0, height=6)
        sc2 = ctk.CTkScrollbar(lw2, command=self.step_lb.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.step_lb.configure(yscrollcommand=sc2.set)
        self.step_lb.pack(side="left", fill="both", expand=True)
        sc2.pack(side="right", fill="y", padx=(8, 0))
        self.step_lb.bind("<Double-Button-1>", lambda e: self.edit_step())
        sr = ctk.CTkFrame(c, fg_color="transparent")
        sr.pack(fill="x", pady=(8, 0))
        ghost_btn(sr, "Edit params…", self.edit_step, width=110).pack(side="left")
        ghost_btn(sr, "Remove", self.remove_step, width=84).pack(side="left", padx=6)
        ghost_btn(sr, "↑", lambda: self.move_step(-1), width=44).pack(side="left")
        ghost_btn(sr, "↓", lambda: self.move_step(1), width=44).pack(side="left", padx=6)

        # ── run ──
        c = self._card(left, "Run", "")
        of = ctk.CTkFrame(c, fg_color="transparent")
        of.pack(fill="x")
        ctk.CTkLabel(of, text="Output folder", font=FONT_SM,
                     text_color=THEME["muted"]).pack(side="left", padx=(0, 8))
        self.auto_out_var = tk.StringVar(value="")
        accent_entry(of, textvariable=self.auto_out_var, height=30).pack(side="left", fill="x",
                                                                         expand=True)
        ghost_btn(of, "Browse", self._pick_out, width=80).pack(side="left", padx=6)
        self.same_src_var = tk.BooleanVar(value=False)
        dark_check(c, "Output next to source files (PDFSuite_Output subfolder)",
                   self.same_src_var).pack(anchor="w", pady=(6, 0))
        rrun = ctk.CTkFrame(c, fg_color="transparent")
        rrun.pack(fill="x", pady=(8, 0))
        primary_btn(rrun, "Run on files…", self.run_on_files, width=130, height=34).pack(side="left")
        ghost_btn(rrun, "Run on folder…", self.run_on_folder, width=130).pack(side="left", padx=8)
        self.log_box = ctk.CTkTextbox(c, corner_radius=10, fg_color="#0b0f1c",
            border_width=1, border_color=THEME["border"], text_color="#9ad0ff",
            font=("Consolas", 10), height=150)
        self.log_box.pack(fill="x", pady=(10, 0))
        self.log_box.configure(state="disabled")
        lr = ctk.CTkFrame(c, fg_color="transparent")
        lr.pack(fill="x", pady=(6, 0))
        ghost_btn(lr, "Open report", self.open_report, width=110).pack(side="left")
        ghost_btn(lr, "Clear log", self.clear_log, width=90).pack(side="right")

        # ── watch folders ──
        c = self._card(right, "Watch folders",
                       "Automatically runs the current recipe on new files")
        lw3 = ctk.CTkFrame(c, fg_color="transparent")
        lw3.pack(fill="x")
        self.watch_lb = tk.Listbox(lw3, bg=THEME["surface2"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#ffffff",
            font=FONT_SM, relief="flat", highlightthickness=0, bd=0,
            activestyle="none", selectborderwidth=0, height=4)
        sc3 = ctk.CTkScrollbar(lw3, command=self.watch_lb.yview, width=12,
            fg_color="transparent", button_color="#2a3247", button_hover_color="#3a4560")
        self.watch_lb.configure(yscrollcommand=sc3.set)
        self.watch_lb.pack(side="left", fill="both", expand=True)
        sc3.pack(side="right", fill="y", padx=(8, 0))
        wr = ctk.CTkFrame(c, fg_color="transparent")
        wr.pack(fill="x", pady=(8, 0))
        ghost_btn(wr, "Add watch…", self.add_watch, width=104).pack(side="left")
        ghost_btn(wr, "Start", self.start_watch, width=70).pack(side="left", padx=6)
        ghost_btn(wr, "Stop", self.stop_watch, width=70).pack(side="left")
        ghost_btn(wr, "Remove", self.remove_watch, width=84).pack(side="right")

        # ── scheduler ──
        c = self._card(right, "Scheduled tasks",
                       "Daily / weekly runs via Windows task scheduler + PDFSuiteCLI")
        self._r(c, "Schedule daily/weekly run…", self.schedule_task)
        self._r(c, "Delete scheduled task…", self.delete_task_ui)

        # ── mail merge ──
        c = self._card(right, "CSV mail merge",
                       "Fills PDF form fields and {{placeholders}} from a CSV")
        mm = ctk.CTkFrame(c, fg_color="transparent")
        mm.pack(fill="x")
        ctk.CTkLabel(mm, text="Template", font=FONT_SM, text_color=THEME["muted"],
                     width=80, anchor="w").pack(side="left")
        self.mm_tpl_var = tk.StringVar(value="")
        accent_entry(mm, textvariable=self.mm_tpl_var, height=30).pack(side="left", fill="x",
                                                                       expand=True)
        ghost_btn(mm, "…", lambda: self._pick_mm("tpl"), width=36).pack(side="left", padx=6)
        mm2 = ctk.CTkFrame(c, fg_color="transparent")
        mm2.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(mm2, text="CSV", font=FONT_SM, text_color=THEME["muted"],
                     width=80, anchor="w").pack(side="left")
        self.mm_csv_var = tk.StringVar(value="")
        accent_entry(mm2, textvariable=self.mm_csv_var, height=30).pack(side="left", fill="x",
                                                                        expand=True)
        ghost_btn(mm2, "…", lambda: self._pick_mm("csv"), width=36).pack(side="left", padx=6)
        mm3 = ctk.CTkFrame(c, fg_color="transparent")
        mm3.pack(fill="x", pady=(6, 0))
        ctk.CTkLabel(mm3, text="Output", font=FONT_SM, text_color=THEME["muted"],
                     width=80, anchor="w").pack(side="left")
        self.mm_out_var = tk.StringVar(value="")
        accent_entry(mm3, textvariable=self.mm_out_var, height=30).pack(side="left", fill="x",
                                                                        expand=True)
        ghost_btn(mm3, "…", lambda: self._pick_mm("out"), width=36).pack(side="left", padx=6)
        self.mm_note = ctk.CTkLabel(c, text="Use {{column}} or <<column>> placeholders "
                                            "in the template.",
                                    font=FONT_SM, text_color=THEME["muted"], wraplength=380,
                                    justify="left")
        self.mm_note.pack(anchor="w", pady=(6, 0))
        self._r(c, "Generate merged PDFs", self.mail_merge)

        # ── email ──
        c = self._card(right, "Email reports",
                       "Optionally email a report after each watched file (SMTP)")
        self.email_enabled = tk.BooleanVar(value=False)
        dark_check(c, "Send email after each watched file",
                   self.email_enabled).pack(anchor="w", pady=(0, 4))
        self.em_host_var = tk.StringVar(value="")
        self.em_port_var = tk.StringVar(value="587")
        self.em_user_var = tk.StringVar(value="")
        self.em_pass_var = tk.StringVar(value="")
        self.em_to_var = tk.StringVar(value="")
        for label, var, show in (("SMTP host", self.em_host_var, False),
                                 ("Port", self.em_port_var, False),
                                 ("Username", self.em_user_var, False),
                                 ("Password", self.em_pass_var, True),
                                 ("Send to", self.em_to_var, False)):
            row = ctk.CTkFrame(c, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, font=FONT_SM, text_color=THEME["muted"],
                         width=80, anchor="w").pack(side="left")
            e = accent_entry(row, textvariable=var, height=28)
            if show:
                e.configure(show="*")
            e.pack(side="left", fill="x", expand=True)
        self._r(c, "Save email settings", self.save_email)

        # ── CLI ──
        c = self._card(right, "Command line companion", "PDFSuiteCLI.exe does the same jobs")
        ex = 'PDFSuiteCLI.exe recipe -r "recipe.json" -d "C:\\Scans" -o "C:\\Out"'
        ctk.CTkLabel(c, text=ex, font=("Consolas", 10), text_color="#9ad0ff",
                     wraplength=380, justify="left").pack(anchor="w")
        ghost_btn(c, "Copy example command", self.copy_cli_example,
                  width=190).pack(anchor="w", pady=(8, 0))

    # ── helpers ──
    def _card(self, parent, title, sub=""):
        f = modern_card(parent)
        f.pack(fill="x", pady=(0, 12))
        c = ctk.CTkFrame(f, fg_color="transparent")
        c.pack(fill="x", padx=14, pady=14)
        ctk.CTkLabel(c, text=title, font=FONT_LARGE, text_color=THEME["fg"]).pack(anchor="w")
        if sub:
            ctk.CTkLabel(c, text=sub, font=FONT_SM, text_color=THEME["muted"],
                         wraplength=380, justify="left").pack(anchor="w", pady=(0, 4))
        return c

    def _r(self, parent, text, cmd):
        ghost_btn(parent, text, cmd).pack(fill="x", pady=3)

    def _poll_log(self):
        try:
            while True:
                msg = self._logq.get_nowait()
                self.log_box.configure(state="normal")
                self.log_box.insert("end", msg + "\n")
                self.log_box.see("end")
                self.log_box.configure(state="disabled")
        except queue.Empty:
            pass
        self.parent.after(350, self._poll_log)

    def log(self, msg):
        self._logq.put(str(msg))

    def clear_log(self):
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

    def _pick_out(self):
        d = filedialog.askdirectory(title="Default output folder")
        if d:
            self.auto_out_var.set(d)

    # ── recipe management ──
    def new_recipe(self):
        name = simpledialog.askstring("New recipe", "Recipe name:",
                                      initialvalue="My Recipe", parent=self.parent)
        if not name:
            return
        self.recipe = au.new_recipe(name.strip())
        self.recipe_file = None
        self._refresh_recipe_view()
        self.log("New recipe: %s" % name.strip())

    def load_recipe_dlg(self):
        p = filedialog.askopenfilename(title="Load recipe",
                                       filetypes=[("Recipe JSON", "*.json"),
                                                  ("All files", "*.*")])
        if not p:
            return
        try:
            self.recipe = au.load_recipe(p)
            self.recipe_file = p
            self.recipe_files[self.recipe.get("name", "recipe")] = p
            self._refresh_recipe_view()
            self._refresh_recipes_list()
            self.log("Loaded recipe: %s" % p)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def save_recipe_dlg(self):
        if not self.recipe:
            messagebox.showerror("Error", "Create or load a recipe first.")
            return
        p = filedialog.asksaveasfilename(title="Save recipe", defaultextension=".json",
            filetypes=[("Recipe JSON", "*.json")],
            initialfile=(self.recipe.get("name") or "recipe").replace(" ", "_") + ".json")
        if not p:
            return
        try:
            au.save_recipe(self.recipe, p)
            self.recipe_file = p
            self.recipe_files[self.recipe.get("name", "recipe")] = p
            self._refresh_recipes_list()
            self.log("Saved recipe: %s" % p)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def delete_recipe(self):
        s = self.recipe_lb.curselection()
        if not s:
            return
        name = self.recipe_lb.get(s[0])
        self.recipe_lb.delete(s[0])
        self.recipe_files.pop(name, None)
        self.log("Removed from list: %s" % name)

    def _refresh_recipes_list(self):
        self.recipe_lb.delete(0, "end")
        for name in sorted(self.recipe_files):
            self.recipe_lb.insert("end", name)

    def _on_recipe_select(self, e=None):
        s = self.recipe_lb.curselection()
        if not s:
            return
        name = self.recipe_lb.get(s[0])
        p = self.recipe_files.get(name)
        if p and os.path.exists(p):
            try:
                self.recipe = au.load_recipe(p)
                self.recipe_file = p
                self._refresh_recipe_view()
            except Exception as ex:
                messagebox.showerror("Error", str(ex))

    def _refresh_recipe_view(self):
        self.step_lb.delete(0, "end")
        if not self.recipe:
            self.cur_lbl.configure(text="No recipe loaded")
            return
        steps = self.recipe.get("steps", [])
        self.cur_lbl.configure(text="Recipe: %s  (%d step(s))%s" % (
            self.recipe.get("name", "?"), len(steps),
            "  ·  " + os.path.basename(self.recipe_file) if self.recipe_file else ""))
        for st in steps:
            spec = au.OPS.get(st.get("op"), {})
            params = st.get("params", {})
            psum = ", ".join("%s=%s" % (k, v) for k, v in list(params.items())[:3])
            self.step_lb.insert("end", "%s  [%s]" % (spec.get("label", st.get("op")), psum))

    def _step_sel(self):
        s = self.step_lb.curselection()
        return s[0] if s else None

    def add_step(self):
        if not self.recipe:
            self.recipe = au.new_recipe("Untitled Recipe")
        lab = self.op_combo.get()
        op = self._op_map.get(lab)
        if not op:
            return
        spec = au.OPS[op]
        params = {prm["key"]: prm.get("default") for prm in spec["params"]}
        self.recipe.setdefault("steps", []).append({"op": op, "params": params})
        self._refresh_recipe_view()

    def edit_step(self):
        i = self._step_sel()
        if i is None or not self.recipe:
            return
        st = self.recipe["steps"][i]
        spec = au.OPS.get(st.get("op"))
        if not spec:
            return
        fields = []
        for prm in spec["params"]:
            cur = st.get("params", {}).get(prm["key"], prm.get("default"))
            fields.append((prm["key"], prm["label"], prm["type"], cur, prm.get("options")))
        if not fields:
            messagebox.showinfo("Step", "This step has no parameters.")
            return
        dlg = SimpleFormDialog(self.parent, spec["label"], fields)
        if dlg.result is None:
            return
        st["params"] = dlg.result
        self._refresh_recipe_view()

    def remove_step(self):
        i = self._step_sel()
        if i is None or not self.recipe:
            return
        del self.recipe["steps"][i]
        self._refresh_recipe_view()

    def move_step(self, d):
        i = self._step_sel()
        if i is None or not self.recipe:
            return
        steps = self.recipe.get("steps", [])
        j = i + d
        if j < 0 or j >= len(steps):
            return
        steps[i], steps[j] = steps[j], steps[i]
        self._refresh_recipe_view()
        self.step_lb.selection_set(j)


    # ── batch runs ──
    def _outdir_for(self):
        if self.same_src_var.get():
            return None
        d = self.auto_out_var.get().strip()
        if not d:
            d = filedialog.askdirectory(title="Output folder")
            if not d:
                return ""
            self.auto_out_var.set(d)
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass
        return d

    def _check_recipe(self):
        if not self.recipe or not self.recipe.get("steps"):
            messagebox.showerror("Error", "Create a recipe with steps first.")
            return False
        return True

    def run_on_files(self):
        if not self._check_recipe():
            return
        files = filedialog.askopenfilenames(title="Select files",
            filetypes=[("PDF & images",
                        "*.pdf *.jpg *.jpeg *.png *.bmp *.webp *.tif *.tiff"),
                       ("All files", "*.*")])
        if not files:
            return
        self._do_batch(list(files))

    def run_on_folder(self):
        if not self._check_recipe():
            return
        d = filedialog.askdirectory(title="Select input folder")
        if not d:
            return
        exts = [".pdf"] + list(fi.IMG_EXTS)
        files = au.list_input_files(d, exts)
        if not files:
            messagebox.showinfo("Batch", "No PDF or image files found in that folder.")
            return
        self._do_batch(files)

    def _do_batch(self, files):
        same = bool(self.same_src_var.get())
        out = None
        if same:
            out = os.path.join(os.path.dirname(files[0]), "PDFSuite_Output")
            try:
                os.makedirs(out, exist_ok=True)
            except OSError:
                pass
        else:
            out = self._outdir_for()
            if not out:
                return
        name = self.recipe.get("name", "recipe")
        self.log("Batch start: %d file(s) -> %s" % (len(files), out))

        def work(pr):
            return au.batch_run(self.recipe, files, out, recipe_name=name,
                                progress=pr, log=self.log)

        def done(rows):
            try:
                rep = au.append_report(rows, os.path.join(out, "automation_report.csv"))
            except Exception as e:
                rep = "report failed: %s" % e
            ok = sum(1 for r in rows if r["status"] == "ok")
            self.log("Batch done: %d ok, %d failed" % (ok, len(rows) - ok))
            messagebox.showinfo("Batch finished",
                "%d of %d succeeded.\n\nReport:\n%s" % (ok, len(rows), rep))
            try:
                os.startfile(out)
            except Exception:
                pass

        self.app.run_bg(work, "Running recipe…", on_done=done)

    def open_report(self):
        d = self.auto_out_var.get().strip()
        rep = os.path.join(d, "automation_report.csv") if d else ""
        if rep and os.path.exists(rep):
            try:
                os.startfile(rep)
                return
            except Exception:
                pass
        messagebox.showinfo("Report", "No report found yet in the output folder.")

    # ── watch folders ──
    def add_watch(self):
        if not self._check_recipe():
            return
        folder = filedialog.askdirectory(title="Folder to watch")
        if not folder:
            return
        out = filedialog.askdirectory(title="Output folder")
        if not out:
            return
        dlg = SimpleFormDialog(self.parent, "Watch options",
            [("poll", "Check every (seconds)", "int", 5),
             ("move", "Move processed files to subfolders", "check", True),
             ("delete", "Delete source files after success", "check", False)])
        if dlg.result is None:
            return
        cfg = {}
        try:
            cfg = (self.app.settings or {}).get("email", {}) or {}
        except Exception:
            cfg = {}
        w = au.Watcher(folder, self.recipe, out,
                       exts=(".pdf",) + tuple(fi.IMG_EXTS),
                       poll=dlg.result["poll"], move_done=dlg.result["move"],
                       delete_src=dlg.result["delete"], log=self.log,
                       email_cfg=cfg, recipe_name=self.recipe.get("name", "recipe"))
        label = "%s  →  %s" % (folder, out)
        self.watches.append({"watch": w, "label": label})
        self.watch_lb.insert("end", "[stopped] " + label)
        self.log("Watch added: %s" % label)

    def _watch_targets(self):
        s = self.watch_lb.curselection()
        if s and 0 <= s[0] < len(self.watches):
            return [(s[0], self.watches[s[0]])]
        return list(enumerate(self.watches))

    def start_watch(self):
        if not self.watches:
            messagebox.showinfo("Watch", "Add a watch folder first.")
            return
        for i, item in self._watch_targets():
            w = item["watch"]
            if not w.is_running():
                w.start()
            self.watch_lb.delete(i)
            self.watch_lb.insert(i, "[running] " + item["label"])

    def stop_watch(self):
        for i, item in self._watch_targets():
            item["watch"].stop()
            self.watch_lb.delete(i)
            self.watch_lb.insert(i, "[stopped] " + item["label"])

    def remove_watch(self):
        for i, item in sorted(self._watch_targets(), key=lambda t: -t[0]):
            item["watch"].stop()
            self.watch_lb.delete(i)
            del self.watches[i]

    def stop_all(self):
        for item in self.watches:
            try:
                item["watch"].stop()
            except Exception:
                pass

    # ── scheduler ──
    def _cli_exe(self):
        if getattr(sys, "frozen", False):
            exe = os.path.join(os.path.dirname(sys.executable), "PDFSuiteCLI.exe")
            if os.path.exists(exe):
                return exe
        return None

    def schedule_task(self):
        if not self._check_recipe():
            return
        if not self.recipe_file:
            messagebox.showinfo("Schedule", "Save the recipe first (Save as…).")
            return
        folder = filedialog.askdirectory(title="Input folder for the scheduled run")
        if not folder:
            return
        out = filedialog.askdirectory(title="Output folder")
        if not out:
            return
        dlg = SimpleFormDialog(self.parent, "Schedule task",
            [("name", "Task name", "text",
              (self.recipe.get("name") or "Recipe") + " run"),
             ("time", "Time (HH:MM)", "text", "18:00"),
             ("when", "Frequency", "combo", "DAILY", ["DAILY", "WEEKLY"])])
        if dlg.result is None:
            return
        args = 'recipe -r "%s" -d "%s" -o "%s"' % (self.recipe_file, folder, out)
        cli = self._cli_exe()
        try:
            if cli:
                info = au.create_task(dlg.result["name"], cli, args,
                                      when=dlg.result["when"], time_str=dlg.result["time"])
            else:
                script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                      "pdf_cli.py")
                info = au.create_task(dlg.result["name"], sys.executable,
                                      '"%s" %s' % (script, args),
                                      when=dlg.result["when"], time_str=dlg.result["time"])
            self.log(info or "Task created")
            messagebox.showinfo("Scheduled", "Task created:\n%s" % dlg.result["name"])
        except Exception as e:
            messagebox.showerror("Scheduler error", str(e))

    def delete_task_ui(self):
        name = simpledialog.askstring("Delete task", "Task name (without folder):",
                                      parent=self.parent)
        if not name:
            return
        try:
            au.delete_task(name.strip())
            messagebox.showinfo("Scheduled", "Delete requested for:\n%s" % name.strip())
        except Exception as e:
            messagebox.showerror("Scheduler error", str(e))

    # ── mail merge ──
    def _pick_mm(self, which):
        if which == "tpl":
            p = filedialog.askopenfilename(title="Template PDF",
                                           filetypes=[("PDF", "*.pdf")])
            if p:
                self.mm_tpl_var.set(p)
                try:
                    if fp.file_has_forms(p):
                        self.mm_note.configure(
                            text="Template has fillable form fields — CSV column "
                                 "names are matched to the field names automatically.")
                    else:
                        self.mm_note.configure(
                            text="Use {{column}} or <<column>> placeholders in the template.")
                except Exception:
                    pass
        elif which == "csv":
            p = filedialog.askopenfilename(title="CSV file",
                                           filetypes=[("CSV", "*.csv"),
                                                      ("All files", "*.*")])
            if p:
                self.mm_csv_var.set(p)
        else:
            d = filedialog.askdirectory(title="Output folder")
            if d:
                self.mm_out_var.set(d)

    def mail_merge(self):
        tpl = self.mm_tpl_var.get().strip()
        csvp = self.mm_csv_var.get().strip()
        out = self.mm_out_var.get().strip()
        if not (tpl and csvp and out):
            messagebox.showerror("Error", "Select template, CSV and output folder.")
            return
        self.log("Mail merge start: %s" % os.path.basename(tpl))

        def done(paths):
            self.log("Mail merge done: %d PDF(s)" % len(paths or []))
            messagebox.showinfo("Mail merge", "Created %d PDF(s) in:\n%s"
                                % (len(paths or []), out))
            try:
                os.startfile(out)
            except Exception:
                pass

        self.app.run_bg(lambda pr: fp.mail_merge(tpl, csvp, out, progress=pr,
                                                 log=self.log),
                        "Mail merging…", on_done=done)

    # ── email settings ──
    def save_email(self):
        try:
            port = int(float(self.em_port_var.get().strip() or 587))
        except ValueError:
            port = 587
        cfg = {"enabled": bool(self.email_enabled.get()),
               "host": self.em_host_var.get().strip(),
               "port": port,
               "user": self.em_user_var.get().strip(),
               "password": self.em_pass_var.get(),
               "to": self.em_to_var.get().strip()}
        s = dict(self.app.settings or {})
        s["email"] = cfg
        self.app.settings = s
        save_settings(s)
        self.log("Email settings saved")
        messagebox.showinfo("Email", "Email settings saved.")

    # ── CLI ──
    def copy_cli_example(self):
        example = ('PDFSuiteCLI.exe recipe -r "%s" -d "C:\\Scans" -o "C:\\Out"'
                   % (self.recipe_file or "recipe.json"))
        try:
            self.parent.clipboard_clear()
            self.parent.clipboard_append(example)
            self.log("Copied: %s" % example)
        except Exception:
            messagebox.showinfo("Command line", example)


# ═══════════════════════ UPDATE DIALOG (v4.1) ═══════════════════════
class UpdateDialog(ctk.CTkToplevel):
    """Shows a new release, downloads the installer from GitHub and runs it."""

    def __init__(self, parent, app, release, latest):
        super().__init__(parent)
        self.app = app
        self.release = release or {}
        self.latest = latest
        self.asset = None
        for a in self.release.get("assets") or []:
            n = (a.get("name") or "").lower()
            if n.endswith(".exe") and "installer" in n:
                self.asset = a
                break
        if self.asset is None:
            for a in self.release.get("assets") or []:
                if (a.get("name") or "").lower().endswith(".exe"):
                    self.asset = a
                    break

        self.title("Update available")
        self.configure(fg_color=THEME["bg"])
        self.resizable(False, False)
        self.transient(parent)
        w, h = 560, 470
        try:
            px = parent.winfo_rootx() + max(0, (parent.winfo_width() - w) // 2)
            py = parent.winfo_rooty() + max(0, (parent.winfo_height() - h) // 3)
            self.geometry("%dx%d+%d+%d" % (w, h, px, py))
        except Exception:
            self.geometry("%dx%d" % (w, h))
        self.protocol("WM_DELETE_WINDOW", self.later)

        c = ctk.CTkFrame(self, fg_color="transparent")
        c.pack(fill="both", expand=True, padx=18, pady=16)
        ctk.CTkLabel(c, text="A new version is available", font=FONT_LARGE,
                     text_color=THEME["fg"]).pack(anchor="w")
        ctk.CTkLabel(c, text="v%s  →  v%s" % (APP_VERSION, latest),
                     font=FONT_BOLD, text_color=THEME["accent_h"]).pack(anchor="w",
                                                                        pady=(4, 8))
        notes = (self.release.get("body") or "No release notes.").strip()
        self.notes_box = ctk.CTkTextbox(c, corner_radius=10, fg_color=THEME["surface2"],
            border_width=1, border_color=THEME["border"], text_color=THEME["fg"],
            font=FONT_SM, height=185, wrap="word")
        self.notes_box.pack(fill="both", expand=True)
        self.notes_box.insert("1.0", notes)
        self.notes_box.configure(state="disabled")

        self.status = ctk.CTkLabel(c, text="", font=FONT_SM, text_color=THEME["muted"])
        self.status.pack(anchor="w", pady=(8, 0))
        self.progress = ctk.CTkProgressBar(c, height=10, corner_radius=5,
            fg_color=THEME["surface2"], progress_color=THEME["accent"])
        self.progress.set(0)

        btns = ctk.CTkFrame(c, fg_color="transparent")
        btns.pack(fill="x", pady=(12, 0))
        self.update_btn = primary_btn(btns, "Download & Install", self.start_update,
                                      width=170, height=36)
        self.update_btn.pack(side="left")
        ghost_btn(btns, "Open release page", self.open_page,
                  width=150).pack(side="left", padx=8)
        ghost_btn(btns, "Later", self.later, width=80).pack(side="right")
        row2 = ctk.CTkFrame(c, fg_color="transparent")
        row2.pack(fill="x", pady=(8, 0))
        self.skip_var = tk.BooleanVar(value=False)
        dark_check(row2, "Don't remind me about v%s" % latest,
                   self.skip_var).pack(side="left")

        try:
            self.lift()
            self.focus_force()
        except Exception:
            pass

    def _closed(self):
        try:
            self.app._update_dlg = None
        except Exception:
            pass

    def later(self):
        if self.skip_var.get():
            s = dict(self.app.settings or {})
            s["skip_version"] = self.latest
            self.app.settings = s
            save_settings(s)
        self._closed()
        self.destroy()

    def open_page(self):
        webbrowser.open(self.release.get("html_url") or RELEASES_PAGE)

    def start_update(self):
        if not self.asset:
            self.open_page()
            return
        url = self.asset.get("browser_download_url")
        name = self.asset.get("name") or "PDFSuitePro_Installer.exe"
        total = int(self.asset.get("size") or 0)
        dest = os.path.join(tempfile.gettempdir(), name)
        self.update_btn.configure(state="disabled", text="Downloading…")
        self.progress.pack(fill="x", pady=(4, 0))
        self.status.configure(text="Downloading v%s…" % self.latest)
        q = queue.Queue()

        def worker():
            try:
                req = urllib.request.Request(url, headers={
                    "User-Agent": "PDFSuitePro-%s" % APP_VERSION})
                got = 0
                with urllib.request.urlopen(req, timeout=30) as r, \
                        open(dest, "wb") as f:
                    while True:
                        chunk = r.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        got += len(chunk)
                        q.put(("p", got, total))
                q.put(("done", dest))
            except Exception as e:
                q.put(("err", str(e)))

        threading.Thread(target=worker, daemon=True).start()

        def poll():
            try:
                while True:
                    item = q.get_nowait()
                    if item[0] == "p":
                        got, tot = item[1], item[2]
                        if tot:
                            self.progress.set(min(1.0, float(got) / tot))
                            self.status.configure(
                                text="Downloading… %d%%" % int(100.0 * got / tot))
                        else:
                            self.status.configure(
                                text="Downloading… %.1f MB" % (got / 1048576.0))
                    elif item[0] == "done":
                        self.progress.set(1.0)
                        self.status.configure(text="Download complete")
                        self._install(item[1])
                        return
                    else:
                        self.update_btn.configure(state="normal",
                                                  text="Download & Install")
                        self.status.configure(text="Download failed: %s" % item[1])
                        return
            except queue.Empty:
                pass
            self.after(120, poll)

        self.after(120, poll)

    def _install(self, path):
        if not messagebox.askyesno("Ready to install",
                "PDF Suite Pro v%s has been downloaded.\n\n"
                "Run the setup now? The application will close so the files "
                "can be updated." % self.latest, parent=self):
            self.status.configure(text="Installer saved to: %s" % path)
            return
        try:
            subprocess.Popen([path])
        except Exception as e:
            messagebox.showerror("Update",
                "Could not start the installer:\n%s" % e, parent=self)
            return
        self._closed()
        self.destroy()
        self.app.root.after(800, self.app.root.destroy)


# ═══════════════════════ ENTRY ═══════════════════════
if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    try:
        root.iconbitmap(resource_path("app_icon.ico"))
    except Exception:
        pass
    app = PDFSuite(root)
    root.mainloop()
