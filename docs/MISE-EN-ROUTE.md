# Mise en route : ce qui reste à faire par un humain

Le code est prêt. Ces étapes demandent **ton** identité, **tes** comptes ou **ta** signature : un agent ne
doit pas les faire à ta place. Compter environ 1 h 30. Tout est gratuit au départ : Stripe ne prend
qu'une commission par vente, et Cloudflare, Resend et GitHub restent dans leurs offres gratuites.

## 1. Statut (≈ 15 min)
- [ ] Déclarer une micro-entreprise sur le guichet unique (formalites.entreprises.gouv.fr) : activité
      de vente de contenus numériques. Gratuit.
- [ ] Remplir les mentions légales en bas de `site/index.html` (nom, SIREN, adresse, email).

## 2. Paiement : Stripe (≈ 20 min)
- [ ] Créer un compte Stripe et un **Payment Link** à 29 € (prix à tester).
- [ ] Dans le Payment Link : **Ajouter un champ personnalisé** de type texte, clé `adresse`,
      libellé « Adresse de la maison » ; activer la collecte de l'email.
- [ ] Ajouter dans la description la case/mention : « Livraison immédiate du contenu numérique :
      je renonce à mon droit de rétractation (art. L221-28 C. conso.). »
- [ ] Coller l'URL du lien dans `site/index.html` (constante `LIEN_PAIEMENT`).

## 3. Relais : Cloudflare Worker (≈ 20 min)
- [ ] Créer un compte Cloudflare, un Worker, coller `relais/worker.js`.
- [ ] Sur GitHub : créer un jeton *fine-grained* limité à ce dépôt, permission **Contents: Read and write**.
- [ ] Variables secrètes du Worker : `STRIPE_WEBHOOK_SECRET`, `GITHUB_TOKEN`, `GITHUB_REPO`
      (= `haynbroit-alt/Alll`).
- [ ] Dans Stripe → Développeurs → Webhooks : ajouter l'URL du Worker, événement
      `checkout.session.completed` ; copier le secret `whsec_…` dans le Worker.

## 4. Email : Resend (≈ 15 min)
- [ ] Créer un compte Resend, vérifier un domaine (ou tester avec `onboarding@resend.dev` vers ta propre adresse).
- [ ] Dans GitHub → Settings → Secrets and variables → Actions :
  - secret `RESEND_API_KEY`
  - variable `EXPEDITEUR` (ex. `L'histoire de votre maison <livret@ton-domaine.fr>`)
  - variable `MARQUE` (facultatif)
  - secret `ANTHROPIC_API_KEY` (facultatif : active la réécriture du récit par Claude)

## 5. ⚠️ Confidentialité
- [ ] **Rendre le dépôt privé** (ou séparer le moteur dans un dépôt privé). Les journaux et artefacts
      d'Actions d'un dépôt public sont visibles : l'adresse et l'email sont masqués dans les journaux, et
      l'artefact n'est conservé qu'un jour, mais un dépôt privé reste la bonne pratique RGPD.
- [ ] Ajouter une courte politique de confidentialité : données utilisées uniquement pour produire et
      envoyer le livret, non conservées.

## 6. Mise en ligne de la page (≈ 10 min)
- [ ] GitHub Pages sur le dossier `site/`, ou n'importe quel hébergeur statique gratuit.
      (Si le dépôt devient privé, GitHub Pages demande un plan payant : utiliser alors Cloudflare Pages, gratuit.)

## 7. Test de bout en bout
- [ ] Onglet Actions → « Livret (commande) » → *Run workflow* avec ton adresse et ton email.
- [ ] Puis un vrai paiement de test Stripe (mode test) → vérifier la réception de l'email.

## 8. Vérifications avant la première vente
- [ ] Licence de la BDNB (CSTB) : confirmer la réutilisation commerciale et la mention exacte.
- [ ] Relire à la main les 20 à 50 premiers livrets (contrôle qualité, cas des adresses rurales).
