"""SQLite database layer with FTS5 for bookmark storage and search."""
import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class Bookmark:
    """Represents a screenshot bookmark."""
    id: Optional[int] = None
    image_path: str = ""
    ocr_text: str = ""
    title: str = ""
    url: str = ""
    description: str = ""
    tags: str = ""  # comma-separated tags
    created_at: str = ""
    file_hash: str = ""  # for deduplication


class Database:
    """Handles SQLite database operations with FTS5 search."""

    def __init__(self, db_path: str = "~/.screenshot-bookmark/bookmarks.db"):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
        # Enable check_same_thread=False to avoid threading issues on Windows
        # Each operation opens a fresh connection via context manager anyway
        self._lock = False  # simple lock flag for safety

    def init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                -- Main bookmarks table
                CREATE TABLE IF NOT EXISTS bookmarks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    image_path TEXT NOT NULL UNIQUE,
                    ocr_text TEXT,
                    title TEXT,
                    url TEXT,
                    description TEXT,
                    tags TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    file_hash TEXT
                );

                -- FTS5 virtual table for full-text search (without content link)
                CREATE VIRTUAL TABLE IF NOT EXISTS bookmarks_fts
                USING fts5(
                    title,
                    description,
                    tags,
                    ocr_text
                );

                -- Indexes for performance
                CREATE INDEX IF NOT EXISTS idx_bookmarks_created_at ON bookmarks(created_at);
                CREATE INDEX IF NOT EXISTS idx_bookmarks_file_hash ON bookmarks(file_hash);
            """)

    def add_bookmark(self, bookmark: Bookmark) -> int:
        """Add a bookmark and return its ID."""
        with sqlite3.connect(self.db_path) as conn:
            # Check if bookmark with this path already exists
            cursor = conn.execute(
                "SELECT id FROM bookmarks WHERE image_path = ?",
                (bookmark.image_path,)
            )
            existing = cursor.fetchone()

            if existing:
                bookmark_id = existing[0]
                # Update existing bookmark
                conn.execute("""
                    UPDATE bookmarks SET
                        ocr_text = ?,
                        title = ?,
                        url = ?,
                        description = ?,
                        tags = ?,
                        file_hash = ?
                    WHERE id = ?
                """, (
                    bookmark.ocr_text,
                    bookmark.title,
                    bookmark.url,
                    bookmark.description,
                    bookmark.tags,
                    bookmark.file_hash,
                    bookmark_id
                ))
            else:
                # Insert new bookmark
                cursor = conn.execute("""
                    INSERT INTO bookmarks
                    (image_path, ocr_text, title, url, description, tags, file_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    bookmark.image_path,
                    bookmark.ocr_text,
                    bookmark.title,
                    bookmark.url,
                    bookmark.description,
                    bookmark.tags,
                    bookmark.file_hash
                ))
                bookmark_id = cursor.lastrowid

            # Update FTS table (delete old, insert new)
            conn.execute("DELETE FROM bookmarks_fts WHERE rowid = ?", (bookmark_id,))
            conn.execute("""
                INSERT INTO bookmarks_fts (rowid, title, description, tags, ocr_text)
                VALUES (?, ?, ?, ?, ?)
            """, (
                bookmark_id,
                bookmark.title,
                bookmark.description,
                bookmark.tags,
                bookmark.ocr_text
            ))
            conn.commit()
            return bookmark_id

    def get_bookmark(self, bookmark_id: int) -> Optional[Bookmark]:
        """Get a bookmark by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM bookmarks WHERE id = ?", (bookmark_id,))
            row = cursor.fetchone()
            if row:
                return Bookmark(**dict(row))
        return None

    def get_bookmark_by_path(self, image_path: str) -> Optional[Bookmark]:
        """Get a bookmark by image path."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM bookmarks WHERE image_path = ?", (image_path,))
            row = cursor.fetchone()
            if row:
                return Bookmark(**dict(row))
        return None

    def search_bookmarks(self, query: str, limit: int = 20) -> List[Bookmark]:
        """Search bookmarks using FTS5."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            # Escape special FTS5 characters by wrapping in quotes
            safe_query = query.replace('"', '""')
            cursor = conn.execute("""
                SELECT b.id, b.image_path, b.ocr_text, b.title, b.url,
                       b.description, b.tags, b.created_at, b.file_hash
                FROM bookmarks_fts
                JOIN bookmarks b ON bookmarks_fts.rowid = b.id
                WHERE bookmarks_fts MATCH ?
                ORDER BY bm25(bookmarks_fts)
                LIMIT ?
            """, (safe_query, limit))
            return [Bookmark(**dict(row)) for row in cursor.fetchall()]

    def get_recent_bookmarks(self, limit: int = 20) -> List[Bookmark]:
        """Get most recent bookmarks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM bookmarks
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
            return [Bookmark(**dict(row)) for row in cursor.fetchall()]

    def get_all_tags(self) -> List[str]:
        """Get all unique tags."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT tags FROM bookmarks WHERE tags IS NOT NULL AND tags != ''")
            tags = set()
            for (tag_str,) in cursor.fetchall():
                if tag_str:
                    for tag in tag_str.split(','):
                        tag = tag.strip()
                        if tag:
                            tags.add(tag)
            return sorted(list(tags))

    def delete_bookmark(self, bookmark_id: int) -> bool:
        """Delete a bookmark by ID."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("DELETE FROM bookmarks WHERE id = ?", (bookmark_id,))
            return cursor.rowcount > 0

    def get_stats(self) -> Dict[str, Any]:
        """Get database statistics."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM bookmarks")
            total_count = cursor.fetchone()[0]

            cursor = conn.execute("SELECT COUNT(*) FROM bookmarks WHERE url != ''")
            with_url_count = cursor.fetchone()[0]

            unique_tags = len(self.get_all_tags())

            return {
                "total_bookmarks": total_count,
                "with_url": with_url_count,
                "unique_tags": unique_tags,
                "database_size": self.db_path.stat().st_size if self.db_path.exists() else 0
            }


def compute_file_hash(file_path: str) -> str:
    """Compute SHA256 hash of a file for deduplication."""
    import hashlib
    hash_sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_sha256.update(chunk)
    return hash_sha256.hexdigest()