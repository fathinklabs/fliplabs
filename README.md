# FlipLabs — Custom Self-Hosted FlipHTML5 PDF Book Viewer (`books.labschool.xyz`)

Platform e-book interaktif **FlipLabs** adalah sistem viewer buku 3D (*Flipbook*) dan etalase rak buku digital (*Virtual Bookcase*) mandiri (*self-hosted*) untuk ekosistem **Labschool**. Dirancang untuk menggantikan ketergantungan pada layanan berbayar pihak ketiga seperti FlipHTML5 dengan performa tinggi, hemat RAM, dan privasi data 100% lokal.

## ✨ Fitur Utama
- **3D Page Flip & Curl Engine**: Efek membalik halaman buku 3D realistis (Double-page spread otomatis di desktop & Single-page di smartphone).
- **Web Audio Paper Flip FX**: Suara lembaran kertas berbalik secara sintetis via Web Audio API tanpa jeda.
- **Multi-Tier WebP Pipeline**: Konversi otomatis PDF menjadi 3 tingkat resolusi (`large`, `mobile`, `thumb`) menggunakan `PyMuPDF` & `Pillow`.
- **Full-Text Search + Coordinate Highlighting**: Pencarian kata kunci/rumus di seluruh buku dengan penanda sorot stabilo kuning otomatis pada posisi kata di halaman.
- **Table of Contents (TOC) & Thumbnail Tray**: Navigasi bab berjenjang dan galeri pratinjau halaman di bagian bawah.
- **Alat Belajar Interaktif**: Stabilo (*Highlighter*), Pena Coretan, Penanda Halaman (*Bookmarks*), dan **FlipShot** (unduh tangkapan layar halaman ber-watermark).
- **Matriks Lisensi Fitur (`Basic`, `Pro`, `Enterprise`)**: Penegakan fitur per buku/pengguna beserta AI Book Tutor.
- **Virtual Bookcase (Rak Buku Digital 3D)**: Rak buku interaktif dengan filter kelas/kategori dan generator kode `<iframe ...>` untuk Moodle LMS.

## 🚀 Menjalankan Server Development
```bash
# Via Podman Compose
podman-compose up -d --build

# Atau langsung via Python Uvicorn (Port 8090)
pip install -r converter/requirements.txt
uvicorn server.app:app --host 0.0.0.0 --port 8090 --reload
```

## 🌐 Production Server
- **Host**: `srv-lmslabs-smpjkt` (`10.255.0.188`)
- **Container Port**: `127.0.0.1:8090`
- **Public URL**: [https://books.labschool.xyz](https://books.labschool.xyz)
