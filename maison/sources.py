"""Collecte des faits sur une adresse à partir de sources publiques ouvertes.

Chaque fonction est tolérante : si une source ne répond pas, elle renvoie
``None`` (ou une liste vide) et le livret est produit sans cette rubrique.
Rien n'est inventé : le récit ne s'appuie que sur ce qui est collecté ici.
"""

from __future__ import annotations

import json
import math
import re
import urllib.parse
from dataclasses import asdict, dataclass, field
from typing import Any

from . import http

GEOCODAGE_IGN = "https://data.geopf.fr/geocodage/search"
GEOCODAGE_BAN = "https://api-adresse.data.gouv.fr/search/"
CADASTRE = "https://apicarto.ign.fr/api/cadastre/parcelle"
BDNB = "https://api.bdnb.io/v1/bdnb/donnees"
BDTOPO_WFS = "https://data.geopf.fr/wfs/ows"
GEO_API = "https://geo.api.gouv.fr/communes"
WIKI_REST = "https://fr.wikipedia.org/api/rest_v1/page/summary/"
WIKI_API = "https://fr.wikipedia.org/w/api.php"


class AdresseIntrouvable(Exception):
    pass


@dataclass
class Adresse:
    label: str
    commune: str
    code_insee: str
    code_postal: str
    lon: float
    lat: float
    cle_ban: str | None = None
    voie: str | None = None
    numero: str | None = None
    score: float = 0.0
    type: str = ""


@dataclass
class Faits:
    adresse: Adresse
    parcelle: dict[str, Any] | None = None
    batiment: dict[str, Any] | None = None
    commune: dict[str, Any] | None = None
    wikipedia_commune: dict[str, Any] | None = None
    alentours: list[dict[str, Any]] = field(default_factory=list)
    avertissements: list[str] = field(default_factory=list)

    def en_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------- géocodage


def _adresse_depuis_feature(feature: dict[str, Any]) -> Adresse:
    p = feature["properties"]
    lon, lat = feature["geometry"]["coordinates"]
    return Adresse(
        label=p.get("label", ""),
        commune=p.get("city", ""),
        code_insee=p.get("citycode", ""),
        code_postal=p.get("postcode", ""),
        lon=float(lon),
        lat=float(lat),
        cle_ban=p.get("id"),
        voie=p.get("street") or p.get("name"),
        numero=p.get("housenumber"),
        score=float(p.get("score", 0)),
        type=p.get("type", ""),
    )


def geocoder(texte: str, score_min: float = 0.4) -> Adresse:
    """Géocode une adresse française (Géoplateforme IGN, repli sur l'API Adresse)."""
    dernier_probleme = "aucun résultat"
    for url in (GEOCODAGE_IGN, GEOCODAGE_BAN):
        try:
            data = http.get_json(url, {"q": texte, "limit": 1})
        except http.ErreurHTTP as e:
            dernier_probleme = str(e)
            continue
        features = data.get("features") or []
        if features and float(features[0]["properties"].get("score", 0)) >= score_min:
            return _adresse_depuis_feature(features[0])
    raise AdresseIntrouvable(f"Adresse introuvable : {texte!r} ({dernier_probleme})")


# ---------------------------------------------------------------- géométrie


def _metres_par_degre(lat: float) -> tuple[float, float]:
    return 111_320 * math.cos(math.radians(lat)), 110_574


def _distance_point_segment(px, py, ax, ay, bx, by) -> float:
    dx, dy = bx - ax, by - ay
    if dx == dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _point_dans_anneau(px, py, anneau) -> bool:
    dedans = False
    j = len(anneau) - 1
    for i in range(len(anneau)):
        xi, yi = anneau[i][0], anneau[i][1]
        xj, yj = anneau[j][0], anneau[j][1]
        if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
            dedans = not dedans
        j = i
    return dedans


def distance_point_geometrie(lon: float, lat: float, geometrie: dict[str, Any]) -> float:
    """Distance approximative en mètres entre un point et un (Multi)Polygon GeoJSON (0 si dedans)."""
    mx, my = _metres_par_degre(lat)
    polygones = geometrie["coordinates"]
    if geometrie["type"] == "Polygon":
        polygones = [polygones]
    meilleure = math.inf
    for polygone in polygones:
        exterieur = polygone[0]
        if _point_dans_anneau(lon, lat, exterieur):
            return 0.0
        for (ax, ay), (bx, by) in zip(exterieur, exterieur[1:]):
            d = _distance_point_segment(
                lon * mx, lat * my, ax * mx, ay * my, bx * mx, by * my
            )
            meilleure = min(meilleure, d)
    return meilleure


def carre_autour(lon: float, lat: float, demi_cote_m: float) -> dict[str, Any]:
    mx, my = _metres_par_degre(lat)
    dlon, dlat = demi_cote_m / mx, demi_cote_m / my
    anneau = [
        [lon - dlon, lat - dlat],
        [lon + dlon, lat - dlat],
        [lon + dlon, lat + dlat],
        [lon - dlon, lat + dlat],
        [lon - dlon, lat - dlat],
    ]
    return {"type": "Polygon", "coordinates": [anneau]}


# ---------------------------------------------------------------- cadastre


def parcelle(lon: float, lat: float) -> dict[str, Any] | None:
    """Parcelle cadastrale contenant le point, sinon la plus proche dans un rayon de ~15 m."""
    for geom in (
        {"type": "Point", "coordinates": [lon, lat]},
        carre_autour(lon, lat, 15),
    ):
        try:
            data = http.get_json(CADASTRE, {"geom": json.dumps(geom)})
        except http.ErreurHTTP:
            return None
        features = data.get("features") or []
        if not features:
            continue
        meilleure = min(
            features, key=lambda f: distance_point_geometrie(lon, lat, f["geometry"])
        )
        p = meilleure["properties"]
        return {
            "section": p.get("section"),
            "numero": p.get("numero"),
            "contenance_m2": p.get("contenance"),
            "idu": p.get("idu"),
        }
    return None


# ---------------------------------------------------------------- bâtiment

_CHAMPS_BDNB = (
    "annee_construction",
    "mat_mur_txt",
    "mat_toit_txt",
    "nb_niveau",
    "nb_log",
    "hauteur_mean",
    "surface_emprise_sol",
    "usage_niveau_1_txt",
)


def batiment_bdnb(cle_ban: str | None) -> dict[str, Any] | None:
    """Caractéristiques du bâtiment via la BDNB (CSTB), à partir de la clé d'adresse BAN."""
    if not cle_ban:
        return None
    try:
        liens = http.get_json(
            f"{BDNB}/rel_batiment_groupe_adresse",
            {"cle_interop_adr": f"eq.{cle_ban}", "limit": 1},
        )
        if not liens:
            return None
        groupe = liens[0]["batiment_groupe_id"]
        lignes = http.get_json(
            f"{BDNB}/batiment_groupe_complet",
            {"batiment_groupe_id": f"eq.{groupe}", "select": ",".join(_CHAMPS_BDNB)},
        )
    except (http.ErreurHTTP, KeyError, ValueError):
        return None
    if not lignes:
        return None
    brut = lignes[0]
    resultat = {k: brut.get(k) for k in _CHAMPS_BDNB if brut.get(k) not in (None, "")}
    if not resultat:
        return None
    resultat["source"] = "BDNB (CSTB)"
    return resultat


def batiment_bdtopo(lon: float, lat: float) -> dict[str, Any] | None:
    """Repli : bâtiment BD TOPO® le plus proche (IGN)."""
    mx, my = _metres_par_degre(lat)
    d = 25
    bbox = f"{lat - d / my},{lon - d / mx},{lat + d / my},{lon + d / mx},urn:ogc:def:crs:EPSG::4326"
    try:
        data = http.get_json(
            BDTOPO_WFS,
            {
                "SERVICE": "WFS",
                "VERSION": "2.0.0",
                "REQUEST": "GetFeature",
                "TYPENAMES": "BDTOPO_V3:batiment",
                "OUTPUTFORMAT": "application/json",
                "SRSNAME": "EPSG:4326",
                "BBOX": bbox,
                "COUNT": 30,
            },
        )
    except http.ErreurHTTP:
        return None
    features = [f for f in data.get("features") or [] if f.get("geometry")]
    if not features:
        return None
    f = min(features, key=lambda f: distance_point_geometrie(lon, lat, _premier_polygone(f["geometry"])))
    p = f["properties"]
    resultat: dict[str, Any] = {}
    apparition = p.get("date_d_apparition")
    if apparition and str(apparition)[:4].isdigit():
        resultat["annee_apparition"] = int(str(apparition)[:4])
    for source, cible in (
        ("nombre_d_etages", "nb_niveau"),
        ("nombre_de_logements", "nb_log"),
        ("hauteur", "hauteur_mean"),
        ("usage_1", "usage_niveau_1_txt"),
    ):
        if p.get(source) not in (None, ""):
            resultat[cible] = p[source]
    if not resultat:
        return None
    resultat["source"] = "BD TOPO® (IGN)"
    return resultat


def _premier_polygone(geometrie: dict[str, Any]) -> dict[str, Any]:
    if geometrie["type"] == "MultiPolygon":
        return {"type": "Polygon", "coordinates": geometrie["coordinates"][0]}
    return geometrie


# ---------------------------------------------------------------- commune


def commune(code_insee: str) -> dict[str, Any] | None:
    try:
        data = http.get_json(
            f"{GEO_API}/{code_insee}",
            {"fields": "nom,code,population,surface,departement,region"},
        )
    except http.ErreurHTTP:
        return None
    return {
        "nom": data.get("nom"),
        "population": data.get("population"),
        "surface_ha": data.get("surface"),
        "departement": (data.get("departement") or {}).get("nom"),
        "region": (data.get("region") or {}).get("nom"),
    }


def _distance_km(lat1, lon1, lat2, lon2) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def wikipedia_commune(nom: str, departement: str | None, lat: float, lon: float) -> dict[str, Any] | None:
    """Résumé Wikipédia de la commune, en vérifiant qu'il s'agit bien de la bonne (≤ 40 km)."""
    candidats = [nom]
    if departement:
        candidats.append(f"{nom} ({departement})")
    for titre in candidats:
        try:
            data = http.get_json(WIKI_REST + urllib.parse.quote(titre.replace(" ", "_")))
        except http.ErreurHTTP:
            continue
        if data.get("type") != "standard" or not data.get("extract"):
            continue
        coords = data.get("coordinates")
        if coords and _distance_km(lat, lon, coords["lat"], coords["lon"]) > 40:
            continue
        resultat = {
            "titre": data.get("title"),
            "description": data.get("description"),
            "extrait": data["extract"],
            "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
        }
        resultat.update(wikipedia_sections(data.get("title") or titre))
        return resultat
    return None


def extraire_section(texte: str, titre: str, max_car: int) -> str | None:
    """Texte d'une section de niveau 2 (« == Titre == »), sous-titres retirés, coupé proprement."""
    motif = re.compile(rf"^==\s*{re.escape(titre)}\s*==\s*$", re.M)
    debut = motif.search(texte)
    if not debut:
        return None
    suite = texte[debut.end():]
    fin = re.search(r"^==\s*[^=].*?==\s*$", suite, re.M)
    corps = suite[: fin.start()] if fin else suite
    paragraphes = [
        ligne.strip()
        for ligne in corps.splitlines()
        if ligne.strip() and not ligne.strip().startswith("=")
    ]
    retenus: list[str] = []
    total = 0
    for paragraphe in paragraphes:
        if total + len(paragraphe) > max_car:
            reste = max_car - total
            if reste > 200:
                coupe = paragraphe[:reste]
                point = coupe.rfind(". ")
                if point > 100:
                    retenus.append(coupe[: point + 1])
            break
        retenus.append(paragraphe)
        total += len(paragraphe)
    return "\n".join(retenus) or None


def wikipedia_sections(titre: str) -> dict[str, str]:
    """Sections « Toponymie » et « Histoire » de l'article (texte brut, CC BY-SA)."""
    try:
        data = http.get_json(
            WIKI_API,
            {
                "action": "query",
                "prop": "extracts",
                "explaintext": 1,
                "exsectionformat": "wiki",
                "redirects": 1,
                "titles": titre,
                "format": "json",
            },
        )
    except http.ErreurHTTP:
        return {}
    pages = data.get("query", {}).get("pages", {})
    texte = next(iter(pages.values()), {}).get("extract", "") if pages else ""
    sections = {}
    for cle, nom, limite in (("toponymie", "Toponymie", 700), ("histoire", "Histoire", 1600)):
        extrait = extraire_section(texte, nom, limite)
        if extrait:
            sections[cle] = extrait
    return sections


# Articles d'entités administratives, souvent géolocalisés sur un chef-lieu : hors sujet ici.
PREFIXES_EXCLUS = (
    "Diocèse", "Archidiocèse", "Arrondissement", "Canton", "Circonscription",
    "Communauté d'agglomération", "Communauté de communes", "Communauté urbaine",
    "Métropole", "Liste ", "Département", "Région", "Pays ",
)


def wikipedia_alentours(lat: float, lon: float, rayon_m: int = 1000, limite: int = 8, exclure: set[str] | None = None) -> list[dict[str, Any]]:
    """Lieux documentés sur Wikipédia autour de l'adresse (distance croissante)."""
    exclure = exclure or set()
    try:
        data = http.get_json(
            WIKI_API,
            {
                "action": "query",
                "list": "geosearch",
                "gscoord": f"{lat}|{lon}",
                "gsradius": rayon_m,
                "gslimit": 25,
                "format": "json",
            },
        )
    except http.ErreurHTTP:
        return []
    lieux = [
        {"titre": g["title"], "distance_m": round(g["dist"])}
        for g in data.get("query", {}).get("geosearch", [])
        if g["title"] not in exclure and not g["title"].startswith(PREFIXES_EXCLUS)
    ][:limite]
    if not lieux:
        return []
    try:
        desc = http.get_json(
            WIKI_API,
            {
                "action": "query",
                "prop": "description",
                "titles": "|".join(l["titre"] for l in lieux),
                "format": "json",
            },
        )
        par_titre = {
            p.get("title"): p.get("description")
            for p in desc.get("query", {}).get("pages", {}).values()
        }
    except http.ErreurHTTP:
        par_titre = {}
    for lieu in lieux:
        lieu["description"] = par_titre.get(lieu["titre"])
        lieu["url"] = "https://fr.wikipedia.org/wiki/" + urllib.parse.quote(lieu["titre"].replace(" ", "_"))
    return lieux


# ---------------------------------------------------------------- orchestration


def collecter(texte_adresse: str) -> Faits:
    adresse = geocoder(texte_adresse)
    faits = Faits(adresse=adresse)
    if adresse.type not in ("housenumber", ""):
        faits.avertissements.append(
            "Adresse localisée sans numéro précis : la position est approximative."
        )

    faits.parcelle = parcelle(adresse.lon, adresse.lat)
    faits.batiment = batiment_bdnb(adresse.cle_ban) or batiment_bdtopo(adresse.lon, adresse.lat)
    faits.commune = commune(adresse.code_insee) if adresse.code_insee else None

    nom = (faits.commune or {}).get("nom") or adresse.commune
    if nom:
        faits.wikipedia_commune = wikipedia_commune(
            nom, (faits.commune or {}).get("departement"), adresse.lat, adresse.lon
        )
    exclure = {nom} | ({faits.wikipedia_commune["titre"]} if faits.wikipedia_commune else set())
    faits.alentours = wikipedia_alentours(adresse.lat, adresse.lon, exclure=exclure)

    for cle, libelle in (
        ("parcelle", "parcelle cadastrale"),
        ("batiment", "caractéristiques du bâtiment"),
        ("wikipedia_commune", "histoire de la commune (Wikipédia)"),
    ):
        if getattr(faits, cle) is None:
            faits.avertissements.append(f"Donnée indisponible : {libelle}.")
    return faits
