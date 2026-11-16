"""Ligne de commande : python -m maison "12 rue de la Paix 75002 Paris" [--pdf] [--ia]."""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from dataclasses import asdict
from pathlib import Path

from . import cartes, recit, rendu, sources

MARQUE_PAR_DEFAUT = "L'histoire de votre maison"


def slug(texte: str) -> str:
    texte = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texte.lower()).strip("-")[:80] or "livret"


def generer(
    texte_adresse: str,
    dossier_sortie: Path,
    *,
    pdf: bool = False,
    ia: bool = False,
    marque: str = MARQUE_PAR_DEFAUT,
    pixels: int = 1000,
) -> dict[str, Path]:
    faits_obj = sources.collecter(texte_adresse)
    faits = faits_obj.en_dict()
    adresse = faits_obj.adresse
    images = cartes.toutes_les_epoques(adresse.lon, adresse.lat, pixels)

    sections = recit.construire(faits, set(images))
    if ia:
        from . import ia as module_ia

        sections = module_ia.enrichir(faits, sections)
    liste_sources = recit.sources_et_licences(faits, set(images))

    dossier = dossier_sortie / slug(adresse.label)
    dossier.mkdir(parents=True, exist_ok=True)
    fichiers: dict[str, Path] = {}

    html = rendu.livret_html(faits, sections, images, liste_sources, marque)
    fichiers["html"] = dossier / "livret.html"
    fichiers["html"].write_text(html, encoding="utf-8")

    fichiers["faits"] = dossier / "faits.json"
    fichiers["faits"].write_text(
        json.dumps(
            {"faits": faits, "epoques_disponibles": sorted(images), "sections": [asdict(s) for s in sections]},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    if "1950" in images and "aujourdhui" in images:
        commune = (faits.get("commune") or {}).get("nom") or adresse.commune
        visuel = rendu.avant_apres(
            images["1950"], images["aujourdhui"], f"{commune} · hier et aujourd'hui",
            "1950-1965", "Aujourd'hui", marque,
        )
        fichiers["avant_apres"] = dossier / "avant-apres.jpg"
        visuel.save(fichiers["avant_apres"], "JPEG", quality=85, optimize=True)

    if pdf:
        chemin_pdf = dossier / "livret.pdf"
        if rendu.exporter_pdf(fichiers["html"], chemin_pdf):
            fichiers["pdf"] = chemin_pdf
        else:
            print("PDF non généré (Node + Playwright requis).", file=sys.stderr)
    return fichiers


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m maison", description=__doc__)
    parser.add_argument("adresse", help="Adresse postale française")
    parser.add_argument("--sortie", type=Path, default=Path("sortie"), help="Dossier de sortie")
    parser.add_argument("--pdf", action="store_true", help="Produire aussi le PDF (Node + Playwright)")
    parser.add_argument("--ia", action="store_true", help="Réécrire le récit avec Claude (clé API requise)")
    parser.add_argument("--marque", default=MARQUE_PAR_DEFAUT, help="Nom affiché sur le livret")
    parser.add_argument("--pixels", type=int, default=1000, help="Taille des images (px)")
    args = parser.parse_args(argv)
    try:
        fichiers = generer(
            args.adresse, args.sortie, pdf=args.pdf, ia=args.ia, marque=args.marque, pixels=args.pixels
        )
    except sources.AdresseIntrouvable as e:
        print(str(e), file=sys.stderr)
        return 2
    for nature, chemin in fichiers.items():
        print(f"{nature}: {chemin}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
