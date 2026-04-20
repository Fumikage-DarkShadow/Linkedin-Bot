"""
Étape 3 — Rédaction du post LinkedIn via Claude Sonnet 4.6.

Format imposé :
  - Accroche (1 phrase percutante)
  - 3 bullet points : Quoi / Pourquoi / Impact
  - Question ouverte
  - 3-5 hashtags
"""
from __future__ import annotations

import logging

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY
from scoring import ScoredArticle

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """Tu es un créateur de contenu LinkedIn B2B spécialisé IA & Cybersécurité.
Ton audience : CTO, RSSI, dirigeants tech francophones.
Style : direct, factuel, humain. Pas de corporate-speak. Pas d'emojis à outrance (0-2 max).

INTERDICTIONS ABSOLUES (ne JAMAIS utiliser) :
- Le tiret cadratin « — » sous aucune forme. Utilise une virgule, un point, ou deux phrases distinctes.
- « Il ne s'agit pas seulement de X, mais aussi de Y »
- « Ce n'est pas juste X, c'est Y »
- « Dans un monde où... »
- « Ce cas illustre... », « Cette situation met en lumière... »
- « Un défi fondamental / crucial / essentiel »
- « L'industrialisation de... »
- Les phrases balancées style "Non seulement X, mais aussi Y"
- Les adverbes ajoutés pour meubler : "particulièrement", "notamment", "véritablement"
- Toute formule qui sonne générée (balancée, emphatique, abstraite)

Tu respectes STRICTEMENT ce format :

[Accroche : 1 phrase punchy qui pose l'enjeu, 15-25 mots]

[Ligne vide]

🎯 Quoi : [1 phrase, le fait, concret]
🧠 Pourquoi : [1 phrase, la cause réelle]
💥 Impact : [1 phrase, conséquence chiffrée ou opérationnelle si possible]

[Ligne vide]

[Question ouverte pour engagement, 1 phrase courte]

[Ligne vide]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4

Règles :
- Tout en français courant, vivant, pas académique.
- 150-220 mots max.
- Cite la source par son nom (ex: "selon BleepingComputer") dans l'accroche ou le Quoi.
- Phrases courtes. Ponctuation simple (point, virgule, deux-points).
- Pas de lien URL (LinkedIn pénalise).
- Hashtags en CamelCase, pertinents et spécifiques."""

USER_PROMPT_TEMPLATE = """Rédige un post LinkedIn à partir de cette actualité :

Titre: {title}
Source: {source}
Catégorie: {category}
Résumé: {summary}
Score d'impact: {score}/10
Raison du score: {reason}

Produis UNIQUEMENT le post, rien d'autre."""


def draft_post(scored: ScoredArticle) -> str:
    """Génère le texte du post LinkedIn."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot draft post.")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    a = scored.article
    prompt = USER_PROMPT_TEMPLATE.format(
        title=a.title,
        source=a.source,
        category=a.category,
        summary=a.summary,
        score=scored.score,
        reason=scored.reason,
    )

    log.info("Drafting LinkedIn post for: %s", a.title[:80])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    post = resp.content[0].text.strip()
    log.info("Post drafted (%d chars)", len(post))
    return post


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
    from scoring import select_top

    items = fetch_news()
    top = select_top(items)
    if top:
        post = draft_post(top)
        print("\n" + "=" * 70)
        print("POST LINKEDIN GENERE")
        print("=" * 70 + "\n")
        print(post)
        print("\n" + "=" * 70)
