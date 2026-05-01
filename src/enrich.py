"""
Recuperation d'image pour le post LinkedIn.

Ordre de priorite :
  1. Image extraite du flux RSS (Article.rss_image_url) -> souvent fiable, l'image officielle de l'article
  2. og:image / twitter:image scrape de la page (avec rotation User-Agent contre les 403)
  3. Fallback aleatoire mais deterministe (hash URL) parmi 8 images Unsplash par categorie
"""
from __future__ import annotations

import hashlib
import logging
import re
from urllib.parse import urljoin

import requests

log = logging.getLogger(__name__)

# Pool de fallbacks Unsplash, choix base sur hash URL = meme article -> meme image, articles differents -> images differentes
FALLBACK_IMAGES = {
    "cybersecurity": [
        "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?w=1200&h=630&fit=crop",  # circuit
        "https://images.unsplash.com/photo-1563206767-5b18f218e8de?w=1200&h=630&fit=crop",  # red hacker
        "https://images.unsplash.com/photo-1614064641938-3bbee52942c7?w=1200&h=630&fit=crop",  # binary
        "https://images.unsplash.com/photo-1526374965328-7f61d4dc18c5?w=1200&h=630&fit=crop",  # matrix
        "https://images.unsplash.com/photo-1518770660439-4636190af475?w=1200&h=630&fit=crop",  # circuit dark
        "https://images.unsplash.com/photo-1551808525-51a94da548ce?w=1200&h=630&fit=crop",  # padlock
        "https://images.unsplash.com/photo-1510511459019-5dda7724fd87?w=1200&h=630&fit=crop",  # tech blue
        "https://images.unsplash.com/photo-1544197150-b99a580bb7a8?w=1200&h=630&fit=crop",  # server room
    ],
    "ai": [
        "https://images.unsplash.com/photo-1677442136019-21780ecad995?w=1200&h=630&fit=crop",  # chatgpt
        "https://images.unsplash.com/photo-1620712943543-bcc4688e7485?w=1200&h=630&fit=crop",  # robot ai
        "https://images.unsplash.com/photo-1655720033654-a4239dd42d10?w=1200&h=630&fit=crop",  # neural net
        "https://images.unsplash.com/photo-1635070041078-e363dbe005cb?w=1200&h=630&fit=crop",  # ai brain
        "https://images.unsplash.com/photo-1593376853899-fbb47a057fa0?w=1200&h=630&fit=crop",  # circuit ai
        "https://images.unsplash.com/photo-1531746790731-6c087fecd65a?w=1200&h=630&fit=crop",  # particles
        "https://images.unsplash.com/photo-1487058792275-0ad4aaf24ca7?w=1200&h=630&fit=crop",  # code
        "https://images.unsplash.com/photo-1488229297570-58520851e868?w=1200&h=630&fit=crop",  # data viz
    ],
}

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",  # social bot, souvent autorise
    "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
]

OG_PATTERNS = [
    re.compile(r'<meta\s+property=["\']og:image(?::secure_url)?["\']\s+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<link\s+rel=["\']image_src["\']\s+href=["\']([^"\']+)["\']', re.IGNORECASE),
]


def _build_headers(ua: str) -> dict:
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }


def _normalize(img: str, base_url: str) -> str:
    img = img.strip()
    if img.startswith("//"):
        return "https:" + img
    if img.startswith("/"):
        return urljoin(base_url, img)
    return img


def fetch_og_image(url: str, timeout: int = 10) -> str | None:
    """Scrape og:image / twitter:image avec rotation User-Agent en cas de 403."""
    if not url:
        return None
    for ua in USER_AGENTS:
        try:
            r = requests.get(url, headers=_build_headers(ua), timeout=timeout, allow_redirects=True)
            if r.status_code == 403:
                log.debug("403 with UA %s, trying next", ua[:30])
                continue
            r.raise_for_status()
            html = r.text[:80_000]
            for pattern in OG_PATTERNS:
                match = pattern.search(html)
                if match:
                    img = _normalize(match.group(1), url)
                    log.info("og:image found via UA=%s: %s", ua[:20], img[:80])
                    return img
            log.debug("No og:image on %s with UA %s", url, ua[:30])
            return None  # page lue mais pas d'og, inutile de retenter
        except Exception as e:
            log.debug("og:image fetch failed (UA=%s): %s", ua[:20], e)
            continue
    log.warning("All UAs failed for %s", url)
    return None


def _hashed_fallback(article_url: str, category: str) -> str:
    pool = FALLBACK_IMAGES.get(category) or FALLBACK_IMAGES["cybersecurity"]
    h = int(hashlib.md5(article_url.encode("utf-8")).hexdigest(), 16)
    return pool[h % len(pool)]


def get_image_with_fallback(
    article_url: str,
    category: str = "cybersecurity",
    rss_image_url: str = "",
) -> str:
    """Strategie complete : RSS image > og:image > fallback hash-base.
    Garantit toujours une URL d'image."""
    # 1. Image du flux RSS (plus fiable et c'est l'image officielle de l'article)
    if rss_image_url:
        log.info("Using RSS image: %s", rss_image_url[:80])
        return rss_image_url

    # 2. og:image scrape
    img = fetch_og_image(article_url)
    if img:
        return img

    # 3. Fallback hash-base (image differente selon l'URL de l'article)
    fallback = _hashed_fallback(article_url, category)
    log.info("Using hashed fallback for category=%s: %s", category, fallback[:80])
    return fallback


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://thehackernews.com/"
    print("Image:", get_image_with_fallback(test_url, "cybersecurity"))
