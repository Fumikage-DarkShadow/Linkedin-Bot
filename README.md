# LinkedIn Daily Bot 

Bot autonome qui scanne les news des dernières 24h, score l'impact via Claude API, et publie un post LinkedIn **seulement si l'événement est majeur** (zero-day exploité, breach massif, cyberattaque infra critique, rupture IA structurante).

 Le bot peut être recyclé sur **n'importe quel autre sujet** (dev, achats, RH, finance, etc.) en éditant 3 fichiers.
---

## Sommaire

- [Architecture (schéma)](#architecture-schema)
- [Stack technique](#stack-technique)
- [Comment ça tourne, jour par jour](#comment-ca-tourne-jour-par-jour)
- [Obtenir et configurer la clé Anthropic Claude](#obtenir-et-configurer-la-cle-anthropic-claude)
- [Recréer l'automatisation Make.com from scratch](#recreer-le-scenario-makecom-from-scratch)
- [Recréer le repo GitHub from scratch](#recreer-le-repo-github-from-scratch)
- [⚙️ Adapter le bot à un autre sujet](#adapter-le-bot-a-un-autre-sujet)
- [⚙️ Modifier la template (ton, format, longueur) du post](#modifier-la-template-du-post)
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

## Obtenir et configurer la clé Anthropic Claude

Le bot a besoin d'une clé API Anthropic pour scorer les news et rédiger les posts. **Sans clé, rien ne marche.**

### Étape 1 — Créer le compte et acheter du crédit

1. Va sur https://console.anthropic.com et signup (email ou Google).
2. Tu arrives sur le dashboard de la **Claude Console**.
3. Menu de gauche → **Billing** → **Buy credits**.
4. Ajoute **5$ minimum** (paiement Stripe). Ces 5$ couvrent **environ 1000 à 1500 posts**, soit ~2 ans à 2 posts/semaine.
5. Vérifie que tu vois "**Credit balance : 5.00 USD**" sur la page Billing.

> ⚠️ Tu peux générer une clé sans crédit, mais elle renvoie **`credit balance too low`** à la première requête.

### Étape 2 — Créer la clé API

1. Menu de gauche → **API keys**.
2. **Create Key**.
3. **Create in Workspace** : laisse `Default` (c'est là où sont les 5$).
4. **Name your key** : `linkedin-bot` (ou ce que tu veux).
5. Clique **Add**.
6. **⚠️ La clé n'est affichée qu'UNE SEULE FOIS.** Format : `sk-ant-api03-XXXXX...XXXX` (108 caractères).
7. Clique **Copy key** et garde-la quelque part de sûr.

```
┌─ Save your API key ────────────────────────────────────────┐
│ Keep a record of the key below. You won't be able          │
│ to view it again.                                          │
│                                                            │
│ ┌────────────────────────────────────────────────────┐     │
│ │ sk-ant-api03-IXGfBen-j8WAs0S3Z64NaFcMg4FgFC3j2...  │     │
│ │ ...baHvOAAA                              [Copy]    │     │
│ └────────────────────────────────────────────────────┘     │
│                                                            │
│                                              [Close]       │
└────────────────────────────────────────────────────────────┘
```

### Étape 3 — Où la mettre

Selon où tu utilises le bot :

| Contexte | Où coller la clé |
|---|---|
| **Test local** (sur ton PC) | Fichier `.env` à la racine du projet, ligne `ANTHROPIC_API_KEY=sk-ant-...` |
| **Production GitHub Actions** | GitHub repo → **Settings → Secrets and variables → Actions → New repository secret** → Name `ANTHROPIC_API_KEY`, Value = la clé |

Exemple de `.env` complet (à créer à partir de `.env.example`) :

```bash
ANTHROPIC_API_KEY=sk-ant-api03-IXGfBen-j8WAs0S3Z64NaFcMg4FgFC3j2...baHvOAAA
MAKE_WEBHOOK_URL=https://hook.eu1.make.com/REDACTED_OLD_WEBHOOK_ID
```

### Étape 4 — Vérifier que la clé marche

```bash
python src/main_webhook_llm.py --dry-run
```

Si tu vois `Sending N articles to Claude for scoring...` puis `Scored N articles. Top = 9.x (...)`, c'est bon.

Si tu vois `credit balance too low` → le workspace de la clé n'a pas de crédit (re-vérifie étape 1).  
Si tu vois `invalid x-api-key` → clé mal copiée (regénère, attention aux espaces/retours à la ligne).

### Coût réel observé

Avec le modèle `claude-sonnet-4-6` et le prompt actuel :
- 1 run complet = scoring de ~30 articles + rédaction d'un post = **~0.004 USD**
- 2 posts/semaine = 8 posts/mois = **~0.03 USD/mois**
- Les **5$ initiaux durent environ 14 ans** à ce rythme.

---

## Recréer le scenario Make.com from scratch

Tu en as besoin si tu repars de zéro, changes d'org Make, ou veux comprendre le câblage. Pour de vraies captures d'écran, voir [`docs/SCREENSHOTS_GUIDE.md`](docs/SCREENSHOTS_GUIDE.md) (mode manuel ou Playwright).

### Vue d'ensemble du scenario final

```
┌─ Make.com Scenario "Webhooks d'intégration, LinkedIn" ──────────────┐
│                                                                      │
│   [Toggle Actif: ON ⬤────]                                           │
│                                                                      │
│      ╔═══════════╗      ╔═══════════╗      ╔═══════════════╗         │
│      ║  Webhook  ║ ──▶  ║   HTTP    ║ ──▶  ║   LinkedIn    ║         │
│      ║  Custom   ║      ║ Download  ║      ║ Create a User ║         │
│      ║  webhook  ║      ║  a file   ║      ║  Image Post   ║         │
│      ╚═══════════╝      ╚═══════════╝      ╚═══════════════╝         │
│         #1                  #2                  #3                   │
│      reçoit JSON       télécharge          publie texte +            │
│      du bot Python     l'image depuis      image sur LinkedIn        │
│      (text, image_url) image_url           via OAuth Make            │
│                                                                      │
│   [Immediately as data arrives: ON ⬤────]                            │
└──────────────────────────────────────────────────────────────────────┘
```

### Étape 1 — Compte Make

1. Sign up sur https://make.com (region Europe).
2. Dashboard → **Create a new scenario**.

### Étape 2 — Module 1 : Webhook trigger

```
┌─ Webhook · Custom webhook ─────────────────────────────────┐
│ Webhook * :                                                │
│   ┌──────────────────────────────────────────────────┐     │
│   │ linkedin-bot                       [Edit] [Add]  │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│   URL: https://hook.eu1.make.com/f9r1ggx9e441aca8...       │
│   [Copy address to clipboard] [Stop]                       │
│                                                            │
│   ✅ Successfully determined (after first POST)            │
└────────────────────────────────────────────────────────────┘
```

1. Clic le grand `+` violet au centre du canvas.
2. Cherche `Webhooks` → choisis **Custom webhook**.
3. **Add** → Webhook name : `linkedin-bot` → **Save**.
4. Copie l'URL affichée. C'est `MAKE_WEBHOOK_URL`.
5. Envoie un premier payload de test pour que Make détecte la structure JSON :
   ```bash
   python src/main_webhook_llm.py
   ```
   Make doit afficher **"Successfully determined"**. Clique **Save**.

### Étape 3 — Module 2 : HTTP Download a file

```
┌─ HTTP · Download a file ───────────────────────────────────┐
│ Authentication type * :                                    │
│   ┌──────────────────────────────┐                         │
│   │ No authentication         ▼  │                         │
│   └──────────────────────────────┘                         │
│                                                            │
│ URL * :                                                    │
│   ┌──────────────────────────────────────────────────┐     │
│   │ [1.image_url] ← pill rouge violet de la variable │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│ [Cancel]                                          [Save]   │
└────────────────────────────────────────────────────────────┘
```

1. Clic le `+` à droite du Webhook.
2. Cherche `HTTP` → choisis **Download a file**.
3. Champ **URL** : tape manuellement `{{1.image_url}}` (Make le reconnaît comme variable et l'affiche en pill).
4. Authentication type : **No authentication**.
5. **Save**.

### Étape 4 — Module 3 : LinkedIn Create a User Image Post

```
┌─ LinkedIn · Create a User Image Post ──────────────────────┐
│ Connection * :                                             │
│   ┌──────────────────────────────────────────────────┐     │
│   │ My LinkedIn connection (Ilyes...)        [Add]   │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│ Choose Upload Method * :                                   │
│   ┌──────────────────────────────┐                         │
│   │ Upload by file            ▼  │                         │
│   └──────────────────────────────┘                         │
│                                                            │
│ File :                                                     │
│   ○ HTTP - Download a file                                 │
│   ● Map                          ← cocher celui-ci !       │
│                                                            │
│   File name * :                                            │
│   ┌──────────────────────────────────────────────────┐     │
│   │ [2. File name]                                   │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│   Data * :                                                 │
│   ┌──────────────────────────────────────────────────┐     │
│   │ [2. Data]                                        │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│ Title :       (laisser vide)                               │
│ Alt Text :    (laisser vide)                               │
│                                                            │
│ Content * :                                                │
│   ┌──────────────────────────────────────────────────┐     │
│   │ [1. text]   ← variable du webhook                │     │
│   └──────────────────────────────────────────────────┘     │
│                                                            │
│ Visibility * :                                             │
│   ┌──────────────────────────────┐                         │
│   │ Anyone                    ▼  │                         │
│   └──────────────────────────────┘                         │
│                                                            │
│ [Cancel]                                          [Save]   │
└────────────────────────────────────────────────────────────┘
```

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

### Étape 6 — Voir les exécutions (debug)

Une fois actif, l'onglet **History** liste chaque webhook reçu :

```
┌─ History ──────────────────────────────────────────────────┐
│ Started               Trigger      Status   Duration       │
│ 20 mai 2026, 12:50    Instantané   Succès    1 sec   3 cr  │
│ 20 mai 2026, 12:33    Instantané   Succès    2 sec   3 cr  │
│ 19 mai 2026, 12:12    Instantané   Succès    1 sec   3 cr  │
│ ...                                                        │
└────────────────────────────────────────────────────────────┘
```

Statut Succès = post LinkedIn publié.  
Statut Erreur = clique sur la ligne pour voir le détail (token LinkedIn expiré, image inaccessible, etc.).

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

## Modifier la template du post

La template (ton, structure, longueur, hashtags) est intégralement définie dans le **system prompt** de Claude dans [`src/writer.py`](src/writer.py).

### Format actuel par défaut

```
[LIGNE 1 — phrase-choc ultra courte, 6-10 mots]
[LIGNE 2 — 2e phrase-choc qui creuse, 10-15 mots]

🎯 Le fond : [2 phrases max, précises, chiffrées si possible]

[1 question provocante courte, "vous/votre" pour impliquer]

🔗 Détails : <URL>

#Hashtag1 #Hashtag2 #Hashtag3
```

Total : **80-130 mots max**, optimisé "scroll-stop" pour LinkedIn mobile.

### Où éditer exactement

[`src/writer.py`](src/writer.py) lignes **23-78** contiennent le `SYSTEM_PROMPT`. Voici les blocs à toucher selon ce que tu veux changer :

| Tu veux changer... | Lignes à toucher dans `writer.py` | Quoi y faire |
|---|---|---|
| **L'audience** | ligne 26 (`Audience : RSSI, CTO...`) | Remplacer par ton audience (ex: "directeurs achats", "head of HR") |
| **L'identité du writer** | ligne 24 (`Tu es un copywriter LinkedIn expert du format viral cyber/IA`) | Remplacer "cyber/IA" par ton secteur |
| **La longueur du post** | ligne 50 (`MAX 100 mots TOTAL`) + ligne 38 (`80-130 mots MAX`) | Mettre 50/150/200 selon ce que tu veux |
| **Les emojis bullet** (`🎯 Le fond`) | lignes 44-46 | Changer `🎯` `🔗` ou virer-les complètement |
| **Le nom des sections** (`Le fond`, `Détails`) | lignes 44, 48 | Renommer en `📌 Pourquoi c'est important`, `📰 Article complet`, etc. |
| **Le nombre de hashtags** | ligne 56 (`3 hashtags max`) | Mettre 5, ou 0 |
| **Les interdictions de style** | lignes 60-68 | Ajouter / retirer des mots-clés (ex: enlever l'interdiction du tiret cadratin) |
| **Les exemples de ligne 1** | lignes 72-77 | Remplacer par des exemples métier que Claude doit imiter |
| **La langue du post** | tout le prompt | Remplacer "français" par "anglais", "espagnol", etc. |

### Exemples de templates alternatives

**Template "Analyse approfondie" (200+ mots, ton expert)**

Remplacer les lignes 38-56 par :

```python
FORMAT IMPOSÉ (200-300 mots, ton analyse expert) :

[Accroche : 1 phrase qui résume l'événement clé, 15-20 mots]

[2 paragraphes courts de 3-4 phrases chacun : contexte + analyse]

💡 Mon point de vue : [2 phrases personnelles avec ton avis tranché]

[Question ouverte 1 phrase]

#Hashtag1 #Hashtag2 #Hashtag3 #Hashtag4 #Hashtag5
```

**Template "Liste à puces" (court mais avec des bullets)**

```python
FORMAT IMPOSÉ (100 mots, format liste) :

[Accroche : 1 phrase contexte, 10-15 mots]

Ce qu'il faut retenir :
• [Point 1 - chiffre ou fait précis]
• [Point 2 - chiffre ou fait précis]
• [Point 3 - chiffre ou fait précis]

[Question 1 phrase]

🔗 Source : <URL>

#Hashtag1 #Hashtag2
```

**Template "Storytelling" (narratif)**

```python
FORMAT IMPOSÉ (150 mots, narratif) :

[Hook narratif : "Hier...", "Cette semaine...", 1 phrase 10-15 mots]

[Récit court 3-4 phrases qui raconte l'événement comme une histoire]

[Punchline qui révèle l'enseignement, 1 phrase]

[Question 1 phrase]

🔗 <URL>

#Hashtag1 #Hashtag2 #Hashtag3
```

### Tester un changement de template

```bash
# Édite src/writer.py
# Puis :
python src/main_webhook_llm.py --dry-run
```

Le script affiche le post généré sans rien envoyer à Make ni LinkedIn. Tu itères jusqu'à être satisfait, puis commit + push.

### Garde-fous à NE PAS supprimer

Quel que soit ton template, **ces interdictions valent pour tous les sujets** (laisser dans le prompt) :

```
INTERDICTIONS ABSOLUES :
- Tiret cadratin « — » : jamais. Utilise virgule, point, ou deux phrases.
- Phrases longues, tournures balancées (« non seulement X mais aussi Y »).
- Mots creux : « fondamental », « crucial », « essentiel », « notamment ».
- Formules « Ce cas illustre », « Dans un monde où ».
- Ton académique, corporate, emphatique.
```

Ce sont les tics de langage qui font "post écrit par IA" et tuent l'engagement. Ils marchent sur tous les sujets.

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

## Captures d'écran

L'architecture est documentée principalement avec des **diagrammes ASCII** (durables, ne périment pas quand l'UI Make/GitHub change). Pour ajouter de vraies captures :

- **Manuel** : Win+Shift+S sur chaque écran utile, sauver dans `docs/screenshots/` avec les noms suggérés dans [`docs/SCREENSHOTS_GUIDE.md`](docs/SCREENSHOTS_GUIDE.md)
- **Automatisé** : `python docs/take_screenshots.py` (nécessite Playwright, demande le login Make + GitHub à la première exécution)

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
