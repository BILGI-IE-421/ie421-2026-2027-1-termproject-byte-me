# Data Card

> **Note:** Raw files larger than 50 MB are never committed to the repository (`data/raw/` is listed in `.gitignore`). Running `python scripts/download_data.py` automatically downloads and recreates the `data/raw/` directory.

---

## Dataset 1: Billboard Hot 100 since 1958 (`charts.csv`)

* **Source and URL:** Kaggle — Billboard Hot 100 (`https://www.kaggle.com/datasets/dhruvildave/billboard-the-hot-100-songs`)
* **License:** CC0: Public Domain
* **Date accessed:** 2026-11-17
* **Time range and granularity:** August 1958 – November 2021; weekly chart rankings (Top 100 songs per week).
* **Size:** 330,087 rows x 7 columns (raw); 330,087 rows x 10 columns after cleaning and feature extraction (0 duplicate rows).
* **Columns used:** `date`, `rank`, `song`, `artist`, `last-week`, `peak-rank`, `weeks-on-board`
* **Known issues:** 
  * `last-week` contains 32,312 missing (`NaN`) values, which naturally correspond to debut entries that were not on the chart the previous week.
  * Inconsistent artist separator conventions across decades (e.g., `"feat."`, `"featuring"`, `"&"`, `"x"`).
  * Minor punctuation and casing differences in `song` and `artist` strings that affect cross-dataset joins.
* **Cleaning decisions and why:** 
  * Converted `date` from `object` to `datetime64[ns]` (`YYYY-MM-DD`) and extracted `year` to enable longitudinal lifespan analysis across decades.
  * Retained rows with null `last-week` values because dropping them would remove every song's debut week and bias lifespan calculations.
  * Created normalized `song_clean` and `artist_clean` columns (lowercased, stripped whitespace/punctuation, extracted primary artist) to reliably join Billboard records with Spotify charts.
* **How to regenerate:** Run `python scripts/download_data.py` to download `charts.csv` into `data/raw/`, then run `python scripts/clean_data.py` to produce `data/processed/billboard_clean.csv`.

---

## Dataset 2: Top Spotify Songs in 73 Countries (`universal_top_spotify_songs.csv`)

* **Source and URL:** Kaggle — Top Spotify Songs in 73 Countries (`https://www.kaggle.com/datasets/asaniczka/top-spotify-songs-in-73-countries-daily-updated`)
* **License:** ODC Attribution License (ODC-By)
* **Date accessed:** 2026-11-17
* **Time range and granularity:** October 2023 – Present; daily Top 50 song rankings across 73 countries plus the Global chart.
* **Size:** ~10M+ rows (depending on the latest daily update dump) x 25 columns (raw); filtered/cleaned rows after processing.
* **Columns used:** `spotify_id`, `name`, `artists`, `daily_rank`, `daily_movement`, `country`, `snapshot_date`, `popularity`, `is_explicit`, `duration_ms`, `danceability`, `energy`, `valence`, `tempo`
* **Known issues:** 
  * Missing (`NaN`) values in the `country` column represent the worldwide `"GLOBAL"` chart rather than missing country codes.
  * The raw CSV file exceeds GitHub's 50 MB file size limit due to daily granularity across 73 markets.
  * Collaborating artists are stored as a single comma-separated string in `artists`.
* **Cleaning decisions and why:** 
  * Imputed null `country` entries as `"GLOBAL"` so global chart trends can be compared directly against national markets without losing rows during filtering.
  * Parsed `snapshot_date` into `datetime64[ns]` and deduplicated any exact `(spotify_id, country, snapshot_date)` entries.
  * Standardized `name` and extracted the lead artist from `artists` into `song_clean` and `artist_clean` to match with Billboard Hot 100 entries.
* **How to regenerate:** Run `python scripts/download_data.py` to fetch the raw CSV into `data/raw/`, then run `python scripts/clean_data.py` to output `data/processed/spotify_clean.csv`.
