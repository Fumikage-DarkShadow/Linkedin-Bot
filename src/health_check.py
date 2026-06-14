"""
Health check Make.com : verifie que le scenario est actif avant chaque run.

Pourquoi : si Make.com auto-desactive le scenario (validation error, token expire, etc.),
notre POST renvoie 200 Accepted mais rien n'est publie. Le script Python n'a jamais
de signal d'erreur, GitHub Actions reste vert. On peut perdre des semaines sans le voir.

Avec ce check : si le scenario est inactif, on leve une exception au lieu de poster.
Le run GitHub Actions devient rouge, et GitHub envoie un email d'alerte.

.env requis :
  MAKE_API_TOKEN     : token Make (cree sur https://eu1.make.com/en/users/me/api)
  MAKE_SCENARIO_ID   : ID numerique du scenario (visible dans l'URL d'edition)
"""
from __future__ import annotations

import logging
import os

import requests

log = logging.getLogger(__name__)

MAKE_API_BASE = "https://eu1.make.com/api/v2"


class ScenarioInactiveError(RuntimeError):
    """Le scenario Make est inactif. Reactiver avant de poster."""


class HealthCheckError(RuntimeError):
    """Probleme d'acces a l'API Make (token invalide, reseau, etc.)."""


def check_scenario_active(scenario_id: str | None = None, api_token: str | None = None,
                          *, timeout: int = 10) -> dict:
    """Verifie que le scenario Make est actif.

    Retourne le dict de la reponse API si OK.
    Leve ScenarioInactiveError si le scenario est inactif.
    Leve HealthCheckError si l'API ne repond pas.
    """
    scenario_id = scenario_id or os.getenv("MAKE_SCENARIO_ID")
    api_token = api_token or os.getenv("MAKE_API_TOKEN")

    if not scenario_id or not api_token:
        # Si pas configure, on log un warning mais on n'echoue pas (compat retro)
        log.warning("Health check Make skip: MAKE_API_TOKEN ou MAKE_SCENARIO_ID absent du .env")
        return {"skipped": True}

    url = f"{MAKE_API_BASE}/scenarios/{scenario_id}"
    headers = {"Authorization": f"Token {api_token}"}

    log.info("Health check Make scenario id=%s...", scenario_id)
    try:
        r = requests.get(url, headers=headers, timeout=timeout)
    except requests.RequestException as e:
        raise HealthCheckError(f"Make API unreachable: {e}") from e

    if r.status_code == 401:
        raise HealthCheckError("Make API token invalide (401). Recree un token sur Make > Profile > API.")
    if r.status_code == 404:
        raise HealthCheckError(f"Scenario id={scenario_id} introuvable (404).")
    if r.status_code >= 400:
        raise HealthCheckError(f"Make API HTTP {r.status_code}: {r.text[:200]}")

    data = r.json().get("scenario", r.json())
    is_active = bool(data.get("isActive", data.get("is_active", False)))
    scheduling_type = (data.get("scheduling") or {}).get("type", "?")

    log.info("Scenario state: isActive=%s, scheduling=%s", is_active, scheduling_type)

    if not is_active:
        raise ScenarioInactiveError(
            f"Make scenario id={scenario_id} est INACTIF. "
            f"Aller sur https://eu1.make.com et reactiver le toggle avant de relancer."
        )

    log.info("Health check OK: scenario actif.")
    return data


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    try:
        check_scenario_active()
        print("OK")
        sys.exit(0)
    except ScenarioInactiveError as e:
        print(f"INACTIVE: {e}")
        sys.exit(1)
    except HealthCheckError as e:
        print(f"ERROR: {e}")
        sys.exit(2)
