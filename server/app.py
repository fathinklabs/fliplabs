#!/usr/bin/env python3
"""
FlipLabs Lightweight Production Backend Server (FastAPI)
--------------------------------------------------------
Provides 3D E-Book Viewer, Virtual Bookcase, PDF Ingestion Converter,
User Registration, Authentication, Role & License Plan Management, and Admin Console.
"""

import datetime
import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "converter"))
sys.path.insert(0, str(ROOT_DIR / "server"))

from converter import LICENSE_PRESETS, convert_pdf_to_flipbook, slugify  # noqa: E402
from auth_db import (  # noqa: E402
    create_session,
    delete_session,
    get_all_book_stats,
    get_conn,
    get_user_by_token,
    hash_password,
    increment_book_view,
    init_db,
    verify_password,
)

BOOKS_DIR = ROOT_DIR / "books"
VIEWER_DIR = ROOT_DIR / "viewer"
BOOKCASE_DIR = ROOT_DIR / "bookcase"
ADMIN_DIR = ROOT_DIR / "admin"
UPLOADS_DIR = ROOT_DIR / "server" / "uploads"

BOOKS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="FlipLabs — Labschool Interactive 3D E-Book Platform",
    description="Perpustakaan Digital 3D, Konversi E-Book & Manajemen Lisensi Labschool (books.labschool.xyz)",
    version="2.0.0",
)


@app.on_event("startup")
def on_startup():
    init_db()
    if not (BOOKS_DIR / "smp8-matematika" / "book-config.json").exists():
        try:
            from generate_sample_books import main as gen_samples
            gen_samples()
        except Exception as exc:
            print(f"[WARN] Could not auto-generate sample books: {exc}")


@app.get("/books/{book_id}/book-config.json")
def serve_sanitized_book_config(book_id: str):
    """Serve book-config.json with password stripped so it cannot be read via DevTools."""
    cfg_path = BOOKS_DIR / book_id / "book-config.json"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail="Config buku tidak ditemukan")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    sec = cfg.get("security", {})
    has_pw = bool(sec.get("isPasswordProtected") and sec.get("password"))
    cfg["security"] = {
        "isPasswordProtected": has_pw,
        "disableRightClick": sec.get("disableRightClick", False),
        "allowedDomains": sec.get("allowedDomains", []),
    }
    return JSONResponse(cfg)


class VerifyBookPasswordRequest(BaseModel):
    password: str


@app.post("/api/books/{book_id}/verify-password")
def verify_book_password(
    book_id: str,
    req: VerifyBookPasswordRequest,
    authorization: Optional[str] = Header(None),
):
    cfg_path = BOOKS_DIR / book_id / "book-config.json"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    sec = cfg.get("security", {})
    real_pw = sec.get("password", "")
    if not sec.get("isPasswordProtected") or not real_pw:
        return {"status": "ok", "unlocked": True}

    # Allow admin bypass if requested with __ADMIN_BYPASS__
    user = get_user_by_token(authorization)
    if user and user.get("role") == "admin" and req.password == "__ADMIN_BYPASS__":
        return {"status": "ok", "unlocked": True}

    if req.password == real_pw:
        return {"status": "ok", "unlocked": True}
    raise HTTPException(status_code=401, detail="Kata sandi buku salah. Silakan coba lagi.")


# Static file mounts
app.mount("/viewer", StaticFiles(directory=str(VIEWER_DIR), html=True), name="viewer")
app.mount("/bookcase", StaticFiles(directory=str(BOOKCASE_DIR), html=True), name="bookcase")
app.mount("/admin-assets", StaticFiles(directory=str(ADMIN_DIR), html=True), name="admin_assets")
app.mount("/books", StaticFiles(directory=str(BOOKS_DIR)), name="books")


def get_current_user(authorization: Optional[str] = Header(None)) -> Optional[Dict[str, Any]]:
    return get_user_by_token(authorization)


def require_user(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = get_user_by_token(authorization)
    if not user:
        raise HTTPException(status_code=401, detail="Silakan login terlebih dahulu")
    return user


def require_admin(authorization: Optional[str] = Header(None)) -> Dict[str, Any]:
    user = require_user(authorization)
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Akses khusus Administrator")
    return user


@app.api_route("/health", methods=["GET", "HEAD"])
def health_check():
    return {"status": "ok", "service": "fliplabs", "domain": "books.labschool.xyz", "version": "2.0.0"}


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_bookcase_home():
    return FileResponse(str(BOOKCASE_DIR / "index.html"))


@app.api_route("/admin", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_admin_portal():
    return FileResponse(str(ADMIN_DIR / "index.html"))


@app.api_route("/view/{book_id}", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_book_viewer(book_id: str):
    cfg_path = BOOKS_DIR / book_id / "book-config.json"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail=f"Buku '{book_id}' tidak ditemukan")
    increment_book_view(book_id)
    return FileResponse(str(VIEWER_DIR / "index.html"))


# ============================================================================
# AUTHENTICATION & REGISTRATION ENDPOINTS
# ============================================================================

class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    unit: str = "SMP Labschool Jakarta"
    role: str = "siswa"  # siswa | guru


class ProfileUpdateRequest(BaseModel):
    name: str
    unit: str
    new_password: Optional[str] = None


@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    conn = get_conn()
    row = conn.execute(
        "SELECT * FROM users WHERE lower(email) = lower(?)",
        (req.email.strip(),),
    ).fetchone()
    conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Email atau kata sandi tidak sesuai")

    if row["status"] != "active":
        raise HTTPException(status_code=403, detail="Akun Anda sedang dinonaktifkan oleh Administrator")

    token = create_session(row["id"])
    user_dict = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "license_tier": row["license_tier"],
        "unit": row["unit"],
        "status": row["status"],
    }
    return {"status": "ok", "token": token, "user": user_dict}


@app.post("/api/auth/register")
def register_endpoint(req: RegisterRequest):
    email = req.email.strip().lower()
    if "@" not in email or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Email harus valid dan password minimal 6 karakter")

    role = req.role.lower() if req.role.lower() in ("siswa", "guru") else "siswa"
    default_tier = "pro" if role == "guru" else "basic"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()

    conn = get_conn()
    existing = conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if existing:
        conn.close()
        raise HTTPException(status_code=409, detail="Email sudah terdaftar. Silakan langsung login.")

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO users (name, email, password_hash, role, license_tier, unit, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, 'active', ?)
        """,
        (req.name.strip(), email, hash_password(req.password), role, default_tier, req.unit.strip(), now),
    )
    user_id = cur.lastrowid
    conn.commit()
    conn.close()

    token = create_session(user_id)
    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": user_id,
            "name": req.name.strip(),
            "email": email,
            "role": role,
            "license_tier": default_tier,
            "unit": req.unit.strip(),
            "status": "active",
        },
    }


@app.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None)):
    delete_session(authorization)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me_endpoint(user: Dict[str, Any] = Depends(require_user)):
    return {"status": "ok", "user": user}


@app.put("/api/auth/profile")
def update_my_profile(req: ProfileUpdateRequest, user: Dict[str, Any] = Depends(require_user)):
    conn = get_conn()
    if req.new_password and len(req.new_password) >= 6:
        conn.execute(
            "UPDATE users SET name = ?, unit = ?, password_hash = ? WHERE id = ?",
            (req.name.strip(), req.unit.strip(), hash_password(req.new_password), user["id"]),
        )
    else:
        conn.execute(
            "UPDATE users SET name = ?, unit = ? WHERE id = ?",
            (req.name.strip(), req.unit.strip(), user["id"]),
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Profil berhasil diperbarui"}


# ============================================================================
# BOOKS CATALOG & UPLOAD ENDPOINTS
# ============================================================================

@app.get("/api/books")
def list_books(authorization: Optional[str] = Header(None)):
    user = get_user_by_token(authorization)
    is_admin = bool(user and user.get("role") == "admin")
    stats_map = get_all_book_stats()
    books: List[Dict[str, Any]] = []
    if BOOKS_DIR.exists():
        for folder in sorted(BOOKS_DIR.iterdir()):
            cfg_file = folder / "book-config.json"
            if folder.is_dir() and cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        b = json.load(f)
                    st = stats_map.get(b.get("id", folder.name), {})
                    b["viewsCount"] = st.get("views_count", 0)
                    b["ownerEmail"] = st.get("owner_email", "labsdul@gmail.com")
                    b["visibility"] = st.get("visibility", "public")
                    sec = b.get("security", {})
                    has_pw = bool(sec.get("isPasswordProtected") and sec.get("password"))
                    b["isPasswordProtected"] = has_pw
                    if not is_admin and "security" in b:
                        b["security"] = {
                            "isPasswordProtected": has_pw,
                            "disableRightClick": sec.get("disableRightClick", False),
                        }
                    books.append(b)
                except Exception:
                    continue
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
    bookPassword: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF (.pdf)")

    current_user = get_user_by_token(authorization)
    owner_email = current_user["email"] if current_user else "labsdul@gmail.com"

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
            password=bookPassword.strip(),
        )
        conn = get_conn()
        conn.execute(
            """
            INSERT INTO book_stats (book_id, owner_email, views_count, downloads_count, visibility)
            VALUES (?, ?, 1, 0, 'public')
            ON CONFLICT(book_id) DO UPDATE SET owner_email = excluded.owner_email
            """,
            (book_slug, owner_email),
        )
        conn.commit()
        conn.close()
        return JSONResponse({"status": "success", "book": cfg})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal mengonversi PDF: {exc}")


# ============================================================================
# ADMIN & MANAGEMENT ENDPOINTS (USERS, ROLES, PLANS, BOOKS)
# ============================================================================

class AdminCreateUserRequest(BaseModel):
    name: str
    email: str
    password: str
    role: str = "siswa"
    license_tier: str = "basic"
    unit: str = "SMP Labschool Jakarta"
    status: str = "active"


class AdminUpdateUserRequest(BaseModel):
    name: str
    role: str
    license_tier: str
    unit: str
    status: str
    new_password: Optional[str] = None


class AdminUpdateBookRequest(BaseModel):
    title: str
    author: str
    category: str
    subject: str
    licenseTier: str
    visibility: str = "public"
    isPasswordProtected: bool = False
    bookPassword: Optional[str] = None


@app.get("/api/admin/overview")
def admin_overview(user: Dict[str, Any] = Depends(require_user)):
    conn = get_conn()
    users = [dict(r) for r in conn.execute("SELECT id, role, license_tier, status FROM users").fetchall()]
    conn.close()

    books_resp = list_books(None)["books"]
    total_views = sum(b.get("viewsCount", 0) for b in books_resp)
    total_pages = sum(b.get("totalPageCount", 0) for b in books_resp)

    plan_counts = {"basic": 0, "pro": 0, "enterprise": 0}
    role_counts = {"admin": 0, "guru": 0, "siswa": 0}
    for u in users:
        t = u["license_tier"].lower()
        if t in plan_counts:
            plan_counts[t] += 1
        r = u["role"].lower()
        if r in role_counts:
            role_counts[r] += 1

    return {
        "totalUsers": len(users),
        "totalBooks": len(books_resp),
        "totalPagesRendered": total_pages,
        "totalBookViews": total_views,
        "planDistribution": plan_counts,
        "roleDistribution": role_counts,
    }


@app.get("/api/admin/users")
def admin_list_users(admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, name, email, role, license_tier, unit, status, created_at, last_login
        FROM users
        ORDER BY CASE role WHEN 'admin' THEN 1 WHEN 'guru' THEN 2 ELSE 3 END, id ASC
        """
    ).fetchall()
    conn.close()
    return {"total": len(rows), "users": [dict(r) for r in rows]}


@app.post("/api/admin/users")
def admin_create_user(req: AdminCreateUserRequest, admin: Dict[str, Any] = Depends(require_admin)):
    email = req.email.strip().lower()
    if "@" not in email or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Email harus valid dan password minimal 6 karakter")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_conn()
    if conn.execute("SELECT id FROM users WHERE lower(email) = ?", (email,)).fetchone():
        conn.close()
        raise HTTPException(status_code=409, detail="Email sudah terdaftar")

    conn.execute(
        """
        INSERT INTO users (name, email, password_hash, role, license_tier, unit, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            req.name.strip(),
            email,
            hash_password(req.password),
            req.role.lower(),
            req.license_tier.lower(),
            req.unit.strip(),
            req.status.lower(),
            now,
        ),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": f"Pengguna {email} berhasil ditambahkan"}


@app.put("/api/admin/users/{user_id}")
def admin_update_user(user_id: int, req: AdminUpdateUserRequest, admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_conn()
    target = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target:
        conn.close()
        raise HTTPException(status_code=404, detail="Pengguna tidak ditemukan")

    if req.new_password and len(req.new_password.strip()) >= 6:
        conn.execute(
            """
            UPDATE users
            SET name = ?, role = ?, license_tier = ?, unit = ?, status = ?, password_hash = ?
            WHERE id = ?
            """,
            (
                req.name.strip(),
                req.role.lower(),
                req.license_tier.lower(),
                req.unit.strip(),
                req.status.lower(),
                hash_password(req.new_password.strip()),
                user_id,
            ),
        )
    else:
        conn.execute(
            """
            UPDATE users
            SET name = ?, role = ?, license_tier = ?, unit = ?, status = ?
            WHERE id = ?
            """,
            (
                req.name.strip(),
                req.role.lower(),
                req.license_tier.lower(),
                req.unit.strip(),
                req.status.lower(),
                user_id,
            ),
        )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Data pengguna berhasil diperbarui"}


@app.delete("/api/admin/users/{user_id}")
def admin_delete_user(user_id: int, admin: Dict[str, Any] = Depends(require_admin)):
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Tidak dapat menghapus akun Anda sendiri yang sedang aktif")
    conn = get_conn()
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Pengguna dihapus"}


@app.put("/api/admin/books/{book_id}")
def admin_update_book(book_id: str, req: AdminUpdateBookRequest, user: Dict[str, Any] = Depends(require_user)):
    if user["role"] not in ("admin", "guru"):
        raise HTTPException(status_code=403, detail="Hanya Admin atau Guru yang dapat mengubah pengaturan buku")

    cfg_path = BOOKS_DIR / book_id / "book-config.json"
    if not cfg_path.exists():
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")

    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    tier = req.licenseTier.lower() if req.licenseTier.lower() in LICENSE_PRESETS else "enterprise"
    cfg["title"] = req.title.strip()
    cfg["author"] = req.author.strip()
    cfg["category"] = req.category.strip()
    cfg["subject"] = req.subject.strip()
    cfg["licenseTier"] = tier
    cfg["features"].update(LICENSE_PRESETS[tier])

    if "security" not in cfg:
        cfg["security"] = {}
    cfg["security"]["isPasswordProtected"] = bool(req.isPasswordProtected)
    if req.bookPassword is not None and req.bookPassword.strip() != "":
        cfg["security"]["password"] = req.bookPassword.strip()
    elif not req.isPasswordProtected:
        cfg["security"]["password"] = ""

    with open(cfg_path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO book_stats (book_id, visibility) VALUES (?, ?)
        ON CONFLICT(book_id) DO UPDATE SET visibility = excluded.visibility
        """,
        (book_id, req.visibility),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "book": cfg}


@app.delete("/api/admin/books/{book_id}")
def admin_delete_book(book_id: str, admin: Dict[str, Any] = Depends(require_admin)):
    book_folder = BOOKS_DIR / book_id
    if not book_folder.exists():
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    shutil.rmtree(book_folder, ignore_errors=True)
    conn = get_conn()
    conn.execute("DELETE FROM book_stats WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": f"Buku {book_id} berhasil dihapus"}


# ============================================================================
# AI BOOK TUTOR ENDPOINT
# ============================================================================

class AIChatRequest(BaseModel):
    bookId: str
    currentPage: int = 1
    question: str


@app.post("/api/ai-chat")
def ai_book_assistant(req: AIChatRequest):
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
            score += 1
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
