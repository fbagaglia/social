"""Caricare un'immagine su umanesimodigitale.info.

Caricare un file sono **due passi, non uno**: `wp_upload_request` restituisce un
indirizzo monouso, e il file si consuma subito con una POST multipart. L'indirizzo
**scade in cinque minuti** e la scadenza non da' un errore parlante — la risposta
torna **vuota**. Quindi: un corpo vuoto e' un fallimento, non un successo silenzioso.

L'`alt` si scrive **qui**, insieme al caricamento: non dopo, e non mai.
"""

from __future__ import annotations

import json
import mimetypes
import pathlib
import re
import urllib.error
import urllib.request
import uuid

from . import mcp as _mcp

TIPI = {
    ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png",
    ".webp": "image/webp", ".gif": "image/gif", ".avif": "image/avif",
    ".mp4": "video/mp4", ".mp3": "audio/mpeg", ".pdf": "application/pdf",
}


class ErroreMedia(Exception):
    """Il caricamento non e' riuscito: il motivo e' in chiaro."""


def tipo_di(nome: str) -> str:
    suffisso = pathlib.Path(nome).suffix.lower()
    return TIPI.get(suffisso) or mimetypes.guess_type(nome)[0] or "application/octet-stream"


def _multipart(nome_file: str, contenuto: bytes, tipo: str) -> tuple[bytes, str]:
    """Il corpo della POST, scritto a mano: nessuna dipendenza oltre la libreria standard."""
    confine = "----SocialStudio" + uuid.uuid4().hex
    pezzi = [
        f'--{confine}\r\nContent-Disposition: form-data; name="file"; '
        f'filename="{nome_file}"\r\nContent-Type: {tipo}\r\n\r\n'.encode("utf-8"),
        contenuto,
        f"\r\n--{confine}--\r\n".encode("utf-8"),
    ]
    return b"".join(pezzi), f"multipart/form-data; boundary={confine}"


def carica(cliente: _mcp.MCP, percorso: pathlib.Path | str, *, titolo: str,
           alt: str, descrizione: str = "", tentativi: int = 2) -> dict:
    """Carica un file e torna {'id': N, 'url': '...'}.

    L'`alt` va scritto guardando l'immagine, non deducendolo dalla descrizione: e' la
    ragione per cui lo chiede come argomento invece di inventarlo.
    """
    percorso = pathlib.Path(percorso)
    if not percorso.is_file():
        raise ErroreMedia(f"file non trovato: {percorso}")
    contenuto = percorso.read_bytes()
    tipo = tipo_di(percorso.name)

    ultimo: str = ""
    for tentativo in range(1, tentativi + 1):
        indirizzo = cliente.chiama("wp_upload_request", {
            "filename": percorso.name,
            # il nome leggibile: la libreria media non si riempie di nomi da generatore
            "title": titolo or percorso.stem,
            "alt": alt,
            "description": descrizione,
        })
        if not isinstance(indirizzo, str) or not indirizzo.startswith("http"):
            raise ErroreMedia(
                f"il sito non ha dato un indirizzo di caricamento: {str(indirizzo)[:200]}"
            )

        corpo, tipo_contenuto = _multipart(percorso.name, contenuto, tipo)
        richiesta = urllib.request.Request(
            indirizzo, data=corpo, method="POST",
            headers={"Content-Type": tipo_contenuto, "Content-Length": str(len(corpo))},
        )
        try:
            with urllib.request.urlopen(richiesta, timeout=180) as risposta:
                grezzo = risposta.read().decode("utf-8", "ignore")
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as errore:
            ultimo = f"{type(errore).__name__}: {errore}"
            continue

        if not grezzo.strip():
            # indirizzo scaduto: si richiede e si ripete, non si dichiara riuscito
            ultimo = "risposta vuota (l'indirizzo monouso e' scaduto)"
            continue
        try:
            esito = json.loads(grezzo)
        except json.JSONDecodeError:
            ultimo = f"risposta non leggibile: {grezzo[:200]}"
            continue
        if not esito.get("success") or not esito.get("attachment_id"):
            ultimo = f"il sito ha risposto: {grezzo[:250]}"
            continue

        return {
            "id": int(esito["attachment_id"]),
            "url": esito.get("url", ""),
            "alt": alt,
            "titolo": titolo or percorso.stem,
            "mime": tipo,
            "file": percorso.name,
        }

    raise ErroreMedia(f"caricamento non riuscito dopo {tentativi} tentativi — {ultimo}")


def dimensioni(percorso: pathlib.Path | str) -> tuple[int, int]:
    """Le misure reali del file, per l'oggetto dell'allegato nell'editor.

    Si leggono dall'intestazione del file, senza dipendere da Pillow: PNG, JPEG, WEBP.
    """
    percorso = pathlib.Path(percorso)
    dati = percorso.read_bytes()[:65536]
    if dati[:8] == b"\x89PNG\r\n\x1a\n":
        return (int.from_bytes(dati[16:20], "big"), int.from_bytes(dati[20:24], "big"))
    if dati[:2] == b"\xff\xd8":
        i = 2
        while i < len(dati) - 9:
            if dati[i] != 0xFF:
                i += 1
                continue
            marcatore = dati[i + 1]
            if marcatore in (0xC0, 0xC1, 0xC2, 0xC3):
                altezza = int.from_bytes(dati[i + 5:i + 7], "big")
                larghezza = int.from_bytes(dati[i + 7:i + 9], "big")
                return (larghezza, altezza)
            i += 2 + int.from_bytes(dati[i + 2:i + 4], "big")
    trovato = re.search(rb"VP8X(....)", dati)
    if trovato:
        b = dati[trovato.end() - 4:trovato.end()]
        return (int.from_bytes(b[1:4] + b"\x00", "little") + 1,
                int.from_bytes(b[4:7] + b"\x00", "little") + 1)
    return (0, 0)
