# PDF Merger & Splitter

**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER

Merge and split PDF files on **Windows** (desktop app) and **Android** (mobile app).

## Features

- **Merge PDFs** — Combine multiple PDFs into one, with per-file page range selection
- **Split PDF** — Split every page into separate files, or extract a custom page range
- **Page Thumbnails** — Visual preview of all pages
- **Rotate Pages** — Rotate selected pages 90° CW or CCW
- **Delete Pages** — Remove unwanted pages before saving
- **Split by Bookmarks** — Automatically split chapters using PDF table of contents
- **Password Protection** — Encrypt output PDFs with AES-256 password
- **Unlock PDFs** — Open password-protected PDFs
- **Compress** — Reduce output file size
- **Dark Mode** — Toggle dark/light theme (Windows only)
- **Drag & Drop Reorder** — Reorder files in the merge list by dragging
- **Recent Files** — Quick access to recently opened PDFs

## Quick Start (Windows)

1. Double-click `dist/PDFMerger.exe` — no installation needed
2. Or right-click `dist/PDFMerger.exe` → **Create shortcut** on desktop

## Desktop (Windows)

### Requirements
- Windows 10 or later (64-bit)
- No additional software — executable is self-contained

### Installation
See [INSTALLATION.txt](INSTALLATION.txt) for detailed instructions.

### Build from Source
```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name "PDFMerger" --hidden-import fitz pdf_tool.py
```

### Run Directly (no build needed)
```bash
pip install -r requirements.txt
python pdf_tool.py
```

---

## Android

### Requirements
- Python 3.8+ with Kivy and Buildozer
- Linux environment (or WSL) for building the APK

### Build APK
```bash
cd android/
pip install buildozer
buildozer android debug
# APK: android/bin/*.apk
```

Or with Docker:
```bash
cd android/
docker run --rm -v "$(pwd):/opt/app" -w /opt/app kivy/buildozer:latest buildozer android debug
```

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
4. Choose: **Extract** | **Split All** | **Split by Bookmarks** | **Save As**

## Project Structure

```
├── pdf_tool.py              # Desktop app source (tkinter/PyMuPDF)
├── dist/PDFMerger.exe       # Pre-built Windows executable
├── android/
│   ├── main.py              # Android app (Kivy/PyMuPDF)
│   └── buildozer.spec       # Buildozer configuration
├── requirements.txt         # Python dependencies
├── README.md
├── INSTALLATION.txt         # Full installation guide
└── INSTALL.txt              # Quick install reference
```

## Dependencies

- **PyMuPDF** (fitz) — PDF reading, writing, rendering
- **PyInstaller** (build only) — Package Windows executable
- **Kivy + Plyer** (Android only) — Mobile UI & file picker

## License

MIT
