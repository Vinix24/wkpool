"""wkpool command-line interface.

    wkpool download          fetch latest results data
    wkpool news              fetch team news via Perplexity (optional)
    wkpool daily             full pipeline: download -> train -> predict -> simulate
    wkpool simulate          tournament Monte Carlo only
    wkpool score             how good were our pre-match predictions so far?
"""
from __future__ import annotations

import argparse
import sys

import pandas as pd

from . import data_io, news, schedule, sources, track
from .config import ensure_dirs, load_env, load_weights
from .elo import EloEngine
from .model import GoalModel, OutcomeModel, build_training_frame
from .plugins import team_adjustments
from .predict import (log_history, predict_remaining, score_history, write_report)
from .sim import TournamentSim


def _prepare(weights: dict):
    """Shared pipeline: data -> ratings/features -> trained models -> state."""
    df = data_io.load_results()
    engine = EloEngine(weights)
    hist = engine.process(df)

    train_df = build_training_frame(hist, weights["model"]["train_since"])
    outcome = OutcomeModel(weights)
    metrics = outcome.train(train_df)
    if metrics:
        print(f"holdout since {metrics['holdout_since']}: "
              f"{metrics['accuracy']:.1%} accuracy, RPS {metrics['rps']:.4f} "
              f"({metrics['holdout_matches']} matches)")
    goal_model = GoalModel(weights)
    goal_model.train(train_df)

    teams = schedule.all_teams()
    now = df["date"].max()
    adjustments = team_adjustments(teams, weights)
    ratings = {t: engine.rating(t) + adjustments.get(t, 0.0) for t in teams}
    forms = {t: engine.form(t, now) for t in teams}

    played = {}
    for r in data_io.world_cup_2026_results(df).itertuples(index=False):
        played[(r.home_team, r.away_team)] = (int(r.home_score), int(r.away_score))

    adjusted = {t: round(adjustments.get(t, 0.0), 1) for t in teams if adjustments.get(t)}
    if adjusted:
        print(f"plugin adjustments (Elo points): {adjusted}")
    return df, outcome, goal_model, ratings, forms, played, metrics


def cmd_download(args, weights):
    data_io.download(force=args.force)


def cmd_news(args, weights):
    teams = args.teams or schedule.all_teams()
    n = news.fetch_all(teams, persist_days=int(weights["injuries"]["persist_days"]))
    print(f"news fetched for {n}/{len(teams)} teams")


def cmd_odds(args, weights):
    sources.fetch_outright_odds()


def cmd_mine(args, weights):
    from . import mine
    mine.run(weights, n_sims=args.sims)


def cmd_simulate(args, weights):
    df, outcome, goal_model, ratings, forms, played, metrics = _prepare(weights)
    n_sims = args.sims or int(weights["simulation"]["n_sims"])
    sim = TournamentSim(goal_model, ratings, weights, played)
    print(f"simulating tournament {n_sims:,}x "
          f"({len(played)} group matches already decided)...")
    result = sim.run(n_sims)
    sim.save(result, n_sims)
    cols = ["team", "group", "p_R16", "p_QF", "p_SF", "p_F", "p_champion"]
    print(result[cols].head(15).to_string(index=False,
          float_format=lambda x: f"{x:.1%}"))


def cmd_daily(args, weights):
    data_io.download(force=args.force)
    if args.with_news:
        news.fetch_all(schedule.all_teams(),
                       persist_days=int(weights["injuries"]["persist_days"]))
        sources.fetch_outright_odds()
    df, outcome, goal_model, ratings, forms, played, metrics = _prepare(weights)

    preds = predict_remaining(outcome, goal_model, ratings, forms, weights, played)
    log_history(preds)

    n_sims = args.sims or int(weights["simulation"]["n_sims"])
    sim = TournamentSim(goal_model, ratings, weights, played)
    print(f"simulating tournament {n_sims:,}x "
          f"({len(played)} group matches already decided)...")
    sim_df = sim.run(n_sims)
    sim.save(sim_df, n_sims)

    score = score_history(data_io.world_cup_2026_results(df))
    write_report(preds, sim_df, metrics, score)

    if args.with_news:
        news.render_digest()
    track.update(weights)


def cmd_score(args, weights):
    df = data_io.load_results()
    score = score_history(data_io.world_cup_2026_results(df))
    if score is None:
        print("nothing to score yet (no logged predictions for played matches)")
        return
    print(f"{score['matches_scored']} matches scored: "
          f"{score['accuracy']:.1%} accuracy, RPS {score['rps']:.4f}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="wkpool",
                                     description="World Cup 2026 predictor")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("download", help="fetch latest results data")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_download)

    p = sub.add_parser("news", help="fetch team news via Perplexity")
    p.add_argument("teams", nargs="*", help="default: all 48 teams")
    p.set_defaults(func=cmd_news)

    p = sub.add_parser("odds", help="fetch bookmaker outright odds (The Odds API)")
    p.set_defaults(func=cmd_odds)

    p = sub.add_parser("mine", help="private predictions (your weights) + change report")
    p.add_argument("--sims", type=int)
    p.set_defaults(func=cmd_mine)

    p = sub.add_parser("simulate", help="Monte Carlo tournament simulation")
    p.add_argument("--sims", type=int)
    p.set_defaults(func=cmd_simulate)

    p = sub.add_parser("daily", help="full pipeline incl. PREDICTIONS.md")
    p.add_argument("--force", action="store_true", help="force data re-download")
    p.add_argument("--with-news", action="store_true", help="also fetch Perplexity news")
    p.add_argument("--public", action="store_true",
                   help="ignore weights.local.yaml (use for the published/committed run)")
    p.add_argument("--sims", type=int)
    p.set_defaults(func=cmd_daily)

    p = sub.add_parser("score", help="score logged predictions vs. results")
    p.set_defaults(func=cmd_score)

    args = parser.parse_args(argv)
    load_env()
    ensure_dirs()
    weights = load_weights(public_only=getattr(args, "public", False))
    pd.set_option("display.width", 160)
    args.func(args, weights)
    return 0


if __name__ == "__main__":
    sys.exit(main())
