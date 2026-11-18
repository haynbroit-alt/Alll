# L'histoire de votre maison — notes pour les agents de code

- Python 3.12 (`pip install -r requirements.txt`), Node 22 pour le PDF (Playwright) et le relais. Avant commit :
  `python -m unittest discover -s tests -q 2>&1 | tail -n 5 && node relais/test-signature.mjs`
- Une commande payée ne doit jamais échouer en silence ni exposer d'adresse ou d'email dans les journaux
  (voir `.github/workflows/livret.yml` et `maison/qualite.py`). Tester sur la vraie chaîne : Actions →
  « Livret (commande) » sans email (artefact) avant toute fusion qui touche la génération.
- Langue : identifiants en français existants à respecter, textes et docs en français.

## Sobriété — chaque session, sans exception
- Lire ciblé : Grep/Glob d'abord, puis Read avec `offset`/`limit`. Ne jamais relire un fichier déjà lu et inchangé.
- Sorties filtrées : jamais un log entier. `| tail -n 20`, `grep -E "error|Error|FAIL"` ; journaux Actions : lire
  le résumé « Contrôle qualité », pas tout le journal. Les sorties Bash sont plafonnées par `.claude/settings.json`.
- Code minimal : le plus petit diff qui résout le problème ; pas d'abstraction, d'option ni de fichier « au cas où ».
- Modèles : sous-agent haiku pour chercher, sonnet pour implémenter ou relire, opus pour décider, fable seulement
  quand la difficulté l'exige. `/clear` entre deux tâches sans lien, `/compact` en disant quoi garder.
- Carte : `maison/sources.py` (géocodage, cadastre, BDNB, BD TOPO, Wikipédia), `cartes.py` (époques IGN),
  `recit.py` (textes, sources et licences), `rendu.py` (HTML, PDF, image avant/après), `qualite.py` (verdict
  d'envoi), `envoi.py` (email + confirmation légale), `__main__.py` (CLI) ; `relais/worker.js` (Stripe → GitHub) ;
  `.github/workflows/livret.yml` (commande) ; `site/` (vente et pages légales) ; `docs/` (stratégie, mise en route).
