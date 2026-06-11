"""Elo engine math."""
import pandas as pd

from wkpool.config import DEFAULTS
from wkpool.elo import EloEngine, expected_score, goal_diff_multiplier, k_factor


def test_expected_score_symmetry():
    assert abs(expected_score(1500, 1500, 0) - 0.5) < 1e-9
    p = expected_score(1700, 1500, 0)
    q = expected_score(1500, 1700, 0)
    assert abs(p + q - 1.0) < 1e-9
    assert p > 0.7


def test_home_advantage_shifts_expectation():
    assert expected_score(1500, 1500, 100) > 0.6


def test_goal_diff_multiplier():
    assert goal_diff_multiplier(0) == 1.0
    assert goal_diff_multiplier(1) == 1.0
    assert goal_diff_multiplier(-2) == 1.5
    assert goal_diff_multiplier(3) == 1.75
    assert goal_diff_multiplier(5) == 2.0


def test_k_factors():
    cfg = DEFAULTS["ratings"]
    assert k_factor("FIFA World Cup", cfg) == 60
    assert k_factor("FIFA World Cup qualification", cfg) == 40
    assert k_factor("UEFA Euro", cfg) == 50
    assert k_factor("Friendly", cfg) == 20


def _matches(rows):
    df = pd.DataFrame(rows, columns=["date", "home_team", "away_team",
                                     "home_score", "away_score", "tournament",
                                     "neutral"])
    df["date"] = pd.to_datetime(df["date"])
    return df


def test_ratings_are_zero_sum_and_winner_gains():
    engine = EloEngine(DEFAULTS)
    hist = engine.process(_matches([
        ("2025-01-01", "Alandia", "Borduria", 3, 0, "Friendly", True),
    ]))
    assert engine.rating("Alandia") > 1500 > engine.rating("Borduria")
    total = engine.rating("Alandia") + engine.rating("Borduria")
    assert abs(total - 3000) < 1e-9
    # pre-match features recorded before the update
    assert hist.iloc[0]["elo_home"] == 1500


def test_form_tracks_recent_results():
    engine = EloEngine(DEFAULTS)
    engine.process(_matches([
        ("2025-01-01", "Alandia", "Borduria", 2, 0, "Friendly", True),
        ("2025-02-01", "Alandia", "Borduria", 1, 0, "Friendly", True),
        ("2025-03-01", "Alandia", "Borduria", 0, 0, "Friendly", True),
    ]))
    at = pd.Timestamp("2025-03-02")
    assert engine.form("Alandia", at) > 2.0
    assert engine.form("Borduria", at) < 1.0
    assert engine.form("Unknownia", at) == 1.4
