"""Tests for the database module."""
import os
from pathlib import Path
import sys
from typing import List

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from screenshot_bookmark.database import Database, Bookmark


def test_database_creation():
    """Test that database initializes correctly."""
    # Use a unique path in current directory (not temp dir to avoid Windows file locks)
    db_path = Path("test_create.db")
    try:
        if db_path.exists():
            db_path.unlink()
        db = Database(str(db_path))
        assert db.db_path.exists()
        # Use os.unlink directly
        del db
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass  # Windows may hold file briefly
        print("[OK] Database creation test passed")
    finally:
        # Cleanup
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def test_add_and_get_bookmark():
    """Test adding and retrieving a bookmark."""
    db_path = Path("test_add.db")
    try:
        if db_path.exists():
            db_path.unlink()
        db = Database(str(db_path))

        bookmark = Bookmark(
            image_path="/test/image.png",
            ocr_text="Sample OCR text",
            title="Test Title",
            url="https://example.com",
            description="Test description",
            tags="test,example"
        )

        bookmark_id = db.add_bookmark(bookmark)
        assert bookmark_id > 0

        retrieved = db.get_bookmark(bookmark_id)
        assert retrieved is not None
        assert retrieved.title == "Test Title"
        assert retrieved.url == "https://example.com"
        assert retrieved.image_path == "/test/image.png"

        # Close connection
        del db
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass
        print("[OK] Add/get bookmark test passed")
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def test_search_bookmarks():
    """Test searching bookmarks."""
    db_path = Path("test_search.db")
    try:
        if db_path.exists():
            db_path.unlink()
        db = Database(str(db_path))

        # Add test bookmarks
        bookmark1 = Bookmark(
            image_path="/test/image1.png",
            ocr_text="neural network tutorial",
            title="Neural Network Tutorial",
            url="https://example.com/nn",
            description="Learn neural networks",
            tags="AI,tutorial"
        )
        bookmark2 = Bookmark(
            image_path="/test/image2.png",
            ocr_text="javascript best practices",
            title="JS Best Practices",
            url="https://example.com/js",
            description="JavaScript coding tips",
            tags="programming,javascript"
        )

        db.add_bookmark(bookmark1)
        db.add_bookmark(bookmark2)

        # Search for neural network - try single words since FTS5 syntax may be picky
        results = db.search_bookmarks("neural")
        assert len(results) >= 1
        # Check that one of the results is the neural network one
        assert any("Neural" in b.title for b in results)

        # Search by tag
        results = db.search_bookmarks("tutorial")
        assert len(results) >= 1

        # Close connection
        del db
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass
        print("[OK] Search bookmarks test passed")
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


def test_get_stats():
    """Test getting database statistics."""
    db_path = Path("test_stats.db")
    try:
        if db_path.exists():
            db_path.unlink()
        db = Database(str(db_path))

        # Add a bookmark
        bookmark = Bookmark(
            image_path="/test/image.png",
            ocr_text="test",
            title="Test",
            url="https://example.com",
            description="Test",
            tags="test"
        )
        db.add_bookmark(bookmark)

        stats = db.get_stats()
        assert stats['total_bookmarks'] >= 1
        assert stats['with_url'] >= 1

        # Close connection
        del db
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass
        print("[OK] Get stats test passed")
    finally:
        if db_path.exists():
            try:
                db_path.unlink()
            except PermissionError:
                pass


if __name__ == "__main__":
    test_database_creation()
    test_add_and_get_bookmark()
    test_search_bookmarks()
    test_get_stats()
    print("\nAll tests passed!")