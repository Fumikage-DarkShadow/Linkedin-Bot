# LinkedIn Daily Bot — IA & Cybersécurité

Pipeline automatisé qui publie chaque jour à **08h30** un post LinkedIn sur la news IA ou Cyber la plus impactante des dernières 24h.

## Stack

- **Python 3.11+**
- **Claude Sonnet 4.6** (scoring + rédaction)
- **Flux RSS** + **NewsAPI** (sourcing)
- **LinkedIn UGC API** (publication)
- **GitHub Actions** (cron 08:30)

## Arborescence

```
linkedin-bot/
├── .github/workflows/daily_post.yml
├── src/
│   ├── config.py       # sources, clés, paramètres
│   ├── sourcing.py     # RSS + NewsAPI (24h)
│   ├── scoring.py      # LLM — note d'impact 0-10
│   ├── writer.py       # LLM — rédaction post
│   ├── publisher.py    # API LinkedIn
│   └── main.py         # orchestrateur
├── logs/               # logs quotidiens (rotation)
├── posted_urls.json    # cache anti-doublon
├── requirements.txt
└── .env.example
```

## Installation locale

```bash
cd linkedin-bot
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt
copy .env.example .env         # Windows  (cp sur Linux)
```

Édite `.env` :

```
ANTHROPIC_API_KEY=sk-ant-...
NEWSAPI_KEY=...                # optionnel
LINKEDIN_ACCESS_TOKEN=...
LINKEDIN_USER_URN=urn:li:person:XXXXXXX
```

## Obtenir les credentials LinkedIn

1. Crée une app sur https://www.linkedin.com/developers/apps
2. Demande les produits : **Share on LinkedIn** (+ **Sign In with LinkedIn**)
3. Scopes requis : `w_member_social`, `openid`, `profile`
4. Récupère un access token via l'OAuth flow (Postman ou script custom)
5. Lance : `python -c "from src.publisher import get_user_urn; get_user_urn('TON_TOKEN')"`
6. Colle l'URN retourné dans `.env`

> ⚠️ Le token expire tous les **60 jours** — prévoir un refresh manuel.

## Utilisation

```bash
# Dry-run : affiche le post sans publier
python src/main.py --dry-run

# Publication réelle
python src/main.py

# Test d'un module isolé
python src/sourcing.py
python src/scoring.py
python src/writer.py
```

## Déploiement GitHub Actions

1. Push le repo sur GitHub
2. Settings → Secrets and variables → Actions :
   - `ANTHROPIC_API_KEY`
   - `NEWSAPI_KEY` (optionnel)
   - `LINKEDIN_ACCESS_TOKEN`
   - `LINKEDIN_USER_URN`
3. Le workflow `.github/workflows/daily_post.yml` s'exécute chaque jour à **06:30 UTC** (= 08:30 Paris en été).
4. Déclenchement manuel possible : onglet **Actions** → **Run workflow**.

## Logs & Monitoring

- Logs locaux : `logs/daily_YYYY-MM-DD.log` (rotation 5 fichiers × 2Mo)
- Logs GitHub Actions : uploadés comme artifact `bot-logs-<run_id>` à chaque run
- Cache anti-doublon : `posted_urls.json` (committé par le workflow)

## Architecture du flow

```
08:30 UTC+2
  │
  ▼
sourcing.fetch_news()         → ~30-50 articles (24h, dédupliqués)
  │
  ▼
scoring.score_articles()      → Claude note chaque article 0-10
  │
  ▼
main.pick_fresh()             → skip URLs déjà postées
  │
  ▼
writer.draft_post()           → post formaté (accroche + 3 bullets + question + 5 hashtags)
  │
  ▼
publisher.post_to_linkedin()  → UGC Posts API
  │
  ▼
save_cache() + logs
```
