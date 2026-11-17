# L'histoire de votre maison

Générateur automatique d'un livret personnalisé : à partir d'une simple adresse, il montre le lieu
sur la **carte de Cassini (vers 1760)**, la **carte d'état-major (1820-1866)**, les **photographies
aériennes de 1950 à aujourd'hui**, avec l'âge estimé du bâtiment, sa parcelle, l'origine du nom et
l'histoire de la commune. Il produit aussi une image « hier / aujourd'hui » prête à partager.

Exemple réel : [`exemples/amiens-cathedrale/livret.pdf`](exemples/amiens-cathedrale/livret.pdf) ·
[`avant-apres.jpg`](exemples/amiens-cathedrale/avant-apres.jpg)

Le pourquoi de ce projet (analyse d'opportunité, chiffres, risques, critères d'arrêt) :
[`docs/STRATEGIE.md`](docs/STRATEGIE.md). Ce qu'il reste à faire côté humain pour encaisser :
[`docs/MISE-EN-ROUTE.md`](docs/MISE-EN-ROUTE.md).

## Utilisation

```bash
pip install -r requirements.txt
python -m maison "30 place Notre-Dame 80000 Amiens" --pdf
# → sortie/<adresse>/livret.html, livret.pdf, avant-apres.jpg, faits.json
```

Options : `--pdf` (Node + Playwright requis), `--ia` (réécriture du récit par Claude, clé API
requise ; sans elle le récit est généré sans IA, uniquement à partir des faits), `--marque`,
`--sortie`, `--pixels`.

## Chaîne automatique (0 € de frais fixes)

```
Stripe Payment Link (champ « adresse »)
   └─► webhook ─► relais/worker.js (Cloudflare Worker, gratuit)
                     └─► GitHub repository_dispatch ─► .github/workflows/livret.yml
                                                         ├─ python -m maison … --pdf
                                                         ├─ python -m maison.qualite (sans donnée personnelle)
                                                         └─ python -m maison.envoi (SMTP d'une boîte existante, ou Resend)
```

Une commande douteuse (adresse sans code postal ou localisée ailleurs, outre-mer, livret trop pauvre) ou une
panne n'est jamais silencieuse : le client est prévenu (livraison sous 24 h) et le responsable reçoit une
alerte GitHub. Pages légales : `site/cgv.html`, `site/confidentialite.html`, `site/mentions-legales.html`.

## Données et licences (vérifiées dans les métadonnées officielles)

| Donnée | Source | Licence |
|---|---|---|
| Cartes de Cassini, d'état-major, photos aériennes | IGN – Géoplateforme (WMS) | Licence Ouverte Etalab |
| Adresse | Base Adresse Nationale via Géoplateforme | Licence Ouverte Etalab |
| Parcelle | Cadastre DGFiP via API Carto | Licence Ouverte Etalab |
| Bâtiment (année, matériaux) | BDNB (CSTB), repli BD TOPO® (IGN) | données ouvertes (licence BDNB à confirmer) |
| Commune | geo.api.gouv.fr | Licence Ouverte Etalab |
| Résumé, toponymie, histoire, lieux proches | Wikipédia | CC BY-SA 4.0 (attribution dans le livret) |

## Tests

```bash
python -m unittest discover -s tests -v   # hors ligne
node relais/test-signature.mjs            # relais Stripe → GitHub
```
