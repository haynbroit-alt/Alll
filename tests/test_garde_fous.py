"""Garde-fous des sessions Claude : code de sortie jamais masqué, journal complet conservé."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

RACINE = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("garde_pipe", RACINE / ".claude" / "hooks" / "garde_pipe.py")
garde = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(garde)


class TestGardeFous(unittest.TestCase):
    def test_verification_dans_un_pipe_refusee(self):
        for commande in ("python -m unittest discover -s tests 2>&1 | tail -n 5 && node relais/test-signature.mjs",
                         "node relais/test-signature.mjs | grep OK"):
            self.assertTrue(garde.verdict(commande), commande)

    def test_formes_sures_autorisees(self):
        for commande in ("bash -o pipefail -c 'python -m unittest discover -s tests | tail -n 5'",
                         ".claude/bin/journal verif python -m unittest discover -s tests",
                         "git log --oneline | head -5"):
            self.assertIsNone(garde.verdict(commande), commande)

    def test_crochet_refuse(self):
        entree = json.dumps({"tool_name": "Bash", "tool_input": {"command": "python -m unittest | tail"}})
        sortie = subprocess.run(["python3", str(RACINE / ".claude" / "hooks" / "garde_pipe.py")],
                                input=entree, capture_output=True, text=True, check=True).stdout
        self.assertEqual(json.loads(sortie)["hookSpecificOutput"]["permissionDecision"], "deny")

    def test_journal_garde_le_code_et_tout_le_journal(self):
        with tempfile.TemporaryDirectory() as dossier:
            resultat = subprocess.run(
                [str(RACINE / ".claude" / "bin" / "journal"), "essai", "bash", "-c",
                 'for i in $(seq 1 5000); do echo "ligne $i ERROR"; done; exit 3'],
                capture_output=True, text=True, check=False, env={"JOURNAL_DIR": dossier, "PATH": "/usr/bin:/bin"},
            )
            lignes = resultat.stdout.splitlines()
            self.assertEqual(resultat.returncode, 3)
            self.assertTrue(lignes[0].startswith("[journal] code=3") and lignes[-1].startswith("[journal] code=3"))
            self.assertLess(len(resultat.stdout), 8000)
            journal = next(Path(dossier).glob("essai-*.log"))
            self.assertEqual(journal.read_text().count("\n"), 5000)


if __name__ == "__main__":
    unittest.main()
