"""
Cache simple 'un post par jour'.
Stocke la date du dernier post reussi dans posted_today.json (commite dans le repo).
"""
from __future__ import annotations

import json
import logging
from datetime import date
from pathlib import Path

from config import ROOT_DIR

log = logging.getLogger(__name__)

CACHE_FILE = ROOT_DIR / "posted_today.json"


def _load() -> dict:
    if not CACHE_FILE.exists():
        return {}
    try:
        return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Cache unreadable, starting fresh: %s", e)
        return {}


def has_posted_today() -> bool:
    data = _load()
    today = date.today().isoformat()
    posted = data.get("last_posted_date") == today
    if posted:
        log.info("Already posted today (%s). Skipping.", today)
    return posted


def mark_posted_today(article_url: str = "") -> None:
    today = date.today().isoformat()
    CACHE_FILE.write_text(
        json.dumps({"last_posted_date": today, "last_article_url": article_url}, indent=2),
        encoding="utf-8",
    )
    log.info("Marked posted for %s (cache saved to %s).", today, CACHE_FILE.name)
