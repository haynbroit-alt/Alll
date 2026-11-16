// Convertit un livret HTML en PDF A4 avec Playwright/Chromium.
// Usage : node outils/html2pdf.mjs <entree.html> <sortie.pdf>
import { pathToFileURL } from "node:url";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");

const [entree, sortie] = process.argv.slice(2);
if (!entree || !sortie) {
  console.error("Usage : node outils/html2pdf.mjs <entree.html> <sortie.pdf>");
  process.exit(2);
}

const navigateur = await chromium.launch();
try {
  const page = await navigateur.newPage();
  await page.goto(pathToFileURL(entree).href, { waitUntil: "load" });
  await page.pdf({
    path: sortie,
    format: "A4",
    printBackground: true,
    margin: { top: "0", right: "0", bottom: "0", left: "0" },
  });
} finally {
  await navigateur.close();
}
