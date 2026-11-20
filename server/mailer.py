#!/usr/bin/env python3
"""
FlipLabs Enterprise Email Sender via Google Workspace XOAUTH2 (Gmail API)
-------------------------------------------------------------------------
Uses the exact same Google Cloud Service Account Domain-Wide Delegation (DwD)
configuration as s.labschool.xyz (impersonating admin@labschool.xyz).
"""

import base64
import email.utils
import json
import os
import subprocess
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

_TOKEN_CACHE: Dict[str, Any] = {"access_token": None, "expires_at": 0}

POSSIBLE_SA_PATHS = [
    "/app/books/google_service_account.json",
    "/var/www/s.labschool.xyz/config/google_service_account.json",
    "C:/GAMConfig/oauth2service.json",
    str(Path(__file__).resolve().parent / "google_service_account.json"),
]


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def find_service_account_path() -> Optional[str]:
    for p in POSSIBLE_SA_PATHS:
        if os.path.exists(p):
            return p
    return None


def sign_rs256_jwt(unsigned_jwt: str, private_key_pem: str) -> bytes:
    """Sign JWT using openssl CLI (zero external Python C-extension dependency)."""
    with tempfile.NamedTemporaryFile("w", delete=False, suffix=".pem", encoding="utf-8") as kf:
        kf.write(private_key_pem)
        key_path = kf.name

    try:
        openssl_bin = "openssl"
        if os.name == "nt" and not shutil_which("openssl"):
            git_openssl = r"C:\Program Files\Git\usr\bin\openssl.exe"
            if os.path.exists(git_openssl):
                openssl_bin = git_openssl

        proc = subprocess.run(
            [openssl_bin, "dgst", "-sha256", "-sign", key_path],
            input=unsigned_jwt.encode("ascii"),
            capture_output=True,
            timeout=8,
            check=True,
        )
        return proc.stdout
    finally:
        try:
            os.remove(key_path)
        except OSError:
            pass


def shutil_which(cmd: str) -> Optional[str]:
    import shutil
    return shutil.which(cmd)


def get_xoauth2_access_token(impersonate_user: str = "admin@labschool.xyz") -> str:
    now = int(time.time())
    if _TOKEN_CACHE["access_token"] and _TOKEN_CACHE["expires_at"] > (now + 120):
        return _TOKEN_CACHE["access_token"]

    sa_path = find_service_account_path()
    if not sa_path:
        raise RuntimeError("File kredensial google_service_account.json tidak ditemukan.")

    with open(sa_path, "r", encoding="utf-8") as f:
        sa = json.load(f)

    header = {"alg": "RS256", "typ": "JWT"}
    claims = {
        "iss": sa["client_email"],
        "sub": impersonate_user,
        "scope": "https://mail.google.com/",
        "aud": "https://oauth2.googleapis.com/token",
        "exp": now + 3600,
        "iat": now,
    }

    unsigned_jwt = (
        b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        + "."
        + b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))
    )
    sig = sign_rs256_jwt(unsigned_jwt, sa["private_key"])
    signed_jwt = unsigned_jwt + "." + b64url_encode(sig)

    body = urllib.parse.urlencode(
        {
            "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
            "assertion": signed_jwt,
        }
    ).encode("utf-8")

    req = urllib.request.Request(
        "https://oauth2.googleapis.com/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        token_data = json.loads(resp.read().decode("utf-8"))

    access_token = token_data["access_token"]
    expires_in = int(token_data.get("expires_in", 3600))
    _TOKEN_CACHE["access_token"] = access_token
    _TOKEN_CACHE["expires_at"] = now + expires_in
    return access_token


def send_mail_xoauth2(
    to_email: str,
    subject: str,
    html_body: str,
    plain_text: str = "",
    from_name: str = "EBOOK LABS — Perpustakaan Digital Labschool",
    from_email: str = "admin@labschool.xyz",
) -> Dict[str, Any]:
    try:
        token = get_xoauth2_access_token(from_email)
    except Exception as exc:
        return {"success": False, "message": f"Gagal otorisasi XOAUTH2: {exc}"}

    if not plain_text:
        import re
        plain_text = re.sub(r"<[^>]+>", "", html_body)

    boundary = f"=_fliplabs_boundary_{uuid.uuid4().hex}"
    from_b64 = base64.b64encode(from_name.encode("utf-8")).decode("ascii")
    subj_b64 = base64.b64encode(subject.encode("utf-8")).decode("ascii")
    plain_b64 = base64.encodebytes(plain_text.encode("utf-8")).decode("ascii")
    html_b64 = base64.encodebytes(html_body.encode("utf-8")).decode("ascii")

    raw_mime = (
        f"From: =?UTF-8?B?{from_b64}?= <{from_email}>\r\n"
        f"To: <{to_email}>\r\n"
        f"Subject: =?UTF-8?B?{subj_b64}?=\r\n"
        f"MIME-Version: 1.0\r\n"
        f"Date: {email.utils.formatdate(localtime=True)}\r\n"
        f"Message-ID: <{uuid.uuid4().hex}@books.labschool.xyz>\r\n"
        f'Content-Type: multipart/alternative; boundary="{boundary}"\r\n\r\n'
        f"--{boundary}\r\n"
        f"Content-Type: text/plain; charset=UTF-8\r\n"
        f"Content-Transfer-Encoding: base64\r\n\r\n"
        f"{plain_b64}\r\n"
        f"--{boundary}\r\n"
        f"Content-Type: text/html; charset=UTF-8\r\n"
        f"Content-Transfer-Encoding: base64\r\n\r\n"
        f"{html_b64}\r\n"
        f"--{boundary}--\r\n"
    )

    encoded_mime = b64url_encode(raw_mime.encode("utf-8"))
    api_url = f"https://gmail.googleapis.com/gmail/v1/users/{urllib.parse.quote(from_email)}/messages/send"

    req = urllib.request.Request(
        api_url,
        data=json.dumps({"raw": encoded_mime}).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            res_json = json.loads(resp.read().decode("utf-8"))
            return {
                "success": True,
                "message_id": res_json.get("id", ""),
                "message": "Email verifikasi berhasil dikirim melalui Google Workspace XOAUTH2 (admin@labschool.xyz).",
            }
    except Exception as exc:
        return {"success": False, "message": f"Gagal mengirim email via Gmail API: {exc}"}


def send_verification_email(to_email: str, full_name: str, otp_code: str, verify_url: str) -> Dict[str, Any]:
    subject = f"[{otp_code}] Kode Verifikasi Pendaftaran Akun EBOOK LABS (books.labschool.xyz)"
    html_body = f"""
    <div style="font-family:'Segoe UI',Roboto,Arial,sans-serif;max-width:560px;margin:0 auto;background:#ffffff;border:1px solid #e2e8f0;border-radius:16px;overflow:hidden;">
      <div style="background:linear-gradient(135deg,#0088ff,#1e40af);padding:24px 28px;color:#ffffff;">
        <h2 style="margin:0;font-size:20px;">EBOOK LABS — Marketplace &amp; Buku Digital 3D</h2>
        <p style="margin:4px 0 0;font-size:13px;opacity:0.9;">books.labschool.xyz • Ekosistem Digital Labschool</p>
      </div>
      <div style="padding:28px;color:#1e293b;line-height:1.6;">
        <p style="margin-top:0;">Halo <strong>{full_name}</strong>,</p>
        <p>Terima kasih telah mendaftar akun Siswa di <strong>EBOOK LABS (books.labschool.xyz)</strong>. Gunakan Kode OTP 6 digit di bawah ini atau klik tombol aktivasi untuk memverifikasi alamat email Anda:</p>
        <div style="background:#f0f7ff;border:2px dashed #0088ff;border-radius:12px;padding:18px;text-align:center;margin:22px 0;">
          <div style="font-size:12px;color:#64748b;font-weight:700;text-transform:uppercase;letter-spacing:1px;">Kode Verifikasi OTP Anda</div>
          <div style="font-size:34px;font-weight:900;letter-spacing:8px;color:#0088ff;margin-top:6px;">{otp_code}</div>
        </div>
        <div style="text-align:center;margin:24px 0;">
          <a href="{verify_url}" style="background:#0088ff;color:#ffffff;text-decoration:none;padding:12px 28px;border-radius:8px;font-weight:700;font-size:14px;display:inline-block;">
            Verifikasi Email Saya Sekarang
          </a>
        </div>
        <p style="font-size:12.5px;color:#64748b;margin-bottom:0;">
          Email ini dikirim secara otomatis melalui layanan resmi Google Workspace XOAUTH2 <strong>admin@labschool.xyz</strong>.
        </p>
      </div>
    </div>
    """
    return send_mail_xoauth2(to_email=to_email, subject=subject, html_body=html_body)
