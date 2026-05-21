# Legacy — fichiers gardés pour référence

Le bot en production utilise **uniquement** `src/main_webhook_llm.py` + Make.com.

Les fichiers ici sont des variantes ou pistes abandonnées pendant le dev. Ils sont fonctionnels mais non utilisés.

| Fichier | Ce que c'est |
|---|---|
| `main_linkedin_api.py` | Ancien orchestrateur qui postait directement via l'API LinkedIn (OAuth). Abandonné parce que LinkedIn impose l'approbation manuelle d'une app pour utiliser `w_member_social`. |
| `publisher_linkedin_api.py` | Module de publication via UGC Posts API LinkedIn. Va avec `main_linkedin_api.py`. |
| `linkedin_oauth.py` | Helper OAuth 2.0 local (serveur callback sur port 8765) pour récupérer un access token LinkedIn perso. Inutile si tu passes par Make. |
| `mailer_outlook.py` | Pipeline qui envoyait le post par email via Outlook COM (Windows uniquement). Abandonné. |
| `mailer_gmail.py` | Variante SMTP Gmail (app password). Abandonné. |
| `main_email_llm.py` | Orchestrateur qui draftait avec Claude et envoyait par email pour copier-coller manuel. |
| `main_email_template.py` | Variante template (sans LLM) envoyée par email. |
| `main_webhook_template.py` | Variante webhook utilisant le writer template (sans LLM). Utile si tu ne veux pas dépenser de crédit Anthropic. |

## Quand les ressortir ?

- Tu n'as pas (ou plus) accès à Make.com → `main_linkedin_api.py` + OAuth direct (long mais auto-hébergé)
- Tu veux poster sans LLM → `main_webhook_template.py` (gratuit, qualité moyenne)
- Tu préfères recevoir le post par mail et publier à la main → `main_email_llm.py`

Tu peux supprimer ce dossier entier si tu es certain de ne jamais y revenir.
