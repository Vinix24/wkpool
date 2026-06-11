"""weights.yaml loading and the plugin contract."""
import json

from wkpool.config import DEFAULTS, load_weights
from wkpool.plugins import team_adjustments
from wkpool.plugins.injuries import InjuryPlugin, _slug


def test_defaults_complete_and_yaml_overrides(tmp_path):
    w = load_weights(tmp_path / "missing.yaml")
    assert w["ratings"]["k_world_cup"] == 60

    custom = tmp_path / "weights.yaml"
    custom.write_text("ratings:\n  k_world_cup: 99\n")
    w = load_weights(custom)
    assert w["ratings"]["k_world_cup"] == 99
    assert w["ratings"]["k_friendly"] == DEFAULTS["ratings"]["k_friendly"]


def test_zero_weight_disables_plugin():
    weights = {**DEFAULTS, "plugin_weights": {"injuries": 0.0, "climate": 0.0}}
    adj = team_adjustments(["Brazil", "Netherlands"], weights)
    assert adj == {"Brazil": 0.0, "Netherlands": 0.0}


def test_injury_plugin_reads_news(tmp_path, monkeypatch):
    import wkpool.plugins.injuries as inj_mod
    monkeypatch.setattr(inj_mod, "NEWS_DIR", tmp_path)
    import datetime as dt
    report = {
        "team": "Netherlands",
        "as_of": dt.date.today().isoformat(),
        "injuries": [
            {"player": "A", "status": "out"},
            {"player": "B", "status": "doubtful"},
            {"player": "C", "status": "returned"},
        ],
        "suspensions": [{"player": "D", "reason": "red card"}],
    }
    (tmp_path / f"{_slug('Netherlands')}.json").write_text(json.dumps(report))
    adj = InjuryPlugin().adjustments(["Netherlands", "Brazil"], DEFAULTS)
    # 2x out (incl. suspension) * 12 + 1x doubtful * 6 = 30 points penalty
    assert adj == {"Netherlands": -30.0}


def test_stale_news_is_ignored(tmp_path, monkeypatch):
    import wkpool.plugins.injuries as inj_mod
    monkeypatch.setattr(inj_mod, "NEWS_DIR", tmp_path)
    report = {"team": "Brazil", "as_of": "2026-01-01",
              "injuries": [{"player": "X", "status": "out"}]}
    (tmp_path / f"{_slug('Brazil')}.json").write_text(json.dumps(report))
    assert InjuryPlugin().adjustments(["Brazil"], DEFAULTS) == {}
