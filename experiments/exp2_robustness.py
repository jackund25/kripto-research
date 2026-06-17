"""
Eksperimen 2: Analisis Ketahanan terhadap Serangan Normalisasi
==============================================================
Menguji seberapa tahan payload tersembunyi ketika stego text melewati
berbagai transformasi yang umum terjadi dalam pemrosesan teks.

Serangan yang diuji:
    baseline        : tanpa serangan (kontrol)
    normalize       : ganti semua Unicode space -> U+0020
    strip_unicode   : hapus semua karakter non-ASCII
    double_space    : autocorrect double-space -> single-space
    truncate_75     : potong teks hingga 75%
    truncate_50     : potong teks hingga 50%
    truncate_25     : potong teks hingga 25%

Output:
    experiments/results/exp2_results.csv
    experiments/results/exp2_robustness.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extended import StegoCipher, ALPHABET_8, ALPHABET_16

# ── Konfigurasi ───────────────────────────────────────────────────────────────

SAMPLE_DIR  = Path(__file__).parent.parent / "sample_texts"
RESULTS_DIR = Path(__file__).parent / "results"

# Himpunan semua karakter Unicode yang pernah dipakai sebagai stego
# (gabungan ALPHABET_4 + 8 + 16, agar normalize mengenali semuanya)
_ALL_STEGO_CHARS: set[str] = set(ALPHABET_16)

# Cover text dan cipher
COVER_FILE = SAMPLE_DIR / "medium.txt"
CIPHER     = StegoCipher(ALPHABET_8)   # 3 bit/spasi

# Secret 32 byte (persis): butuh 91 slot, tersedia 320 di medium.txt
SECRET = "robustness-test-secret-32bytes!!"
assert len(SECRET.encode()) == 32, "SECRET harus tepat 32 byte"


# ── Fungsi Serangan ───────────────────────────────────────────────────────────

def attack_normalize(stego: str) -> str:
    """Ganti semua karakter Unicode whitespace stego kembali ke U+0020.

    Mensimulasikan normalisasi Unicode yang dilakukan oleh beberapa
    platform pesan dan CMS (Content Management System).
    """
    return "".join(" " if c in _ALL_STEGO_CHARS else c for c in stego)


def attack_strip_unicode(stego: str) -> str:
    """Hapus semua karakter non-ASCII (code point > 127).

    Mensimulasikan konversi teks ke encoding ASCII murni, misalnya
    saat teks dikirim melalui protokol atau sistem yang tidak mendukung Unicode.
    """
    return "".join(c for c in stego if ord(c) < 128)


def attack_double_space(stego: str) -> str:
    """Ganti semua double-space (U+0020 U+0020) dengan single-space.

    Mensimulasikan fitur autocorrect yang umum ditemukan pada word processor
    dan editor teks. Karena embedding TREND mengganti SEMUA U+0020 dengan
    karakter stego, serangan ini seharusnya tidak berdampak (tidak ada
    double ASCII-space yang tersisa setelah proses embedding).
    """
    result = stego
    while "  " in result:          # U+0020 U+0020
        result = result.replace("  ", " ")
    return result


def attack_truncate(stego: str, pct: float) -> str:
    """Potong teks hingga pct% dari panjang karakter aslinya.

    Mensimulasikan transmisi yang terpotong, misalnya teks yang dipotong
    karena batas karakter platform atau kesalahan transmisi jaringan.

    Args:
        stego: Stego text yang akan dipotong.
        pct  : Persentase panjang yang dipertahankan (0 < pct <= 1).
    """
    if not 0.0 < pct <= 1.0:
        raise ValueError("pct harus berada di rentang (0, 1].")
    cut = max(1, int(len(stego) * pct))
    return stego[:cut]


# ── Fungsi Metrik ─────────────────────────────────────────────────────────────

def survival_rate(original_secret: str, recovered_secret: str) -> float:
    """Hitung persentase bit payload yang berhasil di-recover.

    Metodologi:
    - Konversi kedua string ke bit (UTF-8 byte per byte).
    - Jika recovered kosong, kembalikan 0.0 langsung.
    - Bandingkan bit per bit sepanjang string terpendek; bit yang hilang
      (karena recovered lebih pendek) dihitung sebagai TIDAK selamat.
    - survival = jumlah bit cocok / jumlah bit original.

    Returns:
        Float antara 0.0 dan 1.0.
    """
    if not original_secret:
        return 1.0
    if not recovered_secret:
        return 0.0
    if original_secret == recovered_secret:
        return 1.0

    orig_bits = "".join(f"{b:08b}" for b in original_secret.encode("utf-8"))
    rec_bits  = "".join(f"{b:08b}" for b in recovered_secret.encode("utf-8"))

    # Hanya bandingkan sejumlah bit yang ada di original
    compare_len = len(orig_bits)
    # rec_bits dipotong/diperpanjang hingga compare_len
    # (tidak ada zero-padding—bit yang tak ada dianggap hilang = tidak cocok)
    matching = sum(
        orig_bits[i] == rec_bits[i]
        for i in range(min(compare_len, len(rec_bits)))
    )
    # Bit yang "hilang" (karena recovered lebih pendek) tidak dihitung sebagai cocok
    return matching / compare_len


def _count_stego_chars(text: str) -> int:
    """Hitung berapa karakter stego yang masih ada dalam teks."""
    return sum(1 for c in text if c in CIPHER._stego_chars)


# ── Eksperimen ────────────────────────────────────────────────────────────────

# Definisi serangan: (nama, deskripsi, fungsi)
_ATTACKS: list[tuple[str, str, object]] = [
    ("baseline",
     "Tanpa serangan (kontrol)",
     lambda s: s),
    ("normalize",
     "Normalisasi Unicode -> U+0020",
     attack_normalize),
    ("strip_unicode",
     "Hapus karakter non-ASCII",
     attack_strip_unicode),
    ("double_space",
     "Autocorrect double-space",
     attack_double_space),
    ("truncate_75",
     "Pemotongan 75% teks",
     lambda s: attack_truncate(s, 0.75)),
    ("truncate_50",
     "Pemotongan 50% teks",
     lambda s: attack_truncate(s, 0.50)),
    ("truncate_25",
     "Pemotongan 25% teks",
     lambda s: attack_truncate(s, 0.25)),
]


def run_experiment(cover: str, stego: str) -> pd.DataFrame:
    """Jalankan semua serangan dan ukur tingkat ketahanan payload.

    Args:
        cover: Cover text asli (untuk referensi statistik).
        stego: Stego text hasil embed yang akan diserang.

    Returns:
        DataFrame hasil; juga disimpan ke exp2_results.csv.
    """
    original_bytes  = len(cover.encode("utf-8"))
    stego_chars_all = _count_stego_chars(stego)
    rows = []

    for name, description, attack_fn in _ATTACKS:
        attacked      = attack_fn(stego)
        stego_remaining = _count_stego_chars(attacked)

        try:
            recovered = CIPHER.extract(attacked)
        except Exception:
            recovered = ""

        rate = survival_rate(SECRET, recovered)

        rows.append({
            "attack_name":       name,
            "description":       description,
            "stego_chars_total": stego_chars_all,
            "stego_chars_after": stego_remaining,
            "stego_loss_pct":    round(
                (stego_chars_all - stego_remaining) / stego_chars_all * 100, 2
            ),
            "recovered_secret":  recovered if recovered else "(kosong)",
            "exact_match":       recovered == SECRET,
            "survival_rate_pct": round(rate * 100, 2),
        })

    df = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / "exp2_results.csv", index=False)
    return df


# ── Visualisasi ───────────────────────────────────────────────────────────────

def _bar_color(rate_pct: float) -> str:
    """Warna batang berdasarkan survival rate: hijau (100%), kuning (parsial), merah (0%)."""
    if rate_pct >= 99.9:
        return "#2ecc71"   # hijau — bertahan penuh
    elif rate_pct > 0.0:
        return "#f39c12"   # kuning — bertahan sebagian
    else:
        return "#e74c3c"   # merah — tidak ada yang bertahan


def plot_robustness(df: pd.DataFrame) -> None:
    """Horizontal bar chart: survival rate per serangan."""
    fig, ax = plt.subplots(figsize=(11, 6))

    labels = df["attack_name"].tolist()
    rates  = df["survival_rate_pct"].tolist()
    colors = [_bar_color(r) for r in rates]
    y_pos  = range(len(labels))

    bars = ax.barh(y_pos, rates, color=colors, edgecolor="white",
                   linewidth=0.8, height=0.6)

    # Label nilai di ujung batang
    for bar, rate in zip(bars, rates):
        x_label = bar.get_width() + 1.0
        ax.text(x_label, bar.get_y() + bar.get_height() / 2,
                f"{rate:.1f}%", va="center", ha="left", fontsize=10, fontweight="bold")

    ax.set_yticks(list(y_pos))
    ax.set_yticklabels(labels, fontsize=11)
    ax.set_xlabel("Survival Rate (%)", fontsize=12)
    ax.set_title(
        "Ketahanan Payload terhadap Serangan Normalisasi\n"
        f"(ALPHABET_8, Secret 32 byte, Cover: medium.txt)",
        fontsize=13, fontweight="bold"
    )
    ax.set_xlim(0, 115)
    ax.axvline(x=100, color="gray", linestyle="--", linewidth=1, alpha=0.5)
    ax.grid(axis="x", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    # Legenda warna
    from matplotlib.patches import Patch
    legend_elems = [
        Patch(facecolor="#2ecc71", label="Bertahan penuh (100%)"),
        Patch(facecolor="#f39c12", label="Bertahan sebagian"),
        Patch(facecolor="#e74c3c", label="Tidak bertahan (0%)"),
    ]
    ax.legend(handles=legend_elems, loc="lower right", fontsize=9)

    fig.tight_layout()
    out = RESULTS_DIR / "exp2_robustness.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Disimpan: {out}")


# ── Ringkasan Terminal ────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Cetak tabel ringkasan hasil ke terminal."""
    cols = ["attack_name", "stego_chars_after", "stego_loss_pct",
            "exact_match", "survival_rate_pct"]
    disp = df[cols].copy()
    disp["stego_loss_pct"]    = disp["stego_loss_pct"].apply(lambda v: f"{v:.1f}%")
    disp["survival_rate_pct"] = disp["survival_rate_pct"].apply(lambda v: f"{v:.2f}%")
    disp["exact_match"]       = disp["exact_match"].apply(lambda v: "OK" if v else "GAGAL")

    print("\n" + "=" * 75)
    print("EKSPERIMEN 2 - Analisis Ketahanan Steganografi Unicode Whitespace")
    print(f"Cipher : ALPHABET_8 (3 bit/spasi)")
    print(f"Cover  : medium.txt  ({COVER_FILE.stat().st_size} byte)")
    print(f"Secret : {SECRET!r}  ({len(SECRET.encode())} byte)")
    print("=" * 75)
    print(disp.to_string(index=False))
    print("=" * 75)

    full   = int((df["survival_rate_pct"] >= 99.9).sum())
    zero   = int((df["survival_rate_pct"] == 0).sum())
    partial = len(df) - full - zero
    print(f"\nHasil  : {full} bertahan penuh | {partial} sebagian | {zero} gagal total")
    print(f"CSV    : {RESULTS_DIR / 'exp2_results.csv'}")
    print(f"Plot   : {RESULTS_DIR / 'exp2_robustness.png'}")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Eksperimen 2: Analisis Ketahanan")
    print("=" * 50)

    print("\n[1/4] Menyiapkan stego text...")
    cover = COVER_FILE.read_text(encoding="utf-8")
    stego = CIPHER.embed(cover, SECRET)

    cap = CIPHER.capacity(cover)
    print(f"  Cover  : {len(cover.split())} kata, {cap['spaces']} spasi")
    print(f"  Secret : {len(SECRET.encode())} byte")
    print(f"  Kapasitas: {cap['bits']} bit ({cap['bytes']} byte bruto)")
    print(f"  Slot terpakai: {__import__('math').ceil((16 + len(SECRET.encode())*8) / 3)}"
          f" dari {cap['spaces']}")

    print("\n[2/4] Menjalankan serangan...")
    df = run_experiment(cover, stego)

    print("\n[3/4] Membuat visualisasi...")
    plot_robustness(df)

    print("\n[4/4] Ringkasan hasil:")
    print_summary(df)
