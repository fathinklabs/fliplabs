#!/usr/bin/env python3
"""
Generates realistic multi-page sample textbooks for FlipLabs (Matematika Kelas 8,
IPA Terpadu Kelas 8, and Modul Literasi Digital Labschool) and converts them into
full multi-tier WebP flipbooks across Enterprise, Pro, and Basic license plans.
"""

from pathlib import Path
import fitz  # PyMuPDF
from converter import convert_pdf_to_flipbook

MATEMATIKA_PAGES = [
    {
        "type": "cover",
        "badge": "KURIKULUM MERDEKA - SMP KELAS VIII",
        "title": "MATEMATIKA",
        "subtitle": "Buku Paket Siswa & Panduan Pemecahan Masalah Kontekstual",
        "footer": "LABSCHOOL DIGITAL PUBLISHING - JAKARTA",
        "bg": (0.07, 0.16, 0.32),
        "accent": (0.05, 0.65, 0.91),
    },
    {
        "chapter": "Kata Pengantar & Petunjuk Buku",
        "title": "Kata Pengantar",
        "body": (
            "Puji syukur kehadirat Tuhan Yang Maha Esa atas tersusunnya Buku Paket Matematika "
            "SMP Kelas VIII (8) Kurikulum Merdeka di lingkungan Labschool.\n\n"
            "Buku ini dirancang dengan pendekatan pemecahan masalah kontekstual melalui konsep "
            "Aljabar (pola bilangan, persamaan linear, relasi dan fungsi) serta Geometri "
            "(koordinat Kartesius, teorema Pythagoras, lingkaran, dan bangun ruang sisi datar).\n\n"
            "Pembelajaran menekankan interaksi dua arah di mana siswa dan guru aktif berdiskusi "
            "untuk mencapai pemahaman konsep matematika yang mendalam dan aplikatif.\n\n"
            "Fitur E-Book FlipLabs memungkinkan siswa mencari kata kunci rumus secara instan, "
            "memberi stabilo (highlighter) pada konsep penting, serta berdiskusi dengan AI Tutor."
        ),
        "box_title": "Profil Pelajar Pancasila & Visi Labschool",
        "box_text": "Iman, Ilmu, Amal - Bernalar Kritis, Mandiri, Kreatif, dan Bergotong Royong.",
    },
    {
        "chapter": "Daftar Isi",
        "title": "Daftar Isi Buku",
        "body": (
            "Halaman 1   : Sampul Depan (Cover)\n"
            "Halaman 2   : Kata Pengantar & Profil Pembelajaran\n"
            "Halaman 3   : Daftar Isi Buku\n"
            "Halaman 4   : Bab 1 - Pola Bilangan & Barisan Konfigurasi Objek\n"
            "Halaman 5   : 1.1 Barisan dan Deret Aritmetika\n"
            "Halaman 6   : Bab 2 - Bidang Koordinat Kartesius\n"
            "Halaman 7   : Bab 3 - Relasi dan Fungsi Linear\n"
            "Halaman 8   : Bab 4 - Persamaan Garis Lurus & Gradien (m)\n"
            "Halaman 9   : Bab 5 - Sistem Persamaan Linear Dua Variabel (SPLDV)\n"
            "Halaman 10  : Bab 6 - Teorema Pythagoras & Tripel Pythagoras\n"
            "Halaman 11  : Bab 7 - Unsur-Unsur Lingkaran, Busur, dan Juring\n"
            "Halaman 12  : Bab 8 - Bangun Ruang Sisi Datar (Kubus, Balok, Prisma, Limas)"
        ),
        "box_title": "Petunjuk Navigasi FlipLabs",
        "box_text": "Gunakan tombol Daftar Isi (TOC) di toolbar bawah atau tekan tombol panah kiri/kanan pada keyboard untuk membalik halaman.",
    },
    {
        "chapter": "Bab 1: Pola Bilangan",
        "title": "Bab 1: Pola Bilangan",
        "body": (
            "Pola bilangan adalah susunan angka atau noktah yang membentuk keteraturan tertentu. "
            "Dalam kehidupan sehari-hari, pola bilangan digunakan pada penomoran rumah di jalan, "
            "susunan kursi stadion olahraga, hingga pertumbuhan cabang pohon.\n\n"
            "Macam-Macam Pola Bilangan Istimewa:\n"
            "1. Pola Bilangan Ganjil: Un = 2n - 1   (Contoh: 1, 3, 5, 7, 9, ...)\n"
            "2. Pola Bilangan Genap:  Un = 2n       (Contoh: 2, 4, 6, 8, 10, ...)\n"
            "3. Pola Bilangan Persegi: Un = n^2     (Contoh: 1, 4, 9, 16, 25, ...)\n"
            "4. Pola Bilangan Segitiga: Un = 1/2 n(n + 1)  (Contoh: 1, 3, 6, 10, 15, ...)\n"
            "5. Barisan Bilangan Fibonacci: 1, 1, 2, 3, 5, 8, 13, 21, 34, ..."
        ),
        "box_title": "Rumus Inti Pola Segitiga",
        "box_text": "Un = n(n + 1) / 2   |   Suku ke-10 adalah U10 = 10 x 11 / 2 = 55.",
    },
    {
        "chapter": "1.1 Barisan dan Deret Aritmetika",
        "title": "1.1 Barisan & Deret Aritmetika",
        "body": (
            "Barisan Aritmetika adalah barisan bilangan yang memiliki selisih atau beda (b) tetap "
            "antara dua suku yang berurutan: b = U2 - U1 = U3 - U2.\n\n"
            "Rumus Suku ke-n Barisan Aritmetika:\n"
            "    Un = a + (n - 1)b\n\n"
            "Rumus Jumlah n Suku Pertama (Deret Aritmetika):\n"
            "    Sn = (n / 2) x (2a + (n - 1)b)   atau   Sn = (n / 2) x (a + Un)\n\n"
            "Contoh Soal Kontekstual:\n"
            "Di aula SMP Labschool terdapat 15 baris kursi. Baris pertama berisi 20 kursi, "
            "baris kedua 24 kursi, dan seterusnya bertambah 4 kursi setiap baris.\n"
            "Banyak kursi pada baris ke-15 adalah: U15 = 20 + (15 - 1) x 4 = 20 + 56 = 76 kursi."
        ),
        "box_title": "Barisan Geometri (Pembanding Rasio r)",
        "box_text": "Un = a * r^(n-1)   dimana a = suku pertama, dan r = U2 / U1.",
    },
    {
        "chapter": "Bab 2: Koordinat Kartesius",
        "title": "Bab 2: Koordinat Kartesius",
        "body": (
            "Sistem koordinat Kartesius ditemukan oleh Rene Descartes untuk menentukan posisi titik "
            "pada bidang datar menggunakan pasangan berurutan (x, y), di mana:\n"
            "- Absis (x): jarak titik terhadap sumbu-Y.\n"
            "- Ordinat (y): jarak titik terhadap sumbu-X.\n\n"
            "Pembagian Empat Kuadran Bidang Kartesius:\n"
            "- Kuadran I   : x > 0 dan y > 0   (Contoh: A(4, 3))\n"
            "- Kuadran II  : x < 0 dan y > 0   (Contoh: B(-5, 2))\n"
            "- Kuadran III : x < 0 dan y < 0   (Contoh: C(-3, -6))\n"
            "- Kuadran IV  : x > 0 dan y < 0   (Contoh: D(7, -4))\n\n"
            "Jarak antara dua titik P(x1, y1) dan Q(x2, y2) dihitung dengan rumus:\n"
            "    d = sqrt((x2 - x1)^2 + (y2 - y1)^2)"
        ),
        "box_title": "Aplikasi Navigasi & Radar",
        "box_text": "Peta GPS dan radar penerbangan menggunakan sistem koordinat dua dan tiga dimensi.",
    },
    {
        "chapter": "Bab 3: Relasi dan Fungsi",
        "title": "Bab 3: Relasi dan Fungsi",
        "body": (
            "Relasi dari himpunan A ke himpunan B adalah aturan yang memasangkan anggota himpunan A "
            "ke anggota himpunan B.\n\n"
            "Fungsi (Pemetaan) adalah relasi khusus yang memasangkan SETIAP anggota himpunan A "
            "(Domain) dengan TEPAT SATU anggota pada himpunan B (Kodomain).\n\n"
            "Istilah Penting dalam Fungsi:\n"
            "1. Domain (Daerah Asal): seluruh anggota himpunan A.\n"
            "2. Kodomain (Daerah Kawan): seluruh anggota himpunan B.\n"
            "3. Range (Daerah Hasil): himpunan anggota B yang memiliki pasangan di A.\n\n"
            "Notasi Fungsi Linear:\n"
            "    f(x) = ax + b\n"
            "Jika f(x) = 3x - 5, maka nilai fungsi untuk x = 4 adalah f(4) = 3(4) - 5 = 7."
        ),
        "box_title": "Banyak Fungsi & Korespondensi Satu-Satu",
        "box_text": "Banyak fungsi dari A ke B = n(B)^n(A). Korespondensi satu-satu = n! (faktorial).",
    },
    {
        "chapter": "Bab 4: Persamaan Garis Lurus",
        "title": "Bab 4: Persamaan Garis Lurus",
        "body": (
            "Persamaan garis lurus memiliki bentuk umum y = mx + c atau ax + by + c = 0.\n\n"
            "Gradien (m) adalah ukuran kemiringan suatu garis lurus:\n"
            "    m = (y2 - y1) / (x2 - x1)\n\n"
            "Hubungan Dua Garis Lurus:\n"
            "- Dua garis SEJAJAR memiliki gradien yang sama: m1 = m2\n"
            "- Dua garis TEGAK LURUS hasil kali gradiennya -1: m1 x m2 = -1\n\n"
            "Menyusun Persamaan Garis:\n"
            "1. Melalui titik (x1, y1) dengan gradien m:\n"
            "       y - y1 = m(x - x1)\n"
            "2. Melalui dua titik (x1, y1) dan (x2, y2):\n"
            "       (y - y1) / (y2 - y1) = (x - x1) / (x2 - x1)"
        ),
        "box_title": "Sifat Kemiringan Garis",
        "box_text": "Jika m > 0 garis miring ke kanan atas; jika m < 0 garis miring ke kiri atas; jika m = 0 garis mendatar.",
    },
    {
        "chapter": "Bab 5: Sistem Persamaan Linear Dua Variabel (SPLDV)",
        "title": "Bab 5: SPLDV",
        "body": (
            "Sistem Persamaan Linear Dua Variabel (SPLDV) terdiri dari dua persamaan linear:\n"
            "    a1*x + b1*y = c1\n"
            "    a2*x + b2*y = c2\n\n"
            "Empat Metode Penyelesaian SPLDV:\n"
            "1. Metode Grafik: mencari titik potong kedua garis pada bidang Kartesius.\n"
            "2. Metode Substitusi: menyatakan satu variabel ke dalam variabel lainnya.\n"
            "3. Metode Eliminasi: menyamakan koefisien salah satu variabel lalu mengurangkan/menjumlahkan.\n"
            "4. Metode Gabungan (Eliminasi - Substitusi): metode paling efisien dan cepat.\n\n"
            "Contoh Masalah Koperasi Sekolah:\n"
            "Harga 2 buku tulis dan 3 pensil adalah Rp17.000, sedangkan 3 buku tulis dan 1 pensil "
            "adalah Rp15.000. Dengan eliminasi diperoleh harga 1 buku = Rp4.000 dan 1 pensil = Rp3.000."
        ),
        "box_title": "Tips Pemeriksaan Jawaban",
        "box_text": "Substitusikan kembali nilai (x, y) yang diperoleh ke kedua persamaan awal untuk memastikan kesamaan bernilai benar.",
    },
    {
        "chapter": "Bab 6: Teorema Pythagoras",
        "title": "Bab 6: Teorema Pythagoras",
        "body": (
            "Pada setiap segitiga siku-siku, kuadrat panjang sisi miring (hipotenusa) sama dengan "
            "jumlah kuadrat panjang kedua sisi siku-sikunya:\n\n"
            "    c^2 = a^2 + b^2     atau     c = sqrt(a^2 + b^2)\n"
            "    a^2 = c^2 - b^2     dan      b^2 = c^2 - a^2\n\n"
            "Daftar Tripel Pythagoras Utama yang Sering Muncul:\n"
            "- (3, 4, 5) beserta kelipatannya (6, 8, 10), (9, 12, 15), (12, 16, 20)\n"
            "- (5, 12, 13) beserta kelipatannya (10, 24, 26)\n"
            "- (7, 24, 25)\n"
            "- (8, 15, 17)\n"
            "- (9, 40, 41)\n\n"
            "Perbandingan Segitiga Siku-Siku Istimewa:\n"
            "- Sudut 45 - 45 - 90 derajat :  1 : 1 : sqrt(2)\n"
            "- Sudut 30 - 60 - 90 derajat :  1 : sqrt(3) : 2"
        ),
        "box_title": "Jenis Segitiga Berdasarkan Panjang Sisi",
        "box_text": "c^2 = a^2 + b^2 (Siku-siku)  |  c^2 < a^2 + b^2 (Lancip)  |  c^2 > a^2 + b^2 (Tumpul).",
    },
    {
        "chapter": "Bab 7: Lingkaran",
        "title": "Bab 7: Lingkaran & Sudut",
        "body": (
            "Lingkaran adalah tempat kedudukan titik-titik yang berjarak sama (jari-jari r) "
            "terhadap sebuah titik pusat O.\n\n"
            "Rumus Keliling dan Luas Lingkaran (pi = 3,14 atau 22/7):\n"
            "- Keliling: K = 2 * pi * r = pi * d\n"
            "- Luas:     L = pi * r^2 = 1/4 * pi * d^2\n\n"
            "Hubungan Sudut Pusat dan Sudut Keliling yang Menghadap Busur Sama:\n"
            "    Sudut Pusat = 2 x Sudut Keliling\n\n"
            "Panjang Busur dan Luas Juring (Sudut pusat alpha):\n"
            "- Panjang Busur AB = (alpha / 360) x 2 * pi * r\n"
            "- Luas Juring AOB  = (alpha / 360) x pi * r^2\n\n"
            "Garis Singgung Persekutuan Dua Lingkaran (Jarak pusat p, jari-jari R dan r):\n"
            "- Garis Singgung Persekutuan Luar (GSPL): l = sqrt(p^2 - (R - r)^2)\n"
            "- Garis Singgung Persekutuan Dalam (GSPD): d = sqrt(p^2 - (R + r)^2)"
        ),
        "box_title": "Sifat Sudut Keliling Menghadap Diameter",
        "box_text": "Setiap sudut keliling yang menghadap diameter lingkaran besarnya selalu 90 derajat (siku-siku).",
    },
    {
        "chapter": "Bab 8: Bangun Ruang Sisi Datar",
        "title": "Bab 8: Bangun Ruang Sisi Datar",
        "body": (
            "Bangun ruang sisi datar meliputi Kubus, Balok, Prisma, dan Limas.\n\n"
            "1. KUBUS (rusuk s):\n"
            "   - Luas Permukaan = 6 * s^2       - Volume = s^3\n"
            "   - Diagonal Bidang = s * sqrt(2)  - Diagonal Ruang = s * sqrt(3)\n\n"
            "2. BALOK (panjang p, lebar l, tinggi t):\n"
            "   - Luas Permukaan = 2(pl + pt + lt)\n"
            "   - Volume = p x l x t\n"
            "   - Diagonal Ruang = sqrt(p^2 + l^2 + t^2)\n\n"
            "3. PRISMA TEGAK:\n"
            "   - Luas Permukaan = (2 x Luas Alas) + (Keliling Alas x Tinggi)\n"
            "   - Volume = Luas Alas x Tinggi\n\n"
            "4. LIMAS:\n"
            "   - Luas Permukaan = Luas Alas + Jumlah Luas Sisi Tegak\n"
            "   - Volume = 1/3 x Luas Alas x Tinggi"
        ),
        "box_title": "Teorema Polihedron Euler",
        "box_text": "Banyak Sisi (S) + Banyak Titik Sudut (T) = Banyak Rusuk (R) + 2   ==>   S + T - R = 2.",
    },
]


def build_pdf(pages_spec, out_pdf_path: Path):
    doc = fitz.open()
    toc_list = []

    for idx, p in enumerate(pages_spec):
        page_num = idx + 1
        page = doc.new_page(width=595, height=842)  # A4 Portrait

        if p.get("type") == "cover":
            toc_list.append([1, "Sampul Depan (Cover)", page_num])
            bg = p.get("bg", (0.07, 0.16, 0.32))
            accent = p.get("accent", (0.05, 0.65, 0.91))
            page.draw_rect(fitz.Rect(0, 0, 595, 842), color=bg, fill=bg)
            page.draw_circle(fitz.Point(510, 140), 190, color=accent, fill=accent, fill_opacity=0.18)
            page.draw_circle(fitz.Point(90, 720), 220, color=accent, fill=accent, fill_opacity=0.12)
            page.draw_rect(fitz.Rect(48, 80, 547, 762), color=(1, 1, 1), width=1.5)
            page.draw_rect(fitz.Rect(48, 80, 547, 130), color=accent, fill=accent)

            page.insert_text(fitz.Point(72, 111), p["badge"], fontsize=13, fontname="helv", color=(1, 1, 1))
            page.insert_text(fitz.Point(72, 260), p["title"], fontsize=42, fontname="hebo", color=(1, 1, 1))
            page.insert_textbox(
                fitz.Rect(72, 295, 515, 420),
                p["subtitle"],
                fontsize=18,
                fontname="helv",
                color=(0.85, 0.93, 1.0),
            )

            page.draw_rect(fitz.Rect(72, 430, 523, 630), color=accent, fill=(0.04, 0.10, 0.22), width=1.5)
            page.insert_text(fitz.Point(95, 475), "c^2 = a^2 + b^2   |   f(x) = mx + c", fontsize=18, fontname="hebo", color=(0.38, 0.85, 1.0))
            page.insert_text(fitz.Point(95, 520), "Un = a + (n - 1)b |   L = pi * r^2", fontsize=17, fontname="helv", color=(0.9, 0.95, 1.0))
            page.insert_text(fitz.Point(95, 565), "S + T - R = 2     |   Sn = n/2 (a + Un)", fontsize=17, fontname="helv", color=(0.9, 0.95, 1.0))

            page.insert_text(fitz.Point(72, 730), p["footer"], fontsize=12, fontname="hebo", color=(0.75, 0.86, 1.0))
        else:
            if p.get("chapter"):
                lvl = 2 if p["chapter"][0].isdigit() else 1
                toc_list.append([lvl, p["chapter"], page_num])

            page.draw_rect(fitz.Rect(0, 0, 595, 842), color=(0.99, 0.99, 1.0), fill=(0.99, 0.99, 1.0))
            page.draw_rect(fitz.Rect(0, 0, 595, 64), color=(0.07, 0.16, 0.32), fill=(0.07, 0.16, 0.32))
            page.insert_text(
                fitz.Point(48, 40),
                "BUKU PAKET KURIKULUM MERDEKA - LABSCHOOL",
                fontsize=10,
                fontname="hebo",
                color=(0.7, 0.88, 1.0),
            )
            page.insert_text(
                fitz.Point(500, 40),
                f"Hal. {page_num}",
                fontsize=11,
                fontname="hebo",
                color=(1, 1, 1),
            )

            page.insert_text(fitz.Point(48, 118), p["title"], fontsize=24, fontname="hebo", color=(0.07, 0.16, 0.32))
            page.draw_line(fitz.Point(48, 132), fitz.Point(547, 132), color=(0.05, 0.65, 0.91), width=2.5)

            page.insert_textbox(
                fitz.Rect(48, 155, 547, 635),
                p["body"],
                fontsize=12.5,
                fontname="helv",
                color=(0.15, 0.18, 0.24),
                lineheight=1.45,
            )

            page.draw_rect(fitz.Rect(48, 650, 547, 765), color=(0.05, 0.65, 0.91), fill=(0.93, 0.97, 1.0), width=1.5)
            page.insert_text(fitz.Point(66, 680), p.get("box_title", "Catatan Penting"), fontsize=13, fontname="hebo", color=(0.04, 0.35, 0.60))
            page.insert_textbox(
                fitz.Rect(66, 692, 530, 755),
                p.get("box_text", ""),
                fontsize=11.5,
                fontname="helv",
                color=(0.1, 0.2, 0.35),
            )

            page.draw_line(fitz.Point(48, 795), fitz.Point(547, 795), color=(0.82, 0.85, 0.90), width=1)
            page.insert_text(fitz.Point(48, 815), "FlipLabs Digital Book Viewer - books.labschool.xyz", fontsize=9.5, fontname="helv", color=(0.45, 0.50, 0.58))
            page.insert_text(fitz.Point(515, 815), f"{page_num}", fontsize=10.5, fontname="hebo", color=(0.15, 0.20, 0.30))

    doc.set_toc(toc_list)
    out_pdf_path.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(out_pdf_path))
    doc.close()


def main():
    root = Path(__file__).resolve().parent.parent
    books_dir = root / "books"
    uploads_dir = root / "server" / "uploads"
    uploads_dir.mkdir(parents=True, exist_ok=True)

    # 1. Matematika SMP Kelas 8 (Enterprise Plan - Flagship Book)
    math_pdf = uploads_dir / "smp8-matematika-kurikulum-merdeka.pdf"
    build_pdf(MATEMATIKA_PAGES, math_pdf)
    convert_pdf_to_flipbook(
        pdf_path=str(math_pdf),
        books_root=str(books_dir),
        book_id="smp8-matematika",
        title="Buku Paket Matematika SMP Kelas VIII (8) Kurikulum Merdeka",
        subtitle="Aljabar, Koordinat Kartesius, Pythagoras, Lingkaran & Bangun Ruang",
        author="Tim Guru Matematika SMP Labschool",
        category="SMP Kelas 8",
        subject="Matematika",
        license_tier="enterprise",
    )

    # 2. Sains & IPA Terpadu SMP Kelas 8 (Pro Plan)
    ipa_pages = [
        {
            "type": "cover",
            "badge": "KURIKULUM MERDEKA - MODUL PRAKTIKUM",
            "title": "IPA TERPADU VIII",
            "subtitle": "Fisika, Biologi & Kimia Kontekstual Laboratorium",
            "footer": "LABSCHOOL SCIENCE DEPARTMENT",
            "bg": (0.04, 0.26, 0.22),
            "accent": (0.06, 0.72, 0.50),
        },
        {
            "chapter": "Bab 1: Sel dan Mikroskop",
            "title": "Bab 1: Struktur dan Fungsi Sel",
            "body": (
                "Sel merupakan unit struktural dan fungsional terkecil dari makhluk hidup.\n\n"
                "Perbedaan Utama Sel Hewan dan Sel Tumbuhan:\n"
                "- Sel Tumbuhan memiliki Dinding Sel (selulosa), Kloroplas (fotosintesis), dan Vakuola besar.\n"
                "- Sel Hewan tidak memiliki dinding sel, namun memiliki Sentriol untuk pembelahan sel.\n\n"
                "Organel Penting Sel:\n"
                "1. Nukleus (Inti Sel): pusat pengendali genetik (DNA).\n"
                "2. Mitokondria: pusat respirasi seluler penghasil energi ATP.\n"
                "3. Ribosom: tempat sintesis protein."
            ),
            "box_title": "Rumus Perbesaran Total Mikroskop Cahaya",
            "box_text": "M_total = M_lensa_okuler x M_lensa_objektif",
        },
        {
            "chapter": "Bab 2: Usaha, Energi, dan Pesawat Sederhana",
            "title": "Bab 2: Usaha & Pesawat Sederhana",
            "body": (
                "Usaha (W) dalam fisika didefinisikan sebagai hasil kali gaya (F) yang bekerja "
                "searah perpindahan dengan besar perpindahan benda (s):\n"
                "    W = F x s   (Satuan: Joule)\n\n"
                "Energi Kinetik dan Energi Potensial Gravitasi:\n"
                "- Ek = 1/2 * m * v^2\n"
                "- Ep = m * g * h\n\n"
                "Keuntungan Mekanis (KM) Pesawat Sederhana:\n"
                "    KM = Beban (w) / Gaya Kuasa (F) = Lengan Kuasa (lk) / Lengan Beban (lb)"
            ),
            "box_title": "Hukum Kekekalan Energi Mekanik",
            "box_text": "Em1 = Em2   <==>   Ep1 + Ek1 = Ep2 + Ek2",
        },
        {
            "chapter": "Bab 3: Getaran, Gelombang, dan Cahaya",
            "title": "Bab 3: Getaran & Gelombang",
            "body": (
                "Getaran adalah gerak bolak-balik secara periodik melalui titik kesetimbangan.\n\n"
                "Hubungan Frekuensi (f), Periode (T), Panjang Gelombang (lambda), dan Cepat Rambat (v):\n"
                "- f = n / t  (Hertz)    dan    T = t / n = 1 / f  (sekon)\n"
                "- v = lambda x f  =  lambda / T   (m/s)\n\n"
                "Rumus Cermin Cekung / Cembung dan Lensa:\n"
                "    1/f = 1/s + 1/s'    dan    Perbesaran M = |s' / s| = |h' / h|"
            ),
            "box_title": "Gelombang Bunyi & Sonar",
            "box_text": "Kedalaman laut dihitung dengan d = (v x t) / 2 karena bunyi menempuh perjalanan pulang-pergi.",
        },
    ]
    ipa_pdf = uploads_dir / "smp8-ipa-terpadu.pdf"
    build_pdf(ipa_pages, ipa_pdf)
    convert_pdf_to_flipbook(
        pdf_path=str(ipa_pdf),
        books_root=str(books_dir),
        book_id="smp8-ipa-terpadu",
        title="Modul Praktikum IPA Terpadu SMP Kelas VIII",
        subtitle="Panduan Eksperimen Fisika, Biologi & Kimia Laboratorium",
        author="MGMP IPA SMP Labschool",
        category="SMP Kelas 8",
        subject="IPA",
        license_tier="pro",
    )

    # 3. Panduan Akademik & Literasi Digital Siswa (Basic Plan)
    panduan_pages = [
        {
            "type": "cover",
            "badge": "BUKU SAKU SISWA - EDISI UMUM",
            "title": "LITERASI DIGITAL",
            "subtitle": "Panduan Etika Siber & Pembelajaran Mandiri Siswa Labschool",
            "footer": "PERPUSTAKAAN DIGITAL LABSCHOOL",
            "bg": (0.22, 0.12, 0.36),
            "accent": (0.65, 0.35, 0.95),
        },
        {
            "chapter": "Bab 1: Etika Akademik & Keamanan Siber",
            "title": "Bab 1: Etika Digital Siswa",
            "body": (
                "Setiap siswa Labschool wajib menjunjung tinggi integritas akademik dalam menggunakan "
                "platform pembelajaran digital (Moodle LMS, Google Workspace, dan FlipLabs).\n\n"
                "Prinsip Utama Keamanan Akun:\n"
                "1. Gunakan kata sandi yang kuat dan rahasiakan kredensial akun @labschool.sch.id.\n"
                "2. Selalu periksa keaslian sumber referensi ilmiah sebelum mengutip.\n"
                "3. Gunakan kecerdasan buatan (AI) sebagai mitra belajar berpikir kritis, bukan menyalin jawaban."
            ),
            "box_title": "Lisensi Edisi Basic",
            "box_text": "Pada buku dengan paket Basic, siswa dapat membaca secara penuh dengan animasi 3D, namun unduhan PDF dinonaktifkan.",
        },
    ]
    panduan_pdf = uploads_dir / "panduan-literasi-digital.pdf"
    build_pdf(panduan_pages, panduan_pdf)
    convert_pdf_to_flipbook(
        pdf_path=str(panduan_pdf),
        books_root=str(books_dir),
        book_id="panduan-literasi-digital",
        title="Buku Saku Literasi Digital & Etika Akademik Siswa",
        subtitle="Panduan Resmi Penggunaan LMS & Perpustakaan Digital",
        author="Perpustakaan Pusat Labschool",
        category="Panduan Umum",
        subject="Literasi Digital",
        license_tier="basic",
    )

    # 4. Buku Siswa Matematika Kelas V (Kurikulum Merdeka) - Hasil Investigasi pjiut/gqfj (#p=6..9)
    sd5_pages = [
        {
            "type": "cover",
            "badge": "KURIKULUM MERDEKA - KELAS V",
            "title": "MATEMATIKA V",
            "subtitle": "Belajar Bersama Temanmu Matematika untuk Sekolah Dasar Kelas V",
            "footer": "KEMENTERIAN PENDIDIKAN, KEBUDAYAAN, RISET, DAN TEKNOLOGI",
            "bg": (0.04, 0.32, 0.58),
            "accent": (0.95, 0.45, 0.15),
        },
        {
            "chapter": "Kata Pengantar & Prakata",
            "title": "Kata Pengantar (Hal. iii)",
            "body": (
                "Buku Siswa Matematika Kelas V Kurikulum Merdeka disusun untuk membantu peserta didik "
                "mengembangkan pemahaman konsep matematika secara visual, eksploratif, dan kontekstual.\n\n"
                "Melalui aktivitas diskusi bersama teman, siswa diajak menemukan sendiri rumus dan pola "
                "dari permasalahan sehari-hari."
            ),
            "box_title": "Karakteristik Buku Kurikulum Merdeka",
            "box_text": "Dilengkapi ilustrasi kontekstual, aktivitas eksplorasi, dan latihan pemecahan masalah.",
        },
        {
            "chapter": "Petunjuk Penggunaan Buku",
            "title": "Petunjuk Penggunaan Buku (Hal. iv)",
            "body": (
                "Kenali tokoh-tokoh pendamping belajar di dalam buku ini:\n"
                "- Yohana, Komang, dan Lukas yang memandu eksperimen matematika.\n"
                "- Ayo Bereksplorasi: kegiatan menemukan konsep baru.\n"
                "- Ayo Berlatih: soal penguatan pemahaman konsep.\n"
                "- Ayo Berpikir Kritis: tantangan penalaran mendalam."
            ),
            "box_title": "Simbol & Navigasi",
            "box_text": "Gunakan Daftar Isi dan Daftar Gambar pada halaman 6 sampai 9 untuk menelusuri topik.",
        },
        {
            "chapter": "Daftar Isi (Bab 1 - Bab 2)",
            "title": "Daftar Isi - Bagian Awal (Hal. v)",
            "body": (
                "Kata Pengantar ................................................................. iii\n"
                "Prakata ............................................................................. iv\n"
                "Daftar Isi .......................................................................... v\n\n"
                "Bab 1 | Bilangan Cacah Sampai 100.000 .............................. 1\n"
                "  A. Membaca dan Menulis Bilangan Cacah Sampai 100.000 .... 4\n"
                "  B. Membandingkan dan Mengurutkan Bilangan ...................... 11\n"
                "  C. Komposisi dan Dekomposisi Bilangan .............................. 17\n"
                "  D. Operasi Hitung pada Bilangan Cacah .............................. 21\n\n"
                "Bab 2 | KPK dan FPB ......................................................... 31\n"
                "  A. Kelipatan dan Kelipatan Persekutuan .............................. 33\n"
                "  B. Faktor dan Faktor Persekutuan ........................................ 42\n"
                "  C. Menentukan KPK dan FPB dengan Faktorisasi Prima .......... 51"
            ),
            "box_title": "Fondasi Aritmetika Dasar",
            "box_text": "Penguasaan operasi bilangan cacah serta KPK dan FPB menjadi dasar untuk mempelajari Bab 3 (Pecahan).",
        },
        {
            "chapter": "Pengantar Bab & Pemetaan Materi",
            "title": "Pemetaan Kompetensi Matematika V",
            "body": (
                "Cakupan Elemen Matematika Kelas V Kurikulum Merdeka:\n"
                "1. Elemen Bilangan: Bab 1 (Bilangan Cacah 100.000), Bab 2 (KPK & FPB), Bab 3 (Pecahan), Bab 9 (Bilangan Cacah 1.000.000).\n"
                "2. Elemen Pengukuran: Bab 4 (Keliling Bangun Datar), Bab 5 (Luas Daerah Bangun Datar), Bab 6 (Sudut).\n"
                "3. Elemen Geometri: Bab 7 (Membandingkan Ciri-Ciri Bangun Datar).\n"
                "4. Elemen Analisis Data dan Peluang: Bab 8 (Data, Piktogram, dan Diagram Batang)."
            ),
            "box_title": "Keterkaitan Antar-Bab",
            "box_text": "Lihat rincian halaman Bab 3 s/d Bab 9 pada Halaman 6 dan 7 serta Daftar Gambar pada Halaman 8 dan 9.",
        },
        {
            "chapter": "Halaman 6 (vi): Daftar Isi Bab 3 - Bab 6",
            "title": "Daftar Isi: Bab 3 s/d Bab 6 (Hal. vi)",
            "body": (
                "Bab 3 | Bilangan Pecahan .................................................... 63\n"
                "  A. Membandingkan dan Mengurutkan Pecahan ...................... 68\n"
                "  B. Penjumlahan Bilangan Pecahan ....................................... 76\n"
                "  C. Pengurangan Bilangan Pecahan ....................................... 91\n\n"
                "Bab 4 | Keliling Bangun Datar .............................................. 105\n"
                "  A. Apakah Keliling Bangun Datar Itu? ................................... 107\n"
                "  B. Keliling Segitiga ............................................................. 115\n"
                "  C. Keliling Segi Empat ......................................................... 118\n"
                "  D. Keliling Segi Banyak ....................................................... 122\n"
                "  E. Keliling Bangun Gabungan ............................................... 125\n\n"
                "Bab 5 | Luas Daerah Bangun Datar ...................................... 131\n"
                "  A. Konsep Luas Daerah Bangun Datar .................................. 133\n"
                "  B. Luas Daerah Bangun Datar .............................................. 144\n"
                "  C. Luas Daerah Bangun Gabungan ....................................... 158\n"
                "  D. Hubungan Keliling dan Luas Daerah Bangun Datar ............ 159\n\n"
                "Bab 6 | Sudut ..................................................................... 163\n"
                "  A. Sudut Siku-Siku (166)   B. Pengertian Sudut (170)\n"
                "  C. Mengukur dan Membandingkan Sudut (175)   D. Melukis Sudut (183)"
            ),
            "box_title": "Halaman vi (Halaman 6)",
            "box_text": "Memuat rincian sub-bab untuk Bilangan Pecahan, Keliling Bangun Datar, Luas Daerah, dan Sudut.",
        },
        {
            "chapter": "Halaman 7 (vii): Daftar Isi Bab 7 - Bab 9",
            "title": "Daftar Isi: Bab 7 s/d Bab 9 (Hal. vii)",
            "body": (
                "Bab 7 | Membandingkan Ciri-Ciri Bangun Datar ................... 191\n"
                "  A. Membandingkan Ciri-Ciri Segitiga ..................................... 196\n"
                "  B. Membandingkan Ciri-Ciri Segi Empat ............................... 209\n\n"
                "Bab 8 | Data ....................................................................... 235\n"
                "  A. Mengumpulkan Data ....................................................... 240\n"
                "  B. Piktogram ...................................................................... 248\n"
                "  C. Diagram Batang ............................................................. 252\n\n"
                "Bab 9 | Bilangan Cacah Sampai 1.000.000 ............................ 273\n"
                "  A. Membaca dan Menulis Bilangan Cacah Sampai 1.000.000\n"
                "     dan Menentukan Nilai Tempatnya .................................... 276\n"
                "  B. Mengurutkan dan Membandingkan Bilangan\n"
                "     Sampai 1.000.000 ........................................................... 284\n"
                "  C. Komposisi dan Dekomposisi Bilangan Sampai 1.000.000 ... 288\n\n"
                "Glosarium ......................................................................... 293\n"
                "Daftar Pustaka ................................................................... 297\n"
                "Index ................................................................................. 299\n"
                "Profil Pelaku Perbukuan ..................................................... 302"
            ),
            "box_title": "Halaman vii (Halaman 7)",
            "box_text": "Memuat rincian Bab 7 (Ciri Bangun Datar), Bab 8 (Data), Bab 9 (Bilangan Cacah 1.000.000), serta Glosarium & Indeks.",
        },
        {
            "chapter": "Halaman 8 (viii): Daftar Gambar (Bagian 1)",
            "title": "Daftar Gambar 1.1 s/d 6.2 (Hal. viii)",
            "body": (
                "Gambar 1.1  Beberapa Barang Dagangan di Pasar Sukawati ...................... 2\n"
                "Gambar 1.2  Jumlah Terpapar Covid-19 di Indonesia ................................. 4\n"
                "Gambar 1.3  Empat Buku Tulis Yohana .................................................... 5\n"
                "Gambar 1.5  Papan Dakon .................................................................... 10\n"
                "Gambar 1.7  Ayam Taliwang dari Lombok ................................................ 19\n"
                "Gambar 2.1  Latihan Renang ................................................................. 31\n"
                "Gambar 2.3  Bermain Congklak ............................................................ 46\n"
                "Gambar 3.1  Jajanan Pasar & Potongan Wingko ..................................... 65\n"
                "Gambar 3.4  Martabak Aneka Rasa ........................................................ 76\n"
                "Gambar 3.7  Kue Apem dan Kue Wajik ................................................... 102\n"
                "Gambar 4.1  Benteng Baluwarti dan Denah Benteng Baluwarti ................. 107\n"
                "Gambar 4.5  Lintasan Lari & Denah Rumah ............................................ 110\n"
                "Gambar 5.1  Alun-Alun Utara & Denah Pemasangan Ubin ........................ 133\n"
                "Gambar 6.1  Contoh Sudut dalam Kehidupan Sehari-Hari ......................... 165\n"
                "Gambar 6.2  Pojok Bingkai yang Membentuk Sudut Siku-Siku .................... 166"
            ),
            "box_title": "Halaman viii (Halaman 8)",
            "box_text": "Daftar ilustrasi kontekstual budaya nusantara (Pasar Sukawati, Papan Dakon, Congklak, Benteng Baluwarti).",
        },
        {
            "chapter": "Halaman 9 (ix): Daftar Gambar (Bagian 2)",
            "title": "Daftar Gambar 6.3 s/d 9.6 (Hal. ix)",
            "body": (
                "Gambar 6.3  Penggaris Siku-Siku ......................................................... 166\n"
                "Gambar 6.4  Cara Membuat Sudut Siku-Siku dari Selembar Kertas ............ 167\n"
                "Gambar 6.7  Tari Pakarena ................................................................... 175\n"
                "Gambar 6.8  Kipas Lipat yang Terbuka dengan Lebar Berbeda ................... 176\n"
                "Gambar 6.9  Bagian-Bagian Busur Derajat .............................................. 177\n"
                "Gambar 7.1  Candi Sewu & Kompleks Candi Sewu ................................... 193\n"
                "Gambar 8.1  Donat Berbagai Rasa ........................................................ 237\n"
                "Gambar 8.2  Diagram Batang Cara Berangkat ke Sekolah Siswa Kelas V .... 239\n"
                "Gambar 8.4  Diagram Batang Perolehan Medali Emas SEA Games ............. 255\n"
                "Gambar 8.10 Diagram Batang Kandungan Kalori Per 100 Gram Makanan ..... 266\n"
                "Gambar 8.12 Diagram Batang Data Pengguna Internet di Indonesia ............ 271\n"
                "Gambar 9.1  Jumlah Penduduk Laki-Laki di Beberapa Wilayah Indonesia .... 274\n"
                "Gambar 9.2  Lemari Jepara & Peta Kabupaten Gianyar ............................. 276\n"
                "Gambar 9.6  Banyaknya Wisatawan Mancanegara ke Yogyakarta .............. 286"
            ),
            "box_title": "Halaman ix (Halaman 9)",
            "box_text": "Daftar gambar alat ukur geometri (Busur Derajat), Candi Sewu, serta berbagai Diagram Batang & Statistik.",
        },
    ]
    sd5_pdf = uploads_dir / "sd5-matematika-kurmer.pdf"
    build_pdf(sd5_pages, sd5_pdf)
    convert_pdf_to_flipbook(
        pdf_path=str(sd5_pdf),
        books_root=str(books_dir),
        book_id="sd5-matematika-kurmer",
        title="Buku Siswa Matematika Kelas V (Kurikulum Merdeka)",
        subtitle="Pecahan, Keliling & Luas Bangun Datar, Sudut, Data & Bilangan Cacah",
        author="Kemendikbudristek - Tim Kurikulum",
        category="SMP Kelas 8",
        subject="Matematika",
        license_tier="enterprise",
    )
    print("[SUCCESS] Generated and converted all 4 sample books with clean typography!")


if __name__ == "__main__":
    main()
