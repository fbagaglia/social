"""Ponte verso la REST API di Mastodon: pubblica un post con immagine.

L'istanza e il token stanno in Configurazione. `account` usa verify_credentials:
e' una lettura, serve a far vedere su quale account si sta per scrivere.
API: https://docs.joinmastodon.org/methods/statuses/
"""

from __future__ import annotations

from pathlib import Path

from canali.form import InvioError, chiedi, corpo_multipart, tipo_immagine


class MastodonError(Exception):
    """Credenziali mancanti o risposta non utilizzabile."""


def _credenziali(conf: dict) -> tuple[str, str]:
    dal_config = (conf.get("canali") or {}).get("mastodon") or {}
    token = (dal_config.get("access_token") or "").strip()
    istanza = (dal_config.get("istanza") or "").strip().rstrip("/")
    if not istanza:
        raise MastodonError("Manca l'indirizzo dell'istanza Mastodon (Configurazione).")
    if not token:
        raise MastodonError("Manca il token di accesso di Mastodon (Configurazione).")
    if not istanza.startswith("http"):
        istanza = "https://" + istanza
    return istanza, token


def account(conf: dict) -> str:
    """L'account su cui si pubblica. Sola lettura: non pubblica niente."""
    istanza, token = _credenziali(conf)
    try:
        profilo = chiedi(istanza + "/api/v1/accounts/verify_credentials", token_bearer=token)
    except InvioError as errore:
        raise MastodonError(str(errore)) from None
    if not profilo.get("username"):
        raise MastodonError("Mastodon non ha riconosciuto il token: " + str(profilo)[:200])
    return (f"@{profilo.get('username')} su {istanza.replace('https://', '')} "
            f"({profilo.get('followers_count', 0)} follower)")


def _carica_immagine(istanza: str, token: str, percorso: Path) -> str:
    corpo, content_type = corpo_multipart(
        {"description": percorso.stem[:400]},
        file=("file", percorso.name, percorso.read_bytes(), tipo_immagine(percorso.name)),
    )
    try:
        risposta = chiedi(istanza + "/api/v1/media", corpo=corpo,
                          content_type=content_type, token_bearer=token)
    except InvioError as errore:
        raise MastodonError("Caricamento dell'immagine: " + str(errore)) from None
    identificativo = risposta.get("id")
    if not identificativo:
        raise MastodonError("Mastodon non ha restituito l'id dell'immagine: " + str(risposta)[:200])
    return str(identificativo)


def pubblica(pubblicazione: dict, conf: dict) -> dict:
    istanza, token = _credenziali(conf)
    testo = pubblicazione.get("testo", "") or ""
    allegati = [Path(p) for p in pubblicazione.get("allegati", []) if Path(p).exists()]

    caricati = [_carica_immagine(istanza, token, p) for p in allegati[:4]]
    campi: dict = {"status": testo}
    if caricati:
        campi["media_ids[]"] = caricati

    try:
        stato = chiedi(istanza + "/api/v1/statuses", form_dati=campi, token_bearer=token)
    except InvioError as errore:
        raise MastodonError(str(errore)) from None

    if not stato.get("id"):
        raise MastodonError("Il post non e' stato creato: " + str(stato)[:200])
    return {
        "pubblicato": True,
        "canale": "mastodon",
        "id": str(stato.get("id")),
        "permalink": stato.get("url") or "",
        "allegati_caricati": [Path(p).name for p in allegati[:4]],
        "nota": "immagini caricate prima del post, nell'ordine dato",
    }
