"""Download and load public match data.

Data is downloaded at runtime and cached under data/ (gitignored). Nothing
is redistributed with this repo — sources keep their own licenses.
"""
from __future__ import annotations

import datetime as dt

import pandas as pd
import requests

from .config import DATA_DIR, ensure_dirs
from . import schedule

RESULTS_URL = (
    "https://raw.githubusercontent.com/martj42/international_results/master/results.csv"
)
RESULTS_CSV = DATA_DIR / "results.csv"


def download(force: bool = False) -> None:
    """Fetch the latest international results (refreshed daily upstream)."""
    ensure_dirs()
    if RESULTS_CSV.exists() and not force:
        age = dt.datetime.now().timestamp() - RESULTS_CSV.stat().st_mtime
        if age < 6 * 3600:
            print(f"results.csv is {age/3600:.1f}h old, skipping download (use --force)")
            return
    resp = requests.get(RESULTS_URL, timeout=60)
    resp.raise_for_status()
    RESULTS_CSV.write_bytes(resp.content)
    print(f"downloaded {len(resp.content)//1024} KB -> {RESULTS_CSV}")


def load_results(with_fallback: bool = True) -> pd.DataFrame:
    if not RESULTS_CSV.exists():
        download()
    df = pd.read_csv(RESULTS_CSV)
    df["date"] = pd.to_datetime(df["date"])
    df = df.dropna(subset=["home_score", "away_score"]).copy()
    df["home_score"] = df["home_score"].astype(int)
    df["away_score"] = df["away_score"].astype(int)
    df = df.sort_values("date").reset_index(drop=True)

    missing = set(schedule.all_teams()) - set(df["home_team"]) - set(df["away_team"])
    if missing:
        raise ValueError(
            f"2026 squad names not found in dataset (naming drift?): {missing}"
        )

    if with_fallback:  # close the martj42 lag with a faster WC results feed
        from . import sources
        df = sources.merge_results(df, sources.fetch_results_fallback())
    return df


def world_cup_2026_results(df: pd.DataFrame) -> pd.DataFrame:
    """Played WC2026 matches: used to freeze group standings & score predictions."""
    mask = (df["date"] >= "2026-06-11") & (df["tournament"] == "FIFA World Cup")
    return df[mask]
