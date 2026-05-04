"""
Cache 'historique des posts' avec contraintes hebdomadaires.

Regles cumulatives :
  - Pas de post les samedi/dimanche (ALLOWED_WEEKDAYS).
  - Max MAX_POSTS_PER_WEEK posts entre lundi et vendredi (compteur reset chaque lundi).
  - Un seul post par jour.

Le compteur hebdomadaire utilise le numero de semaine ISO comme borne, mais comme
le weekend est exclu en amont, en pratique le quota porte uniquement sur lun-ven.

Le cache stocke la liste des dates ou un post a ete publie (posted_dates).
"""
from __future__ import annotations

import json
import logging
from datetime import date, timedelta
from pathlib import Path

from config import ROOT_DIR, MAX_POSTS_PER_WEEK, ALLOWED_WEEKDAYS

log = logging.getLogger(__name__)

CACHE_FILE = ROOT_DIR / "posted_today.json"
HISTORY_RETENTION_DAYS = 90  # on tronque l'historique au-dela pour ne pas faire enfler le fichier


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
    # Tronque l'historique aux N derniers jours
    cutoff = (date.today() - timedelta(days=HISTORY_RETENTION_DAYS)).isoformat()
    data["posted_dates"] = sorted({d for d in data.get("posted_dates", []) if d and d >= cutoff})
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _iso_week(d: date) -> tuple[int, int]:
    """Retourne (annee_iso, num_semaine_iso) pour une date donnee."""
    iso = d.isocalendar()
    return (iso[0], iso[1])


def _count_posts_this_week(posted_dates: list[str]) -> int:
    today = date.today()
    target_week = _iso_week(today)
    count = 0
    for s in posted_dates:
        try:
            d = date.fromisoformat(s)
        except ValueError:
            continue
        if _iso_week(d) == target_week:
            count += 1
    return count


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

    week_count = _count_posts_this_week(posted)
    if week_count >= MAX_POSTS_PER_WEEK:
        return True, f"weekly cap reached ({week_count}/{MAX_POSTS_PER_WEEK} for week {today.isocalendar()[1]})"

    return False, f"OK (week count {week_count}/{MAX_POSTS_PER_WEEK}, weekday={today.strftime('%A')})"


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
    log.info("Marked posted for %s. Week count: %d/%d.",
             today_str, _count_posts_this_week(posted), MAX_POSTS_PER_WEEK)


# Compat retro : has_posted_today reste utilisable mais should_skip_today est plus complet.
def has_posted_today() -> bool:
    skip, reason = should_skip_today()
    if skip:
        log.info("Skipping: %s", reason)
    return skip
