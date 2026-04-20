"""
Étape 4 — Publication via API LinkedIn (UGC Posts endpoint).

Prérequis (OAuth 2.0) :
  - App LinkedIn avec produit "Share on LinkedIn" ou "Community Management API"
  - Scopes : w_member_social (pour poster en tant qu'utilisateur)
  - Access token (expiration 60 jours)
  - User URN : urn:li:person:XXXXXXX

Helper en bas : récupération du User URN à partir du token.
"""
from __future__ import annotations

import logging

import requests

from config import LINKEDIN_ACCESS_TOKEN, LINKEDIN_USER_URN

log = logging.getLogger(__name__)

UGC_POSTS_URL = "https://api.linkedin.com/v2/ugcPosts"
ME_URL = "https://api.linkedin.com/v2/me"


def _headers(token: str) -> dict:
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Restli-Protocol-Version": "2.0.0",
    }


def post_to_linkedin(text: str, *, dry_run: bool = False) -> dict | None:
    """Publie le texte sur LinkedIn en tant que post personnel."""
    if dry_run:
        log.info("[DRY-RUN] LinkedIn post NOT sent. Preview:\n%s", text)
        return {"dry_run": True, "text": text}

    if not LINKEDIN_ACCESS_TOKEN or not LINKEDIN_USER_URN:
        raise RuntimeError("LINKEDIN_ACCESS_TOKEN or LINKEDIN_USER_URN missing in .env")

    payload = {
        "author": LINKEDIN_USER_URN,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }

    log.info("Posting to LinkedIn (author=%s)...", LINKEDIN_USER_URN)
    r = requests.post(UGC_POSTS_URL, headers=_headers(LINKEDIN_ACCESS_TOKEN), json=payload, timeout=20)

    if r.status_code >= 400:
        log.error("LinkedIn API error %d: %s", r.status_code, r.text[:500])
        r.raise_for_status()

    data = r.json() if r.content else {}
    post_id = data.get("id") or r.headers.get("x-restli-id")
    log.info("LinkedIn post published. id=%s", post_id)
    return {"id": post_id, "response": data}


def get_user_urn(token: str | None = None) -> str:
    """Helper : récupère le User URN à partir d'un access token.

    Usage unique, à la mise en place — colle le résultat dans .env (LINKEDIN_USER_URN).
    """
    token = token or LINKEDIN_ACCESS_TOKEN
    if not token:
        raise RuntimeError("No token provided.")
    r = requests.get(ME_URL, headers=_headers(token), timeout=15)
    r.raise_for_status()
    data = r.json()
    urn = f"urn:li:person:{data['id']}"
    log.info("Your User URN: %s", urn)
    return urn


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
    # Mode dry-run par défaut pour ce test standalone
    result = post_to_linkedin(
        "Test post LinkedIn (dry-run) — si tu vois ce message c'est que publisher.py fonctionne.",
        dry_run=True,
    )
    print("\nResult:", result)
