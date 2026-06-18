"""
Eksperimen bonus:
  3a - Uji embedding/ekstraksi pada teks cover berbahasa Indonesia
  3b - Analisis granular threshold truncation (25%-40%, step 1%)
"""

import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from src.extended import StegoCipher, ALPHABET_4, ALPHABET_8, ALPHABET_16

RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(exist_ok=True)

_ALL_ALPHABETS = [
    ("ALPHABET_4",  ALPHABET_4),
    ("ALPHABET_8",  ALPHABET_8),
    ("ALPHABET_16", ALPHABET_16),
]

# =============================================================================
# 3a — Teks Indonesia
# =============================================================================

def exp3a():
    print("=" * 60)
    print("EXP 3a: Uji Teks Cover Bahasa Indonesia")
    print("=" * 60)

    indo_path = Path(__file__).parent.parent / "sample_texts" / "indonesian.txt"
    en_medium = Path(__file__).parent.parent / "sample_texts" / "medium.txt"

    indo_text = indo_path.read_text(encoding="utf-8")
    en_text   = en_medium.read_text(encoding="utf-8")

    # hitung statistik dasar teks
    def text_stats(text, label):
        words  = len(text.split())
        spaces = text.count(" ")
        size   = len(text.encode("utf-8"))
        print(f"\n  [{label}]")
        print(f"    Kata  : {words}")
        print(f"    Spasi : {spaces}")
        print(f"    Ukuran: {size} byte (UTF-8)")
        return spaces

    sp_indo = text_stats(indo_text,  "Indonesia (indonesian.txt)")
    sp_en   = text_stats(en_text,    "Inggris   (medium.txt)   ")

    print(f"\n  Perbandingan kepadatan spasi:")
    print(f"    Indonesia : {sp_indo / len(indo_text.split()) * 100:.1f} spasi per kata (rasio thd kata)")
    print(f"    Inggris   : {sp_en   / len(en_text.split())   * 100:.1f} spasi per kata (rasio thd kata)")

    # uji roundtrip semua alfabet untuk tiga secret
    secrets = [
        "rahasia",                                # 7 byte, ASCII
        "pesan dalam bahasa indonesia",           # 29 byte, ASCII
        "kriptografi: αβγ",       # 3 huruf Yunani, multi-byte UTF-8
    ]

    print("\n  Roundtrip test (indonesian.txt):")
    print("  " + "-" * 56)
    print(f"  {'Secret':<35} {'Alfabet':<12} {'Hasil'}")
    print("  " + "-" * 56)

    rows = []
    for secret in secrets:
        s_bytes = len(secret.encode("utf-8"))
        for name, alphabet in _ALL_ALPHABETS:
            cipher = StegoCipher(alphabet)
            cap    = cipher.capacity(indo_text)
            needed = math.ceil((16 + s_bytes * 8) / cipher.bits_per_space)

            if needed > cap["spaces"]:
                result = "KAPASITAS KURANG"
                ok = False
            else:
                stego     = cipher.embed(indo_text, secret)
                recovered = cipher.extract(stego)
                ok        = recovered == secret
                result    = "OK" if ok else "GAGAL"

            label = ascii(secret)
            if len(label) > 33:
                label = label[:30] + "...'"
            print(f"  {label:<35} {name:<12} {result}")
            rows.append({
                "Secret": ascii(secret),
                "Alfabet": name,
                "Secret (byte)": s_bytes,
                "Slot Butuh": needed,
                "Slot Tersedia": cap["spaces"],
                "Hasil": result,
            })

    print("  " + "-" * 56)

    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / "exp3a_results.csv", index=False)
    print(f"\n  Disimpan ke: experiments/results/exp3a_results.csv")

    # tabel kapasitas perbandingan Indonesia vs Inggris
    print("\n  Kapasitas embedding (bit) - Indonesia vs Inggris:")
    print("  " + "-" * 50)
    print(f"  {'Alfabet':<14} {'Indonesia':>12} {'Inggris':>12} {'Selisih':>10}")
    print("  " + "-" * 50)
    for name, alphabet in _ALL_ALPHABETS:
        cipher = StegoCipher(alphabet)
        ci = cipher.capacity(indo_text)["bits"]
        ce = cipher.capacity(en_text)["bits"]
        print(f"  {name:<14} {ci:>12,} {ce:>12,} {ci - ce:>+10,}")
    print("  " + "-" * 50)


# =============================================================================
# 3b — Granular truncation threshold
# =============================================================================

def exp3b():
    print()
    print("=" * 60)
    print("EXP 3b: Analisis Granular Threshold Truncation")
    print("=" * 60)

    medium_path = Path(__file__).parent.parent / "sample_texts" / "medium.txt"
    cover  = medium_path.read_text(encoding="utf-8")
    secret = "robustness-test-secret-32bytes!!"  # 32 byte, identik dengan exp2

    cipher = StegoCipher(ALPHABET_8)
    stego  = cipher.embed(cover, secret)

    stego_char_set   = set(ALPHABET_8)
    total_slots      = sum(1 for c in stego if c in stego_char_set)
    s_bytes          = len(secret.encode("utf-8"))
    slots_needed     = math.ceil((16 + s_bytes * 8) / cipher.bits_per_space)
    threshold_theory = slots_needed / total_slots * 100  # % karakter stego minimum

    print(f"\n  Setup:")
    print(f"    Cover      : medium.txt ({len(cover.split())} kata, {total_slots} spasi)")
    print(f"    Secret     : {secret!r} ({s_bytes} byte)")
    print(f"    Alfabet    : ALPHABET_8 ({cipher.bits_per_space} bit/spasi)")
    print(f"    Slot butuh : {slots_needed} dari {total_slots}")
    print(f"    Threshold  : {slots_needed}/{total_slots} = {threshold_theory:.2f}% slot")

    # threshold dalam % karakter stego, tapi truncation dilakukan per karakter total
    # sehingga threshold sebenarnya dalam % panjang stego teks (karakter)
    print()
    print(f"  Catatan: truncation memotong per karakter teks, bukan per slot spasi.")
    print(f"  Distribusi spasi dalam teks tidak seragam, sehingga threshold dalam")
    print(f"  % panjang teks bisa sedikit berbeda dari {threshold_theory:.2f}%.")
    print()

    rows = []
    prev_result = None
    boundary_pct = None

    print("  " + "-" * 62)
    print(f"  {'Pct':>5}  {'Karakter':>9}  {'Slot Ada':>9}  {'Slot Butuh':>10}  {'Hasil'}")
    print("  " + "-" * 62)

    for pct_int in range(25, 41):
        pct       = pct_int / 100
        truncated = stego[: int(len(stego) * pct)]
        slots_now = sum(1 for c in truncated if c in stego_char_set)

        recovered = cipher.extract(truncated)
        ok        = recovered == secret
        result    = "OK" if ok else "GAGAL"

        # tandai batas transisi
        marker = ""
        if prev_result is not None and ok != prev_result:
            boundary_pct = pct_int
            marker = " <-- BATAS"

        print(f"  {pct_int:>4}%  {int(len(stego)*pct):>9,}  {slots_now:>9}  {slots_needed:>10}  {result}{marker}")
        rows.append({
            "pct": pct_int,
            "chars_tersisa": int(len(stego) * pct),
            "slot_tersedia": slots_now,
            "slot_dibutuhkan": slots_needed,
            "hasil": result,
        })
        prev_result = ok

    print("  " + "-" * 62)

    if boundary_pct is not None:
        print(f"\n  -> Sistem berhasil mulai pct = {boundary_pct}% (slot >= {slots_needed})")
        print(f"  -> Threshold teoritis: {threshold_theory:.2f}% slot stego")
        print(f"  -> Threshold empiris : {boundary_pct}% panjang teks (karakter)")
    else:
        print("\n  -> Tidak ditemukan transisi dalam rentang 25%-40%.")

    # simpan CSV
    df = pd.DataFrame(rows)
    df.to_csv(RESULTS_DIR / "exp3b_results.csv", index=False)

    # visualisasi
    fig, ax = plt.subplots(figsize=(10, 4))
    colors = ["#2ecc71" if r == "OK" else "#e74c3c" for r in df["hasil"]]
    ax.bar(df["pct"], df["slot_tersedia"], color=colors, edgecolor="white", width=0.7)
    ax.axhline(slots_needed, color="black", linewidth=1.5, linestyle="--",
               label=f"Slot dibutuhkan ({slots_needed})")
    ax.set_xlabel("Truncation (%)")
    ax.set_ylabel("Slot stego tersisa")
    ax.set_title("Analisis Granular Threshold Truncation (ALPHABET_8, medium.txt, 32-byte secret)")
    ax.legend()
    ax.set_xticks(df["pct"])

    # label OK / GAGAL di atas bar
    for _, row in df.iterrows():
        label = "OK" if row["hasil"] == "OK" else "X"
        ax.text(row["pct"], row["slot_tersedia"] + 2, label,
                ha="center", va="bottom", fontsize=8)

    plt.tight_layout()
    plt.savefig(RESULTS_DIR / "exp3b_truncation.png", dpi=150)
    plt.close()

    print(f"\n  Disimpan ke: experiments/results/exp3b_results.csv")
    print(f"               experiments/results/exp3b_truncation.png")


# =============================================================================
# Main
# =============================================================================

if __name__ == "__main__":
    exp3a()
    exp3b()
    print()
    print("=" * 60)
    print("Selesai.")
    print("=" * 60)
