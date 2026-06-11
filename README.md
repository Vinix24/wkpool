# wkpool

**Open-source FIFA World Cup 2026 predictor with user-tunable weights.**
Built to win your office pool — and to let everyone in that pool run the
*same* engine with their *own* convictions. The model is the equalizer;
your information and your weights are the edge.

```
results since 1872 ──► Elo + form ──► calibrated gradient boosting ──► match probabilities
bookmaker-free, fully reproducible      │
your news / plugins ──► rating adjustments ──► 20.000x Monte Carlo ──► tournament odds
```

Current out-of-sample performance: **~61% W/D/L accuracy, RPS ~0.167** on
2,200+ internationals since June 2024 — measured on a holdout the model
never saw, re-reported on every training run. For reference: the
peer-reviewed academic benchmark sits at RPS ≈ 0.17 and a naive
always-pick-the-favourite Elo baseline at 60.0%. Football is noisy;
distrust anyone claiming 70%.

## Quickstart

```bash
git clone https://github.com/Vinix24/wkpool && cd wkpool
python3 -m venv .venv && source .venv/bin/activate
pip install -e .

wkpool daily          # download data, train, predict, simulate
```

That single command:

1. downloads the latest international results (49k+ matches, updated daily upstream),
2. replays all of history through an Elo engine (eloratings.net conventions),
3. trains an isotonic-calibrated gradient-boosting outcome model and a
   Poisson goal model on leakage-free pre-match features,
4. predicts every remaining group match (probabilities + most likely score),
5. simulates the full tournament 20,000× through the **official 2026
   bracket** — 12 groups, round of 32, the 8-best-thirds allocation, all of it,
6. writes [`PREDICTIONS.md`](PREDICTIONS.md) and `output/simulation.json`.

Runs in ~10 seconds on a laptop. No API keys required for any of the above.

## Make it yours: weights.yaml

Everything tunable lives in [`weights.yaml`](weights.yaml):

```yaml
ratings:
  k_world_cup: 60        # how hard World Cup results move ratings
  home_advantage: 100    # rating bonus for the three host nations
form:
  half_life_days: 1095   # a match 3 years ago counts half (lit. optimum)
plugin_weights:
  injuries: 1.0          # trust in the injury feed
  climate: 0.0           # warm-climate hypothesis — off by default
```

Change a number, run `wkpool daily`, done. **Calibration is re-fitted on
every run**, so your probabilities stay honest no matter how exotic your
weights get. That re-fit is not optional politeness — uncalibrated
probabilities silently corrupt every downstream simulation.

## Bring your own information: plugins

A plugin turns any information source into rating-point adjustments:

```python
# plugins_user/my_hunch.py
class MyHunch:
    name = "my_hunch"                    # weight key in weights.yaml

    def adjustments(self, teams, weights):
        return {"Netherlands": +25.0}    # Elo points; negative weakens

PLUGIN = MyHunch()
```

Drop the file in `plugins_user/`, add `my_hunch: 1.0` under
`plugin_weights`, and your conviction flows coherently into both match
probabilities and tournament odds.

Two plugins ship built-in:

- **injuries** — reads structured team-news JSON from `data/news/` and
  penalizes teams per player out/doubtful/suspended. Stale news expires
  automatically.
- **climate** — the "warm-climate teams cope better with US/Mexico summer
  heat" hypothesis. No published evidence quantifies it, so it ships with
  weight **0.0**. Turn it on if you believe; tell us what it did to your score.

## The news feed (optional, needs a key)

```bash
cp .env.example .env     # add your PERPLEXITY_API_KEY
wkpool news              # one structured query per team, strict JSON out
wkpool daily --with-news
```

The prompt was live-tested to *not* hallucinate: on quiet news days it
returns empty arrays and an honest `news_volume: low` instead of inventing
injuries. No key? Everything else works; you just run information-neutral.

The JSON file format is the contract, not the fetcher — write
`data/news/netherlands.json` by hand or with your own scraper and the
injury plugin picks it up all the same.

## Recalibration during the tournament

Played matches enter every simulation as fixed results, and every result
also updates the Elo ratings (K=60). So:

- **Daily** (or via the included GitHub Action at 06:17 UTC): the whole
  pipeline re-runs on everything known so far. After the group stage the
  real round-of-32 pairings freeze automatically.
- **Last minute** (pools that allow edits until kickoff): run
  `wkpool news <team> <team>` for today's teams, then `wkpool daily`.
  Sixty seconds, fresh lineup news included.

Every prediction is logged to `output/history.jsonl` *before* results
exist; `wkpool score` reports your live accuracy and RPS so far —
leakage-free by construction.

## Honest limitations

- Group tiebreaks implement points / goal difference / goals scored /
  two-way head-to-head; FIFA's fair-play points and drawing of lots are
  modelled as random.
- Third-place bracket seating uses constraint-respecting deterministic
  matching; FIFA's exact priority between equally valid seatings is not public.
- Penalty shootouts are 50/50 with a small Elo nudge (capped at 60/40).
- No bookmaker odds: the academic literature says odds are the strongest
  single covariate, but free redistributable odds feeds don't exist. Adding
  them via a plugin is the single biggest upgrade available — see roadmap.

## Data sources (downloaded at runtime, never redistributed)

| Source | Used for |
|---|---|
| [martj42/international_results](https://github.com/martj42/international_results) | all match results since 1872, updated daily |
| [eloratings.net](https://eloratings.net) conventions | K-factors, home advantage |
| Official FIFA schedule | groups, 72 fixtures, knockout bracket (static facts in `wkpool/schedule.py`) |
| Perplexity API (optional) | structured daily team news |

## Development

```bash
pip install -e ".[dev]"
pytest                   # 21 tests, incl. all 495 third-place combinations
```

PRs welcome — especially new plugins, an odds adapter, and pool-strategy
tooling (picking *against* the consensus is how pools are actually won;
that layer is the roadmap).

## License

MIT. Predictions are probabilities, not promises — the 2022 academic
favourite was Brazil, and Argentina won. Use for pool glory, not for betting
decisions.
