"""Emails au client : le livret (avec la confirmation légale de commande) ou un message d'attente.

Usage :
  python -m maison.envoi --dossier sortie/<slug> --email client@exemple.fr [--commande cs_…]
  python -m maison.envoi --email client@exemple.fr --message verification|prise-en-charge [--commande cs_…]

Canal d'envoi (le premier configuré est utilisé) :
  RESEND_API_KEY + EXPEDITEUR (domaine vérifié chez Resend)
  ou SMTP_HOST, SMTP_PORT (465 par défaut), SMTP_USER, SMTP_PASSWORD [+ EXPEDITEUR] : n'importe quelle boîte
  existante (ex. Gmail avec mot de passe d'application) — sans domaine ni frais.
Variables facultatives : CONTACT (adresse de réponse), URL_CGV, PRIX (ex. « 29 € »).
Sans canal configuré, rien n'est envoyé et le code de sortie vaut 3.
"""

from __future__ import annotations

import argparse
import base64
import html as html_lib
import json
import os
import re
import smtplib
import ssl
import sys
import urllib.error
import urllib.request
from email.message import EmailMessage
from email.utils import formataddr, parseaddr
from pathlib import Path

API = "https://api.resend.com/emails"
EMAIL_VALIDE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAILLE_MAX_PIECES = 35 * 1024 * 1024  # marge sous la limite de 40 Mo de Resend


STYLE = 'font-family:Georgia,serif;font-size:16px;line-height:1.5;color:#2b2622'

MESSAGES = {
    "verification": (
        "Votre commande : L'histoire de votre maison",
        "<p>Bonjour,</p><p>Merci pour votre commande. Avant de vous envoyer votre livret, nous vérifions à la main "
        "qu'il correspond bien à votre adresse (adresse incomplète, lieu-dit ou zone moins bien couverte par les "
        "archives). Vous le recevrez <strong>sous 24 heures</strong>.</p><p>Si l'adresse saisie était incomplète, "
        "répondez simplement à cet email avec l'adresse exacte.</p>",
    ),
    "prise-en-charge": (
        "Votre commande : L'histoire de votre maison",
        "<p>Bonjour,</p><p>Merci pour votre commande. Votre livret n'a pas pu être produit automatiquement : nous "
        "le préparons à la main et vous l'envoyons <strong>sous 24 heures</strong>. Si nous ne pouvons pas le "
        "réaliser pour votre adresse, vous serez intégralement remboursé.</p><p>Vous pouvez répondre à cet email "
        "pour préciser l'adresse.</p>",
    ),
}


def confirmation_legale(commande: str, prix: str, url_cgv: str) -> str:
    """Confirmation de commande sur support durable (art. L221-13 C. conso.), jointe à la livraison."""

    ref = f" n° {html_lib.escape(commande)}" if commande else ""
    cgv = f' <a href="{url_cgv}">Conditions générales de vente</a>.' if url_cgv else ""
    montant = f" ({prix} TTC)" if prix else ""
    return (
        f'<hr style="border:0;border-top:1px solid #d9cfc0"><p style="font-size:13px;color:#6b6158">'
        f"Récapitulatif de votre commande{ref} : livret numérique personnalisé « L'histoire de votre maison »"
        f"{montant}. Vous avez demandé sa fourniture immédiate et reconnu perdre ainsi votre droit de rétractation "
        f"(article L221-28 13° du Code de la consommation).{cgv} Si le livret ne correspond pas à votre adresse, "
        f"répondez à cet email : nous le refaisons ou vous remboursons.</p>"
    )


def corps_html(commune: str, commande: str = "", prix: str = "", url_cgv: str = "") -> str:
    return f"""<div style="{STYLE}">
<p>Bonjour,</p>
<p>Voici votre livret <strong>« L'histoire de votre maison »</strong>{f' à {html_lib.escape(commune)}' if commune else ''}, en pièce jointe (PDF).</p>
<p>Vous trouverez aussi l'image « hier et aujourd'hui », prête à partager. Elle n'indique que la commune, jamais votre adresse exacte.</p>
<p>Bonne lecture !</p>
{confirmation_legale(commande, prix, url_cgv)}
</div>"""


def pieces_du_livret(dossier: Path) -> list[dict[str, str]]:
    pieces = []
    for nom in ("livret.pdf", "avant-apres.jpg"):
        chemin = dossier / nom
        if chemin.exists():
            pieces.append({"filename": nom, "content": base64.b64encode(chemin.read_bytes()).decode("ascii")})
    if not any(p["filename"] == "livret.pdf" for p in pieces):
        livret_html = dossier / "livret.html"
        if not livret_html.exists():
            raise FileNotFoundError("aucun livret à envoyer")
        pieces.append({"filename": "livret.html", "content": base64.b64encode(livret_html.read_bytes()).decode("ascii")})
    if sum(len(p["content"]) for p in pieces) > TAILLE_MAX_PIECES:
        raise ValueError("pièces jointes trop volumineuses")
    return pieces


def commune_du_livret(dossier: Path) -> str:
    faits = dossier / "faits.json"
    if not faits.exists():
        return ""
    donnees = json.loads(faits.read_text(encoding="utf-8"))["faits"]
    return (donnees.get("commune") or {}).get("nom") or donnees["adresse"].get("commune", "")


def _par_resend(charge: dict, cle_api: str) -> str:
    requete = urllib.request.Request(
        API,
        data=json.dumps(charge).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {cle_api}",
            "Content-Type": "application/json",
            "User-Agent": "maison-histoire/0.2",
        },
        method="POST",
    )
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8")).get("id", "")


def _par_smtp(charge: dict, env: dict[str, str]) -> str:
    message = EmailMessage()
    message["From"] = charge["from"]
    message["To"] = ", ".join(charge["to"])
    message["Subject"] = charge["subject"]
    if charge.get("reply_to"):
        message["Reply-To"] = charge["reply_to"]
    message.set_content("Ce message est au format HTML.")
    message.add_alternative(charge["html"], subtype="html")
    for piece in charge.get("attachments", []):
        donnees = base64.b64decode(piece["content"])
        principal, secondaire = {
            ".pdf": ("application", "pdf"),
            ".jpg": ("image", "jpeg"),
            "html": ("text", "html"),
        }.get(piece["filename"][-4:], ("application", "octet-stream"))
        message.add_attachment(donnees, maintype=principal, subtype=secondaire, filename=piece["filename"])
    port = int(env.get("SMTP_PORT") or 465)
    contexte = ssl.create_default_context()
    if port == 465:
        serveur: smtplib.SMTP = smtplib.SMTP_SSL(env["SMTP_HOST"], port, context=contexte, timeout=60)
    else:
        serveur = smtplib.SMTP(env["SMTP_HOST"], port, timeout=60)
        serveur.starttls(context=contexte)
    with serveur:
        serveur.login(env["SMTP_USER"], env["SMTP_PASSWORD"])
        serveur.send_message(message)
    return message.get("Message-ID", "smtp")


def canal(env: dict[str, str]) -> str | None:
    if env.get("RESEND_API_KEY"):
        return "resend"
    if env.get("SMTP_HOST") and env.get("SMTP_USER") and env.get("SMTP_PASSWORD"):
        return "smtp"
    return None


def expediteur_par_defaut(env: dict[str, str]) -> str:
    if env.get("EXPEDITEUR"):
        return env["EXPEDITEUR"]
    if canal(env) == "smtp":  # une boîte SMTP envoie sous sa propre adresse
        return formataddr(("L'histoire de votre maison", env["SMTP_USER"]))
    return "L'histoire de votre maison <onboarding@resend.dev>"


def envoyer(
    email: str,
    env: dict[str, str],
    *,
    dossier: Path | None = None,
    message: str | None = None,
    commande: str = "",
) -> str:
    if not EMAIL_VALIDE.match(email):
        raise ValueError("adresse email invalide")
    mode = canal(env)
    if mode is None:
        raise LookupError("aucun canal d'envoi configuré (RESEND_API_KEY ou SMTP_*)")
    if message:
        sujet, contenu = MESSAGES[message]
        html, pieces = f'<div style="{STYLE}">{contenu}</div>', []
    else:
        if dossier is None:
            raise ValueError("dossier du livret requis")
        pieces = pieces_du_livret(dossier)
        sujet = "Votre livret : L'histoire de votre maison"
        html = corps_html(commune_du_livret(dossier), commande, env.get("PRIX", ""), env.get("URL_CGV", ""))
    charge: dict = {"from": expediteur_par_defaut(env), "to": [email], "subject": sujet, "html": html}
    if pieces:
        charge["attachments"] = pieces
    contact = env.get("CONTACT", "")
    if contact and parseaddr(contact)[1]:
        charge["reply_to"] = contact
    return _par_resend(charge, env["RESEND_API_KEY"]) if mode == "resend" else _par_smtp(charge, env)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m maison.envoi")
    parser.add_argument("--dossier", type=Path)
    parser.add_argument("--email", required=True)
    parser.add_argument("--message", choices=sorted(MESSAGES), help="Message d'attente au lieu du livret")
    parser.add_argument("--commande", default="", help="Référence de commande (confirmation légale)")
    args = parser.parse_args(argv)

    env = dict(os.environ)
    if canal(env) is None:
        print("Aucun canal d'envoi (RESEND_API_KEY ou SMTP_HOST/SMTP_USER/SMTP_PASSWORD) : envoi ignoré.", file=sys.stderr)
        return 3
    try:
        identifiant = envoyer(args.email, env, dossier=args.dossier, message=args.message, commande=args.commande)
    except urllib.error.HTTPError as e:
        print(f"Échec de l'envoi : HTTP {e.code} {e.read()[:200]!r}", file=sys.stderr)
        return 1
    except (ValueError, LookupError, FileNotFoundError, urllib.error.URLError, smtplib.SMTPException, OSError) as e:
        print(f"Échec de l'envoi : {type(e).__name__} {e}", file=sys.stderr)
        return 1
    print(f"Email envoyé (id {identifiant}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
