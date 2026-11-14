"""Le tre fonti di partenza: un testo incollato, un link, un video YouTube.

Ogni lettura dichiara per quale via ha ottenuto il materiale (`via`) e, quando
fallisce, elenca le vie provate invece di dire solo che non e' riuscita.
"""

from __future__ import annotations

import html
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

import config as cfg

FOTOCOPIABILI = 1_500_000  # tetto di sicurezza sul corpo scaricato


class FonteError(Exception):
    """Lettura della fonte non riuscita, con il perche' e le vie provate."""


# --------------------------------------------------------------------------- #
# Rete
# --------------------------------------------------------------------------- #

def _http(url: str, *, dati: bytes | None = None, intestazioni: dict | None = None,
          metodo: str | None = None, timeout: int = 30) -> bytes:
    testa = {"User-Agent": "SocialStudio/1.0 (+locale)"}
    testa.update(intestazioni or {})
    req = urllib.request.Request(url, data=dati, headers=testa, method=metodo)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as risposta:
            return risposta.read(FOTOCOPIABILI)
    except urllib.error.HTTPError as errore:
        dettaglio = errore.read(500).decode(errors="replace")
        raise FonteError(f"{url}: HTTP {errore.code} {dettaglio}") from None
    except urllib.error.URLError as errore:
        raise FonteError(f"{url}: rete non raggiungibile ({errore.reason})") from None


def _host_vietato(url: str) -> str | None:
    """Una rotta che scarica un indirizzo scelto dall'utente e' una porta di servizio."""
    pezzi = urllib.parse.urlsplit(url)
    if pezzi.scheme not in ("http", "https"):
        return f"schema non ammesso: {pezzi.scheme or '(nessuno)'}"
    host = (pezzi.hostname or "").lower()
    if not host:
        return "indirizzo senza host"
    if host in ("localhost", "::1", "0.0.0.0") or host.endswith(".local"):
        return "indirizzo interno (loopback)"
    if host.startswith("127.") or host.startswith("10.") or host.startswith("192.168."):
        return "indirizzo di rete privata"
    if re.match(r"^172\.(1[6-9]|2\d|3[01])\.", host):
        return "indirizzo di rete privata"
    return None


def _pulisci_html(grezzo: str) -> str:
    grezzo = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", grezzo)
    grezzo = re.sub(r"(?is)<br\s*/?>|</p>|</div>|</li>|</h[1-6]>", "\n", grezzo)
    grezzo = re.sub(r"(?s)<[^>]+>", " ", grezzo)
    grezzo = html.unescape(grezzo)
    grezzo = re.sub(r"[ \t\u00a0]+", " ", grezzo)
    grezzo = re.sub(r"\n\s*\n\s*\n+", "\n\n", grezzo)
    return grezzo.strip()


def _titolo_html(grezzo: str) -> str:
    trovato = re.search(r"(?is)<title[^>]*>(.*?)</title>", grezzo)
    return html.unescape(trovato.group(1)).strip() if trovato else ""


# --------------------------------------------------------------------------- #
# Link
# --------------------------------------------------------------------------- #

def da_link(url: str, *, ricerca: bool = True, chiavi: dict | None = None) -> dict:
    """Testo da una pagina. Vie: Firecrawl, poi lettura diretta."""
    chiavi = chiavi or {}
    divieto = _host_vietato(url)
    if divieto:
        raise FonteError(f"Indirizzo rifiutato: {divieto}")

    vie_provate: list[str] = []
    testo = ""
    titolo = ""
    via = ""

    chiave_firecrawl = chiavi.get("firecrawlKey") or ""
    if ricerca and chiave_firecrawl:
        try:
            corpo = json.dumps({"url": url, "formats": ["markdown"], "onlyMainContent": True}).encode()
            risposta = json.loads(_http(
                "https://api.firecrawl.dev/v1/scrape", dati=corpo,
                intestazioni={"Content-Type": "application/json",
                              "Authorization": f"Bearer {chiave_firecrawl}"},
            ).decode())
            dati = risposta.get("data") or {}
            testo = (dati.get("markdown") or "").strip()
            titolo = (dati.get("metadata") or {}).get("title") or ""
            if testo:
                via = "Firecrawl"
        except (FonteError, json.JSONDecodeError, KeyError) as errore:
            vie_provate.append(f"Firecrawl: {errore}")

    if not testo:
        try:
            grezzo = _http(url, intestazioni={"Accept": "text/html,application/xhtml+xml"}).decode(
                "utf-8", errors="replace")
            testo = _pulisci_html(grezzo)
            titolo = titolo or _titolo_html(grezzo)
            via = "lettura diretta della pagina"
        except FonteError as errore:
            vie_provate.append(f"lettura diretta: {errore}")

    if not testo:
        raise FonteError("Non sono riuscito a leggere il contenuto. Vie provate:\n- " +
                         "\n- ".join(vie_provate or ["nessuna"]))

    contesto = ""
    chiave_brave = chiavi.get("braveKey") or ""
    if ricerca and chiave_brave:
        try:
            contesto = _ricerca_brave(titolo or url, chiave_brave)
        except FonteError:
            contesto = ""

    return {"tipo": "link", "url": url, "titolo": titolo, "testo": testo,
            "contesto": contesto, "via": via, "vie_provate": vie_provate}


def _ricerca_brave(domanda: str, chiave: str, quanti: int = 4) -> str:
    """Contesto aggiuntivo dal web. Brave e' l'alternativa a Firecrawl."""
    query = urllib.parse.urlencode({"q": domanda[:200], "count": quanti})
    risposta = json.loads(_http(
        f"https://api.search.brave.com/res/v1/web/search?{query}",
        intestazioni={"Accept": "application/json", "X-Subscription-Token": chiave},
    ).decode())
    righe = []
    for voce in ((risposta.get("web") or {}).get("results") or [])[:quanti]:
        righe.append(f"- {voce.get('title', '')}: {voce.get('description', '')} ({voce.get('url', '')})")
    return "\n".join(righe)


# --------------------------------------------------------------------------- #
# Video YouTube
# --------------------------------------------------------------------------- #

def id_youtube(url: str) -> str:
    pezzi = urllib.parse.urlsplit(url)
    host = (pezzi.hostname or "").lower()
    if host.endswith("youtu.be"):
        return pezzi.path.lstrip("/").split("/")[0]
    if "youtube" in host:
        if pezzi.path.startswith("/watch"):
            return urllib.parse.parse_qs(pezzi.query).get("v", [""])[0]
        for prefisso in ("/embed/", "/shorts/", "/live/"):
            if pezzi.path.startswith(prefisso):
                return pezzi.path[len(prefisso):].split("/")[0]
    return ""


def da_video(url: str, *, ricerca: bool = True, chiavi: dict | None = None) -> dict:
    """Trascrizione e metadati di un video YouTube. Vie: transcript API, poi yt-dlp."""
    chiavi = chiavi or {}
    divieto = _host_vietato(url)
    if divieto:
        raise FonteError(f"Indirizzo rifiutato: {divieto}")
    video = id_youtube(url)
    if not video:
        raise FonteError("Non riconosco l'identificativo del video in questo indirizzo.")

    vie_provate: list[str] = []
    titolo, autore, descrizione, trascrizione, via = "", "", "", "", ""

    try:
        titolo, autore, descrizione = _metadati_youtube(url)
    except FonteError as errore:
        vie_provate.append(f"metadati oEmbed: {errore}")

    try:
        trascrizione = _trascrizione_api(video)
        if trascrizione:
            via = "youtube-transcript-api"
    except Exception as errore:  # la libreria cambia firma fra versioni
        vie_provate.append(f"youtube-transcript-api: {type(errore).__name__}: {errore}")

    if not trascrizione:
        try:
            trascrizione = _trascrizione_ytdlp(url)
            if trascrizione:
                via = "yt-dlp (sottotitoli automatici)"
        except Exception as errore:
            vie_provate.append(f"yt-dlp: {type(errore).__name__}: {errore}")

    if not trascrizione:
        raise FonteError(
            "Nessuna trascrizione disponibile per questo video. Vie provate:\n- " +
            "\n- ".join(vie_provate or ["nessuna"]) +
            "\nRimedio: incolla a mano il testo, oppure usa un video con i sottotitoli attivi."
        )

    contesto = ""
    chiave_brave = chiavi.get("braveKey") or ""
    if ricerca and chiave_brave and titolo:
        try:
            contesto = _ricerca_brave(titolo, chiave_brave)
        except FonteError:
            contesto = ""

    return {"tipo": "video", "url": url, "video_id": video, "titolo": titolo,
            "autore": autore, "descrizione": descrizione, "testo": trascrizione,
            "contesto": contesto, "via": via, "vie_provate": vie_provate}


def _metadati_youtube(url: str) -> tuple[str, str, str]:
    indirizzo = "https://www.youtube.com/oembed?" + urllib.parse.urlencode(
        {"url": url, "format": "json"})
    dati = json.loads(_http(indirizzo).decode())
    return dati.get("title", ""), dati.get("author_name", ""), ""


def _trascrizione_api(video: str) -> str:
    from youtube_transcript_api import YouTubeTranscriptApi  # import pigro

    api = YouTubeTranscriptApi()
    if hasattr(api, "fetch"):  # versioni recenti
        provato = api.fetch(video, languages=["it", "en"])
        pezzi = list(provato)
        return " ".join(getattr(p, "text", "") or p.get("text", "") for p in pezzi).strip()
    pezzi = YouTubeTranscriptApi.get_transcript(video, languages=["it", "en"])  # versioni vecchie
    return " ".join(p.get("text", "") for p in pezzi).strip()


def _trascrizione_ytdlp(url: str) -> str:
    """Ultima via: i sottotitoli automatici, scaricati da yt-dlp."""
    import subprocess
    import tempfile

    with tempfile.TemporaryDirectory() as cartella:
        subprocess.run(
            ["yt-dlp", "--skip-download", "--write-auto-subs", "--write-subs",
             "--sub-langs", "it.*,en.*", "--sub-format", "vtt",
             "-o", str(Path(cartella) / "v.%(ext)s"), url],
            capture_output=True, timeout=180,
        )
        for file in sorted(Path(cartella).glob("*.vtt")):
            testo = _pulisci_vtt(file.read_text(encoding="utf-8", errors="replace"))
            if testo:
                return testo
    return ""


def _pulisci_vtt(grezzo: str) -> str:
    righe: list[str] = []
    for riga in grezzo.splitlines():
        riga = riga.strip()
        if not riga or riga.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            continue
        if "-->" in riga or riga.isdigit():
            continue
        riga = re.sub(r"<[^>]+>", "", riga).strip()
        if riga and (not righe or righe[-1] != riga):
            righe.append(riga)
    return " ".join(righe)
