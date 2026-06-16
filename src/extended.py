# Implementasi StegoCipher dengan alfabet Unicode whitespace yang dapat dikonfigurasi.
# Mendukung 3 varian: 4, 8, 16 karakter → 2, 3, 4 bit per spasi.
#
# Protokol bitstream (identik dengan baseline):
#   [16 bit header: panjang payload dalam byte] + [payload bits UTF-8]
# Kesamaan protokol memastikan StegoCipher(ALPHABET_4) kompatibel dengan baseline.py.

import math
from pathlib import Path

import pandas as pd

# ── Definisi Alfabet ──────────────────────────────────────────────────────────

# Basis 4 karakter — identik dengan baseline.py (TREND asli)
ALPHABET_4: list[str] = [
    " ",  # THREE-PER-EM SPACE      → 00
    " ",  # FOUR-PER-EM SPACE       → 01
    " ",  # PUNCTUATION SPACE       → 10
    " ",  # NARROW NO-BREAK SPACE   → 11
]

# Ekstensi ke 8 karakter: tambah 4 karakter spasi EM/EN
ALPHABET_8: list[str] = ALPHABET_4 + [
    " ",  # EN QUAD                 → 100
    " ",  # EM QUAD                 → 101
    " ",  # EN SPACE                → 110
    " ",  # EM SPACE                → 111
]

# Ekstensi ke 16 karakter
# Catatan rendering:
#   U+3000 (IDEOGRAPHIC SPACE) tampil lebih lebar di font CJK → dapat terdeteksi.
#   U+200B (ZERO WIDTH SPACE) tidak memiliki lebar → tidak terlihat sebagai spasi.
#   Kedua karakter tetap diikutsertakan karena keduanya dipakai dalam literatur
#   steganografi Unicode dan diperlukan untuk mengukur dampaknya secara empiris.
ALPHABET_16: list[str] = ALPHABET_8 + [
    " ",  # SIX-PER-EM SPACE        → 1000
    " ",  # THIN SPACE              → 1001
    " ",  # HAIR SPACE              → 1010
    " ",  # MEDIUM MATHEMATICAL SPACE → 1011
    "　",  # IDEOGRAPHIC SPACE       → 1100  ⚠ tampilan berbeda di CJK
    " ",  # NO-BREAK SPACE          → 1101
    " ",  # FIGURE SPACE            → 1110
    "​",  # ZERO WIDTH SPACE        → 1111  ⚠ lebar nol
]

_HEADER_BITS = 16  # mendukung payload hingga 65 535 byte
_RESULTS_DIR = Path(__file__).parent.parent / "experiments" / "results"


# ── Kelas Utama ───────────────────────────────────────────────────────────────

class StegoCipher:
    """Mesin steganografi whitespace berbasis alfabet Unicode yang dapat dikonfigurasi.

    Setiap spasi biasa (U+0020) dalam cover text diganti dengan satu karakter
    dari alfabet yang dipilih. Ukuran alfabet harus pangkat 2.

    Contoh penggunaan:
        cipher = StegoCipher(ALPHABET_8)
        stego  = cipher.embed("teks cover dengan spasi", "pesan")
        pesan  = cipher.extract(stego)
    """

    def __init__(self, alphabet: list[str]) -> None:
        n = len(alphabet)
        if n < 2 or (n & (n - 1)) != 0:
            raise ValueError(
                f"Ukuran alfabet harus pangkat 2 (2, 4, 8, 16, ...), bukan {n}."
            )
        if len(set(alphabet)) != n:
            raise ValueError("Alfabet mengandung karakter duplikat.")

        self._alphabet = list(alphabet)
        self.bits_per_space: int = int(math.log2(n))
        bps = self.bits_per_space

        # Tabel enkode: string bit → karakter Unicode
        self._encode: dict[str, str] = {
            f"{i:0{bps}b}": ch for i, ch in enumerate(self._alphabet)
        }
        # Tabel dekode: karakter Unicode → string bit
        self._decode: dict[str, str] = {
            ch: f"{i:0{bps}b}" for i, ch in enumerate(self._alphabet)
        }
        self._stego_chars: set[str] = set(self._alphabet)

    # ── Metode Publik ─────────────────────────────────────────────────────────

    def embed(self, text: str, secret: str) -> str:
        """Sembunyikan pesan rahasia ke dalam cover text.

        Semua spasi biasa diganti dengan karakter stego — slot setelah payload
        habis diisi karakter nol (indeks 0 dalam alfabet, U+2004 untuk semua varian).

        Args:
            text:   Cover text berisi spasi biasa sebagai slot embedding.
            secret: Pesan rahasia (plain text, UTF-8).

        Returns:
            Stego text dengan spasi yang sudah disubstitusi.

        Raises:
            ValueError: Kapasitas cover text tidak cukup.
        """
        bits = self._build_bitstream(secret)
        bps = self.bits_per_space

        n_spaces = text.count(" ")
        needed = math.ceil(len(bits) / bps)
        if needed > n_spaces:
            raise ValueError(
                f"Cover text tidak cukup: butuh {needed} slot "
                f"({len(bits)} bit termasuk {_HEADER_BITS} bit header), "
                f"tersedia {n_spaces} spasi."
            )

        zero_chunk = "0" * bps
        hasil = []
        bit_idx = 0

        for char in text:
            if char == " ":
                chunk = bits[bit_idx : bit_idx + bps] if bit_idx < len(bits) else zero_chunk
                hasil.append(self._encode[chunk])
                bit_idx += bps
            else:
                hasil.append(char)

        return "".join(hasil)

    def extract(self, stego: str) -> str:
        """Ekstrak pesan tersembunyi dari stego text.

        Args:
            stego: Stego text yang dihasilkan oleh embed() dengan alfabet yang sama.

        Returns:
            Pesan rahasia, atau string kosong jika tidak ada data valid.
        """
        all_bits = "".join(
            self._decode[c] for c in stego if c in self._stego_chars
        )

        if len(all_bits) < _HEADER_BITS:
            return ""

        n_bytes = int(all_bits[:_HEADER_BITS], 2)
        start = _HEADER_BITS
        end = start + n_bytes * 8

        if len(all_bits) < end:
            return ""

        payload_bits = all_bits[start:end]
        byte_list = [
            int(payload_bits[i : i + 8], 2) for i in range(0, len(payload_bits), 8)
        ]
        return bytes(byte_list).decode("utf-8", errors="replace")

    def capacity(self, text: str) -> dict:
        """Hitung kapasitas embedding cover text (kapasitas bruto).

        Returns:
            Dict dengan kunci:
                spaces        : jumlah spasi (slot tersedia)
                bits_per_space: bit yang dikodekan per spasi
                bits          : kapasitas bruto dalam bit
                bytes         : kapasitas bruto dalam byte (floor)
                bits_per_char : rasio bit per karakter teks keseluruhan
        """
        n_spaces = text.count(" ")
        total_bits = n_spaces * self.bits_per_space
        n_chars = len(text)

        return {
            "spaces": n_spaces,
            "bits_per_space": self.bits_per_space,
            "bits": total_bits,
            "bytes": total_bits // 8,
            "bits_per_char": round(total_bits / n_chars, 4) if n_chars else 0.0,
        }

    # ── Helper Privat ─────────────────────────────────────────────────────────

    def _build_bitstream(self, secret: str) -> str:
        """Susun bitstream: 16-bit header + payload bits, di-pad ke kelipatan bps."""
        payload_bytes = secret.encode("utf-8")
        n_bytes = len(payload_bytes)
        if n_bytes > 0xFFFF:
            raise ValueError("Pesan terlalu panjang (maksimal 65 535 byte).")

        header = f"{n_bytes:016b}"
        payload = "".join(f"{b:08b}" for b in payload_bytes)
        bits = header + payload

        # Pad ke kelipatan bits_per_space agar setiap slot terisi penuh
        rem = len(bits) % self.bits_per_space
        if rem:
            bits += "0" * (self.bits_per_space - rem)

        return bits


# ── Fungsi Perbandingan ───────────────────────────────────────────────────────

_VARIANTS: list[tuple[str, list[str]]] = [
    ("ALPHABET_4", ALPHABET_4),
    ("ALPHABET_8", ALPHABET_8),
    ("ALPHABET_16", ALPHABET_16),
]


def compare_alphabets(text: str, secret: str) -> pd.DataFrame:
    """Bandingkan kapasitas dan overhead file untuk ketiga varian alfabet.

    Menjalankan embed pada teks dan pesan yang sama menggunakan ALPHABET_4,
    ALPHABET_8, dan ALPHABET_16, lalu mengukur:
    - kapasitas embedding (bit/byte)
    - persentase kenaikan ukuran file UTF-8

    Kenaikan ukuran terjadi karena karakter Unicode stego (umumnya 3 byte dalam
    UTF-8) menggantikan spasi biasa (1 byte), sehingga setiap spasi menambah
    ~2 byte pada ukuran file.

    Args:
        text:   Cover text. Harus memiliki cukup spasi untuk ALPHABET_4
                (varian paling restriktif: 2 bit/spasi).
        secret: Pesan rahasia yang akan disematkan.

    Returns:
        DataFrame berkolom: alphabet_name, alphabet_size, bits_per_space,
        capacity_bits, capacity_bytes, file_size_increase_pct.
        Hasil disimpan ke experiments/results/capacity_comparison.csv.
    """
    cover_bytes = len(text.encode("utf-8"))
    rows = []

    for name, alphabet in _VARIANTS:
        cipher = StegoCipher(alphabet)
        cap = cipher.capacity(text)
        stego = cipher.embed(text, secret)
        stego_bytes = len(stego.encode("utf-8"))
        increase_pct = (stego_bytes - cover_bytes) / cover_bytes * 100

        rows.append({
            "alphabet_name": name,
            "alphabet_size": len(alphabet),
            "bits_per_space": cap["bits_per_space"],
            "capacity_bits": cap["bits"],
            "capacity_bytes": cap["bytes"],
            "file_size_increase_pct": round(increase_pct, 2),
        })

    df = pd.DataFrame(rows)

    _RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(_RESULTS_DIR / "capacity_comparison.csv", index=False)

    return df


if __name__ == "__main__":
    cover = (
        "Steganografi adalah teknik menyembunyikan pesan rahasia di dalam "
        "media lain sehingga keberadaannya tidak terdeteksi oleh pihak ketiga "
        "yang tidak berwenang untuk membaca isi pesan tersebut sama sekali. "
        "Metode ini memanfaatkan karakter Unicode tak kasat mata sebagai "
        "pembawa informasi tersembunyi di dalam teks biasa."
    )
    pesan = "Hi"

    print("=== Perbandingan Varian Alfabet ===\n")
    df = compare_alphabets(cover, pesan)
    print(df.to_string(index=False))
    print("\nHasil disimpan ke experiments/results/capacity_comparison.csv")

    print("\n=== Demo Roundtrip ALPHABET_8 ===")
    cipher = StegoCipher(ALPHABET_8)
    stego = cipher.embed(cover, pesan)
    print(f"Pesan asli  : {pesan!r}")
    print(f"Hasil ekstrak: {cipher.extract(stego)!r}")
