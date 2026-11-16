"""Petit client HTTP sans dépendance (urllib) avec relances et User-Agent explicite."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

# Wikimedia et d'autres services publics exigent un User-Agent descriptif.
USER_AGENT = "maison-histoire/0.1 (+https://github.com/haynbroit-alt/Alll)"

_RELANCABLES = {429, 500, 502, 503, 504}


class ErreurHTTP(Exception):
    """Échec définitif d'une requête HTTP (après relances)."""

    def __init__(self, url: str, statut: int | None, message: str):
        super().__init__(f"{statut or 'réseau'} sur {url}: {message}")
        self.url = url
        self.statut = statut


def construire_url(url: str, params: dict[str, Any] | None = None) -> str:
    if not params:
        return url
    propres = {k: v for k, v in params.items() if v is not None}
    separateur = "&" if "?" in url else "?"
    return url + separateur + urllib.parse.urlencode(propres)


def get(
    url: str,
    params: dict[str, Any] | None = None,
    *,
    timeout: float = 30,
    relances: int = 3,
    pause: float = 1.5,
) -> tuple[bytes, str]:
    """GET avec relances sur 429/5xx/erreurs réseau. Renvoie (contenu, content-type)."""
    complet = construire_url(url, params)
    derniere: ErreurHTTP | None = None
    for essai in range(relances + 1):
        requete = urllib.request.Request(complet, headers={"User-Agent": USER_AGENT})
        attente = pause * (2**essai)
        try:
            with urllib.request.urlopen(requete, timeout=timeout) as reponse:
                return reponse.read(), reponse.headers.get("Content-Type", "")
        except urllib.error.HTTPError as e:
            corps = e.read()[:300].decode("utf-8", "replace")
            derniere = ErreurHTTP(complet, e.code, corps)
            if e.code not in _RELANCABLES:
                raise derniere from e
            attente = max(attente, _retry_after(e.headers.get("Retry-After")))
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            derniere = ErreurHTTP(complet, None, str(e))
        if essai < relances:
            time.sleep(min(attente, 30))
    assert derniere is not None
    raise derniere


def _retry_after(valeur: str | None) -> float:
    try:
        return float(valeur) if valeur else 0.0
    except ValueError:
        return 0.0


def get_json(url: str, params: dict[str, Any] | None = None, **kwargs: Any) -> Any:
    contenu, _ = get(url, params, **kwargs)
    return json.loads(contenu.decode("utf-8"))
