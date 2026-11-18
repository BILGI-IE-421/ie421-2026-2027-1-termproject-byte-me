"""Clean Billboard and Spotify sources and create analysis-ready tables.

Run from the repository root:
    python scripts/preprocess.py

Optional paths:
    python scripts/preprocess.py --billboard data/raw/billboard/charts.csv \
        --spotify data/raw/spotify/universal_top_spotify_songs.csv

Spotify is staged in SQLite to avoid loading the multi-million-row source into
memory. The script writes slim CSV outputs needed by Q1, Q2, and Q3.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import make_song_key, parse_date  # noqa: E402

RAW_BB_DEFAULT = ROOT / "data/raw/billboard/charts.csv"
RAW_SP_DEFAULT = ROOT / "data/raw/spotify/universal_top_spotify_songs.csv"
OUT_DIR = ROOT / "data/processed"
LOG_PATH = OUT_DIR / "cleaning_log.json"

CHUNK_SIZE = 250_000
DAYFIRST = False


def find_input(explicit: str | None, default: Path, patterns: list[str]) -> Path:
    if explicit:
        path = Path(explicit)
        if not path.is_absolute():
            path = ROOT / path
        if not path.exists():
            raise FileNotFoundError(path)
        return path
    if default.exists():
        return default
    raw_root = ROOT / "data/raw"
    matches = []
    for pattern in patterns:
        matches.extend(raw_root.glob(pattern))
    matches = [p for p in matches if p.is_file()]
    if len(matches) == 1:
        return matches[0]
    if not matches:
        raise FileNotFoundError(
            f"Could not find input file. Expected {default} or pass an explicit path."
        )
    raise RuntimeError(
        "Multiple possible input files found; pass an explicit path: "
        + ", ".join(str(p) for p in matches)
    )


def clean_billboard(path: Path, log: dict) -> None:
    print(f"[Billboard] Reading {path}")
    df = pd.read_csv(path, low_memory=False)
    raw_rows = len(df)
    log["bb_raw_rows"] = int(raw_rows)
    log["bb_raw_columns"] = int(df.shape[1])
    log["bb_exact_duplicate_rows_dropped"] = int(df.duplicated().sum())
    df = df.drop_duplicates().copy()

    rename = {
        "peak-rank": "peak_rank",
        "weeks-on-board": "weeks_on_board",
        "last-week": "last_week",
    }
    df = df.rename(columns=rename)

    required = ["date", "song", "artist", "rank"]
    missing_cols = [c for c in required if c not in df.columns]
    if missing_cols:
        raise ValueError(f"Billboard source is missing required columns: {missing_cols}")

    for col in ["date"]:
        df[col] = df[col].map(parse_date)

    for col in ["rank", "peak_rank", "weeks_on_board"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    for col in ["song", "artist"]:
        df[col] = df[col].astype("string").str.strip()
        df[col] = df[col].replace("", pd.NA)

    missing_mask = df[["date", "song", "artist", "rank"]].isna().any(axis=1)
    log["bb_dropped_missing_date_song_artist_or_rank"] = int(missing_mask.sum())
    df = df.loc[~missing_mask].copy()

    bad_rank = ~df["rank"].between(1, 100)
    log["bb_dropped_rank_outside_1_100"] = int(bad_rank.sum())
    df = df.loc[~bad_rank].copy()
    df["rank"] = df["rank"].astype("int16")

    for col in ["peak_rank", "weeks_on_board"]:
        if col in df.columns:
            df[col] = df[col].astype("Int64")

    df["song_id"] = df["song"].astype(str) + " || " + df["artist"].astype(str)
    duplicate_song_week = df.duplicated(["song_id", "date"], keep=False)
    # If duplicate credits occur for the same song-week, keep the best chart rank.
    duplicate_rows = int(df.duplicated(["song_id", "date"]).sum())
    log["bb_same_song_same_week_dropped"] = duplicate_rows
    df = (
        df.sort_values(["song_id", "date", "rank"])
        .drop_duplicates(["song_id", "date"], keep="first")
        .copy()
    )

    keep = ["date", "rank", "song", "artist"]
    for col in ["peak_rank", "weeks_on_board"]:
        if col in df.columns:
            keep.append(col)
    keep.append("song_id")
    df = df[keep].sort_values(["date", "rank"]).reset_index(drop=True)
    df.to_csv(OUT_DIR / "billboard_clean.csv", index=False)

    songs = (
        df.groupby("song_id", as_index=False)
        .agg(
            song=("song", "first"),
            artist=("artist", "first"),
            debut_date=("date", "min"),
            last_date=("date", "max"),
            total_weeks=("date", "nunique"),
            peak=("rank", "min"),
        )
    )
    songs["debut_year"] = songs["debut_date"].dt.year.astype("int16")
    songs["decade"] = (songs["debut_year"] // 10) * 10
    songs["song_key"] = [
        make_song_key(title, artist)
        for title, artist in zip(songs["song"], songs["artist"])
    ]
    songs.to_csv(OUT_DIR / "billboard_songs.csv", index=False)

    log["bb_clean_rows"] = int(len(df))
    log["bb_unique_songs"] = int(len(songs))
    log["bb_date_min"] = str(df["date"].min().date())
    log["bb_date_max"] = str(df["date"].max().date())
    log["bb_tied_rank_observations"] = int(
        df.duplicated(["date", "rank"], keep=False).sum()
    )
    print(f"[Billboard] {len(df):,} weekly rows; {len(songs):,} songs")


def create_spotify_database(db_path: Path) -> sqlite3.Connection:
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE spotify_rows (
            spotify_id TEXT NOT NULL,
            country TEXT NOT NULL,
            snapshot_date TEXT NOT NULL,
            daily_rank INTEGER,
            name TEXT,
            artists TEXT,
            popularity REAL,
            duration_ms REAL,
            album_release_date TEXT,
            danceability REAL,
            energy REAL,
            valence REAL,
            song_key TEXT,
            PRIMARY KEY (spotify_id, country, snapshot_date)
        )
    """)
    conn.execute("CREATE INDEX idx_spotify_country_date ON spotify_rows(country, snapshot_date)")
    conn.execute("CREATE INDEX idx_spotify_id ON spotify_rows(spotify_id)")
    return conn


def clean_spotify(path: Path, log: dict) -> None:
    print(f"[Spotify] Reading in chunks: {path}")
    db_path = OUT_DIR / "spotify_staging.sqlite"
    conn = create_spotify_database(db_path)

    usecols = [
        "spotify_id", "name", "artists", "daily_rank", "country",
        "snapshot_date", "popularity", "duration_ms", "album_release_date",
        "danceability", "energy", "valence",
    ]
    # Some source versions may omit optional audio fields; validate core columns.
    header = pd.read_csv(path, nrows=0).columns.tolist()
    core = ["spotify_id", "daily_rank", "country", "snapshot_date", "name", "artists"]
    missing_core = [c for c in core if c not in header]
    if missing_core:
        raise ValueError(f"Spotify source is missing required columns: {missing_core}")
    available = [c for c in usecols if c in header]

    raw_rows = 0
    rejected_rows = 0
    inserted_before = 0

    for chunk_no, chunk in enumerate(
        pd.read_csv(path, usecols=available, chunksize=CHUNK_SIZE, low_memory=False), start=1
    ):
        raw_rows += len(chunk)
        for col in ["popularity", "duration_ms", "danceability", "energy", "valence", "daily_rank"]:
            if col in chunk.columns:
                chunk[col] = pd.to_numeric(chunk[col], errors="coerce")
        chunk["snapshot_date"] = chunk["snapshot_date"].map(parse_date)
        if "album_release_date" in chunk.columns:
            chunk["album_release_date"] = chunk["album_release_date"].map(parse_date)
        else:
            chunk["album_release_date"] = pd.NaT

        chunk["spotify_id"] = chunk["spotify_id"].astype("string").str.strip()
        chunk["country"] = chunk["country"].fillna("GLOBAL").astype("string").str.strip()
        chunk["name"] = chunk["name"].astype("string").str.strip()
        chunk["artists"] = chunk["artists"].astype("string").str.strip()

        valid = (
            chunk["spotify_id"].notna()
            & chunk["spotify_id"].ne("")
            & chunk["snapshot_date"].notna()
            & chunk["daily_rank"].notna()
        )
        rejected_rows += int((~valid).sum())
        chunk = chunk.loc[valid].copy()
        chunk = chunk.loc[chunk["daily_rank"].between(1, 50)].copy()
        if chunk.empty:
            continue

        chunk["daily_rank"] = chunk["daily_rank"].astype("int16")
        chunk["song_key"] = [
            make_song_key(title, artist)
            for title, artist in zip(chunk["name"], chunk["artists"])
        ]

        columns = [
            "spotify_id", "country", "snapshot_date", "daily_rank", "name",
            "artists", "popularity", "duration_ms", "album_release_date",
            "danceability", "energy", "valence", "song_key",
        ]
        for col in columns:
            if col not in chunk.columns:
                chunk[col] = np.nan
        chunk = chunk[columns].copy()
        chunk["snapshot_date"] = chunk["snapshot_date"].dt.strftime("%Y-%m-%d")
        chunk["album_release_date"] = pd.to_datetime(
            chunk["album_release_date"], errors="coerce"
        ).dt.strftime("%Y-%m-%d")

        rows = []
        for row in chunk.itertuples(index=False, name=None):
            rows.append(tuple(None if pd.isna(v) else v for v in row))
        conn.executemany(
            """INSERT OR IGNORE INTO spotify_rows
            (spotify_id, country, snapshot_date, daily_rank, name, artists,
             popularity, duration_ms, album_release_date, danceability,
             energy, valence, song_key)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            rows,
        )
        conn.commit()

        if chunk_no % 4 == 0:
            print(f"  processed {raw_rows:,} source rows...")
    inserted = conn.execute("SELECT COUNT(*) FROM spotify_rows").fetchone()[0]

    log["sp_raw_rows"] = int(raw_rows)
    log["sp_rows_dropped_missing_or_invalid"] = int(rejected_rows)
    log["sp_unique_country_track_days"] = int(inserted)
    log["sp_rows_deduplicated_by_key"] = int(max(0, raw_rows - rejected_rows - inserted))
    log["sp_note_top50"] = "Only daily_rank 1-50 rows retained for Q2/Q3."

    # Q3: one row per track. chart_days counts distinct dates on which it appeared
    # in at least one country chart; n_countries excludes GLOBAL.
    track_sql = """
        SELECT
            spotify_id,
            MIN(name) AS name,
            MIN(artists) AS artists,
            MIN(song_key) AS song_key,
            COUNT(DISTINCT snapshot_date) AS chart_days,
            MIN(daily_rank) AS best_rank,
            MAX(popularity) AS popularity_max,
            COUNT(DISTINCT CASE WHEN country <> 'GLOBAL' THEN country END) AS n_countries,
            MIN(snapshot_date) AS first_seen,
            MAX(snapshot_date) AS last_seen,
            MIN(album_release_date) AS album_release_date,
            AVG(duration_ms) AS duration_ms,
            AVG(danceability) AS danceability,
            AVG(energy) AS energy,
            AVG(valence) AS valence
        FROM spotify_rows
        GROUP BY spotify_id
    """
    tracks = pd.read_sql_query(track_sql, conn)
    tracks.to_csv(OUT_DIR / "spotify_tracks.csv", index=False)
    log["sp_unique_tracks"] = int(len(tracks))
    log["sp_tracks_missing_audio_features"] = int(
        tracks[["danceability", "energy", "valence"]].isna().all(axis=1).sum()
    )

    # Q2: choose the latest available daily snapshot in each country-week, then
    # retain its Top-50 set. This creates one representative weekly snapshot.
    weekly_sql = """
        WITH dated AS (
            SELECT *,
                   date(snapshot_date, '-' || ((CAST(strftime('%w', snapshot_date) AS INTEGER) + 6) % 7) || ' days') AS week_start
            FROM spotify_rows
            WHERE country <> 'GLOBAL'
        ),
        latest AS (
            SELECT country, week_start, MAX(snapshot_date) AS selected_date
            FROM dated
            GROUP BY country, week_start
        )
        SELECT d.country, d.week_start, d.snapshot_date AS selected_snapshot_date,
               d.spotify_id, d.name, d.artists, d.daily_rank, d.song_key
        FROM dated d
        JOIN latest l
          ON d.country = l.country
         AND d.week_start = l.week_start
         AND d.snapshot_date = l.selected_date
        ORDER BY d.week_start, d.country, d.daily_rank
    """
    weekly = pd.read_sql_query(weekly_sql, conn)
    weekly.to_csv(OUT_DIR / "spotify_country_week.csv", index=False)
    log["sp_country_week_track_rows"] = int(len(weekly))
    log["sp_countries"] = int(weekly["country"].nunique()) if len(weekly) else 0
    log["sp_weeks"] = int(weekly["week_start"].nunique()) if len(weekly) else 0

    # Compact daily presence table supports Q3 diffusion/animation without
    # copying audio metadata into a second very large file.
    daily_path = OUT_DIR / "spotify_track_country_day.csv"
    pd.read_sql_query(
        """SELECT spotify_id, country, snapshot_date, daily_rank
           FROM spotify_rows
           ORDER BY snapshot_date, country, daily_rank""",
        conn,
    ).to_csv(daily_path, index=False)

    conn.close()
    # Keep the SQLite staging database until outputs have been checked; it can
    # be deleted manually to reclaim disk space after successful regeneration.
    log["sp_staging_database"] = str(db_path.relative_to(ROOT))
    print(
        f"[Spotify] {inserted:,} unique country-track-day rows; "
        f"{len(tracks):,} tracks; {len(weekly):,} country-week-track rows"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Preprocess Billboard and Spotify datasets.")
    parser.add_argument("--billboard", default=None, help="Path to raw Billboard CSV")
    parser.add_argument("--spotify", default=None, help="Path to raw Spotify CSV")
    args = parser.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    billboard_path = find_input(
        args.billboard, RAW_BB_DEFAULT,
        ["billboard/**/*.csv", "**/charts.csv"]
    )
    spotify_path = find_input(
        args.spotify, RAW_SP_DEFAULT,
        ["spotify/**/*.csv", "**/universal_top_spotify_songs.csv"]
    )

    log = {
        "date_accessed": "2026-11-17",
        "date_parser": "pandas.to_datetime via scripts/common.py; DAYFIRST=False",
        "timezone_policy": "Source chart/snapshot dates treated as timezone-naive; no conversion.",
        "billboard_source_file": str(billboard_path.relative_to(ROOT)) if billboard_path.is_relative_to(ROOT) else str(billboard_path),
        "spotify_source_file": str(spotify_path.relative_to(ROOT)) if spotify_path.is_relative_to(ROOT) else str(spotify_path),
    }

    clean_billboard(billboard_path, log)
    clean_spotify(spotify_path, log)

    with open(LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(log, f, indent=2, ensure_ascii=False, default=str)

    print(f"Done. Cleaning log: {LOG_PATH}")


if __name__ == "__main__":
    main()
