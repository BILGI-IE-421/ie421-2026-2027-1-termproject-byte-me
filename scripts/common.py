"""Shared helpers for the byte-me pipeline: paths, one date parser, one song key.

Every script imports from here so that dates are parsed and songs are matched
in exactly one way across the project.
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROC = ROOT / "data" / "processed"
PROC.mkdir(parents=True, exist_ok=True)

# One date setting for the whole project. All source dates are ISO (YYYY-MM-DD,
# or YYYY / YYYY-MM for some album_release_date values), so day-first is False.
DAYFIRST = False


@lru_cache(maxsize=None)
def _parse_one(value: str) -> pd.Timestamp:
    return pd.to_datetime(value, errors="coerce", dayfirst=DAYFIRST, format="mixed")


def parse_date(value):
    """Parse a single date or a whole Series with the project's one date setting.

    Works both as parse_date(series) and as series.map(parse_date).
    Unparseable or missing values become NaT. Dates are kept timezone-naive.
    """
    if isinstance(value, pd.Series):
        return pd.to_datetime(value, errors="coerce", dayfirst=DAYFIRST, format="mixed")
    if value is None or (isinstance(value, float) and pd.isna(value)) or value is pd.NA:
        return pd.NaT
    return _parse_one(str(value).strip())


# ---- song key used to match Billboard songs with Spotify tracks -------------
_BRACKETS = re.compile(r"[\(\[].*?[\)\]]")             # "(feat. X)", "[Remix]"
_DASH_SUFFIX = re.compile(r"\s+-\s+.*$")                # "Song - Remastered 2011"
_FEAT_IN_TITLE = re.compile(r"\s+(feat\.?|ft\.?|featuring)\s+.*$")
_ARTIST_SPLIT = re.compile(
    r"\s*(?:,|&|\+|/|\bfeaturing\b|\bfeat\.?|\bft\.?|\bwith\b|\bx\b|\band\b)\s*"
)
_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def _ascii_lower(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    return text.encode("ascii", "ignore").decode("ascii").lower()


def make_song_key(title, artist):
    """Normalised 'title|lead artist' key, or None if either part is missing.

    Title: ASCII, lowercase, bracketed parts and ' - ...' suffixes removed.
    Artist: only the first (lead) artist, so credit order and features matter less.
    """
    if title is None or artist is None or pd.isna(title) or pd.isna(artist):
        return None
    t = _ascii_lower(str(title))
    t = _BRACKETS.sub(" ", t)
    t = _DASH_SUFFIX.sub("", t)
    t = _FEAT_IN_TITLE.sub("", t)
    t = _NON_ALNUM.sub(" ", t).strip()

    a = _ascii_lower(str(artist))
    a = _ARTIST_SPLIT.split(a, maxsplit=1)[0]
    a = _NON_ALNUM.sub(" ", a).strip()

    if not t or not a:
        return None
    return f"{t}|{a}"


# Older name used by clean_data.py
make_key = make_song_key


def build_song_table(bb: pd.DataFrame) -> pd.DataFrame:
    """One row per Billboard song_id from the cleaned weekly table."""
    songs = (bb.groupby("song_id", as_index=False)
               .agg(song=("song", "first"), artist=("artist", "first"),
                    debut_date=("date", "min"), last_date=("date", "max"),
                    total_weeks=("date", "nunique"), peak=("rank", "min"),
                    max_weeks_on_board=("weeks_on_board", "max")))
    songs["debut_year"] = songs["debut_date"].dt.year
    songs["decade"] = (songs["debut_year"] // 10) * 10
    songs["song_key"] = [make_song_key(s, a) for s, a in zip(songs["song"], songs["artist"])]
    return songs
