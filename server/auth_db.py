#!/usr/bin/env python3
"""
FlipLabs Authentication, Email Verification, 2-Digit Captcha, User Management
& Books Marketplace Module (SQLite)
-----------------------------------------------------------------------------
Persists users, email OTP verification, login math captcha, sessions, roles,
license plans, teacher book sales, and student book collections in fliplabs.db.
"""

import datetime
import hashlib
import hmac
import os
import random
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "books" / "fliplabs.db"
SECRET_SALT = os.environ.get("FLIPLABS_SECRET", "fliplabs-labschool-secret-key-2026")

# In-memory store for 2-digit math captchas: {captcha_id: (answer_int, expires_epoch)}
_CAPTCHA_STORE: Dict[str, Tuple[int, float]] = {}


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def hash_password(password: str) -> str:
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        SECRET_SALT.encode("utf-8"),
        100_000,
    )
    return dk.hex()


def verify_password(password: str, hashed: str) -> bool:
    return hmac.compare_digest(hash_password(password), hashed)


def generate_math_captcha() -> Dict[str, Any]:
    """Generates a simple 2-digit addition captcha (e.g., 24 + 35 = ?)."""
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    # Clean expired captchas
    expired = [cid for cid, (_, exp) in _CAPTCHA_STORE.items() if exp < now]
    for cid in expired:
        _CAPTCHA_STORE.pop(cid, None)

    a = random.randint(10, 49)
    b = random.randint(10, 49)
    cid = secrets.token_hex(12)
    _CAPTCHA_STORE[cid] = (a + b, now + 600)
    return {
        "captchaId": cid,
        "numA": a,
        "numB": b,
        "question": f"{a} + {b} = ?",
    }


def verify_math_captcha(captcha_id: str, answer_str: str) -> bool:
    if not captcha_id or answer_str is None:
        return False
    entry = _CAPTCHA_STORE.pop(captcha_id, None)
    if not entry:
        return False
    expected, exp = entry
    now = datetime.datetime.now(datetime.timezone.utc).timestamp()
    if now > exp:
        return False
    try:
        return int(str(answer_str).strip()) == expected
    except ValueError:
        return False


def _ensure_column(conn: sqlite3.Connection, table: str, col: str, col_def: str) -> None:
    cols = [r["name"] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()]
    if col not in cols:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")


def init_db() -> None:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'siswa',
            license_tier TEXT NOT NULL DEFAULT 'basic',
            unit TEXT NOT NULL DEFAULT 'SMP Labschool Jakarta',
            status TEXT NOT NULL DEFAULT 'active',
            email_verified INTEGER NOT NULL DEFAULT 1,
            verification_code TEXT DEFAULT '',
            verify_token TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )

    _ensure_column(conn, "users", "email_verified", "INTEGER NOT NULL DEFAULT 1")
    _ensure_column(conn, "users", "verification_code", "TEXT DEFAULT ''")
    _ensure_column(conn, "users", "verify_token", "TEXT DEFAULT ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token TEXT PRIMARY KEY,
            user_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS book_stats (
            book_id TEXT PRIMARY KEY,
            owner_email TEXT DEFAULT 'labsdul@gmail.com',
            views_count INTEGER DEFAULT 0,
            downloads_count INTEGER DEFAULT 0,
            visibility TEXT DEFAULT 'public',
            is_for_sale INTEGER DEFAULT 0,
            price INTEGER DEFAULT 0,
            preview_pages INTEGER DEFAULT 3,
            sales_count INTEGER DEFAULT 0,
            description TEXT DEFAULT ''
        )
        """
    )

    _ensure_column(conn, "book_stats", "is_for_sale", "INTEGER DEFAULT 0")
    _ensure_column(conn, "book_stats", "price", "INTEGER DEFAULT 0")
    _ensure_column(conn, "book_stats", "preview_pages", "INTEGER DEFAULT 3")
    _ensure_column(conn, "book_stats", "sales_count", "INTEGER DEFAULT 0")
    _ensure_column(conn, "book_stats", "description", "TEXT DEFAULT ''")

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS book_purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_id TEXT NOT NULL UNIQUE,
            book_id TEXT NOT NULL,
            buyer_email TEXT NOT NULL,
            seller_email TEXT NOT NULL,
            amount INTEGER NOT NULL,
            payment_method TEXT NOT NULL,
            purchased_at TEXT NOT NULL
        )
        """
    )

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS user_collections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            book_id TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'saved',
            added_at TEXT NOT NULL,
            UNIQUE(user_email, book_id)
        )
        """
    )

    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    seed_users = [
        (
            "Abdul Fathir (Super Admin)",
            "labsdul@gmail.com",
            hash_password("LLA!kcolnu@2026"),
            "admin",
            "enterprise",
            "Direktorat IT & LMS Labschool",
            "active",
            1,
            now,
        ),
        (
            "Administrator FlipLabs",
            "admin@labschool.xyz",
            hash_password("LabsAdmin2026!"),
            "admin",
            "enterprise",
            "SMP Labschool Jakarta",
            "active",
            1,
            now,
        ),
        (
            "Guru Matematika Labschool",
            "guru@labschool.xyz",
            hash_password("GuruLabs2026!"),
            "guru",
            "pro",
            "SMP Labschool Jakarta",
            "active",
            1,
            now,
        ),
        (
            "Siswa Kelas VIII Labschool",
            "siswa@labschool.xyz",
            hash_password("SiswaLabs2026!"),
            "siswa",
            "basic",
            "SMP Labschool Jakarta",
            "active",
            1,
            now,
        ),
    ]

    for u in seed_users:
        cur.execute(
            """
            INSERT OR IGNORE INTO users
            (name, email, password_hash, role, license_tier, unit, status, email_verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            u,
        )

    # Seed initial book stats & marketplace pricing
    seed_books = [
        (
            "smp8-matematika",
            "guru@labschool.xyz",
            154,
            12,
            "public",
            1,
            45000,
            3,
            24,
            "Buku Paket & Pembahasan Lengkap Matematika SMP Kelas VIII Kurikulum Merdeka (Aljabar, Kartesius, SPLDV, Pythagoras, Lingkaran & Bangun Ruang).",
        ),
        (
            "smp8-ipa-terpadu",
            "guru@labschool.xyz",
            88,
            8,
            "public",
            1,
            35000,
            2,
            19,
            "Modul Praktikum Laboratorium IPA Terpadu (Biologi Sel, Usaha & Pesawat Sederhana, Getaran, Gelombang & Optik).",
        ),
        (
            "sd5-matematika-kurmer",
            "labsdul@gmail.com",
            112,
            15,
            "public",
            0,
            0,
            9,
            42,
            "Buku Siswa Matematika Kelas V Kurikulum Merdeka — Edisi Terbuka Perpustakaan Digital Labschool.",
        ),
        (
            "panduan-literasi-digital",
            "labsdul@gmail.com",
            66,
            20,
            "public",
            0,
            0,
            2,
            64,
            "Buku Saku Panduan Literasi Digital, Keamanan Siber & Etika Akademik Siswa Labschool.",
        ),
    ]

    for sb in seed_books:
        cur.execute(
            """
            INSERT INTO book_stats
            (book_id, owner_email, views_count, downloads_count, visibility, is_for_sale, price, preview_pages, sales_count, description)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(book_id) DO UPDATE SET
              is_for_sale = CASE WHEN book_stats.price = 0 AND excluded.is_for_sale = 1 THEN excluded.is_for_sale ELSE book_stats.is_for_sale END,
              price = CASE WHEN book_stats.price = 0 AND excluded.price > 0 THEN excluded.price ELSE book_stats.price END,
              description = CASE WHEN book_stats.description = '' THEN excluded.description ELSE book_stats.description END
            """,
            sb,
        )

    conn.commit()
    conn.close()


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.datetime.now(datetime.timezone.utc)
    exp = now + datetime.timedelta(days=14)
    conn = get_conn()
    conn.execute(
        "INSERT INTO sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_id, now.isoformat(), exp.isoformat()),
    )
    conn.execute(
        "UPDATE users SET last_login = ? WHERE id = ?",
        (now.isoformat(), user_id),
    )
    conn.commit()
    conn.close()
    return token


def get_user_by_token(token: Optional[str]) -> Optional[Dict[str, Any]]:
    if not token or not isinstance(token, str):
        return None
    clean_tok = token.replace("Bearer ", "").strip()
    conn = get_conn()
    row = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, u.license_tier, u.unit, u.status, u.email_verified, u.created_at, u.last_login
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND u.status = 'active'
        """,
        (clean_tok,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: Optional[str]) -> None:
    if not token or not isinstance(token, str):
        return
    clean_tok = token.replace("Bearer ", "").strip()
    conn = get_conn()
    conn.execute("DELETE FROM sessions WHERE token = ?", (clean_tok,))
    conn.commit()
    conn.close()


def increment_book_view(book_id: str) -> None:
    conn = get_conn()
    conn.execute(
        """
        INSERT INTO book_stats (book_id, views_count) VALUES (?, 1)
        ON CONFLICT(book_id) DO UPDATE SET views_count = views_count + 1
        """,
        (book_id,),
    )
    conn.commit()
    conn.close()


def get_all_book_stats() -> Dict[str, Dict[str, Any]]:
    conn = get_conn()
    rows = conn.execute("SELECT * FROM book_stats").fetchall()
    conn.close()
    return {r["book_id"]: dict(r) for r in rows}


def get_user_owned_books(user_email: Optional[str]) -> List[str]:
    if not user_email:
        return []
    conn = get_conn()
    rows = conn.execute(
        """
        SELECT book_id FROM user_collections WHERE lower(user_email) = lower(?)
        UNION
        SELECT book_id FROM book_purchases WHERE lower(buyer_email) = lower(?)
        UNION
        SELECT book_id FROM book_stats WHERE lower(owner_email) = lower(?)
        """,
        (user_email, user_email, user_email),
    ).fetchall()
    conn.close()
    return [r["book_id"] for r in rows]
