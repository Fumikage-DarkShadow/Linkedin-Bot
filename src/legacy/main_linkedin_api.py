"""
Orchestrateur — exécute le pipeline complet :
  1. Fetch news (sourcing.py)
  2. Score via LLM (scoring.py)
  3. Filtre articles déjà postés (cache URLs)
  4. Draft post (writer.py)
  5. Publish LinkedIn (publisher.py)
  6. Enregistre URL dans cache

Usage :
  python src/main.py                # exécution normale (publie)
  python src/main.py --dry-run      # affiche le post sans publier
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
from pathlib import Path

from config import CACHE_FILE, LOG_DIR
from sourcing import fetch_news
from scoring import score_articles, ScoredArticle
from writer import draft_post
from publisher import post_to_linkedin

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


def load_cache() -> set[str]:
    if not CACHE_FILE.exists():
        return set()
    try:
        return set(json.loads(CACHE_FILE.read_text(encoding="utf-8")))
    except Exception as e:
        log.warning("Cache unreadable, starting fresh: %s", e)
        return set()


def save_cache(urls: set[str]) -> None:
    CACHE_FILE.write_text(json.dumps(sorted(urls), indent=2), encoding="utf-8")


def pick_fresh(scored: list[ScoredArticle], posted: set[str]) -> ScoredArticle | None:
    """Retourne le meilleur article non déjà publié."""
    for s in scored:
        url = s.article.url.split("?")[0].rstrip("/")
        if url not in posted:
            return s
        log.info("Skipping already-posted URL: %s", url)
    return None


def run(dry_run: bool = False) -> int:
    log.info("=" * 60)
    log.info("LinkedIn bot start | dry_run=%s", dry_run)
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

        posted = load_cache()
        top = pick_fresh(scored, posted)
        if not top:
            log.error("All top articles already posted. Abort.")
            return 1

        log.info("Selected: [%.1f] %s", top.score, top.article.title)

        post = draft_post(top)
        log.info("\n%s\n", post)

        result = post_to_linkedin(post, dry_run=dry_run)

        if not dry_run and result:
            url = top.article.url.split("?")[0].rstrip("/")
            posted.add(url)
            save_cache(posted)
            log.info("URL cached to prevent re-posting: %s", url)

        log.info("Done.")
        return 0

    except Exception as e:
        log.exception("Pipeline failed: %s", e)
        return 2


def main():
    parser = argparse.ArgumentParser(description="LinkedIn daily post bot")
    parser.add_argument("--dry-run", action="store_true", help="Draft post but don't publish")
    args = parser.parse_args()

    setup_logging()
    sys.exit(run(dry_run=args.dry_run))


if __name__ == "__main__":
    main()
