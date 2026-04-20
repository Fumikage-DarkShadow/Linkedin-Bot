"""
Writer template (fallback sans LLM).

Génère un post LinkedIn formaté à partir du titre/résumé + hashtags heuristiques.
Qualité moindre qu'un LLM, mais structure correcte et zéro coût.
"""
from __future__ import annotations

import logging
import re

from scoring_rules import ScoredArticle, suggest_hashtags

log = logging.getLogger(__name__)

CATEGORY_HOOKS = {
    "cybersecurity": [
        "Encore une actualité cyber qui devrait retenir l'attention des RSSI :",
        "Alerte cybersécurité du jour — à ne pas sous-estimer :",
        "Veille cyber : un sujet qui va faire parler cette semaine.",
    ],
    "ai": [
        "L'IA ne dort jamais — voici l'actualité marquante du jour :",
        "Mouvement significatif côté IA ce matin :",
        "Veille IA : une info qui mérite qu'on s'y attarde.",
    ],
}

CATEGORY_QUESTIONS = {
    "cybersecurity": "Comment votre organisation anticipe-t-elle ce type de menace ?",
    "ai": "Quel impact voyez-vous pour votre secteur ?",
}


def _clean(text: str) -> str:
    text = re.sub(r"\s+", " ", text or "").strip()
    return text


def _first_sentence(text: str, max_len: int = 220) -> str:
    text = _clean(text)
    if not text:
        return ""
    # Coupe à la première ponctuation forte
    m = re.search(r"[.!?]\s", text)
    if m and m.end() < max_len:
        return text[:m.end()].strip()
    return text[:max_len].rstrip() + ("…" if len(text) > max_len else "")


def draft_post(scored: ScoredArticle) -> str:
    """Construit un post LinkedIn à partir du template."""
    a = scored.article
    cat = a.category
    hook_pool = CATEGORY_HOOKS.get(cat, CATEGORY_HOOKS["cybersecurity"])
    # Choix déterministe basé sur score pour variabilité sans aléa
    hook = hook_pool[int(scored.score * 10) % len(hook_pool)]

    title = _clean(a.title)
    summary = _first_sentence(a.summary, 300)

    quoi = title if title.endswith((".", "!", "?")) else title + "."
    pourquoi = summary or f"Remonté par {a.source}, cette actualité mérite attention pour son potentiel de propagation."
    impact_template = (
        "Les équipes sécurité doivent mesurer leur exposition et prioriser les actions défensives."
        if cat == "cybersecurity"
        else "Les organisations vont devoir intégrer cette évolution dans leur stratégie tech."
    )

    question = CATEGORY_QUESTIONS.get(cat, "Qu'en pensez-vous ?")
    hashtags = " ".join(suggest_hashtags(scored, n=5))

    post = (
        f"{hook} {title}\n"
        f"\n"
        f"🎯 Quoi : {quoi}\n"
        f"🧠 Pourquoi : {pourquoi}\n"
        f"💥 Impact : {impact_template}\n"
        f"\n"
        f"{question}\n"
        f"\n"
        f"Source : {a.source}\n"
        f"\n"
        f"{hashtags}"
    )
    log.info("Template post drafted (%d chars).", len(post))
    return post


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from sourcing import fetch_news
    from scoring_rules import score_articles
    items = fetch_news()
    scored = score_articles(items)
    if scored:
        print("\n" + "=" * 70)
        print(draft_post(scored[0]))
        print("=" * 70)
