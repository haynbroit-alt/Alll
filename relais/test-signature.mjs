// Test du relais : node relais/test-signature.mjs
import { createHmac } from "node:crypto";
import assert from "node:assert/strict";
import worker, { signatureValide } from "./worker.js";

const secret = "whsec_test";
const t = Math.floor(Date.now() / 1000);

function signer(corps, horodatage = t) {
  const v1 = createHmac("sha256", secret).update(`${horodatage}.${corps}`).digest("hex");
  return `t=${horodatage},v1=${v1}`;
}

const corps = JSON.stringify({
  type: "checkout.session.completed",
  data: {
    object: {
      id: "cs_test_123",
      payment_status: "paid",
      customer_details: { email: "client@example.com" },
      custom_fields: [{ key: "adresse", type: "text", text: { value: "30 place Notre-Dame 80000 Amiens" } }],
    },
  },
});

assert.equal(await signatureValide(corps, signer(corps), secret), true, "signature correcte");
assert.equal(await signatureValide(corps + " ", signer(corps), secret), false, "corps modifié");
assert.equal(await signatureValide(corps, signer(corps, t - 1000), secret), false, "trop ancien");
assert.equal(await signatureValide(corps, "", secret), false, "en-tête absent");

// Bout en bout avec un faux GitHub.
let appel = null;
globalThis.fetch = async (url, options) => {
  appel = { url, options };
  return new Response(null, { status: 204 });
};
const env = { STRIPE_WEBHOOK_SECRET: secret, GITHUB_TOKEN: "x", GITHUB_REPO: "proprio/depot" };
const reponse = await worker.fetch(
  new Request("https://relais.example/", { method: "POST", body: corps, headers: { "stripe-signature": signer(corps) } }),
  env,
);
assert.equal(reponse.status, 200);
assert.equal(appel.url, "https://api.github.com/repos/proprio/depot/dispatches");
const charge = JSON.parse(appel.options.body);
assert.equal(charge.event_type, "commande-livret");
assert.deepEqual(charge.client_payload, {
  adresse: "30 place Notre-Dame 80000 Amiens",
  email: "client@example.com",
  commande: "cs_test_123",
});

const refus = await worker.fetch(
  new Request("https://relais.example/", { method: "POST", body: corps, headers: { "stripe-signature": "t=1,v1=00" } }),
  env,
);
assert.equal(refus.status, 400);
console.log("relais : tous les tests passent");
