#!/bin/zsh
# Daily local wkpool run + macOS notification + GitHub push of PREDICTIONS.md.
# Installed as a launchd agent by scripts/install_launchd.sh.
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

LOG="$REPO/output/daily_local.log"
mkdir -p "$REPO/output"
echo "=== wkpool daily $(date '+%F %T') ===" >> "$LOG"

if ./.venv/bin/wkpool daily --force --with-news --public >> "$LOG" 2>&1; then
    TODAY=$(date +%F)
    # today's rows from the predictions table: "| 2026-06-14 | F | Netherlands – Japan | ... | 1-1 |"
    TIPS=$(grep "^| $TODAY" PREDICTIONS.md \
        | awk -F'|' '{gsub(/^ +| +$/,"",$4); gsub(/^ +| +$/,"",$8); printf "%s: %s\n", $4, $8}' \
        | head -6)
    [ -z "$TIPS" ] && TIPS="Geen wedstrijden vandaag"
    SCORE=$(./.venv/bin/wkpool score 2>/dev/null | tail -1)

    # publish the living document for the world: commit public diffs and push
    if git remote get-url origin > /dev/null 2>&1; then
        git add PREDICTIONS.md NEWS.md TRACK_RECORD.md track_record.jsonl
        if ! git diff --cached --quiet; then
            git commit -q -m "Daily update $TODAY (results + news recalibration)"
            git push -q origin HEAD >> "$LOG" 2>&1 || echo "push failed" >> "$LOG"
        fi
    fi

    # private pass with YOUR weights -> change report for your own pool entry
    ./.venv/bin/wkpool mine >> "$LOG" 2>&1 || true

    # mail your prediction changes (only when something moved; needs SMTP in .env)
    ./.venv/bin/python scripts/mail_predictions.py >> "$LOG" 2>&1 || true

    osascript -e "display notification \"$TIPS\" with title \"WK-tips $TODAY\" subtitle \"$SCORE\" sound name \"Glass\""
else
    osascript -e "display notification \"Run gefaald — zie output/daily_local.log\" with title \"wkpool error\" sound name \"Basso\""
    exit 1
fi
