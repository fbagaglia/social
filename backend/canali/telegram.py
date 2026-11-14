"""Ponte verso la Bot API di Telegram: pubblica testo e foto in un canale.

Tutto in sola lettura finche' non si preme il tasto: `account` usa getChat (non
pubblica nulla) e serve a far vedere su quale canale si sta per scrivere.
Bot API: https://core.telegram.org/bots/api
"""

from __future__ import annotations

from pathlib import Path

from canali.form import InvioError, chiedi, corpo_multipart, tipo_immagine

BASE = "https://api.telegram.org/bot"
LIMITE_TESTO = 4096      # messaggio di solo testo
LIMITE_DIDASCALIA = 1024  # con una foto allegata, il testo diventa una didascalia


class TelegramError(Exception):
    """Credenziali mancanti o risposta non utilizzabile."""


def _credenziali(conf: dict) -> tuple[str, str]:
    dal_config = (conf.get("canali") or {}).get("telegram") or {}
    token = (dal_config.get("bot_token") or "").strip()
    chat = str(dal_config.get("chat_id") or "").strip()
    if not token:
        raise TelegramError("Manca il token del bot Telegram (Configurazione).")
    if not chat:
        raise TelegramError("Manca il destinatario Telegram, cioe' l'id del canale (Configurazione).")
    return token, chat


def _chiama(token: str, metodo: str, *, form: dict | None = None,
            corpo: bytes | None = None, content_type: str | None = None) -> dict:
    try:
        risposta = chiedi(BASE + token + "/" + metodo, form_dati=form,
                          corpo=corpo, content_type=content_type)
    except InvioError as errore:
        raise TelegramError(str(errore)) from None
    if not risposta.get("ok"):
        raise TelegramError("Telegram ha rifiutato: " + str(risposta.get("description", risposta))[:300])
    return risposta.get("result") or {}


def account(conf: dict) -> str:
    """Il canale di destinazione. Sola lettura: non pubblica niente."""
    token, chat = _credenziali(conf)
    info = _chiama(token, "getChat", form={"chat_id": chat})
    nome = info.get("title") or info.get("username") or chat
    tipo = info.get("type", "")
    return f"{nome} ({tipo}, id {chat})"


def pubblica(pubblicazione: dict, conf: dict) -> dict:
    token, chat = _credenziali(conf)
    testo = pubblicazione.get("testo", "") or ""
    allegati = [Path(p) for p in pubblicazione.get("allegati", []) if Path(p).exists()]

    if allegati:
        percorso = allegati[0]
        campi = {"chat_id": chat, "caption": testo[:LIMITE_DIDASCALIA]}
        corpo, content_type = corpo_multipart(
            campi,
            file=("photo", percorso.name, percorso.read_bytes(), tipo_immagine(percorso.name)),
        )
        messaggio = _chiama(token, "sendPhoto", corpo=corpo, content_type=content_type)
    else:
        messaggio = _chiama(token, "sendMessage", form={"chat_id": chat, "text": testo})

    identificativo = messaggio.get("message_id")
    return {
        "pubblicato": True,
        "canale": "telegram",
        "id": str(identificativo),
        "permalink": _collegamento(chat, identificativo),
        "allegati_caricati": [Path(p).name for p in allegati[:1]],
        "nota": ("inviata come didascalia della foto (tetto 1024)" if allegati
                 else "inviata come messaggio di testo"),
    }


def _collegamento(chat: str, messaggio) -> str:
    """Un indirizzo apribile quando il canale ha un nome pubblico, altrimenti vuoto."""
    if not messaggio:
        return ""
    if chat.startswith("@"):
        return f"https://t.me/{chat.lstrip('@')}/{messaggio}"
    if chat.startswith("-100"):
        return f"https://t.me/c/{chat[4:]}/{messaggio}"
    return ""
