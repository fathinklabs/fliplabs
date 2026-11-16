#!/usr/bin/env python3
"""
FlipLabs Automated PDF Ingestion & Multi-Tier WebP Converter Pipeline
---------------------------------------------------------------------
Converts any PDF into a FlipHTML5-compatible self-hosted book folder:
- files/large/{page}.webp  (Desktop & High-Res Zoom, max 2000px, q=82)
- files/mobile/{page}.webp (Mobile & Tablet, max 1000px, q=75)
- files/thumb/{page}.webp  (Thumbnail Drawer & Grid, max 260px, q=65)
- files/shot.jpg           (Cover OpenGraph / Bookcase Preview)
- files/book.pdf           (Original PDF copy for optional download)
- toc.json                 (Hierarchical Table of Contents)
- search-index.json        (Full-text search index + word coordinates)
- book-config.json         (Viewer configuration & license plan tier)
"""

import argparse
import concurrent.futures
import datetime
import json
import os
import re
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import fitz  # PyMuPDF
from PIL import Image

LICENSE_PRESETS: Dict[str, Dict[str, Any]] = {
    "basic": {
        "enableFlipSound": True,
        "enableBackgroundSound": False,
        "enableDownload": False,
        "enablePrint": False,
        "enableSearch": True,
        "enableBookmarks": False,
        "enableAnnotations": False,
        "enableFlipShot": False,
        "enableThumbnails": True,
        "enableTOC": True,
        "enableAutoPlay": True,
        "enableShare": True,
        "enableMagnifier": False,
        "enableAIQuery": False,
    },
    "pro": {
        "enableFlipSound": True,
        "enableBackgroundSound": True,
        "enableDownload": True,
        "enablePrint": True,
        "enableSearch": True,
        "enableBookmarks": True,
        "enableAnnotations": True,
        "enableFlipShot": True,
        "enableThumbnails": True,
        "enableTOC": True,
        "enableAutoPlay": True,
        "enableShare": True,
        "enableMagnifier": True,
        "enableAIQuery": False,
    },
    "enterprise": {
        "enableFlipSound": True,
        "enableBackgroundSound": True,
        "enableDownload": True,
        "enablePrint": True,
        "enableSearch": True,
        "enableBookmarks": True,
        "enableAnnotations": True,
        "enableFlipShot": True,
        "enableThumbnails": True,
        "enableTOC": True,
        "enableAutoPlay": True,
        "enableShare": True,
        "enableMagnifier": True,
        "enableAIQuery": True,
    },
}


def slugify(value: str) -> str:
    value = value.lower().strip()
    value = re.sub(r"[^a-z0-9\-_]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or f"book-{int(time.time())}"


def render_single_page(
    pdf_path: str,
    page_idx: int,
    out_dir: Path,
) -> Dict[str, Any]:
    """Worker function to render a single PDF page into multi-tier WebP & extract text."""
    doc = fitz.open(pdf_path)
    page = doc.load_page(page_idx)
    page_num = page_idx + 1

    rect = page.rect
    width_pt, height_pt = rect.width, rect.height

    # Render high-res pixmap (target max dimension ~1800-2000px)
    scale = min(2000.0 / max(width_pt, height_pt, 1), 2.5)
    mat = fitz.Matrix(scale, scale)
    pix = page.get_pixmap(matrix=mat, alpha=False)

    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # 1. Save Large WebP (up to 2000px)
    large_path = out_dir / "files" / "large" / f"{page_num}.webp"
    img.save(large_path, "WEBP", quality=82, method=4)

    # 2. Save Mobile WebP (max height 1050px)
    mob_ratio = min(1050.0 / max(img.height, 1), 1.0)
    mob_size = (max(1, int(img.width * mob_ratio)), max(1, int(img.height * mob_ratio)))
    img_mobile = img.resize(mob_size, Image.Resampling.LANCZOS)
    mobile_path = out_dir / "files" / "mobile" / f"{page_num}.webp"
    img_mobile.save(mobile_path, "WEBP", quality=75, method=4)

    # 3. Save Thumbnail WebP (max height 260px)
    thumb_ratio = min(260.0 / max(img.height, 1), 1.0)
    thumb_size = (max(1, int(img.width * thumb_ratio)), max(1, int(img.height * thumb_ratio)))
    img_thumb = img.resize(thumb_size, Image.Resampling.LANCZOS)
    thumb_path = out_dir / "files" / "thumb" / f"{page_num}.webp"
    img_thumb.save(thumb_path, "WEBP", quality=65, method=4)

    # 4. If Page 1, also save shot.jpg for OpenGraph & Bookcase cover
    if page_num == 1:
        shot_ratio = min(600.0 / max(img.height, 1), 1.0)
        shot_size = (max(1, int(img.width * shot_ratio)), max(1, int(img.height * shot_ratio)))
        img_shot = img.resize(shot_size, Image.Resampling.LANCZOS)
        img_shot.save(out_dir / "files" / "shot.jpg", "JPEG", quality=85)

    # 5. Extract full text & normalized word boxes for search highlight overlay
    raw_text = page.get_text("text").strip()
    clean_text = re.sub(r"\s+", " ", raw_text)

    # Extract words with normalized coordinates [x0, y0, x1, y1, word] in percentages (0..100)
    words_raw = page.get_text("words")
    words_norm = []
    for w in words_raw[:800]:  # cap per page to keep JSON super compact
        x0, y0, x1, y1, word_str = w[0], w[1], w[2], w[3], w[4]
        if len(word_str.strip()) < 2:
            continue
        words_norm.append({
            "w": word_str,
            "x": round((x0 / width_pt) * 100, 2),
            "y": round((y0 / height_pt) * 100, 2),
            "width": round(((x1 - x0) / width_pt) * 100, 2),
            "height": round(((y1 - y0) / height_pt) * 100, 2),
        })

    doc.close()
    return {
        "page": page_num,
        "width": pix.width,
        "height": pix.height,
        "text": clean_text,
        "words": words_norm,
    }


def extract_toc(doc: fitz.Document, page_texts: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Extracts PDF outline into hierarchical TOC JSON, or auto-detects headings."""
    raw_toc = doc.get_toc()
    if raw_toc:
        root: List[Dict[str, Any]] = []
        stack: List[tuple] = []  # (level, node)
        for item in raw_toc:
            lvl, title, page_num = item[0], item[1].strip(), max(1, item[2])
            node: Dict[str, Any] = {"title": title, "page": page_num, "children": []}
            while stack and stack[-1][0] >= lvl:
                stack.pop()
            if not stack:
                root.append(node)
            else:
                stack[-1][1]["children"].append(node)
            stack.append((lvl, node))
        return root

    # Fallback: auto-generate smart TOC from pages
    auto_toc = []
    for p in page_texts:
        txt = p["text"]
        first_line = txt.split("\n")[0][:65].strip() if txt else f"Halaman {p['page']}"
        if p["page"] == 1:
            auto_toc.append({"title": "Sampul Depan (Cover)", "page": 1, "children": []})
        elif re.search(r"\b(bab|chapter|bagian|kompetensi|latihan|daftar isi|kata pengantar)\b", txt[:160], re.I):
            auto_toc.append({"title": first_line or f"Halaman {p['page']}", "page": p["page"], "children": []})
    if len(auto_toc) <= 1:
        for p in page_texts:
            auto_toc.append({"title": f"Halaman {p['page']}", "page": p["page"], "children": []})
    return auto_toc


def convert_pdf_to_flipbook(
    pdf_path: str,
    books_root: str,
    book_id: Optional[str] = None,
    title: Optional[str] = None,
    subtitle: str = "Kurikulum Merdeka - Labschool Digital Library",
    author: str = "Tim Guru Labschool",
    category: str = "SMP Kelas 8",
    subject: str = "Matematika",
    license_tier: str = "enterprise",
    password: str = "",
    max_workers: int = 4,
) -> Dict[str, Any]:
    """Main pipeline to convert PDF into FlipLabs book bundle."""
    t0 = time.time()
    pdf_file = Path(pdf_path).resolve()
    if not pdf_file.exists():
        raise FileNotFoundError(f"PDF file not found: {pdf_file}")

    doc = fitz.open(str(pdf_file))
    total_pages = len(doc)
    meta = doc.metadata or {}

    final_title = title or meta.get("title") or pdf_file.stem.replace("-", " ").replace("_", " ").title()
    final_author = author or meta.get("author") or "Tim Guru Labschool"
    final_id = slugify(book_id or final_title)

    out_dir = Path(books_root).resolve() / final_id
    for sub in ["files/large", "files/mobile", "files/thumb"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    # Copy original PDF for download feature
    shutil.copy2(pdf_file, out_dir / "files" / "book.pdf")

    # Render pages in parallel
    page_results: List[Dict[str, Any]] = []
    workers = min(max_workers, os.cpu_count() or 2, max(1, total_pages))

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(render_single_page, str(pdf_file), idx, out_dir): idx
            for idx in range(total_pages)
        }
        for future in concurrent.futures.as_completed(futures):
            page_results.append(future.result())

    page_results.sort(key=lambda x: x["page"])

    # Extract TOC
    toc_data = extract_toc(doc, page_results)
    doc.close()

    # Save toc.json
    with open(out_dir / "toc.json", "w", encoding="utf-8") as f:
        json.dump(toc_data, f, ensure_ascii=False, indent=2)

    # Save search-index.json
    search_data = {
        "bookId": final_id,
        "totalPages": total_pages,
        "pages": [
            {
                "page": p["page"],
                "text": p["text"],
                "words": p["words"],
            }
            for p in page_results
        ],
    }
    with open(out_dir / "search-index.json", "w", encoding="utf-8") as f:
        json.dump(search_data, f, ensure_ascii=False)

    # Build book-config.json
    first_w = page_results[0]["width"] if page_results else 800
    first_h = page_results[0]["height"] if page_results else 1131
    tier = license_tier.lower() if license_tier.lower() in LICENSE_PRESETS else "enterprise"

    config_data = {
        "id": final_id,
        "title": final_title,
        "subtitle": subtitle,
        "author": final_author,
        "category": category,
        "subject": subject,
        "licenseTier": tier,
        "totalPageCount": total_pages,
        "pageWidth": first_w,
        "pageHeight": first_h,
        "pageRatio": round(first_h / max(first_w, 1), 4),
        "createdAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "conversionSeconds": round(time.time() - t0, 2),
        "theme": {
            "mode": "metro-dark",
            "toolbarColor": "#1e222d",
            "iconColor": "#f1f5f9",
            "accentColor": "#0ea5e9",
            "backgroundColor": "#11141c",
            "backgroundGradient": "radial-gradient(circle at center, #1e293b 0%, #0f172a 100%)",
        },
        "branding": {
            "logoText": "LABSCHOOL DIGITAL LIBRARY",
            "logoUrl": "/viewer/assets/branding/labschool-logo.svg",
            "linkUrl": "https://books.labschool.xyz",
            "showLogo": True,
            "watermarkText": f"LABSCHOOL DIGITAL LIBRARY • {tier.upper()} EDITION",
        },
        "features": {
            **LICENSE_PRESETS[tier],
            "downloadUrl": f"/books/{final_id}/files/book.pdf",
            "autoPlayDuration": 4,
        },
        "security": {
            "isPasswordProtected": bool(password),
            "password": password,
            "disableRightClick": tier == "enterprise",
            "allowedDomains": [
                "books.labschool.xyz",
                "study.labschool.xyz",
                "lms.labschool.xyz",
                "labschool.sch.id",
                "localhost",
                "127.0.0.1",
            ],
        },
    }

    with open(out_dir / "book-config.json", "w", encoding="utf-8") as f:
        json.dump(config_data, f, ensure_ascii=False, indent=2)

    return config_data


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert PDF to FlipLabs HTML5 Book")
    parser.add_argument("pdf", help="Path to source PDF file")
    parser.add_argument("--out", default="./books", help="Root books output directory")
    parser.add_argument("--id", default=None, help="Custom book slug ID")
    parser.add_argument("--title", default=None, help="Book title")
    parser.add_argument("--author", default="Tim Guru Labschool", help="Book author")
    parser.add_argument("--category", default="SMP Kelas 8", help="Book category / grade")
    parser.add_argument("--subject", default="Matematika", help="Subject")
    parser.add_argument("--tier", default="enterprise", choices=["basic", "pro", "enterprise"], help="License tier")
    parser.add_argument("--password", default="", help="Optional password protection")
    args = parser.parse_args()

    result = convert_pdf_to_flipbook(
        pdf_path=args.pdf,
        books_root=args.out,
        book_id=args.id,
        title=args.title,
        author=args.author,
        category=args.category,
        subject=args.subject,
        license_tier=args.tier,
        password=args.password,
    )
    print(f"[OK] Converted '{result['title']}' ({result['totalPageCount']} pages) in {result['conversionSeconds']}s -> books/{result['id']}")
