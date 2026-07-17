# PDF Suite Pro

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER

A full-featured PDF and image utility for **Windows** with a modern dark UI.

## Features

### Merge
- Standard PDF merging with per-file page ranges
- **Alternate merge** — interleave pages from multiple files
- Insert PDF at specific position
- Add cover page
- Duplicate selected files
- Drag-and-drop reorder
- Password protect output
- Compression

### Split
- Split every page to separate files
- Extract custom page range (e.g. `1,3,5-7`)
- **Split by bookmarks** (chapters)
- **Split by page count** (every N pages)
- **Split even/odd pages** (for duplex scanning)
- **Extract all images** from PDF
- **Extract all text** to .txt file
- Rotate pages (CW/CCW)
- Delete pages
- Insert blank pages
- Duplicate pages
- Mirror/flip pages
- Convert to grayscale
- Search text within PDF
- Save As with modifications

### Tools
- **Digital Signature** — Sign any PDF with styled "Digitally Signed by AYUSH GUPTA" box with date
- **Image Compression** — Reduce JPG/PNG file size (adjustable quality 1-100)
- **Images to PDF** — Combine multiple images into a single PDF
- **PDF Compression** — 4 levels (Low/Medium/High/Max with image downsampling)
- **Redact Text** — Permanently remove text from PDF
- **Remove Metadata** — Strip all author/date/metadata
- **Password Protect** — AES-256 encrypt PDFs
- **Remove Password** — Decrypt password-protected PDFs
- **Add Page Numbers** — Auto-number all pages
- **Flatten PDF** — Merge all layers/annotations

## Quick Start

1. Download or build `dist/PDFSuite.exe`
2. Double-click `PDFSuite.exe` — no installation needed
3. Right-click → Create shortcut on desktop for quick access

## Build from Source

```bash
pip install PyMuPDF
pyinstaller --onefile --noconsole --name "PDFSuite" --hidden-import fitz pdf_tool.py
```

## Project Structure

```
├── pdf_tool.py              # Main application source
├── dist/PDFSuite.exe        # Pre-built executable
├── android/                 # Android app (Kivy)
├── requirements.txt
├── README.md
└── INSTALLATION.txt
```

## License

MIT
