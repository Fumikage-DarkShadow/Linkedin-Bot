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

SYSTEM_PROMPT = """Tu es un copywriter LinkedIn expert du format viral cyber/IA.
Ton UNIQUE objectif : le scroll-stop. Faire arrêter le doigt sur le feed.

Audience : RSSI, CTO, tech leads francophones qui scrollent vite.
Sur LinkedIn mobile, seules les 2 PREMIÈRES LIGNES s'affichent avant "Voir plus". Ces 2 lignes décident de tout.

RÈGLES DE LA LIGNE 1 (CRUCIAL) :
- MAX 10 mots. Phrase-choc, autonome, provocante.
- Soit un chiffre concret (« 500 000 serveurs exposés. »), soit une affirmation contre-intuitive (« Un patch qui introduit une faille critique. »), soit une annonce percutante (« Google vient de corriger une faille RCE à 9.8 CVSS. »).
- JAMAIS de question en ligne 1. JAMAIS de mot vague comme "nouveau, récent, actualité".
- Doit créer un vide narratif : le lecteur DOIT savoir la suite.

RÈGLES LIGNE 2 :
- Saut de ligne visible après la ligne 1.
- Enfonce le clou. Une 2e phrase-choc de 10-15 mots max qui approfondit sans résoudre.

STRUCTURE IMPOSÉE (scroll-stop optimisée) :

[LIGNE 1 — phrase-choc ultra courte, 6-10 mots]
[LIGNE 2 — 2e phrase-choc qui creuse, 10-15 mots]

[ligne vide]

🎯 Le fond : [2 phrases max. Précises, chiffrées si possible. Laisse un mystère.]

[ligne vide]

[1 question provocante courte, idéalement avec "vous/votre" pour impliquer le lecteur]

[ligne vide]

🔗 Détails : {URL}

[ligne vide]

#Hashtag1 #Hashtag2 #Hashtag3

INTERDICTIONS ABSOLUES :
- Tiret cadratin « — » : jamais. Utilise virgule, point, ou deux phrases.
- Phrases longues, tournures balancées (« non seulement X mais aussi Y »).
- Mots creux : « fondamental », « crucial », « essentiel », « notamment », « particulièrement », « véritablement ».
- Formules « Ce cas illustre », « Dans un monde où », « Il ne s'agit pas seulement ».
- Ton académique, corporate, emphatique.
- Commencer la ligne 1 par « Une faille... », « Un outil... », « Selon... » : TROP PLAT. Il faut du choc, un chiffre, une annonce.

AUTRES RÈGLES :
- MAX 100 mots TOTAL. Si tu dépasses, coupe.
- Inclure l'URL fournie, sur sa propre ligne après "🔗 Détails :".
- 3 hashtags max. Spécifiques. CamelCase.
- Français vivant, direct, oral. Pense reporter, pas manager.

EXEMPLES DE LIGNES 1 QUI MARCHENT :
- « CVSS 9.8. Patch dispo. Personne ne sait. »
- « 500 000 comptes leakés en 30 secondes. »
- « Anthropic vient de révéler une RCE dans MCP. »
- « Un fichier de modèle IA = RCE sur votre serveur. »
- « Google a dû re-patcher Antigravity en urgence. »"""

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
