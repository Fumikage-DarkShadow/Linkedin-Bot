# LinkedIn Daily Bot, IA & Cybersécurité

Bot autonome qui scanne les news IA / cybersécurité des dernières 24h, score l'impact via Claude, et publie un post LinkedIn **seulement si l'événement est majeur** (zero-day exploité, breach massif, cyberattaque infra critique, rupture IA).

Fréquence attendue : **2 à 5 posts par semaine**, uniquement sur de la vraie info chaude.

## Stack

- **Python 3.11+**
- **Claude Sonnet 4.6** via Anthropic API (scoring + rédaction)
- **Flux RSS** (BleepingComputer, TheHackerNews, KrebsOnSecurity, DarkReading, TechCrunch AI, TheVerge AI, VentureBeat AI)
- **Make.com webhook → LinkedIn** (pas d'app LinkedIn custom à créer, Make gère l'OAuth)
- **GitHub Actions** (cron cloud avec retry automatique)

## Flow complet

```
GitHub Actions cron (8 créneaux, 30 min d'écart de 06h30 à 10h00 UTC)
  │
  ▼
main_webhook_llm.py
  │
  ├─ daily_cache.has_posted_today() ? ───── OUI ──▶ SKIP silencieux
  │     NON
  │
  ▼
sourcing.fetch_news()                → ~20-40 articles RSS (24h)
  │
  ▼
scoring.score_articles()             → Claude scores 0-10 (focus zero-day, breach, cyberattaque, IA rupture)
  │
  ▼
top.score >= MIN_SCORE_TO_POST (9.0) ? ─── NON ──▶ SKIP (retry dans 30 min)
  │     OUI
  │
  ▼
writer.draft_post()                  → post français scroll-stop, 80-130 mots, URL source
  │
  ▼
enrich.get_image_with_fallback()     → og:image de l'article ou fallback Unsplash
  │
  ▼
publisher_webhook.post_to_webhook()  → JSON POST vers Make.com
  │                                    ├─ text
  │                                    ├─ source_url
  │                                    ├─ image_url
  │                                    └─ score, category
  ▼
Make.com scenario : Webhook → HTTP Download image → LinkedIn Create a User Image Post
  │
  ▼
daily_cache.mark_posted_today()      → écrit posted_today.json
  │
  ▼
git commit + push posted_today.json  → les crons suivants skiperont aujourd'hui
```

## Arborescence

```
linkedin-bot/
├── .github/workflows/daily_post.yml   # 8 crons + commit du cache
├── src/
│   ├── config.py              # sources RSS, seuil MIN_SCORE_TO_POST
│   ├── sourcing.py            # RSS + NewsAPI (24h), dédoublonnage
│   ├── scoring.py             # Claude, priorité cyber/IA impactant
│   ├── scoring_rules.py       # fallback heuristique (si pas de crédit LLM)
│   ├── writer.py              # Claude, format scroll-stop
│   ├── writer_template.py     # fallback template
│   ├── enrich.py              # og:image + fallback Unsplash
│   ├── publisher_webhook.py   # POST Make webhook
│   ├── daily_cache.py         # cache "déjà posté aujourd'hui"
│   └── main_webhook_llm.py    # orchestrateur production
├── logs/                      # logs locaux (gitignored)
├── posted_today.json          # cache date, commité par GitHub Actions
├── requirements.txt
├── .env.example
└── .gitignore
```

## Pré-requis (comptes à créer)

1. **GitHub** (repo privé pour le code + GitHub Actions gratuit)
2. **Anthropic Console** : https://console.anthropic.com → créer une API key dans workspace `Default` + ajouter 5$ de crédit
3. **Make.com** : https://make.com → compte gratuit (tier free 1000 ops/mois suffit pour 30 posts)

## Installation locale (test uniquement)

```bash
cd linkedin-bot
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
copy .env.example .env
```

Éditer `.env` :

```
ANTHROPIC_API_KEY=sk-ant-...
MAKE_WEBHOOK_URL=https://hook.eu1.make.com/xxxxxx
```

Tester en dry-run (n'envoie rien) :

```bash
python src/main_webhook_llm.py --dry-run
```

## Configuration Make.com (une fois, ~10 min)

1. **Créer un nouveau scenario**
2. **Module 1 — Webhook / Custom webhook** :
   - Nom : `linkedin-bot`
   - Copier l'URL générée, la coller dans `MAKE_WEBHOOK_URL`
3. Envoyer un premier payload de test pour que Make détecte la structure JSON :
   ```bash
   python src/main_webhook_llm.py
   ```
4. **Module 2 — HTTP / Download a file** :
   - URL : `{{1.image_url}}` (saisi à la main)
5. **Module 3 — LinkedIn / Create a User Image Post** :
   - Connection : Sign in with LinkedIn (OAuth Make)
   - Choose Upload Method : `Upload by file`
   - File : sélectionner `Map`
     - File name : `{{2.file_name}}` (auto)
     - Data : `{{2.data}}` (auto)
   - Content : `{{1.text}}`
   - Visibility : `Anyone`
6. **Activer le scenario** (toggle `Immediately as data arrives`)

## Déploiement GitHub Actions (production)

1. Push le repo sur GitHub (privé recommandé).
2. **Settings → Secrets and variables → Actions** :
   - `ANTHROPIC_API_KEY`
   - `MAKE_WEBHOOK_URL`
3. **Settings → Actions → General → Workflow permissions** :
   - Cocher `Read and write permissions` (pour que le workflow puisse commit `posted_today.json`)
4. Le workflow `.github/workflows/daily_post.yml` tourne chaque matin à **06:30 UTC** (= 08:30 Paris été), et retry toutes les 30 min jusqu'à 10:00 UTC si rien n'est encore parti.
5. Trigger manuel possible : onglet **Actions → Daily LinkedIn Post → Run workflow**.

## Paramètres clés (à tuner dans `src/config.py`)

| Paramètre | Valeur défaut | Effet |
|---|---|---|
| `MIN_SCORE_TO_POST` | `9.0` | Seuil d'impact minimum pour poster. Baisser à 8.5 pour ~3x plus de posts. Monter à 9.5 pour uniquement les très gros événements. |
| `LOOKBACK_HOURS` | `24` | Fenêtre d'articles considérés. |
| `MAX_ARTICLES_PER_SOURCE` | `15` | Plafonne le nombre d'articles par RSS pour éviter de saturer le LLM. |

## Anti-doublon

Le fichier `posted_today.json` est committé par GitHub Actions après chaque publication réussie. Tant que sa date vaut `aujourd'hui`, tous les crons du jour skipent (peu importe leur heure). Le lendemain, la date ne matche plus → nouveau cycle.

Si un score reste sous le seuil toute la matinée, **aucun post n'est publié ce jour-là**. Silence volontaire, pas d'incident.

## Logs & monitoring

- **Console locale** : `python src/main_webhook_llm.py` imprime tout en stdout
- **Logs GitHub Actions** : onglet Actions → run concerné → logs détaillés + artifact `bot-logs-<run_id>` (14 jours)
- **Historique Make** : scenario → onglet HISTORY (voir exécutions, erreurs HTTP, credits consommés)

## Maintenance

| Quoi | Fréquence | Comment |
|---|---|---|
| Recharger crédit Anthropic | Tous les ~500 posts (~5$) | console.anthropic.com → Billing |
| Ré-autoriser LinkedIn Make | Tous les 60 jours | Make envoie un email, 1 clic sur `Reconnect` |
| Rien d'autre | Jamais | — |

## Style d'écriture

Le writer système prompt interdit explicitement :

- Le tiret cadratin `—` (forme creuse, sonne IA)
- Tournures balancées (« il ne s'agit pas seulement de X mais aussi de Y »)
- Mots creux (« fondamental », « crucial », « essentiel », « notamment », « particulièrement »)
- Formules « ce cas illustre », « dans un monde où »
- Plus de 130 mots

Format attendu : 2 phrases d'accroche staccato, 1 section `🎯 Le fond` (2 phrases max), 1 question impliquante, lien source, 3 hashtags.
