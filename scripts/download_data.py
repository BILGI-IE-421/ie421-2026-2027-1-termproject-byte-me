"""Download both Kaggle datasets through the Kaggle API (reads ~/.kaggle/kaggle.json
or KAGGLE_USERNAME / KAGGLE_KEY). Usage: python src/download_data.py [--skip-spotify] [--force]"""
import argparse
import sys

from common import RAW

DATASETS = {
    "billboard": "dhruvildave/billboard-the-hot-100-songs",
    "spotify": "asaniczka/top-spotify-songs-in-73-countries-daily-updated",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--skip-spotify", action="store_true", help="the Spotify file is several GB")
    ap.add_argument("--force", action="store_true", help="re-download even if files exist")
    args = ap.parse_args()

    try:
        from kaggle.api.kaggle_api_extended import KaggleApi
        api = KaggleApi()
        api.authenticate()
    except Exception as exc:  # missing package or credentials
        sys.exit(f"Kaggle API not available: {exc}\nInstall `kaggle` and add your API token.")

    for name, slug in DATASETS.items():
        if name == "spotify" and args.skip_spotify:
            continue
        out = RAW / name
        out.mkdir(parents=True, exist_ok=True)
        if any(out.glob("*.csv")) and not args.force:
            print(f"[skip] {name}: already in {out}")
            continue
        print(f"[download] {slug} -> {out}")
        api.dataset_download_files(slug, path=str(out), unzip=True, quiet=False)
    print("Expected files: data/raw/billboard/charts.csv and "
          "data/raw/spotify/universal_top_spotify_songs.csv")


if __name__ == "__main__":
    main()
