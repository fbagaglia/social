"""Il canale verso umanesimodigitale.info: MCP su HTTP, solo libreria standard.

Il sito espone un server MCP (plugin AI Engine). Il token vive nella configurazione
dell'app e, se non c'e', nel file `.env` di Hermes: non viene mai stampato, mai
restituito da una rotta, mai scritto nei log.

Il sito ogni tanto risponde 500 anche quando il canale e' sano: per questo ogni
chiamata ritenta. Un sussulto del sito non deve sembrare un guasto del canale.
"""

from __future__ import annotations

import json
import os
import pathlib
import time
import urllib.error
import urllib.request

ENDPOINT = "https://umanesimodigitale.info/wp-json/mcp/v1/"
VARIABILE = "WP_UMANESIMO_MCP_TOKEN"
SITO = "umanesimodigitale.info"
TENTATIVI = 4


class ErroreMCP(Exception):
    """Il sito non ha risposto o ha rifiutato la chiamata: il motivo e' in chiaro."""


# --------------------------------------------------------------------------- #
# Il token
# --------------------------------------------------------------------------- #

def _dal_file_env() -> str:
    for percorso in (pathlib.Path(os.environ.get("LOCALAPPDATA", "")) / "hermes" / ".env",
                     pathlib.Path.home() / ".hermes" / ".env",
                     pathlib.Path.home() / ".env"):
        if not percorso.is_file():
            continue
        for riga in percorso.read_text(encoding="utf-8", errors="ignore").splitlines():
            riga = riga.strip()
            if riga.startswith(VARIABILE):
                return riga.split("=", 1)[1].strip().strip('"').strip("'")
    return ""


def token(conf: dict) -> str:
    """Prima la configurazione dell'app, poi l'ambiente, poi il file .env di Hermes."""
    scritto = ((conf.get("canali") or {}).get("umanesimodigitale") or {}).get("token") or ""
    return (scritto.strip()
            or os.environ.get(VARIABILE, "").strip()
            or _dal_file_env())


def presente(conf: dict) -> bool:
    return bool(token(conf))


# --------------------------------------------------------------------------- #

class MCP:
    """Un client MCP minimo: handshake, poi chiamate ai tool.

    Si usa come:
        m = MCP(conf); m.apri(); m.chiama("wp_count_posts", {"post_type": "post"})
    """

    def __init__(self, conf: dict, *, tentativi: int = TENTATIVI, pausa: float = 5.0):
        chiave = token(conf)
        if not chiave:
            raise ErroreMCP(
                "Manca il token MCP di umanesimodigitale.info: si imposta in "
                "Configurazione (oppure vive in %LOCALAPPDATA%\\hermes\\.env come "
                f"{VARIABILE}). Senza token non si puo' ne' leggere ne' pubblicare."
            )
        self.url = ENDPOINT + chiave
        self.tentativi = tentativi
        self.pausa = pausa
        self.sessione: str | None = None
        self._n = 0

    # --- trasporto --------------------------------------------------------- #

    def _post(self, corpo: dict, timeout: int = 180) -> dict:
        dati = json.dumps(corpo).encode("utf-8")
        intestazioni = {
            "Content-Type": "application/json",
            # il server puo' rispondere in SSE: va dichiarato che lo si accetta
            "Accept": "application/json, text/event-stream",
        }
        if self.sessione:
            intestazioni["mcp-session-id"] = self.sessione

        ultimo = None
        for tentativo in range(1, self.tentativi + 1):
            try:
                richiesta = urllib.request.Request(self.url, data=dati,
                                                   headers=intestazioni, method="POST")
                with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
                    if risposta.headers.get("mcp-session-id"):
                        self.sessione = risposta.headers["mcp-session-id"]
                    grezzo = risposta.read().decode("utf-8", "ignore")
                break
            except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError) as errore:
                ultimo = errore
                if tentativo == self.tentativi:
                    raise ErroreMCP(
                        f"{SITO} non ha risposto dopo {self.tentativi} tentativi: "
                        f"{getattr(errore, 'code', type(errore).__name__)}"
                    ) from None
                time.sleep(self.pausa)

        # il corpo puo' arrivare come Server-Sent Events: si tengono le righe dati
        for riga in grezzo.splitlines():
            riga = riga.strip()
            if riga.startswith("data:"):
                riga = riga[5:].strip()
            if riga.startswith("{"):
                try:
                    return json.loads(riga)
                except json.JSONDecodeError:
                    continue
        return {"_grezzo": grezzo[:400]}

    # --- protocollo -------------------------------------------------------- #

    def apri(self) -> dict:
        """Handshake: initialize, poi la notifica di inizializzazione."""
        esito = self._post({
            "jsonrpc": "2.0", "id": 1, "method": "initialize",
            "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                       "clientInfo": {"name": "social-studio", "version": "0.5"}},
        })
        if "error" in esito:
            raise ErroreMCP(f"handshake rifiutato da {SITO}: {esito['error']}")
        self._post({"jsonrpc": "2.0", "method": "notifications/initialized"})
        return (esito.get("result") or {}).get("serverInfo") or {}

    def chiama(self, nome: str, argomenti: dict) -> object:
        """Invoca un tool. Torna l'oggetto JSON se la risposta ne e' uno, altrimenti il testo.

        Parecchi tool di questo sito rispondono con una *stringa* ("Post created ID 12345")
        invece che con un oggetto: chi legge deve saper gestire entrambi.
        """
        self._n += 1
        risposta = self._post({
            "jsonrpc": "2.0", "id": 100 + self._n, "method": "tools/call",
            "params": {"name": nome, "arguments": argomenti},
        })
        if "error" in risposta:
            raise ErroreMCP(f"{SITO} ha rifiutato {nome}: {risposta['error']}")
        contenuto = (risposta.get("result") or {}).get("content") or []
        testo = (contenuto[0].get("text") if contenuto else "") or ""
        if isinstance(testo, str) and testo.lstrip().startswith(("{", "[")):
            try:
                return json.loads(testo)
            except json.JSONDecodeError:
                pass
        return testo

    # --- comodita' --------------------------------------------------------- #

    def ping(self) -> str:
        esito = self.chiama("mcp_ping", {})
        return esito if isinstance(esito, str) else json.dumps(esito, ensure_ascii=False)

    def tool_disponibili(self) -> list[str]:
        risposta = self._post({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
        elenco = (risposta.get("result") or {}).get("tools") or []
        return [t.get("name", "") for t in elenco]
