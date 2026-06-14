# Changelog

## Project overview (state at 2026-06-14)

**What it is.** An open-source FIFA World Cup 2026 predictor, CLI `wkpool`, repo
`github.com/Vinix24/world-cup-2026-predictor`. Built to win a pool and to be
forked: the engine is shared, the weights are yours.

**Pipeline.** martj42 results since 1872 → Elo (eloratings.net K-factors) + form
(exp. decay, 3y half-life) → isotonic-calibrated gradient boosting (W/D/L) +
Poisson goal model → 20k Monte Carlo through the official 2026 bracket (12
groups, round of 32, 8-best-thirds allocation). Calibration re-fits every run.
Holdout: ~61% W/D/L accuracy, RPS ~0.167 on 2,200+ internationals since 2024-06.

**Feature plugins** (rating-point nudges, weights in `weights.yaml`):
`injuries` (news-driven, persists across days, capped per team), `odds`
(bookmaker consensus, off by default), `climate` (off by default). Add your own
in `plugins_user/` (gitignored).

**Data sources** (downloaded at runtime, never redistributed): martj42 results;
football-data.org (faster results feed, closes the lag); Perplexity (daily team
news → injuries/suspensions incl. red cards); The Odds API (outright odds).
All optional ones are key-gated via `.env`.

**Pool scoring.** `weights.yaml: pool_scoring` holds the pool's points table
(default: graded exact-score — 200 exact / 100 any-draw / 95 winner+one-goal /
75 winner / 20 one-team-goals). `wkpool mine` enters the expected-points-optimal
scoreline, not the modal one.

**Automation (macOS launchd, 09:15 + 15:15 daily).** Public run (`--public`,
default weights) writes & commits `PREDICTIONS.md`, `NEWS.md`, `TRACK_RECORD.md`
+ `track_record.jsonl` and pushes — the living document the world watches. Then
`wkpool mine` runs with private weights → gitignored `PREDICTIONS.local.md` +
`output/changes.md`, and emails the changes (only when the score to enter moved).
macOS notification with the day's tips.

**Public vs private split.** Committed artifacts always use public default
weights. Private edge stays local: `weights.local.yaml`, `plugins_user/`,
`PREDICTIONS.local.md` — all gitignored. Secrets in `.env` (gitignored):
`PERPLEXITY_API_KEY`, `FOOTBALL_DATA_API_KEY` (set), `ODDS_API_KEY`,
`MAIL_TO`/`SMTP_USER`/`SMTP_PASS` (Gmail app password, spaces stripped).

**Commands.** `daily [--public --with-news --sims N]`, `download [--force]`,
`news [teams]`, `odds`, `mine [--sims N]`, `simulate [--sims N]`, `score`.
38 tests. Run on the always-on Mac mini; repo lives at `~/wkpool`.

**Open / next.** Knockout scoring counts after extra time — the goal model needs
an ET adjustment once the group stage ends. Pool-strategy layer (contrarian
picks vs the field) still a roadmap item. `weights.local.yaml` not yet created
(private predictions currently equal public).

## v0.2.1 — 2026-06-14

**Added**
- **Expected-points-optimal scoreline** (`wkpool/scoring.py`). Your pool rewards
  the exact score far above the bare winner, so `wkpool mine` now fills in the
  scoreline that *maximises expected points* under your pool's rubric
  (configurable in `weights.yaml: pool_scoring`) — often different from the most
  likely score (e.g. enter a draw when any draw scores 100). The private change
  report and `PREDICTIONS.local.md` lead with this "ENTER" score and its
  expected points.

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
