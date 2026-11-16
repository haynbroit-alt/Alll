"""Envoi du livret par email via l'API Resend (offre gratuite : 3 000 emails/mois).

Usage : python -m maison.envoi --dossier sortie/<slug> --email client@exemple.fr
Variables d'environnement :
  RESEND_API_KEY  clé API Resend (obligatoire, sinon l'envoi est ignoré et le code de sortie vaut 3)
  EXPEDITEUR      ex. "L'histoire de votre maison <livret@votre-domaine.fr>" (domaine vérifié chez Resend)
"""

from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

API = "https://api.resend.com/emails"
EMAIL_VALIDE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TAILLE_MAX_PIECES = 35 * 1024 * 1024  # marge sous la limite de 40 Mo de Resend


def corps_html(commune: str) -> str:
    return f"""<div style="font-family:Georgia,serif;font-size:16px;line-height:1.5;color:#2b2622">
<p>Bonjour,</p>
<p>Voici votre livret <strong>« L'histoire de votre maison »</strong>{f' à {commune}' if commune else ''}, en pièce jointe (PDF).</p>
<p>Vous trouverez aussi l'image « hier et aujourd'hui », prête à partager. Elle n'indique que la commune, jamais votre adresse exacte.</p>
<p>Bonne lecture !</p>
</div>"""


def envoyer(dossier: Path, email: str, cle_api: str, expediteur: str) -> str:
    if not EMAIL_VALIDE.match(email):
        raise ValueError("adresse email invalide")
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

    commune = ""
    faits = dossier / "faits.json"
    if faits.exists():
        donnees = json.loads(faits.read_text(encoding="utf-8"))["faits"]
        commune = (donnees.get("commune") or {}).get("nom") or donnees["adresse"].get("commune", "")

    charge = {
        "from": expediteur,
        "to": [email],
        "subject": "Votre livret : L'histoire de votre maison",
        "html": corps_html(commune),
        "attachments": pieces,
    }
    requete = urllib.request.Request(
        API,
        data=json.dumps(charge).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {cle_api}",
            "Content-Type": "application/json",
            "User-Agent": "maison-histoire/0.1",
        },
        method="POST",
    )
    with urllib.request.urlopen(requete, timeout=60) as reponse:
        return json.loads(reponse.read().decode("utf-8")).get("id", "")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m maison.envoi")
    parser.add_argument("--dossier", type=Path, required=True)
    parser.add_argument("--email", required=True)
    args = parser.parse_args(argv)

    cle = os.environ.get("RESEND_API_KEY")
    if not cle:
        print("RESEND_API_KEY absente : envoi ignoré.", file=sys.stderr)
        return 3
    expediteur = os.environ.get("EXPEDITEUR") or "L'histoire de votre maison <onboarding@resend.dev>"
    try:
        identifiant = envoyer(args.dossier, args.email, cle, expediteur)
    except urllib.error.HTTPError as e:
        print(f"Échec de l'envoi : HTTP {e.code} {e.read()[:200]!r}", file=sys.stderr)
        return 1
    except (ValueError, FileNotFoundError, urllib.error.URLError) as e:
        print(f"Échec de l'envoi : {e}", file=sys.stderr)
        return 1
    print(f"Email envoyé (id {identifiant}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
