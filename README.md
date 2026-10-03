# Screenshot Bookmark

<p align="center">
  <b>A local-first visual bookmarking ecosystem powered by OCR and AI.</b><br>
  Capture screenshots, select custom webpage regions, or quick-save URLs into a searchable, smart-tagged personal library.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/License-MIT-blue.svg" alt="License: MIT">
  <img src="https://img.shields.io/badge/Python-3.9%2B-blue" alt="Python 3.9+">
  <img src="https://img.shields.io/badge/Manifest-V3-success" alt="Manifest V3">
  <img src="https://img.shields.io/badge/Storage-SQLite%20FTS5-orange" alt="SQLite FTS5">
  <img src="https://img.shields.io/badge/AI-Google%20Gemini-4285F4" alt="Google Gemini">
</p>

---

## Highlights

- **Chrome & Edge Browser Extension (Manifest V3)**:
  - **Quick Save**: 1-click URL & metadata bookmarking (`Ctrl+Shift+B`).
  - **Full Tab Screenshot**: One-click visual capture with instant OCR (`Ctrl+Shift+S`).
  - **Interactive Area Capture**: Draw a crop box on the webpage with real-time dimension badges (`Ctrl+Shift+A`).
  - **Context Menu**: Right-click on any page, image, or selected text to save instantly.
  - **Active Tab Detection**: Automatically checks if current webpage is already bookmarked.
  - **Live Search & Filter**: Instant debounce search with clickable tag chips in the popup.
- **Instant Full-Text Search (SQLite FTS5)**: Fast BM25 full-text search across titles, URLs, OCR extracted text, and tags.
- **Smart AI & Heuristic Analysis**: Extracts titles, domains, descriptions, and tags using Google Gemini API, with built-in rule-based heuristic extraction when offline or without an API key.
- **Modern Web Dashboard**: Built-in responsive dashboard at `http://localhost:8000` with lightbox screenshot viewer, tag filters, database statistics, and bookmark editing.
- **Folder Watcher & CLI**: Command-line tool to watch folders for screenshots or manage bookmarks from terminal.
- **Local-First & Private**: All data and screenshots stay stored safely on your machine in SQLite.
- **Universal Export**: Export all bookmarks into Netscape HTML format (importable into Chrome, Edge, Firefox, Safari) or JSON.

---

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone https://github.com/atharvez/screenshot-bookmark.git
cd screenshot-bookmark

# Install dependencies (development mode)
pip install -e .
```

### 2. Start the Backend API Server

```bash
screenshot-bookmark-server
# Or: python -m screenshot_bookmark.server
```

The server starts at `http://localhost:8000`. You can now open `http://localhost:8000/` in your browser to view the Web Dashboard!

### 3. Install the Browser Extension

1. Open **Chrome** or **Edge** and go to `chrome://extensions/` (or `edge://extensions/`).
2. Toggle on **Developer mode** in the top right.
3. Click **Load unpacked**.
4. Select the `extension/` directory from this repository.
5. Pin the **Screenshot Bookmark** icon to your toolbar!

---

## Extension Shortcuts

| Shortcut | Description |
| :--- | :--- |
| `Ctrl+Shift+B` / `Cmd+Shift+B` | **Quick Bookmark** current webpage |
| `Ctrl+Shift+S` / `Cmd+Shift+S` | **Capture full visible tab** screenshot bookmark |
| `Ctrl+Shift+A` / `Cmd+Shift+A` | **Capture selected area** on webpage |

---

## Configuration & Environment

Configuration is optional. The application works out of the box with local heuristic analysis. To enable Gemini AI analysis, set:

```bash
# Create a .env file or export environment variables
GOOGLE_API_KEY=your_gemini_api_key_here
```

Get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

Additional optional variables in `.env`:
- `HOST=0.0.0.0`
- `PORT=8000`
- `DB_PATH=~/.screenshot-bookmark/bookmarks.db`
- `UPLOAD_DIR=~/.screenshot-bookmark/uploads`
- `GEMINI_MODEL=gemini-2.0-flash`
- `MOCK_OCR=false`

---

## CLI Usage

```bash
# Initialize database
screenshot-bookmark init

# Add a screenshot file manually
screenshot-bookmark add path/to/screenshot.png

# Search bookmarks
screenshot-bookmark search "machine learning"

# Search by tag
screenshot-bookmark search --tag programming

# List recent bookmarks
screenshot-bookmark list --limit 10

# Database stats
screenshot-bookmark stats

# Watch folder for new screenshots automatically
screenshot-bookmark watch ~/Pictures/Screenshots
```

---

## Project Architecture

```
screenshot-bookmark/
|-- extension/                  # Chrome / Edge Extension (Manifest V3)
|   |-- manifest.json           # Permissions, shortcuts, actions
|   |-- background.js           # Service worker & OffscreenCanvas cropping
|   |-- content.js              # Interactive area selector & metadata extractor
|   |-- popup/                  # Extension popup UI (HTML/CSS/JS)
|   \-- icons/                  # 16px, 32px, 48px, 128px PNG icons
|-- src/screenshot_bookmark/    # Python Backend & Core Package
|   |-- analyzer.py             # Gemini API & heuristic fallback extraction
|   |-- cli.py                  # Command-line interface
|   |-- database.py             # SQLite + FTS5 full-text storage
|   |-- ocr.py                  # Tesseract OCR engine
|   |-- server.py               # Uvicorn server entry point
|   |-- watcher.py              # File system watcher (watchdog)
|   |-- web.py                  # FastAPI REST API endpoints & image serving
|   \-- static/                 # Web UI Dashboard (index.html)
|-- tests/                      # Automated test suite (Pytest)
|-- create_icons.py             # Icon generation utility
\-- pyproject.toml              # Package configuration
```

---

## Testing

Run the automated test suite with pytest:

```bash
pytest
```

---

## License

Distributed under the [MIT License](LICENSE). Copyright (c) 2024-2026 Atharva Desai.
