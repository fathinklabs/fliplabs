#!/usr/bin/env python3
"""
FlipLabs Authentication, Registration, User & Book Management Module (SQLite)
-----------------------------------------------------------------------------
Persists users, sessions, roles (admin, guru, siswa), license plans
(basic, pro, enterprise), and book analytics in /app/books/fliplabs.db.
"""

import datetime
import hashlib
import hmac
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
DB_PATH = ROOT_DIR / "books" / "fliplabs.db"
SECRET_SALT = os.environ.get("FLIPLABS_SECRET", "fliplabs-labschool-secret-key-2026")


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
            created_at TEXT NOT NULL,
            last_login TEXT
        )
        """
    )

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
            visibility TEXT DEFAULT 'public'
        )
        """
    )

    # Seed default accounts if not present
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
            now,
        ),
    ]

    for u in seed_users:
        cur.execute(
            """
            INSERT OR IGNORE INTO users
            (name, email, password_hash, role, license_tier, unit, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            u,
        )

    # Seed initial book stats
    for bid, views in [
        ("smp8-matematika", 148),
        ("smp8-ipa-terpadu", 86),
        ("panduan-literasi-digital", 64),
    ]:
        cur.execute(
            """
            INSERT OR IGNORE INTO book_stats (book_id, owner_email, views_count, downloads_count, visibility)
            VALUES (?, 'labsdul@gmail.com', ?, 12, 'public')
            """,
            (bid, views),
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
    if not token:
        return None
    clean_tok = token.replace("Bearer ", "").strip()
    conn = get_conn()
    row = conn.execute(
        """
        SELECT u.id, u.name, u.email, u.role, u.license_tier, u.unit, u.status, u.created_at, u.last_login
        FROM sessions s
        JOIN users u ON u.id = s.user_id
        WHERE s.token = ? AND u.status = 'active'
        """,
        (clean_tok,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_session(token: Optional[str]) -> None:
    if not token:
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
