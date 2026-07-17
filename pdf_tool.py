import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import os, json, threading, queue, io
from pathlib import Path

import fitz
import tempfile

APP_NAME = "PDFMerger"
SETTINGS_DIR = Path(os.environ.get("APPDATA", ".")) / APP_NAME
SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
SETTINGS_FILE = SETTINGS_DIR / "settings.json"
THUMB_W, THUMB_H = 130, 170
MAX_RECENT = 10

THEMES = {
    "light": {
        "bg": "#f0f0f0", "fg": "#000000", "select": "#0078d7",
        "frame": "#ffffff", "entry": "#ffffff", "button": "#e1e1e1",
        "tab_bg": "#f0f0f0", "tab_fg": "#000000",
        "notebook_bg": "#f0f0f0", "canvas_bg": "#ffffff",
        "listbox_bg": "#ffffff", "listbox_fg": "#000000",
        "label_fg": "#000000", "tree_bg": "#ffffff", "tree_fg": "#000000",
        "selected_bg": "#0078d7", "selected_fg": "#ffffff",
    },
    "dark": {
        "bg": "#2d2d2d", "fg": "#e0e0e0", "select": "#404040",
        "frame": "#383838", "entry": "#505050", "button": "#505050",
        "tab_bg": "#2d2d2d", "tab_fg": "#e0e0e0",
        "notebook_bg": "#383838", "canvas_bg": "#383838",
        "listbox_bg": "#383838", "listbox_fg": "#e0e0e0",
        "label_fg": "#e0e0e0", "tree_bg": "#383838", "tree_fg": "#e0e0e0",
        "selected_bg": "#0078d7", "selected_fg": "#ffffff",
    },
}


def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"theme": "light", "recent_files": []}


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


# ───────────────────── Drag-drop reorder listbox ─────────────────────

class ReorderListbox(tk.Listbox):
    def __init__(self, master, **kw):
        super().__init__(master, **kw)
        self.bind("<Button-1>", self.on_press)
        self.bind("<B1-Motion>", self.on_drag)
        self.bind("<ButtonRelease-1>", self.on_release)
        self._drag_data = {"index": None, "y": 0}

    def on_press(self, e):
        index = self.nearest(e.y)
        if index in self.curselection():
            self._drag_data = {"index": index, "y": e.y}
        else:
            self._drag_data = {"index": None, "y": 0}
            self.selection_clear(0, "end")
            self.selection_set(index)
            self.activate(index)

    def on_drag(self, e):
        idx = self._drag_data["index"]
        if idx is None:
            return
        if abs(e.y - self._drag_data["y"]) < 20:
            return
        new = self.nearest(e.y)
        if new != idx:
            self.swap(idx, new)
            self._drag_data["index"] = new
            self._drag_data["y"] = e.y

    def on_release(self, e):
        self._drag_data = {"index": None, "y": 0}

    def swap(self, a, b):
        items = list(self.get(0, "end"))
        items[a], items[b] = items[b], items[a]
        self.delete(0, "end")
        for item in items:
            self.insert("end", item)
        self.selection_set(b)
        self.activate(b)


# ───────────────────── Main App ─────────────────────

class PDFTool:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("820x640")
        self.root.minsize(700, 500)

        self.settings = load_settings()
        self.recent_files = self.settings.get("recent_files", [])
        self.dark_mode = self.settings.get("theme", "light") == "dark"
        self.colors = dict(THEMES["dark" if self.dark_mode else "light"])

        self._build_menu()
        self._apply_theme()

        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=6, pady=6)

        self.merge_frame = ttk.Frame(self.notebook)
        self.split_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.merge_frame, text=" Merge ")
        self.notebook.add(self.split_frame, text=" Split ")

        self.merge_tab = MergeTab(self.merge_frame, self)
        self.split_tab = SplitTab(self.split_frame, self)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # ── Menu ──
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open PDF...", command=self.open_pdf)
        file_menu.add_separator()
        self.recent_menu = tk.Menu(file_menu, tearoff=0)
        file_menu.add_cascade(label="Recent Files", menu=self.recent_menu)
        self._refresh_recent()
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)

        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Toggle Dark Mode", command=self.toggle_theme)
        menubar.add_cascade(label="View", menu=view_menu)

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _refresh_recent(self):
        self.recent_menu.delete(0, "end")
        for f in self.recent_files:
            self.recent_menu.add_command(
                label=f, command=lambda p=f: self.load_recent(p)
            )
        if not self.recent_files:
            self.recent_menu.add_command(label="(no recent files)", state="disabled")

    def load_recent(self, path):
        if not os.path.isfile(path):
            messagebox.showerror("Error", f"File not found:\n{path}")
            self.recent_files = [f for f in self.recent_files if f != path]
            self._refresh_recent()
            return
        self.split_tab.load_pdf(path)

    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Open PDF", filetypes=[("PDF files", "*.pdf")]
        )
        if not path:
            return
        self.split_tab.load_pdf(path)

    # ── Theme ──
    def toggle_theme(self):
        self.dark_mode = not self.dark_mode
        self.colors = dict(THEMES["dark" if self.dark_mode else "light"])
        self._apply_theme()
        self.merge_tab.refresh_theme()
        self.split_tab.refresh_theme()
        self._refresh_recent()

    def _apply_theme(self):
        c = self.colors
        style = ttk.Style()
        style.theme_use("clam")
        style.configure(".", background=c["bg"], foreground=c["fg"])
        style.configure("TFrame", background=c["bg"])
        style.configure("TLabel", background=c["bg"], foreground=c["fg"])
        style.configure("TNotebook", background=c["notebook_bg"])
        style.configure(
            "TNotebook.Tab",
            background=c["tab_bg"],
            foreground=c["tab_fg"],
            padding=[10, 4],
        )
        style.map("TNotebook.Tab", background=[("selected", c["select"])])
        style.configure(
            "TButton",
            background=c["button"],
            foreground=c["fg"],
            bordercolor=c["select"],
        )
        style.map(
            "TButton",
            background=[("active", c["select"])],
            foreground=[("active", c["fg"])],
        )
        style.configure("TEntry", fieldbackground=c["entry"], foreground=c["fg"])
        style.configure(
            "TLabelframe", background=c["bg"], foreground=c["fg"]
        )
        style.configure(
            "TLabelframe.Label", background=c["bg"], foreground=c["fg"]
        )
        self.root.configure(bg=c["bg"])

    # ── Recent files ──
    def add_recent(self, path):
        path = os.path.abspath(path)
        self.recent_files = [f for f in self.recent_files if f != path]
        self.recent_files.insert(0, path)
        if len(self.recent_files) > MAX_RECENT:
            self.recent_files = self.recent_files[:MAX_RECENT]
        self._refresh_recent()

    def on_close(self):
        self.settings["theme"] = "dark" if self.dark_mode else "light"
        self.settings["recent_files"] = self.recent_files
        save_settings(self.settings)
        self.root.destroy()

    def show_about(self):
        messagebox.showinfo(
            "About PDF Merger & Splitter",
            "PDF Merger & Splitter v1.0\n\n"
            "Features:\n"
            "- Merge PDFs with per-file page ranges\n"
            "- Split / extract pages\n"
            "- Drag-and-drop reorder\n"
            "- Page thumbnails preview\n"
            "- Rotate & delete pages\n"
            "- Password protect / decrypt PDFs\n"
            "- Compress PDF size\n"
            "- Split by bookmarks\n"
            "- Dark mode\n"
            "- Recent files\n\n"
            "Built with PyMuPDF & tkinter",
        )


# ───────────────────── Merge Tab ─────────────────────

class MergeTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.files = []  # list of {"path": str, "pages": str}
        self.var_password = tk.StringVar(value="")
        self.var_compress = tk.BooleanVar(value=False)

        self._build()

    def _build(self):
        c = self.app.colors
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", pady=4)
        ttk.Button(toolbar, text="Add PDF(s)", command=self.add_files).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Remove", command=self.remove_selected).pack(
            side="left", padx=2
        )
        ttk.Button(toolbar, text="Clear All", command=self.clear_all).pack(
            side="left", padx=2
        )
        ttk.Label(toolbar, text="  Page range:").pack(
            side="left", padx=(15, 2)
        )
        self.range_var = tk.StringVar(value="all")
        self.range_entry = ttk.Entry(
            toolbar, textvariable=self.range_var, width=14
        )
        self.range_entry.pack(side="left", padx=2)
        ttk.Button(toolbar, text="Apply", command=self.apply_range).pack(
            side="left", padx=2
        )

        # Listbox
        list_frame = ttk.Frame(self.frame)
        list_frame.pack(fill="both", expand=True, pady=4)
        self.listbox = ReorderListbox(
            list_frame,
            selectmode="extended",
            bg=c["listbox_bg"],
            fg=c["listbox_fg"],
            selectbackground=c["selected_bg"],
            selectforeground=c["selected_fg"],
        )
        scroll = ttk.Scrollbar(
            list_frame, orient="vertical", command=self.listbox.yview
        )
        self.listbox.configure(yscrollcommand=scroll.set)
        self.listbox.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.listbox.bind("<<ListboxSelect>>", self.on_select)

        # Info label
        self.info_label = ttk.Label(self.frame, text="", foreground="gray")
        self.info_label.pack(anchor="w")

        # Bottom options
        opts = ttk.Frame(self.frame)
        opts.pack(fill="x", pady=4)
        ttk.Label(opts, text="Output:").pack(side="left", padx=2)
        self.out_var = tk.StringVar(value="merged.pdf")
        ttk.Entry(opts, textvariable=self.out_var, width=30).pack(
            side="left", padx=2
        )
        ttk.Label(opts, text="  Password:").pack(side="left", padx=(10, 2))
        ttk.Entry(opts, textvariable=self.var_password, width=15, show="*").pack(
            side="left", padx=2
        )
        ttk.Checkbutton(
            opts, text="Compress", variable=self.var_compress
        ).pack(side="left", padx=(10, 2))
        ttk.Button(opts, text=" Merge! ", command=self.merge_pdfs).pack(
            side="right", padx=2
        )

    def add_files(self):
        paths = filedialog.askopenfilenames(
            title="Select PDF files", filetypes=[("PDF files", "*.pdf")]
        )
        for p in paths:
            if not any(f["path"] == p for f in self.files):
                self.files.append({"path": p, "pages": "all"})
                self.listbox.insert("end", self._display_name(p, "all"))
                self.app.add_recent(p)
        self._update_info()

    def _display_name(self, path, pages):
        return f"{os.path.basename(path)}  [{pages}]"

    def remove_selected(self):
        sel = self.listbox.curselection()
        for i in reversed(sel):
            self.listbox.delete(i)
            del self.files[i]
        self._update_info()

    def clear_all(self):
        self.listbox.delete(0, "end")
        self.files.clear()
        self._update_info()

    def on_select(self, e):
        sel = self.listbox.curselection()
        if sel:
            idx = sel[0]
            self.range_var.set(self.files[idx]["pages"])
        else:
            self.range_var.set("all")

    def apply_range(self):
        sel = self.listbox.curselection()
        if not sel:
            messagebox.showwarning("Warning", "Select a file first.")
            return
        idx = sel[0]
        pages = self.range_var.get().strip()
        if not pages:
            pages = "all"
        self.files[idx]["pages"] = pages
        self.listbox.delete(idx)
        self.listbox.insert(
            idx, self._display_name(self.files[idx]["path"], pages)
        )
        self.listbox.selection_set(idx)

    def _update_info(self):
        self.info_label.config(
            text=f"{len(self.files)} file(s) added"
        )

    def merge_pdfs(self):
        if len(self.files) < 2:
            messagebox.showerror("Error", "Add at least 2 PDF files.")
            return

        out_name = self.out_var.get().strip() or "merged.pdf"
        if not out_name.endswith(".pdf"):
            out_name += ".pdf"

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=out_name,
        )
        if not out_path:
            return

        password = self.var_password.get()
        compress = self.var_compress.get()

        try:
            writer = fitz.open()
            for f in self.files:
                src = fitz.open(f["path"])
                pages = f["pages"].strip()
                if not pages or pages == "all":
                    writer.insert_pdf(src)
                else:
                    for p in self._parse_range(pages, len(src)):
                        writer.insert_pdf(src, from_page=p - 1, to_page=p - 1)
                src.close()

            if password:
                writer.save(
                    out_path,
                    encryption=fitz.PDF_ENCRYPT_AES_256,
                    user_pw=password,
                    owner_pw=password,
                    garbage=4,
                    deflate=True,
                    compress=compress,
                )
            else:
                writer.save(
                    out_path,
                    garbage=4 if compress else 1,
                    deflate=compress,
                )
            writer.close()
            messagebox.showinfo(
                "Success", f"Merged {len(self.files)} PDFs into:\n{out_path}"
            )
        except Exception as e:
            messagebox.showerror("Error", f"Merge failed:\n{e}")

    def _parse_range(self, text, total):
        result = set()
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                result.update(range(int(a), int(b) + 1))
            else:
                result.add(int(part))
        return sorted(p for p in result if 1 <= p <= total)

    def refresh_theme(self):
        c = self.app.colors
        self.listbox.configure(
            bg=c["listbox_bg"],
            fg=c["listbox_fg"],
            selectbackground=c["selected_bg"],
            selectforeground=c["selected_fg"],
        )


# ───────────────────── Split Tab ─────────────────────

class SplitTab:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.doc = None
        self.doc_path = None
        self.page_images = []
        self.page_rotations = {}  # index -> rotation delta
        self.page_deleted = set()
        self.thumb_frame_refs = []
        self.var_password = tk.StringVar(value="")
        self.var_compress = tk.BooleanVar(value=False)
        self._build()

    def _build(self):
        self.frame = ttk.Frame(self.parent)
        self.frame.pack(fill="both", expand=True, padx=6, pady=6)

        # Toolbar
        toolbar = ttk.Frame(self.frame)
        toolbar.pack(fill="x", pady=4)
        ttk.Button(toolbar, text="Open PDF", command=self.open_pdf).pack(
            side="left", padx=2
        )
        self.file_label = ttk.Label(
            toolbar, text="No file loaded", foreground="gray"
        )
        self.file_label.pack(side="left", padx=10)
        self.page_count_label = ttk.Label(toolbar, text="")
        self.page_count_label.pack(side="left", padx=5)
        ttk.Label(toolbar, text="  Password:").pack(side="left", padx=(10, 2))
        self.pw_entry = ttk.Entry(
            toolbar, textvariable=self.var_password, width=14, show="*"
        )
        self.pw_entry.pack(side="left", padx=2)
        ttk.Button(toolbar, text="Unlock", command=self.unlock_pdf).pack(
            side="left", padx=2
        )

        # Thumbnail canvas
        canvas_frame = ttk.Frame(self.frame)
        canvas_frame.pack(fill="both", expand=True, pady=4)

        self.canvas = tk.Canvas(
            canvas_frame,
            bg=self.app.colors["canvas_bg"],
            highlightthickness=0,
        )
        v_scroll = ttk.Scrollbar(
            canvas_frame, orient="vertical", command=self.canvas.yview
        )
        h_scroll = ttk.Scrollbar(
            canvas_frame, orient="horizontal", command=self.canvas.xview
        )
        self.canvas.configure(
            yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set
        )
        self.canvas.pack(side="left", fill="both", expand=True)
        v_scroll.pack(side="right", fill="y")
        h_scroll.pack(side="bottom", fill="x")

        self.thumb_container = ttk.Frame(self.canvas)
        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.thumb_container, anchor="nw"
        )
        self.thumb_container.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            ),
        )
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(
                self.canvas_window, width=e.width
            ),
        )

        # Action buttons below thumbnails
        action_frame = ttk.Frame(self.frame)
        action_frame.pack(fill="x", pady=4)
        ttk.Button(
            action_frame, text="Rotate CW 90°", command=self.rotate_cw
        ).pack(side="left", padx=2)
        ttk.Button(
            action_frame, text="Rotate CCW 90°", command=self.rotate_ccw
        ).pack(side="left", padx=2)
        ttk.Button(
            action_frame, text="Delete Selected", command=self.delete_selected
        ).pack(side="left", padx=2)
        ttk.Button(
            action_frame, text="Restore All", command=self.restore_all
        ).pack(side="left", padx=2)

        ttk.Separator(self.frame, orient="horizontal").pack(fill="x", pady=4)

        # Bottom options
        bottom = ttk.Frame(self.frame)
        bottom.pack(fill="x", pady=4)

        # Left side - extract range
        left = ttk.Frame(bottom)
        left.pack(side="left", fill="x", expand=True)
        ttk.Label(left, text="Extract pages:").pack(side="left", padx=2)
        self.extract_var = tk.StringVar(value="")
        ttk.Entry(left, textvariable=self.extract_var, width=18).pack(
            side="left", padx=2
        )
        ttk.Button(
            left, text="Extract", command=self.extract_range
        ).pack(side="left", padx=2)

        # Right side - split & save
        right = ttk.Frame(bottom)
        right.pack(side="right")
        ttk.Checkbutton(
            right, text="Compress", variable=self.var_compress
        ).pack(side="left", padx=5)
        ttk.Button(
            right, text="Split All Pages", command=self.split_all
        ).pack(side="left", padx=2)
        ttk.Button(
            right, text="Split by Bookmarks", command=self.split_bookmarks
        ).pack(side="left", padx=2)
        ttk.Button(
            right, text="Save As", command=self.save_as
        ).pack(side="left", padx=2)

    # ── PDF loading ──
    def open_pdf(self):
        path = filedialog.askopenfilename(
            title="Open PDF", filetypes=[("PDF files", "*.pdf")]
        )
        if path:
            self.load_pdf(path)

    def load_pdf(self, path):
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                self._clear_thumbnails()
                self.doc = doc
                self.doc_path = path
                self.file_label.config(
                    text=os.path.basename(path), foreground="orange"
                )
                self.page_count_label.config(
                    text="(encrypted - enter password)"
                )
                self.app.add_recent(path)
                return
            self._set_doc(doc, path)
            self.app.add_recent(path)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot open PDF:\n{e}")

    def unlock_pdf(self):
        if not self.doc or not self.doc.is_encrypted:
            return
        pw = self.var_password.get()
        if self.doc.authenticate(pw):
            self._set_doc(self.doc, self.doc_path)
        else:
            messagebox.showerror("Error", "Incorrect password.")

    def _set_doc(self, doc, path):
        self.doc = doc
        self.doc_path = path
        self.page_rotations.clear()
        self.page_deleted.clear()
        self.file_label.config(text=os.path.basename(path), foreground="black")
        self.page_count_label.config(text=f"{len(doc)} page(s)")
        self._render_thumbnails()

    # ── Thumbnails ──
    def _clear_thumbnails(self):
        for w in self.thumb_container.winfo_children():
            w.destroy()
        self.page_images.clear()
        self.thumb_frame_refs.clear()

    def _render_thumbnails(self):
        self._clear_thumbnails()
        if not self.doc:
            return

        cols = max(1, self.canvas.winfo_width() // (THUMB_W + 20))

        row_frame = None
        row_count = 0

        for i in range(len(self.doc)):
            if row_count % cols == 0:
                row_frame = ttk.Frame(self.thumb_container)
                row_frame.pack(fill="x", pady=4)
            row_count += 1

            f = ttk.Frame(row_frame)
            f.pack(side="left", padx=6)
            self.thumb_frame_refs.append(f)

            # Render page
            page = self.doc[i]
            mat = fitz.Matrix(THUMB_W / page.rect.width, THUMB_H / page.rect.height)
            pix = page.get_pixmap(matrix=mat)
            tmp = tempfile.NamedTemporaryFile(suffix=".ppm", delete=False)
            tmp.write(pix.tobytes("ppm"))
            tmp.close()
            photo = tk.PhotoImage(file=tmp.name)
            os.unlink(tmp.name)
            self.page_images.append(photo)
            lbl = tk.Label(
                f, image=photo, relief="solid", bd=1,
                bg=self.app.colors["canvas_bg"],
            )
            lbl.pack()
            lbl.bind("<Button-1>", lambda e, idx=i: self._toggle_select(idx))

            num_lbl = ttk.Label(f, text=f"Page {i + 1}", anchor="center")
            num_lbl.pack(fill="x")

    def _toggle_select(self, idx):
        # Simple toggle via selection box - we track selection with a set
        if not hasattr(self, "_selected_pages"):
            self._selected_pages = set()
        if idx in self._selected_pages:
            self._selected_pages.discard(idx)
        else:
            self._selected_pages.add(idx)

    def _get_selected(self):
        if not hasattr(self, "_selected_pages"):
            self._selected_pages = set()
        return self._selected_pages

    # ── Rotate / Delete ──
    def rotate_cw(self):
        sel = self._get_selected()
        if not sel:
            messagebox.showwarning("Warning", "Click pages to select them.")
            return
        for idx in sel:
            self.page_rotations[idx] = (
                self.page_rotations.get(idx, 0) + 90
            ) % 360
        self._apply_transforms()
        self._selected_pages.clear()

    def rotate_ccw(self):
        sel = self._get_selected()
        if not sel:
            messagebox.showwarning("Warning", "Click pages to select them.")
            return
        for idx in sel:
            self.page_rotations[idx] = (
                self.page_rotations.get(idx, 0) - 90
            ) % 360
        self._apply_transforms()
        self._selected_pages.clear()

    def delete_selected(self):
        sel = self._get_selected()
        if not sel:
            messagebox.showwarning("Warning", "Click pages to select them.")
            return
        self.page_deleted.update(sel)
        self._apply_transforms()
        self._selected_pages.clear()

    def restore_all(self):
        self.page_rotations.clear()
        self.page_deleted.clear()
        self._apply_transforms()

    def _apply_transforms(self):
        for w in self.thumb_container.winfo_children():
            for child in w.winfo_children():
                child.destroy()
            w.destroy()
        if hasattr(self, "_selected_pages"):
            self._selected_pages.clear()
        self._render_thumbnails()

    # ── Extract range ──
    def extract_range(self):
        if not self.doc:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        text = self.extract_var.get().strip()
        if not text:
            messagebox.showerror("Error", "Enter page range (e.g. 1,3,5-7).")
            return

        total = len(self.doc)
        try:
            pages = self._parse_range(text, total)
        except Exception as e:
            messagebox.showerror("Error", str(e))
            return

        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="extracted.pdf",
        )
        if not out_path:
            return

        try:
            new_doc = fitz.open()
            for p in pages:
                new_doc.insert_pdf(self.doc, from_page=p - 1, to_page=p - 1)
            self._save_with_options(new_doc, out_path)
            new_doc.close()
            messagebox.showinfo(
                "Success",
                f"Extracted {len(pages)} page(s) to:\n{out_path}",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Extraction failed:\n{e}")

    # ── Split all pages ──
    def split_all(self):
        if not self.doc:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        out_dir = filedialog.askdirectory(title="Select output folder")
        if not out_dir:
            return

        try:
            total = len(self.doc)
            for i in range(total):
                if i in self.page_deleted:
                    continue
                new_doc = fitz.open()
                src_page = i
                rot = self.page_rotations.get(i, 0)
                new_doc.insert_pdf(
                    self.doc, from_page=src_page, to_page=src_page
                )
                if rot and len(new_doc):
                    new_doc[0].set_rotation(rot)
                fname = f"page_{i + 1:03d}.pdf"
                fpath = os.path.join(out_dir, fname)
                self._save_with_options(new_doc, fpath)
                new_doc.close()
            kept = total - len(self.page_deleted)
            messagebox.showinfo(
                "Success",
                f"Split {kept} page(s) into:\n{out_dir}",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Split failed:\n{e}")

    # ── Split by bookmarks ──
    def split_bookmarks(self):
        if not self.doc:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        toc = self.doc.get_toc()
        if not toc:
            messagebox.showinfo(
                "Info", "This PDF has no bookmarks (table of contents)."
            )
            return

        out_dir = filedialog.askdirectory(title="Select output folder for bookmarks")
        if not out_dir:
            return

        try:
            # Build chapter ranges from bookmark page numbers
            chapters = []
            for item in toc:
                level, title, page = item
                if level == 1:
                    safe = "".join(c for c in title if c.isalnum() or c in " _-")
                    if not safe:
                        safe = "chapter"
                    chapters.append(
                        {"title": safe, "start": page, "end": None}
                    )

            if not chapters:
                messagebox.showinfo("Info", "No top-level bookmarks found.")
                return

            total = len(self.doc)
            for i in range(len(chapters)):
                if i + 1 < len(chapters):
                    chapters[i]["end"] = chapters[i + 1]["start"] - 1
                else:
                    chapters[i]["end"] = total

            for ch in chapters:
                start = max(1, ch["start"])
                end = min(total, ch["end"])
                if start > end:
                    continue
                new_doc = fitz.open()
                new_doc.insert_pdf(
                    self.doc, from_page=start - 1, to_page=end - 1
                )
                fname = f"{ch['title']}.pdf"
                fpath = os.path.join(out_dir, fname)
                self._save_with_options(new_doc, fpath)
                new_doc.close()

            messagebox.showinfo(
                "Success",
                f"Split {len(chapters)} chapters into:\n{out_dir}",
            )
        except Exception as e:
            messagebox.showerror("Error", f"Split by bookmarks failed:\n{e}")

    # ── Save As ──
    def save_as(self):
        if not self.doc:
            messagebox.showerror("Error", "Open a PDF first.")
            return
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile="output.pdf",
        )
        if not out_path:
            return
        try:
            new_doc = fitz.open()
            total = len(self.doc)
            for i in range(total):
                if i in self.page_deleted:
                    continue
                rot = self.page_rotations.get(i, 0)
                new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                if rot and len(new_doc):
                    new_doc[-1].set_rotation(rot)
            self._save_with_options(new_doc, out_path)
            new_doc.close()
            messagebox.showinfo("Success", f"Saved to:\n{out_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed:\n{e}")

    # ── Helpers ──
    def _save_with_options(self, doc, path):
        compress = self.var_compress.get()
        doc.save(
            path,
            garbage=4 if compress else 1,
            deflate=compress,
        )

    def _parse_range(self, text, total):
        result = set()
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                try:
                    start, end = int(a), int(b)
                    if start < 1 or end > total:
                        raise ValueError(
                            f"Range {part} out of bounds (1-{total})"
                        )
                    result.update(range(start, end + 1))
                except ValueError as e:
                    if "out of bounds" in str(e):
                        raise
                    raise ValueError(f"Invalid range: {part}")
            else:
                try:
                    p = int(part)
                    if p < 1 or p > total:
                        raise ValueError(
                            f"Page {p} out of bounds (1-{total})"
                        )
                    result.add(p)
                except ValueError as e:
                    if "out of bounds" in str(e):
                        raise
                    raise ValueError(f"Invalid page: {part}")
        return sorted(result)

    def refresh_theme(self):
        self.canvas.configure(bg=self.app.colors["canvas_bg"])


# ───────────────────── Entry point ─────────────────────

if __name__ == "__main__":
    import ctypes
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        pass
    root = tk.Tk()
    app = PDFTool(root)
    root.mainloop()
