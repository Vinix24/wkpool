"""Experimental warm-climate plugin — OFF by default (weight 0.0).

Hypothesis: teams from hot climates cope better with midday summer heat in
the US and Mexico. No published evidence quantifies this effect, which is
why the default weight is zero. Turn it on in weights.yaml if you believe
in it — and tell us what it does to your scores.
"""
from __future__ import annotations

WARM_CLIMATE = {
    "Brazil", "Mexico", "Colombia", "Ecuador", "Paraguay", "Uruguay",
    "Argentina", "Morocco", "Tunisia", "Egypt", "Algeria", "Senegal",
    "Ivory Coast", "Ghana", "Cape Verde", "DR Congo", "South Africa",
    "Saudi Arabia", "Qatar", "Iran", "Iraq", "Jordan", "Uzbekistan",
    "Haiti", "Panama", "Curaçao", "Australia",
}


class ClimatePlugin:
    name = "climate"

    def adjustments(self, teams: list[str], weights: dict) -> dict[str, float]:
        bonus = float(weights["climate"]["warm_bonus_points"])
        return {t: bonus for t in teams if t in WARM_CLIMATE}
