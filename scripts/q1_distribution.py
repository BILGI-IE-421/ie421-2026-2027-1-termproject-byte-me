"""Q1 - Distribution of Billboard hit-song lifespan by debut decade.

Run from the repository root:
    python scripts/q1_distribution.py

Input:
    data/processed/billboard_songs.csv

Outputs:
    visuals/q1_lifespan_distribution.png
    data/processed/q1_distribution_summary.csv
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/billboard_songs.csv"
OUTPUT_DIR = ROOT / "visuals"
SUMMARY_DIR = ROOT / "data/processed"


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run scripts/preprocess.py first."
        )

    df = pd.read_csv(INPUT, parse_dates=["debut_date", "last_date"])
    required = {"debut_date", "total_weeks"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    df["total_weeks"] = pd.to_numeric(df["total_weeks"], errors="coerce")
    df = df.dropna(subset=["debut_date", "total_weeks"]).copy()
    df = df[df["total_weeks"] > 0].copy()

    # Conservative cutoff: retain only complete debut years with at least
    # approximately one year of chart observation after the debut.
    last_chart_date = df["last_date"].max() if "last_date" in df else df["debut_date"].max()
    cutoff_date = min(
        last_chart_date - pd.Timedelta(days=365),
        pd.Timestamp(year=last_chart_date.year - 2, month=12, day=31),
    )
    df = df[df["debut_date"] <= cutoff_date].copy()
    if df.empty:
        raise ValueError("No songs remain after the observation-window filter.")

    df["decade"] = (df["debut_date"].dt.year // 10) * 10
    decade_order = sorted(df["decade"].unique())
    grouped = [df.loc[df["decade"] == decade, "total_weeks"].values for decade in decade_order]
    labels = [f"{int(decade)}s" for decade in decade_order]

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)

    summary = (
        df.groupby("decade")["total_weeks"]
        .agg(song_count="count", median_weeks="median", mean_weeks="mean",
             q1_weeks=lambda x: x.quantile(0.25), q3_weeks=lambda x: x.quantile(0.75))
        .reset_index()
    )
    summary.to_csv(SUMMARY_DIR / "q1_distribution_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(11, 6.5))
    ax.boxplot(
        grouped,
        tick_labels=labels,
        showfliers=False,
        patch_artist=True,
        medianprops={"linewidth": 2},
    )
    ax.set_yscale("log")
    ax.set_title("Distribution of Billboard Hit-Song Lifespan by Debut Decade")
    ax.set_xlabel("Debut decade")
    ax.set_ylabel("Time on Billboard Hot 100 (weeks, log scale)")
    ax.grid(axis="y", alpha=0.25, which="both")
    ax.text(
        0.01, -0.19,
        "Note: Lifespan is the number of distinct chart weeks, including re-entries. "
        f"Songs debuting after {cutoff_date.date()} are excluded to reduce right-censoring.",
        transform=ax.transAxes, fontsize=8, va="top",
    )
    fig.tight_layout()
    output_path = OUTPUT_DIR / "q1_lifespan_distribution.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved figure: {output_path}")
    print(f"Saved summary: {SUMMARY_DIR / 'q1_distribution_summary.csv'}")
    print(f"Songs included: {len(df):,}; observation cutoff: {cutoff_date.date()}")


if __name__ == "__main__":
    main()
