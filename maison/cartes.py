"""Cartes anciennes et photographies aériennes de l'IGN (Géoplateforme, service WMS).

Licences vérifiées dans les métadonnées officielles (data.geopf.fr/csw) :
- Cassini (Archives nationales & IGN), SCAN État-major 40K, BD ORTHO® Historique et
  BD ORTHO® : Licence Ouverte Etalab — réutilisation commerciale autorisée avec mention
  de la source.
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass

from PIL import Image, ImageDraw, ImageStat

from . import http

WMS = "https://data.geopf.fr/wms-r/wms"
RAYON_TERRE_MERCATOR = 20037508.34


@dataclass(frozen=True)
class Epoque:
    cle: str
    periode: str
    titre: str
    couche: str
    demi_cote_m: float  # demi-largeur au sol de l'image, en mètres
    source: str
    format: str = "image/png"


EPOQUES: tuple[Epoque, ...] = (
    Epoque(
        "cassini",
        "Vers 1760",
        "La carte de Cassini",
        "AN-IGNF_GEOGRAPHICALGRIDSYSTEMS.CASSINI",
        1800,
        "Carte de France de Cassini reconstituée, Archives nationales et IGN "
        "(planches originales : Archives nationales, E/III/20)",
        "image/jpeg",
    ),
    Epoque(
        "etat-major",
        "1820-1866",
        "La carte d'état-major",
        "GEOGRAPHICALGRIDSYSTEMS.ETATMAJOR40",
        700,
        "IGN – Carte de l'état-major 1:40 000 (SCAN EM 40K)",
        "image/jpeg",
    ),
    Epoque(
        "1950",
        "1950-1965",
        "La première photographie aérienne",
        "ORTHOIMAGERY.ORTHOPHOTOS.1950-1965",
        220,
        "IGN – BD ORTHO® Historique 1950-1965",
    ),
    Epoque(
        "1965",
        "1965-1980",
        "Les années 1970",
        "ORTHOIMAGERY.ORTHOPHOTOS.1965-1980",
        220,
        "IGN – BD ORTHO® Historique 1965-1980",
    ),
    Epoque(
        "2000",
        "2000-2005",
        "Au tournant du siècle",
        "ORTHOIMAGERY.ORTHOPHOTOS2000-2005",
        220,
        "IGN – Photographies aériennes 2000-2005",
        "image/jpeg",
    ),
    Epoque(
        "aujourdhui",
        "Aujourd'hui",
        "Votre maison aujourd'hui",
        "ORTHOIMAGERY.ORTHOPHOTOS",
        220,
        "IGN – BD ORTHO®",
        "image/jpeg",
    ),
)


def vers_mercator(lon: float, lat: float) -> tuple[float, float]:
    x = lon * RAYON_TERRE_MERCATOR / 180
    y = math.log(math.tan((90 + lat) * math.pi / 360)) * RAYON_TERRE_MERCATOR / math.pi
    return x, y


def bbox_mercator(lon: float, lat: float, demi_cote_sol_m: float) -> tuple[float, float, float, float]:
    """Emprise EPSG:3857 couvrant ``demi_cote_sol_m`` mètres au sol autour du point.

    En Web Mercator, un mètre au sol vaut 1/cos(lat) unités : on corrige pour que
    l'image couvre réellement la distance voulue.
    """
    x, y = vers_mercator(lon, lat)
    d = demi_cote_sol_m / math.cos(math.radians(lat))
    return x - d, y - d, x + d, y + d


def est_vide(image: Image.Image, seuil_ecart_type: float = 4.0) -> bool:
    """Vrai si l'image est (presque) vide : transparente ou quasi uniforme (zone non couverte)."""
    if image.mode in ("RGBA", "LA"):
        alpha = image.getchannel("A")
        couverts = sum(alpha.point(lambda a: 255 if a > 10 else 0).histogram()[255:])
        if couverts < 0.6 * image.width * image.height:
            return True
    gris = image.convert("L")
    return ImageStat.Stat(gris).stddev[0] < seuil_ecart_type


def marquer_centre(image: Image.Image, couleur=(220, 30, 30)) -> Image.Image:
    """Dessine un cercle au centre (emplacement de l'adresse)."""
    img = image.convert("RGB")
    trait = ImageDraw.Draw(img)
    cx, cy = img.width / 2, img.height / 2
    r = max(10, img.width // 45)
    epaisseur = max(3, img.width // 250)
    trait.ellipse((cx - r, cy - r, cx + r, cy + r), outline=couleur, width=epaisseur)
    trait.ellipse((cx - 3, cy - 3, cx + 3, cy + 3), fill=couleur)
    return img


def telecharger(epoque: Epoque, lon: float, lat: float, pixels: int = 1000) -> Image.Image | None:
    """Image de l'époque centrée sur le point, ou None si indisponible/non couverte."""
    minx, miny, maxx, maxy = bbox_mercator(lon, lat, epoque.demi_cote_m)
    params = {
        "SERVICE": "WMS",
        "VERSION": "1.3.0",
        "REQUEST": "GetMap",
        "LAYERS": epoque.couche,
        "STYLES": "",
        "CRS": "EPSG:3857",
        "BBOX": f"{minx},{miny},{maxx},{maxy}",
        "WIDTH": pixels,
        "HEIGHT": pixels,
        "FORMAT": epoque.format,
    }
    try:
        contenu, type_contenu = http.get(WMS, params, timeout=90)
    except http.ErreurHTTP:
        return None
    if not type_contenu.startswith("image/"):
        return None
    try:
        image = Image.open(io.BytesIO(contenu))
        image.load()
    except OSError:
        return None
    if est_vide(image):
        return None
    return marquer_centre(image)


def toutes_les_epoques(lon: float, lat: float, pixels: int = 1000) -> dict[str, Image.Image]:
    images: dict[str, Image.Image] = {}
    for epoque in EPOQUES:
        image = telecharger(epoque, lon, lat, pixels)
        if image is not None:
            images[epoque.cle] = image
    return images
