"""Récit du livret, construit uniquement à partir des faits collectés (aucune invention).

Chaque phrase factuelle est conditionnée à la présence de la donnée correspondante.
Les dates de construction sont présentées comme des estimations (fichiers fonciers).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .cartes import EPOQUES


@dataclass
class Section:
    cle: str
    titre: str
    paragraphes: list[str]
    image: str | None = None  # clé d'époque (voir cartes.EPOQUES)
    legende: str | None = None
    liste: list[dict[str, Any]] = field(default_factory=list)


PERIODES: tuple[tuple[int, str], ...] = (
    (1789, "sous l'Ancien Régime"),
    (1799, "pendant la Révolution française"),
    (1815, "sous le Consulat ou le Premier Empire"),
    (1830, "sous la Restauration"),
    (1848, "sous la monarchie de Juillet"),
    (1852, "sous la IIe République"),
    (1870, "sous le Second Empire, l'époque des grands travaux"),
    (1914, "sous la IIIe République, à la Belle Époque"),
    (1919, "pendant la Première Guerre mondiale"),
    (1939, "dans l'entre-deux-guerres"),
    (1945, "pendant la Seconde Guerre mondiale"),
    (1975, "pendant la Reconstruction et les Trente Glorieuses"),
    (2000, "dans le dernier quart du XXe siècle"),
)


def contexte_annee(annee: int) -> str:
    for borne, libelle in PERIODES:
        if annee < borne:
            return libelle
    return "au XXIe siècle"


def _minuscule(texte: str | None) -> str | None:
    return texte.strip().lower() if texte else None


def _materiaux(batiment: dict[str, Any]) -> str | None:
    murs = _minuscule(batiment.get("mat_mur_txt"))
    toit = _minuscule(batiment.get("mat_toit_txt"))
    morceaux = []
    if murs and murs not in ("autres", "indetermine", "indéterminé", "inconnu"):
        morceaux.append(f"des murs en {murs}")
    if toit and toit not in ("autres", "indetermine", "indéterminé", "inconnu"):
        morceaux.append(f"un toit en {toit}")
    if not morceaux:
        return None
    return " et ".join(morceaux)


def _pluriel(n: Any, singulier: str, pluriel: str) -> str | None:
    try:
        valeur = int(n)
    except (TypeError, ValueError):
        return None
    if valeur <= 0:
        return None
    return f"{valeur} {singulier if valeur == 1 else pluriel}"


def _nombre(n: Any) -> str:
    try:
        return f"{int(n):,}".replace(",", " ")
    except (TypeError, ValueError):
        return str(n)


def _annee_batiment(batiment: dict[str, Any] | None) -> tuple[int | None, str | None]:
    """(année, nature) — nature : 'construction' (fichiers fonciers) ou 'apparition' (BD TOPO)."""
    if not batiment:
        return None, None
    for cle, nature in (("annee_construction", "construction"), ("annee_apparition", "apparition")):
        valeur = batiment.get(cle)
        if isinstance(valeur, int) and 1000 < valeur <= 2100:
            return valeur, nature
    return None, None


def construire(faits: dict[str, Any], images_disponibles: set[str]) -> list[Section]:
    adresse = faits["adresse"]
    commune = faits.get("commune") or {}
    nom_commune = commune.get("nom") or adresse.get("commune") or "votre commune"
    batiment = faits.get("batiment")
    annee, nature_annee = _annee_batiment(batiment)
    sections: list[Section] = []

    # --- Introduction
    intro = [
        f"Ce livret retrace l'histoire du lieu où se trouve le {adresse['label']}, "
        "à travers les grandes cartes et photographies aériennes conservées par l'État."
    ]
    if annee and nature_annee == "construction":
        intro.append(
            f"D'après les fichiers fonciers, le bâtiment aurait été construit vers {annee}, "
            f"{contexte_annee(annee)}."
        )
    intro.append(
        "Sur chaque carte, le cercle rouge marque l'emplacement de l'adresse."
    )
    sections.append(Section("introduction", "Votre adresse à travers le temps", intro))

    # --- Cassini
    if "cassini" in images_disponibles:
        texte = [
            "Levée entre 1756 et 1815 par quatre générations de la famille Cassini, "
            "cette carte est la première représentation à la fois générale et détaillée "
            "du royaume de France.",
            "On y distingue les villages, les églises, les routes, les moulins et les bois. "
            "Les maisons individuelles n'y figurent pas : c'est le paysage dans lequel "
            "votre adresse allait naître.",
        ]
        if annee and annee < 1760:
            texte.append(
                f"Si l'estimation de {annee} est exacte, votre bâtiment existait déjà "
                "lorsque les ingénieurs de Cassini ont parcouru la région."
            )
        sections.append(Section("cassini", "Vers 1760 : la France de Cassini", texte, image="cassini"))

    # --- État-major
    if "etat-major" in images_disponibles:
        texte = [
            "Entre 1820 et 1866, les officiers de l'état-major ont cartographié toute la "
            "France au 1:40 000. Ces minutes colorisées montrent le bâti en rouge, les "
            "prés en vert et les vignes en violet.",
        ]
        if annee and nature_annee == "construction":
            if annee < 1820:
                texte.append(
                    f"Construit vers {annee}, votre bâtiment existait sans doute déjà lorsque "
                    "la carte de votre secteur a été levée."
                )
            elif annee <= 1866:
                texte.append(
                    f"Votre bâtiment, daté des environs de {annee}, a été construit à l'époque "
                    "même où cette carte était dressée : selon l'année du levé de votre secteur, "
                    "il peut y figurer ou non."
                )
            else:
                texte.append(
                    "À cette époque, votre maison n'était pas encore construite : "
                    "observez ce qui occupait alors son emplacement."
                )
        sections.append(Section("etat-major", "1820-1866 : la carte d'état-major", texte, image="etat-major"))

    # --- 1950
    if "1950" in images_disponibles:
        texte = [
            "Dans les années 1950-1960, l'IGN photographie systématiquement le territoire "
            "depuis le ciel. Ces clichés en noir et blanc sont le premier regard « vu d'avion » "
            "sur votre quartier."
        ]
        if annee and nature_annee == "construction":
            if annee < 1950:
                texte.append(
                    f"Bâtie vers {annee}, votre maison devrait être visible au centre de la photographie."
                )
            elif annee <= 1965:
                texte.append(
                    f"Votre maison date des environs de {annee}, la période même de ces prises de vue : "
                    "selon la date du cliché, vous verrez peut-être le terrain encore libre."
                )
            else:
                texte.append(
                    f"Votre maison, construite vers {annee}, n'existait pas encore : "
                    "comparez avec la photographie d'aujourd'hui."
                )
        sections.append(Section("1950", "1950-1965 : le premier regard du ciel", texte, image="1950"))

    for cle, titre, texte in (
        ("1965", "1965-1980 : une génération plus tard",
         "Une nouvelle campagne de photographies aériennes, une génération après la précédente : "
         "comparez les deux clichés pour repérer ce qui a changé autour de votre adresse."),
        ("2000", "2000-2005 : au tournant du siècle",
         "Au début des années 2000, l'IGN constitue la BD ORTHO®, une couverture de la France "
         "en photographies aériennes couleur."),
    ):
        if cle in images_disponibles:
            sections.append(Section(cle, titre, [texte], image=cle))

    # --- Le bâtiment
    paragraphe_bat: list[str] = []
    if batiment:
        if annee and nature_annee == "construction":
            paragraphe_bat.append(
                f"Année de construction estimée : vers {annee} ({contexte_annee(annee)}). "
                "Cette date provient des fichiers fonciers et reste indicative."
            )
        elif annee and nature_annee == "apparition":
            paragraphe_bat.append(
                f"Le bâtiment apparaît dans les bases de l'IGN en {annee} ; "
                "il peut être bien plus ancien."
            )
        materiaux = _materiaux(batiment)
        if materiaux:
            paragraphe_bat.append(f"Le bâtiment présente {materiaux}.")
        details = [
            _pluriel(batiment.get("nb_niveau"), "niveau", "niveaux"),
            _pluriel(batiment.get("nb_log"), "logement", "logements"),
        ]
        details = [d for d in details if d]
        if details:
            paragraphe_bat.append("Il compte " + " et ".join(details) + ".")
        if batiment.get("hauteur_mean"):
            paragraphe_bat.append(
                f"Sa hauteur moyenne est d'environ {round(float(batiment['hauteur_mean']))} m."
            )
    parcelle = faits.get("parcelle")
    if parcelle and parcelle.get("section") and parcelle.get("numero"):
        surface = parcelle.get("contenance_m2")
        paragraphe_bat.append(
            f"Au cadastre, l'adresse correspond à la parcelle {parcelle['section']} "
            f"{parcelle['numero']}" + (f" ({_nombre(surface)} m²)." if surface else ".")
        )
    if paragraphe_bat:
        sections.append(Section("batiment", "Le bâtiment", paragraphe_bat))

    # --- Aujourd'hui
    if "aujourdhui" in images_disponibles:
        sections.append(
            Section(
                "aujourdhui",
                "Aujourd'hui",
                ["La photographie aérienne la plus récente de l'IGN, à la même échelle que celle "
                 "des années 1950 : comparez les deux pour mesurer le chemin parcouru."],
                image="aujourdhui",
            )
        )

    # --- La commune
    paragraphes_commune: list[str] = []
    if commune.get("population"):
        lieu = f"{nom_commune}"
        if commune.get("departement"):
            lieu += f" ({commune['departement']}"
            lieu += f", {commune['region']})" if commune.get("region") else ")"
        paragraphes_commune.append(f"{lieu} compte aujourd'hui {_nombre(commune['population'])} habitants.")
    wiki = faits.get("wikipedia_commune")
    if wiki and wiki.get("extrait"):
        paragraphes_commune.append(wiki["extrait"])
    if paragraphes_commune:
        sections.append(Section("commune", f"{nom_commune}", paragraphes_commune))
    for cle, titre in (("toponymie", "D'où vient le nom"), ("histoire", f"L'histoire de {nom_commune}")):
        if wiki and wiki.get(cle):
            sections.append(
                Section(f"commune-{cle}", titre, [p for p in wiki[cle].split("\n") if p.strip()])
            )

    # --- Alentours
    alentours = faits.get("alentours") or []
    if alentours:
        sections.append(
            Section(
                "alentours",
                "Autour de chez vous",
                ["Lieux documentés sur Wikipédia à proximité de votre adresse :"],
                liste=alentours,
            )
        )

    # Ordre de lecture : les époques illustrées d'abord, puis les rubriques texte regroupées.
    ordre = ["introduction", "cassini", "etat-major", "1950", "1965", "2000", "aujourdhui", "batiment",
             "commune", "commune-toponymie", "commune-histoire", "alentours"]
    sections.sort(key=lambda s: ordre.index(s.cle) if s.cle in ordre else len(ordre))

    # Légendes des images
    par_cle = {e.cle: e for e in EPOQUES}
    for section in sections:
        if section.image in par_cle:
            section.legende = f"{par_cle[section.image].periode} — {par_cle[section.image].source}"
    return sections


def sources_et_licences(faits: dict[str, Any], images_disponibles: set[str]) -> list[str]:
    lignes = [e.source + " — Licence Ouverte Etalab" for e in EPOQUES if e.cle in images_disponibles]
    lignes.append("Adresse : Base Adresse Nationale / Géoplateforme IGN — Licence Ouverte Etalab")
    if faits.get("parcelle"):
        lignes.append("Cadastre : DGFiP via API Carto IGN — Licence Ouverte Etalab")
    bat = faits.get("batiment") or {}
    if bat.get("source", "").startswith("BDNB"):
        lignes.append(
            "Bâtiment : Base de Données Nationale des Bâtiments (BDNB), CSTB — Licence Ouverte Etalab 2.0 ; "
            "valeurs estimées"
        )
    elif bat.get("source"):
        lignes.append(f"Bâtiment : {bat['source']} — Licence Ouverte Etalab ; valeurs estimées")
    if faits.get("commune"):
        lignes.append("Commune : API Découpage administratif (geo.api.gouv.fr) — Licence Ouverte Etalab")
    if faits.get("wikipedia_commune") or faits.get("alentours"):
        # CC BY-SA 4.0 : citer les articles et les auteurs, la licence (lien), et signaler les modifications.
        urls = [a["url"] for a in [faits.get("wikipedia_commune") or {}, *(faits.get("alentours") or [])] if a.get("url")]
        lignes.append(
            "Textes : © contributeurs de Wikipédia, licence CC BY-SA 4.0 "
            "(https://creativecommons.org/licenses/by-sa/4.0/deed.fr) ; extraits éventuellement abrégés."
            + (" Articles : " + " ; ".join(urls) if urls else "")
        )
    return lignes
