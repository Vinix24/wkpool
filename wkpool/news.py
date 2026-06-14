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
has since been reported fit.
If the team played a match in the last 48 hours, ALWAYS analyse the match
reports of that game explicitly for: red cards (a red card means a
suspension for the next match -> list under "suspensions"), suspensions
from yellow-card accumulation, injuries or knocks picked up during the
match (list under "injuries"), and any other notable incidents such as
internal conflicts or protests (list under "morale_signals")."""


def _slug(team: str) -> str:
    return team.lower().replace(" ", "_")


def merge_persisted(old: dict | None, new: dict, today: dt.date,
                    persist_days: int) -> dict:
    """Carry forward recent injuries the fresh report dropped, to dampen the
    day-to-day noise of LLM news scraping.

    An injury seen on a previous day stays in the report (flagged persisted)
    until it is either explicitly reported "returned", or `persist_days` have
    passed since it was first seen. Players present in the fresh report always
    win (their status and first_seen are authoritative).
    """
    today_iso = today.isoformat()
    merged = {}
    for inj in new.get("injuries", []):
        name = inj.get("player")
        if not name:
            continue
        inj.setdefault("first_seen", today_iso)
        merged[name] = inj

    returned_today = {i["player"] for i in new.get("injuries", [])
                      if i.get("status") == "returned" and i.get("player")}

    for inj in (old or {}).get("injuries", []):
        name = inj.get("player")
        if not name or name in merged or name in returned_today:
            continue
        if inj.get("status") not in ("out", "doubtful"):
            continue
        first = inj.get("first_seen", inj.get("source_date") or today_iso)
        try:
            age = (today - dt.date.fromisoformat(str(first)[:10])).days
        except ValueError:
            age = 0
        if age <= persist_days:
            merged[name] = {**inj, "first_seen": first, "persisted": True}

    new["injuries"] = list(merged.values())
    return new


def _extract_json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object in response")
    return json.loads(text[start:end + 1])


def _recent_fixture(team: str, today: dt.date) -> str:
    """A concrete search anchor: the team's group match of the last 2 days."""
    from . import schedule
    for date_str, home, away in schedule.GROUP_FIXTURES:
        date = dt.date.fromisoformat(date_str)
        if team in (home, away) and 0 <= (today - date).days <= 2:
            return (f" IMPORTANT: {team} played a World Cup match on {date_str} "
                    f"({home} vs {away}). Analyse the match reports of that game "
                    f"for red cards, suspensions, in-match injuries and incidents.")
    return ""


def fetch_team(team: str, api_key: str, today: dt.date) -> dict:
    user = (f"Team: {team}. Today is {today.isoformat()} during the FIFA World Cup "
            f"2026. Collect injuries, suspensions, expected lineup changes and "
            f"morale signals, and confirm the team's next match."
            + _recent_fixture(team, today))
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


def render_digest(today: dt.date | None = None) -> None:
    """Render a public, shareable daily news digest from the scraped JSON.

    This is the lead-magnet artifact: a clean World Cup injury/suspension
    digest with source links, committed to the repo. It says nothing about
    how the model uses the news — that stays private.
    """
    from .config import ROOT
    today = today or dt.date.today()
    if not NEWS_DIR.is_dir():
        return
    reports = []
    for path in sorted(NEWS_DIR.glob("*.json")):
        try:
            reports.append(json.loads(path.read_text()))
        except json.JSONDecodeError:
            continue
    reports.sort(key=lambda d: d.get("team", ""))

    lines = [
        "# WK 2026 — daily news digest",
        "",
        f"_Auto-generated {today.isoformat()}. Injuries, suspensions and lineup "
        "news per team, gathered each morning. Sources linked per entry._",
        "",
    ]
    for d in reports:
        out = [i for i in d.get("injuries", []) if i.get("status") in ("out", "doubtful")]
        susp = d.get("suspensions", [])
        changes = d.get("expected_lineup_changes", [])
        if not (out or susp or changes):
            continue
        lines.append(f"## {d.get('team', '?')}")
        nxt = d.get("next_match", {})
        if nxt.get("opponent"):
            lines.append(f"_Next: {nxt.get('opponent')} ({nxt.get('date', '?')})_")
        for s in susp:
            who = s.get("player", "?")
            why = s.get("reason") or s.get("detail", "")
            lines.append(f"- **Suspended:** {who} — {why}")
        for i in out:
            tag = "OUT" if i.get("status") == "out" else "Doubtful"
            lines.append(f"- **{tag}:** {i.get('player', '?')} — {i.get('detail', '')}")
        for c in changes:
            if c.get("likelihood") in ("confirmed", "likely"):
                lines.append(f"- _Lineup:_ {c.get('change', '')} ({c['likelihood']})")
        srcs = d.get("sources", [])
        if srcs:
            lines.append(f"- Sources: {', '.join(srcs[:3])}")
        lines.append("")
    (ROOT / "NEWS.md").write_text("\n".join(lines))
    print(f"wrote {ROOT / 'NEWS.md'}")


def fetch_all(teams: list[str], persist_days: int = 3) -> int:
    """Fetch news for the given teams; returns number of teams fetched."""
    api_key = os.environ.get("PERPLEXITY_API_KEY", "").strip()
    if not api_key:
        print("PERPLEXITY_API_KEY not set — skipping news fetch (model runs without it)")
        return 0
    ensure_dirs()
    today = dt.date.today()
    done = 0
    for team in teams:
        path = NEWS_DIR / f"{_slug(team)}.json"
        try:
            report = fetch_team(team, api_key, today)
            report.setdefault("as_of", today.isoformat())
            old = None
            if path.exists():
                try:
                    old = json.loads(path.read_text())
                except json.JSONDecodeError:
                    old = None
            report = merge_persisted(old, report, today, persist_days)
            path.write_text(json.dumps(report, indent=2, ensure_ascii=False))
            inj = report.get("injuries", [])
            carried = sum(1 for i in inj if i.get("persisted"))
            print(f"  {team}: {len(inj)} injury item(s)"
                  f"{f' ({carried} carried)' if carried else ''}, "
                  f"volume={report.get('data_quality', {}).get('news_volume', '?')}")
            done += 1
        except Exception as exc:  # one team failing must not kill the run
            print(f"  {team}: fetch failed ({exc})")
    return done
