"""
Command-line interface untuk demo steganografi Unicode whitespace.

Penggunaan:
    python -m src.cli embed   --input cover.txt --secret "pesan" [--alphabet 8] [--output stego.txt]
    python -m src.cli extract --input stego.txt [--alphabet 8]
    python -m src.cli capacity --input cover.txt [--alphabet 8] [--all-alphabets]
    python -m src.cli compare  --input cover.txt --secret "pesan"
"""

import argparse
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import pandas as pd

from src.extended import StegoCipher, ALPHABET_4, ALPHABET_8, ALPHABET_16
from src.utils import file_size_bytes, print_summary_table

# ── Konstanta ─────────────────────────────────────────────────────────────────

_ALPHABET_MAP: dict[int, list[str]] = {
    4:  ALPHABET_4,
    8:  ALPHABET_8,
    16: ALPHABET_16,
}

_ALL_VARIANTS: list[tuple[str, int, list[str]]] = [
    ("ALPHABET_4",  4,  ALPHABET_4),
    ("ALPHABET_8",  8,  ALPHABET_8),
    ("ALPHABET_16", 16, ALPHABET_16),
]

_HEADER_BITS = 16  # panjang header length-prefix


# ── Helper ────────────────────────────────────────────────────────────────────

def _get_alphabet(size: int) -> list[str]:
    """Kembalikan alfabet berdasarkan ukurannya; keluar dengan pesan error jika tidak valid."""
    if size not in _ALPHABET_MAP:
        print(f"Error: ukuran alfabet harus 4, 8, atau 16 (diberikan: {size}).")
        sys.exit(1)
    return _ALPHABET_MAP[size]


def _read_file(path: str) -> str:
    """Baca file teks UTF-8; keluar dengan pesan error jika file tidak ditemukan."""
    p = Path(path)
    if not p.exists():
        print(f"Error: file tidak ditemukan: {path}")
        sys.exit(1)
    return p.read_text(encoding="utf-8")


def _slots_needed(secret: str, bits_per_space: int) -> int:
    """Hitung jumlah slot spasi yang dibutuhkan untuk menyimpan secret + header."""
    total_bits = _HEADER_BITS + len(secret.encode("utf-8")) * 8
    return math.ceil(total_bits / bits_per_space)


# ── Subcommand: embed ─────────────────────────────────────────────────────────

def cmd_embed(args: argparse.Namespace) -> None:
    """Sembunyikan pesan rahasia ke dalam cover text dan simpan ke file output.

    Mencetak statistik embedding: kapasitas terpakai, ukuran file, dan overhead.
    """
    cover    = _read_file(args.input)
    alphabet = _get_alphabet(args.alphabet)
    cipher   = StegoCipher(alphabet)
    cap      = cipher.capacity(cover)

    s_bytes = len(args.secret.encode("utf-8"))
    needed  = _slots_needed(args.secret, cipher.bits_per_space)

    try:
        stego = cipher.embed(cover, args.secret)
    except ValueError as exc:
        print(f"Error: {exc}")
        sys.exit(1)

    out_path = Path(args.output)
    out_path.write_text(stego, encoding="utf-8")

    cover_size = file_size_bytes(cover)
    stego_size = file_size_bytes(stego)
    overhead   = (stego_size - cover_size) / cover_size * 100

    print(f"\n[embed] Berhasil menyembunyikan pesan.")
    print(f"  Input      : {args.input} ({cover_size} byte, {cap['spaces']} spasi)")
    print(f"  Secret     : {args.secret!r} ({s_bytes} byte, {s_bytes*8} bit payload)")
    print(f"  Alfabet    : ALPHABET_{args.alphabet} ({cipher.bits_per_space} bit/spasi)")
    print(f"  Output     : {args.output} ({stego_size} byte)")
    print(f"  Slot terpakai : {needed}/{cap['spaces']} "
          f"({needed/cap['spaces']*100:.1f}% kapasitas)")
    print(f"  Overhead   : +{overhead:.2f}% ukuran file")


# ── Subcommand: extract ───────────────────────────────────────────────────────

def cmd_extract(args: argparse.Namespace) -> None:
    """Ekstrak dan tampilkan pesan tersembunyi dari stego file."""
    stego    = _read_file(args.input)
    alphabet = _get_alphabet(args.alphabet)
    cipher   = StegoCipher(alphabet)

    result = cipher.extract(stego)

    if result:
        print(f"\n[extract] Pesan ditemukan:")
        print(f"  {result!r}")
        print(f"  ({len(result.encode())} byte)")
    else:
        print(f"\n[extract] Tidak ada pesan yang dapat diekstrak.")
        print(f"  Pastikan file di-embed menggunakan ALPHABET_{args.alphabet}.")


# ── Subcommand: capacity ──────────────────────────────────────────────────────

def cmd_capacity(args: argparse.Namespace) -> None:
    """Tampilkan tabel kapasitas embedding untuk satu atau semua varian alfabet."""
    cover      = _read_file(args.input)
    cover_size = file_size_bytes(cover)

    if args.all_alphabets:
        variants = _ALL_VARIANTS
    else:
        size     = args.alphabet
        alphabet = _get_alphabet(size)
        variants = [(f"ALPHABET_{size}", size, alphabet)]

    print(f"\n[capacity] {args.input}  ({cover_size} byte)")

    rows = []
    for name, size, alphabet in variants:
        cipher = StegoCipher(alphabet)
        cap    = cipher.capacity(cover)
        rows.append({
            "Alfabet":          name,
            "Bit/Spasi":        cap["bits_per_space"],
            "Spasi":            cap["spaces"],
            "Kapasitas (bit)":  f"{cap['bits']:,}",
            "Kapasitas (byte)": f"{cap['bytes']:,}",
            "Efektif (byte)":   f"{max(0, cap['bytes'] - 2):,}",
            "Bit/Char":         cap["bits_per_char"],
        })

    print()
    print_summary_table(pd.DataFrame(rows))
    print("  * Efektif = kapasitas bruto - 2 byte overhead header length-prefix")


# ── Subcommand: compare ───────────────────────────────────────────────────────

def cmd_compare(args: argparse.Namespace) -> None:
    """Jalankan embed+extract untuk semua varian alfabet dan tampilkan tabel perbandingan."""
    cover      = _read_file(args.input)
    cover_size = file_size_bytes(cover)
    s_bytes    = len(args.secret.encode("utf-8"))

    print(f"\n[compare] {args.input}  ({cover_size} byte)")
    print(f"  Secret : {args.secret!r}  ({s_bytes} byte)")

    rows = []
    for name, size, alphabet in _ALL_VARIANTS:
        cipher  = StegoCipher(alphabet)
        cap     = cipher.capacity(cover)
        needed  = _slots_needed(args.secret, cipher.bits_per_space)

        try:
            stego     = cipher.embed(cover, args.secret)
            recovered = cipher.extract(stego)
            ok        = recovered == args.secret
            overhead  = round(
                (file_size_bytes(stego) - cover_size) / cover_size * 100, 2
            )
        except ValueError:
            ok       = False
            overhead = None

        rows.append({
            "Alfabet":        name,
            "Bit/Spasi":     cipher.bits_per_space,
            "Kapasitas(B)":  cap["bytes"],
            "Slot Terpakai": f"{needed}/{cap['spaces']}",
            "Overhead(%)":   f"{overhead:.2f}%" if overhead is not None else "N/A",
            "Roundtrip":     "OK" if ok else "GAGAL",
        })

    print()
    print_summary_table(pd.DataFrame(rows))


# ── Parser ────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    """Bangun dan kembalikan argparse parser untuk CLI steganografi."""
    parser = argparse.ArgumentParser(
        prog="python -m src.cli",
        description="CLI demo steganografi Unicode whitespace (TREND + ekstensi alfabet)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Contoh:\n"
            "  python -m src.cli embed   --input cover.txt --secret \"hello\" --alphabet 8 --output stego.txt\n"
            "  python -m src.cli extract --input stego.txt --alphabet 8\n"
            "  python -m src.cli capacity --input cover.txt --all-alphabets\n"
            "  python -m src.cli compare  --input cover.txt --secret \"test\"\n"
        ),
    )
    sub = parser.add_subparsers(dest="command", metavar="command")
    sub.required = True

    # ── embed ─────────────────────────────────────────────────────────────────
    p_embed = sub.add_parser("embed", help="sembunyikan pesan ke dalam cover file")
    p_embed.add_argument("--input",    required=True,  metavar="FILE",
                         help="path cover text (file sumber)")
    p_embed.add_argument("--secret",   required=True,  metavar="TEXT",
                         help="pesan rahasia yang akan disembunyikan")
    p_embed.add_argument("--alphabet", type=int, default=4, choices=[4, 8, 16],
                         metavar="{4,8,16}",
                         help="ukuran alfabet Unicode (default: 4)")
    p_embed.add_argument("--output",   default="stego.txt", metavar="FILE",
                         help="path file output stego (default: stego.txt)")

    # ── extract ───────────────────────────────────────────────────────────────
    p_ext = sub.add_parser("extract", help="ekstrak pesan dari stego file")
    p_ext.add_argument("--input",    required=True, metavar="FILE",
                       help="path stego file")
    p_ext.add_argument("--alphabet", type=int, default=4, choices=[4, 8, 16],
                       metavar="{4,8,16}",
                       help="ukuran alfabet yang digunakan saat embed (default: 4)")

    # ── capacity ──────────────────────────────────────────────────────────────
    p_cap = sub.add_parser("capacity", help="tampilkan kapasitas embedding cover text")
    p_cap.add_argument("--input",         required=True, metavar="FILE",
                       help="path cover text")
    p_cap.add_argument("--alphabet",      type=int, default=4, choices=[4, 8, 16],
                       metavar="{4,8,16}",
                       help="ukuran alfabet (default: 4, diabaikan jika --all-alphabets)")
    p_cap.add_argument("--all-alphabets", action="store_true",
                       help="tampilkan kapasitas untuk semua varian alfabet (4, 8, 16)")

    # ── compare ───────────────────────────────────────────────────────────────
    p_cmp = sub.add_parser("compare",
                            help="bandingkan semua varian alfabet untuk secret tertentu")
    p_cmp.add_argument("--input",  required=True, metavar="FILE",
                       help="path cover text")
    p_cmp.add_argument("--secret", required=True, metavar="TEXT",
                       help="pesan rahasia yang akan diuji")

    return parser


# ── Entry Point ───────────────────────────────────────────────────────────────

_COMMANDS = {
    "embed":    cmd_embed,
    "extract":  cmd_extract,
    "capacity": cmd_capacity,
    "compare":  cmd_compare,
}


def main() -> None:
    """Titik masuk utama CLI steganografi."""
    parser = build_parser()
    args   = parser.parse_args()
    _COMMANDS[args.command](args)


if __name__ == "__main__":
    main()
