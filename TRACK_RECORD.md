# wkpool — track record

Honest, automated audit trail. Every prediction is logged **before** the
match is played (`output/history.jsonl` + git history), so this accuracy
curve cannot be cherry-picked afterwards. Hits and misses both.

## Cumulative accuracy

| As of | Matches scored | Correct (toto) | Accuracy | RPS |
|---|---|---|---|---|
| 2026-06-11 | 2 | 2 | 100% | 0.0972 |
| 2026-06-12 | 4 | 2 | 50% | 0.1851 |
| 2026-06-13 | 4 | 2 | 50% | 0.1851 |
| 2026-06-14 | 8 | 3 | 38% | 0.2131 |

## Daily recalibration log

### 2026-06-14
- Score so far: 8 matches, 38% correct, RPS 0.2131
- Newly decided: Brazil 1-1 Morocco [X, predicted 1-1]; Haiti 0-1 Scotland [OK, predicted 0-1]; Qatar 1-1 Switzerland [X, predicted 0-2]; Australia 2-0 Turkey [X, predicted 1-1]
- News ingested: 48 teams scanned, 16 out / 10 doubtful
- Active weights: injuries ×1.0 (12/out, 6/doubtful), climate ×0.0, form half-life 1095d, K_wc=60, sims=20000

### 2026-06-13
- Score so far: 4 matches, 50% correct, RPS 0.1851
- News ingested: 0 teams scanned, 0 out / 0 doubtful
- Active weights: injuries x1.0 (12/out, 6/doubtful), form half-life 1095d, K_wc=60, sims=20000

### 2026-06-12
- Score so far: 4 matches, 50% correct, RPS 0.1851
- News ingested: 0 teams scanned, 0 out / 0 doubtful
- Active weights: injuries x1.0 (12/out, 6/doubtful), form half-life 1095d, K_wc=60, sims=20000

### 2026-06-11
- Score so far: 2 matches, 100% correct, RPS 0.0972
- News ingested: 0 teams scanned, 0 out / 0 doubtful
- Active weights: injuries x1.0 (12/out, 6/doubtful), form half-life 1095d, K_wc=60, sims=20000
