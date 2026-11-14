"""I canali social: cosa sa fare ciascuno, e come si pubblica.

Un canale ha due tempi, sempre: `prepara` dice cosa uscirebbe senza toccare
niente (e risponde 200 anche quando dice di no), `invia` esegue. Ci si arriva
solo dopo un secondo gesto esplicito dell'utente.
"""

from __future__ import annotations

import urllib.parse
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Canale:
    chiave: str
    etichetta: str
    limite: int
    hashtag_max: int
    immagine: bool
    prompt: str
    fonte_limite: str
    collegato: bool = False          # True = pubblica davvero via API
    file_immagine: str = ""          # obbligo/limite sull'immagine, per l'anteprima
    titolo_etichetta: str = "Titolo / gancio"
    modello_url: str = ""            # compositore web, per la consegna manuale
    nota_immagine: str = ""          # vincolo dell'immagine su quella rete, se c'e'

    # --- credenziali ------------------------------------------------------- #
    def credenziali_mancanti(self, conf: dict) -> list[str]:
        dal_config = (conf.get("canali") or {}).get(self.chiave) or {}
        return [campo for campo, valore in dal_config.items()
                if not campo.startswith("_") and not valore]

    # --- due tempi --------------------------------------------------------- #
    def prepara(self, pubblicazione: dict, conf: dict) -> dict:
        return {
            "canale": self.chiave,
            "etichetta": self.etichetta,
            "collegato": self.collegato,
            "titolo": pubblicazione.get("titolo", ""),
            "testo": pubblicazione.get("testo", ""),
            "misure": self.misure(pubblicazione.get("testo", "")),
            "allegati": [str(Path(p).name) for p in pubblicazione.get("allegati", [])],
            "problemi": self.problemi(pubblicazione, conf),
            "url_compositore": self.url_compositore(pubblicazione),
        }

    def invia(self, pubblicazione: dict, conf: dict) -> dict:
        problemi = [p for p in self.problemi(pubblicazione, conf)
                    if p.get("bloccante")]
        if problemi:
            return {"pubblicato": False, "motivo": problemi[0]["testo"],
                    "problemi": problemi}
        return {
            "pubblicato": False,
            "manuale": True,
            "motivo": (f"{self.etichetta} non e' ancora collegato all'API di pubblicazione: "
                       "apri il compositore e incolla il testo."),
            "url_compositore": self.url_compositore(pubblicazione),
        }

    # --- utilita' ---------------------------------------------------------- #
    def misure(self, testo: str) -> dict:
        caratteri = len(testo)
        return {
            "caratteri": caratteri,
            "limite": self.limite,
            "restanti": self.limite - caratteri,
            "entro": caratteri <= self.limite,
        }

    def problemi(self, pubblicazione: dict, conf: dict) -> list[dict]:
        testo = pubblicazione.get("testo", "") or ""
        allegati = [Path(p) for p in pubblicazione.get("allegati", [])]
        problemi: list[dict] = []

        if not testo.strip():
            problemi.append({"bloccante": True, "testo": "il testo e' vuoto"})
        elif len(testo) > self.limite:
            problemi.append({
                "bloccante": True,
                "testo": (f"il testo e' di {len(testo)} caratteri, {len(testo) - self.limite} "
                          f"oltre il tetto di {self.limite} di {self.etichetta} "
                          "(non lo tronco: va accorciato a mano)"),
            })

        if allegati and not self.immagine:
            problemi.append({"bloccante": True,
                             "testo": f"{self.etichetta} non allega immagini in questo flusso"})
        if self.file_immagine == "obbligatoria" and not allegati:
            problemi.append({"bloccante": True,
                             "testo": f"{self.etichetta} richiede un'immagine"})
        if allegati and self.nota_immagine:
            problemi.append({"bloccante": False,
                             "testo": f"{self.etichetta}: {self.nota_immagine}"})

        mancanti = self.credenziali_mancanti(conf) if self.collegato else []
        if mancanti:
            problemi.append({
                "bloccante": self.collegato,
                "testo": (f"mancano le credenziali di {self.etichetta}: "
                          + ", ".join(mancanti) + " (si impostano in Configurazione)"),
            })
        return problemi

    def url_compositore(self, pubblicazione: dict) -> str:
        if not self.modello_url:
            return ""
        return self.modello_url.format(testo=_testo_url(pubblicazione.get("testo", "")))


REGISTRO: dict[str, Canale] = {}


def registra(canale: Canale) -> Canale:
    REGISTRO[canale.chiave] = canale
    return canale


def elenco() -> list[dict]:
    """Descrittori per l'interfaccia: nessuna funzione, solo dati."""
    return [
        {
            "chiave": c.chiave,
            "etichetta": c.etichetta,
            "limite": c.limite,
            "hashtag_max": c.hashtag_max,
            "immagine": c.immagine,
            "collegato": c.collegato,
            "titolo_etichetta": c.titolo_etichetta,
            "fonte_limite": c.fonte_limite,
            "file_immagine": c.file_immagine,
            "nota_immagine": c.nota_immagine,
        }
        for c in REGISTRO.values()
    ]


def prendi(chiave: str) -> Canale:
    if chiave not in REGISTRO:
        raise KeyError(f"canale sconosciuto: {chiave}")
    return REGISTRO[chiave]


def _testo_url(testo: str, taglia: int = 1600) -> str:
    return urllib.parse.quote(testo[:taglia], safe="")
