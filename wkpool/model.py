"""Match models.

Two models, one shared rating foundation (the verified Groll/Zeileis design):

1. Outcome classifier: gradient boosting on rating/form differences,
   isotonic-calibrated -> honest W/D/L probabilities per match.
2. Goal model: Poisson regression -> expected goals per side, which drives
   score sampling in the Monte Carlo tournament simulation.

Calibration is re-fitted on every train() call, so user weight changes can
never leave stale, distorted probabilities behind.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from sklearn.calibration import CalibratedClassifierCV
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.linear_model import PoissonRegressor

from .elo import time_decay_weights

FEATURES = ["elo_diff", "form_diff", "importance", "neutral_flag"]
LAMBDA_MIN, LAMBDA_MAX = 0.15, 4.5


def build_training_frame(hist: pd.DataFrame, train_since: str) -> pd.DataFrame:
    df = hist[hist["date"] >= train_since].copy()
    df["elo_diff"] = (df["elo_home"] + df["home_adv"]) - df["elo_away"]
    df["form_diff"] = df["form_home"] - df["form_away"]
    df["importance"] = df["k"]
    df["neutral_flag"] = df["neutral"].astype(int)
    df["outcome"] = np.sign(df["home_score"] - df["away_score"]).astype(int)  # 1/0/-1
    return df


def ranked_probability_score(probs: np.ndarray, outcome: np.ndarray) -> float:
    """RPS for ordered outcomes [home win, draw, away win]; lower is better."""
    onehot = np.zeros_like(probs)
    onehot[np.arange(len(outcome)), outcome] = 1.0
    cum_diff = np.cumsum(probs, axis=1) - np.cumsum(onehot, axis=1)
    return float(np.mean(np.sum(cum_diff[:, :-1] ** 2, axis=1) / (probs.shape[1] - 1)))


class OutcomeModel:
    """Calibrated W/D/L classifier. Classes ordered [home, draw, away]."""

    def __init__(self, weights: dict):
        self.weights = weights
        self.clf: CalibratedClassifierCV | None = None
        self.metrics: dict = {}

    def _xy(self, df: pd.DataFrame):
        X = df[FEATURES].to_numpy(dtype=float)
        # map outcome 1/0/-1 -> class index 0 (home win), 1 (draw), 2 (away win)
        y = (1 - df["outcome"]).to_numpy()
        return X, y

    def train(self, train_df: pd.DataFrame) -> dict:
        half_life = float(self.weights["form"]["half_life_days"])
        holdout_since = self.weights["model"]["eval_holdout_since"]

        fit_df = train_df[train_df["date"] < holdout_since]
        eval_df = train_df[train_df["date"] >= holdout_since]

        def make_clf():
            base = HistGradientBoostingClassifier(
                max_depth=3, learning_rate=0.05, max_iter=300,
                l2_regularization=1.0, random_state=7,
            )
            return CalibratedClassifierCV(base, method="isotonic", cv=3)

        # honest out-of-sample metrics first
        if len(eval_df) > 100:
            X_f, y_f = self._xy(fit_df)
            w_f = time_decay_weights(fit_df["date"], half_life)
            probe = make_clf().fit(X_f, y_f, sample_weight=w_f)
            X_e, y_e = self._xy(eval_df)
            probs = probe.predict_proba(X_e)
            self.metrics = {
                "holdout_matches": int(len(eval_df)),
                "holdout_since": str(holdout_since),
                "accuracy": float((probs.argmax(axis=1) == y_e).mean()),
                "rps": ranked_probability_score(probs, y_e),
            }

        # production model: refit (incl. fresh calibration) on everything
        X, y = self._xy(train_df)
        w = time_decay_weights(train_df["date"], half_life)
        self.clf = make_clf().fit(X, y, sample_weight=w)
        return self.metrics

    def predict_match(self, elo_home_adj: float, elo_away_adj: float,
                      form_home: float, form_away: float,
                      importance: float = 60.0, neutral: bool = True,
                      home_adv: float = 0.0) -> np.ndarray:
        """Return [p_home, p_draw, p_away]."""
        x = np.array([[elo_home_adj + home_adv - elo_away_adj,
                       form_home - form_away, importance, int(neutral)]])
        return self.clf.predict_proba(x)[0]


class GoalModel:
    """Poisson expected goals per side as a function of rating difference."""

    def __init__(self, weights: dict):
        self.weights = weights
        self.reg: PoissonRegressor | None = None

    @staticmethod
    def _rows(df: pd.DataFrame):
        # two rows per match: (rating edge incl. home advantage, goals scored)
        diff_h = ((df["elo_home"] + df["home_adv"]) - df["elo_away"]) / 400.0
        X = np.concatenate([diff_h.to_numpy(), -diff_h.to_numpy()])[:, None]
        y = np.concatenate([df["home_score"].to_numpy(), df["away_score"].to_numpy()])
        return X, y

    def train(self, train_df: pd.DataFrame) -> None:
        half_life = float(self.weights["form"]["half_life_days"])
        X, y = self._rows(train_df)
        w = np.tile(time_decay_weights(train_df["date"], half_life), 2)
        self.reg = PoissonRegressor(alpha=1e-4, max_iter=300).fit(X, y, sample_weight=w)

    def lambdas(self, elo_home_adj: float, elo_away_adj: float,
                home_adv: float = 0.0) -> tuple[float, float]:
        diff = (elo_home_adj + home_adv - elo_away_adj) / 400.0
        lh, la = self.reg.predict(np.array([[diff], [-diff]]))
        return (float(np.clip(lh, LAMBDA_MIN, LAMBDA_MAX)),
                float(np.clip(la, LAMBDA_MIN, LAMBDA_MAX)))
