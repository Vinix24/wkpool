#!/usr/bin/env python3
"""Mail your private prediction changes to yourself after the daily run.

Mails output/changes.md (what moved in YOUR predictions since the last run,
from `wkpool mine`) with the full private list appended, so you only get a
mail when there's something to re-enter in your pool. Falls back to the
public PREDICTIONS.md if no change report exists.

Configure in .env (all required to activate; without them this is a no-op):
    MAIL_TO=you@example.com
    SMTP_USER=you@gmail.com
    SMTP_PASS=xxxx xxxx xxxx xxxx     # Gmail app password, not your login
Optional:
    SMTP_HOST=smtp.gmail.com
    SMTP_PORT=465
"""
from __future__ import annotations

import os
import smtplib
import ssl
import sys
from datetime import date
from email.mime.text import MIMEText
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from wkpool.config import load_env  # noqa: E402

CHANGES = ROOT / "output" / "changes.md"
PRIVATE = ROOT / "PREDICTIONS.local.md"
PUBLIC = ROOT / "PREDICTIONS.md"


def main() -> int:
    load_env()
    to = os.environ.get("MAIL_TO", "").strip()
    user = os.environ.get("SMTP_USER", "").strip()
    # Gmail shows app passwords as "xxxx xxxx xxxx xxxx"; SMTP wants no spaces
    password = os.environ.get("SMTP_PASS", "").strip().replace(" ", "")
    if not (to and user and password):
        print("mail not configured (MAIL_TO/SMTP_USER/SMTP_PASS) — skipping")
        return 0

    if CHANGES.exists():
        subject = f"WK-tips bijgewerkt {date.today().isoformat()}"
        body = CHANGES.read_text()
        if PRIVATE.exists():
            body += "\n\n---\n\n" + PRIVATE.read_text()
    elif "--always" in sys.argv and PUBLIC.exists():
        subject = f"WK-tips {date.today().isoformat()}"
        body = PUBLIC.read_text()
    else:
        print("no prediction changes — no mail sent")
        return 0

    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = user
    msg["To"] = to

    host = os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = int(os.environ.get("SMTP_PORT", "465"))
    with smtplib.SMTP_SSL(host, port, context=ssl.create_default_context()) as smtp:
        smtp.login(user, password)
        smtp.send_message(msg)
    print(f"mailed '{subject}' to {to}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
