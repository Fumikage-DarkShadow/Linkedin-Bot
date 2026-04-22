"""
Orchestrateur — pipeline LLM (Claude Sonnet 4.6) qui envoie au webhook Make.com.

Scoring + rédaction via Anthropic API.
Nécessite ANTHROPIC_API_KEY avec crédit.

Usage :
  python src/main_webhook_llm.py
  python src/main_webhook_llm.py --dry-run
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
from publisher_webhook import post_to_webhook
from enrich import get_image_with_fallback
from daily_cache import has_posted_today, mark_posted_today

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
    log.info("Pipeline WEBHOOK (Claude LLM) start | dry_run=%s", dry_run)
    log.info("=" * 60)

    if not dry_run and has_posted_today():
        log.info("Skipping: a post has already been published today.")
        return 0

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
        log.info("Reason: %s", top.reason)

        post = draft_post(top)
        log.info("\n%s\n", post)

        image_url = get_image_with_fallback(top.article.url, top.article.category)

        post_to_webhook(
            post_text=post,
            source_title=top.article.title,
            source_url=top.article.url,
            score=top.score,
            category=top.article.category,
            image_url=image_url,
            dry_run=dry_run,
        )

        if not dry_run:
            mark_posted_today(top.article.url)

        log.info("Done.")
        return 0

    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        return 2


def main():
    parser = argparse.ArgumentParser(description="Daily LinkedIn post (Claude LLM) -> Make.com webhook")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    setup_logging()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
