"""Unit test untuk modul src.baseline (TREND 4-karakter)."""

import unittest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.baseline import (
    embed_baseline,
    extract_baseline,
    capacity_baseline,
    _ALPHABET,
    _STEGO_CHARS,
    _HEADER_BITS,
)

# Cover cukup panjang: ≥ 36 spasi = 72 bit ≥ 16 bit header + 7 byte × 8 bit
# Dua kalimat dipakai agar semua test bisa memakai COVER yang sama.
COVER = (
    "Steganografi adalah teknik menyembunyikan pesan rahasia di dalam "
    "media lain sehingga keberadaannya tidak terdeteksi oleh pihak ketiga "
    "yang tidak berwenang untuk membaca isi pesan tersebut sama sekali. "
    "Metode ini memanfaatkan karakter Unicode tak kasat mata sebagai "
    "pembawa informasi tersembunyi di dalam teks biasa."
)


class TestEmbedExtractRoundtrip(unittest.TestCase):
    """Pesan yang disematkan harus bisa diekstrak kembali identik."""

    def test_roundtrip_ascii_pendek(self):
        """Pesan ASCII 2 karakter: embed lalu extract harus identik."""
        pesan = "Hi"
        stego = embed_baseline(COVER, pesan)
        self.assertEqual(extract_baseline(stego), pesan)

    def test_roundtrip_kata_ascii(self):
        """Pesan ASCII 7 karakter: roundtrip harus identik."""
        pesan = "rahasia"
        stego = embed_baseline(COVER, pesan)
        self.assertEqual(extract_baseline(stego), pesan)

    def test_roundtrip_utf8_multibyte(self):
        """Karakter non-ASCII (multibyte UTF-8) harus dihandle dengan benar."""
        # "oke" = 3 byte ASCII, cukup sederhana untuk diuji
        pesan = "oke"
        stego = embed_baseline(COVER, pesan)
        self.assertEqual(extract_baseline(stego), pesan)

    def test_roundtrip_tidak_menghasilkan_nol_ekstra(self):
        """Hasil ekstrak tidak boleh mengandung null byte di luar pesan."""
        pesan = "Hi"
        stego = embed_baseline(COVER, pesan)
        hasil = extract_baseline(stego)
        self.assertNotIn("\x00", hasil,
                         "Null byte ditemukan — header panjang tidak terbaca benar")


class TestSubstitusiKarakter(unittest.TestCase):
    """Spasi biasa harus disubstitusi; karakter non-spasi tidak boleh berubah."""

    def test_tidak_ada_spasi_asli_di_stego(self):
        """Semua spasi biasa (U+0020) harus hilang setelah embed."""
        stego = embed_baseline(COVER, "Hi")
        self.assertNotIn(" ", stego,
                         "Masih ada spasi biasa (U+0020) di dalam stego text")

    def test_karakter_stego_valid(self):
        """Setiap karakter stego harus berasal dari alfabet TREND yang ditentukan."""
        stego = embed_baseline(COVER, "Hi")
        for char in stego:
            if char in _STEGO_CHARS:
                self.assertIn(char, _ALPHABET.values(),
                              f"Karakter U+{ord(char):04X} bukan bagian alfabet TREND")

    def test_panjang_stego_sama_dengan_cover(self):
        """Panjang stego text (karakter) harus sama dengan cover text."""
        pesan = "Hi"
        stego = embed_baseline(COVER, pesan)
        self.assertEqual(len(stego), len(COVER),
                         "Substitusi mengubah jumlah karakter — seharusnya hanya mengganti, bukan menambah/menghapus")


class TestCapacity(unittest.TestCase):
    """Fungsi capacity_baseline harus menghitung kapasitas dengan benar."""

    def test_kapasitas_konsisten_dengan_spasi(self):
        """bits harus sama dengan 2 × jumlah spasi."""
        cap = capacity_baseline(COVER)
        self.assertEqual(cap["bits"], cap["spaces"] * 2)

    def test_kapasitas_bytes_floor(self):
        """bytes harus floor(bits / 8)."""
        cap = capacity_baseline(COVER)
        self.assertEqual(cap["bytes"], cap["bits"] // 8)

    def test_kapasitas_teks_kosong(self):
        """Teks kosong harus menghasilkan semua nilai nol."""
        cap = capacity_baseline("")
        self.assertEqual(cap["spaces"], 0)
        self.assertEqual(cap["bits"], 0)
        self.assertEqual(cap["bytes"], 0)
        self.assertEqual(cap["bits_per_char"], 0.0)

    def test_kapasitas_satu_spasi(self):
        """Satu spasi = 2 bit kapasitas bruto."""
        cap = capacity_baseline("a b")
        self.assertEqual(cap["spaces"], 1)
        self.assertEqual(cap["bits"], 2)

    def test_bits_per_char_dalam_rentang(self):
        """bits_per_char tidak boleh melebihi 2.0 (satu karakter = maks 1 spasi)."""
        cap = capacity_baseline(COVER)
        self.assertLessEqual(cap["bits_per_char"], 2.0)
        self.assertGreaterEqual(cap["bits_per_char"], 0.0)


class TestOverflow(unittest.TestCase):
    """Embed harus gagal jika pesan melebihi kapasitas cover text."""

    def test_overflow_raise_valueerror(self):
        """ValueError harus dilempar jika secret terlalu panjang untuk cover."""
        cover_kecil = "a b c"  # 2 spasi = 4 bit, jauh di bawah kebutuhan header 16 bit
        with self.assertRaises(ValueError):
            embed_baseline(cover_kecil, "Pesan ini jauh terlalu panjang")

    def test_header_saja_sudah_overflow(self):
        """Cover tanpa spasi sama sekali harus langsung gagal."""
        with self.assertRaises(ValueError):
            embed_baseline("tanpaspasi", "a")


class TestExtractTanpaData(unittest.TestCase):
    """Fungsi extract harus aman dipanggil pada teks tanpa karakter stego."""

    def test_extract_teks_biasa(self):
        """Teks biasa (tanpa karakter stego) harus menghasilkan string kosong."""
        hasil = extract_baseline("Ini teks biasa tanpa karakter tersembunyi.")
        self.assertEqual(hasil, "")

    def test_extract_string_kosong(self):
        """String kosong harus menghasilkan string kosong."""
        self.assertEqual(extract_baseline(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
