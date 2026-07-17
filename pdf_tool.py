import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog, colorchooser
import os, json, threading, queue, io, tempfile, re
from pathlib import Path
from datetime import datetime

import fitz

APP_NAME = "PDF Suite Pro"
SETTINGS_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THUMB_W, THUMB_H = 130, 170
MAX_RECENT = 15

THEME = {
    "bg": "#1e1e2e", "fg": "#cdd6f4", "select": "#45475a",
    "accent": "#89b4fa", "accent2": "#a6e3a1", "danger": "#f38ba8",
    "frame": "#313244", "entry": "#45475a", "button": "#45475a",
    "button_hover": "#585b70", "tab_bg": "#1e1e2e", "tab_fg": "#cdd6f4",
    "tab_sel": "#89b4fa", "notebook_bg": "#181825", "canvas_bg": "#313244",
}
FONT = ("Segoe UI", 10)
FONT_BOLD = ("Segoe UI", 10, "bold")
FONT_SM = ("Segoe UI", 9)
HEADER_FONT = ("Segoe UI", 12, "bold")


def load_settings():
    if SETTINGS_FILE.exists():
        try: return json.loads(SETTINGS_FILE.read_text())
        except: pass
    return {"recent_files": [], "theme": "dark"}

def save_settings(data):
    try: SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except: pass

# ─── Progress ───
class ProgressDlg:
    def __init__(self, parent, title, maxval):
        self.top = tk.Toplevel(parent)
        self.top.title(title)
        self.top.geometry("350x90")
        self.top.resizable(False, False)
        self.top.transient(parent)
        self.top.grab_set()
        f = ttk.Frame(self.top, padding=12)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text=title, font=FONT_BOLD).pack(anchor="w")
        self.pb = ttk.Progressbar(f, maximum=maxval, mode="determinate")
        self.pb.pack(fill="x", pady=8)
        self.lbl = ttk.Label(f, text="0 / %d" % maxval, font=FONT_SM)
        self.lbl.pack()
        self.top.update()

    def step(self, val=None):
        if val is not None: self.pb["value"] = val
        else: self.pb.step()
        self.lbl.config(text="%d / %d" % (self.pb["value"], self.pb["maximum"]))
        self.top.update()

    def close(self): self.top.destroy()


# ─── Reorder Listbox ───
class ReorderListbox(tk.Listbox):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.bind("<Button-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self._drag = {"index": None, "y": 0}

    def on_press(self, e):
        idx = self.nearest(e.y)
        if idx in self.curselection():
            self._drag = {"index": idx, "y": e.y}
        else:
            self._drag = {"index": None, "y": 0}
            self.selection_clear(0, "end")
            self.selection_set(idx)
            self.activate(idx)

    def on_drag(self, e):
        idx = self._drag["index"]
        if idx is None or abs(e.y - self._drag["y"]) < 20: return
        new = self.nearest(e.y)
        if new != idx:
            self.swap(idx, new)
            self._drag["index"] = new
            self._drag["y"] = e.y

    def on_release(self, e):
        self._drag = {"index": None, "y": 0}

    def swap(self, a, b):
        items = list(self.get(0, "end"))
        items[a], items[b] = items[b], items[a]
        self.delete(0, "end")
        for it in items: self.insert("end", it)
        self.selection_set(b)
        self.activate(b)


# ─── Text Capture for stdout in GUI ───
class TextRedirector:
    def __init__(self, widget): self.widget = widget
    def write(self, s):
        self.widget.insert("end", s)
        self.widget.see("end")
    def flush(self): pass


# ═══════════════════════ MAIN APP ═══════════════════════
class PDFSuite:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("960x720")
        self.root.minsize(800, 550)
        self.root.configure(bg=THEME["bg"])

        c = THEME
        self.settings = load_settings()
        self.recent_files = self.settings.get("recent_files", [])

        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=c["bg"], foreground=c["fg"], font=FONT)
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"], font=FONT)
        style.configure("TNotebook", background=c["notebook_bg"])
        style.configure("TNotebook.Tab", background=c["tab_bg"], foreground=c["tab_fg"], padding=[14, 6], font=FONT_BOLD)
        style.map("TNotebook.Tab", background=[("selected", c["tab_sel"])], foreground=[("selected", "#1e1e2e")])
        style.configure("TButton", background=c["button"], foreground=c["fg"], bordercolor=c["accent"], focuscolor="none", font=FONT)
        style.map("TButton", background=[("active", c["button_hover"])], foreground=[("active", c["fg"])])
        style.configure("TEntry", fieldbackground=c["entry"], foreground=c["fg"], insertcolor=c["fg"])
        style.configure("TLabelframe", background=c["bg"], foreground=c["fg"])
        style.configure("TLabelframe.Label", background=c["bg"], foreground=c["fg"], font=FONT_BOLD)
        style.configure("TNotebook", tabposition="nw")
        style.configure("Vertical.TScrollbar", background=c["button"], troughcolor=c["bg"])
        style.configure("Horizontal.TScrollbar", background=c["button"], troughcolor=c["bg"])
        style.configure("TCheckbutton", background=c["bg"], foreground=c["fg"])
        style.map("TCheckbutton", background=[("active", c["bg"])])
        style.configure("TRadiobutton", background=c["bg"], foreground=c["fg"])

        self._build_menu()
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=8, pady=8)

        self.tab_merge = ttk.Frame(self.notebook)
        self.tab_split = ttk.Frame(self.notebook)
        self.tab_tools = ttk.Frame(self.notebook)
        self.notebook.add(self.tab_merge, text="  Merge  ")
        self.notebook.add(self.tab_split, text="  Split  ")
        self.notebook.add(self.tab_tools, text="  Tools  ")

        self.merge_ui = MergeUI(self.tab_merge, self)
        self.split_ui = SplitUI(self.tab_split, self)
        self.tools_ui = ToolsUI(self.tab_tools, self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── Menu ──
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
        em.add_command(label="Duplicate Pages", command=lambda: self.split_ui.duplicate_pages())
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

    def show_about(self):
        messagebox.showinfo("About PDF Suite Pro",
            "PDF Suite Pro v2.0\n\n"
            "Creator: AYUSH GUPTA\n\n"
            "Features:\n"
            "- Merge PDFs (standard, alternate, insert at page)\n"
            "- Split PDFs (by count, even/odd, bookmarks, blank pages)\n"
            "- Sign PDF with digital signature\n"
            "- Image compression (JPG/PNG)\n"
            "- PDF compression & optimization\n"
            "- Rotate, delete, mirror, flip pages\n"
            "- Extract images, text from PDF\n"
            "- Redact content, remove metadata\n"
            "- Convert to grayscale\n"
            "- Insert blank pages, duplicate pages\n"
            "- Search, page goto, dark mode\n"
            "- Password protect / unlock PDFs\n"
            "- Compress & deflate\n"
            "- Drag-and-drop reorder\n"
            "- Page thumbnails\n"
            "- Recent files")


# ═══════════════════════ MERGE UI ═══════════════════════
class MergeUI:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.files = []
        self.var_pw = tk.StringVar()
        self.var_compress = tk.BooleanVar(value=True)
        self.var_alternate = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        f = ttk.Frame(self.parent, padding=8)
        f.pack(fill="both", expand=True)
        # Toolbar
        tb = ttk.Frame(f); tb.pack(fill="x", pady=4)
        for t, c in [("+ Add PDFs", self.add_files), (". Browse", self.browse_out),
                     ("Remove", self.rem_sel), ("Clear", self.clear_all)]:
            b = ttk.Button(tb, text=t, command=c)
            b.pack(side="left", padx=3)
        ttk.Label(tb, text="  Page range:").pack(side="left", padx=(20, 2))
        self.rng_var = tk.StringVar(value="all")
        ttk.Entry(tb, textvariable=self.rng_var, width=14).pack(side="left", padx=2)
        ttk.Button(tb, text="Apply", command=self.apply_range).pack(side="left", padx=2)
        ttk.Checkbutton(tb, text="Alternate", variable=self.var_alternate).pack(side="left", padx=10)

        # List
        lf = ttk.Frame(f); lf.pack(fill="both", expand=True, pady=4)
        self.lb = ReorderListbox(lf, bg=THEME["entry"], fg=THEME["fg"],
            selectbackground=THEME["accent"], selectforeground="#1e1e2e",
            font=FONT, relief="flat", highlightthickness=0)
        sc = ttk.Scrollbar(lf, orient="vertical", command=self.lb.yview)
        self.lb.configure(yscrollcommand=sc.set)
        self.lb.pack(side="left", fill="both", expand=True); sc.pack(side="right", fill="y")
        self.lb.bind("<<ListboxSelect>>", self.on_sel)
        self.info_lbl = ttk.Label(f, text="0 files", foreground="gray")
        self.info_lbl.pack(anchor="w")

        # Bottom
        bf = ttk.Frame(f); bf.pack(fill="x", pady=4)
        ttk.Label(bf, text="Output:").pack(side="left", padx=2)
        self.out_var = tk.StringVar(value="merged.pdf")
        self.out_e = ttk.Entry(bf, textvariable=self.out_var, width=28)
        self.out_e.pack(side="left", padx=2)

        sb = ttk.Frame(bf); sb.pack(side="right")
        ttk.Label(sb, text="Password:").pack(side="left", padx=(10, 2))
        ttk.Entry(sb, textvariable=self.var_pw, width=12, show="*").pack(side="left", padx=2)
        ttk.Checkbutton(sb, text="Compress", variable=self.var_compress).pack(side="left", padx=6)
        self.merge_btn = ttk.Button(sb, text="  Merge!  ", command=self.merge)
        self.merge_btn.pack(side="left", padx=4)

        # Extra merge options
        ef = ttk.LabelFrame(f, text="Advanced Merge", padding=6); ef.pack(fill="x", pady=4)
        ttk.Button(ef, text="Insert PDF at Page...", command=self.insert_at_page).pack(side="left", padx=4)
        ttk.Button(ef, text="Add Cover Page...", command=self.add_cover).pack(side="left", padx=4)
        ttk.Button(ef, text="Duplicate Selected x2", command=self.dup_sel).pack(side="left", padx=4)

    def add_files(self):
        ps = filedialog.askopenfilenames(title="Select PDFs", filetypes=[("PDF", "*.pdf")])
        for p in ps:
            if not any(f["path"] == p for f in self.files):
                self.files.append({"path": p, "pages": "all"})
                self.lb.insert("end", os.path.basename(p) + "  [all]")
                self.app.add_recent(p)
        self._upd_info()

    def browse_out(self):
        p = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=self.out_var.get())
        if p: self.out_var.set(p)

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

    def merge(self):
        if len(self.files) < 1:
            messagebox.showerror("Error", "Add at least 1 PDF file.")
            return
        out = self.out_var.get().strip() or "merged.pdf"
        if not out.endswith(".pdf"): out += ".pdf"
        if not os.path.dirname(out):
            out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile=out)
            if not out: return
        pw = self.var_pw.get(); comp = self.var_compress.get()
        alt = self.var_alternate.get()
        try:
            writer = fitz.open()
            progress = ProgressDlg(self.parent, "Merging...", len(self.files))
            for idx, f in enumerate(self.files):
                src = fitz.open(f["path"])
                pgs = f["pages"].strip()
                if alt:
                    # Alternate merge: interleave pages from each file
                    for i in range(max(len(src), len(self.files))):
                        if i < len(src):
                            writer.insert_pdf(src, from_page=i, to_page=i)
                elif not pgs or pgs == "all":
                    writer.insert_pdf(src)
                else:
                    for p in self._prs(pgs, len(src)):
                        writer.insert_pdf(src, from_page=p - 1, to_page=p - 1)
                src.close()
                progress.step(idx + 1)
            writer.save(out, encryption=fitz.PDF_ENCRYPT_AES_256 if pw else 0,
                user_pw=pw or None, owner_pw=pw or None,
                garbage=4 if comp else 1, deflate=comp)
            writer.close()
            progress.close()
            messagebox.showinfo("Success", "Merged %d PDF(s) into:\n%s" % (len(self.files), out))
        except Exception as e:
            messagebox.showerror("Error", "Merge failed:\n%s" % e)

    def insert_at_page(self):
        if not self.files:
            messagebox.showerror("Error", "Add files to merge list first.")
            return
        path = filedialog.askopenfilename(title="Select PDF to insert", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pg = simpledialog.askinteger("Insert At", "Insert after page number (in merged output):", minvalue=0, initialvalue=1)
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

    def dup_sel(self):
        s = self.lb.curselection()
        for i in reversed(s):
            f = self.files[i]
            self.files.insert(i + 1, dict(f))
            self.lb.insert(i + 1, os.path.basename(f["path"]) + "  [%s]" % f["pages"])

    def _prs(self, t, total):
        r = set()
        for p in t.replace(" ", "").split(","):
            if not p: continue
            if "-" in p:
                a, b = p.split("-", 1)
                r.update(range(int(a), int(b) + 1))
            else: r.add(int(p))
        return sorted(x for x in r if 1 <= x <= total)


# ═══════════════════════ SPLIT UI ═══════════════════════
class SplitUI:
    def __init__(self, parent, app):
        self.parent = parent; self.app = app
        self.doc = None; self.doc_path = None
        self.page_images = []; self.page_rots = {}; self.page_del = set()
        self.var_pw = tk.StringVar()
        self.var_compress = tk.BooleanVar(value=True)
        self._build()

    def _build(self):
        f = ttk.Frame(self.parent, padding=8); f.pack(fill="both", expand=True)
        # Toolbar
        tb = ttk.Frame(f); tb.pack(fill="x", pady=4)
        ttk.Button(tb, text="Open PDF", command=self.open_pdf).pack(side="left", padx=2)
        self.file_lbl = ttk.Label(tb, text="No file loaded", foreground="gray")
        self.file_lbl.pack(side="left", padx=10)
        self.pg_lbl = ttk.Label(tb, text="")
        self.pg_lbl.pack(side="left", padx=4)
        ttk.Label(tb, text="Password:").pack(side="left", padx=(10, 2))
        ttk.Entry(tb, textvariable=self.var_pw, width=14, show="*").pack(side="left", padx=2)
        ttk.Button(tb, text="Unlock", command=self.unlock).pack(side="left", padx=2)

        # Thumbnail canvas
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

        # Page actions
        af = ttk.Frame(f); af.pack(fill="x", pady=4)
        for t, c in [("Rotate CW", self.rot_cw), ("Rotate CCW", self.rot_ccw),
                     ("Delete", self.del_sel), ("Restore All", self.restore),
                     ("Insert Blank", self.insert_blank), ("Duplicate", self.dup_pgs)]:
            ttk.Button(af, text=t, command=c).pack(side="left", padx=2)

        # Bottom
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

    # ── load ──
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
        if self.doc.authenticate(self.var_pw.get()):
            self._set_doc(self.doc, self.doc_path)
        else:
            messagebox.showerror("Error", "Incorrect password")

    def _set_doc(self, doc, path):
        self.doc = doc; self.doc_path = path; self.page_rots.clear(); self.page_del.clear()
        self.file_lbl.config(text=os.path.basename(path), foreground=THEME["fg"])
        self.pg_lbl.config(text="%d page(s)" % len(doc))
        self._render_thumbs()

    # ── thumbs ──
    def _clear_thumbs(self):
        for w in self.tc.winfo_children(): w.destroy()
        self.page_images.clear()

    def _render_thumbs(self):
        self._clear_thumbs()
        if not self.doc: return
        cols = max(1, self.canvas.winfo_width() // (THUMB_W + 24))
        rf = None; rc = 0
        for i in range(len(self.doc)):
            if rc % cols == 0:
                rf = ttk.Frame(self.tc); rf.pack(fill="x", pady=4)
            rc += 1
            f2 = ttk.Frame(rf); f2.pack(side="left", padx=8)
            pg = self.doc[i]
            mat = fitz.Matrix(THUMB_W / pg.rect.width, THUMB_H / pg.rect.height)
            pix = pg.get_pixmap(matrix=mat)
            tmp = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)
            tmp.write(pix.tobytes("ppm")); tmp.close()
            photo = tk.PhotoImage(file=tmp.name)
            os.unlink(tmp.name)
            self.page_images.append(photo)
            lbl = tk.Label(f2, image=photo, relief="solid", bd=1, bg=THEME["canvas_bg"])
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, idx=i: self._toggle(idx))
            num = self._pg_label(i)
            ttk.Label(f2, text=num, font=FONT_SM).pack()

    def _pg_label(self, i):
        parts = ["Page %d" % (i + 1)]
        if i in self.page_del: parts.append("[DEL]")
        rot = self.page_rots.get(i, 0)
        if rot: parts.append("%d°" % rot)
        return " ".join(parts)

    def _toggle(self, idx):
        if not hasattr(self, "_sel"): self._sel = set()
        if idx in self._sel: self._sel.discard(idx)
        else: self._sel.add(idx)

    def _get_sel(self):
        if not hasattr(self, "_sel"): self._sel = set()
        return self._sel

    # ── actions ──
    def rot_cw(self):
        for i in self._get_sel():
            self.page_rots[i] = (self.page_rots.get(i, 0) + 90) % 360
        self._sel.clear(); self._render_thumbs()

    def rot_ccw(self):
        for i in self._get_sel():
            self.page_rots[i] = (self.page_rots.get(i, 0) - 90) % 360
        self._sel.clear(); self._render_thumbs()

    def del_sel(self):
        self.page_del.update(self._get_sel())
        self._sel.clear(); self._render_thumbs()

    def restore(self):
        self.page_rots.clear(); self.page_del.clear(); self._sel.clear(); self._render_thumbs()

    def insert_blank(self):
        if not self.doc: return
        pos = simpledialog.askinteger("Insert Blank", "Insert after page number (0 = beginning):", minvalue=0, maxvalue=len(self.doc), initialvalue=1)
        if pos is None: return
        cnt = simpledialog.askinteger("Insert Blank", "How many blank pages?", minvalue=1, maxvalue=100, initialvalue=1)
        if cnt is None: return
        new = fitz.open()
        total = len(self.doc)
        for i in range(total):
            if i == pos:
                for _ in range(cnt):
                    new.new_page(width=self.doc[0].rect.width, height=self.doc[0].rect.height)
            if i not in self.page_del:
                new.insert_pdf(self.doc, from_page=i, to_page=i)
        if pos == total:
            for _ in range(cnt):
                new.new_page(width=self.doc[0].rect.width, height=self.doc[0].rect.height)
        self.doc.close(); self._set_doc(new, self.doc_path)

    def dup_pgs(self):
        idxs = sorted(self._get_sel())
        if not idxs: return
        new = fitz.open()
        total = len(self.doc)
        for i in range(total):
            if i not in self.page_del:
                new.insert_pdf(self.doc, from_page=i, to_page=i)
                if i in idxs:
                    new.insert_pdf(self.doc, from_page=i, to_page=i)
        self.doc.close(); self._set_doc(new, self.doc_path)

    def mirror_pages(self):
        self._apply_transform(lambda p: p.set_rotation(p.rotation or 0) or p.add_transform(fitz.Matrix(-1, 1, 0, 0, p.rect.width, 0)))

    def to_grayscale(self):
        if not self.doc: return
        for i in range(len(self.doc)):
            if i in self.page_del: continue
            pix = self.doc[i].get_pixmap(colorspace=fitz.csGRAY)
            self.doc[i].set_pixmap(pix)
        self._render_thumbs()
        messagebox.showinfo("Done", "Converted visible pages to grayscale.")

    def _apply_transform(self, fn):
        if not self.doc: return
        for i in self._get_sel():
            if i in self.page_del: continue
            fn(self.doc[i])
        self.page_rots.clear(); self._sel.clear(); self._render_thumbs()

    # ── extract ──
    def extract_range(self):
        if not self.doc: return
        t = self.ext_var.get().strip()
        if not t: messagebox.showerror("Error", "Enter page range (e.g. 1,3,5-7)"); return
        try:
            pgs = self._prs(t, len(self.doc))
        except Exception as e:
            messagebox.showerror("Error", str(e)); return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="extracted.pdf")
        if not out: return
        try:
            nd = fitz.open()
            for p in pgs: nd.insert_pdf(self.doc, from_page=p - 1, to_page=p - 1)
            self._sav(nd, out); nd.close()
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
                nd.save(os.path.join(d, ch["title"] + ".pdf"), garbage=1); nd.close()
            messagebox.showinfo("Success", "Split %d chapters into:\n%s" % (len(chs), d))
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
                    nd.save(os.path.join(d, "part_%02d.pdf" % fn), garbage=1); nd.close()
                    fn += 1; cnt += 1
            messagebox.showinfo("Success", "Split into %d files in:\n%s" % (cnt, d))
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
                    nd.save(os.path.join(d, "%s_pages.pdf" % name), garbage=1); nd.close()
            messagebox.showinfo("Success", "Even/odd split saved to:\n%s" % d)
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
                    xref = img[0]
                    pix = fitz.Pixmap(self.doc, xref)
                    if pix.n > 4: pix = fitz.Pixmap(fitz.csRGB, pix)
                    pix.save(os.path.join(d, "img_p%02d_%04d.png" % (pgnum + 1, cnt)))
                    cnt += 1
            messagebox.showinfo("Success", "Extracted %d images to:\n%s" % (cnt, d))
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

    def search_pdf(self):
        if not self.doc: return
        q = simpledialog.askstring("Search", "Search text:")
        if not q: return
        results = []
        for i in range(len(self.doc)):
            if i in self.page_del: continue
            insts = self.doc[i].search_for(q)
            for r in insts:
                results.append("Page %d: %s" % (i + 1, r))
        if results:
            messagebox.showinfo("Search Results", "\n".join(results[:50]))
        else:
            messagebox.showinfo("Search", "No results found.")

    def goto_page(self):
        if not self.doc: return
        n = simpledialog.askinteger("Go to Page", "Page number (1-%d):" % len(self.doc), minvalue=1, maxvalue=len(self.doc), initialvalue=1)
        if n:
            messagebox.showinfo("Go to Page", "Page %d selected.\nUse thumbnails to view it." % n)

    def save_as(self):
        if not self.doc: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="output.pdf")
        if not out: return
        try:
            nd = fitz.open()
            total = len(self.doc)
            for i in range(total):
                if i in self.page_del: continue
                nd.insert_pdf(self.doc, from_page=i, to_page=i)
                r = self.page_rots.get(i, 0)
                if r and len(nd): nd[-1].set_rotation(r)
            self._sav(nd, out); nd.close()
            messagebox.showinfo("Success", "Saved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", "Save failed:\n%s" % e)

    def _sav(self, doc, path):
        doc.save(path, garbage=4 if self.var_compress.get() else 1, deflate=self.var_compress.get())

    def _prs(self, t, total):
        r = set()
        for p in t.replace(" ", "").split(","):
            if not p: continue
            if "-" in p:
                a, b = p.split("-", 1)
                s, e = int(a), int(b)
                if s < 1 or e > total: raise ValueError("Range out of bounds")
                r.update(range(s, e + 1))
            else:
                v = int(p)
                if v < 1 or v > total: raise ValueError("Page out of bounds")
                r.add(v)
        return sorted(r)


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
        # Two-column layout
        main = ttk.Frame(self.parent, padding=10)
        main.pack(fill="both", expand=True)

        left = ttk.Frame(main); left.pack(side="left", fill="both", expand=True, padx=(0, 6))
        right = ttk.Frame(main); right.pack(side="right", fill="both", expand=True, padx=(6, 0))

        # ── Left Column ──
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
        self.pdf_comp_lvl = ttk.Combobox(pdfc, values=["Low (garbage)", "Medium (deflate)", "High (deflate+images)", "Max (full optimize)"], state="readonly", width=30)
        self.pdf_comp_lvl.set("Medium (deflate)"); self.pdf_comp_lvl.pack(anchor="w", pady=2)
        ttk.Button(pdfc, text="Compress PDF...", command=self.compress_pdf).pack(anchor="w", pady=2)

        # ── Right Column ──
        conv = ttk.LabelFrame(right, text="Convert & Extract", padding=8)
        conv.pack(fill="x", pady=4)
        ttk.Button(conv, text="Images to PDF...", command=self.images_to_pdf).pack(fill="x", pady=2)
        ttk.Button(conv, text="Extract Text from PDF...", command=lambda: self._run_on_split("extract_text")).pack(fill="x", pady=2)
        ttk.Button(conv, text="Extract Images from PDF...", command=lambda: self._run_on_split("extract_images")).pack(fill="x", pady=2)
        ttk.Button(conv, text="Convert PDF to Grayscale...", command=lambda: self._run_on_split("to_grayscale")).pack(fill="x", pady=2)

        redact = ttk.LabelFrame(right, text="Security & Cleanup", padding=8)
        redact.pack(fill="x", pady=4)
        ttk.Button(redact, text="Redact Text...", command=self.redact_text).pack(fill="x", pady=2)
        ttk.Button(redact, text="Remove Metadata", command=self.remove_metadata).pack(fill="x", pady=2)
        ttk.Button(redact, text="Password Protect PDF...", command=self.password_protect).pack(fill="x", pady=2)
        ttk.Button(redact, text="Remove Password from PDF...", command=self.remove_password).pack(fill="x", pady=2)

        misc = ttk.LabelFrame(right, text="Miscellaneous", padding=8)
        misc.pack(fill="x", pady=4)
        ttk.Button(misc, text="Clone Open PDF x2", command=lambda: self._run_on_split("dup_pgs_all")).pack(fill="x", pady=2)
        ttk.Button(misc, text="Add Page Numbers", command=self.add_page_numbers).pack(fill="x", pady=2)
        ttk.Button(misc, text="Flatten PDF (merge layers)", command=self.flatten_pdf).pack(fill="x", pady=2)

    def _run_on_split(self, action):
        su = self.app.split_ui
        if not su.doc:
            messagebox.showerror("Error", "Open a PDF in the Split tab first.")
            return
        getattr(su, action)()

    # ── Sign PDF ──
    def sign_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF to sign", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="signed.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            signer = self.signer_var.get() or "AYUSH GUPTA"
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

            # Draw signature box with styled text
            shape = pg.new_shape()
            shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
            shape.finish(color=(0.1, 0.3, 0.6), fill=(0.95, 0.95, 1), width=1.5)
            shape.insert_text(
                fitz.Point(x0 + 12, y0 + 28),
                "Digitally Signed",
                fontsize=10, color=(0.3, 0.3, 0.3),
            )
            shape.insert_text(
                fitz.Point(x0 + 12, y0 + 48),
                signer,
                fontsize=14, color=(0.1, 0.3, 0.6),
            )
            shape.insert_text(
                fitz.Point(x0 + 12, y0 + 64),
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                fontsize=8, color=(0.5, 0.5, 0.5),
            )
            shape.commit()

            doc.save(out, garbage=4, deflate=True)
            doc.close()
            messagebox.showinfo("Success", "PDF signed by %s\nSaved to:\n%s" % (signer, out))
        except Exception as e:
            messagebox.showerror("Error", "Sign failed:\n%s" % e)

    # ── Image Compression ──
    def add_images(self):
        ps = filedialog.askopenfilenames(title="Select images", filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp")])
        self.image_paths.extend(ps)
        self.img_lbl.config(text="%d image(s) added" % len(self.image_paths))

    def compress_images(self):
        if not self.image_paths:
            messagebox.showerror("Error", "Add images first.")
            return
        q = self.img_q.get()
        d = filedialog.askdirectory(title="Output folder for compressed images")
        if not d: return
        try:
            from PIL import Image as PILImg
        except ImportError:
            messagebox.showerror("Error", "Pillow required: pip install Pillow")
            return
        try:
            for path in self.image_paths:
                img = PILImg.open(path)
                name = os.path.splitext(os.path.basename(path))[0] + "_compressed.jpg"
                out = os.path.join(d, name)
                if img.mode in ("RGBA", "P"): img = img.convert("RGB")
                img.save(out, "JPEG", quality=q, optimize=True)
            messagebox.showinfo("Success", "Compressed %d images to:\n%s" % (len(self.image_paths), d))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Images to PDF ──
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
            messagebox.showinfo("Success", "Created PDF with %d images:\n%s" % (len(ps), out))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── PDF Compression ──
    def compress_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF to compress", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="compressed.pdf")
        if not out: return
        lvl = self.pdf_comp_lvl.get()
        try:
            doc = fitz.open(path)
            opts = {"garbage": 1, "deflate": False}
            if "Low" in lvl: opts = {"garbage": 4}
            elif "Medium" in lvl: opts = {"garbage": 4, "deflate": True}
            elif "High" in lvl: opts = {"garbage": 4, "deflate": True}
            elif "Max" in lvl: opts = {"garbage": 4, "deflate": True, "linear": True}

            # For High/Max, also downsample images
            if "High" in lvl or "Max" in lvl:
                for pgnum in range(len(doc)):
                    for img in doc[pgnum].get_images():
                        xref = img[0]
                        pix = fitz.Pixmap(doc, xref)
                        if pix.width > 1500:
                            pix.set_resolution(pix.resolution[0], pix.resolution[1])
                            doc[pgnum].replace_image(xref, pix)

            doc.save(out, **opts)
            orig = os.path.getsize(path)
            comp = os.path.getsize(out)
            pct = (1 - comp / orig) * 100 if orig else 0
            doc.close()
            messagebox.showinfo("Success",
                "Compressed from %.1f MB to %.1f MB (%.0f%% reduction)\nSaved to:\n%s" % (orig / 1e6, comp / 1e6, pct, out))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Redact ──
    def redact_text(self):
        path = filedialog.askopenfilename(title="Select PDF to redact", filetypes=[("PDF", "*.pdf")])
        if not path: return
        txt = simpledialog.askstring("Redact Text", "Text to redact (case-sensitive):")
        if not txt: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="redacted.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            for pgnum in range(len(doc)):
                pg = doc[pgnum]
                insts = pg.search_for(txt)
                for r in insts:
                    pg.add_redact_annot(r)
                    pg.apply_redactions()
            doc.save(out, garbage=4, deflate=True); doc.close()
            messagebox.showinfo("Success", "Redacted text '%s'\nSaved to:\n%s" % (txt, out))
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Remove Metadata ──
    def remove_metadata(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="cleaned.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            doc.set_metadata({})
            doc.save(out, garbage=4, deflate=True); doc.close()
            messagebox.showinfo("Success", "Metadata removed.\nSaved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Password Protect ──
    def password_protect(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pw = simpledialog.askstring("Password", "Enter password to encrypt:", show="*")
        if not pw: return
        pw2 = simpledialog.askstring("Password", "Confirm password:", show="*")
        if pw != pw2: messagebox.showerror("Error", "Passwords don't match"); return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="protected.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            doc.save(out, encryption=fitz.PDF_ENCRYPT_AES_256, user_pw=pw, owner_pw=pw, garbage=4, deflate=True)
            doc.close()
            messagebox.showinfo("Success", "PDF encrypted.\nSaved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Remove Password ──
    def remove_password(self):
        path = filedialog.askopenfilename(title="Select encrypted PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        pw = simpledialog.askstring("Password", "Enter current password:", show="*")
        if not pw: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="decrypted.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                if not doc.authenticate(pw):
                    messagebox.showerror("Error", "Incorrect password"); return
            doc.save(out, garbage=4, deflate=True)
            doc.close()
            messagebox.showinfo("Success", "Password removed.\nSaved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Add Page Numbers ──
    def add_page_numbers(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="numbered.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            for i in range(len(doc)):
                pg = doc[i]
                r = pg.rect
                shape = pg.new_shape()
                shape.insert_text(fitz.Point(r.width / 2 - 15, r.height - 20),
                    "- %d -" % (i + 1), fontsize=10, color=(0.4, 0.4, 0.4))
                shape.commit()
            doc.save(out, garbage=4, deflate=True); doc.close()
            messagebox.showinfo("Success", "Page numbers added.\nSaved to:\n%s" % out)
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ── Flatten PDF ──
    def flatten_pdf(self):
        path = filedialog.askopenfilename(title="Select PDF", filetypes=[("PDF", "*.pdf")])
        if not path: return
        out = filedialog.asksaveasfilename(defaultextension=".pdf", filetypes=[("PDF", "*.pdf")], initialfile="flattened.pdf")
        if not out: return
        try:
            doc = fitz.open(path)
            nd = fitz.open()
            for i in range(len(doc)):
                nd.insert_pdf(doc, from_page=i, to_page=i)
            nd.save(out, garbage=4, deflate=True); nd.close(); doc.close()
            messagebox.showinfo("Success", "PDF flattened.\nSaved to:\n%s" % out)
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
