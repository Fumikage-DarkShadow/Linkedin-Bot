"""
Publication via webhook Make.com (ou Zapier).

Make.com reçoit le JSON, authentifie LinkedIn en interne, poste sur ton profil.
Pas d'app LinkedIn à créer — Make gère l'OAuth.

.env requis :
  MAKE_WEBHOOK_URL=https://hook.eu2.make.com/xxxxxxxxxxxxxxxxx
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)


def post_to_webhook(
    post_text: str,
    source_title: str,
    source_url: str,
    score: float,
    category: str,
    image_url: str | None = None,
    *,
    dry_run: bool = False,
) -> dict | None:
    """POST le payload JSON au webhook Make.com."""
    if dry_run:
        log.info("[DRY-RUN] Webhook NOT called. Payload:\n  text=%s...\n  source=%s\n  image=%s",
                 post_text[:100], source_title, image_url)
        return {"dry_run": True}

    url = os.getenv("MAKE_WEBHOOK_URL")
    if not url:
        raise RuntimeError("MAKE_WEBHOOK_URL missing in .env")

    payload = {
        "text": post_text,
        "source_title": source_title,
        "source_url": source_url,
        "score": round(score, 1),
        "category": category,
        "image_url": image_url or "",
    }

    log.info("POST → Make.com webhook (%s chars, image=%s)...", len(post_text), bool(image_url))
    r = requests.post(url, json=payload, timeout=20)

    if r.status_code >= 400:
        log.error("Webhook error %d: %s", r.status_code, r.text[:300])
        r.raise_for_status()

    log.info("Webhook OK (status=%d, resp=%s)", r.status_code, r.text[:200])
    return {"status": r.status_code, "body": r.text}


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    result = post_to_webhook(
        post_text="Test payload depuis publisher_webhook.\n\n#Test",
        source_title="Test source",
        source_url="https://example.com",
        score=8.5,
        category="cybersecurity",
        dry_run=not bool(os.getenv("MAKE_WEBHOOK_URL")),
    )
    print("Result:", result)
