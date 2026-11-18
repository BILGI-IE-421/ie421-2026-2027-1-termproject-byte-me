"""Q1 - Trend in annual median Billboard hit-song lifespan.

Run from the repository root:
    python scripts/q1_trend.py

Input:
    data/processed/billboard_songs.csv

Outputs:
    visuals/q1_annual_lifespan_trend.png
    data/processed/q1_trend_summary.csv
"""
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data/processed/billboard_songs.csv"
OUTPUT_DIR = ROOT / "visuals"
SUMMARY_DIR = ROOT / "data/processed"
N_BOOTSTRAP = 1000
RANDOM_SEED = 42


def bootstrap_median_ci(values, n_bootstrap=N_BOOTSTRAP, seed=RANDOM_SEED):
    """Return percentile 95% bootstrap confidence interval for the median."""
    values = np.asarray(values, dtype=float)
    if len(values) == 0:
        return np.nan, np.nan
    rng = np.random.default_rng(seed)
    samples = rng.choice(values, size=(n_bootstrap, len(values)), replace=True)
    medians = np.median(samples, axis=1)
    lower, upper = np.percentile(medians, [2.5, 97.5])
    return float(lower), float(upper)


def main():
    if not INPUT.exists():
        raise FileNotFoundError(
            f"Missing {INPUT}. Run scripts/preprocess.py first."
        )

    df = pd.read_csv(INPUT, parse_dates=["debut_date", "last_date"])
    required = {"debut_date", "last_date", "total_weeks"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Input is missing required columns: {sorted(missing)}")

    df["total_weeks"] = pd.to_numeric(df["total_weeks"], errors="coerce")
    df = df.dropna(subset=["debut_date", "last_date", "total_weeks"]).copy()
    df = df[df["total_weeks"] > 0].copy()

    last_chart_date = df["last_date"].max()
    # Keep only complete debut years and allow at least a one-year observation
    # window after debut. This avoids comparing partially observed recent years.
    cutoff_date = min(
        last_chart_date - pd.Timedelta(days=365),
        pd.Timestamp(year=last_chart_date.year - 2, month=12, day=31),
    )
    df = df[df["debut_date"] <= cutoff_date].copy()
    df["debut_year"] = df["debut_date"].dt.year

    records = []
    for year, group in df.groupby("debut_year"):
        values = group["total_weeks"].to_numpy()
        lower, upper = bootstrap_median_ci(values, seed=RANDOM_SEED + int(year))
        records.append({
            "debut_year": int(year),
            "song_count": int(len(group)),
            "median_weeks": float(np.median(values)),
            "ci_lower": lower,
            "ci_upper": upper,
            "share_5_weeks_or_less": float((values <= 5).mean()),
        })

    summary = pd.DataFrame(records).sort_values("debut_year")
    if summary.empty:
        raise ValueError("No complete debut years remain after filtering.")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    SUMMARY_DIR.mkdir(parents=True, exist_ok=True)
    summary.to_csv(SUMMARY_DIR / "q1_trend_summary.csv", index=False)

    fig, ax = plt.subplots(figsize=(12, 6.5))
    x = summary["debut_year"].to_numpy()
    median = summary["median_weeks"].to_numpy()
    lower = summary["ci_lower"].to_numpy()
    upper = summary["ci_upper"].to_numpy()

    ax.plot(x, median, linewidth=2, marker="o", markersize=4,
            label="Annual median lifespan")
    ax.fill_between(x, lower, upper, alpha=0.2,
                    label="95% bootstrap confidence interval")
    ax.set_title("Annual Trend in Billboard Hit-Song Lifespan")
    ax.set_xlabel("Debut year")
    ax.set_ylabel("Median time on Billboard Hot 100 (weeks)")
    ax.grid(alpha=0.25)
    ax.legend(frameon=False)
    ax.text(
        0.01, -0.19,
        "Note: Lifespan counts distinct chart weeks, including re-entries. "
        f"Songs debuting after {cutoff_date.date()} are excluded. "
        "The shaded area is a 95% percentile bootstrap confidence interval.",
        transform=ax.transAxes, fontsize=8, va="top",
    )
    fig.tight_layout()
    output_path = OUTPUT_DIR / "q1_annual_lifespan_trend.png"
    fig.savefig(output_path, dpi=300, bbox_inches="tight")
    plt.close(fig)

    print(f"Saved figure: {output_path}")
    print(f"Saved summary: {SUMMARY_DIR / 'q1_trend_summary.csv'}")
    print(f"Years included: {summary['debut_year'].min()}–{summary['debut_year'].max()}")
    print(f"Observation cutoff: {cutoff_date.date()}")


if __name__ == "__main__":
    main()
