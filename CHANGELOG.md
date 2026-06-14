# Changelog

## v0.2 — 2026-06-14

Iterating on the MVP with the highest-leverage data improvements.

**Added**
- **Bookmaker-consensus odds plugin** — the strongest single covariate in the
  literature. Reads `data/odds/outright.json`, strips the margin, and nudges
  each team's rating toward the market. Off by default; `wkpool odds` fills the
  file from The Odds API.
- **Faster results feed** — optional football-data.org source merges
  same-day World Cup results that the martj42 CSV hasn't picked up yet,
  closing the ~1-2 day upstream lag.
- **News stabilisation** — injuries now persist across days (configurable
  `persist_days`) unless a player is reported fit, dampening the day-to-day
  noise of LLM scraping; total injury penalty per team is capped
  (`max_team_penalty`).
- Twice-daily scheduled run (09:15 + 15:15) to catch late upstream results.

**Fixed**
- W/D/L scoring used the wrong goal-difference sign when a result's home/away
  orientation differed from the logged prediction (latent bug, surfaced by a
  new test).

**Changed**
- Repository renamed to `world-cup-2026-predictor` (CLI stays `wkpool`).

## v0.1 — 2026-06-11

MVP. Elo + form → isotonic-calibrated gradient boosting → 20k Monte Carlo
through the official 2026 bracket. Daily Perplexity news feed, user-tunable
`weights.yaml`, plugin system, living audit trail (`PREDICTIONS.md`,
`NEWS.md`, `TRACK_RECORD.md`). Holdout: 61% accuracy, RPS 0.167.
