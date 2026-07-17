# PDF Merger & Splitter

**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER

Merge and split PDF files on **Windows** (desktop app) and **Android** (mobile app).

## Features

- **Merge PDFs** — Combine multiple PDFs into one, with per-file page range selection
- **Split PDF** — Split every page into separate files, or extract a custom page range
- **Page Thumbnails** — Visual preview of all pages (requires Pillow)
- **Rotate Pages** — Rotate selected pages 90° CW or CCW
- **Delete Pages** — Remove unwanted pages before saving
- **Split by Bookmarks** — Automatically split chapters using PDF table of contents
- **Password Protection** — Encrypt output PDFs with AES-256 password
- **Unlock PDFs** — Open password-protected PDFs
- **Compress** — Reduce output file size
- **Dark Mode** — Toggle dark/light theme (Windows only)
- **Drag & Drop Reorder** — Reorder files in the merge list by dragging
- **Recent Files** — Quick access to recently opened PDFs

## Desktop (Windows)

### Requirements
- Windows 10 or later (64-bit)
- No additional software — executable is self-contained

### Installation
See [INSTALLATION.txt](INSTALLATION.txt) for detailed instructions.

### Download
Pre-built executable: `dist/PDFMerger.exe`

### Build from Source
```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name "PDFMerger" --hidden-import fitz pdf_tool.py
```
Executable will be in `dist/PDFMerger.exe`.

### Run Directly (no build needed)
```bash
pip install -r requirements.txt
python pdf_tool.py
```
> **Note:** Without Pillow, thumbnails won't display but all other features work.

---

## Android

### Requirements
- Python 3.8+ with Kivy and Buildozer
- Linux environment (or WSL) for building the APK

### Build APK

```bash
# On Linux or WSL:
cd android/
pip install buildozer
buildozer android debug

# APK will be at: android/bin/*.apk
```

Or build with Docker:
```bash
cd android/
docker run --interactive --tty --rm \
    --volume "$(pwd):/opt/app" \
    --workdir /opt/app \
    kivy/buildozer:latest \
    buildozer android debug
```

### Android Usage
- **Merge tab**: Tap "Add PDF(s)" to select files, set page ranges, tap "MERGE PDFs"
- **Split tab**: Tap "Open PDF", tap thumbnails to select, use Rotate/Delete, then Extract/Split/Save

## Usage

### Merge Tab
1. Click **Add PDF(s)** to select files
2. Select a file and enter a **page range** (e.g. `1-5,7,9-12`) or leave as `all`
3. Drag items to reorder
4. Set **output filename**, optional **password**, and **compress** option
5. Click **Merge!**

### Split Tab
1. Click **Open PDF** to load a file
2. Click thumbnails to **select pages**
3. Use **Rotate CW/CCW** or **Delete Selected** to modify pages
4. Choose an action:
   - **Extract** — Save selected page range to a new file
   - **Split All Pages** — Save each page as a separate PDF
   - **Split by Bookmarks** — Save each chapter as a separate PDF
   - **Save As** — Save the modified document

## Project Structure

```
├── pdf_tool.py              # Desktop app (tkinter/PyMuPDF)
├── dist/PDFMerger.exe       # Pre-built Windows executable
├── android/
│   ├── main.py              # Android app (Kivy/PyMuPDF)
│   └── buildozer.spec        # Buildozer configuration for APK
├── requirements.txt         # Python dependencies
├── README.md
└── INSTALLATION.txt
```

## Dependencies

- **PyMuPDF** (fitz) — PDF reading, writing, rendering
- **Pillow** (optional) — Thumbnail image generation
- **PyInstaller** (build only) — Package Windows executable
- **Kivy** (Android only) — Mobile UI framework
- **Plyer** (Android only) — Native file picker

## License

MIT
