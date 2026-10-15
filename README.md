# PDF Suite Pro

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER  
**Version:** v2.3

A full-featured PDF utility for **Windows** with a modern dark UI — merge, split, sign, compress, redact, and 30+ tools. No installation needed (portable) or install via setup wizard.

## Features

### Merge
- Standard PDF merging with per-file page ranges
- **Drag-and-drop reorder** — merge output follows the order shown in the list
- **Reorder buttons** — Move Up / Move Down / Top / Bottom
- **Alternate merge** — interleave pages from multiple files
- Insert PDF at specific position · Add cover page · Duplicate files
- Password protect · Compression
- **Threaded** — UI stays responsive during large merges

### Split / Edit
- Split every page, extract range, split by bookmarks or page count
- **Split even/odd pages** (duplex scanning)
- Rotate CW/CCW · Delete · Insert blank · Duplicate pages
- **Move page Up/Down/Top/Bottom** · Mirror/flip pages
- Convert to grayscale (new file or in-place)
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
- Supports Windows 7, 8, 8.1, 10, and 11 (32-bit and 64-bit)
- Built as a **32-bit executable** so it runs on all supported Windows versions
- High DPI awareness for sharp display on all screens
- Modern dark theme optimized for Windows

## Quick Start

| Option | Action |
|--------|--------|
| **Installer (recommended)** | Download `PDFSuitePro_Installer.exe` → run the wizard → launch from desktop/Start Menu shortcut |
| **Portable** | Download `PDF Suite Pro.exe` → double-click, no installation required |
| **Script installer** | Run `install.bat` as Administrator (if you built the exe yourself) |

The setup wizard installs to `C:\Program Files\PDF Suite Pro`, creates desktop and Start Menu shortcuts, registers an uninstaller in **Apps & Features**, and can launch the app when finished.

## Build from Source

```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name "PDF Suite Pro" pdf_tool.py
```

Output: `dist/PDF Suite Pro.exe`

### Windows 7–compatible build

Windows 7 requires Python 3.8 (32-bit) + PyInstaller 5.x:

```bash
pip install PyMuPDF==1.23.26 Pillow==10.4.0 pyinstaller==5.13.2
pyinstaller --onefile --windowed --name "PDF Suite Pro" pdf_tool.py
```

### Build the installer (NSIS)

```bash
makensis pdfsuite_pro.nsi
```

Output: `PDFSuitePro_Installer.exe`

## Project Structure

```
├── pdf_tool.py                # Main application source (Tkinter, modern UI)
├── PDF Suite Pro.exe          # Pre-built portable executable (32-bit, ~24 MB)
├── PDFSuitePro_Installer.exe  # Setup wizard (built with NSIS)
├── pdfsuite_pro.nsi           # NSIS installer script
├── pdfsuite_pro.iss           # Inno Setup installer script (alternative)
├── install.bat                # Simple batch installer script
├── LICENSE.txt
├── requirements.txt
├── INSTALL.txt
├── INSTALLATION.txt
├── README.md
└── android/                   # Android app (Kivy)
    ├── main.py
    └── buildozer.spec
```

## License

MIT
