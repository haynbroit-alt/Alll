"""Tests hors ligne (aucun appel réseau) : python -m unittest discover -s tests."""

from __future__ import annotations

import math
import unittest
from unittest import mock

from PIL import Image, ImageDraw

from maison import cartes, recit, rendu, sources


def faits_exemple(**surcharges):
    faits = {
        "adresse": {
            "label": "8 Rue de l'Exemple 80000 Amiens",
            "commune": "Amiens",
            "code_insee": "80021",
            "code_postal": "80000",
            "lon": 2.29,
            "lat": 49.89,
            "cle_ban": "80021_0000_00008",
            "voie": "Rue de l'Exemple",
            "numero": "8",
            "score": 0.9,
            "type": "housenumber",
        },
        "parcelle": {"section": "VA", "numero": "0066", "contenance_m2": 173, "idu": "x"},
        "batiment": {
            "annee_construction": 1850,
            "mat_mur_txt": "BRIQUES",
            "mat_toit_txt": "ARDOISES",
            "nb_niveau": 3,
            "nb_log": 1,
            "hauteur_mean": 7,
            "source": "BDNB (CSTB)",
        },
        "commune": {"nom": "Amiens", "population": 136449, "departement": "Somme", "region": "Hauts-de-France"},
        "wikipedia_commune": {
            "titre": "Amiens",
            "extrait": "Amiens est une commune française.",
            "histoire": "Premier paragraphe.\nSecond paragraphe.",
            "toponymie": "Le nom vient de…",
        },
        "alentours": [{"titre": "Beffroi d'Amiens", "distance_m": 120, "description": "beffroi", "url": "u"}],
        "avertissements": [],
    }
    faits.update(surcharges)
    return faits


TOUTES = {e.cle for e in cartes.EPOQUES}


class TestCartes(unittest.TestCase):
    def test_bbox_couvre_la_distance_au_sol(self):
        minx, miny, maxx, maxy = cartes.bbox_mercator(2.29, 49.89, 200)
        largeur_mercator = maxx - minx
        self.assertAlmostEqual(largeur_mercator * math.cos(math.radians(49.89)), 400, delta=0.5)
        self.assertAlmostEqual(maxx - minx, maxy - miny)

    def test_image_uniforme_est_vide(self):
        self.assertTrue(cartes.est_vide(Image.new("RGB", (100, 100), (255, 255, 255))))

    def test_image_transparente_est_vide(self):
        self.assertTrue(cartes.est_vide(Image.new("RGBA", (100, 100), (0, 0, 0, 0))))

    def test_image_contrastee_non_vide(self):
        img = Image.new("RGB", (100, 100), "white")
        ImageDraw.Draw(img).rectangle((0, 0, 50, 100), fill="black")
        self.assertFalse(cartes.est_vide(img))

    def test_marquer_centre_dessine_en_rouge(self):
        img = cartes.marquer_centre(Image.new("RGB", (200, 200), "white"))
        self.assertEqual(img.getpixel((100, 100))[0], 220)


class TestGeometrie(unittest.TestCase):
    carre = {"type": "Polygon", "coordinates": [[[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001], [0, 0]]]}

    def test_point_dedans(self):
        self.assertEqual(sources.distance_point_geometrie(0.0005, 0.0005, self.carre), 0.0)

    def test_point_dehors(self):
        d = sources.distance_point_geometrie(0.0015, 0.0005, self.carre)
        self.assertAlmostEqual(d, 55.66, delta=1)

    def test_multipolygone(self):
        multi = {"type": "MultiPolygon", "coordinates": [self.carre["coordinates"]]}
        self.assertEqual(sources.distance_point_geometrie(0.0005, 0.0005, multi), 0.0)

    def test_coordonnees_3d_bdtopo(self):
        # Régression (commande réelle, place du Capitole à Toulouse) : la BD TOPO® renvoie (x, y, z).
        carre_3d = {"type": "Polygon", "coordinates": [[[x, y, 146.2] for x, y in self.carre["coordinates"][0]]]}
        d = sources.distance_point_geometrie(0.0015, 0.0005, carre_3d)
        self.assertAlmostEqual(d, 55.66, delta=1)


class TestGeocodage(unittest.TestCase):
    reponse = {
        "features": [
            {
                "geometry": {"coordinates": [2.29, 49.89]},
                "properties": {
                    "label": "8 Boulevard du Port 80000 Amiens",
                    "city": "Amiens",
                    "citycode": "80021",
                    "postcode": "80000",
                    "id": "80021_6590_00008",
                    "street": "Boulevard du Port",
                    "housenumber": "8",
                    "score": 0.9,
                    "type": "housenumber",
                },
            }
        ]
    }

    def test_geocoder(self):
        with mock.patch.object(sources.http, "get_json", return_value=self.reponse):
            adresse = sources.geocoder("8 bd du port amiens")
        self.assertEqual(adresse.code_insee, "80021")
        self.assertEqual(adresse.cle_ban, "80021_6590_00008")

    def test_score_trop_faible(self):
        faible = {"features": [dict(self.reponse["features"][0], properties={**self.reponse["features"][0]["properties"], "score": 0.1})]}
        with mock.patch.object(sources.http, "get_json", return_value=faible):
            with self.assertRaises(sources.AdresseIntrouvable):
                sources.geocoder("n'importe quoi")


class TestWikipedia(unittest.TestCase):
    texte = (
        "Intro.\n\n== Toponymie ==\nLe nom vient du latin.\n\n"
        "== Histoire ==\n=== Antiquité ===\nPhrase une. Phrase deux.\n\n=== Moyen Âge ===\nTrois.\n\n"
        "== Économie ==\nRien.\n"
    )

    def test_extraire_section(self):
        histoire = sources.extraire_section(self.texte, "Histoire", 1000)
        self.assertEqual(histoire, "Phrase une. Phrase deux.\nTrois.")
        self.assertNotIn("Rien", histoire)

    def test_section_absente(self):
        self.assertIsNone(sources.extraire_section(self.texte, "Géographie", 1000))

    def test_alentours_exclut_les_entites_administratives(self):
        geo = {"query": {"geosearch": [
            {"title": "Diocèse d'Arras", "dist": 31},
            {"title": "Beffroi d'Amiens", "dist": 120},
        ]}}
        desc = {"query": {"pages": {"1": {"title": "Beffroi d'Amiens", "description": "beffroi"}}}}
        with mock.patch.object(sources.http, "get_json", side_effect=[geo, desc]):
            lieux = sources.wikipedia_alentours(49.89, 2.29)
        self.assertEqual([l["titre"] for l in lieux], ["Beffroi d'Amiens"])


class TestRecit(unittest.TestCase):
    def test_contexte_annee(self):
        self.assertEqual(recit.contexte_annee(1850), "sous la IIe République")
        self.assertEqual(recit.contexte_annee(1860), "sous le Second Empire, l'époque des grands travaux")
        self.assertEqual(recit.contexte_annee(1930), "dans l'entre-deux-guerres")
        self.assertEqual(recit.contexte_annee(2010), "au XXIe siècle")

    def test_sections_completes(self):
        sections = recit.construire(faits_exemple(), TOUTES)
        cles = [s.cle for s in sections]
        for attendu in ("introduction", "cassini", "etat-major", "1950", "batiment", "aujourdhui",
                        "commune", "commune-toponymie", "commune-histoire", "alentours"):
            self.assertIn(attendu, cles)
        texte = " ".join(p for s in sections for p in s.paragraphes)
        self.assertNotIn("None", texte)
        self.assertIn("vers 1850", texte)
        self.assertIn("des murs en briques et un toit en ardoises", texte)
        self.assertIn("3 niveaux et 1 logement", texte)
        self.assertIn("devrait être visible", texte)  # bâti avant 1950

    def test_maison_recente(self):
        faits = faits_exemple(batiment={"annee_construction": 1985, "source": "BDNB (CSTB)"})
        texte = " ".join(p for s in recit.construire(faits, TOUTES) for p in s.paragraphes)
        self.assertIn("n'existait pas encore", texte)
        self.assertNotIn("devrait être visible", texte)

    def test_sans_donnees_optionnelles(self):
        faits = faits_exemple(parcelle=None, batiment=None, commune=None, wikipedia_commune=None, alentours=[])
        sections = recit.construire(faits, {"aujourdhui"})
        cles = [s.cle for s in sections]
        self.assertEqual(cles, ["introduction", "aujourdhui"])

    def test_sources(self):
        lignes = recit.sources_et_licences(faits_exemple(), {"cassini", "aujourdhui"})
        self.assertTrue(any("Cassini" in l for l in lignes))
        self.assertTrue(any("CC BY-SA" in l for l in lignes))


class TestRendu(unittest.TestCase):
    def images(self):
        img = Image.new("RGB", (60, 60), "white")
        ImageDraw.Draw(img).line((0, 0, 60, 60), fill="black", width=5)
        return {cle: img for cle in ("cassini", "1950", "aujourdhui")}

    def test_paginer(self):
        sections = recit.construire(faits_exemple(), {"cassini", "1950", "aujourdhui"})
        intro, pages = rendu.paginer(sections, {"cassini", "1950", "aujourdhui"})
        self.assertEqual(intro.cle, "introduction")
        for page in pages:
            illustrees = [s for s in page if s.image]
            self.assertLessEqual(len(illustrees), 1)
            if illustrees:
                self.assertEqual(len(page), 1)

    def test_livret_html(self):
        images = self.images()
        faits = faits_exemple()
        sections = recit.construire(faits, set(images))
        html = rendu.livret_html(faits, sections, images, ["Source A"], "Marque test")
        self.assertIn("L'histoire de votre maison", html)
        self.assertIn("data:image/jpeg;base64,", html)
        self.assertIn("Source A", html)
        self.assertIn("Marque test", html)

    def test_avant_apres_sans_adresse(self):
        img = self.images()["1950"]
        visuel = rendu.avant_apres(img, img, "Amiens · hier et aujourd'hui", "1950", "Aujourd'hui", "M", cote=100)
        self.assertEqual(visuel.size, (100 * 2 + 24 * 3, 90 + 100 + 60))


if __name__ == "__main__":
    unittest.main()
