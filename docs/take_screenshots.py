"""
Capture les 7 captures d'ecran de reference du bot (Make.com + GitHub).

Usage :
  pip install playwright
  playwright install chromium
  python docs/take_screenshots.py

Le script t'invite a te logger sur Make + GitHub a la premiere ouverture (cookies persistes
ensuite dans .playwright_profile). Puis il capture les 7 ecrans automatiquement.

Sortie : docs/screenshots/01-*.png ... 07-*.png
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

try:
    from playwright.sync_api import sync_playwright
except ImportError:
    print("Installe Playwright d'abord : pip install playwright && playwright install chromium")
    sys.exit(1)


ROOT = Path(__file__).resolve().parent.parent
PROFILE_DIR = ROOT / "docs" / ".playwright_profile"
OUT_DIR = ROOT / "docs" / "screenshots"
OUT_DIR.mkdir(exist_ok=True, parents=True)

# Configuration via variables d'environnement (ne pas hardcoder ses propres IDs)
# Trouve les IDs dans l'URL Make/GitHub quand tu es loggue.
MAKE_ORG_ID = os.getenv("MAKE_ORG_ID", "YOUR_ORG_ID")
MAKE_SCENARIO_ID = os.getenv("MAKE_SCENARIO_ID", "YOUR_SCENARIO_ID")
GITHUB_REPO = os.getenv("GITHUB_REPO", "YOUR_USERNAME/linkedin-bot")

MAKE_SCENARIO_URL = f"https://eu1.make.com/{MAKE_ORG_ID}/scenarios/{MAKE_SCENARIO_ID}/edit"
MAKE_HISTORY_URL = f"https://eu1.make.com/{MAKE_ORG_ID}/scenarios/{MAKE_SCENARIO_ID}/logs"
GH_ACTIONS_URL = f"https://github.com/{GITHUB_REPO}/actions/workflows/daily_post.yml"
GH_SECRETS_URL = f"https://github.com/{GITHUB_REPO}/settings/secrets/actions"


SHOTS = [
    ("01-make-overview.png", MAKE_SCENARIO_URL, "Vue diagramme Make scenario"),
    ("05-make-history.png", MAKE_HISTORY_URL, "Make History (runs)"),
    ("06-github-actions.png", GH_ACTIONS_URL, "GitHub Actions runs"),
    ("07-github-secrets.png", GH_SECRETS_URL, "GitHub Secrets list"),
]


def main():
    if "YOUR_" in MAKE_SCENARIO_URL or "YOUR_" in GH_ACTIONS_URL:
        print("Configure d'abord les variables d'environnement :")
        print("  set MAKE_ORG_ID=...")
        print("  set MAKE_SCENARIO_ID=...")
        print("  set GITHUB_REPO=tonusername/linkedin-bot")
        print()
        print("Trouve MAKE_ORG_ID + MAKE_SCENARIO_ID dans l'URL Make quand tu edites ton scenario.")
        sys.exit(1)
    print(f"Profile dir: {PROFILE_DIR}")
    print(f"Output dir : {OUT_DIR}")
    print(f"Make URL   : {MAKE_SCENARIO_URL}")
    print(f"GitHub URL : {GH_ACTIONS_URL}")
    print()
    with sync_playwright() as pw:
        context = pw.chromium.launch_persistent_context(
            str(PROFILE_DIR),
            headless=False,
            viewport={"width": 1600, "height": 900},
        )
        page = context.new_page()

        # Premier ecran = chance pour l'utilisateur de se logger
        page.goto(SHOTS[0][1])
        input("Connecte-toi sur Make.com et GitHub si demande, puis tape ENTREE pour lancer les captures...")

        for filename, url, label in SHOTS:
            out = OUT_DIR / filename
            print(f"  -> {label} ({filename})")
            page.goto(url, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2500)
            page.screenshot(path=str(out), full_page=False)

        print()
        print(f"Done. {len(SHOTS)} screenshots saved to {OUT_DIR}")
        print("Pour les modules detailles (Webhook config, HTTP, LinkedIn Image Post),")
        print("ouvre chaque module a la main sur Make et utilise Win+Shift+S.")
        context.close()


if __name__ == "__main__":
    main()
