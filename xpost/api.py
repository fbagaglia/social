"""Chiamate alla X API v2: upload immagine e creazione del post.

Endpoint verificati sulla specifica OpenAPI v2.174 (docs.x.com):
  POST /2/media/upload   scope media.write
  POST /2/tweets         scope tweet.write (+ tweet.read, users.read)
"""

from __future__ import annotations

import json
import mimetypes
import secrets
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from . import config as cfg


class ApiError(SystemExit):
    """Errore restituito da X, con corpo della risposta."""


def _request(method: str, path: str, token: str, *,
             json_body: dict | None = None,
             data: bytes | None = None,
             content_type: str | None = None) -> dict:
    url = f"{cfg.API_BASE}{path}"
    headers = {"Authorization": f"Bearer {token}"}
    if json_body is not None:
        data = json.dumps(json_body).encode()
        content_type = "application/json"
    if content_type:
        headers["Content-Type"] = content_type
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = resp.read().decode()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise ApiError(_explain(exc.code, url, detail)) from None
    except urllib.error.URLError as exc:
        raise ApiError(f"Rete non raggiungibile verso {url}: {exc.reason}") from None


def _explain(status: int, url: str, detail: str) -> str:
    hints = {
        401: "Token non valido o scaduto: rifai  python -m xpost login",
        403: "Permesso negato. Controlla gli scope dell'app (tweet.write, media.write) "
             "e i limiti dell'account (es. video troppo lungo per un account non Premium).",
        429: "Rate limit o credito esaurito: aspetta e riprova; verifica il credito "
             "sul portale sviluppatori.",
    }
    tail = hints.get(status, "")
    return f"X API: HTTP {status} su {url}\n{detail}" + (f"\n{tail}" if tail else "")


# --------------------------------------------------------------------------- #
# Immagini
# --------------------------------------------------------------------------- #

def media_category_for(path: Path) -> str:
    return "tweet_gif" if path.suffix.lower() == ".gif" else "tweet_image"


def check_image(path: Path) -> None:
    """Fallisce subito, con numeri alla mano, invece di farlo fare a X."""
    if not path.exists():
        raise ApiError(f"Immagine inesistente: {path}")
    suffix = path.suffix.lower()
    if suffix not in cfg.IMAGE_SUFFIXES:
        allowed = ", ".join(sorted(cfg.IMAGE_SUFFIXES))
        raise ApiError(f"Formato non ammesso da X: {suffix}. Ammessi: {allowed}")
    limit = cfg.MAX_GIF_BYTES if suffix == ".gif" else cfg.MAX_IMAGE_BYTES
    size = path.stat().st_size
    if size > limit:
        raise ApiError(
            f"{path.name} pesa {size / 1048576:.2f} MB, oltre il limite X di "
            f"{limit / 1048576:.0f} MB per {suffix}."
        )


def upload_image(path: Path, token: str) -> str:
    """Carica un'immagine e ritorna il media_id."""
    check_image(path)
    boundary = "----xpost" + secrets.token_hex(16)
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body = bytearray()
    for name, value in (("media_category", media_category_for(path)),):
        body += (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'
        ).encode()
    body += (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="media"; filename="{path.name}"\r\n'
        f"Content-Type: {ctype}\r\n\r\n"
    ).encode()
    body += path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    result = _request(
        "POST", "/media/upload", token,
        data=bytes(body), content_type=f"multipart/form-data; boundary={boundary}",
    )
    media_id = (result.get("data") or {}).get("id")
    if not media_id:
        raise ApiError(f"Upload senza media_id: {result}")
    return media_id


# --------------------------------------------------------------------------- #
# Post
# --------------------------------------------------------------------------- #

def create_post(text: str, token: str, *, media_ids: list[str] | None = None,
                reply_to: str | None = None) -> dict:
    """Crea il post. Ritorna {'id':..., 'permalink':...}."""
    payload: dict = {"text": text}
    if media_ids:
        payload["media"] = {"media_ids": media_ids}
    if reply_to:
        payload["reply"] = {"in_reply_to_tweet_id": reply_to}
    result = _request("POST", "/tweets", token, json_body=payload)
    data = result.get("data") or {}
    post_id = data.get("id")
    if not post_id:
        raise ApiError(f"Post non creato: {result}")
    return {"id": post_id, "permalink": f"https://x.com/i/web/status/{post_id}"}


def get_me(token: str) -> dict:
    result = _request("GET", "/users/me?user.fields=username,name,verified", token)
    data = result.get("data") or {}
    if not data:
        raise ApiError(f"/users/me non ha restituito l'utente: {result}")
    return data
