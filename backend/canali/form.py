"""Invio HTTP e corpi multipart, in un posto solo.

Le due reti collegate (Telegram e Mastodon) caricano un'immagine con lo stesso
schema: campi di testo piu' un file. Scritto una volta, usato da entrambe.

Niente backslash nel sorgente: i fine-riga del multipart si costruiscono con chr(),
cosi' il file sopravvive a qualunque passaggio di scrittura.
"""

from __future__ import annotations

import json
import secrets
import urllib.error
import urllib.parse
import urllib.request

CRLF = chr(13) + chr(10)


class InvioError(Exception):
    """Invio non riuscito, con il motivo che la rete ha restituito."""


def corpo_multipart(campi: dict, file: tuple | None = None) -> tuple[bytes, str]:
    """(corpo, content_type). `file` = (nome_del_campo, nome_file, contenuto, tipo)."""
    confine = "----socialstudio" + secrets.token_hex(16)
    parti = bytearray()
    for chiave, valore in campi.items():
        parti += (
            "--" + confine + CRLF
            + 'Content-Disposition: form-data; name="' + str(chiave) + '"' + CRLF
            + CRLF + str(valore) + CRLF
        ).encode()
    if file:
        nome_campo, nome_file, contenuto, tipo = file
        parti += (
            "--" + confine + CRLF
            + 'Content-Disposition: form-data; name="' + nome_campo + '"; filename="'
            + nome_file + '"' + CRLF
            + "Content-Type: " + tipo + CRLF + CRLF
        ).encode()
        parti += contenuto + CRLF
    parti += ("--" + confine + "--" + CRLF).encode()
    return bytes(parti), "multipart/form-data; boundary=" + confine


def chiedi(url: str, *, json_dati: dict | None = None, form_dati: dict | None = None,
           corpo: bytes | None = None, content_type: str | None = None,
           token_bearer: str | None = None, timeout: int = 90) -> dict:
    """Una chiamata, una risposta JSON. `InvioError` porta il corpo dell'errore."""
    intestazioni = {"User-Agent": "SocialStudio/0.1"}
    dati = corpo
    if json_dati is not None:
        dati = json.dumps(json_dati).encode()
        content_type = "application/json"
    elif form_dati is not None:
        dati = urllib.parse.urlencode(form_dati, doseq=True).encode()
        content_type = "application/x-www-form-urlencoded"
    if content_type:
        intestazioni["Content-Type"] = content_type
    if token_bearer:
        intestazioni["Authorization"] = "Bearer " + token_bearer

    richiesta = urllib.request.Request(url, data=dati, headers=intestazioni,
                                       method="POST" if dati is not None else "GET")
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            grezzo = risposta.read().decode(errors="replace")
    except urllib.error.HTTPError as errore:
        dettaglio = errore.read(600).decode(errors="replace")
        raise InvioError(f"HTTP {errore.code} da {url}: {dettaglio}") from None
    except urllib.error.URLError as errore:
        raise InvioError(f"{url} non raggiungibile: {errore.reason}") from None
    if not grezzo.strip():
        return {}
    try:
        return json.loads(grezzo)
    except json.JSONDecodeError:
        raise InvioError(f"risposta non leggibile da {url}: {grezzo[:200]}") from None


def tipo_immagine(nome: str) -> str:
    estensione = "." + nome.rsplit(".", 1)[-1].lower() if "." in nome else ""
    return {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
        ".gif": "image/gif",
    }.get(estensione, "application/octet-stream")
