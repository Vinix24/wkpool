"""Tournament simulation: group mechanics and probability sanity."""
import numpy as np
import pytest

from wkpool import schedule
from wkpool.config import DEFAULTS
from wkpool.sim import TournamentSim


class StubGoalModel:
    """Expected goals rise with rating edge — enough to drive the sim."""

    def lambdas(self, elo_home, elo_away, home_adv=0.0):
        diff = (elo_home + home_adv - elo_away) / 400.0
        return float(np.clip(1.35 * np.exp(0.6 * diff), 0.15, 4.5)), \
               float(np.clip(1.35 * np.exp(-0.6 * diff), 0.15, 4.5))


def make_sim(played=None, ratings=None, seed=42):
    weights = {**DEFAULTS, "simulation": {**DEFAULTS["simulation"],
                                          "n_sims": 300, "seed": seed}}
    if ratings is None:
        ratings = {t: 1500.0 for t in schedule.all_teams()}
    return TournamentSim(StubGoalModel(), ratings, weights, played or {})


def test_probabilities_are_coherent():
    df = make_sim().run(300)
    assert len(df) == 48
    assert abs(df["p_champion"].sum() - 1.0) < 1e-9
    assert abs(df["p_F"].sum() - 2.0) < 1e-9
    assert abs(df["p_R32"].sum() - 32.0) < 1e-9
    # survival is monotone: nobody reaches the final more often than the QF
    for r in df.itertuples(index=False):
        assert r.p_R32 >= r.p_R16 >= r.p_QF >= r.p_SF >= r.p_F >= r.p_champion


def test_stronger_team_wins_more():
    ratings = {t: 1500.0 for t in schedule.all_teams()}
    ratings["Spain"] = 2100.0
    ratings["Cape Verde"] = 1200.0
    df = make_sim(ratings=ratings).run(400).set_index("team")
    assert df.loc["Spain", "p_champion"] > 0.25
    assert df.loc["Spain", "p_R32"] > 0.95
    assert df.loc["Cape Verde", "p_champion"] < 0.02


def test_played_results_are_respected():
    # South Africa already thrashed Mexico 9-0 -> that result is in every sim
    played = {("Mexico", "South Africa"): (0, 9)}
    base = make_sim().run(400).set_index("team")
    cond = make_sim(played=played).run(400).set_index("team")
    assert cond.loc["South Africa", "p_R32"] > base.loc["South Africa", "p_R32"]
    assert cond.loc["Mexico", "p_R32"] < base.loc["Mexico", "p_R32"]


def test_group_ranking_tiebreakers():
    sim = make_sim(played={
        # Group A fully played: Mexico and South Korea both 9-... wait, craft:
        # Mexico beats everyone; SK and SA equal on points/gd/gf, SA won h2h.
        ("Mexico", "South Africa"): (2, 0),
        ("South Korea", "Czech Republic"): (3, 0),
        ("Mexico", "South Korea"): (1, 0),
        ("South Africa", "South Korea"): (1, 0),
        ("Czech Republic", "South Africa"): (0, 2),
        ("Czech Republic", "Mexico"): (0, 1),
    })
    rng = np.random.default_rng(0)
    ranked = sim._play_group("A", rng)
    # Mexico 9 pts; SA 6 pts (gd +4... 2-0,1-0,2-0 => gf 5 ga 1? recompute:
    # SA: lost 0-2 vs MEX, beat SK 1-0, beat CZE 2-0 -> 6 pts, gd +1+2-2=+1, gf 3
    # SK: beat CZE 3-0, lost 0-1 MEX, lost 0-1 SA -> 3 pts, gd 0, gf 3
    # CZE: 0 pts
    assert ranked == ["Mexico", "South Africa", "South Korea", "Czech Republic"]


def test_two_way_head_to_head_breaks_full_tie():
    # craft a full three-stat tie between two teams where h2h must decide
    sim = make_sim(played={
        ("Mexico", "South Africa"): (1, 0),       # MEX 3pts
        ("South Korea", "Czech Republic"): (1, 0),  # SK 3pts
        ("Mexico", "South Korea"): (0, 1),        # SK beats MEX -> both 1 win
        ("South Africa", "South Korea"): (1, 0),
        ("Czech Republic", "South Africa"): (1, 0),
        ("Czech Republic", "Mexico"): (0, 1),
    })
    rng = np.random.default_rng(0)
    ranked = sim._play_group("A", rng)
    # MEX: w SA 1-0, l SK 0-1, w CZE 1-0 -> 6 pts, gd +1, gf 2
    # SK:  w CZE 1-0, w MEX 1-0, l SA 0-1 -> 6 pts, gd +1, gf 2  (full tie!)
    # SK beat MEX head-to-head, so SK must rank above MEX
    assert ranked.index("South Korea") < ranked.index("Mexico")
