"""La rassegna stampa: da un elenco di link a una pagina HTML impaginata.

Un link diventa una card con miniatura, titolo e abstract; le card stanno in una
griglia; sopra, un titolo, la data e **l'abstract complessivo** che racconta il
trend — cioe' che cosa dicono insieme quelle notizie, che e' la cosa che un elenco
di link non dice.

L'impaginazione riprende la forma che il sito usa gia' per gli «Approfondimenti»:
griglia a due colonne che diventa una sotto i 640 px, card col bordo sinistro
verde, miniatura come immagine di sfondo. La palette e' quella del progetto, e
sono cinque colori: nero #0C0D0D, verde #379557, chiaro #D9E1DA, grigio scuro
#5B5F5C, grigio chiaro #818484.
"""

from __future__ import annotations

import html as html_mod
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request

NERO = "#0C0D0D"
VERDE = "#379557"
CHIARO = "#D9E1DA"
GRIGIO_SCURO = "#5B5F5C"
GRIGIO_CHIARO = "#818484"

VOCI_MAX = 8
TESTO_PER_VOCE = 6000        # quanto testo di ogni fonte si manda al modello

# gli stessi host che `fonti.py` rifiuta: qui si legge una pagina per la miniatura
HOST_VIETATI = ("localhost", "127.0.0.1", "0.0.0.0", "169.254.169.254", "[::1]")

SCHEMA_URL = re.compile(r"https?://[^\s<>\"')\]]+", re.I)


class RassegnaError(Exception):
    """La rassegna non si e' potuta comporre: il motivo e' in chiaro."""


# --------------------------------------------------------------------------- #
# Gli indirizzi
# --------------------------------------------------------------------------- #

def link_da_testo(testo: str) -> list[str]:
    """Gli indirizzi scritti nel campo, uno per riga o incollati in fila.

    Si tolgono i doppioni tenendo l'ordine: chi incolla la stessa notizia due volte
    non deve ritrovarsela due volte in griglia.
    """
    trovati = SCHEMA_URL.findall(testo or "")
    visti: set[str] = set()
    fuori: list[str] = []
    for indirizzo in trovati:
        pulito = indirizzo.rstrip(".,;:").strip()
        # la punteggiatura finale non fa parte dell'indirizzo
        confronto = pulito.rstrip("/").lower()
        if confronto in visti:
            continue
        visti.add(confronto)
        fuori.append(pulito)
    return fuori[:VOCI_MAX]


def dominio(url: str) -> str:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return host[4:] if host.startswith("www.") else host


def _host_vietato(url: str) -> bool:
    host = urllib.parse.urlsplit(url).netloc.lower()
    return any(v in host for v in HOST_VIETATI)


# --------------------------------------------------------------------------- #
# La miniatura
# --------------------------------------------------------------------------- #

def _og_immagine(pagina: str, base: str) -> str:
    """L'immagine di anteprima dichiarata dalla pagina, o la prima immagine utile."""
    schemi = (
        r'<meta[^>]+property=["\']og:image(?::secure_url)?["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image',
    )
    for schema in schemi:
        trovato = re.search(schema, pagina, re.I)
        if trovato:
            return urllib.parse.urljoin(base, html_mod.unescape(trovato.group(1)))

    for schema in (r'<img[^>]+src=["\']([^"\']+\.(?:jpe?g|png|webp))',
                   r'<img[^>]+src=["\']([^"\']+)'):
        trovato = re.search(schema, pagina, re.I)
        if trovato:
            indirizzo = html_mod.unescape(trovato.group(1))
            if indirizzo.startswith(("data:", "#")):
                continue
            return urllib.parse.urljoin(base, indirizzo)
    return ""


def miniatura(url: str, pagina: str = "") -> str:
    """La miniatura di un link: gratis per YouTube, letta dalla pagina per il resto."""
    video = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{6,})",
                      url, re.I)
    if video:
        # YouTube espone le miniature a indirizzo fisso: non serve leggere niente
        return f"https://img.youtube.com/vi/{video.group(1)}/hqdefault.jpg"
    if not pagina:
        return ""
    return _og_immagine(pagina, url)


def _scarica_pagina(url: str, timeout: int = 30, tentativi: int = 2) -> str:
    """La pagina, per cercarci la miniatura.

    Ritenta una volta: questi siti a volte rispondono un guscio vuoto (protezioni
    anti-bot, o throttling dopo qualche richiesta ravvicinata), e senza ritentativo
    la card resterebbe senza miniatura per un sussulto di mezzo secondo. Il
    fallimento non e' grave — la rassegna regge lo stesso — ma e' evitabile.
    """
    if _host_vietato(url):
        return ""
    richiesta = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (compatible; SocialStudio/1.0)",
        "Accept": "text/html,application/xhtml+xml",
    })
    for tentativo in range(1, tentativi + 1):
        try:
            with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
                pagina = risposta.read(400_000).decode("utf-8", "ignore")
            if len(pagina) > 2000:               # un guscio vuoto non e' una pagina
                return pagina
        except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError):
            pass
        if tentativo < tentativi:
            time.sleep(1.5)
    return ""


# --------------------------------------------------------------------------- #
# Il testo di ogni voce
# --------------------------------------------------------------------------- #

def raccogli(url: str, *, chiavi: dict | None = None, ricerca: bool = True) -> dict:
    """Che cosa serve per una card: titolo, testo per l'abstract, miniatura, dominio.

    La lettura riusa le vie che l'app usa gia' per le fonti (Firecrawl e poi lettura
    diretta; per YouTube la trascrizione). La miniatura invece si prende a parte,
    perche' il testo pulito non conserva le immagini.
    """
    import fonti                                     # import pigro: evita cicli

    e_video = bool(fonti.id_youtube(url)) if hasattr(fonti, "id_youtube") else False
    if e_video:
        letto = fonti.da_video(url, ricerca=ricerca, chiavi=chiavi)
        miniatura_ = miniatura(url)
    else:
        letto = fonti.da_link(url, ricerca=ricerca, chiavi=chiavi)
        miniatura_ = miniatura(url, _scarica_pagina(url))

    return {
        "url": url,
        "dominio": dominio(url),
        "titolo": (letto.get("titolo") or "").strip(),
        "testo": (letto.get("testo") or "")[:TESTO_PER_VOCE],
        "miniatura": miniatura_,
        "via": letto.get("via", ""),
        "video": e_video,
    }


# --------------------------------------------------------------------------- #
# L'HTML
# --------------------------------------------------------------------------- #

def _testo(valore: str) -> str:
    """Il testo entra nell'HTML sempre passando da qui.

    L'e commerciale diventa `&amp;`: nei **nodi di testo** e' innocuo (il browser lo
    decodifica), mentre dentro `<script>` e `<style>` spaccherebbe il codice — per
    questo il foglio di stile qui sotto non contiene nessun `&`.
    """
    return html_mod.escape(str(valore or ""), quote=True)


CSS = """<style>
.ud-rassegna{max-width:960px;margin:0 auto;font-family:inherit;color:#0C0D0D}
.ud-rassegna-testa{border-left:5px solid #379557;padding:4px 0 4px 20px;margin:0 0 28px}
.ud-rassegna-occhiello{margin:0 0 8px;color:#379557;font-weight:700;font-size:.82rem;letter-spacing:3px;text-transform:uppercase}
.ud-rassegna-titolo{margin:0 0 6px;font-size:2rem;line-height:1.15;color:#0C0D0D;font-weight:800}
.ud-rassegna-data{margin:0 0 16px;color:#818484;font-size:.88rem}
.ud-rassegna-sintesi{margin:0;color:#5B5F5C;font-size:1.05rem;line-height:1.65}
.ud-rassegna-griglia{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px;margin:0}
.ud-rassegna-card{display:block;text-decoration:none;background:#D9E1DA;border:1px solid #5B5F5C;border-left:4px solid #379557;border-radius:12px;padding:14px 16px;margin:0;transition:transform .15s ease, box-shadow .15s ease}
.ud-rassegna-card:hover{transform:translateY(-2px);box-shadow:0 10px 26px rgba(12,13,13,.14)}
.ud-rassegna-miniatura{display:block;height:158px;background:#5B5F5C;background-size:cover;background-position:center;border-radius:8px;margin-bottom:12px}
.ud-rassegna-t{display:block;color:#0C0D0D;font-weight:700;font-size:1.05rem;line-height:1.3;margin-bottom:6px}
.ud-rassegna-a{display:block;color:#5B5F5C;font-size:.92rem;line-height:1.6;margin-bottom:10px}
.ud-rassegna-d{display:block;color:#818484;font-size:.8rem;letter-spacing:.4px}
.ud-rassegna-piede{margin:24px 0 0;color:#818484;font-size:.82rem;text-align:center}
@media (max-width:640px){.ud-rassegna-griglia{grid-template-columns:1fr}.ud-rassegna-titolo{font-size:1.55rem}.ud-rassegna-miniatura{height:150px}}
</style>"""


def componi(*, titolo: str, data: str, sintesi: str, voci: list[dict],
            occhiello: str = "Rassegna stampa", firma: str = "") -> str:
    """La rassegna intera: testa, griglia delle card, e una riga in fondo.

    Le card sono `<a>` che contengono tutto: miniatura, titolo, abstract, dominio.
    Cosi' l'intera scheda e' cliccabile, e la miniatura resta decorativa (il titolo
    dice gia' di che cosa si tratta) — per questo non ha un `alt`.
    """
    if not voci:
        raise RassegnaError("nessuna voce da impaginare")

    pezzi = [CSS, '<div class="ud-rassegna">']
    pezzi.append('<div class="ud-rassegna-testa">')
    if occhiello:
        pezzi.append(f'<p class="ud-rassegna-occhiello">{_testo(occhiello)}</p>')
    pezzi.append(f'<h2 class="ud-rassegna-titolo">{_testo(titolo)}</h2>')
    if data:
        pezzi.append(f'<p class="ud-rassegna-data">{_testo(data)}</p>')
    if sintesi:
        pezzi.append(f'<p class="ud-rassegna-sintesi">{_testo(sintesi)}</p>')
    pezzi.append("</div>")

    pezzi.append('<div class="ud-rassegna-griglia">')
    for voce in voci:
        sfondo = (f' style="background-image:url({voce["miniatura"]})"'
                  if voce.get("miniatura") else "")
        pezzi.append(
            f'<a class="ud-rassegna-card" href="{_testo(voce.get("url", ""))}" '
            f'target="_blank" rel="noopener">'
            f'<span class="ud-rassegna-miniatura"{sfondo}></span>'
            f'<span class="ud-rassegna-t">{_testo(voce.get("titolo", ""))}</span>'
            f'<span class="ud-rassegna-a">{_testo(voce.get("abstract", ""))}</span>'
            f'<span class="ud-rassegna-d">{_testo(voce.get("dominio", ""))}</span>'
            f'</a>'
        )
    pezzi.append("</div>")

    if firma:
        pezzi.append(f'<p class="ud-rassegna-piede">{_testo(firma)}</p>')
    pezzi.append("</div>")
    return "".join(pezzi)


def valida(markup: str) -> dict:
    """I controlli che si fanno prima di consegnare l'HTML."""
    problemi: list[str] = []
    for blocco in re.findall(r"<style[^>]*>(.*?)</style>", markup, re.S):
        if "&" in blocco:
            problemi.append("il foglio di stile contiene «&»: WordPress lo spezzerebbe")
    if "<script" in markup.lower():
        problemi.append("c'e' uno script: questa impaginazione non ne ha bisogno")
    if markup.count('class="ud-rassegna-card"') == 0:
        problemi.append("nessuna card: non c'e' niente da mostrare")
    for colore in ("#03a07a", "#1b1f29", "#eaeaea", "#ffffff", "#000000"):
        if colore in markup:
            problemi.append(f"colore fuori palette: {colore}")
    aperti = len(re.findall(r'class="ud-rassegna-card"', markup))
    chiusi = markup.count("</a>")
    if aperti != chiusi:
        problemi.append(f"{aperti} card ma {chiusi} chiusure </a>: il markup e' sbilanciato")
    return {
        "ok": not problemi,
        "problemi": problemi,
        "voci": aperti,
        "byte": len(markup.encode("utf-8")),
        "con_miniatura": markup.count("ud-rassegna-miniatura\" style"),
    }


def salva(markup: str, cartella, *, nome: str = "") -> str:
    """Scrive la rassegna su file, pronta da copiare o da caricare."""
    from pathlib import Path
    import datetime

    cartella = Path(cartella)
    cartella.mkdir(parents=True, exist_ok=True)
    marcia = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    percorso = cartella / (nome or f"rassegna-{marcia}.html")
    percorso.write_text(markup, encoding="utf-8", newline="\n")
    return str(percorso)


def riassunto_dati(dati: dict) -> str:
    """Riga di servizio per il registro e per l'interfaccia."""
    return json.dumps({k: v for k, v in dati.items() if k != "markup"}, ensure_ascii=False)
