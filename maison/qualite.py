"""Contrôle qualité d'un livret, sans aucune donnée personnelle.

Sert à deux choses :
- le journal de chaque commande (GitHub Actions) : ce que contient le livret, sans l'adresse ;
- la décision d'envoi : un livret douteux (adresse mal localisée, hors couverture, trop pauvre) n'est pas
  envoyé automatiquement. Il part en vérification humaine : mieux vaut un client prévenu qu'un livret de
  la mauvaise maison, qui finit en remboursement ou en litige.

Usage : python -m maison.qualite sortie/<slug>/faits.json   (code de sortie 0 = envoyable, 4 = à vérifier)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

EPOQUES_MIN = 3
SCORE_MIN = 0.6
OUTRE_MER = ("97", "98")


def evaluer(donnees: dict[str, Any]) -> dict[str, Any]:
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
    if rapport["precision"] != "housenumber":
        raisons.append(f"adresse localisée au niveau « {rapport['precision']} », pas au numéro : maison incertaine")
    if rapport["score_geocodage"] < SCORE_MIN:
        raisons.append(f"correspondance d'adresse faible ({rapport['score_geocodage']})")
    if len(epoques) < EPOQUES_MIN:
        raisons.append(f"seulement {len(epoques)} époque(s) disponible(s)")
    rapport["verdict"] = "a_verifier" if raisons else "envoyable"
    rapport["raisons"] = raisons
    return rapport


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Usage : python -m maison.qualite <faits.json>", file=sys.stderr)
        return 1
    rapport = evaluer(json.loads(Path(args[0]).read_text(encoding="utf-8")))
    print(json.dumps(rapport, ensure_ascii=False))
    return 0 if rapport["verdict"] == "envoyable" else 4


if __name__ == "__main__":
    raise SystemExit(main())
