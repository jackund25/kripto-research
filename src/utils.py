"""Fungsi-fungsi pembantu untuk modul steganografi Unicode whitespace."""

import pandas as pd


def text_to_bits(text: str) -> str:
    """Konversi string teks ke representasi binary string (UTF-8).

    Setiap byte dari encoding UTF-8 dikonversi menjadi 8 karakter '0'/'1'.
    Contoh: 'A' (0x41) -> '01000001'.

    Args:
        text: String teks yang akan dikonversi.

    Returns:
        Binary string dengan panjang kelipatan 8.
    """
    return "".join(f"{b:08b}" for b in text.encode("utf-8"))


def bits_to_text(bits: str) -> str:
    """Konversi binary string ke string teks (UTF-8).

    Bit sisa yang tidak membentuk byte penuh (kelipatan 8) diabaikan.
    Byte yang tidak valid dalam UTF-8 diganti dengan karakter pengganti.

    Args:
        bits: Binary string yang hanya berisi karakter '0' dan '1'.

    Returns:
        String teks hasil dekoding UTF-8.
    """
    bits = bits[: (len(bits) // 8) * 8]
    byte_list = [int(bits[i : i + 8], 2) for i in range(0, len(bits), 8)]
    return bytes(byte_list).decode("utf-8", errors="replace")


def file_size_bytes(text: str) -> int:
    """Hitung ukuran string dalam byte jika disimpan sebagai file UTF-8.

    Args:
        text: String teks yang akan diukur.

    Returns:
        Jumlah byte yang dibutuhkan untuk menyimpan text dalam encoding UTF-8.
    """
    return len(text.encode("utf-8"))


def print_summary_table(df: pd.DataFrame) -> None:
    """Cetak DataFrame sebagai tabel ringkasan ke terminal (ASCII-safe).

    Lebar garis pembatas menyesuaikan lebar konten tabel secara otomatis.
    Aman digunakan di terminal Windows dengan encoding cp1252.

    Args:
        df: DataFrame yang akan ditampilkan. Jika kosong, cetak pesan khusus.
    """
    if df.empty:
        print("(Tidak ada data untuk ditampilkan)")
        return

    table_str = df.to_string(index=False)
    width = max(len(line) for line in table_str.splitlines())
    sep = "-" * width

    print(sep)
    print(table_str)
    print(sep)
