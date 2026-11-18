# Data Card: Hit-song lifespans (Billboard Hot 100 x Spotify)

## 1. Purpose
Support the research question **"Are hit songs' lifespans getting shorter?"** (Q1 of the project: distribution + trend figures).
Spotify is joined to Billboard for exploratory enrichment (track length, audio features, catalog re-entry). It is **not** used for the two Q1 figures.

## 2. Sources
| | Billboard Hot 100 | Spotify Top Songs in 73 Countries |
|---|---|---|
| Kaggle | `dhruvildave/billboard-the-hot-100-songs` | `asaniczka/top-spotify-songs-in-73-countries-daily-updated` |
| Access | Kaggle API (`src/download_data.py`) | Kaggle API (`src/download_data.py`) |
| File | `charts.csv` | `universal_top_spotify_songs.csv` (several GB) |
| Granularity | one row per song per chart week (Hot 100) | one row per track per country per day (Top 50) |
| Coverage | 1958-08-04 to 2021-11-06 (weekly) | Oct 2023 onwards (daily, ~72 countries + global) |
| Licence | *Record from the Kaggle dataset page before publishing* | *Record from the Kaggle dataset page before publishing* |
| Retrieved | *YYYY-MM-DD (fill in)* | *YYYY-MM-DD (fill in)* |

The two sources **do not overlap in time**; they overlap only in songs (old hits re-streamed after 2023, and 2021-era songs).

## 3. Columns kept and dropped
**Billboard** - kept: `date`, `rank`, `song`, `artist`, `peak-rank`, `weeks-on-board`. Dropped: `last-week` (redundant with last week's rank, NA at debut, adds nothing to lifespan).

**Spotify** - kept: `spotify_id`, `name`, `artists`, `country`, `snapshot_date`, `daily_rank`, `popularity`, `duration_ms`, `album_release_date`, `danceability`, `energy`, `valence`.
Dropped: `daily_movement`, `weekly_movement`, `is_explicit`, `album_name`, `key`, `loudness`, `mode`, `speechiness`, `acousticness`, `instrumentalness`, `liveness`, `tempo`, `time_signature` (not needed for any planned figure; dropping them at read time cuts memory by about half).

## 4. Time, units
* Dates are ISO-8601 `YYYY-MM-DD`, **naive (no time zone)**. One parser (`common.parse_date`), one `DAYFIRST = False` setting; no ambiguity arises because both sources are ISO.
* Billboard `date` is the chart issue date (weekly, Saturday). Spotify `snapshot_date` is the chart day as published; Spotify does not document a time zone, so no conversion was applied (assumption: local chart day per country).
* `rank` / `daily_rank`: positions 1-100 / 1-50. `total_weeks`: count of distinct chart weeks. `duration_ms`: milliseconds. Audio features: 0-1 scale (as Spotify defines them). `popularity`: 0-100.

## 5. Cleaning decisions (implemented in `src/clean_data.py`, counts in `data/processed/cleaning_log.json`)
| Issue | Decision | Why |
|---|---|---|
| Missing `date`, `song`, `artist` or `rank` (Billboard) | **Drop row** | Row cannot be assigned to a song-week |
| Empty strings in `song` / `artist` | Converted to NA, then dropped | Same |
| `rank` outside 1-100 | Drop row | Invalid for a Hot 100 |
| Exact duplicate rows | Drop | Pure repetition |
| Same song twice in one week | Keep the better rank | One chart position per week |
| Several songs tied on a rank | **Keep**, count in log | Real ties, not errors |
| Missing `weeks-on-board` | Keep as NA (not used to define lifespan) | `total_weeks` is derived from dates instead |
| No song ID in Billboard | `song_id = song + " || " + artist` (stripped exact strings) | Only available identity |
| Spotify rows missing `spotify_id`, `snapshot_date` or `daily_rank` | Drop | Unusable |
| Spotify `country` empty | Label `GLOBAL`, excluded from `n_countries` | Empty means the global chart |
| Duplicate `(spotify_id, country, snapshot_date)` | Drop (within 1M-row chunks; cross-chunk duplicates are rare and would only inflate `chart_rows` slightly) | |
| Missing audio features / duration | **Keep NaN, never impute** | Imputation would invent values |
| Several `spotify_id`s for one song (remasters) | Keep the most-charted for the join | Join must be many-to-one |

**Join:** Billboard songs (left) x Spotify tracks on `song_key` = normalised primary title + primary artist (lower-case ASCII, bracketed credits and "- Remix" suffixes removed, only the first credited artist). Reported `join_match_rate` in the log. Non-Latin titles can fail to normalise and remain unmatched.

## 6. Derived variables (Billboard song level)
`debut_date` (first chart week), `last_date`, `total_weeks` (distinct chart weeks, re-entries included), `peak` (best rank), `debut_year`, `decade`.
Right-censoring: songs whose `debut_date` is within 365 days of the last chart week are excluded from analysis; analysis covers debut years 1960 to (last full year).

## 7. Known limitations
* Only the top 100 (Billboard) / top 50 (Spotify) is visible: lifespan is lifespan *in the top tier*.
* Chart methodology changed several times (`data/external/rule_changes.json`, dates must be verified); cross-era comparisons mix behaviour and rules.
* Identity by text: credit variants and re-releases can split or merge songs; seasonal songs (Christmas) re-enter yearly and inflate lifespans.
* The Spotify extract is short (about 2+ years) and biased to the recent catalog; the matched subset is not a random sample of Billboard songs.
* Correlation is not causation.

## 8. Ethics and licensing
Public chart data, no personal data. Charts reflect platform algorithms and sales/stream weighting, not artistic merit. Artist revenue and algorithmic-recommendation effects are out of scope but relevant to interpretation. Respect each Kaggle dataset's licence; do not redistribute the raw files in this repository (`data/raw/` is git-ignored).

## 9. Reproduce
```
pip install -r requirements.txt
python src/download_data.py
python src/clean_data.py
python src/q1_analysis.py
python src/build_site.py
python notebooks/make_notebook.py
```
