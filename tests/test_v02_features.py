"""v0.2: injury persistence, penalty cap, odds plugin, results merge."""
import datetime as dt
import json

import pandas as pd

from wkpool.config import DEFAULTS
from wkpool.news import merge_persisted
from wkpool.plugins.injuries import InjuryPlugin, _slug
from wkpool import sources


# ---------- injury persistence ----------

def test_persist_carries_dropped_injury_forward():
    today = dt.date(2026, 6, 14)
    old = {"injuries": [{"player": "Rodrygo", "status": "out", "first_seen": "2026-06-13"}]}
    new = {"injuries": []}  # fresh scrape missed Rodrygo
    merged = merge_persisted(old, new, today, persist_days=3)
    names = {i["player"]: i for i in merged["injuries"]}
    assert "Rodrygo" in names
    assert names["Rodrygo"]["persisted"] is True


def test_persist_drops_when_returned_reported():
    today = dt.date(2026, 6, 14)
    old = {"injuries": [{"player": "Neymar", "status": "out", "first_seen": "2026-06-13"}]}
    new = {"injuries": [{"player": "Neymar", "status": "returned"}]}
    merged = merge_persisted(old, new, today, persist_days=3)
    # returned today -> not carried as out
    assert all(i["player"] != "Neymar" or i["status"] == "returned"
               for i in merged["injuries"])


def test_persist_expires_after_window():
    today = dt.date(2026, 6, 14)
    old = {"injuries": [{"player": "OldKnock", "status": "doubtful", "first_seen": "2026-06-01"}]}
    merged = merge_persisted(old, {"injuries": []}, today, persist_days=3)
    assert merged["injuries"] == []


def test_fresh_report_wins_over_old():
    today = dt.date(2026, 6, 14)
    old = {"injuries": [{"player": "X", "status": "doubtful", "first_seen": "2026-06-13"}]}
    new = {"injuries": [{"player": "X", "status": "out"}]}
    merged = merge_persisted(old, new, today, persist_days=3)
    x = [i for i in merged["injuries"] if i["player"] == "X"][0]
    assert x["status"] == "out"
    assert x["first_seen"] == "2026-06-14"  # not carried, it's in the fresh report


# ---------- penalty cap ----------

def test_penalty_cap(tmp_path, monkeypatch):
    import wkpool.plugins.injuries as inj_mod
    monkeypatch.setattr(inj_mod, "NEWS_DIR", tmp_path)
    report = {"team": "Brazil", "as_of": dt.date.today().isoformat(),
              "injuries": [{"player": f"P{i}", "status": "out"} for i in range(8)]}
    (tmp_path / f"{_slug('Brazil')}.json").write_text(json.dumps(report))
    cfg = {**DEFAULTS["injuries"], "max_team_penalty": 30}
    adj = InjuryPlugin().adjustments(["Brazil"], {"injuries": cfg})
    # 8*12 = 96 uncapped -> capped at 30
    assert adj == {"Brazil": -30.0}


# ---------- odds plugin ----------

def test_odds_plugin_nudges_toward_market(tmp_path, monkeypatch):
    import wkpool.plugins.odds as odds_mod
    monkeypatch.setattr(odds_mod, "OUTRIGHT", tmp_path / "outright.json")
    (tmp_path / "outright.json").write_text(json.dumps({
        "Spain": 5.0, "Argentina": 7.0, "France": 8.0, "Brazil": 9.0,
        "Cape Verde": 500.0}))
    weights = {"odds": {"blend": 60}}
    adj = odds_mod.OddsPlugin().adjustments(
        ["Spain", "Argentina", "France", "Brazil", "Cape Verde"], weights)
    # favourite gets a positive nudge, the longshot a negative one
    assert adj["Spain"] > 0 > adj["Cape Verde"]
    assert adj["Spain"] > adj["Brazil"]


def test_odds_plugin_silent_without_file(tmp_path, monkeypatch):
    import wkpool.plugins.odds as odds_mod
    monkeypatch.setattr(odds_mod, "OUTRIGHT", tmp_path / "nope.json")
    assert odds_mod.OddsPlugin().adjustments(["Spain"], {"odds": {"blend": 60}}) == {}


# ---------- results merge ----------

def test_merge_results_adds_missing_only():
    primary = pd.DataFrame([{"date": pd.Timestamp("2026-06-11"),
                             "home_team": "Mexico", "away_team": "South Africa",
                             "home_score": 2, "away_score": 0,
                             "tournament": "FIFA World Cup", "neutral": True}])
    extra = pd.DataFrame([
        {"date": pd.Timestamp("2026-06-11"), "home_team": "Mexico",
         "away_team": "South Africa", "home_score": 2, "away_score": 0,
         "tournament": "FIFA World Cup", "neutral": True},  # dup
        {"date": pd.Timestamp("2026-06-13"), "home_team": "Brazil",
         "away_team": "Morocco", "home_score": 1, "away_score": 1,
         "tournament": "FIFA World Cup", "neutral": True},  # new
    ])
    merged = sources.merge_results(primary, extra)
    assert len(merged) == 2
    assert ("Brazil", "Morocco") in {(r.home_team, r.away_team)
                                     for r in merged.itertuples(index=False)}
