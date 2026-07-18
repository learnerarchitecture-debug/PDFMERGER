# PDF Suite Pro

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER  
**Version:** v2.2

A full-featured PDF utility for **Windows** with a modern dark UI — merge, split, sign, compress, redact, and 30+ tools. No installation needed.

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
- **Digital Signature** — Styled "Digitally Signed by AYUSH GUPTA" box with date
- **Image Compression** — JPG/PNG quality 1–100
- **Images to PDF** — Combine multiple images into one PDF
- **PDF Compression** — 4 levels with image downsampling
- **Redact Text** — Permanently remove text
- **Remove Metadata** · **Password Protect** (AES-256) · **Remove Password**
- **Add Page Numbers** · **Flatten PDF** · **Rate & Review** dialog (1–5 stars)

### Android
- Merge & split PDFs on your phone (Kivy-based APK)

## Quick Start

| Step | Action |
|------|--------|
| 1 | Download `PDF Suite Pro.exe` from the repo |
| 2 | Double-click — **no installation required** |
| 3 | Right-click → Create shortcut on desktop |

## Build from Source

```bash
pip install -r requirements.txt
pyinstaller --onefile --noconsole --name "PDF Suite Pro" pdf_tool.py
```

Output: `dist/PDF Suite Pro.exe`

## Project Structure

```
├── pdf_tool.py              # Main application source (Tkinter)
├── PDF Suite Pro.exe        # Pre-built executable (40 MB)
├── android/                 # Android app (Kivy)
│   ├── main.py
│   └── buildozer.spec
├── requirements.txt
├── INSTALL.txt
├── INSTALLATION.txt
└── README.md
```

## License

MIT
