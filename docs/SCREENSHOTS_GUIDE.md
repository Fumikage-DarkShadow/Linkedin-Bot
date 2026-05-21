# Captures d'écran du bot

Le README utilise des diagrammes ASCII pour expliquer l'architecture (durable, ne périme pas). Si tu veux ajouter de vraies captures pour illustrer Make.com ou GitHub Actions, utilise la procédure ci-dessous.

## Procédure manuelle (la plus simple)

1. Ouvre Make.com → `Webhooks d'intégration, LinkedIn` scenario.
2. Pour chaque écran à capturer, utilise `Win + Shift + S` (Snipping Tool).
3. Sélectionne la zone utile, sauvegarde sous `docs/screenshots/<nom>.png`.
4. Commite et push.

## Captures recommandées

| Fichier suggéré | Ce qu'il faut montrer |
|---|---|
| `01-make-overview.png` | Vue diagramme du scenario (3 modules + toggle "Actif") |
| `02-make-webhook-config.png` | Module 1 ouvert : URL du webhook + bouton "Successfully determined" |
| `03-make-http-config.png` | Module 2 ouvert : URL = `{{1.image_url}}` |
| `04-make-linkedin-config.png` | Module 3 ouvert : Connection + Upload Method + File map + Content map |
| `05-make-history.png` | Onglet History : runs récents avec status Success |
| `06-github-actions.png` | Liste des runs GitHub Actions, beaucoup de verts |
| `07-github-secrets.png` | Page Secrets avec `ANTHROPIC_API_KEY` + `MAKE_WEBHOOK_URL` |

## Procédure automatisée (Playwright, optionnel)

Si tu veux refaire toutes les captures en une commande sans clic manuel :

```bash
pip install playwright
playwright install chromium
python docs/take_screenshots.py
```

Le script ouvre un Chromium dédié, te demande de te logger une fois sur Make + GitHub, puis capture les 7 écrans automatiquement.
