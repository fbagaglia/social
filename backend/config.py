"""Configurazione di Social Studio: lettura, fusione, mascheramento dei segreti.

Nessun segreto esce mai dall'app: la GET li azzera e dice solo se ci sono.
La POST fonde col file esistente, cosi' un campo vuoto significa "non cambiare".
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
FILE_CONFIG = RADICE / "config.json"
ESEMPIO = RADICE / "config.example.json"
CARTELLA_DATA = RADICE / "data"
CARTELLA_ALLEGATI = CARTELLA_DATA / "allegati"
CARTELLA_BOZZE = CARTELLA_DATA / "bozze"
CARTELLA_LOG = RADICE / "logs"

# Campi che non si restituiscono mai in chiaro (percorso puntato dentro il config).
SEGRETI = (
    "llm.orKey",
    "ricerca.firecrawlKey",
    "ricerca.braveKey",
    "canali.x.client_secret",
    "canali.linkedin.access_token",
    "canali.mastodon.access_token",
    "canali.bluesky.app_password",
    "canali.telegram.bot_token",
)

PREDEFINITO = {
    "_nota": "Config di Social Studio. GITIGNORED: non finisce mai in git e non si stampa in chat.",
    "llm": {
        "orKey": "",
        "orModel": "openai/gpt-4o-mini",
        "orModelAdatta": "",
        "orUrl": "https://openrouter.ai/api/v1",
        "temperature": 0.7,
    },
    "ricerca": {"firecrawlKey": "", "braveKey": "", "attiva": True},
    "canali": {
        "x": {
            "client_id": "",
            "client_secret": "",
            # "compositore" = non si usa l'API (a pagamento), si apre il compositore.
            "modalita": "compositore",
        },
        "linkedin": {"access_token": "", "autore": ""},
        "mastodon": {"istanza": "", "access_token": ""},
        "bluesky": {"handle": "", "app_password": ""},
        "telegram": {"bot_token": "", "chat_id": ""},
    },
    "pubblicazione": {"lingua": "it", "firma": ""},
}


def assicura_cartelle() -> None:
    for cartella in (CARTELLA_DATA, CARTELLA_ALLEGATI, CARTELLA_BOZZE, CARTELLA_LOG):
        cartella.mkdir(parents=True, exist_ok=True)


# --------------------------------------------------------------------------- #
# Percorsi puntati ("llm.orKey")
# --------------------------------------------------------------------------- #

def leggi_puntato(dati: dict, percorso: str, predefinito=None):
    nodo = dati
    for pezzo in percorso.split("."):
        if not isinstance(nodo, dict) or pezzo not in nodo:
            return predefinito
        nodo = nodo[pezzo]
    return nodo


def scrivi_puntato(dati: dict, percorso: str, valore) -> None:
    pezzi = percorso.split(".")
    nodo = dati
    for pezzo in pezzi[:-1]:
        nodo = nodo.setdefault(pezzo, {})
    nodo[pezzi[-1]] = valore


def fondi(base: dict, nuovo: dict) -> dict:
    """Fusione profonda: i dizionari si uniscono, gli altri valori si sostituiscono."""
    for chiave, valore in nuovo.items():
        if isinstance(valore, dict) and isinstance(base.get(chiave), dict):
            fondi(base[chiave], valore)
        else:
            base[chiave] = valore
    return base


# --------------------------------------------------------------------------- #

def leggi() -> dict:
    """Config completa, con i valori predefiniti per cio' che manca."""
    dati = json.loads(json.dumps(PREDEFINITO))  # copia profonda
    if FILE_CONFIG.exists():
        fondi(dati, json.loads(FILE_CONFIG.read_text(encoding="utf-8")))
    return dati


def leggi_con_segreti() -> dict:
    """Config completa, segreti in chiaro. Uso interno: non finisce mai in una risposta."""
    return leggi()


def leggi_mascherato() -> dict:
    """Config per l'interfaccia: i segreti diventano stringa vuota + elenco di quali ci sono."""
    dati = leggi()
    presenti = {}
    for percorso in SEGRETI:
        valore = leggi_puntato(dati, percorso, "")
        presenti[percorso] = bool(valore)
        scrivi_puntato(dati, percorso, "")
    dati["_segreti_presenti"] = presenti
    return dati


def scrivi(nuovo: dict) -> dict:
    """Fonde il nuovo con il file esistente e salva. Campo segreto vuoto = non cambiare."""
    attuale = leggi()
    for percorso in SEGRETI:
        if percorso in _percorsi_presenti(nuovo) and not leggi_puntato(nuovo, percorso):
            scrivi_puntato(nuovo, percorso, leggi_puntato(attuale, percorso, ""))
    fondi(attuale, nuovo)
    assicura_cartelle()
    if FILE_CONFIG.exists():
        shutil.copy2(FILE_CONFIG, FILE_CONFIG.with_suffix(".json.bak"))
    FILE_CONFIG.write_text(json.dumps(attuale, indent=2, ensure_ascii=False), encoding="utf-8")
    return attuale


def _percorsi_presenti(dati: dict) -> set[str]:
    """Tutti i percorsi puntati che esistono davvero nell'oggetto ricevuto."""
    trovati: set[str] = set()

    def scorri(nodo, prefisso=""):
        if isinstance(nodo, dict):
            for chiave, valore in nodo.items():
                cammino = f"{prefisso}.{chiave}" if prefisso else chiave
                trovati.add(cammino)
                scorri(valore, cammino)

    scorri(dati)
    return trovati
