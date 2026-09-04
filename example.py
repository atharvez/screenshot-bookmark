#!/usr/bin/env python3
"""
Example usage of the screenshot-bookmark tool.
"""

import os
import tempfile
from pathlib import Path

# Add src to path
import sys
sys.path.insert(0, str(Path(__file__).parent / "src"))

from screenshot_bookmark.database import Database
from screenshot_bookmark.ocr import OCRProcessor
from screenshot_bookmark.analyzer import ClaudeAnalyzer

def example_usage():
    """Demonstrate how to use the screenshot-bookmark components."""

    # Use a fixed path in current directory to avoid Windows temp dir issues
    db_path = "example_demo.db"
    # Clean up any existing file
    if os.path.exists(db_path):
        try:
            os.unlink(db_path)
        except OSError:
            pass

    db = Database(db_path)

    try:

        print("=== Screenshot Bookmark Example ===\n")

        # Initialize OCR processor (will warn if Tesseract not available)
        try:
            ocr_processor = OCRProcessor()
            print("[OK] OCR processor initialized")
        except Exception as e:
            print(f"[WARN] OCR processor initialization failed: {e}")
            print("  (This is expected if Tesseract/EasyOCR not installed)")
            ocr_processor = None

        # Initialize Claude analyzer (will need API key for real usage)
        # For this example, we'll show the structure but won't make actual API calls
        try:
            # In real usage, you would provide an API key:
            # analyzer = ClaudeAnalyzer(api_key=os.getenv("ANTHROPIC_API_KEY"))
            analyzer = ClaudeAnalyzer()  # Will use environment variable
            print("[OK] Claude analyzer initialized")
        except Exception as e:
            print(f"[WARN] Claude analyzer initialization failed: {e}")
            print("  (This is expected if ANTHROPIC_API_KEY not set)")
            analyzer = None

        # Show database stats
        stats = db.get_stats()
        print(f"\n[STATS] Database Statistics:")
        print(f"   Total bookmarks: {stats['total_bookmarks']}")

        # Demonstrate adding a bookmark (mock data)
        print(f"\n[ADD] Adding a sample bookmark...")
        from screenshot_bookmark.database import Bookmark

        sample_bookmark = Bookmark(
            image_path="/tmp/sample_screenshot.png",
            ocr_text="""How to Build a REST API with Python and Flask
                      Visit https://realpython.com/api-design for the full tutorial
                      Learn about HTTP methods, JSON serialization, and authentication""",
            title="How to Build a REST API with Python and Flask",
            url="https://realpython.com/api-design",
            description="A comprehensive tutorial on building REST APIs using Python Flask framework",
            tags="python,flask,api,tutorial,web-development"
        )

        bookmark_id = db.add_bookmark(sample_bookmark)
        print(f"[OK] Added bookmark with ID: {bookmark_id}")

        # Retrieve and display the bookmark
        retrieved = db.get_bookmark(bookmark_id)
        if retrieved:
            print(f"\n[VIEW] Retrieved Bookmark:")
            print(f"   Title: {retrieved.title}")
            print(f"   URL: {retrieved.url}")
            print(f"   Description: {retrieved.description}")
            print(f"   Tags: {retrieved.tags}")
            print(f"   File: {retrieved.image_path}")

        # Demonstrate search
        print(f"\n[SEARCH] Searching for 'Flask'...")
        results = db.search_bookmarks("Flask")
        print(f"   Found {len(results)} result(s)")
        for bookmark in results:
            print(f"   - {bookmark.title}")

        # Show all tags
        tags = db.get_all_tags()
        if tags:
            print(f"\n[TAGS] All Tags: {', '.join(tags)}")

        # Final stats
        final_stats = db.get_stats()
        print(f"\n[FINAL] Final Statistics:")
        print(f"   Total bookmarks: {final_stats['total_bookmarks']}")
        print(f"   Bookmarks with URL: {final_stats['with_url']}")
        print(f"   Unique tags: {final_stats['unique_tags']}")

        print(f"\n[SUCCESS] Example completed successfully!")
        print(f"\nTo use with real screenshots:")
        print(f"  1. Install Tesseract OCR: https://github.com/tesseract-ocr/tesseract")
        print(f"  2. Set your Claude API key: export ANTHROPIC_API_KEY='your-key-here'")
        print(f"  3. Run: screenshot-bookmark watch ~/Pictures/Screenshots")

    finally:
        # Clean up demo database
        if os.path.exists(db_path):
            try:
                os.unlink(db_path)
            except OSError:
                pass

if __name__ == "__main__":
    example_usage()