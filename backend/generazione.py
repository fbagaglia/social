"""La generazione del testo con OpenRouter, e l'adattamento al singolo social.

Un solo punto per la chiamata al modello, cosi' le due funzioni (genera, adatta)
non divergono. Il prompt si costruisce leggendo `parametri.py`: aggiungere un
parametro li' lo fa arrivare qui senza toccare questo file.
"""

from __future__ import annotations

import json
import re
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


# --------------------------------------------------------------------------- #
# Il magazine: articolo, FAQ, campi SEO.
#
# Stessa regola dell'adattamento social, e vale soprattutto qui: il modello NON sa
# contare i caratteri. Per i campi SEO il tetto non si chiede — si misura e, se sfora,
# glielo si dice con il numero vero. Il testo dell'articolo invece non ha tetto: li'
# conta la forma (lede, sezioni, risposte autosufficienti).
# --------------------------------------------------------------------------- #

LIMITE_SEO_TITLE = 60
LIMITE_SEO_DESCRIPTION = 160

SISTEMA_MAGAZINE = (
    "Sei l'assistente editoriale di Umanesimo Digitale, un magazine multilingue di "
    "cultura digitale e umanesimo digitale. Scrivi in italiano.\n"
    "Tono: caldo, accessibile, saggistico, umanistico, concreto. Mai accademese, mai "
    "gergo tecnico fine a se stesso: ancora sempre la tecnologia alle persone.\n"
    + parametri.VIETATI + "\n"
    "Regole di scrittura: lede di 2-3 frasi che risponde alla domanda del titolo; "
    "sezioni brevi e scansionabili; esempi concreti; entita' nominate; niente "
    "statistiche, citazioni o numeri inventati; niente superlativi non verificabili; "
    "acronimi spiegati alla prima occorrenza; voce attiva.\n"
    "Non usare mai: delve, landscape, game-changer, in today's fast-paced world, "
    "e gli altri cliche' da modello linguistico."
)


def articolo_da_fonte(fonte: dict, valori: dict | None, conf: dict, *,
                       come_si_aprono: str = "## ") -> dict:
    """Il corpo dell'articolo, con le sezioni gia' marcate.

    I titoli di sezione si chiedono nel formato che il canale sa leggere (una riga che
    comincia con `## `): cosi' il campo di testo resta leggibile e la conversione in
    blocchi Gutenberg non richiede nessun altro passaggio.
    """
    valori = parametri.normalizza(valori or {})
    quante = int(valori.get("paragrafi") or 9)
    sistema = SISTEMA_MAGAZINE + (
        '\nRispondi SOLO con un oggetto JSON con le chiavi '
        '"titolo", "gancio", "sintesi", "testo", "slug".'
    )
    utente = (
        "Materiale di partenza:\n\n" + _materiale(fonte) + "\n\n"
        f"Scrivi un articolo con circa {quante} paragrafi oltre al lede, in italiano.\n"
        f'- "titolo": il titolo dell\'articolo, concreto, senza due punti se non servono '
        "(max 90 caratteri).\n"
        '- "gancio": un titolo-gancio breve (max 60 caratteri) che sta sopra l\'apertura. '
        "E' una frase memorabile, non la ripetizione del titolo.\n"
        '- "sintesi": UNA frase che riassume l\'articolo (max 220 caratteri). Diventa la '
        "frase in corsivo dell'occhiello.\n"
        f'- "testo": il corpo. Il PRIMO paragrafo e\' il lede (2-3 frasi, nessun titolo '
        "sopra). Ogni sezione successiva comincia con una riga che inizia esattamente con "
        f'"{come_si_aprono}" seguito dal titolo della sezione, poi i paragrafi di quella '
        "sezione. Almeno tre sezioni. Un paragrafo per riga: il testo NON va incolonnato.\n"
        '- "slug": lo slug suggerito, minuscolo, con i trattini.\n'
        "Non aggiungere FAQ, non aggiungere note finali, non aggiungere spiegazioni."
    )
    dati = _estrai_json(_chiama(
        [{"role": "system", "content": sistema}, {"role": "user", "content": utente}], conf,
        max_tokens=6000))
    return {
        "titolo": str(dati.get("titolo", "")).strip(),
        "gancio": str(dati.get("gancio", "")).strip(),
        "sintesi": str(dati.get("sintesi", "")).strip(),
        "testo": _pulisci_sezioni(str(dati.get("testo", "")).strip(), come_si_aprono),
        "slug": _slug(str(dati.get("slug", "")).strip() or str(dati.get("titolo", ""))),
        "via": "OpenRouter",
    }


def _pulisci_sezioni(testo: str, prefisso: str) -> str:
    """I modelli incorniciano i titoli come capita: `### Titolo`, `Titolo:` su riga sua.

    Si normalizza tutto al prefisso che il canale legge, senza toccare le parole.
    """
    righe = []
    for riga in testo.splitlines():
        spoglia = riga.strip()
        if not spoglia:
            righe.append("")
            continue
        if spoglia.startswith(prefisso):
            righe.append(prefisso + spoglia[len(prefisso):].strip())
            continue
        if re.match(r"^#{1,6}\s+\S", spoglia):            # ## oppure ### oppure #
            righe.append(prefisso + re.sub(r"^#{1,6}\s+", "", spoglia).strip())
            continue
        righe.append(spoglia)
    return "\n".join(righe).strip()


def _slug(testo: str) -> str:
    senza = re.sub(r"[^\w\s-]", "", testo.lower(), flags=re.UNICODE)
    return re.sub(r"[-\s]+", "-", senza).strip("-")[:70]


def faq_da_testo(testo: str, titolo: str, conf: dict, *, quante: int = 4) -> list[dict]:
    """Da 3 a 5 domande reali, ognuna con la risposta che si regge da sola.

    Le domande non si inventano: se il testo non risponde a niente di sensato, meglio
    non avere la sezione. Per questo si chiede al modello di segnalare quando non ce ne
    sono, invece di riempire per forza.
    """
    sistema = SISTEMA_MAGAZINE + (
        '\nRispondi SOLO con un oggetto JSON con la chiave "faq".'
    )
    utente = (
        f"Titolo dell'articolo: {titolo or '(senza titolo)'}\n\n"
        f"Testo dell'articolo:\n\n{testo[:20000]}\n\n"
        f"Scrivi da 3 a {quante} domande frequenti VERE, del tipo che un lettore si "
        "porrebbe davvero leggendo questo articolo. Ognuna deve avere una risposta "
        "autosufficiente di 2-3 frasi, che non rimanda ad altre domande e non inventa "
        "dati che non siano nel testo.\n"
        'Formato: {"faq": [{"domanda": "...", "risposta": "..."}]}\n'
        "Se dal testo non emergono almeno tre domande sensate, rispondi con \"faq\": []."
    )
    dati = _estrai_json(_chiama(
        [{"role": "system", "content": sistema}, {"role": "user", "content": utente}], conf))
    voci = []
    for voce in (dati.get("faq") or [])[:5]:
        domanda = str(voce.get("domanda", "")).strip()
        risposta = str(voce.get("risposta", "")).strip()
        if domanda and risposta:
            voci.append({"domanda": domanda, "risposta": risposta})
    return voci


def seo_da_articolo(titolo: str, testo: str, sintesi: str, conf: dict) -> dict:
    """SEO title, meta description, parola chiave e slug — misurati, non stimati.

    I tetti sono **rigidi e si controllano in codice**: se il modello sfora, glielo si
    dice con il numero vero e si riprova. Al terzo giro si taglia alle parole, dicendolo:
    un titolo SEO troncato a meta' parola e' peggio di un titolo un po' piu' corto.
    """
    sistema = SISTEMA_MAGAZINE + (
        '\nRispondi SOLO con un oggetto JSON con le chiavi "seo_title", '
        '"seo_description", "focus_keyword".'
    )
    utente = (
        f"Titolo dell'articolo: {titolo}\n"
        f"Sintesi: {sintesi}\n\n"
        f"Testo:\n\n{testo[:20000]}\n\n"
        "Scrivi i campi SEO del magazine:\n"
        f'- "seo_title": massimo {LIMITE_SEO_TITLE} caratteri. E\' il titolo che compare '
        "su Google: deve invogliare al clic, non essere la copia del titolo dell'articolo.\n"
        f'- "seo_description": massimo {LIMITE_SEO_DESCRIPTION} caratteri. Deve dire cosa '
        "trova chi clicca, in modo concreto.\n"
        '- "focus_keyword": la frase di 2-4 parole su cui l\'articolo vuole essere trovato.'
    )
    dati = _estrai_json(_chiama(
        [{"role": "system", "content": sistema}, {"role": "user", "content": utente}], conf))

    seo_title = str(dati.get("seo_title", "")).strip()
    seo_desc = str(dati.get("seo_description", "")).strip()
    parola = str(dati.get("focus_keyword", "")).strip()
    corretto = False

    for _ in range(2):
        fuori = []
        if len(seo_title) > LIMITE_SEO_TITLE:
            fuori.append(f"il SEO title e' di {len(seo_title)} caratteri, il tetto e' {LIMITE_SEO_TITLE}")
        if len(seo_desc) > LIMITE_SEO_DESCRIPTION:
            fuori.append(f"la meta description e' di {len(seo_desc)} caratteri, il tetto e' {LIMITE_SEO_DESCRIPTION}")
        if not fuori:
            break
        corretto = True
        dati = _estrai_json(_chiama(
            [{"role": "system", "content": sistema},
             {"role": "user", "content": utente + "\n\nIl tentativo precedente sforava:\n"
              + "\n".join(fuori) + "\n\nRiscrivi RISPETTANDO i tetti. Conta i caratteri "
              "prima di rispondere."}], conf))
        seo_title = str(dati.get("seo_title", "")).strip()
        seo_desc = str(dati.get("seo_description", "")).strip()
        parola = str(dati.get("focus_keyword", "")).strip() or parola

    return {
        "seo_title": _accorcia(seo_title, LIMITE_SEO_TITLE),
        "seo_description": _accorcia(seo_desc, LIMITE_SEO_DESCRIPTION),
        "focus_keyword": parola,
        "slug": _slug(titolo),
        "misure": {
            "seo_title": {"caratteri": len(seo_title), "limite": LIMITE_SEO_TITLE},
            "seo_description": {"caratteri": len(seo_desc), "limite": LIMITE_SEO_DESCRIPTION},
        },
        "corretto_dopo_sforamento": corretto,
        "via": "OpenRouter",
    }


def _accorcia(testo: str, limite: int) -> str:
    """Taglio alle parole, e non a meta' parola. Si usa solo se il modello ha sforato
    due volte: e' l'ultima rete, non la norma."""
    if len(testo) <= limite:
        return testo
    tagliato = testo[:limite + 1]
    if " " in tagliato:
        tagliato = tagliato[:tagliato.rfind(" ")]
    return tagliato.rstrip(" ,;:-")
