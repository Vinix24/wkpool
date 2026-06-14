"""Optional extra data sources, all key-gated and degrading gracefully:

- football-data.org: a faster World Cup results feed than the martj42 CSV,
  to close the ~1-2 day lag. Key: FOOTBALL_DATA_API_KEY.
- The Odds API: outright (winner) odds -> data/odds/outright.json for the
  bookmaker-consensus plugin. Key: ODDS_API_KEY.

Without keys these are no-ops and the model runs on its public sources.
"""
from __future__ import annotations

import datetime as dt
import json
import os

import pandas as pd
import requests

from . import schedule
from .config import ODDS_DIR, ensure_dirs

FOOTBALL_DATA_URL = "https://api.football-data.org/v4/competitions/WC/matches"
ODDS_API_URL = ("https://api.the-odds-api.com/v4/sports/"
                "soccer_fifa_world_cup_winner/odds")

# football-data.org names -> martj42/schedule names
_FD_ALIASES = {
    "USA": "United States",
    "Republic of Ireland": "Ireland",
    "Korea Republic": "South Korea",
    "IR Iran": "Iran",
    "Côte d'Ivoire": "Ivory Coast",
    "Czechia": "Czech Republic",
    "Türkiye": "Turkey",
    "Cabo Verde": "Cape Verde",
}


def _canon(name: str) -> str:
    name = _FD_ALIASES.get(name, name)
    return name if name in set(schedule.all_teams()) else name


def fetch_results_fallback() -> pd.DataFrame | None:
    """Recent WC2026 results from football-data.org (faster than martj42).

    Returns a DataFrame with the same columns as the martj42 results, or None
    if no key is set or the call fails. Only finished matches are returned.
    """
    key = os.environ.get("FOOTBALL_DATA_API_KEY", "").strip()
    if not key:
        return None
    try:
        resp = requests.get(FOOTBALL_DATA_URL, headers={"X-Auth-Token": key},
                            params={"status": "FINISHED"}, timeout=60)
        resp.raise_for_status()
        matches = resp.json().get("matches", [])
    except (requests.RequestException, ValueError):
        return None

    rows = []
    for m in matches:
        score = m.get("score", {}).get("fullTime", {})
        if score.get("home") is None or score.get("away") is None:
            continue
        rows.append({
            "date": m["utcDate"][:10],
            "home_team": _canon(m["homeTeam"]["name"]),
            "away_team": _canon(m["awayTeam"]["name"]),
            "home_score": int(score["home"]),
            "away_score": int(score["away"]),
            "tournament": "FIFA World Cup",
            "neutral": True,
        })
    if not rows:
        return None
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"])
    return df


def merge_results(primary: pd.DataFrame, extra: pd.DataFrame | None) -> pd.DataFrame:
    """Add any WC matches from `extra` that `primary` does not have yet."""
    if extra is None or extra.empty:
        return primary
    have = {(r.home_team, r.away_team) for r in primary.itertuples(index=False)}
    new = extra[[(h, a) not in have and (a, h) not in have
                 for h, a in zip(extra["home_team"], extra["away_team"])]]
    if new.empty:
        return primary
    print(f"  +{len(new)} WC result(s) from football-data.org not yet in martj42")
    return pd.concat([primary, new], ignore_index=True).sort_values("date").reset_index(drop=True)


def fetch_outright_odds() -> int:
    """Fetch winner odds -> data/odds/outright.json. Returns teams written."""
    key = os.environ.get("ODDS_API_KEY", "").strip()
    if not key:
        print("ODDS_API_KEY not set — skipping odds fetch (odds plugin stays off)")
        return 0
    try:
        resp = requests.get(ODDS_API_URL, params={
            "apiKey": key, "regions": "eu,uk", "oddsFormat": "decimal"}, timeout=60)
        resp.raise_for_status()
        data = resp.json()
    except (requests.RequestException, ValueError) as exc:
        print(f"odds fetch failed ({exc})")
        return 0

    # consensus = median decimal odds across books per team
    per_team: dict[str, list[float]] = {}
    for event in data if isinstance(data, list) else []:
        for book in event.get("bookmakers", []):
            for market in book.get("markets", []):
                if market.get("key") != "outrights":
                    continue
                for oc in market.get("outcomes", []):
                    name = _canon(oc.get("name", ""))
                    price = oc.get("price")
                    if name in set(schedule.all_teams()) and isinstance(price, (int, float)):
                        per_team.setdefault(name, []).append(float(price))
    if not per_team:
        print("odds fetch returned no usable outrights")
        return 0
    consensus = {t: sorted(v)[len(v) // 2] for t, v in per_team.items()}
    ensure_dirs()
    (ODDS_DIR / "outright.json").write_text(
        json.dumps(consensus, indent=2, ensure_ascii=False))
    print(f"wrote outright odds for {len(consensus)} teams")
    return len(consensus)
