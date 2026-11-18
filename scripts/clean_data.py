"""Clean Billboard + Spotify, then join them at song level.
Usage: python src/clean_data.py
Outputs (data/processed): billboard_clean.csv, spotify_songs.csv, billboard_songs.csv, cleaning_log.json
Every decision below is mirrored in DATA_CARD.md."""
import json

import pandas as pd

from common import PROC, RAW, build_song_table, make_key, parse_date

# ---- columns KEPT (everything else is dropped at read time) -----------------
BB_COLS = ["date", "rank", "song", "artist", "peak-rank", "weeks-on-board"]  # drops: last-week
SP_COLS = ["spotify_id", "name", "artists", "country", "snapshot_date", "daily_rank", "popularity",
           "duration_ms", "album_release_date", "danceability", "energy", "valence"]
CHUNK = 1_000_000


def clean_billboard(log):
    bb = pd.read_csv(RAW / "billboard" / "charts.csv", usecols=BB_COLS)
    bb = bb.rename(columns={"peak-rank": "peak_rank", "weeks-on-board": "weeks_on_board"})
    log["bb_raw_rows"] = len(bb)

    bb["date"] = parse_date(bb["date"])
    for c in ("song", "artist"):
        bb[c] = bb[c].astype("string").str.strip()
        bb[c] = bb[c].mask(bb[c] == "")
    for c in ("rank", "peak_rank", "weeks_on_board"):
        bb[c] = pd.to_numeric(bb[c], errors="coerce")

    n = len(bb)
    bb = bb.dropna(subset=["date", "song", "artist", "rank"])
    log["bb_dropped_missing_date_song_artist_or_rank"] = n - len(bb)

    n = len(bb)
    bb = bb[bb["rank"].between(1, 100)]
    log["bb_dropped_rank_outside_1_100"] = n - len(bb)

    bb["song_id"] = bb["song"] + " || " + bb["artist"]  # exact strings = identity

    n = len(bb)
    bb = bb.drop_duplicates()
    log["bb_exact_duplicate_rows_dropped"] = n - len(bb)

    n = len(bb)  # same song twice in one week -> keep the better rank
    bb = bb.sort_values(["date", "song_id", "rank"]).drop_duplicates(["date", "song_id"], keep="first")
    log["bb_same_song_same_week_dropped"] = n - len(bb)

    log["bb_same_rank_ties_in_a_week_kept"] = int(bb.duplicated(["date", "rank"]).sum())
    log["bb_missing_weeks_on_board_kept_as_NA"] = int(bb["weeks_on_board"].isna().sum())
    bb = bb.sort_values(["date", "rank"]).reset_index(drop=True)
    log["bb_clean_rows"] = len(bb)
    log["bb_min_date"], log["bb_max_date"] = str(bb["date"].min().date()), str(bb["date"].max().date())
    return bb


def clean_spotify(log):
    """Stream the multi-GB file in chunks; aggregate to ONE row per spotify_id."""
    parts, pairs, raw_rows, dropped = [], [], 0, 0
    path = RAW / "spotify" / "universal_top_spotify_songs.csv"
    for ch in pd.read_csv(path, usecols=SP_COLS, chunksize=CHUNK):
        raw_rows += len(ch)
        n = len(ch)
        ch["snapshot_date"] = parse_date(ch["snapshot_date"])
        ch = ch.dropna(subset=["spotify_id", "snapshot_date", "daily_rank"])
        ch["country"] = ch["country"].fillna("GLOBAL")  # empty country = global chart
        ch = ch.drop_duplicates(["spotify_id", "country", "snapshot_date"])
        dropped += n - len(ch)
        parts.append(ch.groupby("spotify_id").agg(
            name=("name", "first"), artists=("artists", "first"),
            duration_ms=("duration_ms", "first"), album_release_date=("album_release_date", "first"),
            danceability=("danceability", "first"), energy=("energy", "first"), valence=("valence", "first"),
            popularity_max=("popularity", "max"), chart_rows=("daily_rank", "size"),
            best_rank=("daily_rank", "min"), first_seen=("snapshot_date", "min"),
            last_seen=("snapshot_date", "max")).reset_index())
        pairs.append(ch.loc[ch["country"] != "GLOBAL", ["spotify_id", "country"]].drop_duplicates())

    allp = pd.concat(parts)
    sp = allp.groupby("spotify_id").agg(
        name=("name", "first"), artists=("artists", "first"), duration_ms=("duration_ms", "first"),
        album_release_date=("album_release_date", "first"), danceability=("danceability", "first"),
        energy=("energy", "first"), valence=("valence", "first"), popularity_max=("popularity_max", "max"),
        chart_rows=("chart_rows", "sum"), best_rank=("best_rank", "min"),
        first_seen=("first_seen", "min"), last_seen=("last_seen", "max")).reset_index()
    nc = pd.concat(pairs).drop_duplicates().groupby("spotify_id").size().rename("n_countries")
    sp = sp.merge(nc, on="spotify_id", how="left")
    sp["n_countries"] = sp["n_countries"].fillna(0).astype(int)
    sp["album_release_date"] = parse_date(sp["album_release_date"])
    # Missing audio features / duration are KEPT as NaN (never imputed).
    sp["song_key"] = [make_key(s, a) for s, a in zip(sp["name"], sp["artists"])]

    log.update(sp_raw_rows=raw_rows, sp_rows_dropped_missing_or_duplicate=dropped,
               sp_unique_tracks=len(sp), sp_tracks_missing_audio_features=int(sp["danceability"].isna().sum()))
    return sp


def main():
    log = {}
    bb = clean_billboard(log)
    songs = build_song_table(bb)
    log["bb_unique_songs"] = len(songs)
    log["bb_songs_total_weeks_equals_max_weeks_on_board_share"] = round(
        float((songs["total_weeks"] == songs["max_weeks_on_board"]).mean()), 4)

    sp = clean_spotify(log)

    # ---- JOIN: Billboard songs (left) x Spotify tracks via normalised song+artist key -------------
    sp_one = (sp.dropna(subset=["song_key"]).sort_values("chart_rows", ascending=False)
                .drop_duplicates("song_key"))  # remasters / duplicate ids -> keep most-charted
    keep = ["song_key", "spotify_id", "duration_ms", "danceability", "energy", "valence",
            "popularity_max", "n_countries", "chart_rows", "album_release_date"]
    sp_one = sp_one[keep].rename(columns=lambda c: c if c == "song_key" else f"sp_{c}")
    joined = songs.merge(sp_one, on="song_key", how="left", validate="many_to_one")
    joined["matched_spotify"] = joined["sp_spotify_id"].notna()
    log["join_billboard_songs_matched_to_spotify"] = int(joined["matched_spotify"].sum())
    log["join_match_rate"] = round(float(joined["matched_spotify"].mean()), 4)

    bb.to_csv(PROC / "billboard_clean.csv", index=False)
    sp.to_csv(PROC / "spotify_songs.csv", index=False)
    joined.to_csv(PROC / "billboard_songs.csv", index=False)
    (PROC / "cleaning_log.json").write_text(json.dumps(log, indent=2))
    print(json.dumps(log, indent=2))


if __name__ == "__main__":
    main()
