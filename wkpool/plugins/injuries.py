"""Injury/availability penalty from structured news files.

Reads data/news/<team>.json as produced by `wkpool news` (Perplexity) — or
by hand, or by your own scraper; the file format is the contract, not the
fetcher. Stale files (older than injuries.max_news_age_days) are ignored.
"""
from __future__ import annotations

import datetime as dt
import json

from ..config import NEWS_DIR


def _slug(team: str) -> str:
    return team.lower().replace(" ", "_")


class InjuryPlugin:
    name = "injuries"

    def adjustments(self, teams: list[str], weights: dict) -> dict[str, float]:
        cfg = weights["injuries"]
        out: dict[str, float] = {}
        if not NEWS_DIR.is_dir():
            return out
        today = dt.date.today()
        for team in teams:
            path = NEWS_DIR / f"{_slug(team)}.json"
            if not path.exists():
                continue
            try:
                report = json.loads(path.read_text())
                as_of = dt.date.fromisoformat(report.get("as_of", "1970-01-01"))
            except (json.JSONDecodeError, ValueError):
                continue
            if (today - as_of).days > int(cfg["max_news_age_days"]):
                continue
            penalty = 0.0
            for inj in report.get("injuries", []):
                if inj.get("status") == "out":
                    penalty += float(cfg["points_per_out"])
                elif inj.get("status") == "doubtful":
                    penalty += float(cfg["points_per_doubtful"])
            penalty += float(cfg["points_per_out"]) * len(report.get("suspensions", []))
            if penalty:
                out[team] = -penalty
        return out
