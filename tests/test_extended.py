"""Unit test untuk modul src.extended (StegoCipher multi-alfabet)."""

import unittest
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pandas as pd
from src.extended import (
    StegoCipher,
    ALPHABET_4,
    ALPHABET_8,
    ALPHABET_16,
    compare_alphabets,
)
from src.baseline import embed_baseline, extract_baseline

# Cover memiliki 37+ spasi agar cukup untuk semua varian alfabet
COVER = (
    "Steganografi adalah teknik menyembunyikan pesan rahasia di dalam "
    "media lain sehingga keberadaannya tidak terdeteksi oleh pihak ketiga "
    "yang tidak berwenang untuk membaca isi pesan tersebut sama sekali. "
    "Metode ini memanfaatkan karakter Unicode tak kasat mata sebagai "
    "pembawa informasi tersembunyi di dalam teks biasa."
)


class TestRoundtrip(unittest.TestCase):
    """Pesan yang disematkan harus bisa diekstrak kembali identik untuk semua alfabet."""

    def _assert_roundtrip(self, alphabet: list, pesan: str):
        cipher = StegoCipher(alphabet)
        stego = cipher.embed(COVER, pesan)
        self.assertEqual(cipher.extract(stego), pesan)

    def test_roundtrip_alphabet4(self):
        self._assert_roundtrip(ALPHABET_4, "Hi")

    def test_roundtrip_alphabet8(self):
        self._assert_roundtrip(ALPHABET_8, "Hi")

    def test_roundtrip_alphabet16(self):
        self._assert_roundtrip(ALPHABET_16, "Hi")

    def test_roundtrip_pesan_panjang_alphabet8(self):
        """Pesan lebih panjang tetap harus diekstrak benar dengan ALPHABET_8."""
        self._assert_roundtrip(ALPHABET_8, "rahasia")

    def test_roundtrip_pesan_panjang_alphabet16(self):
        """Pesan lebih panjang tetap harus diekstrak benar dengan ALPHABET_16."""
        self._assert_roundtrip(ALPHABET_16, "rahasia")

    def test_tanpa_null_byte_alphabet8(self):
        """Hasil ekstrak ALPHABET_8 tidak boleh mengandung null byte ekstra."""
        cipher = StegoCipher(ALPHABET_8)
        stego = cipher.embed(COVER, "Hi")
        self.assertNotIn("\x00", cipher.extract(stego))

    def test_tanpa_null_byte_alphabet16(self):
        """Hasil ekstrak ALPHABET_16 tidak boleh mengandung null byte ekstra."""
        cipher = StegoCipher(ALPHABET_16)
        stego = cipher.embed(COVER, "Hi")
        self.assertNotIn("\x00", cipher.extract(stego))


class TestBitsPerSpace(unittest.TestCase):
    """Setiap varian harus melaporkan bits_per_space yang benar."""

    def test_alphabet4_2_bits(self):
        self.assertEqual(StegoCipher(ALPHABET_4).bits_per_space, 2)

    def test_alphabet8_3_bits(self):
        self.assertEqual(StegoCipher(ALPHABET_8).bits_per_space, 3)

    def test_alphabet16_4_bits(self):
        self.assertEqual(StegoCipher(ALPHABET_16).bits_per_space, 4)


class TestCapacityScaling(unittest.TestCase):
    """Kapasitas harus meningkat seiring ukuran alfabet."""

    def setUp(self):
        self.cap4 = StegoCipher(ALPHABET_4).capacity(COVER)
        self.cap8 = StegoCipher(ALPHABET_8).capacity(COVER)
        self.cap16 = StegoCipher(ALPHABET_16).capacity(COVER)

    def test_kapasitas_meningkat_monoton(self):
        """ALPHABET_8 harus memiliki kapasitas lebih besar dari ALPHABET_4."""
        self.assertGreater(self.cap8["bits"], self.cap4["bits"])

    def test_kapasitas_alphabet16_terbesar(self):
        """ALPHABET_16 harus memiliki kapasitas terbesar."""
        self.assertGreater(self.cap16["bits"], self.cap8["bits"])

    def test_rasio_kapasitas_tepat(self):
        """Rasio kapasitas harus sesuai dengan perbandingan bits_per_space."""
        # cap8 / cap4 = 3/2, cap16 / cap4 = 4/2 = 2
        self.assertAlmostEqual(self.cap8["bits"] / self.cap4["bits"], 3 / 2)
        self.assertAlmostEqual(self.cap16["bits"] / self.cap4["bits"], 4 / 2)

    def test_spasi_sama_semua_varian(self):
        """Jumlah spasi harus identik untuk semua varian (cover text yang sama)."""
        self.assertEqual(self.cap4["spaces"], self.cap8["spaces"])
        self.assertEqual(self.cap8["spaces"], self.cap16["spaces"])

    def test_bits_konsisten_dengan_rumus(self):
        """bits harus sama dengan spaces × bits_per_space."""
        for cap in (self.cap4, self.cap8, self.cap16):
            self.assertEqual(cap["bits"], cap["spaces"] * cap["bits_per_space"])


class TestKompatibilitasBaseline(unittest.TestCase):
    """StegoCipher(ALPHABET_4) harus kompatibel penuh dengan baseline.py."""

    def test_embed_identik_dengan_baseline(self):
        """Output embed harus byte-identical dengan baseline untuk ALPHABET_4."""
        pesan = "Hi"
        stego_extended = StegoCipher(ALPHABET_4).embed(COVER, pesan)
        stego_baseline = embed_baseline(COVER, pesan)
        self.assertEqual(stego_extended, stego_baseline)

    def test_extract_baseline_baca_stego_extended(self):
        """baseline.extract_baseline harus bisa membaca stego dari StegoCipher(ALPHABET_4)."""
        pesan = "Hi"
        stego = StegoCipher(ALPHABET_4).embed(COVER, pesan)
        self.assertEqual(extract_baseline(stego), pesan)

    def test_extended_baca_stego_baseline(self):
        """StegoCipher(ALPHABET_4).extract harus bisa membaca stego dari baseline."""
        pesan = "Hi"
        stego = embed_baseline(COVER, pesan)
        self.assertEqual(StegoCipher(ALPHABET_4).extract(stego), pesan)


class TestAlfabetTidakValid(unittest.TestCase):
    """Konstruktor harus menolak alfabet yang tidak valid."""

    def test_ukuran_bukan_pangkat_dua(self):
        """Alfabet dengan 3 karakter harus menghasilkan ValueError."""
        with self.assertRaises(ValueError):
            StegoCipher([" ", " ", " "])

    def test_alfabet_satu_karakter(self):
        """Alfabet satu karakter harus menghasilkan ValueError."""
        with self.assertRaises(ValueError):
            StegoCipher([" "])

    def test_duplikat_karakter(self):
        """Alfabet dengan karakter duplikat harus menghasilkan ValueError."""
        with self.assertRaises(ValueError):
            StegoCipher([" ", " ", " ", " "])

    def test_cover_terlalu_kecil(self):
        """ValueError harus dilempar jika cover text tidak cukup kapasitas."""
        with self.assertRaises(ValueError):
            StegoCipher(ALPHABET_4).embed("a b", "pesan yang sangat panjang sekali")


class TestCompareAlphabets(unittest.TestCase):
    """Fungsi compare_alphabets harus mengembalikan DataFrame yang benar."""

    @classmethod
    def setUpClass(cls):
        cls.df = compare_alphabets(COVER, "Hi")

    def test_mengembalikan_dataframe(self):
        self.assertIsInstance(self.df, pd.DataFrame)

    def test_tiga_baris(self):
        """Harus ada tepat 3 baris (satu per varian alfabet)."""
        self.assertEqual(len(self.df), 3)

    def test_kolom_lengkap(self):
        """Semua kolom yang diperlukan harus ada."""
        kolom_wajib = {
            "alphabet_size", "bits_per_space",
            "capacity_bits", "file_size_increase_pct",
        }
        self.assertTrue(kolom_wajib.issubset(set(self.df.columns)))

    def test_urutan_alphabet_size(self):
        """Baris harus berurutan dari alfabet terkecil ke terbesar."""
        sizes = list(self.df["alphabet_size"])
        self.assertEqual(sizes, sorted(sizes))

    def test_capacity_meningkat(self):
        """capacity_bits harus meningkat seiring alphabet_size."""
        caps = list(self.df["capacity_bits"])
        self.assertEqual(caps, sorted(caps))

    def test_file_size_increase_positif(self):
        """Semua varian harus menambah ukuran file (spasi biasa → Unicode multibyte)."""
        self.assertTrue(all(self.df["file_size_increase_pct"] > 0))

    def test_csv_tersimpan(self):
        """File CSV harus terbuat di experiments/results/."""
        csv_path = (
            Path(__file__).parent.parent
            / "experiments" / "results" / "capacity_comparison.csv"
        )
        self.assertTrue(csv_path.exists(), f"File CSV tidak ditemukan: {csv_path}")


class TestExtractTanpaData(unittest.TestCase):
    """Fungsi extract harus aman dipanggil pada input tanpa karakter stego."""

    def test_teks_biasa(self):
        """Teks tanpa karakter stego harus menghasilkan string kosong."""
        cipher = StegoCipher(ALPHABET_8)
        self.assertEqual(cipher.extract("Ini teks biasa tanpa karakter tersembunyi."), "")

    def test_string_kosong(self):
        for alphabet in (ALPHABET_4, ALPHABET_8, ALPHABET_16):
            self.assertEqual(StegoCipher(alphabet).extract(""), "")


if __name__ == "__main__":
    unittest.main(verbosity=2)
