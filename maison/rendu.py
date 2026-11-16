"""Mise en page : livret HTML autonome (images intégrées), PDF et image « avant / après »."""

from __future__ import annotations

import base64
import datetime as dt
import io
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image, ImageDraw, ImageFont

from .recit import Section

RACINE = Path(__file__).resolve().parent
OUTIL_PDF = RACINE.parent / "outils" / "html2pdf.mjs"
POLICES = (
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
    "/Library/Fonts/Arial Bold.ttf",
)


def _police(taille: int) -> ImageFont.ImageFont:
    for chemin in POLICES:
        if Path(chemin).exists():
            return ImageFont.truetype(chemin, taille)
    return ImageFont.load_default(size=taille)


def image_en_data_uri(image: Image.Image, qualite: int = 82) -> str:
    tampon = io.BytesIO()
    image.convert("RGB").save(tampon, "JPEG", quality=qualite, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(tampon.getvalue()).decode("ascii")


def paginer(sections: list[Section], images_disponibles: set[str]) -> tuple[Section | None, list[list[Section]]]:
    """Introduction (affichée en couverture) + pages : une page par image, textes regroupés."""
    introduction = next((s for s in sections if s.cle == "introduction"), None)
    pages: list[list[Section]] = []
    for section in sections:
        if section is introduction:
            continue
        illustree = section.image in images_disponibles
        if illustree or not pages or pages[-1][-1].image in images_disponibles:
            pages.append([section])
        else:
            pages[-1].append(section)
    return introduction, pages


def livret_html(
    faits: dict[str, Any],
    sections: list[Section],
    images: dict[str, Image.Image],
    sources: list[str],
    marque: str,
) -> str:
    env = Environment(
        loader=FileSystemLoader(RACINE / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
    )
    gabarit = env.get_template("livret.html.j2")
    commune = (faits.get("commune") or {}).get("nom") or faits["adresse"].get("commune", "")
    couverture = images.get("1950") or images.get("etat-major") or images.get("aujourdhui")
    introduction, pages = paginer(sections, set(images))
    return gabarit.render(
        adresse=faits["adresse"],
        commune=commune,
        introduction=introduction,
        pages=pages,
        images={cle: image_en_data_uri(img) for cle, img in images.items()},
        couverture=image_en_data_uri(couverture) if couverture else None,
        sources=sources,
        avertissements=faits.get("avertissements") or [],
        date=dt.date.today().strftime("%d/%m/%Y"),
        marque=marque,
    )


def avant_apres(
    avant: Image.Image,
    apres: Image.Image,
    titre: str,
    libelle_avant: str,
    libelle_apres: str,
    marque: str,
    cote: int = 800,
) -> Image.Image:
    """Visuel 2 × 1 à partager : seule la commune apparaît (jamais l'adresse exacte)."""
    marge, bandeau_haut, bandeau_bas = 24, 90, 60
    largeur = cote * 2 + marge * 3
    hauteur = bandeau_haut + cote + bandeau_bas
    fond = Image.new("RGB", (largeur, hauteur), (24, 22, 20))
    dessin = ImageDraw.Draw(fond)
    dessin.text((marge, 24), titre, font=_police(40), fill=(245, 240, 230))
    for i, (img, libelle) in enumerate(((avant, libelle_avant), (apres, libelle_apres))):
        x = marge + i * (cote + marge)
        fond.paste(img.convert("RGB").resize((cote, cote)), (x, bandeau_haut))
        police = _police(34)
        boite = dessin.textbbox((0, 0), libelle, font=police)
        dessin.rectangle(
            (x, bandeau_haut, x + boite[2] + 28, bandeau_haut + boite[3] + 20), fill=(24, 22, 20)
        )
        dessin.text((x + 14, bandeau_haut + 8), libelle, font=police, fill=(245, 240, 230))
    dessin.text(
        (marge, bandeau_haut + cote + 16),
        f"{marque} · Sources : IGN (Licence Ouverte)",
        font=_police(22),
        fill=(190, 182, 170),
    )
    return fond


def exporter_pdf(chemin_html: Path, chemin_pdf: Path) -> bool:
    """Convertit le livret en PDF A4 via Playwright/Chromium (Node). Renvoie False si indisponible."""
    if not shutil.which("node") or not OUTIL_PDF.exists():
        return False
    try:
        subprocess.run(
            ["node", str(OUTIL_PDF), str(chemin_html.resolve()), str(chemin_pdf.resolve())],
            check=True,
            capture_output=True,
            timeout=180,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        return False
    return chemin_pdf.exists()
