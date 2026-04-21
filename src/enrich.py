"""
Enrichissement d'article : récupère l'image Open Graph (og:image) de la page source.

Utile pour ajouter une image au post LinkedIn et augmenter l'engagement.
"""
from __future__ import annotations

import logging
import re
from urllib.parse import urljoin

import requests

log = logging.getLogger(__name__)

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"

HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
}

OG_PATTERNS = [
    re.compile(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']', re.IGNORECASE),
    re.compile(r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']', re.IGNORECASE),
    re.compile(r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']', re.IGNORECASE),
]


def fetch_og_image(url: str, timeout: int = 10) -> str | None:
    """Retourne l'URL de l'image Open Graph d'un article, ou None si introuvable."""
    if not url:
        return None
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, allow_redirects=True)
        r.raise_for_status()
        html = r.text[:50_000]  # on lit juste le début, og est dans le <head>
        for pattern in OG_PATTERNS:
            match = pattern.search(html)
            if match:
                img = match.group(1).strip()
                if img.startswith("//"):
                    img = "https:" + img
                elif img.startswith("/"):
                    img = urljoin(url, img)
                log.info("og:image found: %s", img[:100])
                return img
        log.info("No og:image found on %s", url)
    except Exception as e:
        log.warning("Failed to fetch og:image from %s: %s", url, e)
    return None


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    test_url = sys.argv[1] if len(sys.argv) > 1 else "https://thehackernews.com/"
    print("Image:", fetch_og_image(test_url))
