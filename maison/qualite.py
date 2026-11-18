"""Contrôle qualité d'un livret, sans aucune donnée personnelle.

Sert à deux choses :
- le journal de chaque commande (GitHub Actions) : ce que contient le livret, sans l'adresse ;
- la décision d'envoi : un livret douteux (adresse mal localisée, hors couverture, trop pauvre) n'est pas
  envoyé automatiquement. Il part en vérification humaine : mieux vaut un client prévenu qu'un livret de
  la mauvaise maison, qui finit en remboursement ou en litige.

Usage : python -m maison.qualite livret/faits.json [--saisie "adresse tapée par le client"]
        (code de sortie 0 = envoyable, 4 = à vérifier)

Règles, établies sur des commandes de test réelles (novembre 2026) :
- outre-mer : les cartes anciennes ne couvrent pas ces territoires ;
- code postal absent de la saisie, ou différent de celui trouvé : « 12 rue Victor Hugo » sans ville a été
  localisé à Bordeaux avec un score élevé — un livret de la mauvaise maison ;
- localisation au niveau de la commune seulement, ou correspondance faible ;
- moins de 3 époques disponibles.
Une adresse de rue ou de lieu-dit (sans numéro) reste envoyable : les cartes sont justes à cette échelle et le
récit n'affirme rien sur le bâtiment sans numéro exact.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

EPOQUES_MIN = 3
SCORE_MIN = 0.6
OUTRE_MER = ("97", "98")


CODE_POSTAL = re.compile(r"(?<!\d)(\d{5})(?!\d)")


def evaluer(donnees: dict[str, Any], saisie: str | None = None) -> dict[str, Any]:
    faits = donnees.get("faits", {})
    adresse = faits.get("adresse") or {}
    epoques = list(donnees.get("epoques_disponibles") or [])
    code_postal = str(adresse.get("code_postal") or "")
    batiment = faits.get("batiment") or {}
    rapport: dict[str, Any] = {
        "precision": adresse.get("type") or "inconnue",
        "score_geocodage": round(float(adresse.get("score") or 0), 2),
        "departement": code_postal[:3] if code_postal.startswith(OUTRE_MER) else code_postal[:2],
        "epoques": epoques,
        "batiment": bool(batiment),
        "annee_batiment": bool(batiment.get("annee_construction") or batiment.get("annee_apparition")),
        "parcelle": bool(faits.get("parcelle")),
        "histoire_commune": bool(faits.get("wikipedia_commune")),
        "lieux_proches": len(faits.get("alentours") or []),
        "avertissements": len(faits.get("avertissements") or []),
    }
    raisons: list[str] = []
    if code_postal.startswith(OUTRE_MER):
        raisons.append("hors France métropolitaine : cartes anciennes non couvertes")
    if saisie is not None:
        tapes = CODE_POSTAL.findall(saisie)
        rapport["code_postal_saisi"] = bool(tapes)
        if not tapes:
            raisons.append("aucun code postal dans l'adresse saisie : commune incertaine")
        elif code_postal not in tapes:
            raisons.append("le code postal saisi ne correspond pas à l'adresse trouvée")
    if rapport["precision"] not in ("housenumber", "street", "locality"):
        raisons.append(f"adresse localisée seulement au niveau « {rapport['precision']} »")
    if rapport["score_geocodage"] < SCORE_MIN:
        raisons.append(f"correspondance d'adresse faible ({rapport['score_geocodage']})")
    if len(epoques) < EPOQUES_MIN:
        raisons.append(f"seulement {len(epoques)} époque(s) disponible(s)")
    rapport["verdict"] = "a_verifier" if raisons else "envoyable"
    rapport["raisons"] = raisons
    return rapport


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m maison.qualite")
    parser.add_argument("faits", type=Path)
    parser.add_argument("--saisie", help="Adresse telle que tapée par le client (jamais affichée)")
    args = parser.parse_args(argv)
    rapport = evaluer(json.loads(args.faits.read_text(encoding="utf-8")), args.saisie)
    print(json.dumps(rapport, ensure_ascii=False))
    return 0 if rapport["verdict"] == "envoyable" else 4


if __name__ == "__main__":
    raise SystemExit(main())
