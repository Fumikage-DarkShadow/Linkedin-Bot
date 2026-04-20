"""
Scoring heuristique (fallback sans LLM).

Score sur 10 = poids source + mots-clés impact + fraîcheur.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from dataclasses import dataclass

from sourcing import Article

log = logging.getLogger(__name__)

SOURCE_WEIGHT = {
    "bleepingcomputer.com": 2.5,
    "thehackernews.com":    2.5,
    "krebsonsecurity.com":  2.8,
    "darkreading.com":      2.2,
    "techcrunch.com":       2.3,
    "theverge.com":         2.0,
    "venturebeat.com":      2.0,
}

IMPACT_KEYWORDS = {
    # Critique cyber (+3)
    "zero-day": 3.0, "rce": 3.0, "critical vulnerability": 3.0, "wormable": 3.0,
    "mass exploitation": 3.0, "exploited in the wild": 3.0,
    # Cyber fort (+2)
    "breach": 2.0, "ransomware": 2.0, "malware": 1.5, "backdoor": 2.0,
    "data leak": 2.0, "vulnerability": 1.5, "patch": 1.0, "supply chain": 2.5,
    "phishing": 1.0, "hack": 1.5, "attack": 1.2,
    # IA rupture (+3)
    "gpt-5": 3.0, "claude 5": 3.0, "breakthrough": 2.5, "agi": 2.5,
    "state-of-the-art": 2.0,
    # IA business (+2)
    "acquires": 2.0, "acquisition": 2.0, "ipo": 2.5, "raises": 1.8,
    "billion": 2.2, "funding": 1.5, "unicorn": 2.0,
    # Dégraissages (-1)
    "rumor": -1.0, "leaked": -0.5, "allegedly": -1.0,
}

HASHTAG_RULES = {
    "cybersecurity": ["#Cybersécurité", "#CyberSecurity", "#InfoSec"],
    "ai":            ["#IA", "#AI", "#ArtificialIntelligence"],
}

CONTEXTUAL_HASHTAGS = {
    "ransomware": "#Ransomware",
    "breach":     "#DataBreach",
    "vulnerability": "#Vulnerability",
    "zero-day":   "#ZeroDay",
    "llm":        "#LLM",
    "openai":     "#OpenAI",
    "anthropic":  "#Anthropic",
    "microsoft":  "#Microsoft",
    "google":     "#Google",
    "apple":      "#Apple",
}


@dataclass
class ScoredArticle:
    article: Article
    score: float
    reason: str


def _keyword_score(text: str) -> tuple[float, list[str]]:
    text_low = text.lower()
    hits: list[str] = []
    total = 0.0
    for kw, w in IMPACT_KEYWORDS.items():
        if kw in text_low:
            total += w
            hits.append(f"{kw}:+{w}")
    return min(total, 6.0), hits  # cap keyword bonus at 6


def _recency_score(published: datetime) -> float:
    """Bonus fraîcheur : +1 si <6h, +0.5 si <12h, 0 sinon."""
    now = datetime.now(timezone.utc)
    age_h = (now - published).total_seconds() / 3600
    if age_h < 6:
        return 1.0
    if age_h < 12:
        return 0.5
    return 0.0


def score_article(a: Article) -> ScoredArticle:
    source_s = SOURCE_WEIGHT.get(a.source, 1.5)
    kw_s, hits = _keyword_score(f"{a.title} {a.summary}")
    recency_s = _recency_score(a.published)
    total = source_s + kw_s + recency_s
    total = max(0.0, min(total, 10.0))
    reason = f"source={source_s:.1f} + kw={kw_s:.1f} ({','.join(hits[:3]) or '-'}) + recency={recency_s:.1f}"
    return ScoredArticle(article=a, score=total, reason=reason)


def score_articles(articles: list[Article]) -> list[ScoredArticle]:
    scored = [score_article(a) for a in articles]
    scored.sort(key=lambda s: s.score, reverse=True)
    if scored:
        log.info("Top heuristique = %.1f | %s", scored[0].score, scored[0].article.title[:80])
    return scored


def suggest_hashtags(scored: ScoredArticle, n: int = 5) -> list[str]:
    tags = list(HASHTAG_RULES.get(scored.article.category, []))
    low = (scored.article.title + " " + scored.article.summary).lower()
    for kw, tag in CONTEXTUAL_HASHTAGS.items():
        if kw in low and tag not in tags:
            tags.append(tag)
    tags.append("#Tech")
    return tags[:n]


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from sourcing import fetch_news
    items = fetch_news()
    scored = score_articles(items)
    print(f"\n=== Top 5 (heuristique) ===\n")
    for s in scored[:5]:
        safe = s.article.title.encode("ascii", "replace").decode("ascii")[:70]
        print(f"{s.score:4.1f} | {s.article.source:22s} | {safe}")
        print(f"       {s.reason}\n")
