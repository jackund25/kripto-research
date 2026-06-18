# Ringkasan Hasil Eksperimen

Dokumen ini merangkum temuan utama dari dua eksperimen yang dijalankan dalam project
steganografi Unicode whitespace ini.

---

## Eksperimen 1 — Analisis Kapasitas

**Setup:** Secret uji `"rahasia"` (7 byte), tiga teks dengan panjang berbeda,
tiga varian alfabet (ALPHABET_4/8/16). Total: 9 kombinasi, semua roundtrip OK.

### Kapasitas per Teks per Alfabet

| Teks | Kata | Spasi | Alfabet | Bit/Spasi | Kapasitas (bit) | Kapasitas (byte) | Overhead |
|---|---|---|---|---|---|---|---|
| short | 97 | 89 | ALPHABET_4 | 2 | 178 | 22 | 25.00% |
| short | 97 | 89 | ALPHABET_8 | 3 | 267 | 33 | 25.00% |
| short | 97 | 89 | ALPHABET_16 | 4 | 356 | 44 | 25.00% |
| medium | 348 | 320 | ALPHABET_4 | 2 | 640 | 80 | 25.74% |
| medium | 348 | 320 | ALPHABET_8 | 3 | 960 | 120 | 25.74% |
| medium | 348 | 320 | ALPHABET_16 | 4 | 1,280 | 160 | 25.74% |
| long | 811 | 748 | ALPHABET_4 | 2 | 1,496 | 187 | 25.90% |
| long | 811 | 748 | ALPHABET_8 | 3 | 2,244 | 280 | 25.90% |
| long | 811 | 748 | ALPHABET_16 | 4 | 2,992 | 374 | 25.90% |

### Temuan Utama

1. **Kapasitas meningkat linear** seiring ukuran alfabet: ALPHABET_8 memberikan
   kapasitas 1.5× lipat ALPHABET_4, dan ALPHABET_16 memberikan 2× lipat.

2. **Overhead identik antar alfabet** pada teks yang sama (~25–26%). Ini terjadi
   karena hampir semua karakter Unicode stego dalam ketiga alfabet berukuran 3 byte
   dalam UTF-8 (menggantikan spasi 1 byte), sehingga overhead ditentukan semata-mata
   oleh kepadatan spasi dalam teks, bukan oleh pilihan alfabet.

   Formula: `overhead ≈ (2 × jumlah_spasi) / ukuran_file_asli × 100%`

3. **Overhead meningkat perlahan** seiring panjang teks (25.00% → 25.90%) karena
   teks yang lebih panjang cenderung memiliki proporsi spasi yang sedikit lebih tinggi.

4. Memperluas alfabet dari 4 ke 16 karakter **menggandakan kapasitas tanpa menambah
   overhead** — ini adalah argumen utama untuk penggunaan alfabet yang diperluas.

---

## Eksperimen 2 — Analisis Ketahanan

**Setup:** ALPHABET_8 (3 bit/spasi), cover `medium.txt` (320 spasi),
secret 32 byte. Slot terpakai: 91 dari 320 (28.4%).

### Survival Rate per Serangan

| Serangan | Deskripsi | Stego Char Tersisa | Exact Match | Survival Rate |
|---|---|---|---|---|
| baseline | Tanpa serangan (kontrol) | 320/320 (0% hilang) | OK | 100.00% |
| normalize | Ganti semua stego char → U+0020 | 0/320 (100% hilang) | GAGAL | 0.00% |
| strip_unicode | Hapus semua karakter non-ASCII | 0/320 (100% hilang) | GAGAL | 0.00% |
| double_space | Autocorrect double-space | 320/320 (0% hilang) | OK | 100.00% |
| truncate_75 | Potong teks hingga 75% | 248/320 (22% hilang) | OK | 100.00% |
| truncate_50 | Potong teks hingga 50% | 159/320 (50% hilang) | OK | 100.00% |
| truncate_25 | Potong teks hingga 25% | 83/320 (74% hilang) | GAGAL | 0.00% |

**Ringkasan:** 4 bertahan penuh | 0 bertahan sebagian | 3 gagal total

### Temuan Utama

1. **Imunitas terhadap double-space autocorrect**: Serangan ini sama sekali tidak
   berdampak (survival 100%) karena TREND embedding mengganti **semua** U+0020 dengan
   karakter stego — tidak ada double ASCII-space yang tersisa setelah embedding.
   Ini adalah sifat imunitas bawaan dari skema substitusi total.

2. **Rentan terhadap normalisasi Unicode**: Baik `normalize` maupun `strip_unicode`
   menghancurkan payload sepenuhnya (survival 0%). Sistem tidak tahan terhadap
   pemrosesan teks yang mengubah atau menghapus karakter non-ASCII.

3. **Perilaku all-or-nothing**: Tidak ditemukan recovery parsial — semua hasil adalah
   tepat 0% atau tepat 100%. Ini disebabkan oleh protokol length-prefix 16-bit:
   sistem hanya mengembalikan pesan jika **seluruh** bit payload tersedia; jika tidak,
   dikembalikan string kosong.

4. **Ambang batas pemotongan**: Sistem gagal ketika teks dipotong di bawah ~28.4%
   panjang aslinya. Formula: sistem berhasil jika
   `pct ≥ ⌈(16 + N×8) / bps⌉ / S`
   di mana N = panjang secret (byte), bps = bit per spasi, S = total spasi.
   Pada eksperimen ini: ⌈(16 + 256) / 3⌉ / 320 = 91/320 ≈ 28.4%.

---

## Kesimpulan

| Aspek | ALPHABET_4 | ALPHABET_8 | ALPHABET_16 |
|---|---|---|---|
| Kapasitas (medium.txt) | 80 byte | 120 byte | 160 byte |
| Overhead | ~25.7% | ~25.7% | ~25.7% |
| Ketahanan normalisasi | Rendah | Rendah | Rendah |
| Ketahanan double-space | Tinggi | Tinggi | Tinggi |
| Ketahanan truncate 50% | Tinggi\* | Tinggi\* | Tinggi\* |

\* Bergantung pada jumlah spasi dan panjang secret.

**Rekomendasi:** Gunakan ALPHABET_16 untuk kapasitas maksimal dengan overhead yang
sama dengan ALPHABET_4. Tambahkan lapisan enkripsi sebelum embedding untuk ketahanan
terhadap normalisasi Unicode.

---

## Eksperimen Bonus 3a — Teks Cover Bahasa Indonesia

**Setup:** `sample_texts/indonesian.txt` (245 kata, 240 spasi, 1851 byte UTF-8),
dibandingkan dengan `medium.txt` Inggris (348 kata, 320 spasi, 2486 byte).

### Roundtrip Test (9 kombinasi)

| Secret | Alfabet | Hasil |
|---|---|---|
| `'rahasia'` (7 byte) | ALPHABET_4 | OK |
| `'rahasia'` (7 byte) | ALPHABET_8 | OK |
| `'rahasia'` (7 byte) | ALPHABET_16 | OK |
| `'pesan dalam bahasa indonesia'` (29 byte) | ALPHABET_4 | OK |
| `'pesan dalam bahasa indonesia'` (29 byte) | ALPHABET_8 | OK |
| `'pesan dalam bahasa indonesia'` (29 byte) | ALPHABET_16 | OK |
| `'kriptografi: αβγ'` (20 byte, UTF-8 multi-byte) | ALPHABET_4 | OK |
| `'kriptografi: αβγ'` (20 byte, UTF-8 multi-byte) | ALPHABET_8 | OK |
| `'kriptografi: αβγ'` (20 byte, UTF-8 multi-byte) | ALPHABET_16 | OK |

### Kapasitas: Indonesia vs Inggris

| Alfabet | Indonesia (bit) | Inggris (bit) | Selisih |
|---|---|---|---|
| ALPHABET_4 | 480 | 640 | -160 |
| ALPHABET_8 | 720 | 960 | -240 |
| ALPHABET_16 | 960 | 1,280 | -320 |

### Temuan

1. **Sistem language-agnostic**: Semua 9 roundtrip berhasil. Logika embedding tidak
   bergantung pada bahasa — hanya bergantung pada jumlah karakter spasi U+0020 di teks.

2. **Teks Indonesia memiliki rasio spasi lebih tinggi**: 240/245 = 98% spasi per kata
   vs 92% pada medium.txt Inggris. Meski begitu, kapasitas total lebih kecil karena
   jumlah kata (dan spasi absolut) lebih sedikit.

3. **Secret UTF-8 multi-byte berhasil**: `'kriptografi: αβγ'` yang mengandung huruf
   Yunani (3 byte per karakter di UTF-8) diembed dan diekstrak dengan benar di ketiga
   alfabet. Sistem menangani semua string UTF-8 valid tanpa kasus khusus.

---

## Eksperimen Bonus 3b — Granular Threshold Truncation

**Setup:** identik dengan Exp2 — ALPHABET_8, `medium.txt` (320 spasi), secret 32 byte,
slot dibutuhkan: 91. Pengujian per 1% dari 25% hingga 40%.

### Hasil per Persentase

| Pct | Karakter tersisa | Slot ada | Slot butuh | Hasil |
|---|---|---|---|---|
| 25% | 621 | 83 | 91 | GAGAL |
| 26% | 646 | 88 | 91 | GAGAL |
| 27% | 671 | 90 | 91 | GAGAL |
| **28%** | **696** | **93** | **91** | **OK** |
| 29% | 720 | 96 | 91 | OK |
| 30% | 745 | 99 | 91 | OK |
| 31%–40% | — | >100 | 91 | OK |

### Temuan

1. **Threshold empiris: 28% panjang teks** — sistem mulai berhasil saat teks tidak
   dipotong lebih dari 72%. Di 27%, hanya tersisa 90 slot (kurang 1 dari 91 yang
   dibutuhkan); di 28%, sudah ada 93 slot.

2. **Threshold teoritis vs empiris sangat dekat**: Formula `⌈(16 + N×8) / bps⌉ / S`
   menghasilkan 28.44% (slot), sedangkan empiris 28% (karakter teks). Selisih kecil
   karena distribusi spasi dalam teks relatif merata.

3. **Konfirmasi perilaku all-or-nothing**: Tidak ada survival parsial di antara 0%
   dan 100% meskipun pengujian dilakukan per 1%. Transisi langsung dari GAGAL (0%)
   ke OK (100%) saat slot melewati ambang batas.
