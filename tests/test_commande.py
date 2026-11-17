"""Parcours d'une commande payée : tolérance des sources, contrôle qualité, emails au client."""

from __future__ import annotations

import base64
import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from maison import envoi, qualite, sources

ADRESSE = sources.Adresse(
    label="1 place du Capitole 31000 Toulouse", commune="Toulouse", code_insee="31555", code_postal="31000",
    lon=1.4437, lat=43.6045, cle_ban="31555_xxxx_00001", score=0.93, type="housenumber",
)


def faits_json(**surcharges) -> dict:
    faits = {
        "adresse": {"code_postal": "31000", "type": "housenumber", "score": 0.93},
        "batiment": {"annee_construction": 1750},
        "parcelle": {"id": "x"},
        "wikipedia_commune": {"titre": "Toulouse"},
        "alentours": [{}, {}],
        "avertissements": [],
    }
    faits.update(surcharges.pop("faits", {}))
    donnees = {"faits": faits, "epoques_disponibles": ["cassini", "etat-major", "1950", "aujourdhui"]}
    donnees.update(surcharges)
    return donnees


class TestToleranceDesSources(unittest.TestCase):
    def test_une_source_facultative_qui_plante_ne_bloque_pas_la_commande(self):
        with (
            mock.patch.object(sources, "geocoder", return_value=ADRESSE),
            mock.patch.object(sources, "parcelle", return_value=None),
            mock.patch.object(sources, "batiment_bdnb", return_value=None),
            mock.patch.object(sources, "batiment_bdtopo", side_effect=ValueError("géométrie inattendue")),
            mock.patch.object(sources, "commune", return_value={"nom": "Toulouse"}),
            mock.patch.object(sources, "wikipedia_commune", side_effect=TimeoutError()),
            mock.patch.object(sources, "wikipedia_alentours", return_value=[]),
        ):
            faits = sources.collecter("1 place du Capitole 31000 Toulouse")
        self.assertIsNone(faits.batiment)
        self.assertIsNone(faits.wikipedia_commune)
        self.assertIn("Donnée indisponible : caractéristiques du bâtiment.", faits.avertissements)


class TestQualite(unittest.TestCase):
    def test_livret_complet_envoyable(self):
        rapport = qualite.evaluer(faits_json())
        self.assertEqual(rapport["verdict"], "envoyable")
        self.assertNotIn("label", json.dumps(rapport))  # aucune adresse dans le journal

    def test_rue_ou_lieu_dit_envoyable_commune_seule_non(self):
        for precision in ("street", "locality"):
            rapport = qualite.evaluer(faits_json(faits={"adresse": {"code_postal": "29280", "type": precision, "score": 0.68}}))
            self.assertEqual(rapport["verdict"], "envoyable", precision)
        rapport = qualite.evaluer(faits_json(faits={"adresse": {"code_postal": "31000", "type": "municipality", "score": 0.5}}))
        self.assertEqual(rapport["verdict"], "a_verifier")
        self.assertEqual(len(rapport["raisons"]), 2)  # niveau commune + correspondance faible

    def test_adresse_sans_ville_localisee_ailleurs(self):
        # Cas réel : « 12 rue Victor Hugo » sans ville a été localisé à Bordeaux (33200) avec un score élevé.
        bordeaux = faits_json(faits={"adresse": {"code_postal": "33200", "type": "housenumber", "score": 0.95}})
        self.assertEqual(qualite.evaluer(bordeaux, "12 rue Victor Hugo")["verdict"], "a_verifier")
        self.assertEqual(qualite.evaluer(bordeaux, "12 rue Victor Hugo 69002 Lyon")["verdict"], "a_verifier")
        self.assertEqual(qualite.evaluer(bordeaux, "12, rue Victor-Hugo, 33200 Bordeaux")["verdict"], "envoyable")

    def test_outre_mer_et_livret_pauvre_a_verifier(self):
        rapport = qualite.evaluer(
            faits_json(faits={"adresse": {"code_postal": "97400", "type": "housenumber", "score": 0.9}},
                       epoques_disponibles=["aujourdhui"])
        )
        self.assertEqual(rapport["departement"], "974")
        self.assertTrue(any("métropolitaine" in r for r in rapport["raisons"]))
        self.assertTrue(any("1 époque" in r for r in rapport["raisons"]))

    def test_code_de_sortie(self):
        with tempfile.TemporaryDirectory() as d:
            chemin = Path(d) / "faits.json"
            chemin.write_text(json.dumps(faits_json()), encoding="utf-8")
            self.assertEqual(qualite.main([str(chemin), "--saisie", "1 place du Capitole 31000 Toulouse"]), 0)
            chemin.write_text(json.dumps(faits_json(epoques_disponibles=[])), encoding="utf-8")
            self.assertEqual(qualite.main([str(chemin)]), 4)


class TestEnvoi(unittest.TestCase):
    def setUp(self):
        self.dossier = Path(tempfile.mkdtemp())
        (self.dossier / "livret.pdf").write_bytes(b"%PDF-1.7 test")
        (self.dossier / "faits.json").write_text(
            json.dumps({"faits": {"commune": {"nom": "Toulouse"}, "adresse": {"commune": "Toulouse"}}}),
            encoding="utf-8",
        )

    def test_livraison_porte_la_confirmation_legale(self):
        env = {"RESEND_API_KEY": "re_test", "PRIX": "29 €", "URL_CGV": "https://exemple.fr/cgv.html",
               "CONTACT": "contact@exemple.fr"}
        with mock.patch.object(envoi, "_par_resend", return_value="id-1") as resend:
            envoi.envoyer("client@exemple.fr", env, dossier=self.dossier, commande="cs_123")
        charge = resend.call_args.args[0]
        self.assertIn("L221-28 13°", charge["html"])
        self.assertIn("n° cs_123", charge["html"])
        self.assertIn("29 € TTC", charge["html"])
        self.assertIn("https://exemple.fr/cgv.html", charge["html"])
        self.assertEqual(charge["reply_to"], "contact@exemple.fr")
        self.assertEqual(charge["attachments"][0]["filename"], "livret.pdf")

    def test_message_d_attente_sans_piece_jointe(self):
        with mock.patch.object(envoi, "_par_resend", return_value="id-2") as resend:
            envoi.envoyer("client@exemple.fr", {"RESEND_API_KEY": "re_test"}, message="verification")
        charge = resend.call_args.args[0]
        self.assertNotIn("attachments", charge)
        self.assertIn("24 heures", charge["html"])

    def test_smtp_sans_domaine(self):
        env = {"SMTP_HOST": "smtp.exemple.fr", "SMTP_USER": "boutique@exemple.fr", "SMTP_PASSWORD": "x"}
        serveur = mock.MagicMock()
        with mock.patch.object(envoi.smtplib, "SMTP_SSL", return_value=serveur):
            envoi.envoyer("client@exemple.fr", env, dossier=self.dossier, commande="cs_9")
        message = serveur.send_message.call_args.args[0]
        self.assertIn("boutique@exemple.fr", message["From"])
        pieces = [p.get_filename() for p in message.iter_attachments()]
        self.assertEqual(pieces, ["livret.pdf"])
        serveur.login.assert_called_once_with("boutique@exemple.fr", "x")

    def test_sans_canal_rien_n_est_envoye(self):
        with mock.patch.dict(envoi.os.environ, {}, clear=True):
            self.assertEqual(envoi.main(["--email", "client@exemple.fr", "--message", "verification"]), 3)

    def test_email_invalide(self):
        with self.assertRaises(ValueError):
            envoi.envoyer("pas-un-email", {"RESEND_API_KEY": "re_test"}, message="verification")


if __name__ == "__main__":
    unittest.main()
