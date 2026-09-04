# Screenshot Bookmark

A local-first, open-source tool that automatically turns your screenshots into searchable bookmarks using OCR and AI.

## Features

- 📸 **Automatic OCR**: Extracts text from screenshots using Tesseract or EasyOCR
- 🤖 **AI Analysis**: Uses Claude API to extract titles, URLs, descriptions, and tags
- 🔍 **Full-text Search**: Search your bookmarks using FTS5 (Fast full-text search)
- 🏷️ **Smart Tagging**: Automatically generates relevant tags for categorization
- 👁️ **Folder Watching**: Automatically processes new screenshots as they appear
- 💾 **Local Storage**: All data stored locally in SQLite - no cloud dependencies
- ⚡ **Fast & Lightweight**: Optimized for performance on any machine including Raspberry Pi

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/screenshot-bookmark.git
cd screenshot-bookmark

# Install in development mode
pip install -e .

# Or install dependencies directly
pip install anthropic pytesseract pillow watchdog
```

## Usage

### Initialize the database
```bash
screenshot-bookmark init
```

### Add a screenshot manually
```bash
screenshot-bookmark add path/to/screenshot.png
```

### Search your bookmarks
```bash
# Search by text
screenshot-bookmark search "neural network tutorial"

# Search by tag
screenshot-bookmark search --tag programming

# List recent bookmarks
screenshot-bookmark list --limit 10
```

### Watch a folder for new screenshots
```bash
screenshot-bookmark watch ~/Pictures/Screenshots
```

### View statistics
```bash
screenshot-bookmark stats
```

## Configuration

The tool uses the following environment variables for configuration:
- `ANTHROPIC_API_KEY`: Your Claude API key (required for AI analysis)
- Or pass `--api-key` to any command

## How it Works

1. **Detection**: Watches a folder for new screenshot files (PNG, JPG, etc.)
2. **OCR**: Extracts text from the screenshot using Tesseract or EasyOCR
3. **AI Analysis**: Sends the OCR text to Claude API to extract:
   - Title: Main headline or title
   - URL: Any website links visible
   - Description: Brief summary of content
   - Tags: Relevant categorical tags
4. **Storage**: Saves everything to a local SQLite database with FTS5 search
5. **Search**: Find your bookmarks later by text, tag, or browsing recent items

## Requirements

- Python 3.9+
- Tesseract OCR (for best results) or EasyOCR
- Claude API key (for AI analysis)

### Installing Tesseract OCR

#### Ubuntu/Debian
```bash
sudo apt-get install tesseract-ocr
```

#### macOS (Homebrew)
```bash
brew install tesseract
```

#### Windows
Download from: https://github.com/UB-Mannheim/tesseract/wiki

## Development

### Running Tests
```bash
pytest
```

### Code Formatting
```bash
black src/
ruff check src/
mypy src/
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Acknowledgements

- Built with [Anthropic's Claude API](https://www.anthropic.com/)
- Uses [Tesseract OCR](https://github.com/tesseract-ocr/tesseract)
- Uses [Watchdog](https://github.com/gorakhargosh/watchdog) for file system watching