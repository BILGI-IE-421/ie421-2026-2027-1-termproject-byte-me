"""Produce the M2 static figures in visuals/ from the raw Billboard file.

Run from the repository root:  python scripts/figures.py
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "billboard" / "charts.csv"  # created by scripts/download_data.py
OUT = ROOT / "visuals"
OUT.mkdir(exist_ok=True)

# Okabe-Ito colour-blind-safe palette
BLUE, ORANGE, GREY = "#0072B2", "#E69F00", "#999999"
SOURCE = "Source: Billboard Hot 100, weekly charts 1958-2021 (Kaggle, dhruvildave)."


def load_songs():
    charts = pd.read_csv(DATA)
    charts["date"] = pd.to_datetime(charts["date"], format="%Y-%m-%d")
    songs = (charts.groupby(["song", "artist"])
                   .agg(debut=("date", "min"), weeks=("date", "count"))
                   .reset_index())
    songs["debut_year"] = songs["debut"].dt.year
    # 2021 debuts are cut off by the end of the data (Nov 2021): drop them
    return songs[songs["debut_year"] <= 2020]


def fig_trend(songs):
    g = songs.groupby("debut_year")["weeks"]
    med, q1, q3 = g.median(), g.quantile(0.25), g.quantile(0.75)

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.fill_between(med.index, q1, q3, color=BLUE, alpha=0.2,
                    label="middle 50% of songs")
    ax.plot(med.index, med, color=BLUE, lw=2, label="median song")
    peak_year = med.idxmax()
    ax.annotate(f"{peak_year}: median {med[peak_year]:.0f} weeks",
                xy=(peak_year, med[peak_year]), xytext=(1983, 21.8),
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.annotate(f"2020: median {med[2020]:.0f} weeks",
                xy=(2020, med[2020]), xytext=(2003, 3),
                arrowprops=dict(arrowstyle="->", color="black"))
    ax.set_title("Hits lasted longer for four decades, then collapsed in the streaming era",
                 loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("Year the song first entered the Hot 100")
    ax.set_ylabel("Weeks on the Hot 100 (per song)")
    ax.set_ylim(0, 23)
    ax.legend(frameon=False, loc="upper left")
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, SOURCE + " Songs debuting in 2021 excluded (runs not finished).",
             fontsize=8, color="dimgrey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig1_lifespan_trend.png", dpi=150)
    plt.close(fig)


def fig_distribution(songs):
    eras = {"1990-2004": (1990, 2004, ORANGE), "2015-2020": (2015, 2020, BLUE)}
    bins = np.arange(0.5, 61.5, 1)
    fig, ax = plt.subplots(figsize=(9, 5))
    for name, (a, b, col) in eras.items():
        w = songs.loc[songs["debut_year"].between(a, b), "weeks"]
        share = (w <= 2).mean() * 100
        ax.hist(w.clip(upper=60), bins=bins, weights=np.full(len(w), 100 / len(w)),
                histtype="step", lw=2, color=col,
                label=f"{name} (n={len(w):,}; {share:.0f}% gone within 2 weeks)")
    ax.set_title("In the streaming era, a large share of hits vanish within two weeks",
                 loc="left", fontsize=12, fontweight="bold")
    ax.set_xlabel("Total weeks on the Hot 100 (runs over 60 weeks shown at 60)")
    ax.set_ylabel("Share of songs in the era (%)")
    ax.legend(frameon=False)
    ax.spines[["top", "right"]].set_visible(False)
    fig.text(0.01, 0.01, SOURCE, fontsize=8, color="dimgrey")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(OUT / "fig2_lifespan_distribution.png", dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    songs = load_songs()
    fig_trend(songs)
    fig_distribution(songs)
    print(f"{len(songs):,} songs; figures written to {OUT}")
