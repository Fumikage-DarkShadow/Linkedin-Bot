"""
Étape 3 — Rédaction du post LinkedIn via Claude Sonnet 4.6.

Pour éviter l'effet "template IA" (tous les posts identiques), on fait tourner
6 styles de post différents, choisis aléatoirement à chaque run. Chaque style a
sa propre structure (avec/sans emojis, hook différent, longueur variable).
"""
from __future__ import annotations

import logging
import random

from anthropic import Anthropic

from config import ANTHROPIC_API_KEY
from scoring import ScoredArticle

log = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-6"

# Règles universelles : qualité + anti-signature-IA. Valent pour TOUS les styles.
SYSTEM_PROMPT = """Tu es un rédacteur LinkedIn francophone spécialisé tech (IA, cybersécurité).
Tu écris comme un humain qui connaît son sujet, pas comme un outil de génération de contenu.
Ton public : RSSI, CTO, ingénieurs, qui scrollent vite sur mobile.

OBJECTIF : un post qui arrête le scroll et donne envie de cliquer la source. La 1re ligne décide de tout (seules 2 lignes s'affichent avant "Voir plus").

INTERDICTIONS ABSOLUES (ce sont les tics qui font "écrit par une IA") :
- Tiret cadratin « — » : jamais. Virgule, point, ou deux phrases.
- Tournures balancées : « non seulement X mais aussi Y », « ce n'est pas X, c'est Y ».
- Mots creux : « fondamental », « crucial », « essentiel », « notamment », « particulièrement », « véritablement », « à l'ère de », « dans un monde où ».
- Formules de dissertation : « Ce cas illustre », « Cette actualité met en lumière », « force est de constater ».
- Conclusions moralisatrices génériques (« la sécurité est l'affaire de tous », « restons vigilants »).
- Ouvrir par « Une faille... », « Un nouveau... », « Selon... » : trop plat.

STYLE :
- Français parlé, direct, nerveux. Phrases courtes. Du concret, des chiffres, des noms.
- Varie ton vocabulaire et ta syntaxe. Ne tombe jamais dans un gabarit récurrent.
- Cite la source par son nom une seule fois si pertinent.
- Inclure l'URL fournie quelque part dans le post (ligne dédiée OU en fin).

Tu produis UNIQUEMENT le texte du post final, rien d'autre (pas de préambule, pas de guillemets autour)."""


# 6 styles. Un seul est tiré au sort par post -> diversité visuelle et de ton.
POST_STYLES = [
    {
        "name": "punchy",
        "instruction": (
            "STYLE : punchy staccato.\n"
            "- Ligne 1 : une phrase-choc de 6-10 mots (un chiffre, une annonce, un fait brut).\n"
            "- Ligne 2 : une 2e phrase qui creuse sans résoudre.\n"
            "- Saut de ligne, puis 2 phrases max d'explication concrète.\n"
            "- Une question courte qui implique le lecteur (vous/votre).\n"
            "- Mets l'URL sur sa propre ligne, précédée de 'Source : '.\n"
            "- Finis par 3 hashtags spécifiques en CamelCase.\n"
            "- Pas d'emoji bullet de section. Max 90 mots."
        ),
    },
    {
        "name": "hot-take",
        "instruction": (
            "STYLE : opinion tranchée (hot take).\n"
            "- Démarre par TON avis cash sur l'événement (1 phrase qui assume une position).\n"
            "- Puis le fait qui justifie ton avis (1-2 phrases, chiffré).\n"
            "- Puis ce que ça change concrètement pour les équipes tech.\n"
            "- Termine par l'URL en fin de post, format 'Lien : <url>'.\n"
            "- 2 hashtags max. Pas d'emoji. Ton assumé, presque oral. Max 100 mots."
        ),
    },
    {
        "name": "mini-story",
        "instruction": (
            "STYLE : mini-récit.\n"
            "- Raconte l'événement comme une scène courte (3-4 phrases) avec un fil narratif (qui, quoi, comment ça a dérapé).\n"
            "- Une phrase de chute qui révèle l'enseignement, sans moraliser.\n"
            "- Glisse l'URL en fin avec 'Le détail ici : <url>'.\n"
            "- 0 à 2 emoji max, placés naturellement dans le texte (pas en début de ligne). 3 hashtags. Max 110 mots."
        ),
    },
    {
        "name": "stat-bomb",
        "instruction": (
            "STYLE : choc par les chiffres.\n"
            "- Ligne 1 : LE chiffre le plus fort de l'histoire, seul, brut.\n"
            "- 2-3 lignes très courtes qui empilent d'autres chiffres ou faits (style liste sans puces, juste retours à la ligne).\n"
            "- Une phrase de contexte qui explique pourquoi ces chiffres comptent.\n"
            "- URL en fin : 'Source : <url>'.\n"
            "- 2-3 hashtags. Pas d'emoji. Max 90 mots."
        ),
    },
    {
        "name": "question-led",
        "instruction": (
            "STYLE : amorcé par une question dérangeante.\n"
            "- Ligne 1 : une question directe et concrète qui pique (pas générique).\n"
            "- Puis le fait d'actualité qui motive la question (2 phrases, précises).\n"
            "- Puis une implication pratique pour le lecteur.\n"
            "- URL intégrée en fin, format libre mais visible.\n"
            "- 3 hashtags. Au plus 1 emoji. Max 100 mots."
        ),
    },
    {
        "name": "journalist",
        "instruction": (
            "STYLE : dépêche de reporter tech, zéro fioriture.\n"
            "- Ligne 1 : le fait, nu, comme un titre de presse percutant (sans 'Selon').\n"
            "- 2-3 phrases factuelles qui donnent l'essentiel (acteurs, ampleur, conséquence).\n"
            "- Pas de question, pas d'emoji, pas de hashtag de section.\n"
            "- Termine par l'URL seule sur une ligne.\n"
            "- 2 hashtags discrets tout en bas. Max 85 mots. Ton sobre et pro."
        ),
    },
]

USER_PROMPT_TEMPLATE = """Actualité à transformer en post LinkedIn :

Titre: {title}
Source: {source}
URL de la source: {url}
Catégorie: {category}
Résumé: {summary}
Raison de l'intérêt: {reason}

{style_instruction}

Rappel : inclure l'URL exacte ci-dessus. Produis UNIQUEMENT le post."""


def draft_post(scored: ScoredArticle, style_name: str | None = None) -> str:
    """Génère le texte du post LinkedIn avec un style tiré au sort (ou imposé)."""
    if not ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY not set — cannot draft post.")

    style = next((s for s in POST_STYLES if s["name"] == style_name), None) or random.choice(POST_STYLES)
    log.info("Post style selected: %s", style["name"])

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    a = scored.article
    prompt = USER_PROMPT_TEMPLATE.format(
        title=a.title,
        source=a.source,
        url=a.url,
        category=a.category,
        summary=a.summary,
        reason=scored.reason,
        style_instruction=style["instruction"],
    )

    log.info("Drafting LinkedIn post for: %s", a.title[:80])
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    post = resp.content[0].text.strip()
    log.info("Post drafted (%d chars, style=%s)", len(post), style["name"])
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
        # Affiche les 6 styles sur le meme article pour comparer
        for style in POST_STYLES:
            print("\n" + "=" * 70)
            print(f"STYLE: {style['name']}")
            print("=" * 70)
            print(draft_post(top, style_name=style["name"]))
