"""Réécriture optionnelle du récit par Claude (option ``--ia``).

Le récit déterministe (recit.py) reste la référence : Claude ne fait que reformuler
nos propres paragraphes dans un style plus chaleureux, à partir des MÊMES faits.
En cas d'erreur, de refus ou de réponse incohérente, le texte d'origine est conservé.
L'extrait Wikipédia (CC BY-SA) n'est pas réécrit, pour garder une attribution simple.

Nécessite le paquet ``anthropic`` et des identifiants (ANTHROPIC_API_KEY ou ``ant auth login``).
"""

from __future__ import annotations

import json
import sys
from typing import Any

from .recit import Section

MODELE = "claude-opus-5-5"
SECTIONS_NON_REECRITES = {"commune", "commune-toponymie", "commune-histoire", "alentours"}

CONSIGNES = """Tu es l'auteur d'un livret-cadeau intitulé « L'histoire de votre maison ».
On te donne des faits vérifiés (JSON) et des paragraphes déjà écrits à partir de ces faits.
Réécris chaque paragraphe en français, dans un style chaleureux, vivant et précis.

Règles impératives :
- N'ajoute AUCUN fait absent des données fournies (pas de personnage, d'événement, de date ou de chiffre nouveaux).
- Conserve les précautions : une année de construction issue des fichiers fonciers reste une estimation (« vers », « environ »).
- Garde le même nombre de sections et les mêmes clés ; longueur comparable à l'original.
- Ne cite pas l'adresse complète plus d'une fois dans tout le livret."""

SCHEMA = {
    "type": "object",
    "properties": {
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "cle": {"type": "string"},
                    "paragraphes": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["cle", "paragraphes"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["sections"],
    "additionalProperties": False,
}


def enrichir(faits: dict[str, Any], sections: list[Section]) -> list[Section]:
    try:
        import anthropic
    except ImportError:
        print("[ia] paquet 'anthropic' absent : récit d'origine conservé.", file=sys.stderr)
        return sections

    a_reecrire = [
        {"cle": s.cle, "titre": s.titre, "paragraphes": s.paragraphes}
        for s in sections
        if s.cle not in SECTIONS_NON_REECRITES
    ]
    faits_utiles = {k: v for k, v in faits.items() if k != "wikipedia_commune"}
    message = (
        "Faits vérifiés :\n" + json.dumps(faits_utiles, ensure_ascii=False, indent=1)
        + "\n\nParagraphes à réécrire :\n" + json.dumps(a_reecrire, ensure_ascii=False, indent=1)
    )

    client = anthropic.Anthropic()
    try:
        reponse = client.beta.messages.create(
            model=MODELE,
            max_tokens=16000,
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # bascule automatique vers un autre modèle en cas de refus
            system=CONSIGNES,
            output_config={
                "effort": "medium",
                "format": {"type": "json_schema", "schema": SCHEMA},
            },
            messages=[{"role": "user", "content": message}],
        )
    except anthropic.RateLimitError:
        print("[ia] limite de débit atteinte : récit d'origine conservé.", file=sys.stderr)
        return sections
    except anthropic.APIStatusError as e:
        print(f"[ia] erreur API {e.status_code} : récit d'origine conservé.", file=sys.stderr)
        return sections
    except anthropic.APIConnectionError:
        print("[ia] réseau indisponible : récit d'origine conservé.", file=sys.stderr)
        return sections

    if reponse.stop_reason != "end_turn":
        print(f"[ia] arrêt '{reponse.stop_reason}' : récit d'origine conservé.", file=sys.stderr)
        return sections
    texte = next((b.text for b in reponse.content if b.type == "text"), None)
    try:
        nouvelles = {s["cle"]: s["paragraphes"] for s in json.loads(texte or "")["sections"]}
    except (ValueError, KeyError, TypeError):
        return sections

    attendues = {s["cle"] for s in a_reecrire}
    if set(nouvelles) != attendues or any(not p for p in nouvelles.values()):
        print("[ia] réponse incomplète : récit d'origine conservé.", file=sys.stderr)
        return sections
    for section in sections:
        if section.cle in nouvelles:
            section.paragraphes = [p.strip() for p in nouvelles[section.cle] if p.strip()]
    return sections
