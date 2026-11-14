"""La generazione del testo con OpenRouter, e l'adattamento al singolo social.

Un solo punto per la chiamata al modello, cosi' le due funzioni (genera, adatta)
non divergono. Il prompt si costruisce leggendo `parametri.py`: aggiungere un
parametro li' lo fa arrivare qui senza toccare questo file.
"""

from __future__ import annotations

import json
import urllib.error
import urllib.request

import parametri


class GenerazioneError(Exception):
    """Chiamata al modello non riuscita, con il motivo in chiaro."""


def _chiave(conf: dict) -> tuple[str, str, float]:
    llm = conf.get("llm") or {}
    chiave = (llm.get("orKey") or "").strip()
    if not chiave:
        raise GenerazioneError(
            "Manca la chiave di OpenRouter: si imposta in Configurazione. "
            "Senza chiave l'app non inventa contenuti, si ferma e lo dice."
        )
    modello = (llm.get("orModel") or "openai/gpt-4o-mini").strip()
    try:
        temperatura = float(llm.get("temperature", 0.7))
    except (TypeError, ValueError):
        temperatura = 0.7
    return chiave, modello, temperatura


def _chiama(messaggi: list[dict], conf: dict, *, modello: str | None = None,
            max_tokens: int = 2600) -> str:
    chiave, modello_config, temperatura = _chiave(conf)
    corpo = {
        "model": modello or modello_config,
        "messages": messaggi,
        "temperature": temperatura,
        "max_tokens": max_tokens,
        # Alcuni modelli di ragionamento tornano con content vuoto se non li si spegne.
        "reasoning": {"enabled": False},
    }
    indirizzo = (conf.get("llm") or {}).get("orUrl") or "https://openrouter.ai/api/v1"
    richiesta = urllib.request.Request(
        indirizzo.rstrip("/") + "/chat/completions",
        data=json.dumps(corpo).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {chiave}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(richiesta, timeout=180) as risposta:
            dati = json.loads(risposta.read().decode())
    except urllib.error.HTTPError as errore:
        dettaglio = errore.read(600).decode(errors="replace")
        raise GenerazioneError(f"OpenRouter: HTTP {errore.code} — {dettaglio}") from None
    except urllib.error.URLError as errore:
        raise GenerazioneError(f"OpenRouter non raggiungibile: {errore.reason}") from None

    scelte = dati.get("choices") or []
    if not scelte:
        raise GenerazioneError(f"Risposta senza risultati: {str(dati)[:300]}")
    contenuto = (scelte[0].get("message") or {}).get("content") or ""
    if not contenuto.strip():
        raise GenerazioneError(
            "Il modello ha risposto a vuoto. Succede con i modelli di ragionamento "
            "quando il tetto di token e' basso: cambia modello o alza max_tokens."
        )
    return contenuto.strip()


def _estrai_json(testo: str) -> dict:
    """Il modello puo' incorniciare il JSON: si estrae il primo oggetto bilanciato."""
    inizio = testo.find("{")
    while inizio != -1:
        livello, dentro_stringa, fuga = 0, False, False
        for indice in range(inizio, len(testo)):
            carattere = testo[indice]
            if dentro_stringa:
                if fuga:
                    fuga = False
                elif carattere == "\\":
                    fuga = True
                elif carattere == '"':
                    dentro_stringa = False
                continue
            if carattere == '"':
                dentro_stringa = True
            elif carattere == "{":
                livello += 1
            elif carattere == "}":
                livello -= 1
                if livello == 0:
                    try:
                        return json.loads(testo[inizio:indice + 1])
                    except json.JSONDecodeError:
                        break
        inizio = testo.find("{", inizio + 1)
    raise GenerazioneError(f"Il modello non ha restituito JSON leggibile: {testo[:300]}")


def _istruzioni(valori: dict) -> str:
    righe = [
        f"- Tono: {valori.get('tono')}",
        f"- Pubblico: {valori.get('pubblico')}",
        f"- Lingua: {'italiano' if valori.get('lingua') == 'it' else 'inglese'}",
        f"- Punto di vista: {valori.get('punto_di_vista')}",
        f"- Lunghezza: circa {valori.get('lunghezza')} parole",
        f"- Emoji: {'consentite' if valori.get('emoji') else 'vietate'}",
        "- Hashtag: NON inserirli, li aggiunge l'adattamento al singolo social",
    ]
    if valori.get("istruzioni"):
        righe.append(f"- Indicazioni dell'autore (hanno la precedenza): {valori['istruzioni']}")
    return "\n".join(righe)


def _materiale(fonte: dict) -> str:
    pezzi = []
    if fonte.get("titolo"):
        pezzi.append(f"TITOLO DELLA FONTE: {fonte['titolo']}")
    if fonte.get("autore"):
        pezzi.append(f"AUTORE: {fonte['autore']}")
    if fonte.get("url"):
        pezzi.append(f"INDIRIZZO: {fonte['url']}")
    pezzi.append("CONTENUTO:\n" + (fonte.get("testo") or "")[:24000])
    if fonte.get("contesto"):
        pezzi.append("CONTESTO DAL WEB (solo per orientarsi, non citarlo come se fosse la fonte):\n"
                     + fonte["contesto"])
    return "\n\n".join(pezzi)


def genera(fonte: dict, valori: dict | None, conf: dict) -> dict:
    """Titolo + testo di partenza, dal materiale scelto."""
    valori = parametri.normalizza(valori)
    sistema = (
        "Sei un editor che scrive testi destinati ai social di un umanista digitale "
        "che si occupa di intelligenza artificiale, educazione, lifelong learning e "
        "divario digitale.\n" + parametri.STILE_BASE + "\n" + parametri.VIETATI + "\n"
        "Rispondi SOLO con un oggetto JSON con le chiavi \"titolo\" e \"testo\"."
    )
    utente = (
        "Materiale di partenza:\n\n" + _materiale(fonte) +
        "\n\nScrivi un testo nuovo con queste caratteristiche:\n" + _istruzioni(valori) +
        "\n\nIl campo \"titolo\" e' un titolo breve e concreto (max 90 caratteri). "
        "Il campo \"testo\" e' il corpo, in prosa, senza meta-introduzioni."
    )
    grezzo = _chiama(
        [{"role": "system", "content": sistema}, {"role": "user", "content": utente}], conf)
    dati = _estrai_json(grezzo)
    return {"titolo": str(dati.get("titolo", "")).strip(),
            "testo": str(dati.get("testo", "")).strip(),
            "via": "OpenRouter"}


def _chiedi_adattamento(canale, valori, testo, titolo, conf, correzione=None,
                        precedente=None) -> dict:
    """Un tentativo. Al secondo giro base_testo e il tentativo precedente."""
    base_testo = precedente if precedente else testo
    if valori.get("hashtag") and canale.hashtag_max:
        quanto_hashtag = str(canale.hashtag_max) + " hashtag pertinenti in coda"
    else:
        quanto_hashtag = "nessun hashtag"

    # Un tetto chiesto "pari pari" viene sforato: si punta piu' in basso, cosi' l'errore
    # di stima del modello cade dentro il margine invece che fuori.
    margine = max(20, int(canale.limite * 0.12))
    obiettivo = canale.limite - margine

    sistema = (
        "Sei un editor social. Adatti un testo allo stile e ai limiti di una singola "
        "piattaforma, senza tradirne il contenuto.\n" + parametri.STILE_BASE + "\n"
        + parametri.VIETATI + "\n"
        'Rispondi SOLO con un oggetto JSON con le chiavi "titolo" e "testo".'
    )
    righe = [
        "Piattaforma: " + canale.etichetta,
        "Regole di questa piattaforma: " + canale.prompt,
        "Tetto rigido: " + str(canale.limite) + " caratteri per il campo testo. "
        "Scrivi al massimo " + str(obiettivo) + " caratteri: meglio corto che fuori misura.",
        "Hashtag: " + quanto_hashtag + ".",
        "Emoji: " + ("consentite" if valori.get("emoji") else "vietate") + ".",
        "Lingua: " + ("italiano" if valori.get("lingua") == "it" else "inglese") + ".",
        "Tono: " + str(valori.get("tono")) + ". Pubblico: " + str(valori.get("pubblico")) + ".",
    ]
    if valori.get("istruzioni"):
        righe.append("Indicazioni dell'autore: " + str(valori["istruzioni"]))
    righe += [
        "",
        "Titolo di partenza:",
        titolo or "(nessuno)",
        "",
        "Testo di partenza:",
        base_testo or "",
        "",
        'Il campo "titolo" e\' un gancio breve (max 90 caratteri). '
        'Il campo "testo" e\' il post finito, dentro il tetto.',
    ]
    if correzione:
        righe += [
            "",
            "Il testo qui sopra e' di " + str(correzione[0]) + " caratteri: e' TROPPO LUNGO.",
            "Riscrivilo in NON PIU' di " + str(correzione[1]) + " caratteri. "
            "Taglia frasi intere e aggettivi, non cambiare il senso. "
            "Conta i caratteri del risultato prima di rispondere.",
        ]

    grezzo = _chiama(
        [{"role": "system", "content": sistema}, {"role": "user", "content": "\n".join(righe)}],
        conf, modello=(conf.get("llm") or {}).get("orModelAdatta") or None)
    return _estrai_json(grezzo)


def adatta(testo: str, titolo: str, canale, valori: dict | None, conf: dict) -> dict:
    """Riscrive titolo e testo per un social preciso.

    Il modello non sa contare i caratteri in modo affidabile, quindi non ci si fida
    della sua stima: si MISURA il risultato e, se sfora, glielo si dice con il numero
    vero. Al massimo tre tentativi, poi si consegna il testo dicendo che ha sforato:
    troncarlo cambierebbe il senso senza dirlo.
    """
    valori = parametri.normalizza(valori)
    obiettivo = canale.limite - max(20, int(canale.limite * 0.12))

    dati: dict = {}
    correzione = None
    precedente = None
    finale = ""
    tentativi = 0
    while tentativi < 3:
        tentativi += 1
        dati = _chiedi_adattamento(canale, valori, testo, titolo, conf, correzione, precedente)
        finale = str(dati.get("testo", "")).strip()
        if canale.misure(finale)["entro"]:
            break
        correzione = (len(finale), obiettivo)
        precedente = finale

    testo_finale = str(dati.get("testo", "")).strip()
    misure = canale.misure(testo_finale)
    misure["tentativi"] = tentativi
    return {"titolo": str(dati.get("titolo", "")).strip(),
            "testo": testo_finale,
            "misure": misure,
            "via": "OpenRouter"}
