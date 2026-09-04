"""Integration tests for the screenshot bookmark tool."""
import os
from pathlib import Path
import sys

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def test_imports():
    """Test that all modules can be imported."""
    try:
        from screenshot_bookmark.database import Database
        from screenshot_bookmark.ocr import OCRProcessor
        from screenshot_bookmark.analyzer import ClaudeAnalyzer
        from screenshot_bookmark.watcher import FolderWatcher
        from screenshot_bookmark.cli import main
        print("[OK] All imports successful")
    except ImportError as e:
        print(f"[FAIL] Import failed: {e}")
        raise


def test_database_integration():
    """Test database integration."""
    db_path = Path("test_integration.db")
    try:
        if db_path.exists():
            db_path.unlink()
        from screenshot_bookmark.database import Database
        db = Database(str(db_path))

        # Test adding a bookmark
        from screenshot_bookmark.database import Bookmark
        bookmark = Bookmark(
            image_path="/fake/path.png",
            ocr_text="Fake OCR text for testing",
            title="Test Bookmark",
            url="https://test.example.com",
            description="A test bookmark",
            tags="test,integration"
        )

        bookmark_id = db.add_bookmark(bookmark)
        assert bookmark_id > 0

        # Test retrieval
        retrieved = db.get_bookmark(bookmark_id)
        assert retrieved is not None
        assert retrieved.title == "Test Bookmark"

        # Test search
        results = db.search_bookmarks("test")
        assert len(results) >= 1

        # Test stats
        stats = db.get_stats()
        assert stats['total_bookmarks'] >= 1

        # Close connection
        del db
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass
        print("[OK] Database integration test passed")
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


if __name__ == "__main__":
    test_imports()
    test_database_integration()
    print("\nAll integration tests passed!")