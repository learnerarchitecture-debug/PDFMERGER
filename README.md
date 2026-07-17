# PDF Merger & Splitter

A Windows desktop application to merge and split PDF files with a simple GUI.

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
- **Dark Mode** — Toggle dark/light theme
- **Drag & Drop Reorder** — Reorder files in the merge list by dragging
- **Recent Files** — Quick access to recently opened PDFs

## Screenshots

*(Add screenshots here)*

## Requirements

- Windows 10 or later (64-bit)
- No additional software required — the executable is self-contained

## Installation

See [INSTALLATION.txt](INSTALLATION.txt) for detailed instructions.

## Usage

### Merge Tab
1. Click **Add PDF(s)** to select files
2. Select a file and enter a **page range** (e.g. `1-5,7,9-12`) or leave as `all`
3. Drag items to reorder
4. Set **output filename**, optional **password**, and **compress** option
5. Click **Merge!**

### Split Tab
1. Click **Open PDF** to load a file
2. Enter a **password** if the PDF is encrypted, then click **Unlock**
3. Click thumbnails to **select pages**
4. Use **Rotate CW/CCW** or **Delete Selected** to modify pages
5. Choose an action:
   - **Extract** — Save selected page range to a new file
   - **Split All Pages** — Save each page as a separate PDF
   - **Split by Bookmarks** — Save each chapter as a separate PDF
   - **Save As** — Save the modified document

## Building from Source

```bash
pip install PyMuPDF Pillow pyinstaller
pyinstaller --onefile --noconsole --name "PDFMerger" --hidden-import fitz pdf_tool.py
```

## License

MIT
