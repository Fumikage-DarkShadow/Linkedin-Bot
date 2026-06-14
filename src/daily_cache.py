"""
Cache 'historique des posts' avec cadence minimale entre 2 publications.

Regles cumulatives :
  - Pas de post les samedi/dimanche (ALLOWED_WEEKDAYS).
  - Le dernier post doit dater d'au moins MIN_DAYS_BETWEEN_POSTS jours.
  - Un seul post par jour.

Le cache stocke la liste des dates ou un post a ete publie (posted_dates).
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from config import ROOT_DIR, MIN_DAYS_BETWEEN_POSTS, ALLOWED_WEEKDAYS

log = logging.getLogger(__name__)

CACHE_FILE = ROOT_DIR / "posted_today.json"
HISTORY_RETENTION_DAYS = 365  # on garde 1 an d'historique max


def _load() -> dict:
    if not CACHE_FILE.exists():
        return {"posted_dates": []}
    try:
        data = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
    except Exception as e:
        log.warning("Cache unreadable, starting fresh: %s", e)
        return {"posted_dates": []}

    # Migration douce de l'ancien format {"last_posted_date": "..."} vers le nouveau
    if "posted_dates" not in data:
        legacy = data.get("last_posted_date")
        data["posted_dates"] = [legacy] if legacy else []
    return data


def _save(data: dict) -> None:
    cutoff = (date.today() - timedelta(days=HISTORY_RETENTION_DAYS)).isoformat()
    data["posted_dates"] = sorted({d for d in data.get("posted_dates", []) if d and d >= cutoff})
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _last_post_date(posted_dates: list[str]) -> date | None:
    latest: date | None = None
    for s in posted_dates:
        try:
            d = date.fromisoformat(s)
        except ValueError:
            continue
        if latest is None or d > latest:
            latest = d
    return latest


def should_skip_today() -> tuple[bool, str]:
    """Determine si le run doit skiper aujourd'hui.
    Retourne (skip: bool, raison: str)."""
    today = date.today()
    today_str = today.isoformat()

    if today.weekday() not in ALLOWED_WEEKDAYS:
        return True, f"weekend ({today.strftime('%A')}) - no post on Sat/Sun"

    data = _load()
    posted = data.get("posted_dates", [])

    if today_str in posted:
        return True, f"already posted today ({today_str})"

    last = _last_post_date(posted)
    if last is not None:
        days_since = (today - last).days
        if days_since < MIN_DAYS_BETWEEN_POSTS:
            remaining = MIN_DAYS_BETWEEN_POSTS - days_since
            return True, (
                f"cadence: last post {last.isoformat()} (J-{days_since}), "
                f"next eligible in {remaining}j (min {MIN_DAYS_BETWEEN_POSTS}j)"
            )

    return False, f"OK (last={last.isoformat() if last else 'never'}, weekday={today.strftime('%A')})"


def mark_posted_today(article_url: str = "") -> None:
    today_str = date.today().isoformat()
    data = _load()
    posted = data.get("posted_dates", [])
    if today_str not in posted:
        posted.append(today_str)
    data["posted_dates"] = posted
    data["last_posted_date"] = today_str
    data["last_article_url"] = article_url
    _save(data)
    log.info("Marked posted for %s. Next eligible in %d days.",
             today_str, MIN_DAYS_BETWEEN_POSTS)


# Compat retro : has_posted_today reste utilisable mais should_skip_today est plus complet.
def has_posted_today() -> bool:
    skip, reason = should_skip_today()
    if skip:
        log.info("Skipping: %s", reason)
    return skip
