"""
PDF Merger & Splitter — Android App (Kivy)
"""
import os, json, threading, queue
from pathlib import Path

from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.gridlayout import GridLayout
from kivy.uix.scrollview import ScrollView
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.uix.popup import Popup
from kivy.uix.filechooser import FileChooserListView
from kivy.uix.checkbox import CheckBox
from kivy.uix.progressbar import ProgressBar
from kivy.uix.image import Image
from kivy.uix.behaviors import ButtonBehavior
from kivy.core.window import Window
from kivy.clock import Clock
from kivy.graphics.texture import Texture
from kivy.metrics import dp
from kivy.utils import platform

try:
    import fitz
except ImportError:
    fitz = None

try:
    from PIL import Image as PILImage
except ImportError:
    PILImage = None

APP_DIR = Path(os.environ.get("APP_DIR", "."))
SETTINGS_FILE = APP_DIR / "settings.json"
THUMB_W, THUMB_H = 120, 160


# ───────────────────── Settings ─────────────────────

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {"recent_files": []}


def save_settings(data):
    try:
        SETTINGS_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


# ───────────────────── Reorderable List Item ─────────────────────

class FileItem(BoxLayout):
    def __init__(self, path, idx, **kw):
        super().__init__(orientation="horizontal", size_hint_y=None, height=dp(44), **kw)
        self.path = path
        self.idx = idx
        self.page_range = "all"

        self.add_widget(Label(
            text=os.path.basename(path),
            size_hint_x=0.6,
            halign="left",
            text_size=(None, None),
            shorten=True,
        ))
        self.range_input = TextInput(
            text="all",
            size_hint_x=0.25,
            multiline=False,
            font_size=dp(14),
        )
        self.add_widget(self.range_input)
        self.add_widget(Button(
            text="X",
            size_hint_x=0.15,
            on_press=self.remove_self,
            background_color=(0.8, 0.2, 0.2, 1),
        ))

    def remove_self(self, btn):
        parent = self.parent
        if parent:
            parent.remove_widget(self)


# ───────────────────── Clickable Image for Thumbnails ─────────────────────

class ThumbnailImage(ButtonBehavior, Image):
    def __init__(self, page_index, **kw):
        super().__init__(**kw)
        self.page_index = page_index
        self.selected = False
        self.bind(on_press=self.toggle_select)

    def toggle_select(self, *a):
        self.selected = not self.selected
        self.color = (0.3, 0.7, 1, 1) if self.selected else (1, 1, 1, 1)


# ───────────────────── Merge Screen ─────────────────────

class MergeScreen(BoxLayout):
    def __init__(self, app_ref, **kw):
        super().__init__(orientation="vertical", spacing=dp(6), padding=dp(8), **kw)
        self.app_ref = app_ref
        self.file_widgets = []

        # Toolbar
        toolbar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        toolbar.add_widget(Button(text="Add PDF(s)", on_press=self.add_files))
        toolbar.add_widget(Button(text="Clear All", on_press=self.clear_all))
        self.add_widget(toolbar)

        # File list
        scroll = ScrollView()
        self.file_list = GridLayout(
            cols=1, spacing=dp(4), size_hint_y=None
        )
        self.file_list.bind(
            minimum_height=self.file_list.setter("height")
        )
        scroll.add_widget(self.file_list)
        self.add_widget(scroll)

        # Info
        self.info_label = Label(
            text="No files added", size_hint_y=None, height=dp(30)
        )
        self.add_widget(self.info_label)

        # Options
        opts = BoxLayout(
            size_hint_y=None, height=dp(100), orientation="vertical", spacing=dp(4)
        )
        row1 = BoxLayout(spacing=dp(6))
        row1.add_widget(Label(text="Output:", size_hint_x=0.25))
        self.out_input = TextInput(text="merged.pdf", multiline=False, size_hint_x=0.75)
        row1.add_widget(self.out_input)
        opts.add_widget(row1)

        row2 = BoxLayout(spacing=dp(6))
        row2.add_widget(Label(text="Password:", size_hint_x=0.25))
        self.pw_input = TextInput(text="", password=True, multiline=False, size_hint_x=0.5)
        row2.add_widget(Label(text="Compress:", size_hint_x=0.15))
        self.compress_cb = CheckBox(size_hint_x=0.1)
        row2.add_widget(self.compress_cb)
        opts.add_widget(row2)

        self.add_widget(opts)

        # Merge button
        self.add_widget(Button(
            text="MERGE PDFs",
            size_hint_y=None,
            height=dp(48),
            background_color=(0.2, 0.6, 0.3, 1),
            on_press=self.merge_pdfs,
        ))

    def add_files(self, btn=None):
        if platform == "android":
            from plyer import filechooser
            filechooser.open_file(
                filters=["*.pdf"],
                multiple=True,
                on_selection=self._on_files_selected,
            )
        else:
            content = FileChooserListView(
                filters=["*.pdf"],
                dirselect=False,
                multiselect=True,
            )
            content.bind(on_submit=self._on_desktop_files)
            popup = Popup(
                title="Select PDF files",
                content=content,
                size_hint=(0.9, 0.9),
            )
            content.popup = popup
            btn_close = Button(text="Done", size_hint_y=None, height=dp(40))
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            popup.open()

    def _on_files_selected(self, paths):
        for p in paths:
            self._add_single(p)

    def _on_desktop_files(self, chooser, selection, *a):
        if selection:
            for p in selection:
                self._add_single(p)
        if hasattr(chooser, "popup"):
            chooser.popup.dismiss()

    def _add_single(self, path):
        if not path.endswith(".pdf"):
            return
        item = FileItem(path, len(self.file_widgets))
        self.file_widgets.append(item)
        self.file_list.add_widget(item)
        self.app_ref.add_recent(path)
        self._update_info()

    def clear_all(self, btn=None):
        self.file_list.clear_widgets()
        self.file_widgets.clear()
        self._update_info()

    def _update_info(self):
        self.info_label.text = f"{len(self.file_widgets)} file(s) added"

    def merge_pdfs(self, btn):
        if len(self.file_widgets) < 2:
            self._show_popup("Error", "Add at least 2 PDF files.")
            return
        if fitz is None:
            self._show_popup("Error", "PyMuPDF not available.")
            return

        out_name = self.out_input.text.strip() or "merged.pdf"
        if not out_name.endswith(".pdf"):
            out_name += ".pdf"

        save_path = self._get_save_path(out_name)
        if not save_path:
            return

        password = self.pw_input.text
        compress = self.compress_cb.active

        try:
            writer = fitz.open()
            for item in self.file_widgets:
                src = fitz.open(item.path)
                pages = item.range_input.text.strip()
                if not pages or pages == "all":
                    writer.insert_pdf(src)
                else:
                    for p in self._parse_range(pages, len(src)):
                        writer.insert_pdf(src, from_page=p - 1, to_page=p - 1)
                src.close()

            writer.save(
                save_path,
                encryption=fitz.PDF_ENCRYPT_AES_256 if password else 0,
                user_pw=password or None,
                owner_pw=password or None,
                garbage=4 if compress else 1,
                deflate=compress,
            )
            writer.close()
            self._show_popup("Success", f"Merged to:\n{save_path}")
        except Exception as e:
            self._show_popup("Error", f"Merge failed:\n{e}")

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

    def _get_save_path(self, fname):
        if platform == "android":
            from plyer import filechooser as fc
            from kivy.clock import mainthread
            self._save_result = None
            ev = threading.Event()

            def cb(paths):
                if paths:
                    self._save_result = paths[0]
                ev.set()

            fc.save_file(
                filters=["*.pdf"],
                on_selection=cb,
            )
            ev.wait(timeout=30)
            return self._save_result
        else:
            from kivy.uix.filechooser import FileChooserListView
            content = BoxLayout(orientation="vertical")
            fc = FileChooserListView(filters=["*.pdf"])
            content.add_widget(fc)
            btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            result = [None]

            def on_select(*a):
                sel = fc.selection
                if sel:
                    result[0] = sel[0]
                popup.dismiss()

            btn_row.add_widget(Button(text="Save", on_press=on_select))
            btn_row.add_widget(Button(
                text="Cancel",
                on_press=lambda x: popup.dismiss(),
            ))
            content.add_widget(btn_row)
            popup = Popup(title="Save As", content=content, size_hint=(0.9, 0.9))
            popup.open()
            popup.bind(on_dismiss=lambda *a: None)
            return result[0]

    def _show_popup(self, title, msg):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text=msg, halign="center"))
        btn = Button(text="OK", size_hint_y=None, height=dp(40))
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


# ───────────────────── Split Screen ─────────────────────

class SplitScreen(BoxLayout):
    def __init__(self, app_ref, **kw):
        super().__init__(orientation="vertical", spacing=dp(6), padding=dp(8), **kw)
        self.app_ref = app_ref
        self.doc = None
        self.doc_path = None
        self.thumb_widgets = []
        self.page_rotations = {}
        self.page_deleted = set()

        # Toolbar
        toolbar = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
        toolbar.add_widget(Button(text="Open PDF", on_press=self.open_pdf))
        self.file_label = Label(text="No file loaded", size_hint_x=0.5)
        toolbar.add_widget(self.file_label)
        self.add_widget(toolbar)

        # Thumbnails
        scroll = ScrollView()
        self.thumb_grid = GridLayout(
            cols=3, spacing=dp(6), size_hint_y=None, padding=dp(4)
        )
        self.thumb_grid.bind(
            minimum_height=self.thumb_grid.setter("height")
        )
        scroll.add_widget(self.thumb_grid)
        self.add_widget(scroll)

        # Actions
        act = BoxLayout(
            size_hint_y=None, height=dp(44), spacing=dp(6)
        )
        act.add_widget(Button(text="Rotate CW", on_press=self.rotate_cw))
        act.add_widget(Button(text="Rotate CCW", on_press=self.rotate_ccw))
        act.add_widget(Button(text="Delete", on_press=self.delete_selected))
        act.add_widget(Button(text="Restore", on_press=self.restore_all))
        self.add_widget(act)

        # Bottom controls
        bottom = BoxLayout(
            size_hint_y=None, height=dp(120), orientation="vertical", spacing=dp(4)
        )
        row1 = BoxLayout(spacing=dp(6))
        row1.add_widget(Label(text="Extract:", size_hint_x=0.2))
        self.extract_input = TextInput(
            text="", hint_text="e.g. 1,3,5-7", multiline=False, size_hint_x=0.5
        )
        row1.add_widget(self.extract_input)
        row1.add_widget(Button(
            text="Extract", size_hint_x=0.3, on_press=self.extract_range
        ))
        bottom.add_widget(row1)

        row2 = BoxLayout(spacing=dp(6))
        row2.add_widget(Button(text="Split All", on_press=self.split_all))
        row2.add_widget(Button(text="Bookmarks", on_press=self.split_bookmarks))
        row2.add_widget(Button(text="Save As", on_press=self.save_as))
        bottom.add_widget(row2)

        row3 = BoxLayout(spacing=dp(6))
        row3.add_widget(Label(text="Compress:", size_hint_x=0.25))
        self.compress_cb = CheckBox(size_hint_x=0.1)
        row3.add_widget(self.compress_cb)
        bottom.add_widget(row3)

        self.add_widget(bottom)

    # ── PDF Load ──
    def open_pdf(self, btn=None):
        if platform == "android":
            from plyer import filechooser
            filechooser.open_file(
                filters=["*.pdf"],
                multiple=False,
                on_selection=self._on_pdf_selected,
            )
        else:
            content = FileChooserListView(filters=["*.pdf"])
            content.bind(on_submit=self._on_desktop_pdf)
            popup = Popup(
                title="Open PDF",
                content=content,
                size_hint=(0.9, 0.9),
            )
            content.popup = popup
            btn_close = Button(
                text="Cancel", size_hint_y=None, height=dp(40)
            )
            btn_close.bind(on_press=lambda x: popup.dismiss())
            content.add_widget(btn_close)
            popup.open()

    def _on_pdf_selected(self, paths):
        if paths:
            self.load_pdf(paths[0])

    def _on_desktop_pdf(self, chooser, selection, *a):
        if selection:
            self.load_pdf(selection[0])
        if hasattr(chooser, "popup"):
            chooser.popup.dismiss()

    def load_pdf(self, path):
        if not os.path.isfile(path):
            self._show_popup("Error", "File not found.")
            return
        try:
            doc = fitz.open(path)
            if doc.is_encrypted:
                self._prompt_password(doc, path)
                return
            self._set_doc(doc, path)
            self.app_ref.add_recent(path)
        except Exception as e:
            self._show_popup("Error", f"Cannot open PDF:\n{e}")

    def _prompt_password(self, doc, path):
        content = BoxLayout(
            orientation="vertical", spacing=dp(10), padding=dp(10)
        )
        content.add_widget(Label(text="PDF is encrypted. Enter password:"))
        pw_input = TextInput(password=True, multiline=False)
        content.add_widget(pw_input)
        btn = Button(text="Unlock", size_hint_y=None, height=dp(40))
        content.add_widget(btn)
        popup = Popup(title="Password", content=content, size_hint=(0.8, 0.4))
        btn.bind(on_press=lambda x: self._try_unlock(doc, path, pw_input.text, popup))
        popup.open()

    def _try_unlock(self, doc, path, pw, popup):
        if doc.authenticate(pw):
            popup.dismiss()
            self._set_doc(doc, path)
        else:
            self._show_popup("Error", "Incorrect password.")

    def _set_doc(self, doc, path):
        self.doc = doc
        self.doc_path = path
        self.page_rotations.clear()
        self.page_deleted.clear()
        self.file_label.text = f"{os.path.basename(path)} ({len(doc)} pages)"
        self._render_thumbnails()

    # ── Thumbnails ──
    def _render_thumbnails(self):
        self.thumb_grid.clear_widgets()
        self.thumb_widgets.clear()
        if not self.doc:
            return

        for i in range(len(self.doc)):
            try:
                page = self.doc[i]
                mat = fitz.Matrix(80 / page.rect.width, 110 / page.rect.height)
                pix = page.get_pixmap(matrix=mat)
                img_data = pix.tobytes("ppm")
                tex = Texture.create(size=(pix.width, pix.height))
                tex.blit_buffer(img_data, colorfmt="rgb")
                tex.flip_vertical()

                thumb = ThumbnailImage(page_index=i, texture=tex, size_hint_y=None, height=dp(130))
                self.thumb_grid.add_widget(thumb)
                self.thumb_widgets.append(thumb)
            except Exception:
                lbl = Label(
                    text=f"[{i + 1}]",
                    size_hint_y=None,
                    height=dp(130),
                )
                self.thumb_grid.add_widget(lbl)
                self.thumb_widgets.append(lbl)

    # ── Rotate / Delete ──
    def rotate_cw(self, btn):
        for w in self.thumb_widgets:
            if isinstance(w, ThumbnailImage) and w.selected:
                idx = w.page_index
                self.page_rotations[idx] = (
                    self.page_rotations.get(idx, 0) + 90
                ) % 360
        self._clear_selection()

    def rotate_ccw(self, btn):
        for w in self.thumb_widgets:
            if isinstance(w, ThumbnailImage) and w.selected:
                idx = w.page_index
                self.page_rotations[idx] = (
                    self.page_rotations.get(idx, 0) - 90
                ) % 360
        self._clear_selection()

    def delete_selected(self, btn):
        for w in self.thumb_widgets:
            if isinstance(w, ThumbnailImage) and w.selected:
                self.page_deleted.add(w.page_index)
        self._clear_selection()

    def restore_all(self, btn):
        self.page_rotations.clear()
        self.page_deleted.clear()
        self._clear_selection()

    def _clear_selection(self):
        for w in self.thumb_widgets:
            if isinstance(w, ThumbnailImage):
                w.selected = False
                w.color = (1, 1, 1, 1)

    # ── Extract ──
    def extract_range(self, btn):
        if not self.doc:
            self._show_popup("Error", "Open a PDF first.")
            return
        text = self.extract_input.text.strip()
        if not text:
            self._show_popup("Error", "Enter page range e.g. 1,3,5-7")
            return
        total = len(self.doc)
        try:
            pages = self._parse_range(text, total)
        except Exception as e:
            self._show_popup("Error", str(e))
            return

        save_path = self._get_save_path("extracted.pdf")
        if not save_path:
            return
        try:
            new_doc = fitz.open()
            for p in pages:
                new_doc.insert_pdf(self.doc, from_page=p - 1, to_page=p - 1)
            self._save_doc(new_doc, save_path)
            new_doc.close()
            self._show_popup("Success", f"Extracted {len(pages)} page(s)")
        except Exception as e:
            self._show_popup("Error", f"Extraction failed:\n{e}")

    # ── Split All ──
    def split_all(self, btn):
        if not self.doc:
            self._show_popup("Error", "Open a PDF first.")
            return
        if platform == "android":
            from plyer import filechooser as fc
            self._split_dir = None
            ev = threading.Event()

            def cb(paths):
                if paths:
                    self._split_dir = paths[0] if os.path.isdir(paths[0]) else os.path.dirname(paths[0])
                ev.set()

            fc.choose_dir(on_selection=cb)
            ev.wait(timeout=30)
            out_dir = self._split_dir
        else:
            from kivy.uix.filechooser import FileChooserListView
            content = BoxLayout(orientation="vertical")
            fc = FileChooserListView(dirselect=True)
            content.add_widget(fc)
            result = [None]
            btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))

            def on_select(*a):
                sel = fc.selection
                if sel:
                    result[0] = sel[0] if os.path.isdir(sel[0]) else os.path.dirname(sel[0])
                popup.dismiss()

            btn_row.add_widget(Button(text="Select", on_press=on_select))
            btn_row.add_widget(Button(text="Cancel", on_press=lambda x: popup.dismiss()))
            content.add_widget(btn_row)
            popup = Popup(title="Select folder", content=content, size_hint=(0.9, 0.9))
            popup.open()
            out_dir = result[0]

        if not out_dir:
            return
        try:
            total = len(self.doc)
            for i in range(total):
                if i in self.page_deleted:
                    continue
                new_doc = fitz.open()
                new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                rot = self.page_rotations.get(i, 0)
                if rot and len(new_doc):
                    new_doc[0].set_rotation(rot)
                fpath = os.path.join(out_dir, f"page_{i + 1:03d}.pdf")
                self._save_doc(new_doc, fpath)
                new_doc.close()
            kept = total - len(self.page_deleted)
            self._show_popup("Success", f"Split {kept} pages into:\n{out_dir}")
        except Exception as e:
            self._show_popup("Error", f"Split failed:\n{e}")

    # ── Split by Bookmarks ──
    def split_bookmarks(self, btn):
        if not self.doc:
            self._show_popup("Error", "Open a PDF first.")
            return
        toc = self.doc.get_toc()
        if not toc:
            self._show_popup("Info", "No bookmarks found.")
            return

        out_dir = self._get_save_path("")
        if not out_dir:
            return
        out_dir = os.path.dirname(out_dir) if os.path.isfile(out_dir) else out_dir

        try:
            chapters = []
            for item in toc:
                level, title, page = item
                if level == 1:
                    safe = "".join(c for c in title if c.isalnum() or c in " _-")
                    chapters.append({"title": safe or "chapter", "start": page, "end": None})

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
                new_doc.insert_pdf(self.doc, from_page=start - 1, to_page=end - 1)
                fpath = os.path.join(out_dir, f"{ch['title']}.pdf")
                self._save_doc(new_doc, fpath)
                new_doc.close()

            self._show_popup("Success", f"Split {len(chapters)} chapters")
        except Exception as e:
            self._show_popup("Error", f"Bookmark split failed:\n{e}")

    # ── Save As ──
    def save_as(self, btn):
        if not self.doc:
            self._show_popup("Error", "Open a PDF first.")
            return
        save_path = self._get_save_path("output.pdf")
        if not save_path:
            return
        try:
            new_doc = fitz.open()
            total = len(self.doc)
            for i in range(total):
                if i in self.page_deleted:
                    continue
                new_doc.insert_pdf(self.doc, from_page=i, to_page=i)
                rot = self.page_rotations.get(i, 0)
                if rot and len(new_doc):
                    new_doc[-1].set_rotation(rot)
            self._save_doc(new_doc, save_path)
            new_doc.close()
            self._show_popup("Success", f"Saved to:\n{save_path}")
        except Exception as e:
            self._show_popup("Error", f"Save failed:\n{e}")

    # ── Helpers ──
    def _save_doc(self, doc, path):
        compress = self.compress_cb.active
        doc.save(path, garbage=4 if compress else 1, deflate=compress)

    def _parse_range(self, text, total):
        result = set()
        for part in text.replace(" ", "").split(","):
            if not part:
                continue
            if "-" in part:
                a, b = part.split("-", 1)
                s, e = int(a), int(b)
                if s < 1 or e > total:
                    raise ValueError(f"Range {part} out of bounds (1-{total})")
                result.update(range(s, e + 1))
            else:
                p = int(part)
                if p < 1 or p > total:
                    raise ValueError(f"Page {p} out of bounds (1-{total})")
                result.add(p)
        return sorted(result)

    def _get_save_path(self, fname):
        if platform == "android":
            from plyer import filechooser as fc
            self._save_result = None
            ev = threading.Event()

            def cb(paths):
                if paths:
                    self._save_result = paths[0]
                ev.set()

            fc.save_file(filters=["*.pdf"], on_selection=cb)
            ev.wait(timeout=30)
            return self._save_result
        else:
            from kivy.uix.filechooser import FileChooserListView
            content = BoxLayout(orientation="vertical")
            fch = FileChooserListView(filters=["*.pdf"])
            content.add_widget(fch)
            result = [None]

            def on_select(*a):
                sel = fch.selection
                if sel:
                    result[0] = sel[0] if sel[0].endswith(".pdf") else sel[0] + ".pdf"
                popup.dismiss()

            btn_row = BoxLayout(size_hint_y=None, height=dp(40), spacing=dp(6))
            btn_row.add_widget(Button(text="Save", on_press=on_select))
            btn_row.add_widget(Button(text="Cancel", on_press=lambda x: popup.dismiss()))
            content.add_widget(btn_row)
            popup = Popup(title="Save As", content=content, size_hint=(0.9, 0.9))
            popup.open()
            return result[0]

    def _show_popup(self, title, msg):
        content = BoxLayout(orientation="vertical", spacing=dp(10), padding=dp(10))
        content.add_widget(Label(text=msg, halign="center"))
        btn = Button(text="OK", size_hint_y=None, height=dp(40))
        content.add_widget(btn)
        popup = Popup(title=title, content=content, size_hint=(0.8, 0.5))
        btn.bind(on_press=popup.dismiss)
        popup.open()


# ───────────────────── Main App ─────────────────────

class PDFMergerApp(App):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.settings = load_settings()
        self.recent_files = self.settings.get("recent_files", [])

    def build(self):
        self.title = "PDF Merger & Splitter"
        root = BoxLayout(orientation="vertical")

        # Tab buttons
        tabs = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(2))
        self.merge_btn = ToggleButton(
            text="Merge",
            group="tabs",
            state="down",
            on_press=self.switch_to_merge,
        )
        self.split_btn = ToggleButton(
            text="Split",
            group="tabs",
            on_press=self.switch_to_split,
        )
        tabs.add_widget(self.merge_btn)
        tabs.add_widget(self.split_btn)
        root.add_widget(tabs)

        # Content area
        self.content = BoxLayout()
        root.add_widget(self.content)

        self.merge_screen = MergeScreen(app_ref=self)
        self.split_screen = SplitScreen(app_ref=self)
        self.content.add_widget(self.merge_screen)

        self._apply_theme()
        return root

    def switch_to_merge(self, btn):
        self.content.clear_widgets()
        self.content.add_widget(self.merge_screen)

    def switch_to_split(self, btn):
        self.content.clear_widgets()
        self.content.add_widget(self.split_screen)

    def add_recent(self, path):
        path = os.path.abspath(path)
        self.recent_files = [f for f in self.recent_files if f != path]
        self.recent_files.insert(0, path)
        if len(self.recent_files) > 10:
            self.recent_files = self.recent_files[:10]
        self._save()

    def _save(self):
        self.settings["recent_files"] = self.recent_files
        save_settings(self.settings)

    def _apply_theme(self):
        from kivy.core.window import Window
        Window.clearcolor = (0.15, 0.15, 0.15, 1)

    def on_stop(self):
        self._save()


if __name__ == "__main__":
    PDFMergerApp().run()
