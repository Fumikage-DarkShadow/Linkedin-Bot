<div align="center">

# 🤖 LinkedIn Daily Bot

**Bot Python autonome qui scanne les news cyber/IA, score l'impact via Claude, et publie un post LinkedIn — uniquement si l'événement est vraiment majeur.**

[![GitHub Actions](https://img.shields.io/badge/runs_on-GitHub_Actions-2088ff?style=for-the-badge&logo=githubactions&logoColor=white)](https://github.com/Fumikage-DarkShadow/Linkedin-Bot/actions)
[![Python](https://img.shields.io/badge/Python-3.11+-3776ab?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Claude API](https://img.shields.io/badge/Powered_by-Claude_Sonnet-d97757?style=for-the-badge)](https://anthropic.com)
[![License](https://img.shields.io/badge/license-MIT-22c55e?style=for-the-badge)](LICENSE)

</div>

---

## Aperçu

Un bot qui tourne **tout seul sur GitHub Actions** (gratuit, pas de serveur à payer), scanne ~30-40 articles RSS chaque matin, demande à Claude de noter chaque news sur 10, et ne publie sur LinkedIn **que si le score dépasse 9.0** — c'est-à-dire un zero-day exploité en masse, un breach majeur, ou une rupture IA structurante.

Cadence par défaut : **1 post tous les 2 mois max** (réglable). L'objectif n'est PAS de spammer ton feed LinkedIn — c'est de poster uniquement quand tu as vraiment quelque chose d'intéressant à dire, pour rester crédible auprès de ton réseau.

> 🔌 **Recyclable** sur n'importe quel sujet (dev, achats, RH, finance, M&A, climat…) en éditant 3 fichiers : `config.py` (sources RSS), `scoring.py` (prompt Claude), `writer_template.py` (template de post).

---

## Exemple de post généré

Voici le format type d'un post produit par le bot :
<img width="511" height="572" alt="image" src="https://github.com/user-attachments/assets/fb6eec09-6fc0-4ddb-8109-2e5512cb928a" />


Le bot ajoute automatiquement les hashtags pertinents, le lien source, et une image (RSS officielle, og:image scrapée, ou fallback hashé).

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│            GitHub Actions (cron, gratuit, cloud)                │
│  8 fenêtres entre 06h30 et 10h00 UTC (= 08h30-12h00 Paris été)  │
│  Première exécution réussie de la journée → suivantes skipent   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Python — src/main_webhook_llm.py                   │
│                                                                 │
│  1. should_skip_today()                                         │
│        ├─ weekend ? → SKIP                                      │
│        ├─ dernier post < 60 jours ? → SKIP                      │
│        └─ déjà posté aujourd'hui ? → SKIP                       │
│                                                                 │
│  2. sourcing.fetch_news()       → 30-40 articles RSS (24h)      │
│  3. scoring.score_articles()    → Claude scores 0-10            │
│  4. top.score < 9.0 ? → SKIP (retry dans +30min)                │
│  5. writer.draft_post()         → 80-130 mots LinkedIn          │
│  6. enrich.get_image_with_fallback()                            │
│       ├─ RSS image officielle ?                                 │
│       ├─ og:image scrape ?                                      │
│       └─ fallback hashé (1 image parmi 8 par catégorie)         │
│  7. publisher_webhook.post_to_webhook() → Make.com              │
│  8. mark_posted_today() + git commit posted_today.json          │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│              Make.com — Scenario en 4 modules                   │
│                                                                 │
│  Webhook ─→ HTTP Download ─→ LinkedIn Create Post ─→ Gmail      │
│   reçoit    télécharge        publie sur ton          envoie    │
│   {text,    l'image            profil LinkedIn        un mail   │
│    image,                                             d'alerte  │
│    source}                                                       │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                  📢 Post LinkedIn + 📧 email de confirmation
```

---

## Comment ça tourne — journée type

| Heure (UTC) | Heure (Paris été) | Action |
| --- | --- | --- |
| 06h30 | 08h30 | Cron 1 lance le script. Si dernier post < 60j ou weekend → SKIP. Sinon scoring. Si meilleur score < 9.0 → SKIP "rien de bouleversant aujourd'hui". |
| 07h00 → 10h00 | 09h00 → 12h00 | 7 autres crons retrient à 30 min d'intervalle. Le bot scanne à nouveau (les news arrivent en continu) — peut-être qu'un événement majeur tombera entre 9h et 11h. |
| 1er succès | — | Le bot publie via Make.com, écrit la date dans `posted_today.json`, commit + push → tous les crons restants de la journée détectent `posted_today` et skipent. |
| Le lendemain | — | Le compteur "dernier post" repart de zéro, le filtre des 60 jours bloque l'envoi pendant 2 mois. |

---

## Stack technique

| Catégorie | Tech |
| --- | --- |
| Langage | **Python 3.11+** |
| LLM | **Claude Sonnet 4.6** (scoring + writing) via SDK `anthropic` |
| Sourcing | `feedparser` (RSS) + `newsapi-python` (optionnel) |
| Image enrichment | `requests` + `httpx` (scrape og:image, fallbacks hashés) |
| Publication | Webhook **Make.com** → module **LinkedIn Create a User Image Post** |
| Orchestration | **GitHub Actions** (8 crons + workflow_dispatch manuel) |
| Cache local | `posted_today.json` + `posted_urls.json` commitées via Actions |
| Secrets | `.env` local (gitignore) + **GitHub Secrets** pour les Actions |

---

## Configuration en 3 étapes

### 1. Clé Anthropic Claude

1. Crée un compte sur [console.anthropic.com](https://console.anthropic.com/settings/keys)
2. Génère une clé API (format `sk-ant-api03-...`)
3. Ajoute-la dans `.env` local ET dans **GitHub Settings → Secrets and variables → Actions** (nom : `ANTHROPIC_API_KEY`)

### 2. Webhook Make.com

1. Crée un compte sur [make.com](https://www.make.com) (offre gratuite : 1 000 ops/mois — largement suffisant ici)
2. **New Scenario** → ajoute un module **Webhooks → Custom webhook**
3. Note l'URL générée (`https://hook.eu1.make.com/XXXXX`)
4. Ajoute 3 modules à la suite :
   - **HTTP → Get a file** (input : `{{ 1.image_url }}`)
   - **LinkedIn → Create a User Image Post** (text : `{{ 1.text }}`, image : output du HTTP)
   - **Gmail → Send an email** (alerte succès à toi-même)
5. **Webhooks → linkedin-bot → Edit → Add API key** : génère une clé longue aléatoire, copie-la
6. Active le scenario (toggle ON)
   <img width="1231" height="577" alt="image" src="https://github.com/user-attachments/assets/9caf1aaf-0f2b-4383-9c4c-479aaa9e66bc" />


### 3. Variables GitHub Secrets

Dans le repo GitHub → **Settings → Secrets and variables → Actions**, crée :

| Secret | Valeur |
| --- | --- |
| `ANTHROPIC_API_KEY` | Clé Claude `sk-ant-api03-...` |
| `MAKE_WEBHOOK_URL` | URL du webhook Make `https://hook.eu1.make.com/...` |
| `MAKE_WEBHOOK_API_KEY` | Clé aléatoire créée à l'étape 2 (header `x-make-apikey`) |
| `MAKE_API_TOKEN` | Token API Make (profile API token, pour le health check) |
| `MAKE_SCENARIO_ID` | ID numérique du scenario (visible dans l'URL Make) |
| `NEWSAPI_KEY` | *(optionnel)* clé [newsapi.org](https://newsapi.org) pour élargir le sourcing |

Le workflow `.github/workflows/daily_post.yml` est déjà configuré pour tourner automatiquement.

---

## Lancer en local (debug)

```bash
git clone https://github.com/Fumikage-DarkShadow/Linkedin-Bot.git
cd Linkedin-Bot
cp .env.example .env
# Édite .env et remplis ANTHROPIC_API_KEY, MAKE_WEBHOOK_URL, etc.

pip install -r requirements.txt
python src/main_webhook_llm.py
```

Le script imprime ses étapes dans la console. Si le top article ne passe pas le seuil de 9.0, il s'arrête avec `SKIP score insuffisant`. Si tout passe, il appelle Make.com et tu reçois un mail de confirmation + le post apparaît sur LinkedIn.

Pour **forcer un post de test** (bypass des skips), lance via GitHub Actions :
- Onglet **Actions** → **Daily LinkedIn Post** → **Run workflow** (workflow_dispatch)

---

## Adapter le bot à un autre sujet

Le bot a été conçu pour être **recyclable**. Pour le transformer en bot Dev/Achats/RH/Finance, édite 3 fichiers :

### 1. `src/config.py` — Sources RSS

```python
RSS_FEEDS = {
    "ton_sujet": [
        "https://example.com/feed.xml",
        "https://autresource.com/rss",
    ],
}
NEWSAPI_QUERIES = ["mots clés OR autres mots"]
```

### 2. `src/scoring.py` — Prompt de scoring Claude

Modifie le prompt système pour décrire ce qui constitue un événement à fort impact dans ton domaine. Exemple pour un bot Finance :

```python
SCORING_PROMPT = """Tu es analyste financier senior. Note de 0 à 10 chaque article
selon son impact marché. 10 = annonce de fusion majeure, faillite bancaire,
décision FED inattendue. 5 = résultat trimestriel d'un mid-cap. 0 = rumeur."""
```

### 3. `src/writer_template.py` — Ton et format du post

Adapte le prompt du writer pour le ton voulu (formel finance, friendly tech, etc.) et la longueur cible.

---

## Réglages utiles (`src/config.py`)

| Variable | Défaut | Effet |
| --- | --- | --- |
| `MIN_SCORE_TO_POST` | `9.0` | Seuil minimum pour publier (0-10). Baisser à `8.0` pour poster plus souvent. |
| `MIN_DAYS_BETWEEN_POSTS` | `60` | Jours minimum entre 2 posts. `7` = 1/semaine, `30` = 1/mois. |
| `ALLOWED_WEEKDAYS` | `{0,1,2,3,4}` | Lundi-Vendredi. Ajoute `5,6` pour le weekend. |
| `LOOKBACK_HOURS` | `24` | Fenêtre de recherche RSS. |
| `MAX_ARTICLES_PER_SOURCE` | `15` | Articles max scannés par flux. |

Pour changer les **horaires de cron**, édite `.github/workflows/daily_post.yml` (8 lignes `cron:`).

---

## Maintenance & monitoring

- **Logs** : visibles dans **Actions → Daily LinkedIn Post → run**. Chaque étape est tracée (sourcing, scoring, draft, publish).
- **Email d'alerte** : à chaque post réussi, Make.com t'envoie un mail. Si tu ne reçois rien pendant >2 mois, vérifie que le scenario Make n'est pas désactivé (souvent à cause d'une OAuth LinkedIn expirée).
- **Cache** : `posted_today.json` est commité par le bot lui-même via le token `GITHUB_TOKEN` automatique. Si le commit échoue, le bot peut poster 2 fois le même jour — surveille les logs.
- **Quota Claude** : ~30k tokens par run × ~10 runs/mois (la plupart skipent vite) = négligeable.
- **Quota Make.com** : ~4 ops par post × 12 posts/an = 50 ops/an. Très en dessous des 1 000 ops/mois gratuits.

---

## Structure du code

```
src/
├── config.py              # Sources RSS, clés API, seuils, cadence
├── sourcing.py            # Fetch RSS + NewsAPI → liste d'Articles (24h)
├── scoring.py             # Prompt Claude → score 0-10 par article
├── scoring_rules.py       # Fallback heuristique sans LLM (mots-clés + poids source)
├── writer.py              # Prompt Claude → texte LinkedIn 80-130 mots
├── writer_template.py     # Templates de prompts (ton, format, hashtags)
├── enrich.py              # Récup image (RSS / og:image / fallback hashé)
├── publisher_webhook.py   # POST JSON vers Make.com (+ x-make-apikey)
├── daily_cache.py         # Lecture/écriture posted_today.json
├── health_check.py        # Vérifie que le scenario Make est actif avant de poster
├── main_webhook_llm.py    # Orchestrateur principal (point d'entrée)
└── legacy/                # Anciennes versions (LinkedIn API directe, mailer Outlook/Gmail)
```

---
