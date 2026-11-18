# L'histoire de votre maison — notes pour les agents de code

- Python 3.12 (`pip install -r requirements.txt`), Node 22 pour le PDF (Playwright) et le relais. Avant commit :
  `.claude/bin/journal verif bash -o pipefail -c 'python -m unittest discover -s tests && node relais/test-signature.mjs'`
- Une commande payée ne doit jamais échouer en silence ni exposer d'adresse ou d'email dans les journaux
  (voir `.github/workflows/livret.yml` et `maison/qualite.py`). Tester sur la vraie chaîne : Actions →
  « Livret (commande) » sans email (artefact) avant toute fusion qui touche la génération.
- Langue : identifiants en français existants à respecter, textes et docs en français.

## Fiabilité avant sobriété — la preuve prime sur le plafond de sortie
- Toute vérification passe par `.claude/bin/journal <étiquette> <commande>` : journal complet sur disque, résumé
  jamais tronqué, code de sortie exact. Jamais `vérification | tail/head/grep` sans `pipefail` (le crochet
  `.claude/hooks/garde_pipe.py` le refuse) : le pipe masque l'échec.
- « Réussi » exige le code 0 ET la ligne de bilan de l'outil (« OK », « tous les tests passent »). Sortie
  incomplète : lire le journal complet avant de conclure ; sinon écrire « non vérifié ».
- Une commande test sur la vraie chaîne n'est prouvée que par le `conclusion: success` de l'API GitHub ET le
  verdict de « Contrôle qualité » lu dans le journal. Fusion seulement si tous les contrôles de la tête actuelle
  sont en success (aucun `in_progress` ni manquant) ; si une preuve vient d'un autre SHA, le dire et vérifier
  que le changement intermédiaire ne touche pas ce qu'elle prouve.

## Sobriété — chaque session, sans exception
- Lire ciblé : Grep/Glob d'abord, puis Read avec `offset`/`limit`. Ne jamais relire un fichier déjà lu et inchangé.
- Sorties filtrées : jamais un log entier ; une vérification passe par `.claude/bin/journal` (voir « Fiabilité »).
  Journaux Actions : lire le résumé « Contrôle qualité » et le `conclusion` de l'API, pas tout le journal.
- Code minimal : le plus petit diff qui résout le problème ; pas d'abstraction, d'option ni de fichier « au cas où ».
- Modèles : sous-agent haiku pour chercher, sonnet pour implémenter ou relire, opus pour décider, fable seulement
  quand la difficulté l'exige. `/clear` entre deux tâches sans lien, `/compact` en disant quoi garder.
- Carte : `maison/sources.py` (géocodage, cadastre, BDNB, BD TOPO, Wikipédia), `cartes.py` (époques IGN),
  `recit.py` (textes, sources et licences), `rendu.py` (HTML, PDF, image avant/après), `qualite.py` (verdict
  d'envoi), `envoi.py` (email + confirmation légale), `__main__.py` (CLI) ; `relais/worker.js` (Stripe → GitHub) ;
  `.github/workflows/livret.yml` (commande) ; `site/` (vente et pages légales) ; `docs/` (stratégie, mise en route).
