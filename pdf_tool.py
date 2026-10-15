import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import os, json, tempfile, threading, queue
from pathlib import Path
from datetime import datetime
import sys
import fitz
import customtkinter as ctk

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
APP_VERSION = "3.0"
SETTINGS_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THUMB_W, THUMB_H = 130, 170
MAX_RECENT = 15

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
        self.tab_tools = self.tabview.add("Tools")

        self.merge_ui = MergeUI(self.tab_merge, self)
        self.split_ui = SplitUI(self.tab_split, self)
        self.tools_ui = ToolsUI(self.tab_tools, self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

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
        ctk.CTkLabel(tf, text="Merge  ·  Split  ·  Sign  ·  Compress — a modern PDF toolkit for Windows",
                     font=FONT_SM, text_color=THEME["muted"]).pack(anchor="w")

        chip2 = ctk.CTkFrame(inner, fg_color=THEME["surface2"], corner_radius=12,
                             border_width=1, border_color=THEME["border"])
        chip2.pack(side="right", padx=(8, 0))
        ctk.CTkLabel(chip2, text="★  30+ tools", font=FONT_SM,
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
        fm.add_command(label="Add Images...", command=lambda: self.tools_ui.add_images())
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
        self.root.destroy()

    def open_rating(self):
        RatingDialog(self.root)

    def show_about(self):
        messagebox.showinfo("About PDF Suite Pro",
            "PDF Suite Pro v" + APP_VERSION + "\n\nCreator: AYUSH GUPTA\n\n"
            "Merge | Split | Sign | Compress | Redact | Extract\n"
            "Password protect | Page numbers | Grayscale | Flatten\n"
            "And many more PDF tools.")


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
            lbl.bind("<Button-1>", lambda e, idx=i: self._toggle(idx))
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


# ═══════════════════════ TOOLS UI ═══════════════════════
class ToolsUI:
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


# ═══════════════════════ ENTRY ═══════════════════════
if __name__ == "__main__":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except: pass
    ctk.set_appearance_mode("dark")
    root = ctk.CTk()
    app = PDFSuite(root)
    root.mainloop()
