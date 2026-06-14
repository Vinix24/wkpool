"""Bookmaker-consensus plugin — the strongest single covariate in the
literature (Groll/Zeileis), shipped OFF by default (weight 0.0).

Reads data/odds/outright.json: {"Spain": 5.5, "Argentina": 7.0, ...}
(decimal odds to win the tournament). The plugin removes the bookmaker
margin, converts to implied championship probabilities, turns those into a
relative strength z-score, and nudges each team's Elo rating toward the
market by up to `odds.blend` points. So a market view flows coherently into
both match probabilities and the tournament simulation.

Populate the file by hand, with your own scraper, or with `wkpool odds`
(The Odds API, key ODDS_API_KEY). The file format is the contract.
"""
from __future__ import annotations

import json
import math

from ..config import ODDS_DIR

OUTRIGHT = ODDS_DIR / "outright.json"


class OddsPlugin:
    name = "odds"

    def adjustments(self, teams: list[str], weights: dict) -> dict[str, float]:
        if not OUTRIGHT.exists():
            return {}
        try:
            raw = json.loads(OUTRIGHT.read_text())
        except json.JSONDecodeError:
            return {}
        odds = {t: float(v) for t, v in raw.items()
                if t in teams and isinstance(v, (int, float)) and float(v) > 1.0}
        if len(odds) < 4:
            return {}

        # decimal odds -> raw implied prob; normalise to strip the overround
        implied = {t: 1.0 / o for t, o in odds.items()}
        total = sum(implied.values())
        implied = {t: p / total for t, p in implied.items()}

        # log-prob as a strength scale, standardised across the rated teams
        logp = {t: math.log(p) for t, p in implied.items()}
        mean = sum(logp.values()) / len(logp)
        var = sum((v - mean) ** 2 for v in logp.values()) / len(logp)
        std = math.sqrt(var) or 1.0

        blend = float(weights.get("odds", {}).get("blend", 0))
        # nudge proportional to how far above/below the field the market rates a team
        return {t: blend * ((logp[t] - mean) / std) for t in odds}
