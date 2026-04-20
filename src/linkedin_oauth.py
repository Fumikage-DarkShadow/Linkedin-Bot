"""
Helper OAuth 2.0 LinkedIn — récupère access_token + user_urn et les écrit dans .env.

Usage (à faire une seule fois, puis tous les 60 jours quand le token expire) :

  1. Crée une app sur https://www.linkedin.com/developers/apps
  2. Dans "Auth" : ajoute Redirect URL = http://localhost:8765/callback
  3. Dans "Products" : active "Sign In with LinkedIn using OpenID Connect"
                      + "Share on LinkedIn"
  4. Copie Client ID et Client Secret.
  5. Lance :
       python src/linkedin_oauth.py --client-id XXX --client-secret YYY

  6. Ton navigateur s'ouvre, tu autorises, tu es redirigé, le token est écrit dans .env.

Scopes utilisés : openid profile w_member_social
  - openid/profile : pour récupérer le user URN
  - w_member_social : pour poster en ton nom
"""
from __future__ import annotations

import argparse
import http.server
import logging
import secrets
import socketserver
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

log = logging.getLogger("linkedin-oauth")

REDIRECT_PORT = 8765
REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"
AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
USERINFO_URL = "https://api.linkedin.com/v2/userinfo"
SCOPES = "openid profile w_member_social"

_received_code: dict[str, str] = {}
_expected_state: str = ""


class _CallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if parsed.path != "/callback":
            self.send_response(404)
            self.end_headers()
            return

        if "error" in params:
            self._reply(400, f"<h1>Erreur LinkedIn</h1><pre>{params}</pre>")
            _received_code["error"] = params.get("error_description", [""])[0]
            return

        state = params.get("state", [""])[0]
        if state != _expected_state:
            self._reply(400, "<h1>State mismatch (CSRF protection)</h1>")
            _received_code["error"] = "state_mismatch"
            return

        code = params.get("code", [""])[0]
        if not code:
            self._reply(400, "<h1>No code in callback</h1>")
            _received_code["error"] = "no_code"
            return

        _received_code["code"] = code
        self._reply(
            200,
            "<h1>Authentification LinkedIn OK</h1>"
            "<p>Tu peux fermer cet onglet et revenir au terminal.</p>",
        )

    def log_message(self, format, *args):
        pass  # silence default HTTP logs

    def _reply(self, status: int, html: str):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(html.encode("utf-8"))


def _build_auth_url(client_id: str, state: str) -> str:
    qs = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "state": state,
        "scope": SCOPES,
    })
    return f"{AUTH_URL}?{qs}"


def _exchange_code(client_id: str, client_secret: str, code: str) -> dict:
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "client_secret": client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=15,
    )
    r.raise_for_status()
    return r.json()


def _fetch_user_urn(access_token: str) -> str:
    r = requests.get(
        USERINFO_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=15,
    )
    r.raise_for_status()
    data = r.json()
    # OpenID userinfo renvoie "sub" = LinkedIn member ID
    return f"urn:li:person:{data['sub']}"


def _write_env(env_path: Path, access_token: str, user_urn: str) -> None:
    """Met à jour (ou crée) le fichier .env avec token + URN."""
    lines: list[str] = []
    if env_path.exists():
        lines = env_path.read_text(encoding="utf-8").splitlines()

    updates = {
        "LINKEDIN_ACCESS_TOKEN": access_token,
        "LINKEDIN_USER_URN": user_urn,
    }
    written = set()
    new_lines = []
    for line in lines:
        key = line.split("=", 1)[0].strip() if "=" in line else ""
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            written.add(key)
        else:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in written:
            new_lines.append(f"{key}={val}")

    env_path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


def run(client_id: str, client_secret: str, env_path: Path) -> None:
    global _expected_state
    _expected_state = secrets.token_urlsafe(16)

    server = socketserver.TCPServer(("localhost", REDIRECT_PORT), _CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    auth_url = _build_auth_url(client_id, _expected_state)
    print(f"\nOuverture du navigateur pour autorisation LinkedIn...")
    print(f"Si ca ne s'ouvre pas, copie-colle cette URL :\n  {auth_url}\n")
    webbrowser.open(auth_url)

    print("En attente du callback sur http://localhost:8765/callback ...")
    try:
        while "code" not in _received_code and "error" not in _received_code:
            thread.join(timeout=0.5)
    finally:
        server.shutdown()

    if "error" in _received_code:
        raise RuntimeError(f"OAuth failed: {_received_code['error']}")

    code = _received_code["code"]
    print("[OK] Code recu, echange contre un access token...")

    token_data = _exchange_code(client_id, client_secret, code)
    access_token = token_data["access_token"]
    expires_in = token_data.get("expires_in", "?")
    print(f"[OK] Access token obtenu (expire dans {expires_in} s).")

    user_urn = _fetch_user_urn(access_token)
    print(f"[OK] User URN : {user_urn}")

    _write_env(env_path, access_token, user_urn)
    print(f"\n[OK] Fichier .env mis a jour : {env_path}")
    print("\nTu peux maintenant lancer : python src/main.py --dry-run")


def main():
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    parser = argparse.ArgumentParser(description="LinkedIn OAuth 2.0 helper")
    parser.add_argument("--client-id", required=True, help="LinkedIn app Client ID")
    parser.add_argument("--client-secret", required=True, help="LinkedIn app Client Secret")
    parser.add_argument(
        "--env",
        default=str(Path(__file__).resolve().parent.parent / ".env"),
        help="Chemin du .env a mettre a jour (defaut: ../.env)",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run(args.client_id, args.client_secret, Path(args.env))


if __name__ == "__main__":
    main()
