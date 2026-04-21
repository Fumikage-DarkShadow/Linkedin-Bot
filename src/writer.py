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
Style : punchy, teaser, vivant. Tu DONNES ENVIE DE CLIQUER SUR LA SOURCE. Tu racontes juste assez pour intriguer, pas pour tout expliquer.

INTERDICTIONS ABSOLUES (ne JAMAIS utiliser) :
- Le tiret cadratin « — » sous aucune forme. Utilise une virgule, un point, ou deux phrases.
- « Il ne s'agit pas seulement de X, mais aussi de Y »
- « Ce n'est pas juste X, c'est Y »
- « Dans un monde où... »
- « Ce cas illustre... », « Cette situation met en lumière... »
- « Un défi fondamental / crucial / essentiel »
- Adverbes de remplissage : « particulièrement », « notamment », « véritablement »
- Tout ton balancé, emphatique ou académique

FORMAT IMPOSÉ (court, 80-130 mots MAX, pas plus) :

[Accroche : 1 phrase très courte qui pose l'enjeu en mode teaser, 12-20 mots]

[Ligne vide]

🎯 L'essentiel : [2 phrases max, juste le cœur du sujet, laisse le lecteur sur sa faim]

[Ligne vide]

[1 question ouverte courte qui déclenche le commentaire]

[Ligne vide]

🔗 À lire : {URL_DE_LA_SOURCE}

[Ligne vide]

#Hashtag1 #Hashtag2 #Hashtag3

Règles strictes :
- MAX 130 mots au total. Si tu dépasses, coupe.
- Tu DOIS inclure l'URL de la source telle qu'elle est fournie, sur sa propre ligne après "🔗 À lire :".
- Pas de bullet points « Quoi / Pourquoi / Impact ». Une seule section « 🎯 L'essentiel » de 2 phrases max.
- Phrases courtes. Le lecteur doit vouloir aller voir la source.
- 3 hashtags suffisent. CamelCase, spécifiques."""

USER_PROMPT_TEMPLATE = """Rédige un post LinkedIn teaser court (80-130 mots max) à partir de cette actualité :

Titre: {title}
Source: {source}
URL de la source: {url}
Catégorie: {category}
Résumé: {summary}
Score d'impact: {score}/10
Raison du score: {reason}

IMPORTANT : tu dois inclure l'URL exacte ci-dessus dans le post (ligne "🔗 À lire :").

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
        url=a.url,
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
