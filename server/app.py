#!/usr/bin/env python3
"""
FlipLabs Production Backend Server (FastAPI v3.0)
-------------------------------------------------
Provides:
- 3D E-Book Viewer, Virtual Bookcase, Templates Gallery, Pricing & Books Marketplace
- Google Workspace XOAUTH2 Email Verification (admin@labschool.xyz)
- 2-Digit Addition Login Captcha
- Teacher Book Selling & Student Book Buying / Personal Book Collection
"""

import datetime
import json
import os
import random
import re
import secrets
import shutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "converter"))
sys.path.insert(0, str(ROOT_DIR / "server"))

from converter import LICENSE_PRESETS, convert_pdf_to_flipbook, slugify  # noqa: E402
from auth_db import (  # noqa: E402
    create_session,
    delete_session,
    generate_math_captcha,
    get_all_book_stats,
    get_conn,
    get_user_by_token,
    get_user_owned_books,
    hash_password,
    increment_book_view,
    init_db,
    verify_math_captcha,
    verify_password,
)
from mailer import send_verification_email  # noqa: E402

BOOKS_DIR = ROOT_DIR / "books"
VIEWER_DIR = ROOT_DIR / "viewer"
BOOKCASE_DIR = ROOT_DIR / "bookcase"
ADMIN_DIR = ROOT_DIR / "admin"
UPLOADS_DIR = ROOT_DIR / "server" / "uploads"

BOOKS_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
ADMIN_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="EBOOK LABS — Labschool Interactive 3D E-Book Marketplace Platform",
    description="Marketplace Pembelian Buku Digital 3D Siswa, Panel Modul Guru (/guru) & Super Admin (/admin) — books.labschool.xyz",
    version="3.4.0",
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
def serve_sanitized_book_config(
    book_id: str,
    authorization: Optional[str] = Header(None),
):
    """Serve book-config.json with password stripped and marketplace ownership attached."""
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

    # Attach marketplace info
    stats_map = get_all_book_stats()
    st = stats_map.get(book_id, {})
    is_for_sale = bool(st.get("is_for_sale", 0) and st.get("price", 0) > 0)
    price = int(st.get("price", 0))
    preview_pages = int(st.get("preview_pages", 3))

    user = get_user_by_token(authorization)
    owned_ids = get_user_owned_books(user["email"]) if user else []
    is_owned = bool(
        not is_for_sale
        or (user and user.get("role") == "admin")
        or (book_id in owned_ids)
    )

    cfg["marketplace"] = {
        "isForSale": is_for_sale,
        "price": price,
        "previewPages": preview_pages,
        "salesCount": int(st.get("sales_count", 0)),
        "ownerEmail": st.get("owner_email", "guru@labschool.xyz"),
        "description": st.get("description", ""),
        "isOwned": is_owned,
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
    return {"status": "ok", "service": "ebook-labs", "domain": "books.labschool.xyz", "version": "3.4.0"}


@app.api_route("/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_bookcase_home():
    return FileResponse(str(BOOKCASE_DIR / "index.html"))


@app.api_route("/guru", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/guru/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_guru_panel():
    return FileResponse(str(BOOKCASE_DIR / "guru.html"))


@app.api_route("/pricing", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/fliphtml5-pricing.php", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_pricing_page():
    return FileResponse(str(BOOKCASE_DIR / "pricing.html"))


@app.api_route("/templates", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/templates/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_templates_page():
    return FileResponse(str(BOOKCASE_DIR / "templates.html"))


@app.api_route("/marketplace", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/marketplace/", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_marketplace_page():
    return FileResponse(str(BOOKCASE_DIR / "index.html"))


@app.api_route("/dashboard", methods=["GET", "HEAD"], response_class=HTMLResponse)
@app.api_route("/user", methods=["GET", "HEAD"], response_class=HTMLResponse)
def serve_user_dashboard():
    return FileResponse(str(BOOKCASE_DIR / "dashboard.html"))


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
# CAPTCHA, AUTHENTICATION & EMAIL VERIFICATION ENDPOINTS
# ============================================================================

@app.get("/api/auth/captcha")
def get_login_captcha():
    """Returns a simple 2-digit math addition challenge (e.g. 24 + 35 = ?)."""
    return generate_math_captcha()


class LoginRequest(BaseModel):
    email: str
    password: str
    captchaId: Optional[str] = None
    captchaAnswer: Optional[str] = None


class RegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    unit: str = "SMP Labschool Jakarta"
    role: str = "siswa"


class VerifyEmailOtpRequest(BaseModel):
    email: str
    otpCode: str


class ResendOtpRequest(BaseModel):
    email: str


class ProfileUpdateRequest(BaseModel):
    name: str
    unit: str
    new_password: Optional[str] = None


@app.post("/api/auth/login")
def login_endpoint(req: LoginRequest):
    # Verify 2-digit math captcha if captchaId is provided
    if req.captchaId is not None:
        if not verify_math_captcha(req.captchaId, req.captchaAnswer or ""):
            raise HTTPException(
                status_code=400,
                detail="Jawaban Captcha penjumlahan salah atau kedaluwarsa. Silakan hitung kembali.",
            )

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

    if int(row["email_verified"] or 0) == 0:
        raise HTTPException(
            status_code=403,
            detail=f"UNVERIFIED_EMAIL:{row['email']}:Alamat email belum diverifikasi. Silakan masukkan kode OTP 6 digit yang telah dikirim ke email Anda.",
        )

    token = create_session(row["id"])
    user_dict = {
        "id": row["id"],
        "name": row["name"],
        "email": row["email"],
        "role": row["role"],
        "license_tier": row["license_tier"],
        "unit": row["unit"],
        "status": row["status"],
        "email_verified": 1,
    }
    return {"status": "ok", "token": token, "user": user_dict}


@app.post("/api/auth/register")
def register_endpoint(req: RegisterRequest):
    email = req.email.strip().lower()
    if "@" not in email or len(req.password) < 6:
        raise HTTPException(status_code=400, detail="Email harus valid dan password minimal 6 karakter")

    if req.role and req.role.strip().lower() not in ("siswa", ""):
        raise HTTPException(
            status_code=403,
            detail="Pendaftaran sebagai Guru dinonaktifkan. Akun Guru ditentukan dan didaftarkan oleh Administrator. Pendaftaran di web utama hanya sebagai Siswa.",
        )

    role = "siswa"
    default_tier = "basic"
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    otp_code = str(random.randint(100000, 999999))
    verify_tok = secrets.token_urlsafe(24)

    conn = get_conn()
    existing = conn.execute("SELECT id, email_verified FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if existing:
        if int(existing["email_verified"] or 0) == 1:
            conn.close()
            raise HTTPException(status_code=409, detail="Email sudah terdaftar. Silakan langsung login.")
        else:
            # Update OTP for unverified account
            conn.execute(
                """
                UPDATE users
                SET name = ?, password_hash = ?, role = ?, license_tier = ?, unit = ?,
                    verification_code = ?, verify_token = ?
                WHERE id = ?
                """,
                (req.name.strip(), hash_password(req.password), role, default_tier, req.unit.strip(), otp_code, verify_tok, existing["id"]),
            )
            conn.commit()
            conn.close()
    else:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users
            (name, email, password_hash, role, license_tier, unit, status, email_verified, verification_code, verify_token, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'active', 0, ?, ?, ?)
            """,
            (req.name.strip(), email, hash_password(req.password), role, default_tier, req.unit.strip(), otp_code, verify_tok, now),
        )
        conn.commit()
        conn.close()

    verify_url = f"https://books.labschool.xyz/verify-email?token={verify_tok}"
    mail_res = send_verification_email(
        to_email=email,
        full_name=req.name.strip(),
        otp_code=otp_code,
        verify_url=verify_url,
    )

    return {
        "status": "pending_verification",
        "email": email,
        "mailSent": mail_res.get("success", False),
        "mailMessage": mail_res.get("message", ""),
        "message": f"Kode verifikasi OTP 6 digit telah dikirim dari admin@labschool.xyz ke {email}.",
    }


@app.post("/api/auth/verify-email")
def verify_email_otp(req: VerifyEmailOtpRequest):
    email = req.email.strip().lower()
    code = req.otpCode.strip()

    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan")

    if row["verification_code"] != code:
        conn.close()
        raise HTTPException(status_code=400, detail="Kode OTP verifikasi tidak sesuai. Silakan periksa kembali email Anda.")

    conn.execute(
        "UPDATE users SET email_verified = 1, verification_code = '', verify_token = '' WHERE id = ?",
        (row["id"],),
    )
    conn.commit()
    conn.close()

    token = create_session(row["id"])
    return {
        "status": "ok",
        "token": token,
        "user": {
            "id": row["id"],
            "name": row["name"],
            "email": row["email"],
            "role": row["role"],
            "license_tier": row["license_tier"],
            "unit": row["unit"],
            "status": row["status"],
            "email_verified": 1,
        },
    }


@app.post("/api/auth/resend-verification")
def resend_verification_otp(req: ResendOtpRequest):
    email = req.email.strip().lower()
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE lower(email) = ?", (email,)).fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Email tidak ditemukan")

    otp_code = str(random.randint(100000, 999999))
    verify_tok = secrets.token_urlsafe(24)
    conn.execute(
        "UPDATE users SET verification_code = ?, verify_token = ? WHERE id = ?",
        (otp_code, verify_tok, row["id"]),
    )
    conn.commit()
    conn.close()

    verify_url = f"https://books.labschool.xyz/verify-email?token={verify_tok}"
    mail_res = send_verification_email(
        to_email=email,
        full_name=row["name"],
        otp_code=otp_code,
        verify_url=verify_url,
    )
    return {
        "status": "ok",
        "mailSent": mail_res.get("success", False),
        "message": f"Kode OTP baru telah dikirim ulang ke {email}.",
    }


@app.get("/verify-email")
def verify_email_link(token: str = Query(...)):
    conn = get_conn()
    row = conn.execute("SELECT * FROM users WHERE verify_token = ?", (token.strip(),)).fetchone()
    if not row:
        conn.close()
        return RedirectResponse(url="/#login")

    conn.execute(
        "UPDATE users SET email_verified = 1, verification_code = '', verify_token = '' WHERE id = ?",
        (row["id"],),
    )
    conn.commit()
    conn.close()
    return RedirectResponse(url="/#verified")


@app.post("/api/auth/logout")
def logout_endpoint(authorization: Optional[str] = Header(None)):
    delete_session(authorization)
    return {"status": "ok"}


@app.get("/api/auth/me")
def me_endpoint(user: Dict[str, Any] = Depends(require_user)):
    owned = get_user_owned_books(user["email"])
    return {"status": "ok", "user": user, "ownedBooks": owned}


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
# BOOKS CATALOG, UPLOAD & MARKETPLACE ENDPOINTS
# ============================================================================

@app.get("/api/books")
def list_books(authorization: Optional[str] = Header(None)):
    user = get_user_by_token(authorization)
    is_admin = bool(user and user.get("role") == "admin")
    owned_ids = get_user_owned_books(user["email"]) if user else []
    stats_map = get_all_book_stats()

    books: List[Dict[str, Any]] = []
    if BOOKS_DIR.exists():
        for folder in sorted(BOOKS_DIR.iterdir()):
            cfg_file = folder / "book-config.json"
            if folder.is_dir() and cfg_file.exists():
                try:
                    with open(cfg_file, "r", encoding="utf-8") as f:
                        b = json.load(f)
                    bid = b.get("id", folder.name)
                    st = stats_map.get(bid, {})
                    b["viewsCount"] = st.get("views_count", 0)
                    b["ownerEmail"] = st.get("owner_email", "guru@labschool.xyz")
                    b["visibility"] = st.get("visibility", "public")
                    b["isForSale"] = bool(st.get("is_for_sale", 0) and st.get("price", 0) > 0)
                    b["price"] = int(st.get("price", 0))
                    b["previewPages"] = int(st.get("preview_pages", 3))
                    b["salesCount"] = int(st.get("sales_count", 0))
                    b["description"] = st.get("description", b.get("subtitle", ""))
                    b["isOwned"] = bool(is_admin or (bid in owned_ids))

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
    price: int = Form(0),
    previewPages: int = Form(3),
    description: str = Form(""),
    authorization: Optional[str] = Header(None),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File harus berformat PDF (.pdf)")

    current_user = get_user_by_token(authorization)
    if not current_user:
        raise HTTPException(
            status_code=401,
            detail="Akses ditolak: Silakan masuk ke akun Guru Anda terlebih dahulu.",
        )
    if current_user.get("role") not in ("guru", "admin"):
        raise HTTPException(
            status_code=403,
            detail="Akses ditolak: Fitur Upload PDF dan membuat Flipbook hanya tersedia untuk Guru melalui panel books.labschool.xyz/guru.",
        )
    owner_email = current_user["email"]

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
        clean_price = max(0, int(price))
        is_sale = 1 if clean_price > 0 else 0
        conn = get_conn()
        conn.execute(
            """
            INSERT INTO book_stats
            (book_id, owner_email, views_count, downloads_count, visibility, is_for_sale, price, preview_pages, sales_count, description)
            VALUES (?, ?, 1, 0, 'public', ?, ?, ?, 0, ?)
            ON CONFLICT(book_id) DO UPDATE SET
              owner_email = excluded.owner_email,
              is_for_sale = excluded.is_for_sale,
              price = excluded.price,
              preview_pages = excluded.preview_pages,
              description = excluded.description
            """,
            (book_slug, owner_email, is_sale, clean_price, max(1, int(previewPages)), description.strip()),
        )
        conn.commit()
        conn.close()
        return JSONResponse({"status": "success", "book": cfg})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Gagal mengonversi PDF: {exc}")


class BuyBookRequest(BaseModel):
    paymentMethod: str = "QRIS"


@app.post("/api/marketplace/buy/{book_id}")
def buy_marketplace_book(
    book_id: str,
    req: BuyBookRequest,
    user: Dict[str, Any] = Depends(require_user),
):
    stats_map = get_all_book_stats()
    st = stats_map.get(book_id)
    if not st:
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan di Marketplace")

    price = int(st.get("price", 0))
    seller_email = st.get("owner_email", "guru@labschool.xyz")
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    invoice_id = f"INV-{datetime.datetime.now().strftime('%Y%m%d')}-{secrets.token_hex(3).upper()}"

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO book_purchases (invoice_id, book_id, buyer_email, seller_email, amount, payment_method, purchased_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (invoice_id, book_id, user["email"], seller_email, price, req.paymentMethod, now),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO user_collections (user_email, book_id, source, added_at)
        VALUES (?, ?, 'purchased', ?)
        """,
        (user["email"], book_id, now),
    )
    conn.execute(
        "UPDATE book_stats SET sales_count = sales_count + 1 WHERE book_id = ?",
        (book_id,),
    )
    conn.commit()
    conn.close()

    return {
        "status": "ok",
        "invoiceId": invoice_id,
        "bookId": book_id,
        "amount": price,
        "paymentMethod": req.paymentMethod,
        "message": f"Pembelian berhasil ({invoice_id})! Buku telah ditambahkan ke Koleksi Buku Anda.",
    }


@app.post("/api/marketplace/collect/{book_id}")
def add_to_my_collection(book_id: str, user: Dict[str, Any] = Depends(require_user)):
    stats_map = get_all_book_stats()
    st = stats_map.get(book_id, {})
    if st.get("is_for_sale") and int(st.get("price", 0)) > 0:
        owned = get_user_owned_books(user["email"])
        if book_id not in owned:
            raise HTTPException(status_code=402, detail="Buku berbayar harus dibeli terlebih dahulu")

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    conn = get_conn()
    conn.execute(
        """
        INSERT OR IGNORE INTO user_collections (user_email, book_id, source, added_at)
        VALUES (?, ?, 'saved', ?)
        """,
        (user["email"], book_id, now),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Buku berhasil disimpan ke Koleksi Buku Saya!"}


@app.delete("/api/marketplace/collect/{book_id}")
def remove_from_my_collection(book_id: str, user: Dict[str, Any] = Depends(require_user)):
    conn = get_conn()
    conn.execute(
        "DELETE FROM user_collections WHERE lower(user_email) = lower(?) AND book_id = ?",
        (user["email"], book_id),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "message": "Buku dihapus dari Koleksi Buku Saya"}


@app.get("/api/marketplace/my-collection")
def get_my_collection_and_sales(user: Dict[str, Any] = Depends(require_user)):
    conn = get_conn()
    col_rows = conn.execute(
        """
        SELECT book_id FROM user_collections WHERE lower(user_email) = lower(?)
        UNION
        SELECT book_id FROM book_purchases WHERE lower(buyer_email) = lower(?)
        """,
        (user["email"], user["email"]),
    ).fetchall()
    collected_ids = {r["book_id"] for r in col_rows}

    all_books = list_books("Bearer ")["books"]
    my_uploaded_books = []
    my_collected_books = []
    for b in all_books:
        is_mine = str(b.get("ownerEmail", "")).lower() == user["email"].lower()
        if is_mine:
            b["isOwned"] = True
            my_uploaded_books.append(b)
        if b["id"] in collected_ids:
            b["isOwned"] = True
            my_collected_books.append(b)

    purchases = [
        dict(r)
        for r in conn.execute(
            "SELECT * FROM book_purchases WHERE lower(buyer_email) = lower(?) ORDER BY id DESC",
            (user["email"],),
        ).fetchall()
    ]
    if user["role"] == "admin":
        sales = [
            dict(r)
            for r in conn.execute("SELECT * FROM book_purchases ORDER BY id DESC").fetchall()
        ]
    else:
        sales = [
            dict(r)
            for r in conn.execute(
                "SELECT * FROM book_purchases WHERE lower(seller_email) = lower(?) ORDER BY id DESC",
                (user["email"],),
            ).fetchall()
        ]
    conn.close()

    total_revenue = sum(int(s.get("amount", 0)) for s in sales)
    return {
        "uploadedBooks": my_uploaded_books,
        "collection": my_collected_books,
        "purchases": purchases,
        "sales": sales,
        "totalRevenue": total_revenue,
    }


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
    isForSale: bool = False
    price: int = 0
    previewPages: int = 3
    description: Optional[str] = ""


@app.get("/api/admin/overview")
def admin_overview(admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_conn()
    users = [dict(r) for r in conn.execute("SELECT id, role, license_tier, status FROM users").fetchall()]
    sales_rows = conn.execute("SELECT SUM(amount) AS rev, COUNT(*) AS cnt FROM book_purchases").fetchone()
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
        "totalSalesCount": int(sales_rows["cnt"] or 0) if sales_rows else 0,
        "totalSalesRevenue": int(sales_rows["rev"] or 0) if sales_rows else 0,
        "planDistribution": plan_counts,
        "roleDistribution": role_counts,
    }


@app.get("/api/admin/users")
def admin_list_users(admin: Dict[str, Any] = Depends(require_admin)):
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT id, name, email, role, license_tier, unit, status, email_verified, created_at, last_login
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
        INSERT INTO users (name, email, password_hash, role, license_tier, unit, status, email_verified, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?)
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
    stats_map = get_all_book_stats()
    st = stats_map.get(book_id, {})
    owner_email = str(st.get("owner_email", "guru@labschool.xyz")).lower()
    if user["role"] != "admin" and owner_email != user["email"].lower():
        raise HTTPException(status_code=403, detail="Anda hanya dapat mengubah buku milik Anda sendiri")

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

    clean_price = max(0, int(req.price)) if req.isForSale else 0
    is_sale_int = 1 if (req.isForSale and clean_price > 0) else 0

    conn = get_conn()
    conn.execute(
        """
        INSERT INTO book_stats (book_id, visibility, is_for_sale, price, preview_pages, description)
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(book_id) DO UPDATE SET
          visibility = excluded.visibility,
          is_for_sale = excluded.is_for_sale,
          price = excluded.price,
          preview_pages = excluded.preview_pages,
          description = excluded.description
        """,
        (book_id, req.visibility, is_sale_int, clean_price, max(1, int(req.previewPages)), (req.description or "").strip()),
    )
    conn.commit()
    conn.close()
    return {"status": "ok", "book": cfg}


@app.delete("/api/admin/books/{book_id}")
def admin_delete_book(book_id: str, user: Dict[str, Any] = Depends(require_user)):
    stats_map = get_all_book_stats()
    st = stats_map.get(book_id, {})
    owner_email = str(st.get("owner_email", "guru@labschool.xyz")).lower()
    if user["role"] != "admin" and owner_email != user["email"].lower():
        raise HTTPException(status_code=403, detail="Hanya Super Admin atau pemilik buku yang dapat menghapus buku ini")

    book_folder = BOOKS_DIR / book_id
    if not book_folder.exists():
        raise HTTPException(status_code=404, detail="Buku tidak ditemukan")
    shutil.rmtree(book_folder, ignore_errors=True)
    conn = get_conn()
    conn.execute("DELETE FROM book_stats WHERE book_id = ?", (book_id,))
    conn.commit()
    conn.close()
    return {"status": "ok", "message": f"Buku {book_id} berhasil dihapus"}

