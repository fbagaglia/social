"""Percorsi, credenziali e costanti della X API v2.

Nessun segreto vive nel codice ne' nella chat: le credenziali arrivano
dall'ambiente oppure da .state/client.json, che sta fuori dal controllo di
versione. I token stanno in .state/ e non vengono mai stampati.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUTBOX = ROOT / "outbox"
STATE = ROOT / ".state"
TOKEN_FILE = STATE / "token.json"
CLIENT_FILE = STATE / "client.json"

AUTHORIZE_URL = "https://x.com/i/oauth2/authorize"
TOKEN_URL = "https://api.x.com/2/oauth2/token"
API_BASE = "https://api.x.com/2"
INTENT_URL = "https://x.com/intent/post"

# Deve combaciare ESATTAMENTE con un callback registrato sull'app X.
REDIRECT_URI = os.environ.get("XPOST_REDIRECT_URI", "http://localhost:8080/callback")

# offline.access e' obbligatorio: senza, il token vive 2 ore e non c'e' refresh.
SCOPES = ("tweet.read", "tweet.write", "users.read", "media.write", "offline.access")

# Limiti verificati su docs.x.com (POST /2/media/upload e POST /2/tweets).
MAX_TEXT_CHARS = 280            # account senza X Premium
MAX_IMAGES_PER_POST = 4
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_GIF_BYTES = 15 * 1024 * 1024
IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".gif", ".webp"}

# Stima di costo (analisi di terze parti, X non pubblica un listino unico).
COST_TEXT_OR_MEDIA_USD = 0.015
COST_WITH_URL_USD = 0.20


class ConfigError(SystemExit):
    """Errore di configurazione con messaggio gia' pronto per l'utente."""


def ensure_dirs() -> None:
    OUTBOX.mkdir(parents=True, exist_ok=True)
    STATE.mkdir(parents=True, exist_ok=True)


def client_credentials() -> tuple[str, str | None]:
    """(client_id, client_secret | None).

    Priorita': variabili d'ambiente, poi .state/client.json.
    Il secret e' None per i client pubblici (Native App / Single page App).
    """
    cid = os.environ.get("X_CLIENT_ID")
    secret = os.environ.get("X_CLIENT_SECRET")
    if not cid and CLIENT_FILE.exists():
        data = json.loads(CLIENT_FILE.read_text(encoding="utf-8"))
        cid = cid or data.get("client_id")
        secret = secret or data.get("client_secret")
    if not cid:
        raise ConfigError(
            "Mancano le credenziali dell'app X.\n"
            "  1. crea l'app su https://console.x.com con OAuth 2.0 attivo\n"
            "  2. registra il callback: " + REDIRECT_URI + "\n"
            "  3. poi:  python -m xpost login --set-client\n"
            "     (oppure esporta X_CLIENT_ID e X_CLIENT_SECRET)"
        )
    return cid, secret


def save_client(client_id: str, client_secret: str | None) -> Path:
    """Scrive le credenziali dell'app in .state/client.json (permessi ristretti dove possibile)."""
    ensure_dirs()
    payload = {"client_id": client_id}
    if client_secret:
        payload["client_secret"] = client_secret
    CLIENT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(CLIENT_FILE, 0o600)
    except OSError:
        pass  # su Windows il chmod POSIX e' un no-op: la cartella resta fuori da git
    return CLIENT_FILE
