"""
Orchestrateur — pipeline template (sans LLM) qui envoie au webhook Make.com.

Usage :
  python src/main_webhook.py
  python src/main_webhook.py --dry-run
"""
from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler

from config import LOG_DIR
from sourcing import fetch_news
from scoring_rules import score_articles
from writer_template import draft_post
from publisher_webhook import post_to_webhook

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


def run(dry_run: bool = False) -> int:
    log.info("=" * 60)
    log.info("Pipeline WEBHOOK (template) start | dry_run=%s", dry_run)
    log.info("=" * 60)

    try:
        articles = fetch_news()
        if not articles:
            log.error("No articles fetched. Abort.")
            return 1

        scored = score_articles(articles)
        top = scored[0]
        log.info("Selected: [%.1f] %s", top.score, top.article.title)
        log.info("Reason: %s", top.reason)

        post = draft_post(top)
        log.info("\n%s\n", post)

        post_to_webhook(
            post_text=post,
            source_title=top.article.title,
            source_url=top.article.url,
            score=top.score,
            category=top.article.category,
            dry_run=dry_run,
        )
        log.info("Done.")
        return 0

    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        return 2


def main():
    parser = argparse.ArgumentParser(description="Daily LinkedIn post (template) -> Make.com webhook")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
