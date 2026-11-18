# IE 421 - Data Science for Engineers Term Project

## Disposable Hits, Global Sounds: Music Under Platform Capitalism
Popular music operates in a globalized digital marketplace where streaming platforms accelerate distribution across national borders while competing intensely for listener attention. This project investigates whether chart-topping songs have become shorter-lived over time and whether national musical tastes are converging under platform capitalism. By combining historical weekly rankings from the Billboard Hot 100 (1958–2021) with daily Top 50 country-level charts across 73 countries and the Global chart on Spotify (2023–present), we examine both long-term shifts in hit lifecycles and contemporary cross-national chart similarity. For our first research question, we measure song lifespan as distinct chart weeks from debut to final appearance while excluding right-censored recent debuts. Milestone 2 evidence indicates that median Hot 100 longevity rose steadily from roughly 7 weeks in the 1960s to a peak of 20 weeks around 2001, before collapsing to 2 weeks by 2020 as ultra-short streaming-era chart runs surged. Subsequent milestones will separate Billboard's 20-week recurrent chart rule from full-album streaming drops, quantify country-to-country taste similarity, and evaluate how multi-country presence shapes track durability. Together, these analyses clarify how algorithmic curation and platform economics reshape modern musical culture.

## Student Names
- Aleyna Cingiler (123203093)
- Meryem Öncü (125203106)
- Hakan Yıldırım (122203040)
- Abdüssamet Tutal (123203085)

## Files (Explain each of them with a sentence)
- `data/`: Contains the dataset documentation in `data/README.md` (raw Kaggle downloads stay in `data/raw/` and processed tables in `data/processed/`, and are excluded or regenerated locally).
- `scripts/`: Contains `download_data.py` (downloads raw Kaggle datasets), `common.py` (shared paths, date parser, and song-key helper), `preprocess.py` and `clean_data.py` (clean, stage, and join Billboard and Spotify tables), `figures.py`, `q1_trend.py`, and `q1_distribution.py` (generate Q1 static figures and summary CSVs), and `eda.ipynb` (exploratory data analysis notebook).
- `visuals/`: Includes the generated static figures `fig1_lifespan_trend.png` (annual median Billboard Hot 100 lifespan trend, 1958–2020) and `fig2_lifespan_distribution.png` (chart lifespan distributions comparing 1990–2004 and 2015–2020).
- `index.html` and `css/`: Main webpage (`index.html`) and stylesheet (`css/style.css`) for GitHub Pages hosting.
- `PROPOSAL.md`, `AI_USAGE.md`: Our project proposal defining the problem and research questions, and our AI usage declaration.
- `requirements.txt`: Python libraries required by the download, preprocessing, and plotting scripts.
- `.github/`: The automatic repository structure and script-compilation check (`structure-check.yml`).

## How to run (from the repository root)
List the commands that reproduce your results, in the order they must be run.
```
pip install -r requirements.txt
python scripts/download_data.py
python scripts/preprocess.py
python scripts/figures.py
```

## Key findings
- Typical Billboard Hot 100 hit longevity grew from a median of roughly 7 weeks in the 1960s to a peak of 20 weeks in 2001, before falling to a median of just 2 weeks for songs debuting in 2020.
- Short-lived chart runs rose sharply in the streaming era: only 3% of 1990–2004 debuts (`n = 4,940`) exited the Hot 100 within two weeks, compared with 43% of 2015–2020 debuts (`n = 3,042`), where roughly one in three lasted a single week.
- The flat 20-week upper quartile ceiling visible from the 1990s onward likely reflects Billboard's recurrent removal rule rather than listener behavior alone, motivating further rule and album-drop analysis in Milestone 3.

## Hosting
The project is hosted using GitHub Pages (https://bilgi-ie-421.github.io/ie421-2026-2027-1-termproject-byte-me/).
