"""
Eksperimen 1: Analisis Kapasitas Steganografi Unicode Whitespace
================================================================
Membandingkan kapasitas embedding dan overhead ukuran file untuk tiga
varian alfabet (ALPHABET_4, ALPHABET_8, ALPHABET_16) pada tiga teks uji
dengan panjang berbeda (short, medium, long).

Output:
    experiments/results/exp1_results.csv
    experiments/results/exp1_capacity.png
    experiments/results/exp1_overhead.png
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")  # backend non-interaktif; harus dipanggil sebelum pyplot
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import pandas as pd

# Tambah root project ke sys.path agar src dapat diimpor
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.extended import StegoCipher, ALPHABET_4, ALPHABET_8, ALPHABET_16

# ── Konfigurasi ───────────────────────────────────────────────────────────────

SAMPLE_DIR  = Path(__file__).parent.parent / "sample_texts"
RESULTS_DIR = Path(__file__).parent / "results"

# Pesan uji: 7 byte → butuh minimal 36 slot dengan ALPHABET_4 (2 bit/spasi)
SECRET = "rahasia"

ALPHABETS: dict[str, list[str]] = {
    "ALPHABET_4":  ALPHABET_4,
    "ALPHABET_8":  ALPHABET_8,
    "ALPHABET_16": ALPHABET_16,
}

# Warna konsisten untuk setiap alfabet di semua plot
COLORS: dict[str, str] = {
    "ALPHABET_4":  "#4C72B0",
    "ALPHABET_8":  "#55A868",
    "ALPHABET_16": "#C44E52",
}

# Urutan tampilan teks dari pendek ke panjang
TEXT_ORDER = ["short", "medium", "long"]


# ── Pemuatan Data ─────────────────────────────────────────────────────────────

def load_texts() -> dict[str, str]:
    """Muat semua file .txt dari sample_texts/, diurutkan sesuai TEXT_ORDER."""
    if not SAMPLE_DIR.exists():
        raise FileNotFoundError(f"Folder tidak ditemukan: {SAMPLE_DIR}")

    texts: dict[str, str] = {}
    for name in TEXT_ORDER:
        path = SAMPLE_DIR / f"{name}.txt"
        if path.exists():
            texts[name] = path.read_text(encoding="utf-8")

    # Sertakan juga file lain yang ada di folder (di luar TEXT_ORDER)
    for f in sorted(SAMPLE_DIR.glob("*.txt")):
        if f.stem not in texts:
            texts[f.stem] = f.read_text(encoding="utf-8")

    if not texts:
        raise FileNotFoundError("Tidak ada file .txt di sample_texts/")

    return texts


# ── Eksperimen ────────────────────────────────────────────────────────────────

def run_experiment(texts: dict[str, str]) -> pd.DataFrame:
    """Jalankan eksperimen untuk semua kombinasi (teks × alfabet).

    Untuk setiap kombinasi:
    - Hitung kapasitas bruto (spasi, bit, byte, bit/char)
    - Embed SECRET dan ukur overhead ukuran file UTF-8
    - Verifikasi roundtrip embed → extract

    Returns:
        DataFrame hasil lengkap; juga disimpan ke exp1_results.csv.
    """
    rows = []

    for text_name, text in texts.items():
        original_bytes = len(text.encode("utf-8"))
        word_count     = len(text.split())

        for alpha_name, alphabet in ALPHABETS.items():
            cipher = StegoCipher(alphabet)
            cap    = cipher.capacity(text)

            try:
                stego         = cipher.embed(text, SECRET)
                extracted     = cipher.extract(stego)
                roundtrip_ok  = extracted == SECRET
                stego_bytes   = len(stego.encode("utf-8"))
                overhead_pct  = round(
                    (stego_bytes - original_bytes) / original_bytes * 100, 4
                )
            except ValueError:
                # Cover text tidak cukup kapasitas untuk SECRET + header
                roundtrip_ok = False
                stego_bytes  = None
                overhead_pct = None

            rows.append({
                "text_name":      text_name,
                "word_count":     word_count,
                "char_count":     len(text),
                "original_bytes": original_bytes,
                "alphabet_name":  alpha_name,
                "alphabet_size":  len(alphabet),
                "bits_per_space": cap["bits_per_space"],
                "spaces":         cap["spaces"],
                "capacity_bits":  cap["bits"],
                "capacity_bytes": cap["bytes"],
                "bits_per_char":  cap["bits_per_char"],
                "stego_bytes":    stego_bytes,
                "overhead_pct":   overhead_pct,
                "roundtrip_ok":   roundtrip_ok,
            })

    df = pd.DataFrame(rows)
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    df.to_csv(RESULTS_DIR / "exp1_results.csv", index=False)
    return df


# ── Visualisasi ───────────────────────────────────────────────────────────────

def _text_order_key(name: str) -> int:
    """Kembalikan indeks urutan teks agar grafik tampil short → medium → long."""
    try:
        return TEXT_ORDER.index(name)
    except ValueError:
        return len(TEXT_ORDER)


def plot_capacity(df: pd.DataFrame) -> None:
    """Bar chart: kapasitas embedding (bits) per teks per alfabet."""
    pivot = df.pivot(index="text_name", columns="alphabet_name", values="capacity_bits")

    # Urutkan baris: short → medium → long
    ordered_index = sorted(pivot.index, key=_text_order_key)
    pivot = pivot.reindex(ordered_index)
    alpha_cols = list(ALPHABETS.keys())  # urutan alfabet konsisten

    fig, ax = plt.subplots(figsize=(10, 6))
    n      = len(pivot)
    n_col  = len(alpha_cols)
    width  = 0.25
    x      = range(n)

    for i, col in enumerate(alpha_cols):
        offsets = [xi + (i - n_col / 2 + 0.5) * width for xi in x]
        ax.bar(offsets, pivot[col], width=width,
               label=col, color=COLORS[col], edgecolor="white", linewidth=0.5)

    ax.set_xticks(list(x))
    ax.set_xticklabels(ordered_index, fontsize=12)
    ax.set_xlabel("Teks Uji", fontsize=12)
    ax.set_ylabel("Kapasitas (bit)", fontsize=12)
    ax.set_title("Kapasitas Embedding per Teks dan Varian Alfabet", fontsize=14, fontweight="bold")
    ax.legend(title="Alfabet", fontsize=10)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{int(v):,}"))
    ax.grid(axis="y", alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    fig.tight_layout()
    out = RESULTS_DIR / "exp1_capacity.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Disimpan: {out}")


def plot_overhead(df: pd.DataFrame) -> None:
    """Line chart: overhead ukuran file (%) vs panjang teks (jumlah kata)."""
    valid = df[df["overhead_pct"].notna()].copy()

    # Urutkan setiap grup berdasarkan word_count
    fig, ax = plt.subplots(figsize=(10, 6))

    for alpha_name in ALPHABETS:
        group = valid[valid["alphabet_name"] == alpha_name].sort_values("word_count")
        ax.plot(
            group["word_count"],
            group["overhead_pct"],
            marker="o",
            label=alpha_name,
            color=COLORS[alpha_name],
            linewidth=2,
            markersize=8,
        )
        # Label titik data
        for _, row in group.iterrows():
            ax.annotate(
                f"{row['overhead_pct']:.2f}%",
                (row["word_count"], row["overhead_pct"]),
                textcoords="offset points",
                xytext=(0, 8),
                ha="center",
                fontsize=8,
                color=COLORS[alpha_name],
            )

    ax.set_xlabel("Jumlah Kata dalam Teks", fontsize=12)
    ax.set_ylabel("Overhead Ukuran File (%)", fontsize=12)
    ax.set_title("Overhead Ukuran File vs Panjang Teks", fontsize=14, fontweight="bold")
    ax.legend(title="Alfabet", fontsize=10)
    ax.grid(alpha=0.3, linestyle="--")
    ax.set_axisbelow(True)

    fig.tight_layout()
    out = RESULTS_DIR / "exp1_overhead.png"
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"  Disimpan: {out}")


# ── Ringkasan Terminal ────────────────────────────────────────────────────────

def print_summary(df: pd.DataFrame) -> None:
    """Cetak tabel ringkasan hasil eksperimen ke terminal."""
    # Kolom yang ditampilkan
    summary = df[[
        "text_name", "word_count", "spaces",
        "alphabet_name", "bits_per_space",
        "capacity_bits", "capacity_bytes",
        "overhead_pct", "roundtrip_ok",
    ]].copy()

    summary["capacity_bits"]  = summary["capacity_bits"].apply(lambda v: f"{v:,}")
    summary["capacity_bytes"] = summary["capacity_bytes"].apply(lambda v: f"{v:,}")
    summary["overhead_pct"]   = summary["overhead_pct"].apply(
        lambda v: f"{v:.4f}%" if pd.notna(v) else "N/A"
    )
    summary["roundtrip_ok"] = summary["roundtrip_ok"].apply(
        lambda v: "OK" if v else "GAGAL"
    )

    # Urutkan: short → medium → long, lalu per alfabet
    summary["_order"] = summary["text_name"].apply(_text_order_key)
    summary = summary.sort_values(["_order", "alphabet_name"]).drop(columns="_order")

    print("\n" + "=" * 95)
    print("EKSPERIMEN 1 - Analisis Kapasitas Steganografi Unicode Whitespace")
    print(f"Secret uji : {SECRET!r}  ({len(SECRET.encode())} byte)")
    print("=" * 95)
    print(summary.to_string(index=False))
    print("=" * 95)

    total  = len(df)
    passed = int(df["roundtrip_ok"].sum())
    print(f"\nRoundtrip  : {passed}/{total} kombinasi OK")
    print(f"CSV        : {RESULTS_DIR / 'exp1_results.csv'}")
    print(f"Plot       : {RESULTS_DIR / 'exp1_capacity.png'}")
    print(f"           : {RESULTS_DIR / 'exp1_overhead.png'}")


# ── Entry Point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 50)
    print("Eksperimen 1: Analisis Kapasitas")
    print("=" * 50)

    print("\n[1/4] Memuat teks uji...")
    texts = load_texts()
    for name, text in texts.items():
        print(f"  {name:8s}: {len(text.split()):4d} kata, {text.count(' '):4d} spasi")

    print("\n[2/4] Menjalankan eksperimen...")
    df = run_experiment(texts)
    print(f"  {len(df)} kombinasi selesai -> exp1_results.csv")

    print("\n[3/4] Membuat visualisasi...")
    plot_capacity(df)
    plot_overhead(df)

    print("\n[4/4] Ringkasan hasil:")
    print_summary(df)
