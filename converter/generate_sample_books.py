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
        "badge": "KURIKULUM MERDEKA • SMP KELAS VIII",
        "title": "MATEMATIKA",
        "subtitle": "Buku Paket Siswa & Panduan Pemecahan Masalah Kontekstual",
        "footer": "LABSCHOOL DIGITAL PUBLISHING • JAKARTA",
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
            "memberi stabilo (highlighter) pada konsep penting, serta berdiskusi dengan AI Assistant."
        ),
        "box_title": "Profil Pelajar Pancasila & Visi Labschool",
        "box_text": "Iman, Ilmu, Amal • Bernalar Kritis, Mandiri, Kreatif, dan Bergotong Royong.",
    },
    {
        "chapter": "Daftar Isi",
        "title": "Daftar Isi Buku",
        "body": (
            "Halaman 1   — Sampul Depan (Cover)\n"
            "Halaman 2   — Kata Pengantar & Profil Pembelajaran\n"
            "Halaman 3   — Daftar Isi Buku\n"
            "Halaman 4   — Bab 1: Pola Bilangan & Barisan Konfigurasi Objek\n"
            "Halaman 5   — 1.1 Barisan dan Deret Aritmetika\n"
            "Halaman 6   — Bab 2: Bidang Koordinat Kartesius\n"
            "Halaman 7   — Bab 3: Relasi dan Fungsi Linear\n"
            "Halaman 8   — Bab 4: Persamaan Garis Lurus & Gradien (m)\n"
            "Halaman 9   — Bab 5: Sistem Persamaan Linear Dua Variabel (SPLDV)\n"
            "Halaman 10  — Bab 6: Teorema Pythagoras & Tripel Pythagoras\n"
            "Halaman 11  — Bab 7: Unsur-Unsur Lingkaran, Busur, dan Juring\n"
            "Halaman 12  — Bab 8: Bangun Ruang Sisi Datar (Kubus, Balok, Prisma, Limas)"
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
            "• Pola Bilangan Ganjil: Un = 2n - 1  (Contoh: 1, 3, 5, 7, 9, ...)\n"
            "• Pola Bilangan Genap:  Un = 2n      (Contoh: 2, 4, 6, 8, 10, ...)\n"
            "• Pola Bilangan Persegi: Un = n²     (Contoh: 1, 4, 9, 16, 25, ...)\n"
            "• Pola Bilangan Segitiga: Un = ½ n(n + 1) (Contoh: 1, 3, 6, 10, 15, ...)\n"
            "• Barisan Bilangan Fibonacci: 1, 1, 2, 3, 5, 8, 13, 21, 34, ..."
        ),
        "box_title": "Rumus Inti Pola Segitiga",
        "box_text": "Un = n(n + 1) / 2   |   Suku ke-10 adalah U10 = 10 × 11 / 2 = 55.",
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
            "    Sn = ½ n (2a + (n - 1)b)  atau  Sn = ½ n (a + Un)\n\n"
            "Contoh Soal Kontekstual:\n"
            "Di aula SMP Labschool terdapat 15 baris kursi. Baris pertama berisi 20 kursi, "
            "baris kedua 24 kursi, dan seterusnya bertambah 4 kursi setiap baris.\n"
            "Banyak kursi pada baris ke-15 adalah: U15 = 20 + (15 - 1) × 4 = 20 + 56 = 76 kursi."
        ),
        "box_title": "Barisan Geometri (Pembanding Rasio r)",
        "box_text": "Un = a · r^(n-1)   dimana a = suku pertama, dan r = U2 / U1.",
    },
    {
        "chapter": "Bab 2: Koordinat Kartesius",
        "title": "Bab 2: Koordinat Kartesius",
        "body": (
            "Sistem koordinat Kartesius ditemukan oleh René Descartes untuk menentukan posisi titik "
            "pada bidang datar menggunakan pasangan berurutan (x, y), di mana:\n"
            "• Absis (x): jarak titik terhadap sumbu-Y.\n"
            "• Ordinat (y): jarak titik terhadap sumbu-X.\n\n"
            "Pembagian Empat Kuadran Bidang Kartesius:\n"
            "• Kuadran I   : x > 0 dan y > 0  — Contoh: A(4, 3)\n"
            "• Kuadran II  : x < 0 dan y > 0  — Contoh: B(-5, 2)\n"
            "• Kuadran III : x < 0 dan y < 0  — Contoh: C(-3, -6)\n"
            "• Kuadran IV  : x > 0 dan y < 0  — Contoh: D(7, -4)\n\n"
            "Jarak antara dua titik P(x1, y1) dan Q(x2, y2) dihitung dengan rumus:\n"
            "    d = √[(x2 - x1)² + (y2 - y1)²]"
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
            "    m = Δy / Δx = (y2 - y1) / (x2 - x1)\n\n"
            "Hubungan Dua Garis Lurus:\n"
            "• Dua garis SEJAJAR memiliki gradien yang sama: m1 = m2\n"
            "• Dua garis TEGAK LURUS hasil kali gradiennya -1: m1 × m2 = -1\n\n"
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
            "    a1x + b1y = c1\n"
            "    a2x + b2y = c2\n\n"
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
            "    c² = a² + b²   ⇔   c = √(a² + b²)\n"
            "    a² = c² - b²   dan  b² = c² - a²\n\n"
            "Daftar Tripel Pythagoras Utama yang Sering Muncul:\n"
            "• (3, 4, 5) beserta kelipatannya (6, 8, 10), (9, 12, 15), (12, 16, 20)\n"
            "• (5, 12, 13) beserta kelipatannya (10, 24, 26)\n"
            "• (7, 24, 25)\n"
            "• (8, 15, 17)\n"
            "• (9, 40, 41)\n\n"
            "Perbandingan Segitiga Siku-Siku Istimewa:\n"
            "• Sudut 45° - 45° - 90°  :  1 : 1 : √2\n"
            "• Sudut 30° - 60° - 90°  :  1 : √3 : 2"
        ),
        "box_title": "Jenis Segitiga Berdasarkan Panjang Sisi",
        "box_text": "c² = a² + b² (Siku-siku)  |  c² < a² + b² (Lancip)  |  c² > a² + b² (Tumpul).",
    },
    {
        "chapter": "Bab 7: Lingkaran",
        "title": "Bab 7: Lingkaran & Sudut",
        "body": (
            "Lingkaran adalah tempat kedudukan titik-titik yang berjarak sama (jari-jari r) "
            "terhadap sebuah titik pusat O.\n\n"
            "Rumus Keliling dan Luas Lingkaran:\n"
            "• Keliling: K = 2πr = πd\n"
            "• Luas:     L = πr² = ¼ πd²\n\n"
            "Hubungan Sudut Pusat dan Sudut Keliling yang Menghadap Busur Sama:\n"
            "    Sudut Pusat = 2 × Sudut Keliling\n\n"
            "Panjang Busur dan Luas Juring (Sudut pusat α):\n"
            "• Panjang Busur AB = (α / 360°) × 2πr\n"
            "• Luas Juring AOB  = (α / 360°) × πr²\n\n"
            "Garis Singgung Persekutuan Dua Lingkaran (Jarak pusat p, jari-jari R dan r):\n"
            "• Garis Singgung Persekutuan Luar (GSPL): l = √[p² - (R - r)²]\n"
            "• Garis Singgung Persekutuan Dalam (GSPD): d = √[p² - (R + r)²]"
        ),
        "box_title": "Sifat Sudut Keliling Menghadap Diameter",
        "box_text": "Setiap sudut keliling yang menghadap diameter lingkaran besarnya selalu 90° (siku-siku).",
    },
    {
        "chapter": "Bab 8: Bangun Ruang Sisi Datar",
        "title": "Bab 8: Bangun Ruang Sisi Datar",
        "body": (
            "Bangun ruang sisi datar meliputi Kubus, Balok, Prisma, dan Limas.\n\n"
            "1. KUBUS (rusuk s):\n"
            "   • Luas Permukaan = 6s²       • Volume = s³\n"
            "   • Diagonal Bidang = s√2      • Diagonal Ruang = s√3\n\n"
            "2. BALOK (panjang p, lebar l, tinggi t):\n"
            "   • Luas Permukaan = 2(pl + pt + lt)\n"
            "   • Volume = p × l × t\n"
            "   • Diagonal Ruang = √(p² + l² + t²)\n\n"
            "3. PRISMA TEGAK:\n"
            "   • Luas Permukaan = (2 × Luas Alas) + (Keliling Alas × Tinggi)\n"
            "   • Volume = Luas Alas × Tinggi\n\n"
            "4. LIMAS:\n"
            "   • Luas Permukaan = Luas Alas + Jumlah Luas Sisi Tegak\n"
            "   • Volume = ⅓ × Luas Alas × Tinggi"
        ),
        "box_title": "Teorema Polihedron Euler",
        "box_text": "Banyak Sisi (S) + Banyak Titik Sudut (T) = Banyak Rusuk (R) + 2   ⇒   S + T - R = 2.",
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
            # Decorative geometric circles & stripes
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

            # Formula illustration box on cover
            page.draw_rect(fitz.Rect(72, 430, 523, 630), color=accent, fill=(0.04, 0.10, 0.22), width=1.5)
            page.insert_text(fitz.Point(95, 475), "c² = a² + b²     |     f(x) = mx + c", fontsize=18, fontname="hebo", color=(0.38, 0.85, 1.0))
            page.insert_text(fitz.Point(95, 520), "Un = a + (n - 1)b     |     L = πr²", fontsize=17, fontname="helv", color=(0.9, 0.95, 1.0))
            page.insert_text(fitz.Point(95, 565), "S + T - R = 2     |     Sn = ½n(a + Un)", fontsize=17, fontname="helv", color=(0.9, 0.95, 1.0))

            page.insert_text(fitz.Point(72, 730), p["footer"], fontsize=12, fontname="hebo", color=(0.75, 0.86, 1.0))
        else:
            if p.get("chapter"):
                lvl = 2 if p["chapter"][0].isdigit() else 1
                toc_list.append([lvl, p["chapter"], page_num])

            # Page background
            page.draw_rect(fitz.Rect(0, 0, 595, 842), color=(0.99, 0.99, 1.0), fill=(0.99, 0.99, 1.0))
            # Top header bar
            page.draw_rect(fitz.Rect(0, 0, 595, 64), color=(0.07, 0.16, 0.32), fill=(0.07, 0.16, 0.32))
            page.insert_text(
                fitz.Point(48, 40),
                "BUKU PAKET KURIKULUM MERDEKA • LABSCHOOL",
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

            # Title
            page.insert_text(fitz.Point(48, 118), p["title"], fontsize=24, fontname="hebo", color=(0.07, 0.16, 0.32))
            page.draw_line(fitz.Point(48, 132), fitz.Point(547, 132), color=(0.05, 0.65, 0.91), width=2.5)

            # Body text
            page.insert_textbox(
                fitz.Rect(48, 155, 547, 635),
                p["body"],
                fontsize=12.5,
                fontname="helv",
                color=(0.15, 0.18, 0.24),
                lineheight=1.45,
            )

            # Highlight Callout Box at bottom
            page.draw_rect(fitz.Rect(48, 650, 547, 765), color=(0.05, 0.65, 0.91), fill=(0.93, 0.97, 1.0), width=1.5)
            page.insert_text(fitz.Point(66, 680), p.get("box_title", "Catatan Penting"), fontsize=13, fontname="hebo", color=(0.04, 0.35, 0.60))
            page.insert_textbox(
                fitz.Rect(66, 692, 530, 755),
                p.get("box_text", ""),
                fontsize=11.5,
                fontname="helv",
                color=(0.1, 0.2, 0.35),
            )

            # Footer
            page.draw_line(fitz.Point(48, 795), fitz.Point(547, 795), color=(0.82, 0.85, 0.90), width=1)
            page.insert_text(fitz.Point(48, 815), "FlipLabs Digital Book Viewer • books.labschool.xyz", fontsize=9.5, fontname="helv", color=(0.45, 0.50, 0.58))
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
            "badge": "KURIKULUM MERDEKA • MODUL PRAKTIKUM",
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
                "• Sel Tumbuhan memiliki Dinding Sel (selulosa), Kloroplas (fotosintesis), dan Vakuola besar.\n"
                "• Sel Hewan tidak memiliki dinding sel, namun memiliki Sentriol untuk pembelahan sel.\n\n"
                "Organel Penting Sel:\n"
                "1. Nukleus (Inti Sel): pusat pengendali genetik (DNA).\n"
                "2. Mitokondria: pusat respirasi seluler penghasil energi ATP.\n"
                "3. Ribosom: tempat sintesis protein."
            ),
            "box_title": "Rumus Perbesaran Total Mikroskop Cahaya",
            "box_text": "M_total = M_lensa_okuler × M_lensa_objektif",
        },
        {
            "chapter": "Bab 2: Usaha, Energi, dan Pesawat Sederhana",
            "title": "Bab 2: Usaha & Pesawat Sederhana",
            "body": (
                "Usaha (W) dalam fisika didefinisikan sebagai hasil kali gaya (F) yang bekerja "
                "searah perpindahan dengan besar perpindahan benda (s):\n"
                "    W = F × s   (Satuan: Joule)\n\n"
                "Energi Kinetik dan Energi Potensial Gravitasi:\n"
                "• Ek = ½ m v²\n"
                "• Ep = m g h\n\n"
                "Keuntungan Mekanis (KM) Pesawat Sederhana:\n"
                "    KM = Beban (w) / Gaya Kuasa (F) = Lengan Kuasa (lk) / Lengan Beban (lb)"
            ),
            "box_title": "Hukum Kekekalan Energi Mekanik",
            "box_text": "Em1 = Em2   ⇔   Ep1 + Ek1 = Ep2 + Ek2",
        },
        {
            "chapter": "Bab 3: Getaran, Gelombang, dan Cahaya",
            "title": "Bab 3: Getaran & Gelombang",
            "body": (
                "Getaran adalah gerak bolak-balik secara periodik melalui titik kesetimbangan.\n\n"
                "Hubungan Frekuensi (f), Periode (T), Panjang Gelombang (λ), dan Cepat Rambat (v):\n"
                "• f = n / t  (Hertz)    dan    T = t / n = 1 / f  (sekon)\n"
                "• v = λ × f  =  λ / T   (m/s)\n\n"
                "Rumus Cermin Cekung / Cembung dan Lensa:\n"
                "    1/f = 1/s + 1/s'    dan    Perbesaran M = |s' / s| = |h' / h|"
            ),
            "box_title": "Gelombang Bunyi & Sonar",
            "box_text": "Kedalaman laut dihitung dengan d = (v × t) / 2 karena bunyi menempuh perjalanan pulang-pergi.",
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
            "badge": "BUKU SAKU SISWA • EDISI UMUM",
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
    print("[SUCCESS] Generated and converted all 3 sample books (Enterprise, Pro, Basic)!")


if __name__ == "__main__":
    main()
