# PageDeck

**Creator:** AYUSH GUPTA  
**Repository:** https://github.com/learnerarchitecture-debug/PDFMERGER  
**Version:** v5.1.3 — auto-updates, no token needed (public repo) · 100+ tools in 6 tabs

PageDeck (formerly *PDF Suite Pro*) is a full-featured PDF & image toolkit for
**Windows 7, 8, 8.1, 10 and 11** with a sleek dark UI. Merge, edit, sign, redact,
compress, convert, clean up scans — plus a full **Image editor suite** and an
**Automation** tab with recipes, watch folders, scheduled runs and a command-line
companion (`PageDeckCLI.exe`). Portable or installed.

## What's New in v5.1.3

- Fixed the auto-update install step: starting the downloaded setup from the
  app could fail with **"WinError 740 — the requested operation requires
  elevation"**. The app now launches it through the Windows shell, so the
  normal permission prompt appears and the setup can run

## What's New in v5.1.2

- The update settings window no longer shows a GitHub token box for normal
  (public-repo) users — only the two toggles remain. A token stored by an
  older version still appears so it can be reviewed or cleared
- Updates are now robust against a stale or invalid stored token: checks and
  downloads automatically retry without it

## What's New in v5.1.1

- Fixed the installer text — the welcome page and the window title bar used to
  show a placeholder ("Welcome to NAME Setup"); they now say *PageDeck*
- The installer now reports the right version to Windows (Add/Remove Programs
  previously listed 5.0)

## What's New in v5.1

- **Automatic updates** — when a new version is published, PageDeck now
  **downloads the installer by itself** and shows the release notes with a
  progress bar. One click (*Restart & Install*) applies it. Toggle under
  **Help → Update settings…**
- **No token needed any more** — the repository is now **public**, so update
  checks and downloads work out of the box on every PC. The token field is
  hidden for everyone now (it only re-appears if a token was ever stored)
- Fixed the release download for public repositories (it previously expected a
  token and would have saved the wrong file).

## What's New in v5.0

- **New name — PageDeck.** Everything was renamed: `PageDeck.exe`, `PageDeckCLI.exe`,
  `PageDeck_Installer.exe`. Upgrading is automatic — the installer removes a previous
  "PDF Suite Pro" installation, and your settings, signatures, recent files and
  automation recipes carry over on first launch.
- **New Home tab** — quick actions for the 8 most used tools, recent files and a
  rate & review / about / update-check panel.
- **Reorganized into 6 tabs** — **Home · Organize · Edit PDF · Convert & Secure ·
  Images · Automation**, with Organize split into *Merge files* and *Pages & Split*
  sub-tabs. Every tool now lives under a clear category.
- **PDF editing is here** — typewriter text, fill form fields, highlight phrases,
  find & replace text, and **draw redaction areas** directly on the pages.
- **Smart split** — split every N pages, at a keyword, at blank separator pages, or
  even/odd — on top of the classic split tools.
- **OCR** — make scans searchable (needs free Tesseract; PageDeck finds it
  automatically and links you to the download if it's missing).
- **Word / Excel / PPT → PDF** — via LibreOffice (auto-detected, same guidance).
- **PDF attachments** — list, add and extract files embedded inside a PDF.
- **Image clean-up tools** — scan cleanup (straighten + whiten + despeckle),
  background remover, 2x–4x upscale, batch crop with the same margins.
- **Image looks & sizes** — one-click filters (B&W · Warm · Cool · Vintage ·
  Vignette · Clarity), social-media export presets (Instagram, Story/Reels,
  YouTube, Facebook, X, WhatsApp, LinkedIn) and a **collage maker**.
- **Image privacy** — EXIF viewer and one-click *remove GPS location*.
- **Automation grew to 40+ recipe operations** including all of the above.
- **`PageDeckCLI.exe`** learned 17 new commands (OCR, replace, highlight,
  typewriter, attach, smart splits, image clean-up & more).

## What's New in v4.1

- **Modern app icon** — gradient document icon on the desktop shortcut, taskbar,
  title bar and the installer
- **Built-in auto-updater** — checks GitHub silently at startup (Help → Check for
  Updates for a manual check), shows release notes, **downloads the installer and
  runs it** — no manual downloading
- **"Don't remind me about this version"** option · **private-repo support** with a
  GitHub access token (Help → Update settings…), stored only on this computer

## Quick Start

| Option | Action |
|--------|--------|
| **Installer (recommended)** | Download `PageDeck_Installer.exe` → run the wizard → launch from desktop/Start Menu |
| **Portable** | Download `PageDeck.exe` → double-click, no installation required |
| **Script installer** | Run `install.bat` as Administrator (if you built the exe yourself) |

The wizard installs to `C:\Program Files\PageDeck`, creates desktop and Start Menu
shortcuts, registers an uninstaller in **Apps & Features**, and can launch the app
when finished.

**Updating:** PageDeck checks GitHub for new versions automatically at startup
(the repository is public, so no configuration or token is needed). When a new
version exists, the app downloads the installer for you and asks one question —
*Restart & Install* — then it closes and the setup updates it (Windows asks
for your permission first — allow it). Manual check:
**Help → Check for Updates** or the button on the Home tab. Downloads can be
turned off under **Help → Update settings…**.

## The Six Tabs

### 1. Home
- **Quick actions** — one-click Compress PDF · Merge PDFs · Images → PDF ·
  PDF → Images · OCR scan · Clean document photo · Remove background ·
  Social media export
- **Recent files** — double-click to add to the merge list · open folder · clear
- **More** — Rate & Review · About PageDeck · Check for updates · jump to Automation

### 2. Organize
**Merge files** — standard merging with per-file page ranges · alternate
(interleave) merge · **order = the list order** (drag rows or Move Up/Down/Top/Bottom) ·
right-click a row to remove/duplicate/reveal · insert PDF at a position · cover page ·
password protect the result · compression · threaded (the UI stays responsive)

**Pages & Split** — thumbnail view with **drag-to-reorder pages** · rotate · delete ·
insert blank · duplicate · move page Up/Down/Top/Bottom · mirror/flip · grayscale
(new file or in-place) · **Undo / Redo** for all page actions · **search text** with
thumbnail highlighting · extract all images or text · Save As · print, plus:
- Split every page · extract range · split by bookmarks · even/odd
- **Smart split** — every N pages · at a keyword · at blank pages · even-odd

### 3. Edit PDF
- **Sign & stamps** — Sign PDF (text block with signer name & date) · Signature
  studio (draw or type → transparent PNG, reusable) · click-to-place signing
  preview · QR stamps · text watermark (tiled or single) · header/footer &
  `{page} / {total}` numbering · Bates numbering
- **Mark up & find** — **Typewriter** (add text anywhere) · **Fill form fields** ·
  **Highlight a phrase** · **Find & replace text** (retypes at the same spot)
- **Redaction & privacy** — redact text · **auto-redact patterns** (email, phone,
  card, Aadhaar, PAN, IFSC + custom regex) · **draw redaction areas on pages** ·
  metadata editor · remove metadata
- **Bookmarks** — full bookmark editor (add/edit/delete/demote) · auto-generate
  from headings
- **Extras** — add page numbers · flatten annotations · clone open PDF ×2
- **Organize & pages** (shared) — normalize page size (A4/Letter) · auto-trim white
  margins · crop margins (mm) · N-up (pages per sheet) · print

### 4. Convert & Secure
- **Compress & optimize** — 4 lossless levels · **smart compress-to-target size**
  (e.g. "must fit 5 MB") · split by size (MB)
- **Convert & extract** — PDF → images at chosen DPI · extract text · extract
  images · convert to grayscale · **add attachment inside PDF** · **extract
  attachments**
- **OCR & Office** — **OCR scan → searchable PDF** (Tesseract) · **Word / Excel /
  PPT → PDF** (LibreOffice)
- **Security** — password protect (AES-256) · remove password · sanitize (strip
  JavaScript & embedded files)
- **Compare & repair** — visual compare of two PDFs (text diff per page) ·
  repair/rebuild

### 5. Images
- **Works on a list** — Add images · Add folder · remove/clear
- **Compress & convert** — JPEG compression with quality slider · convert to
  JPEG/PNG/WEBP/BMP/TIFF/GIF · create `.ICO` icons
- **Resize & transform** — resize by percent or exact width/height · rotate
  90/-90/180 · flip horizontal/vertical · grayscale
- **Clean up & fix** — scan cleanup (straighten + whiten + despeckle) · remove
  background (transparent PNG) · upscale 2x–4x · crop the same margins (%)
- **Enhance & filters** — brightness · contrast · saturation · sharpness ·
  auto-trim borders · strip EXIF & metadata · add border/frame
- **Watermark images** — text watermark, 7 positions, opacity slider
- **Filters & looks** — B&W · Warm · Cool · Vintage · Vignette · Clarity, applied
  to the whole list in one click
- **Social & collage** — social-media export presets (Instagram post/portrait,
  Story/Reels, YouTube thumbnail, Facebook cover, X/Twitter, WhatsApp status,
  LinkedIn) · collage maker (grid, spacing, rounded corners, background colour)
- **EXIF & privacy** — view EXIF of the selected image · remove GPS location
- **Create PDF / export** — images → single PDF (fit / A4 / Letter) · PDF → images
- **Batch rename** — placeholders `{name}` `{n}` `{date}`, start number,
  zero-padding, preview before renaming in place

### 6. Automation
- **Recipes** — a recipe is a JSON list of steps applied to every input file. New /
  Load / Save as / Remove. **40+ PDF & image operations** with an Edit-params dialog
- **Run** — on selected files or a whole folder; progress dialog; live log; CSV
  report (`automation_report.csv`) in the output folder; optional "output next to
  source"
- **Watch folders** — when a new PDF/image appears the current recipe runs
  automatically in a background thread; processed files are moved aside or deleted
- **Scheduled tasks** — create/delete **Windows Task Scheduler** jobs (daily/weekly)
  that run a saved recipe through `PageDeckCLI.exe`
- **CSV mail merge** — fill a template PDF per CSV row: form-field names or
  `{{column}}` / `<<column>>` placeholders
- **Email reports** — optionally send a report by SMTP after each watched file
- **Command line companion** — copy-pasteable CLI examples right in the tab

Recipe operations: Compress PDF · Compress to target size · PDF to grayscale ·
Text watermark · Header/footer · Bates numbering · Normalize page size · Pages per
sheet · Auto-trim white margins · Password protect · Remove password · Auto-redact
patterns · Sanitize · Repair/rebuild · PDF → images · Split by size · **Split at
keyword** · **Split at blank pages** · **OCR scan** · **Highlight phrase** ·
**Find & replace** · **Typewriter text** · **Attach file** · **Office → PDF** ·
Compress image · Convert image format · Resize image · Watermark image · Image to
grayscale · Enhance image · Strip EXIF · Convert to icon · Rename · **Scan
cleanup** · **Remove background** · **Social export** · **Filter/look** ·
**Upscale** · **Batch crop** · **Remove GPS**.

## Optional external tools

PageDeck detects these automatically and shows a friendly message with the
download page if a feature needs one:

| Feature | Needs | Get it |
|---------|-------|--------|
| OCR scan → searchable PDF | **Tesseract OCR** | github.com/UB-Mannheim/tesseract (Windows installer) |
| Word / Excel / PPT → PDF | **LibreOffice** | libreoffice.org (any recent version) |

Everything else works out of the box — no runtime dependencies.

## Command Line (PageDeckCLI.exe)

```text
PageDeckCLI.exe <command> [options]

PDFs:       merge · compress · grayscale · protect · unlock · watermark · headerfooter ·
            bates · normalize · nup · trim · crop · redact · sanitize · repair ·
            split-size · metadata · bookmarks · sign · qr · pdf2img · img2pdf ·
            ocr · office2pdf · replace · highlight · typewriter · attach ·
            extract-attach · split-keyword · split-blank
Images:     img-compress · img-convert · img-resize · img-grayscale · img-watermark ·
            img-adjust · img-exif · img-border · img-ico · img-trim · img-rename ·
            img-scan · img-nobg · img-upscale · img-filter · img-social ·
            img-collage · img-crop · img-nogps
Automation: recipe · watch · schedule · ops
```

Examples:

```bat
PageDeckCLI.exe merge a.pdf b.pdf -o merged.pdf
PageDeckCLI.exe compress big.pdf --target 5
PageDeckCLI.exe watermark contract.pdf --text "CONFIDENTIAL" --tiled
PageDeckCLI.exe redact scan.pdf --patterns emails,phones,aadhaar
PageDeckCLI.exe ocr scan.pdf --lang eng
PageDeckCLI.exe replace invoice.pdf --find "Draft" --replace "Final"
PageDeckCLI.exe highlight notes.pdf --phrase "ACTION ITEM"
PageDeckCLI.exe split-keyword binder.pdf --keyword "SECTION"
PageDeckCLI.exe img-scan photo.jpg
PageDeckCLI.exe img-social *.jpg --preset "Instagram post"
PageDeckCLI.exe img2pdf scan1.png scan2.png -o scan.pdf --page A4
PageDeckCLI.exe recipe -r myrecipe.json -d "C:\Scans" -o "C:\Out"
PageDeckCLI.exe watch -d "C:\Scans" -r myrecipe.json -o "C:\Out" --interval 10
PageDeckCLI.exe schedule --name NightRun -r myrecipe.json -d "C:\Scans" -o "C:\Out" --time 23:00
PageDeckCLI.exe ops
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
pyinstaller --noconfirm --clean "PageDeck.spec"
pyinstaller --onefile --console --noconfirm --name "PageDeckCLI" --icon app_icon.ico pdf_cli.py
```

Output: `dist/PageDeck.exe` and `dist/PageDeckCLI.exe`

For a **Windows 7–compatible** build use Python 3.8 (32-bit):

```bash
pip install PyMuPDF==1.23.26 Pillow==10.4.0 pyinstaller==5.13.2 tkinterdnd2 qrcode
```

Build the installer (NSIS):

```bash
makensis pagedeck.nsi
```

Output: `PageDeck_Installer.exe`

### Publishing an update (this is what the auto-updater sees)

1. Bump `APP_VERSION` in `pdf_tool.py` (e.g. `"5.1"`), commit and push.
2. Create and push a tag: `git tag v5.1` then `git push origin v5.1`.
3. GitHub Actions (`.github/workflows/build-release.yml`) builds the app, the CLI and
   the installer and attaches all three to a new **Release** for that tag.
4. Installed copies of the app find the release on their next startup check and offer
   to download and install it (or check manually via **Help → Check for Updates**).

The repository is public, so users need no token and the update window shows
no token box. If you ever fork it as a private repo, a token can be stored in
the app's settings file (`%APPDATA%\PageDeck\settings.json`) — the update
window only shows a token box when one is already stored.

## Project Structure

```
├── pdf_tool.py                # Main GUI application (customtkinter, 6 tabs)
├── pdf_cli.py                 # Command-line companion → PageDeckCLI.exe
├── features_pdf.py            # PDF engine (merge, split, sign, redact, compress, …)
├── features_image.py          # Image engine (compress, convert, resize, watermark, …)
├── automation.py              # Recipes, batch runner, watcher, scheduler, mail merge, SMTP
├── app_icon.ico               # Application icon (desktop / taskbar / installer)
├── make_icon.py               # Icon generator script
├── PageDeck.exe               # Pre-built portable executable (32-bit)
├── PageDeckCLI.exe            # Pre-built command-line executable
├── PageDeck_Installer.exe     # Setup wizard (built with NSIS)
├── PageDeck.spec              # PyInstaller spec (app)
├── PageDeckCLI.spec           # PyInstaller spec (CLI)
├── pagedeck.nsi               # NSIS installer script
├── pagedeck.iss               # Inno Setup installer script (alternative)
├── install.bat                # Simple batch installer script
├── requirements.txt           # Python dependencies
├── INSTALLATION.txt           # Step-by-step installation guide
├── LICENSE.txt
├── README.md
└── android/                   # Android app (Kivy)
```

## License

MIT
