"""
Envoi du post quotidien par email via Outlook local (COM, pas de SMTP).

Utilise le profil Outlook déjà configuré sur la machine.
Le post est envoyé en HTML pour faciliter le copier-coller (mise en forme préservée).
"""
from __future__ import annotations

import logging

log = logging.getLogger(__name__)


def _html_escape(txt: str) -> str:
    return (
        txt.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _format_html(post: str, source_title: str, source_url: str, score: float) -> str:
    """Construit un email HTML avec le post prêt à copier + contexte source."""
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
    """Envoie (ou affiche) le post via Outlook COM."""
    import win32com.client

    outlook = win32com.client.Dispatch("Outlook.Application")
    mail = outlook.CreateItem(0)  # 0 = olMailItem
    mail.To = to_address
    mail.Subject = subject
    mail.HTMLBody = _format_html(post, source_title, source_url, score)

    if display_only:
        mail.Display()
        log.info("Email displayed in Outlook (not sent).")
    else:
        mail.Send()
        log.info("Email sent to %s via Outlook.", to_address)


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    # Test rapide — affiche un mail de demo dans Outlook sans l'envoyer
    send_post_email(
        to_address="test@example.com",
        subject="[TEST] Mailer via Outlook COM",
        post="Ceci est un test.\n\n🎯 Quoi : test\n🧠 Pourquoi : verifier le mailer\n💥 Impact : on va publier le vrai post\n\nC'est cool non ?\n\n#Test #Bot",
        source_title="Test source",
        source_url="https://example.com",
        score=7.5,
        display_only=True,
    )
