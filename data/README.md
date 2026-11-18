# Data Card

> **Note:** Raw files larger than 50 MB are never committed to the repository (`data/raw/` is listed in `.gitignore`). Running `python scripts/download_data.py` automatically downloads and recreates the `data/raw/` directory.

---

## Dataset 1: Billboard Hot 100 since 1958 (`charts.csv`)

* **Source and URL:** Kaggle — Billboard Hot 100 (`https://www.kaggle.com/datasets/dhruvildave/billboard-the-hot-100-songs`)
* **License:** CC0: Public Domain
* **Date accessed:** 2026-11-17
* **Time range and granularity:** August 1958 – November 2021; weekly chart rankings (Top 100 songs per week).
* **Size:** 330,087 rows x 7 columns (raw, 0 duplicate rows). After cleaning: 6 columns (`date`, `rank`, `song`, `artist`, `peak_rank`, `weeks_on_board`) plus the derived identifier `song_id`; the exact row count is written to `data/processed/cleaning_log.json` (`bb_clean_rows`).
* **Columns used:** `date`, `rank`, `song`, `artist`, `peak-rank`, `weeks-on-board`
* **Columns dropped:** `last-week` (see cleaning decisions).
* **Known issues:**
  * `last-week` contains 32,312 missing (`NaN`) values, which naturally correspond to debut entries that were not on the chart the previous week.
  * Inconsistent artist separator conventions across decades (e.g., `"feat."`, `"featuring"`, `"&"`, `"x"`).
  * Minor punctuation and casing differences in `song` and `artist` strings that affect cross-dataset joins.
  * There is no song identifier, so a song can only be identified by its `song` + `artist` text; re-releases and credit variants may split or merge songs, and seasonal songs re-enter the chart every year.
* **Cleaning decisions and why:**
  * **Dropped column `last-week`.** It only repeats the previous week's `rank` and is empty for every debut. Lifespan is derived from the dates instead, so no information is lost and no rows are removed because of it.
  * Parsed `date` from `object` to `datetime64[ns]` with one parser (`parse_date` in `scripts/common.py`) and one `DAYFIRST = False` setting. Dates are ISO `YYYY-MM-DD`, naive, with no time-zone conversion (chart issue dates, weekly).
  * Renamed `peak-rank` → `peak_rank` and `weeks-on-board` → `weeks_on_board`; converted `rank`, `peak_rank`, `weeks_on_board` to numeric.
  * Created the identifier `song_id = song + " || " + artist` (whitespace-stripped exact strings), because no id exists.
  * Built a song-level table (`groupby("song_id")`) with `debut_date`, `last_date`, `total_weeks` (distinct chart weeks), `peak` (best rank), `debut_year`, `decade`, and a normalized `song_key` (lowercased ASCII title without bracketed credits / "- Remix" suffixes + primary artist only) used to join with Spotify.
  * Kept rows with tied ranks in the same week (real ties, only counted in the log).
  * Kept missing `weeks_on_board` as `NA` (not used to define lifespan).
* **Deleted rows (counts logged in `cleaning_log.json`):**
  * Rows with missing `date`, `song`, `artist` or `rank` (empty strings count as missing): `bb_dropped_missing_date_song_artist_or_rank`.
  * Rows with `rank` outside 1–100: `bb_dropped_rank_outside_1_100`.
  * Exact duplicate rows: `bb_exact_duplicate_rows_dropped` (0 expected).
  * Same song twice in one week: `bb_same_song_same_week_dropped` (better rank kept).
  * Not deleted from the data but excluded **at analysis time**: songs that debuted in the last 365 days of the data (right-censoring) and partial calendar years (1958 and the final year).
* **How to regenerate:** Run `python scripts/download_data.py` to download `charts.csv` into `data/raw/billboard/`, then run `python scripts/clean_data.py` to produce `data/processed/billboard_clean.csv` (weekly rows) and `data/processed/billboard_songs.csv` (one row per song, joined with Spotify).

---

## Dataset 2: Top Spotify Songs in 73 Countries (`universal_top_spotify_songs.csv`)

* **Source and URL:** Kaggle — Top Spotify Songs in 73 Countries (`https://www.kaggle.com/datasets/asaniczka/top-spotify-songs-in-73-countries-daily-updated`)
* **License:** ODC Attribution License (ODC-By)
* **Date accessed:** 2026-11-17
* **Time range and granularity:** October 2023 – Present; daily Top 50 song rankings across 73 countries plus the Global chart.
* **Size:** ~10M+ rows (depending on the latest daily update dump) x 25 columns (raw). After cleaning the file is aggregated to **one row per track** (`spotify_id`); the exact counts are in `cleaning_log.json` (`sp_raw_rows`, `sp_unique_tracks`).
* **Columns used:** `spotify_id`, `name`, `artists`, `daily_rank`, `country`, `snapshot_date`, `popularity`, `duration_ms`, `album_release_date`, `danceability`, `energy`, `valence`
* **Columns dropped:** `daily_movement`, `weekly_movement`, `is_explicit`, `album_name`, `key`, `loudness`, `mode`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `tempo`, `time_signature`.
* **Known issues:**
  * Missing (`NaN`) values in the `country` column represent the worldwide `"GLOBAL"` chart rather than missing country codes.
  * The raw CSV file exceeds GitHub's 50 MB file size limit due to daily granularity across 73 markets.
  * Collaborating artists are stored as a single comma-separated string in `artists`.
  * `spotify_id` identifies a track *version*: remasters and re-uploads of the same song have different ids.
  * The Spotify window (Oct 2023 onward) does not overlap with Billboard (ends Nov 2021); the two datasets share songs, not time periods. Spotify does not document a time zone for `snapshot_date`.
* **Cleaning decisions and why:**
  * **Dropped 13 columns** (listed above) because none is needed for the Q1 lifespan analysis or the planned figures; this also roughly halves memory use for a multi-GB file. Reading uses `usecols` and 1,000,000-row chunks.
  * Filled null `country` entries with `"GLOBAL"` so the global chart is separable from national markets; `GLOBAL` is excluded from `n_countries`.
  * Parsed `snapshot_date` (and `album_release_date`, which may be `YYYY`, `YYYY-MM` or `YYYY-MM-DD`) with the same `parse_date` helper into `datetime64[ns]`.
  * Deduplicated exact `(spotify_id, country, snapshot_date)` entries inside each chunk.
  * Aggregated to one row per `spotify_id`: `chart_rows` (rows on any chart), `best_rank`, `popularity_max`, `first_seen`, `last_seen`, `n_countries`, with `duration_ms`, audio features and `album_release_date` taken as the first non-chunk value.
  * Missing audio features / `duration_ms` are kept as `NaN` and **never imputed**.
  * Created `song_key` (normalized title + lead artist from `artists`) to match Billboard. For the join, several tracks sharing a `song_key` are reduced to the most-charted one so the join is many-to-one.
* **Deleted rows (counts logged in `cleaning_log.json`):**
  * Rows missing `spotify_id`, `snapshot_date` or `daily_rank`, plus duplicate `(spotify_id, country, snapshot_date)` rows: `sp_rows_dropped_missing_or_duplicate`.
  * Duplicates that fall into different chunks are not detected; they could only inflate `chart_rows` slightly.
  * Tracks with missing audio features are kept (`sp_tracks_missing_audio_features` reports how many).
* **Join result:** Billboard songs (left) x Spotify tracks on `song_key`; matched counts and rate are reported as `join_billboard_songs_matched_to_spotify` and `join_match_rate`. The matched subset is biased toward old hits that were re-streamed after 2023, so it is used only for exploratory analysis.
* **How to regenerate:** Run `python scripts/download_data.py` to fetch the raw CSV into `data/raw/spotify/`, then run `python scripts/clean_data.py` to output `data/processed/spotify_clean.csv`.
