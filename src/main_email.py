"""
Orchestrateur variante EMAIL — génère le post et l'envoie par Outlook.

Usage :
  python src/main_email.py --to tonemail@domaine.com
  python src/main_email.py --to tonemail@domaine.com --display-only   # ouvre Outlook sans envoyer
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import LOG_DIR
from sourcing import fetch_news
from scoring import score_articles
from writer import draft_post
from mailer import send_post_email

log = logging.getLogger("linkedin-bot")


def setup_logging():
    LOG_DIR.mkdir(exist_ok=True)
    log_file = LOG_DIR / f"daily_{datetime.now():%Y-%m-%d}.log"
    fmt = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    handlers = [
        RotatingFileHandler(log_file, maxBytes=2_000_000, backupCount=5, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(level=logging.INFO, format=fmt, handlers=handlers, force=True)


def run(to_address: str, display_only: bool = False) -> int:
    log.info("=" * 60)
    log.info("Pipeline EMAIL start | to=%s | display_only=%s", to_address, display_only)
    log.info("=" * 60)

    try:
        articles = fetch_news()
        if not articles:
            log.error("No articles fetched. Abort.")
            return 1

        scored = score_articles(articles)
        if not scored:
            log.error("Scoring returned nothing. Abort.")
            return 1

        top = scored[0]
        log.info("Selected: [%.1f] %s", top.score, top.article.title)

        post = draft_post(top)
        log.info("\n%s\n", post)

        subject = f"[LinkedIn Post du {datetime.now():%d/%m}] {top.article.title[:70]}"
        send_post_email(
            to_address=to_address,
            subject=subject,
            post=post,
            source_title=top.article.title,
            source_url=top.article.url,
            score=top.score,
            display_only=display_only,
        )

        log.info("Done.")
        return 0

    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        return 2


def main():
    parser = argparse.ArgumentParser(description="Daily LinkedIn post generator -> email")
    parser.add_argument("--to", required=True, help="Destination email address")
    parser.add_argument("--display-only", action="store_true",
                        help="Open email in Outlook but don't send")
    args = parser.parse_args()

    setup_logging()
    sys.exit(run(to_address=args.to, display_only=args.display_only))


if __name__ == "__main__":
    main()
