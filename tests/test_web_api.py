"""Tests for the Screenshot Bookmark Web API and Extension endpoints."""
import os
import io
import asyncio
from pathlib import Path
import sys
from fastapi.testclient import TestClient

# Add src to path for testing
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from screenshot_bookmark.web import app, startup_event
import screenshot_bookmark.web as web_module
from screenshot_bookmark.database import Database

def get_test_client():
    # Configure test database
    test_db_path = Path("test_api.db")
    if test_db_path.exists():
        try:
            test_db_path.unlink()
        except Exception:
            pass

    asyncio.run(startup_event())
    web_module.db = Database(str(test_db_path))
    return TestClient(app), test_db_path

def test_health_endpoint():
    client, db_path = get_test_client()
    try:
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "ocr_available" in data
        assert "ai_available" in data
    finally:
        cleanup_db(db_path)

def test_quick_bookmark_and_check():
    client, db_path = get_test_client()
    try:
        # Check initial (not bookmarked)
        check1 = client.get("/api/check?url=https://github.com/google/gemini")
        assert check1.status_code == 200
        assert check1.json()["bookmarked"] is False

        # Create quick bookmark
        res = client.post("/api/bookmarks", json={
            "url": "https://github.com/google/gemini",
            "title": "Google Gemini Repository",
            "tags": "ai, google, repo",
            "description": "The official repo"
        })
        assert res.status_code == 200
        bm = res.json()
        assert bm["id"] > 0
        assert bm["title"] == "Google Gemini Repository"
        assert bm["url"] == "https://github.com/google/gemini"

        # Check again (now bookmarked)
        check2 = client.get("/api/check?url=https://github.com/google/gemini")
        assert check2.status_code == 200
        assert check2.json()["bookmarked"] is True
        assert check2.json()["bookmark"]["title"] == "Google Gemini Repository"

        # Update bookmark
        update_res = client.put(f"/api/bookmark/{bm['id']}", json={
            "title": "Google Gemini AI Updated",
            "tags": "ai, gemini, google"
        })
        assert update_res.status_code == 200
        assert update_res.json()["title"] == "Google Gemini AI Updated"

        # Search
        search_res = client.get("/api/search?q=Gemini")
        assert search_res.status_code == 200
        assert len(search_res.json()["results"]) >= 1

        # Delete
        del_res = client.delete(f"/api/bookmark/{bm['id']}")
        assert del_res.status_code == 200

        # Check after deletion
        check3 = client.get("/api/check?url=https://github.com/google/gemini")
        assert check3.json()["bookmarked"] is False
    finally:
        cleanup_db(db_path)

def test_upload_screenshot_with_client_metadata():
    client, db_path = get_test_client()
    try:
        # Create a tiny 10x10 png image
        from PIL import Image
        img = Image.new("RGB", (30, 30), color="blue")
        img_bytes = io.BytesIO()
        img.save(img_bytes, format="PNG")
        img_bytes.seek(0)

        # Upload with client metadata
        res = client.post(
            "/api/upload",
            files={"file": ("test_tab.png", img_bytes, "image/png")},
            data={
                "url": "https://python.org",
                "title": "Welcome to Python.org",
                "tags": "programming, python",
                "description": "Python official site"
            }
        )
        assert res.status_code == 200
        data = res.json()
        assert data["url"] == "https://python.org"
        assert data["title"] == "Welcome to Python.org"
        assert "python" in data["tags"]
        assert data["image_url"] is not None

        # Verify image serving endpoint
        img_filename = Path(data["image_path"]).name
        img_res = client.get(f"/api/images/{img_filename}")
        assert img_res.status_code == 200
        assert img_res.headers["content-type"].startswith("image/")
    finally:
        cleanup_db(db_path)

def test_export_bookmarks():
    client, db_path = get_test_client()
    try:
        # Add a bookmark
        client.post("/api/bookmarks", json={
            "url": "https://example.com/export-test",
            "title": "Export Test",
            "tags": "export, test"
        })

        # Test JSON export
        res_json = client.get("/api/export?format=json")
        assert res_json.status_code == 200
        assert any(b["url"] == "https://example.com/export-test" for b in res_json.json())

        # Test HTML Netscape export
        res_html = client.get("/api/export?format=html")
        assert res_html.status_code == 200
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in res_html.text
        assert "https://example.com/export-test" in res_html.text
    finally:
        cleanup_db(db_path)

def cleanup_db(path):
    if path and path.exists():
        try:
            path.unlink()
        except Exception:
            pass
