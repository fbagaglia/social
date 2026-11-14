"""Social Studio — server locale (sola libreria standard).

Entry point unico. Avvio:  py -3.14 server.py   (oppure avvia_social_studio.bat)

Guardie: ascolta solo su 127.0.0.1; ogni POST pretende l'intestazione
X-Social-Studio e risponde 403 senza; i percorsi che arrivano dal client si
risolvono e si verificano dentro le cartelle consentite.
"""

from __future__ import annotations

import json
import os
import sys
import time
import traceback
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

QUI = Path(__file__).resolve().parent
RADICE = QUI.parent
sys.path.insert(0, str(QUI))       # i moduli di backend si importano per nome
sys.path.insert(0, str(RADICE))    # il pacchetto xpost sta nella radice del progetto

from canali import base as canali          # noqa: E402
from canali import x as canale_x           # noqa: E402  (registra il canale "x")
import config as cfg                       # noqa: E402
import fonti                               # noqa: E402
import generazione                         # noqa: E402
import immagini                            # noqa: E402
import parametri                           # noqa: E402
import sistema                             # noqa: E402
import stato                               # noqa: E402

VERSIONE = "0.1.0"
PORTA = int(os.environ.get("SOCIAL_STUDIO_PORT", "8796"))
CARTELLA_UI = RADICE / "ui"
INTESTAZIONE_POST = "X-Social-Studio"
TETTO_CORPO = 12 * 1024 * 1024

# La sonda di un canale interroga la rete (Telegram, Mastodon): si tiene in cache
# invece di ripeterla a ogni clic, che e' lento e fragile.
CACHE_STATO: dict = {}
CACHE_SECONDI = 600

TIPI = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".md": "text/markdown; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}


# --------------------------------------------------------------------------- #
# Utilita'
# --------------------------------------------------------------------------- #

def dentro(percorso: Path, cartella: Path) -> bool:
    """Il percorso risolto deve stare dentro la cartella consentita."""
    try:
        percorso.resolve().relative_to(cartella.resolve())
        return True
    except (ValueError, OSError):
        return False


def diagnosi() -> dict:
    conf = cfg.leggi()
    llm = conf.get("llm") or {}
    ricerca = conf.get("ricerca") or {}
    return {
        "versione": VERSIONE,
        "porta": PORTA,
        "python": sys.version.split()[0],
        "radice": str(RADICE),
        "cartelle": {
            "allegati": str(cfg.CARTELLA_ALLEGATI),
            "bozze": str(cfg.CARTELLA_BOZZE),
            "log": str(cfg.CARTELLA_LOG),
        },
        "chiavi": {
            "openrouter": bool((llm.get("orKey") or "").strip()),
            "modello": (llm.get("orModel") or "").strip(),
            "firecrawl": bool((ricerca.get("firecrawlKey") or "").strip()),
            "brave": bool((ricerca.get("braveKey") or "").strip()),
        },
        "canali": canali.elenco(),
    }


# --------------------------------------------------------------------------- #
# Gestore
# --------------------------------------------------------------------------- #

class Gestore(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "SocialStudio/" + VERSIONE

    # --- risposte ---------------------------------------------------------- #
    def _scrivi(self, dati: bytes) -> None:
        """Se il client ha gia' chiuso (ricarica, cambio pagina) non e' un errore nostro."""
        try:
            self.wfile.write(dati)
        except (ConnectionError, OSError):
            pass

    def _invia(self, stato_http: int, corpo: bytes, tipo: str) -> None:
        self.send_response(stato_http)
        self.send_header("Content-Type", tipo)
        self.send_header("Content-Length", str(len(corpo)))
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("X-Content-Type-Options", "nosniff")
        try:
            self.end_headers()
        except (ConnectionError, OSError):
            return
        if self.command != "HEAD":
            self._scrivi(corpo)

    def json(self, dati, stato_http: int = 200) -> None:
        corpo = json.dumps(dati, ensure_ascii=False).encode()
        self._invia(stato_http, corpo, "application/json; charset=utf-8")

    def errore(self, messaggio: str, stato_http: int = 400) -> None:
        self.json({"errore": messaggio}, stato_http)

    def file(self, percorso: Path) -> None:
        try:
            corpo = percorso.read_bytes()
        except OSError as errore:
            self.errore("file non leggibile: " + str(errore), 404)
            return
        self._invia(200, corpo, TIPI.get(percorso.suffix.lower(), "application/octet-stream"))

    def log_message(self, formato: str, *args) -> None:
        sys.stderr.write("%s %s\n" % (self.address_string(), formato % args))

    # --- lettura corpo ----------------------------------------------------- #
    def _corpo(self) -> bytes:
        """Il corpo si legge UNA volta: chi lo usa lo riceve, non lo rilegge."""
        try:
            lunghezza = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            lunghezza = 0
        if lunghezza <= 0:
            return b""
        if lunghezza > TETTO_CORPO:
            return b""
        return self.rfile.read(lunghezza)

    def _json_corpo(self, grezzo: bytes) -> dict:
        if not grezzo:
            return {}
        try:
            return json.loads(grezzo.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as errore:
            raise ValueError("corpo JSON non leggibile: " + str(errore)) from None

    @staticmethod
    def _multipart(grezzo: bytes, tipo_contenuto: str) -> dict:
        """Upload con la sola libreria standard: si prende la prima parte con filename."""
        if "boundary=" not in tipo_contenuto:
            raise ValueError("manca il boundary nel Content-Type")
        confine = tipo_contenuto.split("boundary=", 1)[1].strip().strip('"').encode()
        for parte in grezzo.split(b"--" + confine):
            if b"filename=" not in parte:
                continue
            testa, _, corpo = parte.partition(b"\r\n\r\n")
            corpo = corpo.rstrip(b"\r\n-")
            nome = ""
            for riga in testa.split(b"\r\n"):
                if b"filename=" in riga:
                    nome = riga.split(b"filename=", 1)[1].strip().strip(b'"').decode(
                        "utf-8", errors="replace")
            if nome:
                return {"nome": nome, "contenuto": corpo}
        raise ValueError("nessun file con nome trovato nel corpo")

    # --- GET --------------------------------------------------------------- #
    def do_GET(self) -> None:  # noqa: N802
        pezzi = urlsplit(self.path)
        percorso = pezzi.path
        try:
            if percorso in ("/", "/index.html"):
                self.file(CARTELLA_UI / "index.html")
            elif percorso == "/favicon.ico":
                self._invia(204, b"", "image/x-icon")
            elif percorso.startswith("/ui/"):
                relativo = percorso[len("/ui/"):]
                candidato = (CARTELLA_UI / relativo)
                if not dentro(candidato, CARTELLA_UI) or not candidato.is_file():
                    self.errore("risorsa non trovata", 404)
                else:
                    self.file(candidato)
            elif percorso.startswith("/api/allegati/"):
                nome = percorso[len("/api/allegati/"):]
                candidato = cfg.CARTELLA_ALLEGATI / nome
                if not dentro(candidato, cfg.CARTELLA_ALLEGATI) or not candidato.is_file():
                    self.errore("allegato non trovato", 404)
                else:
                    self.file(candidato)
            elif percorso == "/health" or percorso == "/api/stato":
                self.json(diagnosi())
            elif percorso == "/api/config":
                self.json(cfg.leggi_mascherato())
            elif percorso == "/api/parametri":
                self.json({"parametri": parametri.PARAMETRI,
                           "predefiniti": parametri.predefiniti()})
            elif percorso == "/api/canali":
                conf = cfg.leggi()
                elenco = canali.elenco()
                for voce in elenco:
                    pronto, motivo = canali.prendi(voce["chiave"]).pronto(conf)
                    voce["pronto"] = pronto
                    voce["motivo_pronto"] = motivo
                self.json({"canali": elenco})
            elif percorso == "/api/guida":
                guida = CARTELLA_UI / "guida.md"
                if guida.exists():
                    self._invia(200, guida.read_bytes(), TIPI[".md"])
                else:
                    self.errore("guida non trovata", 404)
            elif percorso == "/api/corrente":
                self.json(stato.leggi_corrente())
            elif percorso == "/api/pubblicazioni":
                self.json({"pubblicazioni": stato.leggi_registro()})
            elif percorso == "/api/x/stato":
                self.json(canale_x.stato_token(cfg.leggi()))
            elif percorso.startswith("/api/canale/") and percorso.endswith("/stato"):
                self._stato_canale(percorso[len("/api/canale/"):-len("/stato")])
            else:
                self.errore("rotta non trovata: " + percorso, 404)
        except Exception as errore:  # una lettura non deve mai portare giu' il servizio
            self.errore(f"{type(errore).__name__}: {errore}", 500)
            traceback.print_exc()

    def _stato_canale(self, chiave: str) -> None:
        """Stato del collegamento di un singolo canale. Sola lettura: non pubblica nulla."""
        try:
            canale = canali.prendi(chiave)
        except KeyError as errore:
            self.errore(str(errore), 404)
            return
        if not canale.collegato or not hasattr(canale, "ponte"):
            self.json({"collegato": False, "manuale": True, "account": None, "motivo": ""})
            return

        adesso = time.time()
        salvato = CACHE_STATO.get(chiave)
        if salvato and adesso - salvato[0] < CACHE_SECONDI:
            self.json(salvato[1])
            return

        try:
            esito = {"collegato": True, "manuale": False,
                     "account": canale.ponte().account(cfg.leggi()), "motivo": ""}
            CACHE_STATO[chiave] = (adesso, esito)
        except BaseException as errore:  # i ponti escono con eccezioni proprie o SystemExit
            esito = {"collegato": False, "manuale": False, "account": None,
                     "motivo": str(errore)}
        self.json(esito)

    def do_HEAD(self) -> None:  # noqa: N802
        self.do_GET()

    # --- POST -------------------------------------------------------------- #
    def do_POST(self) -> None:  # noqa: N802
        if not self.headers.get(INTESTAZIONE_POST):
            self.errore("richiesta rifiutata: manca l'intestazione " + INTESTAZIONE_POST, 403)
            return
        percorso = urlsplit(self.path).path
        grezzo = self._corpo()
        tipo_contenuto = self.headers.get("Content-Type") or ""

        try:
            if percorso == "/api/config":
                cfg.scrivi(self._json_corpo(grezzo))
                self.json({"ok": True, "config": cfg.leggi_mascherato()})
            elif percorso == "/api/fonte":
                self._fonte(grezzo)
            elif percorso == "/api/genera":
                self._genera(grezzo)
            elif percorso == "/api/adatta":
                self._adatta(grezzo)
            elif percorso == "/api/immagine/carica":
                self._carica_immagine(grezzo, tipo_contenuto)
            elif percorso == "/api/immagine/genera":
                self._genera_immagine(grezzo)
            elif percorso in ("/api/allegato/copia", "/api/allegato/cartella"):
                self._allegato_sul_sistema(percorso, grezzo)
            elif percorso == "/api/x/login":
                self.json(canale_x.avvia_login(cfg.leggi()))
            elif percorso == "/api/prepara":
                self._prepara(grezzo)
            elif percorso == "/api/invia":
                self._invia_social(grezzo)
            elif percorso == "/api/corrente":
                self.json(stato.salva_corrente(self._json_corpo(grezzo)))
            else:
                self.errore("rotta non trovata: " + percorso, 404)
        except ValueError as errore:
            self.errore(str(errore), 400)
        except Exception as errore:
            self.errore(f"{type(errore).__name__}: {errore}", 500)
            traceback.print_exc()

    # --- rotte ------------------------------------------------------------- #
    def _fonte(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        tipo = dati.get("tipo")
        conf = cfg.leggi()
        ricerca = conf.get("ricerca") or {}
        chiavi = {"firecrawlKey": ricerca.get("firecrawlKey"),
                  "braveKey": ricerca.get("braveKey")}
        usa_ricerca = bool(dati.get("ricerca_web", True)) and bool(ricerca.get("attiva", True))
        try:
            if tipo == "link":
                esito = fonti.da_link(dati.get("url", ""), ricerca=usa_ricerca, chiavi=chiavi)
            elif tipo == "video":
                esito = fonti.da_video(dati.get("url", ""), ricerca=usa_ricerca, chiavi=chiavi)
            elif tipo == "testo":
                esito = {"tipo": "testo", "titolo": dati.get("titolo", ""),
                         "testo": dati.get("testo", ""), "via": "incollato a mano"}
            else:
                self.errore("tipo di fonte sconosciuto: " + str(tipo), 400)
                return
        except fonti.FonteError as errore:
            # La lettura non riuscita e' una RISPOSTA, non un guasto: 200 con il motivo.
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, "fonte": esito})

    def _genera(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        try:
            esito = generazione.genera(dati.get("fonte") or {}, dati.get("parametri"), cfg.leggi())
        except generazione.GenerazioneError as errore:
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, **esito})

    def _adatta(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        try:
            canale = canali.prendi(dati.get("canale", ""))
        except KeyError as errore:
            self.errore(str(errore), 400)
            return
        try:
            esito = generazione.adatta(dati.get("testo", ""), dati.get("titolo", ""),
                                       canale, dati.get("parametri"), cfg.leggi())
        except generazione.GenerazioneError as errore:
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, "canale": canale.chiave, **esito})

    def _carica_immagine(self, grezzo: bytes, tipo_contenuto: str) -> None:
        try:
            parte = self._multipart(grezzo, tipo_contenuto)
            esito = immagini.salva_caricata(parte["nome"], parte["contenuto"])
        except (ValueError, immagini.ImmagineError) as errore:
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, **esito})

    def _genera_immagine(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        conf = cfg.leggi()
        firma = dati.get("firma")
        if firma is None:
            firma = (conf.get("pubblicazione") or {}).get("firma", "")
        try:
            esito = immagini.genera_pannello(
                dati.get("titolo", ""), dati.get("sottotitolo", ""), firma,
                dati.get("formato", "orizzontale"))
        except immagini.ImmagineError as errore:
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, **esito})

    def _allegato_sul_sistema(self, rotta: str, grezzo: bytes) -> None:
        """Porta l'immagine a portata di mano: negli appunti o nella cartella aperta.

        E' il pezzo che manca alla consegna manuale: l'URL del compositore non porta
        le immagini, quindi l'allegato si prepara qui.
        """
        dati = self._json_corpo(grezzo)
        percorso = Path(dati.get("percorso", ""))
        if not dentro(percorso, cfg.CARTELLA_ALLEGATI) or not percorso.exists():
            self.errore("immagine non trovata tra gli allegati", 404)
            return
        try:
            if rotta == "/api/allegato/copia":
                messaggio = sistema.copia_immagine(percorso)
            else:
                messaggio = sistema.apri_cartella(percorso)
        except sistema.SistemaError as errore:
            self.json({"ok": False, "motivo": str(errore)})
            return
        self.json({"ok": True, "messaggio": messaggio, "nome": percorso.name})

    def _prepara(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        try:
            canale = canali.prendi(dati.get("canale", ""))
        except KeyError as errore:
            self.errore(str(errore), 400)
            return
        try:
            esito = canale.prepara(dati, cfg.leggi())
        except BaseException as errore:  # il motore esce con SystemExit
            self.errore(f"{type(errore).__name__}: {errore}", 500)
            return
        # 200 anche quando dice di no: i problemi sono la risposta, non un guasto.
        self.json({"ok": True, "preparazione": esito})

    def _invia_social(self, grezzo: bytes) -> None:
        dati = self._json_corpo(grezzo)
        try:
            canale = canali.prendi(dati.get("canale", ""))
        except KeyError as errore:
            self.errore(str(errore), 400)
            return
        try:
            esito = canale.invia(dati, cfg.leggi())
        except BaseException as errore:  # idem
            self.errore(f"{type(errore).__name__}: {errore}", 500)
            return
        if esito.get("pubblicato"):
            stato.registra_pubblicazione({
                "canale": canale.chiave, "etichetta": canale.etichetta,
                "titolo": dati.get("titolo", ""), "testo": dati.get("testo", ""),
                **{k: v for k, v in esito.items() if k != "pubblicato"},
            })
        self.json({"ok": True, "esito": esito})


# --------------------------------------------------------------------------- #

def banner() -> None:
    info = diagnosi()
    chiavi = info["chiavi"]
    print("=" * 62)
    print(f" Social Studio {VERSIONE} — app locale di pubblicazione")
    print("=" * 62)
    print(f" indirizzo   http://127.0.0.1:{PORTA}/")
    print(f" python      {info['python']}")
    print(f" progetto    {info['radice']}")
    print(f" OpenRouter  {'chiave presente' if chiavi['openrouter'] else 'CHIAVE ASSENTE'}"
          f" · modello {chiavi['modello'] or '(nessuno)'}")
    print(f" ricerca web Firecrawl {'ok' if chiavi['firecrawl'] else 'assente'}"
          f" · Brave {'ok' if chiavi['brave'] else 'assente'}")
    collegati = [c["etichetta"] for c in info["canali"] if c["collegato"]]
    print(f" canali      {len(info['canali'])} in elenco"
          f" · pubblicano via API: {', '.join(collegati) or 'nessuno'}")
    if not chiavi["openrouter"]:
        print(" ATTENZIONE  senza la chiave OpenRouter la generazione non parte:")
        print("             impostala in Configurazione dentro l'app.")
    print("=" * 62)


def main() -> int:
    cfg.assicura_cartelle()
    banner()
    server = ThreadingHTTPServer(("127.0.0.1", PORTA), Gestore)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nChiuso.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
