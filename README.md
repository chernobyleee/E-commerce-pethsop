# PetShopin - Platform E-Commerce Kebutuhan Hewan Peliharaan

![PetShopin Logo](app/static/images/logo.png) {# GANTI DENGAN PATH LOGO ANDA YANG BENAR #}

Selamat datang di PetShopin! Ini adalah aplikasi web e-commerce yang dirancang khusus untuk memenuhi semua kebutuhan hewan peliharaan kesayangan Anda. Dibangun dengan Flask (Python) dan diintegrasikan dengan template modern, PetShopin menawarkan pengalaman berbelanja yang mudah dan menyenangkan.

## Fitur Utama

* **Katalog Produk Dinamis:** Tampilan produk yang menarik dengan detail, filter berdasarkan kategori, dan pencarian.
* **Manajemen Pengguna:** Registrasi, login, profil pengguna, dan edit profil.
* **Keranjang Belanja Fungsional:** Tambah, update kuantitas, dan hapus item dari keranjang.
* **Proses Checkout Lengkap:**
    * Formulir alamat pengiriman dengan pencarian lokasi (integrasi API RajaOngkir/Khomsip).
    * Perhitungan ongkos kirim otomatis dengan JNE.
    * Ringkasan pesanan yang jelas.
* **Integrasi Pembayaran Midtrans:** Pembayaran online yang aman menggunakan Midtrans Snap.
* **Manajemen Pesanan Pengguna:** Pelanggan dapat melihat riwayat pesanan dan detailnya, termasuk status dan pelacakan.
* **Pelacakan Pesanan (Eksternal & Internal):** Fitur untuk melacak pesanan berdasarkan Nomor Invoice dan Nomor Resi.
* **Alur Pembatalan Pesanan:** Pelanggan dapat meminta pembatalan dengan alasan, yang kemudian diproses oleh admin.
* **Dasbor Admin Komprehensif:**
    * Statistik penjualan (harian, bulanan, total).
    * Statistik pesanan berdasarkan status.
    * Statistik produk (total, stok menipis, habis stok).
    * Manajemen Produk (CRUD).
    * Manajemen Kategori (CRUD).
    * Manajemen Pesanan (lihat detail, update status, input resi, proses refund).
    * Manajemen Pengguna (lihat daftar, edit role).
* **Notifikasi:** Sistem notifikasi sederhana untuk admin terkait aktivitas terbaru.
* **Desain Responsif:** Tampilan yang menyesuaikan dengan baik di berbagai perangkat.

## Teknologi yang Digunakan

* **Backend:** Python, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-Login, Flask-WTF
* **Frontend:** HTML, CSS, JavaScript, Jinja2, Bootstrap 4 (diadaptasi dari template Famms)
* **Database:** SQLite (atau PostgreSQL/MySQL sesuai konfigurasi Anda)
* **API Eksternal:** Midtrans (Payment Gateway), RajaOngkir/Khomsip (Ongkos Kirim & Lokasi)

## Setup Lokal (Contoh Dasar)

1.  Clone repository: `git clone https://github.com/NAMA_ANDA/NAMA_REPO_ANDA.git`
2.  Masuk ke direktori proyek: `cd NAMA_REPO_ANDA`
3.  Buat dan aktifkan virtual environment:
    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Untuk Linux/Mac
    # .venv\Scripts\activate  # Untuk Windows
    ```
4.  Install dependencies: `pip install -r requirements.txt`
5.  Setup variabel environment (buat file `.env` dari `.env.example` jika ada).
6.  Inisialisasi dan migrasi database:
    ```bash
    flask db init  # Hanya jika belum pernah
    flask db migrate -m "Initial migration"
    flask db upgrade
    ```
7.  Jalankan aplikasi: `flask run`

## TODO / Rencana Pengembangan Selanjutnya

* [ ] Fitur ulasan produk oleh pelanggan.
* [ ] Notifikasi email untuk status pesanan.
* [ ] Fitur wishlist.
* [ ] Optimasi performa dan query database.
* [ ] Penambahan metode pembayaran lain.

---

Kontribusi selalu diterima! Silakan buat Pull Request atau buka Issue.
