// Relais Stripe → GitHub Actions (Cloudflare Worker, offre gratuite).
//
// Stripe appelle ce Worker à chaque paiement (événement checkout.session.completed).
// Le Worker vérifie la signature Stripe, lit l'email du client et l'adresse saisie
// dans le champ personnalisé « adresse » du Payment Link, puis déclenche le workflow
// .github/workflows/livret.yml via l'API repository_dispatch.
//
// Variables (Cloudflare → Worker → Settings → Variables, en « Secret ») :
//   STRIPE_WEBHOOK_SECRET  whsec_... (Stripe → Développeurs → Webhooks)
//   GITHUB_TOKEN           jeton « fine-grained » limité à ce dépôt, permission Contents: Read and write
//   GITHUB_REPO            ex. haynbroit-alt/Alll
//   CHAMP_ADRESSE          (facultatif) clé du champ personnalisé, « adresse » par défaut

const TOLERANCE_SECONDES = 300;

export default {
  async fetch(request, env) {
    if (request.method !== "POST") {
      return new Response("Méthode non autorisée", { status: 405 });
    }
    const brut = await request.text();
    const signature = request.headers.get("stripe-signature") || "";
    if (!(await signatureValide(brut, signature, env.STRIPE_WEBHOOK_SECRET))) {
      return new Response("Signature invalide", { status: 400 });
    }

    const evenement = JSON.parse(brut);
    if (evenement.type !== "checkout.session.completed") {
      return new Response("Ignoré", { status: 200 });
    }
    const session = evenement.data.object;
    if (session.payment_status !== "paid") {
      return new Response("Paiement non finalisé", { status: 200 });
    }

    const cle = env.CHAMP_ADRESSE || "adresse";
    const champ = (session.custom_fields || []).find((c) => c.key === cle);
    const adresse = champ && champ.text && champ.text.value ? champ.text.value.trim() : "";
    const email = (session.customer_details && session.customer_details.email) || "";
    if (!adresse || adresse.length > 200 || !email) {
      // On répond 200 pour que Stripe ne réessaie pas : la commande est à traiter à la main.
      console.log(`Commande ${session.id} incomplète : traitement manuel requis.`);
      return new Response("Commande incomplète", { status: 200 });
    }

    const reponse = await fetch(`https://api.github.com/repos/${env.GITHUB_REPO}/dispatches`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${env.GITHUB_TOKEN}`,
        Accept: "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": "relais-livret",
      },
      body: JSON.stringify({
        event_type: "commande-livret",
        client_payload: { adresse, email, commande: session.id },
      }),
    });
    if (!reponse.ok) {
      // 500 : Stripe réessaiera automatiquement plus tard.
      return new Response(`GitHub a répondu ${reponse.status}`, { status: 500 });
    }
    return new Response("OK", { status: 200 });
  },
};

export async function signatureValide(corps, entete, secret, maintenant = Date.now() / 1000) {
  if (!secret || !entete) return false;
  const morceaux = grouper(entete.split(","));
  const t = (morceaux.t || [])[0]?.split("=")[1];
  const signatures = (morceaux.v1 || []).map((p) => p.split("=")[1]);
  if (!t || signatures.length === 0) return false;
  if (Math.abs(maintenant - Number(t)) > TOLERANCE_SECONDES) return false;

  const cle = await crypto.subtle.importKey(
    "raw",
    new TextEncoder().encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"],
  );
  const mac = await crypto.subtle.sign("HMAC", cle, new TextEncoder().encode(`${t}.${corps}`));
  const attendu = [...new Uint8Array(mac)].map((o) => o.toString(16).padStart(2, "0")).join("");
  return signatures.some((s) => egalite(s, attendu));
}

function grouper(parties) {
  const resultat = {};
  for (const p of parties) {
    const k = p.split("=")[0];
    (resultat[k] = resultat[k] || []).push(p);
  }
  return resultat;
}

function egalite(a, b) {
  if (a.length !== b.length) return false;
  let diff = 0;
  for (let i = 0; i < a.length; i++) diff |= a.charCodeAt(i) ^ b.charCodeAt(i);
  return diff === 0;
}
