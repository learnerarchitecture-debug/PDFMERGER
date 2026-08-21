# PDF Suite Pro

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER  
**Version:** v2.3

A full-featured PDF utility for **Windows** with a modern dark UI — merge, split, sign, compress, redact, and 30+ tools. No installation needed (portable) or install via setup wizard.

## Features

### Merge
- Standard PDF merging with per-file page ranges
- **Alternate merge** — interleave pages from multiple files
- Insert PDF at specific position
- Add cover page · Duplicate files · Drag-and-drop reorder
- Password protect · Compression
- **Threaded** — UI stays responsive during large merges

### Split / Edit
- Split every page, extract range, split by bookmarks or page count
- **Split even/odd pages** (duplex scanning)
- Rotate CW/CCW · Delete · Insert blank · Duplicate pages
- Mirror/flip pages · Convert to grayscale (new file or in-place)
- **Undo/Redo** for all page actions
- **Search text** with thumbnail highlighting (runs in background thread)
- Extract all images or text from PDF
- Save As with modifications

### Tools
- **Digital Signature** — Modern styled "Digitally Signed by AYUSH GUPTA" box with date
- **Image Compression** — JPG/PNG quality 1–100
- **Images to PDF** — Combine multiple images into one PDF
- **PDF Compression** — 4 levels with image downsampling
- **Redact Text** — Permanently remove text
- **Remove Metadata** · **Password Protect** (AES-256) · **Remove Password**
- **Add Page Numbers** · **Flatten PDF** (annotations)
- **Clone Open PDF x2**
- **Rate & Review** dialog (1–5 stars)

### Windows Compatibility
- Supports Windows 7, 8, 8.1, 10, and 11
- Automatic Windows version check at startup
- High DPI awareness for sharp display on all screens
- Modern dark theme optimized for Windows

## Quick Start

| Step | Action |
|------|--------|
| 1 | Download `PDF Suite Pro.exe` from the Releases page **or** install via the setup wizard |
| 2 | Double-click — **no installation required** (portable) |
| 3 | Or install via `PDFSuitePro_Installer.exe` for proper Windows integration |

## Build from Source

```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name "PDF Suite Pro" pdf_tool.py
```

Output: `dist/PDF Suite Pro.exe`

## Project Structure

```
├── pdf_tool.py              # Main application source (Tkinter with modern UI)
├── PDF Suite Pro.exe        # Pre-built executable (40 MB)
├── PDFSuitePro_Installer.exe  # Inno Setup installer
├── pdf_merger.spec          # PyInstaller specification
├── requirements.txt
├── INSTALL.txt
├── INSTALLATION.txt
├── README.md
├── dist/                    # PyInstaller build output
├── build/                   # PyBuild temporary files
└── android/                 # Android app (Kivy)
    ├── main.py
    └── buildozer.spec
└── icons/                   # Installer icons
    └── pdf_suite_pro.ico
```

## License

MIT