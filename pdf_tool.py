import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import os, json, tempfile, threading, queue
from pathlib import Path
from datetime import datetime
import sys
import fitz

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
SETTINGS_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THUMB_W, THUMB_H = 130, 170
MAX_RECENT = 15

# Modern enhanced theme with better contrast and modern colors
THEME = {
    "bg": "#0a0a1a", "fg": "#e8e8f0",
    "accent": "#7c5cff", "accent2": "#00e5d4",
    "frame": "#15152a", "entry": "#1f1f3d", "button": "#1f1f3d",
    "button_hover": "#2a2a55", "tab_bg": "#1f1f3d", "tab_fg": "#e8e8f0",
    "tab_sel": "#7c5cff", "notebook_bg": "#0a0a1a", "canvas_bg": "#15152a",
    "success": "#00e676", "warning": "#ff9800", "danger": "#ff5252",
    "selection": "#3d3d75", "hover": "#2a2a55",
    "border": "#3d3d75", "shadow": "#050510",
}
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SM = ("Segoe UI", 9)
FONT_LARGE = ("Segoe UI", 12, "bold")
FONT_TITLE = ("Segoe UI", 14, "bold")

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

        self.top = tk.Toplevel(parent)
        self.top.title("Rate & Review")
        self.top.geometry("420x340")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        self.top.configure(bg=THEME["bg"])

        f = ttk.Frame(self.top, padding=16)
        f.pack(fill="both", expand=True)

        ttk.Label(f, text="Rate PDF Suite Pro", font=("Segoe UI", 14, "bold")).pack(pady=6)
        ttk.Label(f, text="Tap a star to rate:", font=FONT).pack()

        sf = ttk.Frame(f)
        sf.pack(pady=8)
        for i in range(5):
            btn = tk.Button(sf, text="\u2606", font=("Segoe UI", 24),
                bg=THEME["bg"], fg=THEME["accent"], relief="flat",
                activebackground=THEME["bg"], activeforeground=THEME["accent2"],
                cursor="hand2",
                command=lambda v=i + 1: self.set_star(v))
            btn.pack(side="left", padx=3)
            self.star_btns.append(btn)

        self.rating_lbl = ttk.Label(f, text="", font=FONT_BOLD)
        self.rating_lbl.pack()

        ttk.Label(f, text="Leave a review (optional):", font=FONT).pack(anchor="w", pady=(8, 2))
        self.review_text = tk.Text(f, height=3, bg=THEME["entry"], fg=THEME["fg"],
            font=FONT, relief="flat", insertbackground=THEME["fg"])
        self.review_text.pack(fill="x")

        if self.data["submitted"]:
            self.set_star(self.data["rating"], animate=False)
            self.review_text.insert("1.0", self.data.get("review", ""))
            self.review_text.configure(state="disabled")

        bf = ttk.Frame(f); bf.pack(fill="x", pady=10)
        ttk.Button(bf, text="Submit", command=self.submit, style="Accent.TButton").pack(side="left", padx=6)
        ttk.Button(bf, text="Open GitHub Issues", command=self.open_github).pack(side="left", padx=6)
        ttk.Button(bf, text="Close", command=self.top.destroy).pack(side="right", padx=6)

    def set_star(self, v, animate=True):
        self.rating = v
        labels = {1: "Poor", 2: "Below Average", 3: "Average", 4: "Good", 5: "Excellent"}
        self.rating_lbl.config(text="%d / 5 - %s" % (v, labels.get(v, "")))
        for i, btn in enumerate(self.star_btns):
            btn.config(text="\u2605" if i < v else "\u2606",
                fg=THEME["accent"] if i < v else THEME["button_hover"])

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
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("380x100")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        f = ttk.Frame(self.top, padding=16)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=title, font=FONT_BOLD).pack(anchor="w")
        self.pb = ttk.Progressbar(f, maximum=maxval, mode="determinate")
        self.pb.pack(fill="x", pady=6)
        self.lbl = ttk.Label(f, text="0 / %d" % maxval, font=FONT_SM)
        self.lbl.pack()
        self.top.update()

    def step(self, val=None):
        if val is not None: self.pb["value"] = val
        else: self.pb.step()
        self.lbl.config(text="%d / %d" % (self.pb["value"], self.pb["maximum"]))
        self.top.update()
        for w in self.top.winfo_children():
            try: w.update()
            except: pass

    def close(self): self.top.destroy()


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
        self.root.title(APP_NAME + " - v2.3")
        self.root.geometry("1100x750")
        self.root.minsize(900, 600)
        self.root.configure(bg=THEME["bg"])

        self.settings = load_settings()
        self.recent_files = self.settings.get("recent_files", [])

        self._apply_theme()
        self._build_menu()
        
        # Header banner
        self._build_header()
        
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self.tab_merge = ttk.Frame(self.notebook)
        self.tab_split = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_merge, text="  📄 Merge  ")
        self.notebook.add(self.tab_split, text="  ✂️ Split & Edit  ")
        self.notebook.add(self.tab_tools, text="  🔧 Tools  ")

        self.merge_ui = MergeUI(self.tab_merge, self)
        self.split_ui = SplitUI(self.tab_split, self)
        self.tools_ui = ToolsUI(self.tab_tools, self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _build_header(self):
        """Build a beautiful header banner"""
        header = tk.Frame(self.root, bg=THEME["frame"], height=70)
        header.pack(fill="x", padx=12, pady=(12, 6))
        header.pack_propagate(False)
        
        title_frame = tk.Frame(header, bg=THEME["frame"])
        title_frame.pack(side="left", padx=20, pady=10)
        
        tk.Label(title_frame, text="PDF Suite Pro", font=("Segoe UI", 18, "bold"),
                bg=THEME["frame"], fg=THEME["accent"]).pack(anchor="w")
        tk.Label(title_frame, text="v2.3 - Modern PDF Tool for Windows", font=("Segoe UI", 9),
                bg=THEME["frame"], fg=THEME["accent2"]).pack(anchor="w")
        
        stats_frame = tk.Frame(header, bg=THEME["frame"])
        stats_frame.pack(side="right", padx=20, pady=10)
        tk.Label(stats_frame, text="✨ 30+ Tools", font=("Segoe UI", 10, "bold"),
                bg=THEME["frame"], fg=THEME["accent2"]).pack(anchor="e")
        tk.Label(stats_frame, text="Merge • Split • Sign • Compress", font=("Segoe UI", 8),
                bg=THEME["frame"], fg=THEME["fg"]).pack(anchor="e")

    def _apply_theme(self):
        c = THEME
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=c["bg"], foreground=c["fg"], font=FONT)
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"], font=FONT)
        style.configure("TNotebook", background=c["notebook_bg"])
        style.configure("TNotebook.Tab", background=c["tab_bg"], foreground=c["tab_fg"], padding=[18, 8], font=FONT_BOLD)
        style.map("TNotebook.Tab", background=[("selected", c["tab_sel"])], foreground=[("selected", "#0a0a1a")])
        style.configure("TButton", background=c["button"], foreground=c["fg"], bordercolor=c["accent"], focuscolor="none", font=FONT, padding=[8, 4])
        style.map("TButton", background=[("active", c["button_hover"])], foreground=[("active", c["fg"])])
        style.configure("TEntry", fieldbackground=c["entry"], foreground=c["fg"], insertcolor=c["fg"], bordercolor=c["border"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["accent"], bordercolor=c["border"])
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["accent2"], font=FONT_BOLD)
        style.configure("Vertical.TScrollbar", background=c["button"], troughcolor=c["bg"], bordercolor=c["border"])
        style.configure("Horizontal.TScrollbar", background=c["button"], troughcolor=c["bg"], bordercolor=c["border"])
        style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"], focuscolor="none")
        style.map("TCheckbutton", background=[("active", c["bg"])])
        # Configure custom styles for modern controls
        style.configure("Accent.TButton", background=c["accent"], foreground="#0a0a1a", font=FONT_BOLD, padding=[10, 6])
        style.map("Accent.TButton", background=[("active", c["accent2"])], foreground=[("active", "#0a0a1a")])
        style.configure("Danger.TButton", background=c["danger"], foreground="#fff", font=FONT_BOLD, padding=[10, 6])
        style.configure("Success.TButton", background=c["success"], foreground="#0a0a1a", font=FONT_BOLD, padding=[10, 6])
        style.configure("Title.TLabel", background=c["bg"], foreground=c["accent"], font=FONT_TITLE)
        style.configure("Header.TLabel", background=c["bg"], foreground=c["accent2"], font=FONT_LARGE)

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
            "PDF Suite Pro v2.1\n\nCreator: AYUSH GUPTA\n\n"
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
        f = ttk.Frame(self.parent, padding=8)
        f.pack(fill="both", expand=True)
        tb = ttk.Frame(f); tb.pack(fill="x", pady=4)
        
        # File management section
        file_f = ttk.LabelFrame(tb, text="Files", padding=4)
        file_f.pack(side="left", padx=4, fill="y")
        for t, c in [("+ Add PDFs", self.add_files), ("Remove", self.rem_sel),
                     ("Clear", self.clear_all), ("Duplicate", self.dup_sel)]:
            ttk.Button(file_f, text=t, command=c).pack(side="left", padx=2)
        
        # File reorder section
        reorder_f = ttk.LabelFrame(tb, text="Reorder Files", padding=4)
        reorder_f.pack(side="left", padx=4, fill="y")
        ttk.Button(reorder_f, text="↑ Up", command=self.move_file_up, width=8).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="↓ Down", command=self.move_file_down, width=8).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="⇡ Top", command=self.move_file_top, width=8).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="⇣ Bottom", command=self.move_file_bottom, width=8).pack(side="left", padx=2)
        
        ttk.Separator(tb, orient="vertical").pack(side="left", fill="y", padx=6)
        
        ttk.Label(tb, text="Page range:").pack(side="left", padx=(10, 2))
        self.rng_var = tk.StringVar(value="all")
        ttk.Entry(tb, textvariable=self.rng_var, width=14).pack(side="left", padx=2)
        ttk.Button(tb, text="Apply", command=self.apply_range).pack(side="left", padx=2)

        lf = ttk.Frame(f); lf.pack(fill="both", expand=True, pady=4)
        self.lb = ReorderListbox(lf, bg=THEME["entry"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#1e1e2e",
            font=FONT, relief="flat", highlightthickness=0)
        sc = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True); sc.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self.on_sel)
        self.lb.on_move = self._on_files_reordered
        self.info_lbl = ttk.Label(f, text="0 files", foreground="gray")
        self.info_lbl.pack(anchor="w")

        bf = ttk.Frame(f); bf.pack(fill="x", pady=4)
        ttk.Label(bf, text="Output:").pack(side="left", padx=2)
        self.out_var = tk.StringVar(value="merged.pdf")
        ttk.Entry(bf, textvariable=self.out_var, width=28).pack(side="left", padx=2)
        sb = ttk.Frame(bf); sb.pack(side="right")
        ttk.Label(sb, text="Password:").pack(side="left", padx=(10, 2))
        self.pw_e = ttk.Entry(sb, textvariable=self.var_pw, width=12, show="*")
        self.pw_e.pack(side="left", padx=2)
        ttk.Checkbutton(sb, text="Compress", variable=self.var_compress).pack(side="left", padx=6)
        ttk.Button(sb, text="  Merge!  ", command=self.merge).pack(side="left", padx=4)

        ef = ttk.LabelFrame(f, text="Advanced Merge", padding=6); ef.pack(fill="x", pady=4)
        ttk.Button(ef, text="Insert PDF at Page...", command=self.insert_at_page).pack(side="left", padx=4)
        ttk.Button(ef, text="Add Cover Page...", command=self.add_cover).pack(side="left", padx=4)
        self.alt_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(ef, text="Alternate (interleave all)", variable=self.alt_var).pack(side="left", padx=10)

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
        self.info_lbl.config(text="%d file(s)" % len(self.files))

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
        self._build()

    def _build(self):
        f = ttk.Frame(self.parent, padding=8); f.pack(fill="both", expand=True)
        tb = ttk.Frame(f); tb.pack(fill="x", pady=4)
        ttk.Button(tb, text="Open PDF", command=self.open_pdf).pack(side="left", padx=2)
        self.file_lbl = ttk.Label(tb, text="No file loaded", foreground="gray")
        self.file_lbl.pack(side="left", padx=10)
        self.pg_lbl = ttk.Label(tb, text="")
        self.pg_lbl.pack(side="left", padx=4)
        ttk.Label(tb, text="Password:").pack(side="left", padx=(10, 2))
        ttk.Entry(tb, textvariable=self.var_pw, width=14, show="*").pack(side="left", padx=2)
        ttk.Button(tb, text="Unlock", command=self.unlock).pack(side="left", padx=2)

        cf = ttk.Frame(f); cf.pack(fill="both", expand=True, pady=4)
        self.canvas = tk.Canvas(cf, bg=THEME["canvas_bg"], highlightthickness=0)
        vs = ttk.Scrollbar(cf, orient="vertical", command=self.canvas.yview)
        hs = ttk.Scrollbar(cf, orient="horizontal", command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        vs.pack(side="right", fill="y"); hs.pack(side="bottom", fill="x")
        self.tc = ttk.Frame(self.canvas)
        self.cw = self.canvas.create_window((0, 0), window=self.tc, anchor="nw")
        self.tc.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.cw, width=e.width))

        af = ttk.Frame(f); af.pack(fill="x", pady=4)
        
        # Page reorder section
        reorder_f = ttk.LabelFrame(af, text="Page Order", padding=4)
        reorder_f.pack(side="left", padx=4, fill="y")
        ttk.Button(reorder_f, text="↑ Move Up", command=self.move_up, width=12).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="↓ Move Down", command=self.move_down, width=12).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="↑ Top", command=self.move_top, width=10).pack(side="left", padx=2)
        ttk.Button(reorder_f, text="↓ Bottom", command=self.move_bottom, width=10).pack(side="left", padx=2)
        
        ttk.Separator(af, orient="vertical").pack(side="left", fill="y", padx=6)
        
        # Page transform section
        transform_f = ttk.LabelFrame(af, text="Transform", padding=4)
        transform_f.pack(side="left", padx=4, fill="y")
        for t, c in [("Rotate CW", self.rot_cw), ("Rotate CCW", self.rot_ccw),
                     ("Mirror", self.mirror_pages), ("Grayscale", self.to_grayscale)]:
            ttk.Button(transform_f, text=t, command=c).pack(side="left", padx=2)
        
        ttk.Separator(af, orient="vertical").pack(side="left", fill="y", padx=6)
        
        # Page edit section
        edit_f = ttk.LabelFrame(af, text="Edit Pages", padding=4)
        edit_f.pack(side="left", padx=4, fill="y")
        for t, c in [("Delete", self.del_sel), ("Restore All", self.restore),
                     ("Insert Blank", self.insert_blank), ("Duplicate", self.dup_pgs)]:
            ttk.Button(edit_f, text=t, command=c).pack(side="left", padx=2)
        
        ttk.Separator(af, orient="vertical").pack(side="left", fill="y", padx=6)
        
        # Undo/Redo section
        undo_f = ttk.LabelFrame(af, text="History", padding=4)
        undo_f.pack(side="left", padx=4, fill="y")
        self.undo_btn = ttk.Button(undo_f, text="↶ Undo", command=self.undo, state="disabled", width=10)
        self.undo_btn.pack(side="left", padx=2)
        self.redo_btn = ttk.Button(undo_f, text="↷ Redo", command=self.redo, state="disabled", width=10)
        self.redo_btn.pack(side="left", padx=2)

        bf = ttk.Frame(f); bf.pack(fill="x", pady=4)
        ttk.Label(bf, text="Extract:").pack(side="left", padx=2)
        self.ext_var = tk.StringVar()
        ttk.Entry(bf, textvariable=self.ext_var, width=20).pack(side="left", padx=2)
        ttk.Button(bf, text="Extract", command=self.extract_range).pack(side="left", padx=2)
        ttk.Button(bf, text="Split All", command=self.split_all).pack(side="left", padx=6)
        ttk.Button(bf, text="Bookmarks", command=self.split_bookmarks).pack(side="left", padx=2)
        ttk.Button(bf, text="Save As", command=self.save_as).pack(side="left", padx=6)
        ttk.Separator(bf, orient="vertical").pack(side="left", fill="y", padx=6)
        ttk.Checkbutton(bf, text="Compress", variable=self.var_compress).pack(side="left", padx=4)

    def open_pdf(self):
        p = filedialog.askopenfilename(title="Open PDF", filetypes=[("PDF", "*.pdf")])
        if p: self.load_pdf(p)

    def load_pdf(self, path):
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                self._clear_thumbs(); self.doc = doc; self.doc_path = path
                self.file_lbl.config(text=os.path.basename(path), foreground="orange")
                self.pg_lbl.config(text="(encrypted)"); self.app.add_recent(path); return
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
        self.file_lbl.config(text=os.path.basename(path), foreground=THEME["fg"])
        self.pg_lbl.config(text="%d page(s)" % len(doc))
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
        if not self.doc: return
        cols = max(1, self.canvas.winfo_width() // (THUMB_W + 32))
        rf = None; rc = 0
        for i in range(len(self.doc)):
            if rc % cols == 0:
                rf = ttk.Frame(self.tc); rf.pack(fill="x", pady=6)
            rc += 1
            f2 = tk.Frame(rf, bg=THEME["canvas_bg"], highlightthickness=2, highlightbackground=THEME["border"])
            f2.pack(side="left", padx=8, pady=4)
            pg = self.doc[i]
            mat = fitz.Matrix(THUMB_W / pg.rect.width, THUMB_H / pg.rect.height)
            pix = pg.get_pixmap(matrix=mat)
            tmp = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)
            tmp.write(pix.tobytes("ppm")); tmp.close()
            self._temp_files.append(tmp.name)
            photo = tk.PhotoImage(file=tmp.name)
            self.page_images.append(photo)
            sel = i in self._sel; hilite = i in self._search_highlights
            deleted = i in self.page_del
            if deleted:
                bg = "#5a1a1a"
                border = THEME["danger"]
            elif sel:
                bg = THEME["accent"]
                border = THEME["accent2"]
            elif hilite:
                bg = "#5a5a1a"
                border = "#f1c40f"
            else:
                bg = THEME["canvas_bg"]
                border = THEME["border"]
            f2.configure(highlightbackground=border, highlightcolor=border)
            lbl = tk.Label(f2, image=photo, relief="flat", bd=0, bg=bg)
            lbl.pack(padx=2, pady=2)
            lbl.bind("<Button-1>", lambda e, idx=i: self._toggle(idx))
            # Page label with status
            status = ""
            if deleted:
                status = " ✗ DELETED"
            elif sel:
                status = " ✓ SELECTED"
            elif hilite:
                status = " 🔍 FOUND"
            rot = self.page_rots.get(i, 0)
            if rot:
                status += f" ↻{rot}°"
            tk.Label(f2, text=f"Page {i + 1}{status}", font=FONT_SM,
                    bg=bg, fg=THEME["fg"]).pack(pady=(0, 4))

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
        top = tk.Toplevel(self.parent)
        top.title("Search Results")
        top.geometry("500x350")
        top.transient(self.parent)
        f = ttk.Frame(top, padding=8); f.pack(fill="both", expand=True)
        ttk.Label(f, text="%d result(s):" % len(results)).pack(anchor="w")
        txt = tk.Text(f, wrap="word", bg=THEME["entry"], fg=THEME["fg"], font=FONT)
        sc = ttk.Scrollbar(f, orient="vertical", command=txt.yview)
        txt.configure(yscrollcommand=sc.set)
        txt.pack(side="left", fill="both", expand=True); sc.pack(side="right", fill="y")
        txt.insert("1.0", "\n".join(results))
        txt.configure(state="disabled")
        ttk.Button(f, text="Close", command=top.destroy).pack(pady=4)

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

    def _accent_btn(self, parent, text, command):
        b = tk.Button(parent, text=text, command=command,
            bg=THEME["accent"], fg="#1e1e2e", font=FONT_BOLD,
            relief="flat", padx=16, pady=8, cursor="hand2",
            activebackground=THEME["accent2"], activeforeground="#1e1e2e")
        b.pack(pady=4, fill="x")
        return b

    def _build(self):
        main = ttk.Frame(self.parent, padding=10)
        main.pack(fill="both", expand=True)
        left = ttk.Frame(main); left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = ttk.Frame(main); right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ── Left ──
        sig = ttk.LabelFrame(left, text="Digital Signature", padding=8)
        sig.pack(fill="x", pady=4)
        ttk.Label(sig, text="Signer:", font=FONT_BOLD).pack(anchor="w")
        self.signer_var = tk.StringVar(value="AYUSH GUPTA")
        ttk.Entry(sig, textvariable=self.signer_var, font=("Segoe UI", 11, "bold"), width=30).pack(fill="x", pady=2)
        sf = ttk.Frame(sig); sf.pack(fill="x", pady=4)
        ttk.Label(sf, text="Position:").pack(side="left")
        self.sig_pos = ttk.Combobox(sf, values=["Bottom-Right", "Bottom-Left", "Top-Right", "Top-Left", "Center"], state="readonly", width=14)
        self.sig_pos.set("Bottom-Right"); self.sig_pos.pack(side="left", padx=6)
        ttk.Label(sf, text=" Page:").pack(side="left")
        self.sig_page = tk.StringVar(value="last")
        ttk.Entry(sf, textvariable=self.sig_page, width=5).pack(side="left", padx=2)
        ttk.Label(sf, text="(1 / last)").pack(side="left")
        self._accent_btn(sig, "Sign PDF", self.sign_pdf)

        imgc = ttk.LabelFrame(left, text="Image Compression", padding=8)
        imgc.pack(fill="x", pady=4)
        ttk.Button(imgc, text="Add Images", command=self.add_images).pack(anchor="w", pady=2)
        self.img_lbl = ttk.Label(imgc, text="0 images added", foreground="gray")
        self.img_lbl.pack(anchor="w")
        qf = ttk.Frame(imgc); qf.pack(fill="x", pady=4)
        ttk.Label(qf, text="Quality (1-100):").pack(side="left")
        self.img_q = tk.IntVar(value=60)
        ttk.Scale(qf, from_=1, to=100, variable=self.img_q, orient="horizontal", length=150).pack(side="left", padx=6)
        self.img_q_lbl = ttk.Label(qf, text="60")
        self.img_q_lbl.pack(side="left")
        self.img_q.trace("w", lambda *a: self.img_q_lbl.config(text=str(self.img_q.get())))
        ttk.Button(imgc, text="Compress Images", command=self.compress_images).pack(anchor="w", pady=2)

        pdfc = ttk.LabelFrame(left, text="PDF Compression", padding=8)
        pdfc.pack(fill="x", pady=4)
        ttk.Label(pdfc, text="Level:").pack(anchor="w")
        lvls = ["Low (garbage)", "Medium (deflate)", "High (deflate+images)", "Max (full optimize)"]
        self.pdf_comp_lvl = ttk.Combobox(pdfc, values=lvls, state="readonly", width=30)
        self.pdf_comp_lvl.set("Medium (deflate)"); self.pdf_comp_lvl.pack(anchor="w", pady=2)
        ttk.Button(pdfc, text="Compress PDF...", command=self.compress_pdf).pack(anchor="w", pady=2)

        # ── Right ──
        conv = ttk.LabelFrame(right, text="Convert & Extract", padding=8)
        conv.pack(fill="x", pady=4)
        ttk.Button(conv, text="Images to PDF...", command=self.images_to_pdf).pack(fill="x", pady=2)
        self._btn(conv, "Extract Text from PDF...", lambda: self._run_split("extract_text"))
        self._btn(conv, "Extract Images from PDF...", lambda: self._run_split("extract_images"))
        self._btn(conv, "Convert to Grayscale...", lambda: self._run_split("to_grayscale"))

        redact = ttk.LabelFrame(right, text="Security & Cleanup", padding=8)
        redact.pack(fill="x", pady=4)
        ttk.Button(redact, text="Redact Text...", command=self.redact_text).pack(fill="x", pady=2)
        ttk.Button(redact, text="Remove Metadata", command=self.remove_metadata).pack(fill="x", pady=2)
        ttk.Button(redact, text="Password Protect PDF...", command=self.password_protect).pack(fill="x", pady=2)
        ttk.Button(redact, text="Remove Password from PDF...", command=self.remove_password).pack(fill="x", pady=2)

        misc = ttk.LabelFrame(right, text="Miscellaneous", padding=8)
        misc.pack(fill="x", pady=4)
        ttk.Button(misc, text="Add Page Numbers", command=self.add_page_numbers).pack(fill="x", pady=2)
        ttk.Button(misc, text="Flatten PDF (annotations)", command=self.flatten_pdf).pack(fill="x", pady=2)
        self._btn(misc, "Clone Open PDF x2", lambda: self._run_split("dup_pgs"))
        ttk.Separator(misc, orient="horizontal").pack(fill="x", pady=4)
        tk.Button(misc, text="\u2605 Rate & Review", font=FONT_BOLD,
            bg=THEME["accent"], fg="#1e1e2e", relief="flat", cursor="hand2",
            command=self.open_rating).pack(fill="x", pady=2)

    def _btn(self, parent, text, cmd):
        ttk.Button(parent, text=text, command=cmd).pack(fill="x", pady=2)

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
        self.img_lbl.config(text="%d image(s) added" % len(self.image_paths))

    def compress_images(self):
        if not self.image_paths:
            messagebox.showerror("Error", "Add images first."); return
        q = self.img_q.get()
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
    root = tk.Tk()
    app = PDFSuite(root)
    root.mainloop()
