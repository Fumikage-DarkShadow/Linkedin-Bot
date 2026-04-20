"""
Étape 2 — Scoring d'impact via Claude Sonnet 4.6.

Prend la liste d'articles produite par sourcing.py et note chacun de 0 à 10
selon 5 critères d'impact (rupture tech, portée, gravité, nouveauté, pertinence B2B).
Retourne le top 1 + top 5 pour contexte/log.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY
from sourcing import Article

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Tu es un analyste senior en veille tech spécialisé IA & Cybersécurité.
Ton job : noter l'impact business/industriel d'actualités pour un post LinkedIn pro.

SUJETS PRIORITAIRES (les seuls qui méritent >6/10) :
1. Cyberattaques majeures (groupes APT, ransomware, infrastructures critiques)
2. Fuites de données / breaches (volume massif, entreprise connue, données sensibles)
3. Zero-day exploité in-the-wild (CVE critique, RCE, privilège escalation)
4. Ruptures IA (modèle majeur, vulnérabilité d'un LLM/agent, régulation structurante)
5. Vulnérabilités critiques largement exploitables (type Log4Shell, supply chain)

Critères de scoring (0-10) :
- 9-10 : rupture massive — zero-day exploité, breach >1M comptes, cyberattaque infra critique, faille AI system large
- 7-8  : impact fort — vulnérabilité critique confirmée, breach notable, APT actif, modèle IA majeur
- 5-6  : actualité solide dans les 5 sujets prioritaires mais portée plus limitée
- 3-4  : news de niche, recap hebdo, rumeur, ou sujet hors priorités
- 0-2  : off-topic total (gadgets, gaming, lifestyle, company blog), clickbait, pur commentaire

Règle dure : si l'article n'entre dans AUCUN des 5 sujets prioritaires, score MAX = 3.
Règle dure : un weekly recap ou un article d'opinion plafonne à 4, même si bien écrit.

Tu réponds UNIQUEMENT en JSON valide, sans texte avant/après."""

USER_PROMPT_TEMPLATE = """Voici {n} articles des dernières 24h. Note chacun et renvoie un JSON :

{{
  "rankings": [
    {{"id": 0, "score": 8.5, "reason": "faille RCE dans MCP d'Anthropic, portée large"}},
    ...
  ]
}}

Articles :
{articles}"""


@dataclass
class ScoredArticle:
    article: Article
    score: float
    reason: str


def _format_articles(articles: list[Article]) -> str:
    lines = []
    for i, a in enumerate(articles):
        lines.append(
            f"[{i}] ({a.category}) {a.source} — {a.title}\n"
            f"    Résumé: {a.summary[:300]}"
        )
    return "\n\n".join(lines)


def score_articles(articles: list[Article]) -> list[ScoredArticle]:
    """Envoie les articles au LLM, récupère les scores, trie par score desc."""
    if not articles:
        log.warning("No articles to score.")
        return []
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot score articles.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    prompt = USER_PROMPT_TEMPLATE.format(n=len(articles), articles=_format_articles(articles))

    log.info("Sending %d articles to Claude for scoring...", len(articles))
    resp = client.messages.create(
        model=MODEL,
        max_tokens=2048,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = resp.content[0].text.strip()
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        log.error("Failed to parse LLM response as JSON: %s\nRaw: %s", e, raw[:500])
        raise

    by_id = {i: a for i, a in enumerate(articles)}
    scored = [
        ScoredArticle(article=by_id[r["id"]], score=float(r["score"]), reason=r.get("reason", ""))
        for r in data.get("rankings", [])
        if r["id"] in by_id
    ]
    scored.sort(key=lambda s: s.score, reverse=True)
    log.info("Scored %d articles. Top = %.1f (%s)", len(scored), scored[0].score, scored[0].article.title[:80])
    return scored


def select_top(articles: list[Article]) -> ScoredArticle | None:
    """Renvoie l'article avec le meilleur score d'impact."""
    scored = score_articles(articles)
    return scored[0] if scored else None


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
    from sourcing import fetch_news
    items = fetch_news()
    scored = score_articles(items)
    print(f"\n=== Top 5 articles ===\n")
    for s in scored[:5]:
        safe_title = s.article.title.encode("ascii", "replace").decode("ascii")[:80]
        print(f"{s.score:4.1f} | {s.article.source:22s} | {safe_title}")
        print(f"       -> {s.reason[:120]}\n")
