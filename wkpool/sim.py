"""Monte Carlo tournament simulation through the official 2026 bracket.

Design follows the verified Groll/Zeileis approach: expected goals per side
become Poisson intensities, the whole tournament is simulated n_sims times,
extra time scales intensities by `extra_time_factor`, remaining ties go to
(slightly Elo-informed) penalties.

Recalibration is structural: group matches that have actually been played
enter every simulation as fixed results, so each daily run automatically
conditions the whole tournament on everything known so far. Once a group is
fully played, its qualifiers are effectively frozen.

Known approximations (documented, deliberate):
- Group tiebreak: points, goal difference, goals for, then head-to-head
  result for two-way ties, then random. FIFA adds fair-play points and
  drawing of lots; those are noise-level and unknowable in advance.
- Third-place slot allocation uses constraint-respecting deterministic
  matching; FIFA's exact priority order between equally valid assignments
  is not public.
- Penalty shootouts: 50% +/- a small Elo nudge (capped at 60/40).
"""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import schedule
from .config import OUTPUT_DIR
from .model import GoalModel


class TournamentSim:
    def __init__(self, goal_model: GoalModel, ratings: dict[str, float],
                 weights: dict, played: dict[tuple[str, str], tuple[int, int]]):
        self.goals = goal_model
        self.ratings = ratings
        self.cfg = weights["simulation"]
        self.home_adv = float(weights["ratings"]["home_advantage"])
        self.played = played
        self._lam_cache: dict[tuple[str, str], tuple[float, float]] = {}

    # ---------- match level ----------

    def _advantage(self, home: str, away: str) -> float:
        adv = 0.0
        if home in schedule.HOSTS:
            adv += self.home_adv
        if away in schedule.HOSTS:
            adv -= self.home_adv
        return adv

    def _lambdas(self, home: str, away: str) -> tuple[float, float]:
        key = (home, away)
        if key not in self._lam_cache:
            self._lam_cache[key] = self.goals.lambdas(
                self.ratings[home], self.ratings[away],
                home_adv=self._advantage(home, away))
        return self._lam_cache[key]

    def _sample_goals(self, home: str, away: str, rng, factor: float = 1.0,
                      cap: int | None = None) -> tuple[int, int]:
        lh, la = self._lambdas(home, away)
        cap = cap or int(self.cfg["max_goals"])
        return (min(int(rng.poisson(lh * factor)), cap),
                min(int(rng.poisson(la * factor)), cap))

    def _ko_winner(self, home: str, away: str, rng) -> str:
        hg, ag = self._sample_goals(home, away, rng)
        if hg != ag:
            return home if hg > ag else away
        et = float(self.cfg["extra_time_factor"])
        hg, ag = self._sample_goals(home, away, rng, factor=et)
        if hg != ag:
            return home if hg > ag else away
        diff = np.clip(self.ratings[home] - self.ratings[away], -400, 400)
        p_home = 0.5 + diff / 4000.0
        return home if rng.random() < p_home else away

    # ---------- group stage ----------

    def _play_group(self, letter: str, rng) -> list[str]:
        """Return the group's teams ranked 1st..4th."""
        teams = schedule.GROUPS[letter]
        pts = {t: 0 for t in teams}
        gd = {t: 0 for t in teams}
        gf = {t: 0 for t in teams}
        h2h: dict[tuple[str, str], int] = {}  # (a, b) -> sign of a's result vs b

        for _, home, away in schedule.fixtures_of_group(letter):
            if (home, away) in self.played:
                hg, ag = self.played[(home, away)]
            elif (away, home) in self.played:
                ag, hg = self.played[(away, home)]
            else:
                hg, ag = self._sample_goals(home, away, rng)
            gf[home] += hg; gf[away] += ag
            gd[home] += hg - ag; gd[away] += ag - hg
            if hg > ag:
                pts[home] += 3
            elif hg < ag:
                pts[away] += 3
            else:
                pts[home] += 1; pts[away] += 1
            sign = int(np.sign(hg - ag))
            h2h[(home, away)] = sign
            h2h[(away, home)] = -sign

        keyed = sorted(teams, key=lambda t: (-pts[t], -gd[t], -gf[t], rng.random()))
        # two-way head-to-head correction on full ties
        for i in range(3):
            a, b = keyed[i], keyed[i + 1]
            if (pts[a], gd[a], gf[a]) == (pts[b], gd[b], gf[b]) and h2h.get((b, a), 0) > 0:
                keyed[i], keyed[i + 1] = b, a
        self._last_group_stats = {t: (pts[t], gd[t], gf[t]) for t in teams}
        return keyed

    # ---------- tournament ----------

    def run(self, n_sims: int | None = None) -> pd.DataFrame:
        n_sims = n_sims or int(self.cfg["n_sims"])
        rng = np.random.default_rng(self.cfg.get("seed"))
        teams = schedule.all_teams()
        rounds = ["R32", "R16", "QF", "SF", "F", "champion"]
        counts = {t: dict.fromkeys(rounds, 0) for t in teams}

        for _ in range(n_sims):
            winners: dict[str, str] = {}
            runners: dict[str, str] = {}
            third_stats: list[tuple[str, str, tuple]] = []  # (group, team, stats)
            for letter in schedule.GROUP_LETTERS:
                ranked = self._play_group(letter, rng)
                winners[letter], runners[letter] = ranked[0], ranked[1]
                third_stats.append((letter, ranked[2], self._last_group_stats[ranked[2]]))

            third_stats.sort(key=lambda x: (-x[2][0], -x[2][1], -x[2][2], rng.random()))
            qualified_thirds = [g for g, _, _ in third_stats[:8]]
            third_team = {g: t for g, t, _ in third_stats[:8]}
            allocation = schedule.allocate_thirds(qualified_thirds)
            if allocation is None:  # cannot happen with FIFA's slot design
                slots = [m["away"][1] for m in schedule.ROUND_OF_32 if m["away"][0] == "3"]
                allocation = dict(zip(slots, qualified_thirds))

            def resolve(slot: tuple[str, str]) -> str:
                kind, ref = slot
                if kind == "1":
                    return winners[ref]
                if kind == "2":
                    return runners[ref]
                return third_team[allocation[ref]]

            match_winner: dict[int, str] = {}
            r32_qualifiers = set()
            for m in schedule.ROUND_OF_32:
                home, away = resolve(m["home"]), resolve(m["away"])
                r32_qualifiers.update((home, away))
                match_winner[m["match"]] = self._ko_winner(home, away, rng)
            for t in r32_qualifiers:
                counts[t]["R32"] += 1

            for round_name, tree in (("R16", schedule.ROUND_OF_16),
                                     ("QF", schedule.QUARTER_FINALS),
                                     ("SF", schedule.SEMI_FINALS)):
                for match_no, (h_ref, a_ref) in tree.items():
                    home, away = match_winner[h_ref], match_winner[a_ref]
                    counts[home][round_name] += 1
                    counts[away][round_name] += 1
                    match_winner[match_no] = self._ko_winner(home, away, rng)

            h_ref, a_ref = schedule.FINAL
            home, away = match_winner[h_ref], match_winner[a_ref]
            counts[home]["F"] += 1
            counts[away]["F"] += 1
            counts[self._ko_winner(home, away, rng)]["champion"] += 1

        rows = [{"team": t, "group": schedule.group_of(t), "elo": self.ratings[t],
                 **{f"p_{r}": counts[t][r] / n_sims for r in rounds}}
                for t in teams]
        df = (pd.DataFrame(rows)
              .sort_values(["p_champion", "p_F", "elo"], ascending=False)
              .reset_index(drop=True))
        return df

    def save(self, df: pd.DataFrame, n_sims: int) -> None:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        payload = {"n_sims": n_sims, "results": df.to_dict(orient="records")}
        (OUTPUT_DIR / "simulation.json").write_text(json.dumps(payload, indent=2,
                                                               ensure_ascii=False))
