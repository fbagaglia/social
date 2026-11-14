"""Le immagini: quelle caricate dall'utente e quelle generate dall'app.

La generazione e' grafica, non AI: testo nitido su una tavolozza fissa. Se in futuro
si aggiunge un'immagine di sfondo generata da un modello, va dichiarata come tale
(AI Act art. 50): l'app non la spaccia per fotografia.
"""

from __future__ import annotations

import re
import secrets
import unicodedata
from pathlib import Path

import config as cfg

TAVOLOZZA = {
    "fondo": "#0C0D0D",
    "accento": "#379557",
    "carta": "#D9E1DA",
    "grigio_scuro": "#5B5F5C",
    "grigio_chiaro": "#818484",
}

FORMATI = {
    "orizzontale": (1200, 675),   # 16:9 — X, LinkedIn, Facebook
    "quadrato": (1080, 1080),     # Instagram, Threads
    "verticale": (1080, 1350),    # 4:5 — feed Instagram
}

ESTENSIONI = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
TETTO_BYTE = 8 * 1024 * 1024


class ImmagineError(Exception):
    """Immagine non accettata o non generabile, con il motivo in chiaro."""


def _nome_sicuro(nome: str) -> str:
    """Dal nome che arriva dal client si prende SOLO il nome, ripulito."""
    base = Path(nome).name
    base = unicodedata.normalize("NFKD", base).encode("ascii", "ignore").decode()
    base = re.sub(r"[^A-Za-z0-9._-]+", "-", base).strip("-.") or "immagine"
    return base[:80]


def percorso_nuovo(nome: str) -> Path:
    cfg.assicura_cartelle()
    base = _nome_sicuro(nome)
    candidato = cfg.CARTELLA_ALLEGATI / base
    if candidato.exists():  # non si sovrascrive mai: il doppione prende un suffisso
        candidato = cfg.CARTELLA_ALLEGATI / f"{candidato.stem}-{secrets.token_hex(3)}{candidato.suffix}"
    return candidato


def salva_caricata(nome: str, contenuto: bytes) -> dict:
    if not contenuto:
        raise ImmagineError("Il file e' arrivato vuoto.")
    if len(contenuto) > TETTO_BYTE:
        raise ImmagineError(
            f"Il file pesa {len(contenuto) / 1048576:.1f} MB, oltre il tetto di "
            f"{TETTO_BYTE // 1048576} MB.")
    estensione = Path(nome).suffix.lower()
    if estensione not in ESTENSIONI:
        raise ImmagineError(
            "Formato non ammesso: " + estensione + ". Ammessi: " + ", ".join(sorted(ESTENSIONI)))
    percorso = percorso_nuovo(nome)
    percorso.write_bytes(contenuto)
    larghezza, altezza = misura(percorso)
    return {"percorso": str(percorso), "nome": percorso.name,
            "larghezza": larghezza, "altezza": altezza,
            "peso": len(contenuto), "via": "caricata"}


def misura(percorso: Path) -> tuple[int, int]:
    try:
        from PIL import Image
    except ImportError:
        return 0, 0
    try:
        with Image.open(percorso) as immagine:
            return immagine.width, immagine.height
    except Exception:
        return 0, 0


# --------------------------------------------------------------------------- #
# Generazione grafica (testo nitido, non AI)
# --------------------------------------------------------------------------- #

def _font(dimensione: int, grassetto: bool = False):
    from PIL import ImageFont

    candidati = [
        Path("C:/Windows/Fonts") / ("segoeuib.ttf" if grassetto else "segoeui.ttf"),
        Path("C:/Windows/Fonts") / ("arialbd.ttf" if grassetto else "arial.ttf"),
    ]
    for percorso in candidati:
        if percorso.exists():
            try:
                return ImageFont.truetype(str(percorso), dimensione)
            except OSError:
                continue
    return ImageFont.load_default()


def _a_capo(penna, testo: str, font, larghezza_max: int) -> list[str]:
    righe: list[str] = []
    for paragrafo in testo.split("\n"):
        parole = paragrafo.split()
        if not parole:
            righe.append("")
            continue
        corrente = ""
        for parola in parole:
            prova = f"{corrente} {parola}".strip()
            if penna.textlength(prova, font=font) <= larghezza_max:
                corrente = prova
            else:
                if corrente:
                    righe.append(corrente)
                corrente = parola
        if corrente:
            righe.append(corrente)
    return righe


def genera_pannello(titolo: str, sottotitolo: str = "", firma: str = "",
                    formato: str = "orizzontale", tavolozza: dict | None = None) -> dict:
    """Una card con testo nitido: fondo scuro, barretta d'accento, titolo grande."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        raise ImmagineError("Pillow non e' disponibile: la generazione grafica e' spenta.")
    if formato not in FORMATI:
        raise ImmagineError("Formato sconosciuto: " + formato)
    if not titolo.strip():
        raise ImmagineError("Serve almeno il titolo da mettere nell'immagine.")

    colori = dict(TAVOLOZZA, **(tavolozza or {}))
    larghezza, altezza = FORMATI[formato]
    immagine = Image.new("RGB", (larghezza, altezza), colori["fondo"])
    penna = ImageDraw.Draw(immagine)

    margine = int(larghezza * 0.085)
    spessore = max(8, larghezza // 90)
    penna.rectangle([margine, margine, margine + spessore, altezza - margine],
                    fill=colori["accento"])

    sinistra = margine + spessore + int(larghezza * 0.045)
    larghezza_testo = larghezza - sinistra - margine
    font_titolo = _font(int(altezza * 0.095), grassetto=True)
    font_sotto = _font(int(altezza * 0.042))
    font_firma = _font(int(altezza * 0.033))

    righe = _a_capo(penna, titolo.strip(), font_titolo, larghezza_testo)
    altezza_riga = int(altezza * 0.115)
    blocco = len(righe) * altezza_riga + (int(altezza * 0.10) if sottotitolo else 0)
    y = max(margine, (altezza - blocco) // 2 - int(altezza * 0.03))

    for riga in righe:
        penna.text((sinistra, y), riga, font=font_titolo, fill=colori["carta"])
        y += altezza_riga

    if sottotitolo:
        y += int(altezza * 0.035)
        for riga in _a_capo(penna, sottotitolo.strip(), font_sotto, larghezza_testo)[:4]:
            penna.text((sinistra, y), riga, font=font_sotto, fill=colori["grigio_chiaro"])
            y += int(altezza * 0.058)

    if firma:
        penna.text((sinistra, altezza - margine - int(altezza * 0.045)), firma.strip(),
                   font=font_firma, fill=colori["accento"])

    percorso = percorso_nuovo("pannello.png")
    immagine.save(percorso, "PNG", optimize=True)
    return {"percorso": str(percorso), "nome": percorso.name,
            "larghezza": larghezza, "altezza": altezza,
            "peso": percorso.stat().st_size, "via": "generata dall'app (grafica, non AI)"}


def controlla(percorso) -> tuple[bool, str]:
    cammino = Path(percorso)
    if not cammino.exists():
        return False, "immagine inesistente"
    estensione = cammino.suffix.lower()
    if estensione not in ESTENSIONI:
        return False, "formato non ammesso: " + estensione
    return True, ""
