# Mise en route : ce qui reste à faire par un humain

Le code est prêt et a été éprouvé sur 13 commandes de test réelles (novembre 2026). Les étapes ci-dessous
demandent **ton** identité, **tes** comptes ou **ta** signature : un agent ne doit pas les faire à ta place.
Durée totale : environ 2 heures, en deux sessions. Toutes les obligations ont été vérifiées sur sources
officielles (Légifrance, economie.gouv.fr, service-public, CNIL, documentation Stripe et GitHub).

**Une seule dépense est obligatoire avant la première vente : le médiateur de la consommation** (environ 48 €
pour 3 ans). SOVEREIGN la refuse (règle des 10 % : 0 € encaissé = 0 € autorisé). C'est donc une décision
personnelle, hors enveloppe. Tout le reste est gratuit ; Stripe prend une commission par vente.

## Session 1 — environ 1 h

1. **Rendre ce dépôt privé** (Settings → General → Danger Zone → Change visibility). Les journaux et
   livrets de commande ne doivent pas être publics. Puis Settings → Actions → General → *Artifact and log
   retention* : **7 jours**.
2. **Déclarer la micro-entreprise** sur formalites.entreprises.gouv.fr (activité : édition et vente de
   livrets numériques personnalisés). Gratuit. On peut commencer à vendre dès le dépôt (déclaration au plus
   tard 15 jours après le début d'activité) ; le SIREN arrive en 2 semaines environ. En attendant, écrire
   « SIREN en cours d'attribution ». Option : demander à l'INSEE la non-diffusion de ton adresse.
3. **Adhérer à un médiateur de la consommation** référencé (liste CECMC sur economie.gouv.fr ; le moins
   cher trouvé : CM2C, 48 € pour 3 ans + 36 € par dossier). Obligatoire (amende jusqu'à 3 000 €).
4. **Boîte d'envoi des livrets (0 €)** : créer une adresse Gmail dédiée, activer la validation en deux
   étapes, créer un *mot de passe d'application*. Puis dans GitHub → Settings → Secrets and variables →
   Actions :
   - secrets : `SMTP_USER` (l'adresse), `SMTP_PASSWORD` (le mot de passe d'application) ;
   - variables : `SMTP_HOST` = `smtp.gmail.com`, `SMTP_PORT` = `465`, `CONTACT` = l'adresse de contact,
     `PRIX` = `29 €`, `URL_CGV` = l'adresse de `cgv.html` une fois le site en ligne.
   (Plus tard, avec un nom de domaine — environ 10 €/an, à financer par les premières ventes — passer à
   Resend : secret `RESEND_API_KEY` + variable `EXPEDITEUR`.)
5. **Site sur Cloudflare Pages** (gratuit, compatible dépôt privé ; GitHub Pages interdit l'e-commerce) :
   Cloudflare → Workers & Pages → Pages → connecter ce dépôt → dossier de sortie `site`, aucune commande
   de build. Activer **Web Analytics** (sans cookie) : il compte les visites du critère d'arrêt.
6. **Compléter les champs surlignés** `[À COMPLÉTER]` de `site/mentions-legales.html`, `site/cgv.html`,
   `site/confidentialite.html` (identité « Prénom Nom EI », adresse, téléphone, email, SIREN, médiateur,
   date), et copier dans les CGV **l'encadré officiel** annexé à l'article D. 211-4 du Code de la
   consommation (Légifrance), mot pour mot.

## Session 2 — environ 45 min

7. **Stripe** (compte en entreprise individuelle ; si Stripe exige le SIREN pour vérifier, lancer dès sa
   réception) :
   - Paramètres → Informations publiques : URL des CGV (obligatoire pour la case à cocher) ;
   - Paramètres → E-mails clients : activer les reçus de paiement ;
   - **Lien de paiement** à 29 € :
     - champ personnalisé *texte*, clé `adresse`, libellé « Adresse complète du bien (n°, rue, code
       postal, commune) », **obligatoire** ;
     - collecte de l'e-mail ;
     - « Exiger l'acceptation des conditions d'utilisation », texte personnalisé :
       « Je demande la fourniture immédiate de mon livret numérique et je reconnais perdre mon droit de
       rétractation dès sa fourniture (art. L221-28 13° du Code de la consommation). J'accepte les CGV. »
8. **Relais Cloudflare Worker** : créer un Worker, coller `relais/worker.js`, variables secrètes
   `STRIPE_WEBHOOK_SECRET`, `GITHUB_TOKEN` (jeton *fine-grained* limité à ce dépôt, Contents : Read and
   write), `GITHUB_REPO` = `haynbroit-alt/Alll`. Dans Stripe → Développeurs → Webhooks : URL du Worker,
   événement `checkout.session.completed`, secret `whsec_…` copié dans le Worker.
9. Coller l'URL du lien de paiement dans `site/index.html` (constante `LIEN_PAIEMENT`).
10. **Tests de bout en bout** :
    - Actions → « Livret (commande) » → *Run workflow* avec ton adresse **et** ton email → tu dois recevoir
      le livret et la confirmation de commande ;
    - un paiement en **mode test** Stripe (carte 4242 4242 4242 4242) → même résultat ;
    - un test avec une adresse sans code postal → tu dois recevoir l'email « vérification sous 24 h » et
      GitHub doit t'alerter.

## Ce que fait la chaîne, et ce qu'elle te demande

- Commande normale : livret envoyé en quelques minutes, avec la confirmation légale.
- Adresse douteuse (sans code postal, code postal différent, outre-mer, localisée à la commune seulement,
  livret trop pauvre) ou panne : le client reçoit « livraison sous 24 h », **tu reçois une alerte GitHub**
  « Commande à traiter à la main ». Ouvre l'exécution, télécharge le livret (conservé 3 jours), vérifie,
  puis relance « Livret (commande) » avec l'adresse corrigée et l'email du client. Si c'est impossible :
  rembourse dans Stripe.

## Risque connu à surveiller

Les conditions de GitHub réservent Actions aux activités liées au logiciel du dépôt ; fabriquer des commandes
clients est une zone grise. Au volume du test de Noël (quelques dizaines de commandes), le risque est faible.
**Si le test réussit (≥ 30 commandes), déplacer la fabrication** sur un petit serveur financé par
l'enveloppe des 10 % (environ 5 €/mois), avant d'augmenter le volume.

## Critère d'arrêt (docs/STRATEGIE.md)

Moins de 30 commandes pour environ 1 000 visites au 20/12 : arrêter la vente aux particuliers et basculer
vers les agences immobilières et notaires.
