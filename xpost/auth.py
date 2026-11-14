"""OAuth 2.0 Authorization Code + PKCE, cache del token e refresh.

Flusso (docs.x.com › fundamentals/authentication/oauth-2-0/authorization-code):
  authorize -> callback locale -> scambio del code (scade in 30 s) -> token
  -> refresh automatico quando serve.

Il token vive in .state/token.json e non viene mai stampato a schermo.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import secrets
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import config as cfg


# --------------------------------------------------------------------------- #
# HTTP minimale (solo libreria standard)
# --------------------------------------------------------------------------- #

def post_form(url: str, fields: dict[str, str], basic: tuple[str, str] | None = None) -> dict:
    """POST application/x-www-form-urlencoded -> JSON."""
    body = urllib.parse.urlencode(fields).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    if basic:
        raw = f"{basic[0]}:{basic[1]}".encode()
        headers["Authorization"] = "Basic " + base64.b64encode(raw).decode()
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode(errors="replace")
        raise cfg.ConfigError(
            f"X token endpoint: HTTP {exc.code}\n{detail}\n"
            "Se e' 401/403: controlla client_id/client_secret e che il callback "
            f"registrato sull'app sia esattamente {cfg.REDIRECT_URI}"
        ) from None
    except urllib.error.URLError as exc:
        raise cfg.ConfigError(f"Rete non raggiungibile verso {url}: {exc.reason}") from None


# --------------------------------------------------------------------------- #
# PKCE
# --------------------------------------------------------------------------- #

def _pkce_pair() -> tuple[str, str]:
    verifier = base64.urlsafe_b64encode(os.urandom(48)).rstrip(b"=").decode()
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def _authorize_url(client_id: str, state: str, challenge: str) -> str:
    query = urllib.parse.urlencode({
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": cfg.REDIRECT_URI,
        "scope": " ".join(cfg.SCOPES),
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
    })
    return f"{cfg.AUTHORIZE_URL}?{query}"


# --------------------------------------------------------------------------- #
# Callback locale
# --------------------------------------------------------------------------- #

class _Callback(BaseHTTPRequestHandler):
    """Un solo GET sulla redirect URI: cattura i parametri e chiude."""

    params: dict[str, str] = {}

    def do_GET(self) -> None:  # noqa: N802 - nome imposto da BaseHTTPRequestHandler
        query = urllib.parse.urlparse(self.path).query
        _Callback.params = dict(urllib.parse.parse_qsl(query))
        granted = "code" in _Callback.params
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        if granted:
            page = "<h2>Autorizzazione completata.</h2><p>Puoi chiudere questa scheda.</p>"
        else:
            page = ("<h2>Autorizzazione rifiutata.</h2>"
                    "<p>Torna al terminale per il dettaglio.</p>")
        self.wfile.write(page.encode())

    def log_message(self, *args) -> None:  # silenzio: non sporcare la CLI
        pass


def _await_callback(timeout: int = 300) -> dict[str, str]:
    parsed = urllib.parse.urlparse(cfg.REDIRECT_URI)
    host, port = parsed.hostname or "localhost", parsed.port or 80
    try:
        server = HTTPServer((host, port), _Callback)
    except OSError as exc:
        raise cfg.ConfigError(
            f"Porta {port} occupata ({exc}). Chiudi chi la usa o cambia "
            "XPOST_REDIRECT_URI (ricordando di registrare il nuovo callback sull'app)."
        ) from None
    server.timeout = timeout
    _Callback.params = {}
    server.handle_request()
    server.server_close()
    return _Callback.params


# --------------------------------------------------------------------------- #
# Token: login, salvataggio, refresh
# --------------------------------------------------------------------------- #

def _store(payload: dict) -> None:
    cfg.ensure_dirs()
    payload = dict(payload)
    if "expires_in" in payload:
        payload["expires_at"] = int(time.time()) + int(payload["expires_in"]) - 60
    cfg.TOKEN_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    try:
        os.chmod(cfg.TOKEN_FILE, 0o600)
    except OSError:
        pass


def _load() -> dict:
    if not cfg.TOKEN_FILE.exists():
        raise cfg.ConfigError(
            "Nessun token salvato. Lancia prima:  python -m xpost login"
        )
    return json.loads(cfg.TOKEN_FILE.read_text(encoding="utf-8"))


def login(open_browser: bool = True) -> str:
    """Esegue il flusso completo e salva il token. Ritorna l'access token."""
    client_id, client_secret = cfg.client_credentials()
    verifier, challenge = _pkce_pair()
    state = secrets.token_urlsafe(32)
    url = _authorize_url(client_id, state, challenge)

    print("\nApro il browser per l'autorizzazione su X.")
    print("ATTENZIONE: viene autorizzato l'account con cui sei loggato nel browser.")
    print("Se pubblichi per un altro account, cambia account PRIMA di continuare.\n")
    print("Se il browser non si apre, incolla questo indirizzo:\n" + url + "\n")
    if open_browser:
        webbrowser.open(url)

    params = _await_callback()
    if not params:
        raise cfg.ConfigError("Nessuna risposta dal callback: tempo scaduto.")
    if params.get("error"):
        raise cfg.ConfigError(f"X ha rifiutato l'autorizzazione: {params.get('error')}")
    if params.get("state") != state:
        raise cfg.ConfigError("state non corrispondente: possibile CSRF, autorizzazione annullata.")
    code = params.get("code")
    if not code:
        raise cfg.ConfigError(f"Callback senza 'code': {params}")

    # Il code scade in 30 secondi: si scambia subito.
    fields = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": cfg.REDIRECT_URI,
        "code_verifier": verifier,
    }
    basic = None
    if client_secret:
        # Client confidenziale: Basic auth, client_id NON nel body.
        basic = (client_id, client_secret)
    else:
        # Client pubblico: client_id nel body.
        fields["client_id"] = client_id

    payload = post_form(cfg.TOKEN_URL, fields, basic=basic)
    if "access_token" not in payload:
        raise cfg.ConfigError(f"Risposta inattesa dal token endpoint: {payload}")
    if "refresh_token" not in payload:
        print("Nota: nessun refresh token ricevuto — manca lo scope offline.access?")
    _store(payload)
    print("Token salvato in " + str(cfg.TOKEN_FILE.relative_to(cfg.ROOT)))
    return payload["access_token"]


def access_token() -> str:
    """Token valido, rinnovato se necessario."""
    data = _load()
    if data.get("expires_at", 0) > time.time():
        return data["access_token"]
    refresh = data.get("refresh_token")
    if not refresh:
        raise cfg.ConfigError("Token scaduto e nessun refresh token: rifai  python -m xpost login")
    client_id, client_secret = cfg.client_credentials()
    fields = {"grant_type": "refresh_token", "refresh_token": refresh}
    basic = None
    if client_secret:
        basic = (client_id, client_secret)
    else:
        fields["client_id"] = client_id
    payload = post_form(cfg.TOKEN_URL, fields, basic=basic)
    if "access_token" not in payload:
        raise cfg.ConfigError(f"Refresh fallito: {payload}\nRifai  python -m xpost login")
    # Alcuni refresh non rimandano il refresh_token: si conserva quello vecchio.
    payload.setdefault("refresh_token", refresh)
    _store(payload)
    return payload["access_token"]
