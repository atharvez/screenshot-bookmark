# Screenshot Bookmark - Browser Extension

A full-featured Chrome and Edge browser extension that captures screenshots, preserves real webpage metadata (URL, page title, favicon), and organizes your bookmarks with OCR and AI.

## Features

- 📸 **Capture Visible Tab**: One-click full viewport screenshot with OCR extraction
- ✂️ **Capture Custom Area**: Interactive on-page rectangle selector with live dimensions
- ⭐ **Quick Bookmark**: Instant URL + title bookmarking without needing a screenshot
- 🧠 **Smart Metadata & OCR**: Automatically extracts text, identifies titles, descriptions, and tags via Gemini AI (or local heuristic extraction)
- ★ **Bookmarked Indicator**: Detects if the current active tab is already bookmarked
- 🔍 **Instant Full-Text Search**: Live search across titles, URLs, tags, and OCR content
- 🏷️ **Tag Management**: Clickable tag chips for quick filtering and organization
- 📋 **One-Click Actions**: Open links in new tabs, copy URLs, and preview screenshot thumbnails
- ⚙️ **Configurable Backend**: Easily customize the API server URL in the popup settings
- 🖱️ **Context Menu Integration**: Right-click anywhere to quick save, screenshot tab, or screenshot area
- ⌨️ **Keyboard Shortcuts**: Global shortcuts for lightning-fast capture

---

## Installation

### 1. Start the Backend API Server

Ensure the Python dependencies are installed and start the server:

```bash
# From the project root
pip install -e .

# Run the API server
screenshot-bookmark-server
# Or: python -m screenshot_bookmark.server
```

The API will be available at `http://localhost:8000` (Web UI at `http://localhost:8000/`).

> [!NOTE]
> The server runs out of the box with local heuristic extraction. To enable Gemini AI analysis, set `GOOGLE_API_KEY=your_key` in a `.env` file or your environment variables.

### 2. Install the Extension in Your Browser

1. Open Chrome or Edge:
   - Chrome: Navigate to `chrome://extensions/`
   - Edge: Navigate to `edge://extensions/`
2. Enable **Developer mode** (toggle in the top-right corner).
3. Click **Load unpacked**.
4. Select the `extension/` folder inside this repository.
5. Pin the **Screenshot Bookmark** icon to your browser toolbar!

---

## Usage

### Keyboard Shortcuts

- `Ctrl+Shift+S` (or `Cmd+Shift+S` on Mac) — **Capture visible tab screenshot bookmark**
- `Ctrl+Shift+A` (or `Cmd+Shift+A` on Mac) — **Select custom area on page to bookmark**
- `Ctrl+Shift+B` (or `Cmd+Shift+B` on Mac) — **Quick bookmark current page (URL + title)**

### Extension Popup

1. Click the extension icon in your toolbar.
2. Current active page details (title, domain, favicon) load automatically.
3. Choose an action:
   - **Quick Save**: Saves the page immediately.
   - **Screenshot Tab**: Captures viewport, runs OCR, and saves bookmark.
   - **Area**: Activates the crosshair selector on the webpage.
4. Add custom tags or personal notes in the expandable details section.
5. Browse or search through your bookmarks directly inside the popup.
6. Click any bookmark title to navigate to it, click its thumbnail to preview the screenshot, or click 📋 to copy the URL.

### Context Menu

Right-click anywhere on any webpage to access:
- *Quick Bookmark this page*
- *Capture Tab Screenshot Bookmark*
- *Capture Area Screenshot Bookmark*
- *Bookmark Selected Text*

---

## Configuration

Click the **⚙️ (Settings)** icon in the extension popup header to change your API server URL (default: `http://localhost:8000`).

---

## File Structure

```
extension/
├── manifest.json         # Extension configuration (Manifest V3)
├── background.js         # Service worker (shortcuts, context menus, API sync)
├── content.js            # Content script (interactive area selector & metadata)
├── popup/
│   ├── popup.html        # Modern popup UI
│   ├── popup.css         # Styling & responsive layout
│   └── popup.js          # Popup interactivity & API calls
└── icons/                # Extension icons (16px, 32px, 48px, 128px)
    ├── icon16.png
    ├── icon32.png
    ├── icon48.png
    └── icon128.png
```

---

## Troubleshooting

### "Server: Offline" in popup
- Verify that `screenshot-bookmark-server` is running in your terminal.
- Visit `http://localhost:8000/health` in your browser to verify connectivity.
- Check the API URL in extension settings (gear icon) matches your server host and port.

### OCR text not appearing
- Check if Tesseract OCR is installed on your system (`tesseract --version`).
- On Windows, typical installation is `C:\Program Files\Tesseract-OCR\tesseract.exe`.
- When Tesseract is not installed, the tool gracefully falls back to metadata extracted from page titles and URLs.

---

## License

MIT License. See [LICENSE](../LICENSE) for details.
