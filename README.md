# Steganografi Teks Berbasis Unicode Whitespace

Implementasi dan eksperimen untuk penelitian steganografi teks menggunakan karakter
Unicode whitespace tak terlihat sebagai media penyisipan pesan rahasia.
Project ini mereplikasi dan mengembangkan metode **TREND** (Hellmeier et al., 2025).

---

## Deskripsi

Project ini mengkaji dua hal utama:

1. **Replikasi TREND** — mengimplementasikan metode steganografi yang mengganti spasi
   biasa (U+0020) dengan empat karakter Unicode tak terlihat sebagai alfabet biner
   (2 bit per spasi).

2. **Ekstensi Alfabet** — mengusulkan dan mengevaluasi varian alfabet yang diperluas
   (8 dan 16 karakter) untuk meningkatkan kapasitas embedding tanpa menambah overhead
   ukuran file.

### Varian Alfabet

| Alfabet | Karakter | Bit/Spasi | Codepoint |
|---|---|---|---|
| ALPHABET_4 | 4 | 2 | U+2004, U+2005, U+2008, U+202F |
| ALPHABET_8 | 8 | 3 | + U+2000, U+2001, U+2002, U+2003 |
| ALPHABET_16 | 16 | 4 | + U+2006, U+2009, U+200A, U+205F, U+3000, U+00A0, U+2007, U+200B |

---

## Struktur Direktori

```
kripto-research/
├── src/
│   ├── baseline.py        # Implementasi TREND asli (ALPHABET_4, 2 bit/spasi)
│   ├── extended.py        # StegoCipher generik + 3 varian alfabet
│   ├── utils.py           # Fungsi pembantu (bits, file size, tabel)
│   └── cli.py             # Command-line interface (argparse)
├── experiments/
│   ├── exp1_capacity.py   # Eksperimen kapasitas (3 teks x 3 alfabet)
│   ├── exp2_robustness.py # Eksperimen ketahanan (7 serangan normalisasi)
│   └── results/           # Output CSV dan PNG (di-generate saat run)
├── tests/
│   ├── test_baseline.py   # 16 unit test untuk baseline.py
│   └── test_extended.py   # 31 unit test untuk extended.py
├── sample_texts/
│   ├── short.txt          # ~97 kata (89 spasi)
│   ├── medium.txt         # ~348 kata (320 spasi)
│   └── long.txt           # ~811 kata (748 spasi)
├── requirements.txt
└── RESULTS.md             # Ringkasan temuan eksperimen
```

---

## Instalasi

```bash
pip install -r requirements.txt
```

Dependensi: `python-docx`, `pypdf`, `pandas`, `matplotlib`

Membutuhkan Python 3.10 atau lebih baru (menggunakan type hints modern).

---

## Menjalankan Eksperimen

### Eksperimen 1 — Analisis Kapasitas

Membandingkan kapasitas embedding dan overhead ukuran file untuk ketiga varian alfabet
pada tiga teks uji.

```bash
python experiments/exp1_capacity.py
```

Output di `experiments/results/`:
- `exp1_results.csv` — data lengkap 9 kombinasi (teks × alfabet)
- `exp1_capacity.png` — bar chart kapasitas per teks per alfabet
- `exp1_overhead.png` — line chart overhead ukuran file vs panjang teks

### Eksperimen 2 — Analisis Ketahanan

Menguji ketahanan payload terhadap 6 jenis serangan normalisasi teks.

```bash
python experiments/exp2_robustness.py
```

Output di `experiments/results/`:
- `exp2_results.csv` — survival rate tiap serangan
- `exp2_robustness.png` — bar chart horizontal survival rate

---

## Penggunaan CLI

### Menyembunyikan pesan (embed)

```bash
python -m src.cli embed \
  --input sample_texts/medium.txt \
  --secret "pesan rahasia" \
  --alphabet 8 \
  --output stego.txt
```

### Mengekstrak pesan (extract)

```bash
python -m src.cli extract --input stego.txt --alphabet 8
```

### Melihat kapasitas cover text

```bash
# Satu alfabet
python -m src.cli capacity --input sample_texts/long.txt --alphabet 16

# Semua varian sekaligus
python -m src.cli capacity --input sample_texts/long.txt --all-alphabets
```

### Membandingkan semua alfabet

```bash
python -m src.cli compare --input sample_texts/long.txt --secret "pesan uji"
```

### Opsi `--alphabet`

| Nilai | Alfabet | Bit/Spasi |
|---|---|---|
| `4` | ALPHABET_4 (default) | 2 |
| `8` | ALPHABET_8 | 3 |
| `16` | ALPHABET_16 | 4 |

---

## Menjalankan Unit Test

```bash
python -m pytest tests/ -v
```

Total: **47 unit test** (16 baseline + 31 extended), semua harus lulus.

---

## Output Eksperimen

| File | Keterangan |
|---|---|
| `exp1_results.csv` | Kapasitas, overhead, roundtrip OK/GAGAL untuk 9 kombinasi |
| `exp1_capacity.png` | Bar chart kapasitas (bit) per teks per alfabet |
| `exp1_overhead.png` | Line chart overhead file size vs panjang teks |
| `exp2_results.csv` | Survival rate untuk 7 kondisi serangan |
| `exp2_robustness.png` | Bar chart survival rate per serangan |

Lihat [RESULTS.md](RESULTS.md) untuk ringkasan temuan.

---

## Referensi

**Paper TREND:**

> Hellmeier, M., Morawietz, N., & Wressnegger, C. (2025).
> *TREND: Text Steganography Using Unicode Non-printing Characters.*
> arXiv preprint arXiv:2502.12710.
> https://arxiv.org/abs/2502.12710
