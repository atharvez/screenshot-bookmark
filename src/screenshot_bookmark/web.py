"""FastAPI web server for the Screenshot Bookmark tool."""
import logging
import os
from pathlib import Path
from typing import List, Optional
import io
import time
import json
import re

from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Query, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import Database, Bookmark
from .ocr import OCRProcessor
from .analyzer import GeminiAnalyzer, BookmarkMetadata

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Screenshot Bookmark API",
    description="Convert screenshots to searchable bookmarks with OCR and AI",
    version="1.1.0"
)

# Enable CORS for browser extensions and local tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Package directories
PACKAGE_DIR = Path(__file__).parent
STATIC_DIR = PACKAGE_DIR / "static"
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", "~/.screenshot-bookmark/uploads")).expanduser()
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Global instances (initialized on startup)
db: Optional[Database] = None
ocr_processor: Optional[OCRProcessor] = None
analyzer: Optional[GeminiAnalyzer] = None


@app.on_event("startup")
async def startup_event():
    """Initialize components on startup."""
    global db, ocr_processor, analyzer

    load_dotenv()

    db_path = os.getenv("DB_PATH", "~/.screenshot-bookmark/bookmarks.db")
    db = Database(db_path)

    # Initialize OCR with mock=False (use real Tesseract if available)
    use_mock = os.getenv("MOCK_OCR", "false").lower() == "true"
    ocr_processor = OCRProcessor(mock=use_mock)

    # Initialize Gemini analyzer (gracefully degrades to heuristic analysis if no key)
    analyzer = GeminiAnalyzer()

    # Ensure uploads directory exists
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

    logger.info("Screenshot Bookmark API started successfully")


# Pydantic models for request/response
class BookmarkResponse(BaseModel):
    id: int
    image_path: str
    image_url: Optional[str] = None
    title: str
    url: str
    description: str
    tags: str
    created_at: str
    ocr_text: Optional[str] = None


class BookmarkCreate(BaseModel):
    url: str
    title: Optional[str] = ""
    description: Optional[str] = ""
    tags: Optional[str] = ""


class BookmarkUpdate(BaseModel):
    title: Optional[str] = None
    url: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[str] = None


class SearchResponse(BaseModel):
    query: str
    results: List[BookmarkResponse]
    count: int


class StatsResponse(BaseModel):
    total_bookmarks: int
    with_url: int
    unique_tags: int
    database_size: int


def format_bookmark_response(b: Bookmark) -> BookmarkResponse:
    """Format a database Bookmark object into a BookmarkResponse."""
    img_url = None
    if b.image_path and not b.image_path.startswith("web://"):
        file_name = Path(b.image_path).name
        full_file = UPLOAD_DIR / file_name
        if full_file.exists() or Path(b.image_path).exists():
            img_url = f"/api/images/{file_name}"

    return BookmarkResponse(
        id=b.id or 0,
        image_path=b.image_path,
        image_url=img_url,
        title=b.title or "Untitled Bookmark",
        url=b.url or "",
        description=b.description or "",
        tags=b.tags or "",
        created_at=b.created_at or "",
        ocr_text=b.ocr_text[:500] if b.ocr_text else None
    )


# API Routes
@app.get("/")
async def root():
    """Serve the web UI."""
    html_file = STATIC_DIR / "index.html"
    if html_file.exists():
        return FileResponse(html_file)
    return HTMLResponse(content=get_default_html(), status_code=200)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "ocr_available": ocr_processor is not None and not getattr(ocr_processor, 'mock', False),
        "ai_available": analyzer is not None and getattr(analyzer, 'has_api_key', False),
        "database": "connected" if db is not None else "disconnected"
    }


@app.get("/api/images/{filename}")
async def get_image(filename: str):
    """Serve uploaded screenshot images."""
    safe_filename = Path(filename).name
    file_path = UPLOAD_DIR / safe_filename
    if not file_path.exists():
        # Also check current working directory / uploads if needed
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(file_path)


@app.get("/api/check")
async def check_url(url: str = Query(..., description="Check if a URL is already bookmarked")):
    """Check if a URL is already saved as a bookmark."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    normalized_url = url.strip().rstrip('/')
    found = db.get_bookmark_by_url(url) or db.get_bookmark_by_url(normalized_url) or db.get_bookmark_by_url(normalized_url + '/')
    if found:
        return {"bookmarked": True, "bookmark": format_bookmark_response(found)}
    return {"bookmarked": False, "bookmark": None}


@app.post("/api/bookmarks", response_model=BookmarkResponse)
async def create_bookmark(data: BookmarkCreate):
    """Create a standard URL bookmark directly without a screenshot."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    title = data.title.strip() if data.title else ""
    if not title:
        # Generate friendly title from URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(data.url)
            domain = parsed.netloc.replace('www.', '')
            path_part = parsed.path.strip('/').split('/')[-1]
            title = f"{path_part.replace('-', ' ').title()} - {domain}" if path_part else domain
        except Exception:
            title = data.url

    bookmark = Bookmark(
        image_path="",
        ocr_text="",
        title=title,
        url=data.url.strip(),
        description=data.description.strip() if data.description else "",
        tags=data.tags.strip() if data.tags else "",
        file_hash=""
    )

    bookmark_id = db.add_bookmark(bookmark)
    saved = db.get_bookmark(bookmark_id)
    return format_bookmark_response(saved or bookmark)


@app.post("/api/upload", response_model=BookmarkResponse)
async def upload_screenshot(
    file: UploadFile = File(...),
    url: Optional[str] = Form(None),
    title: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    run_ocr: bool = Form(True),
    background_tasks: BackgroundTasks = None
):
    """Upload and process a screenshot into a searchable bookmark."""
    if not db or not ocr_processor or not analyzer:
        raise HTTPException(status_code=503, detail="Service not initialized")

    # Validate file type
    allowed_extensions = {'.png', '.jpg', '.jpeg', '.bmp', '.tiff', '.webp', '.gif'}
    file_ext = Path(file.filename or "screenshot.png").suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {', '.join(allowed_extensions)}"
        )

    try:
        content = await file.read()

        # Generate a unique safe filename
        safe_base = re.sub(r'[^a-zA-Z0-9_\-\.]', '_', Path(file.filename or 'screenshot').stem)
        unique_filename = f"{safe_base}_{int(time.time()*1000)}{file_ext}"
        file_path = UPLOAD_DIR / unique_filename

        with open(file_path, "wb") as f:
            f.write(content)

        ocr_text = ""
        metadata = BookmarkMetadata()

        if run_ocr:
            try:
                ocr_text = ocr_processor.extract_text(str(file_path))
            except Exception as ocr_err:
                logger.warning(f"OCR processing failed: {ocr_err}")
                ocr_text = ""

            if ocr_text:
                try:
                    metadata = analyzer.analyze_ocr_text(ocr_text, str(file_path))
                except Exception as ai_err:
                    logger.warning(f"AI analysis failed: {ai_err}")

        # Client-supplied metadata takes precedence over OCR/AI guesses
        final_title = (title or "").strip()
        if not final_title:
            final_title = metadata.title or Path(file.filename or "Screenshot").stem.replace('_', ' ').title()

        final_url = (url or "").strip()
        if not final_url:
            final_url = metadata.url

        final_desc = (description or "").strip()
        if not final_desc:
            final_desc = metadata.description

        # Combine explicit tags with extracted tags
        all_tags = []
        if tags:
            all_tags.extend([t.strip() for t in tags.split(',') if t.strip()])
        if metadata.tags:
            all_tags.extend([t.strip() for t in metadata.tags.split(',') if t.strip()])
        # Deduplicate while preserving order
        unique_tags = list(dict.fromkeys(all_tags))
        final_tags = ", ".join(unique_tags)

        # Create bookmark
        bookmark = Bookmark(
            image_path=str(file_path),
            ocr_text=ocr_text,
            title=final_title,
            url=final_url,
            description=final_desc,
            tags=final_tags,
            file_hash=""
        )

        bookmark_id = db.add_bookmark(bookmark)
        saved = db.get_bookmark(bookmark_id)

        return format_bookmark_response(saved or bookmark)

    except Exception as e:
        logger.exception(f"Upload failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/search", response_model=SearchResponse)
async def search_bookmarks(
    q: Optional[str] = Query(None, description="Search query"),
    tag: Optional[str] = Query(None, description="Filter by tag"),
    limit: int = Query(20, description="Maximum results")
):
    """Search bookmarks using full-text search or tags."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    try:
        if tag:
            all_recent = db.get_recent_bookmarks(limit=1000)
            results = []
            tag_lower = tag.lower().strip()
            for b in all_recent:
                if b.tags:
                    tags = [t.strip().lower() for t in b.tags.split(',')]
                    if tag_lower in tags:
                        results.append(b)
                        if len(results) >= limit:
                            break
        elif q and q.strip():
            results = db.search_bookmarks(q.strip(), limit=limit)
        else:
            results = db.get_recent_bookmarks(limit=limit)

        response_results = [format_bookmark_response(r) for r in results]

        return SearchResponse(
            query=q if (q and not tag) else (f"tag:{tag}" if tag else ""),
            results=response_results,
            count=len(response_results)
        )

    except Exception as e:
        logger.exception(f"Search failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/recent", response_model=List[BookmarkResponse])
async def get_recent(limit: int = Query(20)):
    """Get recent bookmarks."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    bookmarks = db.get_recent_bookmarks(limit=limit)
    return [format_bookmark_response(b) for b in bookmarks]


@app.get("/api/bookmark/{bookmark_id}", response_model=BookmarkResponse)
@app.get("/api/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
async def get_bookmark(bookmark_id: int):
    """Get a single bookmark by ID."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    bookmark = db.get_bookmark(bookmark_id)
    if not bookmark:
        raise HTTPException(status_code=404, detail="Bookmark not found")
    return format_bookmark_response(bookmark)


@app.put("/api/bookmark/{bookmark_id}", response_model=BookmarkResponse)
@app.put("/api/bookmarks/{bookmark_id}", response_model=BookmarkResponse)
async def update_bookmark(bookmark_id: int, data: BookmarkUpdate):
    """Update an existing bookmark."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    success = db.update_bookmark(
        bookmark_id=bookmark_id,
        title=data.title,
        url=data.url,
        description=data.description,
        tags=data.tags
    )
    if not success:
        raise HTTPException(status_code=404, detail="Bookmark not found")

    updated = db.get_bookmark(bookmark_id)
    return format_bookmark_response(updated)


@app.delete("/api/bookmark/{bookmark_id}")
@app.delete("/api/bookmarks/{bookmark_id}")
async def delete_bookmark(bookmark_id: int):
    """Delete a bookmark."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    if db.delete_bookmark(bookmark_id):
        return {"message": "Bookmark deleted", "id": bookmark_id, "success": True}
    raise HTTPException(status_code=404, detail="Bookmark not found")


@app.get("/api/tags")
async def get_tags():
    """Get all unique tags."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    return {"tags": db.get_all_tags()}


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats():
    """Get database statistics."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    stats = db.get_stats()
    return StatsResponse(**stats)


@app.get("/api/export")
async def export_bookmarks(format: str = Query("json", description="Export format: 'json' or 'html'")):
    """Export all bookmarks as JSON or Netscape HTML bookmark format."""
    if not db:
        raise HTTPException(status_code=503, detail="Service not initialized")

    bookmarks = db.get_recent_bookmarks(limit=10000)

    if format.lower() == "html":
        # Generate Netscape Bookmark HTML (compatible with Chrome, Firefox, Edge, Safari import)
        html_lines = [
            "<!DOCTYPE NETSCAPE-Bookmark-file-1>",
            "<!-- This is an automatically generated file. -->",
            '<META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">',
            "<TITLE>Bookmarks</TITLE>",
            "<H1>Bookmarks</H1>",
            "<DL><p>"
        ]
        for b in bookmarks:
            url = b.url or "#"
            title = b.title or "Untitled"
            tags = b.tags or ""
            html_lines.append(f'    <DT><A HREF="{url}" TAGS="{tags}">{title}</A>')
            if b.description:
                html_lines.append(f'    <DD>{b.description}')
        html_lines.append("</DL><p>")
        content = "\n".join(html_lines)
        return Response(
            content=content,
            media_type="text/html",
            headers={"Content-Disposition": "attachment; filename=bookmarks.html"}
        )

    # Default to JSON
    data = [format_bookmark_response(b).model_dump() for b in bookmarks]
    return JSONResponse(
        content=data,
        headers={"Content-Disposition": "attachment; filename=bookmarks.json"}
    )


def get_default_html():
    """Default fallback HTML page if static files are not built."""
    return """
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Screenshot Bookmark Hub</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; max-width: 900px; margin: 40px auto; padding: 20px; color: #222; }
        header { border-bottom: 2px solid #e0e0e0; padding-bottom: 16px; margin-bottom: 24px; }
        h1 { margin: 0 0 8px 0; color: #1a73e8; }
        .card { background: #fdfdfd; border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin-bottom: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.05); }
        .bookmark-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; margin-top: 20px; }
        .bookmark-card { border: 1px solid #e2e8f0; border-radius: 8px; padding: 16px; background: white; transition: transform 0.15s, box-shadow 0.15s; }
        .bookmark-card:hover { transform: translateY(-2px); box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }
        .bookmark-card img { width: 100%; height: 140px; object-fit: cover; border-radius: 6px; margin-bottom: 10px; background: #eee; }
        .tag { display: inline-block; background: #e8f0fe; color: #1a73e8; font-size: 11px; padding: 2px 8px; border-radius: 12px; margin-right: 4px; margin-top: 4px; }
        button { background: #1a73e8; color: white; border: none; padding: 8px 16px; border-radius: 6px; cursor: pointer; font-weight: 500; }
        button:hover { background: #1557b0; }
        input[type=text] { width: 100%; padding: 10px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; }
    </style>
</head>
<body>
    <header>
        <h1>📸 Screenshot Bookmark Hub</h1>
        <p>Your local-first visual bookmarks library powered by OCR and AI.</p>
    </header>
    <div class="card">
        <input type="text" id="search" placeholder="Search your bookmarks (full-text search)..." oninput="doSearch()">
    </div>
    <div id="bookmarks" class="bookmark-grid">Loading bookmarks...</div>
    <script>
        async function loadBookmarks(q = '') {
            const url = q ? `/api/search?q=${encodeURIComponent(q)}` : '/api/recent?limit=50';
            const res = await fetch(url);
            const data = await res.json();
            const items = q ? data.results : data;
            const container = document.getElementById('bookmarks');
            if (!items || items.length === 0) {
                container.innerHTML = '<p>No bookmarks found.</p>';
                return;
            }
            container.innerHTML = items.map(b => `
                <div class="bookmark-card">
                    ${b.image_url ? `<img src="${b.image_url}" alt="Screenshot">` : ''}
                    <h3 style="margin:0 0 8px 0; font-size: 16px;">
                        <a href="${b.url || '#'}" target="_blank" style="color:#1a73e8; text-decoration:none;">${b.title}</a>
                    </h3>
                    <p style="font-size: 13px; color: #555; margin: 0 0 8px 0;">${b.description || 'No description'}</p>
                    <div>${(b.tags || '').split(',').filter(Boolean).map(t => `<span class="tag">${t.trim()}</span>`).join('')}</div>
                </div>
            `).join('');
        }
        let timeout = null;
        function doSearch() {
            clearTimeout(timeout);
            timeout = setTimeout(() => {
                loadBookmarks(document.getElementById('search').value);
            }, 250);
        }
        loadBookmarks();
    </script>
</body>
</html>
"""

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")