# Implementasi baseline TREND (arXiv 2502.12710)
# Alfabet 4 karakter Unicode whitespace, masing-masing mewakili 2 bit.
#
# Protokol embedding:
#   [header 16 bit: panjang payload dalam byte] + [payload bits]
# Header memungkinkan extractor berhenti tepat tanpa membaca padding nol.

# Pemetaan 2-bit → karakter Unicode pengganti spasi
_ALPHABET = {
    "00": " ",  # THREE-PER-EM SPACE
    "01": " ",  # FOUR-PER-EM SPACE
    "10": " ",  # PUNCTUATION SPACE
    "11": " ",  # NARROW NO-BREAK SPACE
}

# Pemetaan balik: karakter → 2-bit string
_REVERSE = {v: k for k, v in _ALPHABET.items()}

# Himpunan karakter stego untuk pengecekan cepat
_STEGO_CHARS = set(_ALPHABET.values())

# Panjang header (bit): menyimpan ukuran payload dalam byte (maks 65535 byte)
_HEADER_BITS = 16


def embed_baseline(text: str, secret: str) -> str:
    """Sembunyikan pesan rahasia ke dalam cover text.

    Format bitstream yang disematkan:
        [16 bit header = panjang payload] + [payload bits UTF-8]

    Setiap pasangan bit dipetakan ke satu karakter Unicode stego
    yang menggantikan spasi biasa (U+0020).

    Args:
        text:   Cover text berisi spasi biasa sebagai slot embedding.
        secret: Pesan rahasia yang akan disembunyikan (plain text).

    Returns:
        Stego text dengan spasi yang sudah disubstitusi.

    Raises:
        ValueError: Jika kapasitas cover text tidak cukup.
    """
    payload_bytes = secret.encode("utf-8")
    n_bytes = len(payload_bytes)
    if n_bytes > 0xFFFF:
        raise ValueError("Pesan terlalu panjang (maksimal 65535 byte).")

    # Susun bitstream: header + data
    header_bits = f"{n_bytes:016b}"
    data_bits = "".join(f"{b:08b}" for b in payload_bytes)
    bits = header_bits + data_bits

    # Pad agar panjang kelipatan 2
    if len(bits) % 2:
        bits += "0"

    # Validasi kapasitas
    n_spaces = text.count(" ")
    kapasitas_bit = n_spaces * 2
    if len(bits) > kapasitas_bit:
        raise ValueError(
            f"Cover text tidak cukup: butuh {len(bits)} bit (termasuk "
            f"{_HEADER_BITS} bit header), tersedia {kapasitas_bit} bit "
            f"({n_spaces} spasi)."
        )

    hasil = []
    bit_idx = 0
    for char in text:
        if char == " ":
            pasangan = bits[bit_idx : bit_idx + 2] if bit_idx < len(bits) else "00"
            hasil.append(_ALPHABET[pasangan])
            bit_idx += 2
        else:
            hasil.append(char)

    return "".join(hasil)


def extract_baseline(stego_text: str) -> str:
    """Ekstrak pesan tersembunyi dari stego text.

    Membaca header 16 bit untuk mengetahui panjang payload,
    lalu mengkonversi tepat sejumlah bit tersebut ke string UTF-8.

    Args:
        stego_text: Teks yang mengandung karakter Unicode whitespace stego.

    Returns:
        Pesan rahasia yang berhasil diekstrak, atau string kosong jika
        tidak ada data valid.
    """
    all_bits = "".join(_REVERSE[c] for c in stego_text if c in _STEGO_CHARS)

    if len(all_bits) < _HEADER_BITS:
        return ""

    # Baca header: panjang payload dalam byte
    n_bytes = int(all_bits[:_HEADER_BITS], 2)
    payload_start = _HEADER_BITS
    payload_end = payload_start + n_bytes * 8

    if len(all_bits) < payload_end:
        return ""

    payload_bits = all_bits[payload_start:payload_end]
    byte_list = [int(payload_bits[i : i + 8], 2) for i in range(0, len(payload_bits), 8)]
    return bytes(byte_list).decode("utf-8", errors="replace")


def capacity_baseline(text: str) -> dict:
    """Hitung kapasitas embedding cover text.

    Kapasitas yang dilaporkan adalah kapasitas bruto (tanpa dikurangi overhead
    header 16 bit). Kapasitas efektif untuk payload = bytes - 2.

    Args:
        text: Cover text yang akan dianalisis.

    Returns:
        Dict berisi:
            spaces        : jumlah spasi yang bisa digunakan sebagai slot
            bits          : total kapasitas dalam bit (bruto)
            bytes         : total kapasitas dalam byte (dibulatkan ke bawah)
            bits_per_char : rasio bit per karakter teks keseluruhan
    """
    n_spaces = text.count(" ")
    total_bits = n_spaces * 2
    total_bytes = total_bits // 8
    n_chars = len(text)
    bits_per_char = total_bits / n_chars if n_chars > 0 else 0.0

    return {
        "spaces": n_spaces,
        "bits": total_bits,
        "bytes": total_bytes,
        "bits_per_char": round(bits_per_char, 4),
    }


if __name__ == "__main__":
    cover = (
        "Steganografi adalah teknik menyembunyikan pesan rahasia di dalam "
        "media lain sehingga keberadaannya tidak terdeteksi oleh pihak ketiga "
        "yang tidak berwenang untuk membaca isi pesan tersebut."
    )
    pesan = "Hi"

    print("=== TREND Baseline Demo ===")
    print(f"Cover text   : {cover}")
    print(f"Pesan        : {pesan!r}")

    cap = capacity_baseline(cover)
    print(f"\nKapasitas    : {cap}")
    print(f"  → efektif  : {cap['bytes'] - 2} byte (setelah overhead header 2 byte)")

    stego = embed_baseline(cover, pesan)
    print(f"\nStego text   : {stego}")

    hasil = extract_baseline(stego)
    print(f"Hasil ekstrak: {hasil!r}")
    print(f"Berhasil     : {hasil == pesan}")
