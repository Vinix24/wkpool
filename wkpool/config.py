"""Configuration: weights.yaml + .env loading."""
from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
OUTPUT_DIR = ROOT / "output"
MODELS_DIR = ROOT / "models"
NEWS_DIR = DATA_DIR / "news"

DEFAULTS: dict = {
    "ratings": {
        "k_world_cup": 60, "k_continental": 50, "k_qualifier": 40,
        "k_nations_league": 30, "k_friendly": 20, "home_advantage": 100,
    },
    "form": {"half_life_days": 1095},
    "plugin_weights": {"injuries": 1.0, "climate": 0.0},
    "injuries": {"points_per_out": 12, "points_per_doubtful": 6, "max_news_age_days": 5},
    "climate": {"warm_bonus_points": 15},
    "simulation": {"n_sims": 20000, "max_goals": 12, "extra_time_factor": 0.33, "seed": None},
    "model": {"train_since": "1993-01-01", "eval_holdout_since": "2024-06-01"},
}


def _merge(base: dict, override: dict) -> dict:
    out = dict(base)
    for k, v in override.items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load_weights(path: Path | None = None) -> dict:
    """DEFAULTS < weights.yaml < weights.local.yaml (gitignored, your edge)."""
    weights = dict(DEFAULTS)
    paths = [path] if path else [ROOT / "weights.yaml", ROOT / "weights.local.yaml"]
    for p in paths:
        if p.exists():
            with open(p) as f:
                weights = _merge(weights, yaml.safe_load(f) or {})
    return weights


def load_env(path: Path | None = None) -> None:
    """Minimal .env loader: KEY=VALUE lines into os.environ (no override)."""
    path = path or ROOT / ".env"
    if not path.exists():
        return
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


def ensure_dirs() -> None:
    for d in (DATA_DIR, OUTPUT_DIR, MODELS_DIR, NEWS_DIR):
        d.mkdir(parents=True, exist_ok=True)
