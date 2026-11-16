#!/usr/bin/env python3
"""
FlipLabs Lightweight Production Backend Server (FastAPI)
--------------------------------------------------------
Designed for minimal memory footprint (<80MB RAM) on srv-lmslabs-smpjkt
while taking advantage of multi-core Xeon CPU for instant PDF->WebP conversion.
"""

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "converter"))

from converter import convert_pdf_to_flipbook, slugify  # noqa: E402

BOOKS_DIR = ROOT_DIR / "books"
VIEWER_DIR = ROOT_DIR / "viewer"
BOOKCASE_DIR = ROOT_DIR / "bookcase"
UPLOADS_DIR = ROOT_DIR / "server" / "uploads"

BOOKS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="FlipLabs — Self-Hosted FlipHTML5 Platform",
    description="Labschool Digital Library & 3D FlipBook Engine (books.labschool.xyz)",
    version="1.0.0",
)


@app.on_event("startup")
def ensure_sample_books():
    """Ensure sample books exist on first startup."""
    if not (BOOKS_DIR / "smp8-matematika" / "book-config.json").exists():
        try:
            from generate_sample_books import main as gen_samples
            gen_samples()
        except Exception as exc:
            print(f"[WARN] Could not auto-generate sample books: {exc}")


# Static file mounts
app.mount("/viewer", StaticFiles(directory=str(VIEWER_DIR), html=True), name="viewer")
app.mount("/bookcase", StaticFiles(directory=str(BOOKCASE_DIR), html=True), name="bookcase")
app.mount("/books", StaticFiles(directory=str(BOOKS_DIR)), name="books")


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "fliplabs", "domain": "books.labschool.xyz"}


@app.get("/", response_class=HTMLResponse)
def serve_bookcase_home():
    index_file = BOOKCASE_DIR / "index.html"
    return FileResponse(str(index_file))


@app.get("/view/{book_id}", response_class=HTMLResponse)
def serve_book_viewer(book_id: str):
    cfg_path = BOOKS_DIR / book_id / "book-config.json"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail=f"Buku '{book_id}' tidak ditemukan")
    return FileResponse(str(VIEWER_DIR / "index.html"))


@app.get("/api/books")
def list_books():
    books: List[Dict[str, Any]] = []
    if BOOKS_DIR.exists():
        for folder in sorted(BOOKS_DIR.iterdir()):
            cfg_file = folder / "book-config.json"
            if folder.is_dir() and cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        books.append(json.load(f))
                except Exception:
                    continue
    # Sort so smp8-matematika is first
    books.sort(key=lambda b: (0 if b.get("id") == "smp8-matematika" else 1, b.get("title", "")))
    return {"total": len(books), "books": books}


@app.post("/api/upload")
async def upload_and_convert_pdf(
    file: UploadFile = File(...),
    title: str = Form(...),
    author: str = Form("Tim Guru Labschool"),
    category: str = Form("SMP Kelas 8"),
    subject: str = Form("Umum"),
    licenseTier: str = Form("enterprise"),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF (.pdf)")

    book_slug = slugify(title)
    temp_pdf = UPLOADS_DIR / f"{book_slug}.pdf"

    with open(temp_pdf, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        cfg = convert_pdf_to_flipbook(
            pdf_path=str(temp_pdf),
            books_root=str(BOOKS_DIR),
            book_id=book_slug,
            title=title,
            author=author,
            category=category,
            subject=subject,
            license_tier=licenseTier,
        )
        return JSONResponse({"status": "success", "book": cfg})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal mengonversi PDF: {exc}")


class AIChatRequest(BaseModel):
    bookId: str
    currentPage: int = 1
    question: str


@app.post("/api/ai-chat")
def ai_book_assistant(req: AIChatRequest):
    """Smart contextual RAG search over the book's extracted search-index.json."""
    idx_file = BOOKS_DIR / req.bookId / "search-index.json"
    if not idx_file.exists():
        raise HTTPException(status_code=404, detail="Indeks buku tidak ditemukan")

    with open(idx_file, "r", encoding="utf-8") as f:
        idx_data = json.load(f)

    pages = idx_data.get("pages", [])
    tokens = [w.lower() for w in re.findall(r"[a-zA-Z0-9]{3,}", req.question)]

    scored_pages = []
    for p in pages:
        txt = p.get("text", "")
        txt_lower = txt.lower()
        score = sum(3 for t in tokens if t in txt_lower)
        if p.get("page") == req.currentPage:
            score += 1  # slight boost for current page context
        if score > 0:
            scored_pages.append((score, p["page"], txt))

    scored_pages.sort(key=lambda x: (-x[0], x[1]))

    if not scored_pages:
        cur_p = next((p for p in pages if p["page"] == req.currentPage), pages[0] if pages else {"page": 1, "text": ""})
        return {
            "answer": (
                f"Berdasarkan <b>Halaman {cur_p['page']}</b> yang sedang dibuka:<br>"
                f"{cur_p['text'][:360]}...<br><br>"
                f"<small>💡 Tip: Gunakan kata kunci spesifik seperti <i>Pythagoras</i>, <i>gradien</i>, <i>pola bilangan</i>, atau <i>lingkaran</i>.</small>"
            )
        }

    top_hits = scored_pages[:2]
    parts = []
    for _, page_num, txt in top_hits:
        parts.append(
            f"<div style='margin-bottom:8px;'>"
            f"<b style='color:#38bdf8;cursor:pointer;' onclick='goToPage({page_num})'>📖 Halaman {page_num} (Klik untuk buka):</b><br>"
            f"{txt[:320]}..."
            f"</div>"
        )
    return {"answer": "".join(parts)}
