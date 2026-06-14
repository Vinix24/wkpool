"""Per-match predictions and the PREDICTIONS.md report.

Every run logs its predictions for unplayed fixtures to output/history.jsonl
*before* results exist, which is what makes later scoring (wkpool score)
leakage-free by construction.
"""
from __future__ import annotations

import datetime as dt
import json
import math

import numpy as np
import pandas as pd

from . import schedule
from .config import OUTPUT_DIR, ROOT
from .model import GoalModel, OutcomeModel

HISTORY = OUTPUT_DIR / "history.jsonl"
PREDICTIONS_MD = ROOT / "PREDICTIONS.md"


def likely_score(goal_model: GoalModel, ratings: dict,
                 home: str, away: str, adv: float, max_goals: int = 8) -> tuple[int, int]:
    lh, la = goal_model.lambdas(ratings[home], ratings[away], home_adv=adv)
    g = np.arange(max_goals + 1)
    # independent Poisson pmfs
    fact = np.array([math.factorial(int(i)) for i in g], dtype=float)
    ph = np.exp(-lh) * lh ** g / fact
    pa = np.exp(-la) * la ** g / fact
    matrix = np.outer(ph, pa)
    idx = np.unravel_index(matrix.argmax(), matrix.shape)
    return int(idx[0]), int(idx[1])


def _advantage(home: str, away: str, home_adv: float) -> float:
    adv = 0.0
    if home in schedule.HOSTS:
        adv += home_adv
    if away in schedule.HOSTS:
        adv -= home_adv
    return adv


def predict_remaining(outcome: OutcomeModel, goal_model: GoalModel,
                      ratings: dict[str, float], forms: dict[str, float],
                      weights: dict,
                      played: dict[tuple[str, str], tuple[int, int]]) -> pd.DataFrame:
    home_adv = float(weights["ratings"]["home_advantage"])
    rows = []
    for date, home, away in schedule.GROUP_FIXTURES:
        if (home, away) in played or (away, home) in played:
            continue
        adv = _advantage(home, away, home_adv)
        p = outcome.predict_match(ratings[home], ratings[away],
                                  forms[home], forms[away],
                                  importance=60.0, neutral=(adv == 0.0),
                                  home_adv=adv)
        hg, ag = likely_score(goal_model, ratings, home, away, adv)
        rows.append({"date": date, "group": schedule.group_of(home),
                     "home": home, "away": away,
                     "p_home": round(float(p[0]), 4),
                     "p_draw": round(float(p[1]), 4),
                     "p_away": round(float(p[2]), 4),
                     "likely_score": f"{hg}-{ag}"})
    return pd.DataFrame(rows)


def log_history(preds: pd.DataFrame) -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().isoformat(timespec="seconds")
    with open(HISTORY, "a") as f:
        for row in preds.to_dict(orient="records"):
            f.write(json.dumps({"generated_at": stamp, **row}, ensure_ascii=False) + "\n")


def score_history(results_2026: pd.DataFrame) -> dict | None:
    """RPS/accuracy of the latest pre-match prediction for each played match."""
    if not HISTORY.exists():
        return None
    latest: dict[tuple[str, str], dict] = {}
    for line in HISTORY.read_text().splitlines():
        rec = json.loads(line)
        latest[(rec["home"], rec["away"])] = rec  # later lines overwrite

    rps_terms, hits, n = [], 0, 0
    for r in results_2026.itertuples(index=False):
        rec = latest.get((r.home_team, r.away_team)) or latest.get((r.away_team, r.home_team))
        if rec is None:
            continue
        # probs in result orientation: [home win, draw, away win]
        if rec["home"] == r.home_team:
            probs = [rec["p_home"], rec["p_draw"], rec["p_away"]]
        else:  # prediction stored with teams swapped vs. the result
            probs = [rec["p_away"], rec["p_draw"], rec["p_home"]]
        diff = r.home_score - r.away_score
        outcome_idx = 0 if diff > 0 else (1 if diff == 0 else 2)
        cum_p = np.cumsum(probs)
        cum_o = np.cumsum([1 if i == outcome_idx else 0 for i in range(3)])
        rps_terms.append(float(np.sum((cum_p - cum_o)[:2] ** 2) / 2))
        hits += int(int(np.argmax(probs)) == outcome_idx)
        n += 1
    if n == 0:
        return None
    return {"matches_scored": n, "accuracy": hits / n, "rps": sum(rps_terms) / n}


def write_report(preds: pd.DataFrame, sim_df: pd.DataFrame | None,
                 metrics: dict, score: dict | None) -> None:
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        "# WK 2026 — Predictions",
        "",
        f"_Generated {now} by [wkpool](https://github.com/Vinix24/world-cup-2026-predictor). "
        "Probabilities are isotonic-calibrated; weights in `weights.yaml`._",
        "",
    ]
    if metrics:
        lines += [f"Model holdout (since {metrics.get('holdout_since', '?')}): "
                  f"**{metrics.get('accuracy', 0):.1%} accuracy**, "
                  f"RPS {metrics.get('rps', 0):.4f} "
                  f"on {metrics.get('holdout_matches', 0)} matches.", ""]
    if score:
        lines += [f"Tournament so far: **{score['accuracy']:.0%}** of "
                  f"{score['matches_scored']} scored matches correct, "
                  f"RPS {score['rps']:.4f}.", ""]

    if sim_df is not None:
        lines += ["## Tournament outlook", "",
                  "| Team | Group | P(R16) | P(QF) | P(SF) | P(final) | P(champion) |",
                  "|---|---|---|---|---|---|---|"]
        for r in sim_df.head(12).itertuples(index=False):
            lines.append(f"| {r.team} | {r.group} | {r.p_R16:.1%} | {r.p_QF:.1%} "
                         f"| {r.p_SF:.1%} | {r.p_F:.1%} | **{r.p_champion:.1%}** |")
        lines.append("")

    lines += ["## Upcoming group matches", "",
              "| Date | Grp | Match | P(1) | P(X) | P(2) | Likely score |",
              "|---|---|---|---|---|---|---|"]
    for r in preds.itertuples(index=False):
        lines.append(f"| {r.date} | {r.group} | {r.home} – {r.away} "
                     f"| {r.p_home:.0%} | {r.p_draw:.0%} | {r.p_away:.0%} "
                     f"| {r.likely_score} |")
    lines.append("")
    PREDICTIONS_MD.write_text("\n".join(lines))
    print(f"wrote {PREDICTIONS_MD}")
