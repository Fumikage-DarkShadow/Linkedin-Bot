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

from config import LOG_DIR, MIN_SCORE_TO_POST
from sourcing import fetch_news
from scoring import score_articles
from writer import draft_post
from publisher_webhook import post_to_webhook
from enrich import get_image_with_fallback
from daily_cache import should_skip_today, mark_posted_today
from health_check import check_scenario_active, ScenarioInactiveError, HealthCheckError

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


def run(dry_run: bool = False, force: bool = False) -> int:
    log.info("=" * 60)
    log.info("Pipeline WEBHOOK (Claude LLM) start | dry_run=%s | force=%s", dry_run, force)
    log.info("=" * 60)

    # Health check Make.com avant tout : si scenario inactif, on fail visiblement
    # pour que GitHub Actions devienne rouge et qu'un email d'alerte parte.
    if not dry_run:
        try:
            check_scenario_active()
        except ScenarioInactiveError as e:
            log.error("HEALTH CHECK FAILED: %s", e)
            return 3
        except HealthCheckError as e:
            log.warning("Make API health check error (non bloquant): %s", e)

    if not dry_run and not force:
        skip, reason = should_skip_today()
        if skip:
            log.info("Skipping: %s", reason)
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

        if not dry_run and not force and top.score < MIN_SCORE_TO_POST:
            log.info(
                "Top score %.1f < threshold %.1f -> SKIP (no post today, cache not updated, next cron will retry).",
                top.score, MIN_SCORE_TO_POST,
            )
            return 0

        if force and top.score < MIN_SCORE_TO_POST:
            log.warning(
                "FORCE mode: posting despite top score %.1f < threshold %.1f.",
                top.score, MIN_SCORE_TO_POST,
            )

        post = draft_post(top)
        log.info("\n%s\n", post)

        image_url = get_image_with_fallback(
            top.article.url,
            top.article.category,
            rss_image_url=getattr(top.article, "rss_image_url", ""),
        )

        post_to_webhook(
            post_text=post,
            source_title=top.article.title,
            source_url=top.article.url,
            score=top.score,
            category=top.article.category,
            image_url=image_url,
            dry_run=dry_run,
        )

        # En mode force on N'ECRIT PAS le cache pour ne pas consommer le quota hebdo
        # (un test manuel ne doit pas compter contre les 2 posts/semaine).
        if not dry_run and not force:
            mark_posted_today(top.article.url)
        elif force and not dry_run:
            log.info("FORCE mode: cache NOT updated (this manual test does not count against weekly cap).")

        log.info("Done.")
        return 0

    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        return 2


def main():
    parser = argparse.ArgumentParser(description="Daily LinkedIn post (Claude LLM) -> Make.com webhook")
    parser.add_argument("--dry-run", action="store_true", help="Affiche le post sans rien envoyer")
    parser.add_argument("--force", action="store_true",
                        help="Bypass tous les garde-fous (weekend, cap hebdo, seuil score). Cache non mis a jour.")
    args = parser.parse_args()
    setup_logging()
    sys.exit(run(dry_run=args.dry_run, force=args.force))


if __name__ == "__main__":
    main()
