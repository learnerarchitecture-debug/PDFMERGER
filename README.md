# PDF Suite Pro

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER  
**Version:** v4.0 — "Mega" release · 60+ tools in 5 tabs

A full-featured PDF & image toolkit for **Windows 7, 8, 8.1, 10 and 11** with a sleek dark UI.
Merge, split, sign, redact, compress, convert, watermark — plus a full **Image Tools** suite and an
**Automation** tab with recipes, watch folders, scheduled runs and a command-line companion
(`PDFSuiteCLI.exe`). Portable or installed.

## What's New in v4.0

- **Reorganized into 5 tabs** — Merge · Split & Edit · PDF Tools · Image Tools · Automation
- **PDF Tools tab** — watermark, header/footer & page numbers, Bates numbering, QR stamps,
  signature studio with click-to-place signing, crop/normalize/trim, N-up, split by size,
  compress-to-target, compare, repair, sanitize, metadata editor, bookmark editor + auto-generate,
  auto-redact patterns (email/phone/card/Aadhaar/PAN/IFSC), mail merge, print
- **Image Tools tab** — compress, convert (JPEG/PNG/WEBP/BMP/TIFF/GIF), resize, rotate/flip,
  grayscale, adjust (brightness/contrast/saturation/sharpness), trim borders, strip EXIF,
  watermark, add border/frame, batch rename, images → PDF, PDF → images, ICO converter
- **Automation tab** — build **recipes** (chains of steps), run them on files/folders,
  **watch folders** that process new files automatically, **scheduled tasks** via Windows Task
  Scheduler, **CSV mail merge**, optional **email reports**, and a log + CSV report after every run
- **Drag & drop** files straight onto the window (PDFs go to Merge, images to Image Tools)
- **Keyboard shortcuts** — Ctrl+O open · Ctrl+M add to merge · Ctrl+S save · Ctrl+P print · Ctrl+F search
- **`PDFSuiteCLI.exe`** — command-line companion for scripting & scheduled runs
- **Update checker** — Help → Check for Updates (GitHub releases)

## Quick Start

| Option | Action |
|--------|--------|
| **Installer (recommended)** | Download `PDFSuitePro_Installer.exe` → run the wizard → launch from desktop/Start Menu |
| **Portable** | Download `PDF Suite Pro.exe` → double-click, no installation required |
| **Script installer** | Run `install.bat` as Administrator (if you built the exe yourself) |

The wizard installs to `C:\Program Files\PDF Suite Pro`, creates desktop and Start Menu shortcuts,
registers an uninstaller in **Apps & Features**, and can launch the app when finished.

## The Five Tabs

### 1. Merge
- Standard merging with per-file page ranges · alternate (interleave) merge
- **Order = the list order** — drag rows or use Move Up / Down / Top / Bottom
- **Right-click a row** — Remove · Duplicate · Move to top/bottom · Open file location
- Insert PDF at a position · add cover page · duplicate entries
- Password protect the result · compression · threaded (UI stays responsive)

### 2. Split & Edit
- Split every page · extract range · split by bookmarks · split by page count · even/odd pages
- Thumbnail view with **drag-to-reorder pages** · rotate · delete · insert blank · duplicate
- Move page Up/Down/Top/Bottom · mirror/flip · to grayscale (new file or in-place)
- **Undo / Redo** for all page actions
- **Search text** (background thread) with thumbnail highlighting
- Extract all images or text · Save As with modifications · Print

### 3. PDF Tools
- **Sign & stamps** — Sign PDF (text block with signer name & date) · Signature studio
  (draw or type → transparent PNG, reusable) · click-to-place signing preview · QR stamps ·
  text watermark (tiled or single) · header/footer & `{page} / {total}` numbering · Bates numbering
- **Organize & pages** — normalize page size (A4/Letter) · auto-trim white margins · crop margins
  (mm) · N-up (pages per sheet) · split by size (MB) · print
- **Compress & optimize** — 4 lossless levels · **smart compress-to-target size** (e.g. "must fit 5 MB")
- **Convert & extract** — PDF → images at chosen DPI · extract text · extract images · grayscale
- **Compare & repair** — visual compare of two PDFs (text diff per page) · repair/rebuild ·
  sanitize (strip JavaScript & embedded files)
- **Security & redaction** — redact text · **auto-redact patterns** (email, phone, card, Aadhaar,
  PAN, IFSC + custom regex) · password protect (AES-256) · remove password · metadata editor
- **Bookmarks** — full bookmark editor (add/edit/delete/demote) · auto-generate from headings
- **Miscellaneous** — add page numbers · flatten annotations · clone open PDF ×2 · rate & review

### 4. Image Tools
- **Works on a list** — Add images · Add folder · remove/clear
- **Compress & convert** — JPEG compression with quality slider · convert to
  JPEG/PNG/WEBP/BMP/TIFF/GIF · create `.ICO` icons
- **Resize & transform** — resize by percent or exact width/height · rotate 90/-90/180 ·
  flip horizontal/vertical · grayscale
- **Enhance & filters** — brightness · contrast · saturation · sharpness sliders ·
  auto-trim borders · strip EXIF & metadata (with auto-rotate) · add border/frame (width + colour)
- **Watermark images** — text watermark, 7 positions, opacity slider
- **Create PDF / export** — images → single PDF (fit image / A4 / Letter) · PDF → images at DPI
- **Batch rename** — pattern placeholders `{name}` `{n}` `{date}`, start number, zero-padding,
  Preview before renaming in place

### 5. Automation
- **Recipes** — a recipe is a JSON list of steps applied to every input file. New / Load / Save as
  / Remove. Steps: 20+ PDF & image operations (see list below) with an Edit params dialog
- **Run** — on selected files or a whole folder; progress dialog; live log; CSV report
  (`automation_report.csv`) in the output folder; option "output next to source"
- **Watch folders** — add folders to watch; when a new PDF/image appears the current recipe runs
  automatically; processed files are moved aside or deleted (optional); all from a background thread
- **Scheduled tasks** — create/delete **Windows Task Scheduler** jobs (daily/weekly) that run a
  saved recipe through `PDFSuiteCLI.exe`
- **CSV mail merge** — fill a template PDF per CSV row: form-field names or `{{column}}` /
  `<<column>>` placeholders
- **Email reports** — optionally send a report by SMTP after each watched file
- **Command line companion** — copy-pasteable CLI examples right in the tab

Recipe operations: Compress PDF · Compress to target size · PDF to grayscale · Add text watermark ·
Header/footer · Bates numbering · Normalize page size · Pages per sheet · Auto-trim white margins ·
Password protect · Remove password · Auto-redact patterns · Sanitize · Repair/rebuild ·
PDF → images · Split by size · Compress image · Convert image format · Resize image ·
Watermark image · Image to grayscale · Enhance image · Strip EXIF · Convert to icon · Rename.

## Command Line (PDFSuiteCLI.exe)

```text
PDFSuiteCLI.exe <command> [options]

PDFs:       merge · compress · grayscale · protect · unlock · watermark · headerfooter ·
            bates · normalize · nup · trim · crop · redact · sanitize · repair ·
            split-size · metadata · bookmarks · sign · qr · pdf2img · img2pdf
Images:     img-compress · img-convert · img-resize · img-grayscale · img-watermark ·
            img-adjust · img-exif · img-border · img-ico · img-trim · img-rename
Automation: recipe · watch · schedule · ops
```

Examples:

```bat
PDFSuiteCLI.exe merge a.pdf b.pdf -o merged.pdf
PDFSuiteCLI.exe compress big.pdf --target 5
PDFSuiteCLI.exe compress big.pdf --level high -o small.pdf
PDFSuiteCLI.exe watermark contract.pdf --text "CONFIDENTIAL" --tiled
PDFSuiteCLI.exe redact scan.pdf --patterns emails,phones,aadhaar
PDFSuiteCLI.exe img-compress *.jpg --quality 55
PDFSuiteCLI.exe img2pdf scan1.png scan2.png -o scan.pdf --page A4
PDFSuiteCLI.exe recipe -r myrecipe.json -d "C:\Scans" -o "C:\Out"
PDFSuiteCLI.exe watch -d "C:\Scans" -r myrecipe.json -o "C:\Out" --interval 10
PDFSuiteCLI.exe schedule --name NightRun -r myrecipe.json -d "C:\Scans" -o "C:\Out" --time 23:00
PDFSuiteCLI.exe ops
```

## Windows Compatibility

- Windows 7, 8, 8.1, 10, 11 — **32-bit and 64-bit**
- Built as a **32-bit executable** (runs everywhere) with high-DPI awareness
- No runtime dependencies — single portable exe

## Build from Source

```bash
pip install -r requirements.txt
python pdf_tool.py                 # run from source
```

Build the executables (PyInstaller):

```bash
pyinstaller --onefile --windowed --name "PDF Suite Pro" pdf_tool.py
pyinstaller --onefile --console  --name "PDFSuiteCLI" pdf_cli.py
```

Output: `dist/PDF Suite Pro.exe` and `dist/PDFSuiteCLI.exe`

For a **Windows 7–compatible** build use Python 3.8 (32-bit):

```bash
pip install PyMuPDF==1.23.26 Pillow==10.4.0 pyinstaller==5.13.2 tkinterdnd2 qrcode
```

Build the installer (NSIS):

```bash
makensis pdfsuite_pro.nsi
```

Output: `PDFSuitePro_Installer.exe`

## Project Structure

```
├── pdf_tool.py                # Main GUI application (customtkinter, 5 tabs)
├── pdf_cli.py                 # Command-line companion → PDFSuiteCLI.exe
├── features_pdf.py            # PDF engine (merge, split, sign, redact, compress, …)
├── features_image.py          # Image engine (compress, convert, resize, watermark, …)
├── automation.py              # Recipes, batch runner, watcher, scheduler, mail merge, SMTP
├── PDF Suite Pro.exe          # Pre-built portable executable (32-bit)
├── PDFSuiteCLI.exe            # Pre-built command-line executable
├── PDFSuitePro_Installer.exe  # Setup wizard (built with NSIS)
├── pdfsuite_pro.nsi           # NSIS installer script
├── pdfsuite_pro.iss           # Inno Setup installer script (alternative)
├── install.bat                # Simple batch installer script
├── requirements.txt           # Python dependencies
├── INSTALLATION.txt           # Step-by-step installation guide
├── LICENSE.txt
├── README.md
└── android/                   # Android app (Kivy)
```

## License

MIT
