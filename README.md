# LinkedIn Daily Bot 

Bot autonome qui scanne les news des dernières 24h, score l'impact via Claude API, et publie un post LinkedIn **seulement si l'événement est majeur** (zero-day exploité, breach massif, cyberattaque infra critique, rupture IA structurante).

 Le bot peut être recyclé sur **n'importe quel autre sujet** (dev, achats, RH, finance, etc.) en éditant 3 fichiers.
---

## Sommaire

- [Architecture (schéma)](#architecture-schema)
- [Stack technique](#stack-technique)
- [Comment ça tourne, jour par jour](#comment-ca-tourne-jour-par-jour)
- [Recréer l'automatisation Make.com from scratch](#recreer-le-scenario-makecom-from-scratch)
- [Recréer le repo GitHub from scratch](#recreer-le-repo-github-from-scratch)
- [⚙️ Adapter le bot à un autre sujet](#adapter-le-bot-a-un-autre-sujet)
- [⚙️ Changer le nombre de posts par semaine](#changer-le-nombre-de-posts-par-semaine)
- [⚙️ Changer la fenêtre horaire ou les jours autorisés](#changer-la-fenetre-horaire-ou-les-jours)
- [⚙️ Changer le seuil de score minimum](#changer-le-seuil-de-score-minimum)
- [Maintenance & monitoring](#maintenance--monitoring)

---

## Architecture (schéma)

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions (cloud, gratuit)              │
│                                                                 │
│   8 crons entre 06h30 et 10h00 UTC (= 08h30-12h00 Paris été)    │
│   Première exécution réussie de la journée → suivantes skipent  │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Python: src/main_webhook_llm.py                │
│                                                                 │
│   1. should_skip_today()                                        │
│        ├─ weekend ? → SKIP                                      │
│        ├─ déjà 2 posts cette semaine ? → SKIP                   │
│        └─ déjà posté aujourd'hui ? → SKIP                       │
│                                                                 │
│   2. sourcing.fetch_news()       → 30-40 articles RSS (24h)     │
│   3. scoring.score_articles()    → Claude scores 0-10           │
│   4. top.score < 9.0 ? → SKIP "score insuffisant" (retry +30min)│
│   5. writer.draft_post()         → texte LinkedIn 80-130 mots   │
│   6. enrich.get_image_with_fallback()                           │
│         ├─ RSS image officielle ?                               │
│         ├─ og:image scrape ?                                    │
│         └─ fallback hashé (1 image parmi 8 par catégorie)       │
│   7. publisher_webhook.post_to_webhook()                        │
│         POST JSON → Make.com                                    │
│   8. mark_posted_today() + git commit posted_today.json         │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                Make.com — Scenario 3 modules                    │
│                                                                 │
│   ┌──────────┐    ┌──────────┐    ┌────────────────────────┐    │
│   │ Webhook  │ ── │ HTTP     │ ── │ LinkedIn               │    │
│   │ Custom   │    │ Download │    │ Create a User          │    │
│   │ webhook  │    │ a file   │    │ Image Post             │    │
│   └──────────┘    └──────────┘    └────────────────────────┘    │
│     reçoit:         télécharge        publie le post +          │
│     - text          l'image           image sur ton profil      │
│     - image_url     depuis            LinkedIn perso            │
│     - source_url    image_url                                   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
                       Post LinkedIn visible
```

---

## Stack technique

- **Python 3.11+**
- **Claude Sonnet 4.6** via Anthropic API (scoring + rédaction)
- **Flux RSS** (BleepingComputer, TheHackerNews, KrebsOnSecurity, DarkReading, TechCrunch AI, TheVerge AI, VentureBeat AI)
- **Make.com** (orchestrateur webhook → LinkedIn, gère l'OAuth)
- **GitHub Actions** (cron cloud avec retry)

---

## Comment ça tourne, jour par jour

| Heure (Paris) | Action |
|---|---|
| 08h30 | 1er cron GitHub. Vérifie weekend / cap hebdo / déjà posté. Si OK, fetch news + score. Si top < 9.0, skip. Si ≥ 9.0, post. |
| 09h00 | 2e cron. Si 08h30 a posté, le cache dit "déjà fait", skip silencieux. Sinon retry. |
| 09h30 → 12h00 | 6 crons de plus, même logique. |
| 12h01 | Plus rien jusqu'à demain. Si rien n'est passé aujourd'hui, journée sans post (normal si actualité calme). |

---

## Recréer le scenario Make.com from scratch

Tu en as besoin si tu repars de zéro, changes d'org Make, ou veux comprendre le câblage.

### Étape 1 — Compte Make

1. Sign up sur https://make.com (region Europe).
2. Dashboard → **Create a new scenario**.

### Étape 2 — Module 1 : Webhook trigger

1. Clic le grand `+` violet au centre du canvas.
2. Cherche `Webhooks` → choisis **Custom webhook**.
3. Add a new webhook → nom `linkedin-bot` → **Save**.
4. Copie l'URL affichée (format `https://hook.eu1.make.com/xxxxx`). C'est `MAKE_WEBHOOK_URL`.
5. Envoie un premier payload de test pour que Make détecte la structure JSON :
   ```bash
   python src/main_webhook_llm.py
   ```
   Make doit afficher **"Successfully determined"**. Clique **Save**.

### Étape 3 — Module 2 : HTTP Download

1. Clic le `+` à droite du Webhook.
2. Cherche `HTTP` → choisis **Download a file**.
3. Champ **URL** : tape manuellement `{{1.image_url}}` (Make le reconnaît comme variable et l'affiche en pill rouge).
4. Authentication type : **No authentication**.
5. **Save**.

### Étape 4 — Module 3 : LinkedIn Image Post

1. Clic le `+` à droite du HTTP.
2. Cherche `LinkedIn` → choisis **Create a User Image Post**.
3. **Connection** → **Create a connection** → **LinkedIn** (pas OpenID Connect) → Sign in avec ton compte perso → Allow.
4. **Choose Upload Method** : `Upload by file`.
5. **File** : sélectionne le radio **Map** (pas "HTTP - Download a file").
   - **File name** : `{{2.file_name}}` (auto-rempli si tu cliques dans le champ)
   - **Data** : `{{2.data}}` (auto-rempli)
6. **Content** : clique dans le champ, le panneau de variables s'ouvre → clique sur `text` sous "Webhooks - Custom webhook".
7. **Visibility** : `Anyone`.
8. **Save**.

### Étape 5 — Activer

- En bas de page : toggle **Immediately as data arrives** → ON (violet).
- En haut à droite : toggle **Active** → ON.
- ⚠️ Si tu désactives le scenario, les webhooks reçus pendant la pause sont mis en queue et bloqueront le suivant. Garde-le actif.

---

## Recréer le repo GitHub from scratch

1. Crée un repo privé `linkedin-bot` sur GitHub.
2. Clone-le, copie tous les fichiers du dossier `linkedin-bot/` dedans, push.
3. **Settings → Actions → General → Workflow permissions** : coche **Read and write permissions** (le workflow doit pouvoir commit `posted_today.json`).
4. **Settings → Secrets and variables → Actions → New repository secret** :
   - `ANTHROPIC_API_KEY` : ta clé Anthropic du workspace où tu as ajouté du crédit.
   - `MAKE_WEBHOOK_URL` : l'URL du webhook copiée à l'étape 2 de Make.
5. Actions tab → run manuel pour valider : **Daily LinkedIn Post → Run workflow → Run workflow**.

---

## Adapter le bot à un autre sujet

Le bot est paramétré par défaut sur IA + Cybersécurité, mais peut être recyclé sur **dev**, **achats**, **finance**, **RH**, **secteur immobilier**, **médical**, etc. Tu édites **3 fichiers**.

### Fichier 1 — Sources RSS : [`src/config.py`](src/config.py) lignes 17-33

```python
RSS_FEEDS = {
    "cybersecurity": [
        "https://www.bleepingcomputer.com/feed/",
        "https://thehackernews.com/feeds/posts/default",
        # ... à remplacer par tes sources
    ],
    "ai": [
        "https://techcrunch.com/category/artificial-intelligence/feed/",
        # ...
    ],
}
```

**Exemples par sujet :**

| Sujet visé | Sources RSS à mettre |
|---|---|
| **Dev / engineering** | `https://blog.pragmaticengineer.com/rss/`, `https://news.ycombinator.com/rss`, `https://martinfowler.com/feed.atom`, `https://blog.bytebytego.com/feed`, `https://thenewstack.io/feed/` |
| **Achats / supply chain** | `https://www.supplychaindive.com/feeds/news/`, `https://www.procurious.com/feed`, `https://feeds.feedburner.com/scmr`, `https://www.cips.org/intelligence-hub/feed/` |
| **Finance / VC** | `https://www.bloomberg.com/feeds/sitemap_news.xml`, `https://www.ft.com/markets?format=rss`, `https://news.crunchbase.com/feed/`, `https://www.reuters.com/finance/markets/rss` |
| **HR / future of work** | `https://hbr.org/feed`, `https://www.shrm.org/rss`, `https://feeds.feedburner.com/HRDive` |

Tu peux aussi mélanger 2 thèmes (clé du dict = nom de catégorie, libre).

### Fichier 2 — Critères de scoring LLM : [`src/scoring.py`](src/scoring.py) lignes 23-46

```python
SYSTEM_PROMPT = """Tu es un analyste senior en veille tech spécialisé IA & Cybersécurité.
...
SUJETS PRIORITAIRES (les seuls qui méritent >6/10) :
1. Cyberattaques majeures (groupes APT, ransomware, infrastructures critiques)
2. Fuites de données / breaches (volume massif, entreprise connue, données sensibles)
3. Zero-day exploité in-the-wild (CVE critique, RCE, privilège escalation)
4. Ruptures IA (modèle majeur, vulnérabilité d'un LLM/agent, régulation structurante)
5. Vulnérabilités critiques largement exploitables (type Log4Shell, supply chain)
...
"""
```

**À réécrire complètement** avec les sujets prioritaires de ton secteur. Exemples :

```python
# Pour les ACHATS
SUJETS PRIORITAIRES :
1. Rupture supply chain mondiale (port bloqué, sanctions, pénurie matière)
2. Faillite majeure de fournisseur stratégique
3. Innovation contractuelle structurante (e-procurement, blockchain achats)
4. Mouvements de prix matières premières > 10% en 24h
5. Régulation nouvelle (ESG mandatory, sanctions geopolitiques)

# Pour le DEV
SUJETS PRIORITAIRES :
1. Vulnérabilité majeure dans un framework largement utilisé (React, Django, etc.)
2. Sortie majeure d'un langage / framework (Python 4, React 20, etc.)
3. Outage d'un service critique (GitHub, AWS, Cloudflare)
4. Acquisition stratégique entre éditeurs (Microsoft → GitHub style)
5. Rupture IA pour le dev (nouveau Copilot, Cursor, Devin-like)
```

### Fichier 3 — Ton et format du post : [`src/writer.py`](src/writer.py) lignes 23-65

```python
SYSTEM_PROMPT = """Tu es un copywriter LinkedIn expert du format viral cyber/IA.
Audience : RSSI, CTO, tech leads francophones qui scrollent vite.
...
"""
```

**À adapter** :
- "expert du format viral cyber/IA" → "expert du format viral achats/supply chain"
- "Audience : RSSI, CTO, tech leads" → "Audience : directeurs achats, supply chain managers"
- Exemples de lignes 1 dans la liste → réécrire avec des exemples métier

Le reste (interdictions du tiret cadratin, des formules creuses, du format scroll-stop) marche pour tous les sujets.

### Mini-checklist pour migrer

- [ ] `src/config.py` : remplacer `RSS_FEEDS`
- [ ] `src/scoring.py` : réécrire `SYSTEM_PROMPT` (les 5 sujets prioritaires)
- [ ] `src/writer.py` : réécrire `SYSTEM_PROMPT` (audience + exemples d'accroche)
- [ ] Test local : `python src/main_webhook_llm.py --dry-run` → vérifier que le post est cohérent
- [ ] Commit + push

---

## Changer le nombre de posts par semaine

[`src/config.py`](src/config.py) ligne 38 :

```python
MAX_POSTS_PER_WEEK = 2
```

| Valeur | Effet |
|---|---|
| `1` | 1 seul post max entre lundi et vendredi |
| `2` (défaut) | 2 posts max entre lundi et vendredi |
| `3` | 3 posts max entre lundi et vendredi |
| `5` | Jusqu'à 1 post chaque jour ouvré |
| `7` | Plafond désactivé en pratique (jamais 7 jours dans une semaine ISO) |

Le compteur reset chaque **lundi 00h00**.

---

## Changer la fenêtre horaire ou les jours

### Heures de tentative (cron GitHub Actions)

[`.github/workflows/daily_post.yml`](.github/workflows/daily_post.yml) lignes 5-13 :

```yaml
schedule:
  - cron: "30 6 * * *"   # 06h30 UTC = 08h30 Paris été
  - cron: "0 7 * * *"
  - cron: "30 7 * * *"
  - cron: "0 8 * * *"
  - cron: "30 8 * * *"
  - cron: "0 9 * * *"
  - cron: "30 9 * * *"
  - cron: "0 10 * * *"
```

**Ajuster les heures** : modifie les expressions cron. Format `m h * * *`. Attention, c'est en **UTC** (Paris UTC+1 hiver, UTC+2 été).

Exemples :
- Pour viser 18h00 Paris en été → `"0 16 * * *"`
- Pour retry de 14h à 17h Paris en été → `"0 12 * * *"` jusqu'à `"0 15 * * *"`

### Jours autorisés (semaine de travail)

[`src/config.py`](src/config.py) ligne 39 :

```python
ALLOWED_WEEKDAYS = {0, 1, 2, 3, 4}  # 0=lundi, 4=vendredi
```

| Set | Effet |
|---|---|
| `{0, 1, 2, 3, 4}` (défaut) | Lun-Ven |
| `{0, 1, 2, 3, 4, 5, 6}` | Tous les jours, weekend inclus |
| `{1, 3}` | Mardi et jeudi uniquement |
| `{0}` | Lundi uniquement |

---

## Changer le seuil de score minimum

[`src/config.py`](src/config.py) ligne 34 :

```python
MIN_SCORE_TO_POST = 9.0
```

| Valeur | Effet attendu |
|---|---|
| `9.5` | Très strict, ne post que sur événements ultra-majeurs. 0-1 post/semaine estimé. |
| `9.0` (défaut) | Strict, événements vraiment chauds. 1-2 posts/semaine. |
| `8.5` | Modéré, inclut les vulnérabilités critiques mais pas encore exploitées. 3-4 posts/semaine. |
| `8.0` | Permissif, inclut les news significatives. 4-5 posts/semaine (mais capé à `MAX_POSTS_PER_WEEK`). |
| `7.0` | Très permissif, beaucoup de bruit. Tu auras un post quasi tous les jours ouvrés. |
| `0.0` | Désactive le filtre, post quoi qu'il arrive (mauvaise idée). |

---

## Maintenance & monitoring

| Quoi | Quand | Comment |
|---|---|---|
| Recharger crédit Anthropic | ~tous les 1000 posts (~5 €) | https://console.anthropic.com → Billing |
| Ré-autoriser LinkedIn Make | Tous les ~60 jours | Make envoie un email, clique **Reconnect** depuis Connections |
| Voir logs run | À la demande | GitHub → Actions → run concerné → logs + artifact `bot-logs-<id>` (14 j) |
| Voir historique Make | À la demande | Make → scenario → onglet **History** |
| Voir cache anti-doublon | À la demande | Fichier `posted_today.json` à la racine du repo (committé par le bot) |

### En cas de bug : ordre de diagnostic

1. **GitHub Actions** : le workflow a-t-il fired ? Status vert ? Logs détaillés ?
2. **Make History** : l'exécution est-elle arrivée côté Make ? Status Success ?
3. **LinkedIn** : si Make Success mais pas de post visible → token LinkedIn expiré, re-auth.
4. **Anthropic balance** : si Python échoue avec "credit balance too low" → recharger.

---

## Fichiers à connaître

```
linkedin-bot/
├── .github/workflows/daily_post.yml   # 8 crons + commit cache
├── src/
│   ├── config.py              # ⚙️ paramètres tunables (sources, seuils, cap)
│   ├── sourcing.py            # fetch RSS, dédup, extraction image RSS
│   ├── scoring.py             # ⚙️ prompt LLM scoring (sujets prioritaires)
│   ├── writer.py              # ⚙️ prompt LLM writer (ton + format)
│   ├── enrich.py              # og:image avec fallback hashé
│   ├── publisher_webhook.py   # POST JSON vers Make
│   ├── daily_cache.py         # règles weekend + cap hebdo + 1/jour
│   └── main_webhook_llm.py    # orchestrateur production
├── posted_today.json          # cache committé par GitHub Actions
├── requirements.txt
├── .env.example
└── README.md
```

Les 3 fichiers marqués ⚙️ sont les seuls à éditer pour customiser le bot.
