"""Feature plugins: how users add their own information to the model.

A plugin is any object with:
    name: str                       — key in weights.yaml `plugin_weights`
    adjustments(teams, weights)     — dict[team, rating_points]

Positive points strengthen a team, negative weaken it. The engine sums
weight * points over all plugins onto each team's Elo rating before
prediction and simulation, so a plugin shifts both match probabilities and
tournament odds coherently.

To add your own: drop a .py file in plugins_user/ at the repo root defining
PLUGIN (an instance), and give its name a weight in weights.yaml.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Protocol

from ..config import ROOT


class FeaturePlugin(Protocol):
    name: str

    def adjustments(self, teams: list[str], weights: dict) -> dict[str, float]: ...


def load_plugins() -> list:
    from .injuries import InjuryPlugin
    from .climate import ClimatePlugin
    from .odds import OddsPlugin

    plugins: list = [InjuryPlugin(), ClimatePlugin(), OddsPlugin()]

    user_dir = ROOT / "plugins_user"
    if user_dir.is_dir():
        for path in sorted(user_dir.glob("*.py")):
            spec = importlib.util.spec_from_file_location(f"plugins_user.{path.stem}", path)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            if hasattr(mod, "PLUGIN"):
                plugins.append(mod.PLUGIN)
    return plugins


def team_adjustments(teams: list[str], weights: dict) -> dict[str, float]:
    """Weighted sum of all plugin adjustments, in Elo rating points."""
    total = {t: 0.0 for t in teams}
    plugin_weights = weights.get("plugin_weights", {})
    for plugin in load_plugins():
        w = float(plugin_weights.get(plugin.name, 0.0))
        if w == 0.0:
            continue
        for team, points in plugin.adjustments(teams, weights).items():
            if team in total:
                total[team] += w * points
    return total
