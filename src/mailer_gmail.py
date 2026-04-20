"""
Envoi du post quotidien via Gmail SMTP (TLS port 587).

Prérequis dans .env :
  GMAIL_USER=tonemail@gmail.com
  GMAIL_APP_PASSWORD=xxxxxxxxxxxxxxxx    # 16 chars, sans espaces

Comment obtenir l'app password :
  1. Activer la 2FA sur ton compte Google
  2. https://myaccount.google.com/apppasswords
  3. Créer un nouveau mot de passe -> copier les 16 caractères
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

log = logging.getLogger(__name__)

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587


def _html_escape(txt: str) -> str:
    return (txt.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _format_html(post: str, source_title: str, source_url: str, score: float) -> str:
    post_html = _html_escape(post).replace("\n", "<br>")
    return f"""\
<html>
<body style="font-family: Segoe UI, Arial, sans-serif; max-width: 720px;">
  <h2 style="color:#0A66C2; margin-bottom: 4px;">📬 Post LinkedIn du jour</h2>
  <p style="color:#666; margin-top:0;">Score d'impact : <b>{score:.1f}/10</b></p>

  <div style="border: 1px solid #ddd; border-radius: 8px; padding: 20px;
              background: #fafafa; white-space: pre-wrap; font-size: 15px;
              line-height: 1.55; margin: 16px 0;">
{post_html}
  </div>

  <p style="color:#888; font-size: 13px;">
    👉 <b>Copie le bloc ci-dessus</b> et colle-le sur LinkedIn.
  </p>

  <hr style="margin-top: 24px;">
  <p style="color:#555; font-size: 13px;">
    <b>Source :</b> {_html_escape(source_title)}<br>
    <a href="{_html_escape(source_url)}">{_html_escape(source_url)}</a>
  </p>
</body>
</html>"""


def send_post_email(
    to_address: str,
    subject: str,
    post: str,
    source_title: str,
    source_url: str,
    score: float,
    *,
    display_only: bool = False,
) -> None:
    """Envoie le post via Gmail SMTP. `display_only` ignoré ici (compat API)."""
    gmail_user = os.getenv("GMAIL_USER")
    gmail_pwd = os.getenv("GMAIL_APP_PASSWORD", "").replace(" ", "")

    if display_only:
        log.info("[DISPLAY-ONLY] Post preview:\n%s", post)
        return

    if not gmail_user or not gmail_pwd:
        raise RuntimeError("GMAIL_USER or GMAIL_APP_PASSWORD missing in .env")

    msg = MIMEMultipart("alternative")
    msg["From"] = gmail_user
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.attach(MIMEText(post, "plain", "utf-8"))  # fallback text
    msg.attach(MIMEText(_format_html(post, source_title, source_url, score), "html", "utf-8"))

    log.info("Connecting to %s:%d (user=%s)...", SMTP_HOST, SMTP_PORT, gmail_user)
    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        smtp.login(gmail_user, gmail_pwd)
        smtp.send_message(msg)

    log.info("Email sent to %s via Gmail SMTP.", to_address)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Charger .env
    from pathlib import Path
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=True)

    send_post_email(
        to_address=os.getenv("GMAIL_USER"),  # test : s'envoyer à soi-même
        subject="[TEST Gmail SMTP] Mailer OK",
        post="Test Gmail SMTP — si tu vois ce mail, on est bons.\n\n#Test",
        source_title="Test technique",
        source_url="https://example.com",
        score=0.0,
    )
