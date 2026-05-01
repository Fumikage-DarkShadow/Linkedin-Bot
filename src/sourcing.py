"""
Étape 1 — Récupération des news IA & Cybersécurité des dernières 24h.

Combine :
  - Flux RSS (BleepingComputer, TheHackerNews, KrebsOnSecurity, TechCrunch AI, TheVerge AI, VentureBeat…)
  - NewsAPI (fallback + élargissement couverture)

Sortie : liste de dicts normalisés, dédupliqués, triés par date desc.
    { "title", "summary", "url", "source", "published", "category" }
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Iterable
from urllib.parse import urlparse

import feedparser
import requests

from config import (
    RSS_FEEDS,
    NEWSAPI_KEY,
    NEWSAPI_QUERIES,
    LOOKBACK_HOURS,
    MAX_ARTICLES_PER_SOURCE,
)

log = logging.getLogger(__name__)


@dataclass
class Article:
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    category: str
    rss_image_url: str = ""  # image extraite du flux RSS si presente (souvent fiable)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["published"] = self.published.isoformat()
        return d


def _extract_rss_image(entry) -> str:
    """Extrait une URL d'image depuis une entree RSS (media:thumbnail, media:content, enclosure, content/summary).
    Retourne une string vide si rien trouve."""
    import re

    # 1. media:thumbnail (TechCrunch, BleepingComputer)
    thumbs = entry.get("media_thumbnail") or []
    for t in thumbs:
        if isinstance(t, dict) and t.get("url"):
            return t["url"]

    # 2. media:content (souvent VentureBeat, TheVerge)
    contents = entry.get("media_content") or []
    for c in contents:
        if isinstance(c, dict) and c.get("url"):
            url = c["url"]
            type_ = (c.get("type") or "").lower()
            if not type_ or type_.startswith("image/"):
                return url

    # 3. enclosure (RSS standard)
    for link in entry.get("links") or []:
        if isinstance(link, dict) and link.get("rel") == "enclosure":
            type_ = (link.get("type") or "").lower()
            if type_.startswith("image/") and link.get("href"):
                return link["href"]

    # 4. img dans content ou summary HTML
    html_blobs = []
    contents_html = entry.get("content") or []
    for c in contents_html:
        if isinstance(c, dict) and c.get("value"):
            html_blobs.append(c["value"])
    if entry.get("summary"):
        html_blobs.append(entry.get("summary"))
    for html in html_blobs:
        m = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', html, re.IGNORECASE)
        if m:
            return m.group(1)

    return ""


def _parse_date(raw) -> datetime | None:
    """Normalise les formats de date variés des flux RSS en datetime UTC."""
    if not raw:
        return None
    try:
        if isinstance(raw, time.struct_time):
            return datetime.fromtimestamp(time.mktime(raw), tz=timezone.utc)
        if isinstance(raw, str):
            dt = parsedate_to_datetime(raw)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
    except Exception as e:
        log.debug("parse_date failed for %r: %s", raw, e)
    return None


def _clean_summary(text: str, limit: int = 500) -> str:
    """Retire les tags HTML basiques et tronque."""
    import re
    text = re.sub(r"<[^>]+>", "", text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text[:limit]


def fetch_rss(category: str, feeds: list[str], cutoff: datetime) -> list[Article]:
    """Récupère les articles d'une liste de flux RSS, filtrés par date."""
    articles: list[Article] = []
    for feed_url in feeds:
        try:
            parsed = feedparser.parse(feed_url)
            source = urlparse(feed_url).netloc.replace("www.", "")
            kept = 0
            for entry in parsed.entries[:MAX_ARTICLES_PER_SOURCE * 2]:
                published = _parse_date(
                    entry.get("published_parsed") or entry.get("published")
                    or entry.get("updated_parsed") or entry.get("updated")
                )
                if not published or published < cutoff:
                    continue
                articles.append(Article(
                    title=(entry.get("title") or "").strip(),
                    summary=_clean_summary(entry.get("summary", "")),
                    url=entry.get("link", ""),
                    source=source,
                    published=published,
                    category=category,
                    rss_image_url=_extract_rss_image(entry),
                ))
                kept += 1
                if kept >= MAX_ARTICLES_PER_SOURCE:
                    break
            log.info("RSS %s → %d articles (24h)", source, kept)
        except Exception as e:
            log.warning("RSS fetch failed for %s: %s", feed_url, e)
    return articles


def fetch_newsapi(queries: Iterable[str], cutoff: datetime) -> list[Article]:
    """Récupère les articles via NewsAPI (optionnel, activé si clé présente)."""
    if not NEWSAPI_KEY:
        log.info("NEWSAPI_KEY absent, skip NewsAPI.")
        return []
    articles: list[Article] = []
    from_iso = cutoff.strftime("%Y-%m-%dT%H:%M:%S")
    for q in queries:
        try:
            r = requests.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": q,
                    "from": from_iso,
                    "sortBy": "popularity",
                    "language": "en",
                    "pageSize": MAX_ARTICLES_PER_SOURCE,
                },
                headers={"X-Api-Key": NEWSAPI_KEY},
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            category = "cybersecurity" if "cyber" in q.lower() or "ransomware" in q.lower() else "ai"
            for it in data.get("articles", []):
                published = _parse_date(it.get("publishedAt"))
                if not published or published < cutoff:
                    continue
                articles.append(Article(
                    title=(it.get("title") or "").strip(),
                    summary=_clean_summary(it.get("description") or ""),
                    url=it.get("url", ""),
                    source=(it.get("source") or {}).get("name", "newsapi"),
                    published=published,
                    category=category,
                ))
            log.info("NewsAPI q=%r → %d articles", q, len(data.get("articles", [])))
        except Exception as e:
            log.warning("NewsAPI query failed (%s): %s", q, e)
    return articles


def dedupe(articles: list[Article]) -> list[Article]:
    """Supprime les doublons par URL puis par titre normalisé."""
    seen_urls, seen_titles, out = set(), set(), []
    for a in articles:
        url_key = a.url.split("?")[0].rstrip("/")
        title_key = a.title.lower().strip()
        if not url_key or not title_key:
            continue
        if url_key in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url_key)
        seen_titles.add(title_key)
        out.append(a)
    return out


def fetch_news() -> list[Article]:
    """Point d'entrée principal : récupère, filtre, dédoublonne, trie."""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=LOOKBACK_HOURS)
    log.info("Fetching news since %s", cutoff.isoformat())

    all_articles: list[Article] = []
    for category, feeds in RSS_FEEDS.items():
        all_articles.extend(fetch_rss(category, feeds, cutoff))
    all_articles.extend(fetch_newsapi(NEWSAPI_QUERIES, cutoff))

    unique = dedupe(all_articles)
    unique.sort(key=lambda a: a.published, reverse=True)
    log.info("Total: %d articles after dedupe (from %d)", len(unique), len(all_articles))
    return unique


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    items = fetch_news()
    print(f"\n=== {len(items)} articles trouves ===\n")
    for a in items[:15]:
        safe_title = a.title.encode("ascii", "replace").decode("ascii")[:90]
        print(f"[{a.category:14s}] {a.source:25s} | {a.published:%Y-%m-%d %H:%M} | {safe_title}")
