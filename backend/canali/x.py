"""Ponte verso il motore X del progetto: il pacchetto `xpost`.

L'app non reimplementa OAuth ne' l'upload: usa `xpost`, che e' gia' collaudato anche
come riga di comando. Qui si traducono soltanto la configurazione dell'app e le
eccezioni del motore (`xpost` esce con `SystemExit` per dire cosa manca: va fermato
qui, o porterebbe giu' il servizio).
"""

from __future__ import annotations

import os
import sys
import threading
from pathlib import Path

import config as cfg

RADICE = Path(__file__).resolve().parents[2]
if str(RADICE) not in sys.path:
    sys.path.insert(0, str(RADICE))

from xpost import api as xapi          # noqa: E402
from xpost import auth as xauth        # noqa: E402
from xpost import config as xconf      # noqa: E402

# Un solo posto per lo stato dell'app: i token di X vivono in data/x/.
xconf.STATE = cfg.CARTELLA_DATA / "x"
xconf.CLIENT_FILE = xconf.STATE / "client.json"
xconf.TOKEN_FILE = xconf.STATE / "token.json"

LOGIN_IN_CORSO = threading.Event()
ESITO_LOGIN: dict = {"esito": None, "messaggio": ""}


def _config_x(conf: dict) -> tuple[str, str]:
    dati = (conf.get("canali") or {}).get("x") or {}
    client_id = (dati.get("client_id") or "").strip()
    client_secret = (dati.get("client_secret") or "").strip()
    if not client_id:
        raise xconf.ConfigError(
            "Manca il Client ID dell'app X. Si imposta in Configurazione: "
            "crea l'app su https://console.x.com con OAuth 2.0 e callback "
            + xconf.REDIRECT_URI
        )
    os.environ["X_CLIENT_ID"] = client_id
    if client_secret:
        os.environ["X_CLIENT_SECRET"] = client_secret
    else:
        os.environ.pop("X_CLIENT_SECRET", None)
    return client_id, client_secret


def account(conf: dict) -> str:
    """Account su cui stiamo operando. Solleva se non c'e' un token valido."""
    _config_x(conf)
    io = xapi.get_me(xauth.access_token())
    return f"@{io.get('username')} ({io.get('name')})"


def stato_token(conf: dict) -> dict:
    """Stato del collegamento, senza mai sollevare: l'interfaccia deve poter disegnare."""
    try:
        _config_x(conf)
    except BaseException as errore:
        return {"collegato": False, "account": None, "motivo": str(errore),
                "in_corso": LOGIN_IN_CORSO.is_set()}
    try:
        return {"collegato": True, "account": account(conf), "motivo": "",
                "in_corso": LOGIN_IN_CORSO.is_set()}
    except BaseException as errore:
        return {"collegato": False, "account": None, "motivo": str(errore),
                "in_corso": LOGIN_IN_CORSO.is_set()}


def avvia_login(conf: dict) -> dict:
    """Apre il browser e aspetta il callback in un filo separato (blocca a lungo)."""
    if LOGIN_IN_CORSO.is_set():
        return {"avviato": False, "motivo": "un accesso e' gia' in corso"}
    try:
        _config_x(conf)
    except BaseException as errore:
        return {"avviato": False, "motivo": str(errore)}

    ESITO_LOGIN.update({"esito": None, "messaggio": ""})
    LOGIN_IN_CORSO.set()

    def lavora():
        try:
            xauth.login()
            ESITO_LOGIN.update({"esito": "ok", "messaggio": "accesso completato"})
        except BaseException as errore:  # SystemExit compreso
            ESITO_LOGIN.update({"esito": "errore", "messaggio": str(errore)})
        finally:
            LOGIN_IN_CORSO.clear()

    threading.Thread(target=lavora, daemon=True).start()
    return {"avviato": True,
            "messaggio": ("Si e' aperto il browser: completa l'accesso su X. "
                          "Viene autorizzato l'account con cui sei loggato NEL BROWSER.")}


COSTO_TESTO_O_MEDIA = xconf.COST_TEXT_OR_MEDIA_USD


def costo_stimato(testo: str) -> float:
    contiene_url = False
    for pezzo in (testo or "").split():
        if pezzo.startswith("http://") or pezzo.startswith("https://"):
            contiene_url = True
            break
    return xconf.COST_WITH_URL_USD if contiene_url else xconf.COST_TEXT_OR_MEDIA_USD


def pubblica(pubblicazione: dict, conf: dict) -> dict:
    """Carica gli allegati e crea il post. Ritorna l'esito con il collegamento."""
    _config_x(conf)
    token = xauth.access_token()
    allegati = [Path(p) for p in pubblicazione.get("allegati", [])]

    identificativi = []
    for percorso in allegati:
        identificativi.append(xapi.upload_image(percorso, token))

    esito = xapi.create_post(
        pubblicazione.get("testo", ""),
        token,
        media_ids=identificativi or None,
        reply_to=pubblicazione.get("reply_to") or None,
    )
    return {
        "pubblicato": True,
        "canale": "x",
        "id": esito["id"],
        "permalink": esito["permalink"],
        "allegati_caricati": identificativi,
        "costo_stimato_usd": costo_stimato(pubblicazione.get("testo", "")),
    }
