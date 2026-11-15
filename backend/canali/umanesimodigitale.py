"""Il canale «Umanesimodigitale.info»: l'articolo, non il post.

Qui non si scrive un testo breve da incollare in un compositore: si compone
**l'articolo** nella forma del sito (apertura Spectra, corpo in h2, FAQ a scomparsa,
immagini nel corpo, pattern invito) e si deposita come **bozza** su WordPress,
via MCP. La pubblicazione resta un atto dell'utente: `draft` e' la norma.

Perche' una classe a parte e non un `Canale` con qualche campo in piu': le due cose
hanno **tempi diversi**. Un post social e' pronto quando sta nel tetto di caratteri;
un articolo e' pronto quando ha titolo, occhiello, copertina, corpo, FAQ e campi SEO.
Tenerli nella stessa classe avrebbe voluto dire un `if` in ogni metodo.
"""

from __future__ import annotations

import pathlib

from umanesimo import articolo as art
from umanesimo import mcp as mcp_mod
from umanesimo import media

from .base import Canale

# Il corpo dell'articolo accetta due convenzioni, cosi' chi scrive non deve sapere
# niente di Gutenberg: una riga che comincia con "## " diventa un h2.
PREFISSO_SEZIONE = "## "


class CanaleUmanesimo(Canale):
    """L'articolo su umanesimodigitale.info. `tipo = "blog"` accende il pannello suo."""

    # attributo di classe, non campo: e' la regola di questo canale, non un dato dell'istanza
    immagini_corpo_max = 2

    def modalita(self, conf: dict) -> str:
        """Il blog non ha un compositore da aprire: deposita la bozza via MCP. Sempre."""
        return "api"

    def pronto(self, conf: dict) -> tuple[bool, str]:
        """Pronto = il token c'e'. E' un fatto locale: non si chiama il sito per saperlo."""
        if not mcp_mod.presente(conf):
            return False, ("manca il token MCP di umanesimodigitale.info: si incolla in "
                           "Configurazione, oppure vive in %LOCALAPPDATA%\\hermes\\.env")
        return True, ""

    def prepara(self, pubblicazione: dict, conf: dict) -> dict:
        base = super().prepara(pubblicazione, conf)
        corpo = _corpo(pubblicazione)
        immagini = [pathlib.Path(p) for p in pubblicazione.get("immagini_corpo") or []]
        faq = _faq(pubblicazione)

        base.update({
            "tipo": "blog",
            "occhiello": (pubblicazione.get("gancio") or "").strip(),
            "sintesi": (pubblicazione.get("sintesi") or "").strip(),
            "paragrafi": len(corpo["paragrafi"]),
            "sezioni": [t for t in corpo["sezioni"]],
            "faq": len(faq),
            "immagini_corpo": [p.name for p in immagini],
            "copertina": [pathlib.Path(p).name for p in pubblicazione.get("allegati") or []],
            "slug": (pubblicazione.get("slug") or "").strip(),
            "seo_title": (pubblicazione.get("seo_title") or "").strip(),
            "seo_description": (pubblicazione.get("seo_description") or "").strip(),
            "focus_keyword": (pubblicazione.get("focus_keyword") or "").strip(),
            "categorie": pubblicazione.get("categorie") or [],
            "misure": _misure_blog(pubblicazione),
            "via": "bozza su WordPress (MCP)",
        })
        return base

    def misure(self, testo: str, limite: int | None = None) -> dict:
        # per un articolo il tetto non e' un numero di caratteri: e' il SEO title a 60
        # e la meta description a 160. Il conteggio del corpo resta, come informazione.
        return {"caratteri": len(testo), "limite": 0, "restanti": 0, "entro": True}

    def problemi(self, pubblicazione: dict, conf: dict) -> list[dict]:
        corpo = _corpo(pubblicazione)
        faq = _faq(pubblicazione)
        problemi: list[dict] = []

        if not (pubblicazione.get("titolo") or "").strip():
            problemi.append({"bloccante": True, "testo": "manca il titolo dell'articolo"})
        if len(corpo["paragrafi"]) < 4:
            problemi.append({
                "bloccante": True,
                "testo": (f"il corpo ha {len(corpo['paragrafi'])} paragrafi: un articolo "
                          "ne vuole almeno quattro (il primo va nell'apertura)"),
            })
        if not corpo["sezioni"]:
            problemi.append({
                "bloccante": True,
                "testo": ("nessuna sezione: servono almeno due h2. Le righe che cominciano "
                          f"con «{PREFISSO_SEZIONE.strip()} » diventano titoli di sezione"),
            })
        elif len(corpo["sezioni"]) < 2:
            problemi.append({"bloccante": False,
                             "testo": "una sola sezione: il modello ne vuole almeno due"})
        if any(indice == 0 for indice, _ in corpo["sezioni"]):
            problemi.append({
                "bloccante": True,
                "testo": ("la prima sezione cade sul primo paragrafo, che va dentro l'apertura: "
                          "metti un paragrafo introduttivo prima del primo titolo di sezione"),
            })
        for orfano in corpo.get("orfani", []):
            problemi.append({
                "bloccante": True,
                "testo": (f"il titolo di sezione «{orfano}» non ha nessun paragrafo sotto: "
                          "senza testo non e' una sezione, va tolto o va scritto il paragrafo"),
            })
        if not (pubblicazione.get("gancio") or "").strip():
            problemi.append({"bloccante": False,
                             "testo": "senza titolo-gancio l'apertura resta piu' povera"})
        if not (pubblicazione.get("sintesi") or "").strip():
            problemi.append({"bloccante": False,
                             "testo": "senza frase-sintesi l'occhiello non comincia in corsivo"})
        if not faq:
            problemi.append({"bloccante": False, "testo": "nessuna FAQ: la sezione non verra' creata"})
        elif not (3 <= len(faq) <= 5):
            problemi.append({"bloccante": False,
                             "testo": f"{len(faq)} domande: il modello ne vuole da 3 a 5"})

        seo_title = (pubblicazione.get("seo_title") or "").strip()
        seo_desc = (pubblicazione.get("seo_description") or "").strip()
        if not seo_title:
            problemi.append({"bloccante": False, "testo": "manca il SEO title"})
        elif len(seo_title) > 60:
            problemi.append({"bloccante": True,
                             "testo": f"il SEO title e' di {len(seo_title)} caratteri: il tetto e' 60"})
        if not seo_desc:
            problemi.append({"bloccante": False, "testo": "manca la meta description"})
        elif len(seo_desc) > 160:
            problemi.append({"bloccante": True,
                             "testo": (f"la meta description e' di {len(seo_desc)} caratteri: "
                                       "il tetto e' 160")})

        immagini = list(pubblicazione.get("allegati") or []) + list(pubblicazione.get("immagini_corpo") or [])
        for percorso in immagini:
            if not pathlib.Path(percorso).is_file():
                problemi.append({"bloccante": True, "testo": f"immagine non trovata: {pathlib.Path(percorso).name}"})
        if len(pubblicazione.get("immagini_corpo") or []) > self.immagini_corpo_max:
            problemi.append({"bloccante": True,
                             "testo": f"al massimo {self.immagini_corpo_max} immagini nel corpo"})
        if not pubblicazione.get("allegati"):
            problemi.append({"bloccante": False,
                             "testo": ("nessuna copertina: l'apertura restera' senza immagine "
                                       "e l'articolo senza immagine in evidenza")})

        if not mcp_mod.presente(conf):
            problemi.append({
                "bloccante": True,
                "testo": ("manca il token MCP di umanesimodigitale.info: si imposta in "
                          "Configurazione, senza token non si pubblica"),
            })
        return problemi

    def url_compositore(self, pubblicazione: dict) -> str:
        return ""   # non c'e' un compositore da aprire: si pubblica via MCP

    # --- il secondo tempo: si deposita la bozza ---------------------------- #

    def invia(self, pubblicazione: dict, conf: dict) -> dict:
        bloccanti = [p for p in self.problemi(pubblicazione, conf) if p.get("bloccante")]
        if bloccanti:
            return {"pubblicato": False, "motivo": bloccanti[0]["testo"], "problemi": bloccanti}

        cliente = mcp_mod.MCP(conf)
        passi: list[str] = []
        try:
            info = cliente.apri()
            passi.append(f"canale aperto su {info.get('name', mcp_mod.SITO)}")

            # 1. le immagini: prima si caricano, poi si compone il markup con gli id veri
            copertina = None
            for percorso in list(pubblicazione.get("allegati") or [])[:1]:
                copertina = self._carica(cliente, percorso, pubblicazione)
                passi.append(f"copertina caricata (id {copertina['id']})")

            immagini_corpo = []
            for percorso in list(pubblicazione.get("immagini_corpo") or [])[:self.immagini_corpo_max]:
                immagini_corpo.append(self._carica(cliente, percorso, pubblicazione))
            if immagini_corpo:
                passi.append(f"{len(immagini_corpo)} immagini del corpo caricate "
                             f"(id {', '.join(str(i['id']) for i in immagini_corpo)})")

            # 2. il markup, validato prima di creare
            corpo = _corpo(pubblicazione)
            markup = art.componi(
                copertina=copertina,
                gancio=(pubblicazione.get("gancio") or "").strip(),
                sintesi=(pubblicazione.get("sintesi") or "").strip(),
                paragrafi=corpo["paragrafi"],
                sezioni=corpo["sezioni"],
                immagini_corpo=immagini_corpo,
                faq=_faq(pubblicazione),
                intro_faq=(pubblicazione.get("intro_faq") or "").strip(),
                nota_fonte=(pubblicazione.get("nota_fonte") or "").strip(),
            )
            controllo = art.valida(markup)
            if not controllo["ok"]:
                return {"pubblicato": False,
                        "motivo": "il markup non passa le validazioni: " + "; ".join(controllo["problemi"]),
                        "problemi": controllo["problemi"]}
            passi.append(f"markup composto e validato ({controllo['byte']} byte, "
                         f"{controllo['h2']} sezioni, {controllo['immagini']} immagini)")

            # 3. la bozza
            creato = cliente.chiama("wp_create_post", {
                "post_type": "post",
                "post_status": "draft",
                "post_title": (pubblicazione.get("titolo") or "").strip(),
                "post_excerpt": (pubblicazione.get("sintesi") or "").strip(),
                "post_name": (pubblicazione.get("slug") or "").strip(),
                "post_content": markup,
            })
            # la risposta di questo tool e' una STRINGA ("Post created ID 12345"),
            # non un oggetto: chi la tratta come oggetto conclude che non e' riuscita
            identificatore = _id_da_risposta(creato)
            if not identificatore:
                return {"pubblicato": False,
                        "motivo": f"la creazione non ha dato un ID leggibile: {str(creato)[:300]}",
                        "passi": passi}
            passi.append(f"bozza creata (ID {identificatore})")

            # 4. categorie: con wp_update_post non si assegnano, va usato il tool delle tassonomie
            categorie = [int(c) for c in (pubblicazione.get("categorie") or []) if str(c).isdigit()]
            if categorie:
                cliente.chiama("wp_add_post_terms",
                               {"ID": identificatore, "taxonomy": "category",
                                "terms": categorie, "append": False})
                lette = cliente.chiama("wp_get_post_terms",
                                       {"ID": identificatore, "taxonomy": "category"})
                nomi = [t.get("name") for t in lette] if isinstance(lette, list) else lette
                passi.append(f"categorie assegnate: {nomi}")

            # 5. immagine in evidenza: la stessa copertina dell'apertura
            if copertina:
                cliente.chiama("wp_set_featured_image",
                               {"post_id": identificatore, "media_id": copertina["id"]})
                passi.append("immagine in evidenza impostata")

            # 6. i campi SEO del plugin (Rank Math)
            cliente.chiama("wp_update_seo", {
                "ID": identificatore,
                "fields": {
                    "title": (pubblicazione.get("seo_title") or "").strip(),
                    "description": (pubblicazione.get("seo_description") or "").strip(),
                    "focus_keyword": (pubblicazione.get("focus_keyword") or "").strip(),
                },
            })
            passi.append("campi SEO scritti")

            # 7. la resa vera, e l'anteprima da mandare all'utente
            resa = cliente.chiama("wp_get_rendered", {"ID": identificatore})
            anteprima = cliente.chiama("wp_preview_link",
                                       {"ID": identificatore, "share": True, "days": 7})

        except mcp_mod.ErroreMCP as errore:
            return {"pubblicato": False, "motivo": str(errore), "passi": passi}
        except media.ErroreMedia as errore:
            return {"pubblicato": False, "motivo": f"immagine: {errore}", "passi": passi}

        esito = {
            "pubblicato": True,
            "bozza": True,
            "id": identificatore,
            "passi": passi,
            "anteprima": anteprima if isinstance(anteprima, str) else str(anteprima),
            "motivo": (f"bozza creata su {mcp_mod.SITO}: si pubblica da wp-admin, "
                       "e' una decisione tua"),
        }
        if isinstance(resa, dict):
            esito["resa"] = {
                "titoli": resa.get("headings"),
                "immagini": resa.get("images"),
                "senza_alt": resa.get("images_without_alt"),
                "parole": resa.get("words"),
                "http": resa.get("http_status"),
            }
            if not art.valida(markup)["ok"]:
                esito["avviso"] = "le validazioni locali segnalano qualcosa: rileggi i problemi"
        return esito

    def _carica(self, cliente: mcp_mod.MCP, percorso: str, pubblicazione: dict) -> dict:
        percorso_nodo = pathlib.Path(percorso)
        alt = ""
        for voce in pubblicazione.get("alt_immagini") or []:
            if pathlib.Path(voce.get("file", "")).name == percorso_nodo.name:
                alt = (voce.get("alt") or "").strip()
        if not alt:
            alt = (pubblicazione.get("titolo") or "").strip()
        caricata = media.carica(
            cliente, percorso_nodo,
            titolo=f"{(pubblicazione.get('titolo') or '').strip()} — {percorso_nodo.stem}",
            alt=alt,
            descrizione=(pubblicazione.get("sintesi") or "").strip()[:200],
        )
        misure = media.dimensioni(percorso_nodo)
        if misure[0]:
            caricata["larghezza"], caricata["altezza"] = misure
        return caricata


# --------------------------------------------------------------------------- #

def _corpo(pubblicazione: dict) -> dict:
    """Dal testo dell'articolo ai paragrafi e alle sezioni.

    Le sezioni si riconoscono dal prefisso `## `: chi scrive non deve sapere niente di
    Gutenberg, e la convenzione resta leggibile nel campo di testo.

    Si legge **riga per riga**, non a blocchi separati da righe vuote: un titolo di
    sezione puo' arrivare subito dopo un paragrafo, senza una riga vuota in mezzo, e con
    il taglio sui soli blocchi il titolo si sarebbe mangiato il testo che segue.
    Una riga vuota chiude comunque il paragrafo.
    """
    testo = pubblicazione.get("testo") or ""
    paragrafi: list[str] = []
    sezioni: list[tuple[int, str]] = []
    orfani: list[str] = []
    pendente: str | None = None
    buffer: list[str] = []

    def chiudi_paragrafo() -> None:
        nonlocal pendente
        if not buffer:
            return
        pezzi = art.testo_a_paragrafi("\n".join(buffer))
        buffer.clear()
        if not pezzi:
            return
        testo_paragrafo = " ".join(pezzi)
        if pendente is not None:
            sezioni.append((len(paragrafi), pendente))
            pendente = None
        paragrafi.append(testo_paragrafo)

    def nuovo_titolo(titolo: str) -> None:
        """Un titolo che arriva quando ce n'e' gia' uno in attesa non e' una sezione:
        e' un titolo orfano, e va detto invece che perso in silenzio."""
        nonlocal pendente
        if pendente is not None:
            orfani.append(pendente)
        pendente = titolo

    for riga in testo.splitlines():
        spoglia = riga.strip()
        if spoglia.startswith(PREFISSO_SEZIONE):
            chiudi_paragrafo()
            nuovo_titolo(spoglia[len(PREFISSO_SEZIONE):].strip())
            continue
        if not spoglia:
            chiudi_paragrafo()
            continue
        buffer.append(spoglia)
    chiudi_paragrafo()

    # un titolo in coda, senza paragrafi dopo: non e' una sezione, e' un residuo
    if pendente is not None:
        orfani.append(pendente)

    return {"paragrafi": paragrafi, "sezioni": sezioni, "orfani": orfani}


def sezioni_di(testo: str) -> dict:
    """Le sezioni e i paragrafi di un testo, senza costruire l'articolo.

    E' la stessa lettura che fa la pubblicazione: cosi' quello che l'interfaccia mostra
    («3 sezioni riconosciute») e' esattamente quello che finira' nella bozza.
    """
    return _corpo({"testo": testo})


def _faq(pubblicazione: dict) -> list[tuple[str, str]]:
    fuori = []
    for voce in pubblicazione.get("faq") or []:
        domanda = (voce.get("domanda") or "").strip()
        risposta = (voce.get("risposta") or "").strip()
        if domanda and risposta:
            fuori.append((domanda, risposta))
    return fuori


def _misure_blog(pubblicazione: dict) -> dict:
    seo_title = (pubblicazione.get("seo_title") or "").strip()
    seo_desc = (pubblicazione.get("seo_description") or "").strip()
    corpo = _corpo(pubblicazione)
    return {
        "caratteri": len(pubblicazione.get("testo") or ""),
        "seo_title": {"caratteri": len(seo_title), "limite": 60, "entro": len(seo_title) <= 60},
        "seo_description": {"caratteri": len(seo_desc), "limite": 160, "entro": len(seo_desc) <= 160},
        "paragrafi": len(corpo["paragrafi"]),
        "sezioni": len(corpo["sezioni"]),
        "faq": len(_faq(pubblicazione)),
    }


def _id_da_risposta(risposta) -> int | None:
    """L'ID dell'articolo, letto da una stringa o da un oggetto: le due forme esistono."""
    if isinstance(risposta, dict):
        for chiave in ("ID", "id", "post_id"):
            if str(risposta.get(chiave, "")).isdigit():
                return int(risposta[chiave])
        return None
    trovato = __import__("re").search(r"\b(\d{2,})\b", str(risposta))
    return int(trovato.group(1)) if trovato else None
