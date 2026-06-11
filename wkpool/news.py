"""Daily team-news fetcher via the Perplexity API (optional feature).

Needs PERPLEXITY_API_KEY in .env. Without it this module is skipped
gracefully — the model then simply runs without the injury feature.

The prompt forces strict JSON and explicitly allows empty arrays, which in
live testing kept the model honest on quiet news days instead of
hallucinating injuries.
"""
from __future__ import annotations

import datetime as dt
import json
import os

import requests

from .config import NEWS_DIR, ensure_dirs

API_URL = "https://api.perplexity.ai/chat/completions"
MODEL = "sonar-pro"

SYSTEM_PROMPT = """\
You are a data-extraction agent for a World Cup 2026 prediction model. You
search current news (last 48 hours) about one national football team and
return ONLY valid JSON matching exactly this schema — no prose, no markdown:
{
  "team": string,
  "as_of": string (ISO date),
  "injuries": [{"player": string, "position": string|null,
                "status": "out"|"doubtful"|"returned", "detail": string,
                "source_date": string|null}],
  "suspensions": [{"player": string, "reason": string}],
  "expected_lineup_changes": [{"change": string,
                               "likelihood": "confirmed"|"likely"|"rumour"}],
  "morale_signals": [{"signal": string, "direction": "positive"|"negative",
                      "detail": string}],
  "next_match": {"opponent": string|null, "date": string|null,
                 "kickoff_local": string|null},
  "sources": [string],
  "data_quality": {"news_volume": "high"|"medium"|"low", "caveats": string}
}
Rules: only facts from news of the last 48 hours or explicitly still-current
situations. Never invent; empty arrays are fine. When unsure use status
"doubtful" and likelihood "rumour". Never list an old injury if the player
has since been reported fit."""


def _slug(team: str) -> str:
    return team.lower().replace(" ", "_")


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


def fetch_team(team: str, api_key: str, today: dt.date) -> dict:
    user = (f"Team: {team}. Today is {today.isoformat()} during the FIFA World Cup "
            f"2026. Collect injuries, suspensions, expected lineup changes and "
            f"morale signals, and confirm the team's next match.")
    payload = {
        "model": MODEL,
        "temperature": 0.1,
        "max_tokens": 2048,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user},
        ],
    }
    headers = {"Authorization": f"Bearer {api_key}"}
    resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
    resp.raise_for_status()
    text = resp.json()["choices"][0]["message"]["content"]
    try:
        return _extract_json(text)
    except (ValueError, json.JSONDecodeError):
        # one retry, feeding the broken output back
        payload["messages"].append({"role": "assistant", "content": text})
        payload["messages"].append({"role": "user", "content":
                                    "That was not valid JSON. Return ONLY the JSON object."})
        resp = requests.post(API_URL, json=payload, headers=headers, timeout=120)
        resp.raise_for_status()
        return _extract_json(resp.json()["choices"][0]["message"]["content"])


def fetch_all(teams: list[str]) -> int:
    """Fetch news for the given teams; returns number of teams fetched."""
    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        print("PERPLEXITY_API_KEY not set — skipping news fetch (model runs without it)")
        return 0
    ensure_dirs()
    today = dt.date.today()
    done = 0
    for team in teams:
        try:
            report = fetch_team(team, api_key, today)
            report.setdefault("as_of", today.isoformat())
            (NEWS_DIR / f"{_slug(team)}.json").write_text(
                json.dumps(report, indent=2, ensure_ascii=False))
            n_inj = len(report.get("injuries", []))
            print(f"  {team}: {n_inj} injury item(s), "
                  f"volume={report.get('data_quality', {}).get('news_volume', '?')}")
            done += 1
        except Exception as exc:  # one team failing must not kill the run
            print(f"  {team}: fetch failed ({exc})")
    return done
