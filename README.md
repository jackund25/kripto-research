# Steganografi Teks Berbasis Unicode Whitespace

Repositori ini berisi implementasi dan eksperimen untuk penelitian steganografi teks menggunakan karakter Unicode whitespace tak terlihat sebagai media penyisipan pesan rahasia.

## Latar Belakang

Penelitian ini mengkaji metode TREND (*Text Steganography Using Unicode Non-printing Characters*) yang menggunakan empat karakter Unicode tak terlihat (U+200B, U+200C, U+200D, U+FEFF) sebagai alfabet biner untuk menyembunyikan pesan di dalam teks biasa. Selain itu, penelitian ini mengusulkan ekstensi alfabet dengan karakter Unicode tambahan untuk meningkatkan kapasitas penyisipan.

## Struktur Direktori

```
trend_stego/
├── src/
│   ├── baseline.py       # Implementasi TREND asli (alfabet 4 karakter)
│   ├── extended.py       # Ekstensi alfabet dengan karakter Unicode tambahan
│   └── utils.py          # Fungsi-fungsi pembantu
├── experiments/
│   └── results/          # Output CSV hasil eksperimen
├── tests/                # Unit test
└── sample_texts/         # Teks uji untuk eksperimen
```

## Instalasi

```bash
pip install -r requirements.txt
```

## Penggunaan

*(akan diisi setelah implementasi selesai)*
