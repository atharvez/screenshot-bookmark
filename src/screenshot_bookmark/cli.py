"""Command-line interface for screenshot-bookmark."""
import argparse
import sys
import logging
from pathlib import Path
from typing import Optional
import time

from .database import Database, Bookmark
from .ocr import OCRProcessor
from .analyzer import ClaudeAnalyzer
from .watcher import FolderWatcher

logger = logging.getLogger(__name__)

def setup_logging(verbose: bool = False):
    """Setup logging configuration."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

def process_screenshot(image_path: str, db: Database, analyzer: ClaudeAnalyzer,
                      ocr_processor: Optional[OCRProcessor] = None) -> bool:
    """
    Process a single screenshot through the pipeline.

    Args:
        image_path: Path to the screenshot image
        db: Database instance
        analyzer: Claude analyzer instance
        ocr_processor: Optional OCR processor (will create if not provided)

    Returns:
        True if processing succeeded, False otherwise
    """
    try:
        logger.info(f"Processing screenshot: {image_path}")

        # Check if already processed
        existing = db.get_bookmark_by_path(image_path)
        if existing:
            logger.info(f"Screenshot already processed: {image_path}")
            return True

        # Extract text via OCR
        if ocr_processor is None:
            ocr_processor = OCRProcessor()

        logger.debug("Extracting text via OCR...")
        ocr_text = ocr_processor.extract_text(image_path)
        if not ocr_text.strip():
            logger.warning(f"No text extracted from {image_path}")
            # Still create a bookmark with empty OCR text
            ocr_text = ""

        # Analyze with Claude
        logger.debug("Analyzing with Claude API...")
        metadata = analyzer.analyze_ocr_text(ocr_text, image_path)

        # Create bookmark
        bookmark = Bookmark(
            image_path=image_path,
            ocr_text=ocr_text,
            title=metadata.title,
            url=metadata.url,
            description=metadata.description,
            tags=metadata.tags,
            file_hash=""  # Could compute hash here for deduplication
        )

        # Save to database
        bookmark_id = db.add_bookmark(bookmark)
        logger.info(f"Saved bookmark with ID {bookmark_id}: {metadata.title or '[No title]'}")
        return True

    except Exception as e:
        logger.exception(f"Failed to process screenshot {image_path}: {e}")
        return False

def cmd_init(args):
    """Initialize the application."""
    db_path = Path(args.db_path).expanduser()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    db = Database(str(db_path))
    print(f"Initialized database at {db.db_path}")
    return 0

def cmd_add(args):
    """Add a screenshot to the bookmark database."""
    db = Database(args.db_path)
    analyzer = ClaudeAnalyzer(api_key=args.api_key)
    # Get args with defaults if they don't exist (for subcommand compatibility)
    ocr_lang = getattr(args, 'ocr_lang', 'eng')
    mock_ocr = getattr(args, 'mock_ocr', False)
    ocr_processor = OCRProcessor(lang=ocr_lang, mock=mock_ocr)

    success = process_screenshot(args.image_path, db, analyzer, ocr_processor)
    return 0 if success else 1

def cmd_search(args):
    """Search bookmarks."""
    db = Database(args.db_path)

    if args.tag:
        # Search by tag - get all bookmarks and filter by tag
        # This is simplified; in production you might want a better tag search
        bookmarks = db.get_recent_bookmarks(limit=1000)  # Get a reasonable number
        filtered = []
        for bookmark in bookmarks:
            if bookmark.tags:
                tags = [t.strip() for t in bookmark.tags.split(',')]
                if args.tag.lower() in [t.lower() for t in tags]:
                    filtered.append(bookmark)
        bookmarks = filtered
    elif args.query:
        # Full-text search
        bookmarks = db.search_bookmarks(args.query, limit=args.limit)
    else:
        # Recent bookmarks
        bookmarks = db.get_recent_bookmarks(limit=args.limit)

    if not bookmarks:
        print("No bookmarks found.")
        return 0

    print(f"\nFound {len(bookmarks)} bookmark(s):\n")
    for i, bookmark in enumerate(bookmarks, 1):
        print(f"{i}. {bookmark.title or '[No title]'}")
        if bookmark.url:
            print(f"   URL: {bookmark.url}")
        if bookmark.description:
            print(f"   Description: {bookmark.description}")
        if bookmark.tags:
            print(f"   Tags: {bookmark.tags}")
        print(f"   File: {bookmark.image_path}")
        print(f"   Added: {bookmark.created_at}")
        print()

    return 0

def cmd_list(args):
    """List recent bookmarks."""
    args.limit = args.limit or 20
    args.query = None
    args.tag = None
    return cmd_search(args)

def cmd_stats(args):
    """Show database statistics."""
    db = Database(args.db_path)
    stats = db.get_stats()

    print("Screenshot Bookmark Statistics:")
    print(f"  Total bookmarks: {stats['total_bookmarks']}")
    print(f"  Bookmarks with URL: {stats['with_url']}")
    print(f"  Unique tags: {stats['unique_tags']}")
    print(f"  Database size: {stats['database_size']} bytes")

    if stats['total_bookmarks'] > 0:
        # Show recent tags
        tags = db.get_all_tags()[:10]  # Top 10 tags
        if tags:
            print(f"  Recent tags: {', '.join(tags)}")

    return 0

def cmd_watch(args):
    """Watch a folder for new screenshots."""
    db = Database(args.db_path)
    analyzer = ClaudeAnalyzer(api_key=args.api_key)
    # Get args with defaults if they don't exist (for subcommand compatibility)
    ocr_lang = getattr(args, 'ocr_lang', 'eng')
    mock_ocr = getattr(args, 'mock_ocr', False)
    ocr_processor = OCRProcessor(lang=ocr_lang, mock=mock_ocr)

    def on_screenshot_detected(image_path: str):
        print(f"New screenshot detected: {image_path}")
        process_screenshot(image_path, db, analyzer, ocr_processor)

    watcher = FolderWatcher(args.watch_path, on_screenshot_detected)
    print(f"Watching {args.watch_path} for new screenshots...")
    print("Press Ctrl+C to stop")

    try:
        while watcher.is_running():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping watcher...")
        watcher.stop()

    return 0

def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Screenshot to Bookmark tool - OCR screenshots and make them searchable"
    )
    parser.add_argument(
        "--db-path",
        default="~/.screenshot-bookmark/bookmarks.db",
        help="Path to SQLite database (default: ~/.screenshot-bookmark/bookmarks.db)"
    )
    parser.add_argument(
        "--api-key",
        help="Claude API key (can also use ANTHROPIC_API_KEY environment variable)"
    )
    parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # init command
    init_parser = subparsers.add_parser('init', help='Initialize the database')

    # add command
    add_parser = subparsers.add_parser('add', help='Add a screenshot to bookmarks')
    add_parser.add_argument('image_path', help='Path to screenshot image')
    add_parser.add_argument('--mock-ocr', action='store_true', help='Use mock OCR for testing')

    # search command
    search_parser = subparsers.add_parser('search', help='Search bookmarks')
    search_parser.add_argument('query', nargs='?', help='Search query')
    search_parser.add_argument('--tag', help='Search by tag')
    search_parser.add_argument('--limit', type=int, default=20, help='Maximum results to show')

    # list command
    list_parser = subparsers.add_parser('list', help='List recent bookmarks')
    list_parser.add_argument('--limit', type=int, default=20, help='Maximum results to show')

    # stats command
    subparsers.add_parser('stats', help='Show database statistics')

    # watch command
    watch_parser = subparsers.add_parser('watch', help='Watch folder for new screenshots')
    watch_parser.add_argument('watch_path', help='Path to folder to watch')
    watch_parser.add_argument(
        '--ocr-lang',
        default='eng',
        help='Language for OCR (default: eng)'
    )
    watch_parser.add_argument(
        '--mock-ocr',
        action='store_true',
        help='Use mock OCR for testing'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    setup_logging(args.verbose)

    # Route to appropriate command handler
    if args.command == 'init':
        return cmd_init(args)
    elif args.command == 'add':
        return cmd_add(args)
    elif args.command == 'search':
        return cmd_search(args)
    elif args.command == 'list':
        return cmd_list(args)
    elif args.command == 'stats':
        return cmd_stats(args)
    elif args.command == 'watch':
        return cmd_watch(args)
    else:
        parser.print_help()
        return 1

if __name__ == '__main__':
    sys.exit(main())