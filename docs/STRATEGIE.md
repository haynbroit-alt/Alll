# Stratégie : trouver une opportunité originale, légale, à 0 €, capable de 1 000 €/jour

Analyse réalisée en novembre 2026, selon la boucle Observer → Comprendre → Confronter → Hypothèses →
Anticiper → Prioriser → Décider → Simuler → Exécuter → Mesurer → Apprendre → Réviser → Dreaming.
Les probabilités sont des **estimations subjectives**, pas des promesses.

## 1. Observer / Comprendre

1 000 €/jour, c'est 30 000 €/mois, soit environ 365 000 €/an de chiffre d'affaires. À 0 € de départ, il faut
un client qui a déjà un budget, un canal de diffusion gratuit et une livraison quasi gratuite.

## 2. Confronter : pistes testées et écartées (avec preuves)

| Piste | Verdict |
|---|---|
| Radar des parkings soumis à l'obligation d'ombrières (loi APER) | Solide (aucune base nationale, amendes de 20 000 à 40 000 €/an, échéance du 30/06/2027 pour le report), mais demande de la prospection commerciale. **Gardée en plan B.** |
| Récupération de loyers commerciaux trop indexés (Cour de cassation 2025) | Le conseil juridique est réservé aux avocats (loi de 1971). Écartée sauf profil juriste. |
| Mise en conformité « anti-déforestation » (EUDR) pour PME | Échéances réelles (30/12/2026 et 30/06/2027), mais déjà beaucoup de logiciels et un texte instable. |
| Appli qui traque le greenwashing (directive 2024/825) | Au moins 7 outils existent déjà, et la France n'a pas transposé la directive. |
| Générateur de déclarations de travaux pour panneaux solaires | Déjà pris (Vesta, Hélios, Démarcheco, DPT Solaire, Solteo, iColl). |
| API payée directement par les agents IA (x402) | Environ 3,7 M$ par trimestre pour tout l'écosystème mondial : 1 000 €/jour ≈ 3 % du total. |
| Robots de collecte vendus sur Apify | Les meilleurs créateurs dépassent 10 000 $/mois, mais 0,67 % des robots captent la moitié de la demande. |
| Classiques (dropshipping, formation, agence réseaux sociaux, trading) | Écartés par principe. |

**Leçon :** en 2026, toute idée « réglementation + appli automatique » est copiée en quelques semaines.
L'originalité doit venir d'un acheteur inattendu ou d'une émotion, pas d'une obligation légale.

## 3. Hypothèse retenue : « L'histoire de votre maison »

- **Ce qui existe :** des visionneuses gratuites (IGN Remonter le temps, Skywayback, Retoria) et un poster
  historique vendu par l'IGN, signe que des gens paient pour ce type d'image en cadeau.
- **Ce qui manque :** aucun **livret personnalisé et raconté** produit automatiquement.
- **Le marché :** l'émotion (cadeau, crémaillère, maison de famille, Noël), plus un usage professionnel
  (agences immobilières, notaires).

## 4. Anticiper / Prioriser : calcul

| Voie vers 1 000 €/jour | Volume |
|---|---|
| Livret PDF à 29-33 € | ≈ 30 ventes/jour |
| Livre imprimé à environ 67 € (impression à la demande) | ≈ 15 ventes/jour |
| Agences immobilières à 99 €/mois | ≈ 300 agences |

Estimations personnelles :
- **Première vente dans les 2 semaines après le lancement :** environ 50 %.
- **Un jour à 1 000 € grâce à une publication virale :** plausible.
- **1 000 €/jour en moyenne sur un mois dans les 12 mois :** environ 5 à 10 %.

## 5. Décider / Simuler

- **Test :** Noël 2026, puisqu'un PDF livré instantanément fait un cadeau de dernière minute.
- **Critère d'arrêt :** moins de 30 commandes pour environ 1 000 visites au 20/12, ou on bascule sur les seules agences immobilières.
- **Diffusion à 0 € :** l'image avant/après partagée dans les groupes Facebook de nostalgie locale
  (« Tu es de [ville] si… »), sur TikTok et Instagram, et lors de démarchages ciblés d'agences.

## 6. Exécuter (fait dans ce dépôt)

- **Le générateur :** testé en conditions réelles.
- **L'automatisation complète :** Stripe → Cloudflare Worker → GitHub Actions → email Resend.
- **La page de vente.**
- **Ce qui reste humain :** voir `docs/MISE-EN-ROUTE.md` (statut, comptes, dépôt privé, mentions légales).

## 7. Mesurer : indicateurs à suivre

- **Le tunnel de vente :** visites → clics « Créer mon livret » → paiements (taux de conversion visé : 3 %).
- **La qualité :** taux de livrets corrects (époques disponibles, bâtiment trouvé), demandes de remboursement.
- **La diffusion :** partages de l'image avant/après.
- **Le chiffre d'affaires par jour,** et la part venant des agences immobilières.

## 8. Risques et validation humaine

- **Ce qui est vérifié :** la licence des cartes et photos IGN (Licence Ouverte, réutilisation commerciale
  autorisée avec mention de la source), dans les métadonnées officielles de la Géoplateforme.
- **Ce qui reste à vérifier :** la licence de la BDNB (CSTB).
- **À ne pas utiliser :** la base des ventes immobilières (DVF), dont la licence interdit d'identifier les personnes.
- **L'IA :** le récit par défaut n'invente rien. L'option `--ia` reformule sans ajouter de faits,
  avec un retour au texte d'origine en cas de doute.
- **La confidentialité :** l'image partagée n'affiche que la commune. Le dépôt doit être privé en production.

## 9. Dreaming : ce qui peut tout faire échouer

- **L'IGN lance le même produit.** Il faudrait se différencier par le récit et par l'offre aux agences.
- **Un assistant IA le fait gratuitement.**
- **La saisonnalité des cadeaux.**
- **Une couverture photo ancienne incomplète,** à signaler avant l'achat.
- **Les pistes suivantes :** livre imprimé, version « maison de famille » (succession), API pour agences,
  et le radar des parkings APER en parallèle (plan B).
