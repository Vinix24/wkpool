"""Elo rating engine (eloratings.net conventions) + form tracking.

One chronological pass over the full match history produces:
  - current ratings per team
  - leakage-free pre-match features for every historical match
    (ratings and form as they stood *before* kickoff)

Both the classifier and the goal model train on these features, which is
what keeps the whole pipeline causally honest.
"""
from __future__ import annotations

import math

import numpy as np
import pandas as pd

START_RATING = 1500.0


def k_factor(tournament: str, ratings_cfg: dict) -> float:
    t = tournament.lower()
    if t == "fifa world cup":
        return ratings_cfg["k_world_cup"]
    if "qualification" in t:
        return ratings_cfg["k_qualifier"]
    if any(name in t for name in (
            "uefa euro", "copa américa", "copa america", "african cup",
            "africa cup", "afc asian cup", "gold cup", "confederations")):
        return ratings_cfg["k_continental"]
    if "nations league" in t:
        return ratings_cfg["k_nations_league"]
    return ratings_cfg["k_friendly"]


def expected_score(r_home: float, r_away: float, home_adv: float) -> float:
    return 1.0 / (1.0 + 10 ** (-(r_home + home_adv - r_away) / 400.0))


def goal_diff_multiplier(diff: int) -> float:
    """eloratings.net margin-of-victory scaling."""
    d = abs(diff)
    if d <= 1:
        return 1.0
    if d == 2:
        return 1.5
    return (11.0 + d) / 8.0


class EloEngine:
    def __init__(self, weights: dict):
        self.cfg = weights["ratings"]
        self.half_life = float(weights["form"]["half_life_days"])
        self.ratings: dict[str, float] = {}
        # form: exponentially decayed points-per-game (and last-seen date)
        self._form_num: dict[str, float] = {}
        self._form_den: dict[str, float] = {}
        self._last_date: dict[str, pd.Timestamp] = {}

    def rating(self, team: str) -> float:
        return self.ratings.get(team, START_RATING)

    def form(self, team: str, at_date: pd.Timestamp | None = None) -> float:
        """Decayed points per game in [0, 3]; 1.4 ≈ neutral before any match."""
        den = self._form_den.get(team, 0.0)
        if den <= 0:
            return 1.4
        num, last = self._form_num[team], self._last_date[team]
        if at_date is not None and at_date > last:
            decay = 0.5 ** ((at_date - last).days / self.half_life)
            num, den = num * decay, den * decay
            if den <= 1e-9:
                return 1.4
        return num / den

    def _bump_form(self, team: str, points: float, date: pd.Timestamp) -> None:
        last = self._last_date.get(team)
        decay = 0.5 ** ((date - last).days / self.half_life) if last is not None else 1.0
        self._form_num[team] = self._form_num.get(team, 0.0) * decay + points
        self._form_den[team] = self._form_den.get(team, 0.0) * decay + 1.0
        self._last_date[team] = date

    def process(self, df: pd.DataFrame) -> pd.DataFrame:
        """Replay history chronologically; return per-match pre-kickoff features."""
        home_adv = float(self.cfg["home_advantage"])
        rows = []
        for r in df.itertuples(index=False):
            rh, ra = self.rating(r.home_team), self.rating(r.away_team)
            adv = 0.0 if r.neutral else home_adv
            fh = self.form(r.home_team, r.date)
            fa = self.form(r.away_team, r.date)
            k = k_factor(r.tournament, self.cfg)
            rows.append((rh, ra, adv, fh, fa, k))

            # update ratings
            exp_h = expected_score(rh, ra, adv)
            if r.home_score > r.away_score:
                actual, ph, pa = 1.0, 3.0, 0.0
            elif r.home_score < r.away_score:
                actual, ph, pa = 0.0, 0.0, 3.0
            else:
                actual, ph, pa = 0.5, 1.0, 1.0
            delta = k * goal_diff_multiplier(r.home_score - r.away_score) * (actual - exp_h)
            self.ratings[r.home_team] = rh + delta
            self.ratings[r.away_team] = ra - delta
            self._bump_form(r.home_team, ph, r.date)
            self._bump_form(r.away_team, pa, r.date)

        feats = pd.DataFrame(
            rows, columns=["elo_home", "elo_away", "home_adv", "form_home", "form_away", "k"]
        )
        return pd.concat([df.reset_index(drop=True), feats], axis=1)

    def snapshot(self, teams: list[str], at_date: pd.Timestamp) -> pd.DataFrame:
        return pd.DataFrame({
            "team": teams,
            "elo": [self.rating(t) for t in teams],
            "form": [self.form(t, at_date) for t in teams],
        }).sort_values("elo", ascending=False).reset_index(drop=True)


def time_decay_weights(dates: pd.Series, half_life_days: float,
                       reference: pd.Timestamp | None = None) -> np.ndarray:
    ref = reference or dates.max()
    age = (ref - dates).dt.days.to_numpy(dtype=float)
    return np.power(0.5, age / half_life_days)
