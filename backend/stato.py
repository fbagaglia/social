"""Lo stato che sopravvive alla chiusura della pagina.

Due cose sole: il lavoro in corso (per non perderlo ricaricando) e il registro di
cio' che e' uscito davvero verso l'esterno. Il registro serve a rispondere alla
domanda "cosa ho pubblicato?" senza chiederlo a X.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import config as cfg


def percorso_corrente() -> Path:
    cfg.assicura_cartelle()
    return cfg.CARTELLA_DATA / "corrente.json"


def salva_corrente(dati: dict) -> dict:
    dati = dict(dati)
    dati["_salvato_il"] = datetime.now().isoformat(timespec="seconds")
    percorso = percorso_corrente()
    percorso.write_text(json.dumps(dati, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"salvato": True, "quando": dati["_salvato_il"]}


def leggi_corrente() -> dict:
    percorso = percorso_corrente()
    if not percorso.exists():
        return {}
    try:
        return json.loads(percorso.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}


def percorso_registro() -> Path:
    cfg.assicura_cartelle()
    return cfg.CARTELLA_DATA / "pubblicazioni.jsonl"


def registra_pubblicazione(voce: dict) -> dict:
    voce = dict(voce)
    voce["quando"] = datetime.now().isoformat(timespec="seconds")
    with percorso_registro().open("a", encoding="utf-8") as file:
        file.write(json.dumps(voce, ensure_ascii=False) + "\n")
    return voce


def leggi_registro(quante: int = 30) -> list[dict]:
    percorso = percorso_registro()
    if not percorso.exists():
        return []
    righe = percorso.read_text(encoding="utf-8").splitlines()[-quante:]
    voci = []
    for riga in righe:
        try:
            voci.append(json.loads(riga))
        except json.JSONDecodeError:
            continue
    return list(reversed(voci))
