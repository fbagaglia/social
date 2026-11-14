"""I canali concreti: X pubblica davvero, gli altri si preparano e si consegnano.

Le fonti dei tetti di caratteri sono dichiarate per canale. I valori sono stati
incrociati su piu' contatori indipendenti (novembre 2026) e le reti li cambiano:
prima di fidarsi di un numero, rimisurarlo sul proprio account.
"""

from __future__ import annotations

from canali.base import Canale, registra, _testo_url

# --------------------------------------------------------------------------- #

CONSIGLIO_HASHTAG = {
    3: "2-3 hashtag, in coda",
    4: "3-4 hashtag, in coda",
    5: "3-5 hashtag, in coda",
    8: "5-8 hashtag, in coda",
}


class CanaleX(Canale):
    def problemi(self, pubblicazione: dict, conf: dict) -> list[dict]:
        from . import x as ponte

        problemi = super().problemi(pubblicazione, conf)
        costo = ponte.costo_stimato(pubblicazione.get("testo", ""))
        if costo > ponte.COSTO_TESTO_O_MEDIA:
            problemi.append({
                "bloccante": False,
                "testo": (f"il testo contiene un indirizzo web: su X questo post costa circa "
                          f"${costo:.2f} invece di ${ponte.COSTO_TESTO_O_MEDIA:.3f}. "
                          "Se vuoi risparmiare, togli il link dal testo (mettilo nell'immagine "
                          "o in bio) e ripubblica l'anteprima."),
            })
        return problemi

    def prepara(self, pubblicazione: dict, conf: dict) -> dict:
        from . import x as ponte

        base = super().prepara(pubblicazione, conf)
        base["costo_stimato_usd"] = ponte.costo_stimato(pubblicazione.get("testo", ""))
        try:
            base["a_nome_di"] = ponte.account(conf)
        except BaseException as errore:  # il motore esce con SystemExit: va fermato qui
            base["a_nome_di"] = None
            gia_detto = any("credenziali" in p["testo"] for p in base["problemi"])
            if not gia_detto:
                base["problemi"] = base["problemi"] + [
                    {"bloccante": True, "testo": str(errore)}
                ]
        return base

    def invia(self, pubblicazione: dict, conf: dict) -> dict:
        from . import x as ponte

        problemi = [p for p in self.problemi(pubblicazione, conf) if p.get("bloccante")]
        if problemi:
            return {"pubblicato": False, "motivo": problemi[0]["testo"], "problemi": problemi}
        try:
            esito = ponte.pubblica(pubblicazione, conf)
        except BaseException as errore:  # idem: SystemExit non e' un Exception
            return {"pubblicato": False, "motivo": str(errore)}
        return esito

    def url_compositore(self, pubblicazione: dict) -> str:
        # Testo soltanto: l'intent di X non allega immagini.
        return "https://x.com/intent/post?text=" + _testo_url(pubblicazione.get("testo", ""))


# --------------------------------------------------------------------------- #
# X — l'unico collegato all'API di pubblicazione
# --------------------------------------------------------------------------- #

registra(CanaleX(
    chiave="x",
    etichetta="X / Twitter",
    limite=280,
    hashtag_max=3,
    immagine=True,
    collegato=True,
    prompt=("Post per X/Twitter (max 280 caratteri): diretto e incisivo, 2-3 hashtag, "
            "niente link di condivisione, tono adatto a X."),
    fonte_limite="docs.x.com (limite account senza Premium) e contatori indipendenti",
))

# --------------------------------------------------------------------------- #
# Gli altri: anteprima, testo pronto e apertura del compositore
# --------------------------------------------------------------------------- #

registra(Canale(
    chiave="linkedin",
    etichetta="LinkedIn",
    limite=3000,
    hashtag_max=5,
    immagine=True,
    prompt=("Post professionale per LinkedIn (max 3000 caratteri): gancio nelle prime 2 righe, "
            "3-5 hashtag pertinenti, una domanda finale per stimolare i commenti. "
            "NESSUN link di condivisione tipo linkedin.com/sharing."),
    fonte_limite="Contatori indipendenti (novembre 2026): 3.000 caratteri",
    modello_url="https://www.linkedin.com/feed/?shareActive=true&text={testo}",
))

registra(Canale(
    chiave="facebook",
    etichetta="Facebook",
    limite=63206,
    hashtag_max=4,
    immagine=True,
    prompt=("Post per Facebook (min 100 e max 200 parole): tono caldo e personale, 2-3 emoji, "
            "3-4 hashtag, call-to-action chiaro. NESSUN link di condivisione."),
    fonte_limite="Documentazione Meta: 63.206 caratteri (tetto ampio, non vincolante)",
    modello_url="https://www.facebook.com/",
))

registra(Canale(
    chiave="instagram",
    etichetta="Instagram",
    limite=2200,
    hashtag_max=8,
    immagine=True,
    file_immagine="obbligatoria",
    prompt=("Didascalia per Instagram (max 2200 caratteri): prima riga che invita ad aprire il "
            "testo lungo, tono caldo, 5-8 hashtag in coda."),
    fonte_limite=("Instagram Platform: 2.200 caratteri (contatori indipendenti, nov 2026); "
                  "100 pubblicazioni API ogni 24 ore"),
    nota_immagine="l'API di Instagram pubblica solo JPEG: una PNG viene rifiutata",
))

registra(Canale(
    chiave="threads",
    etichetta="Threads",
    limite=500,
    hashtag_max=5,
    immagine=True,
    prompt=("Post per Threads (max 500 caratteri): conversazionale, una sola idea, "
            "3-5 hashtag in coda."),
    fonte_limite="Threads API: 500 caratteri, 250 pubblicazioni ogni 24 ore",
    nota_immagine="immagine ammessa fino a 8 MB, JPEG o PNG",
    modello_url="https://www.threads.net/intent/post?text={testo}",
))

registra(Canale(
    chiave="mastodon",
    etichetta="Mastodon",
    limite=500,
    hashtag_max=5,
    immagine=True,
    prompt=("Post per Mastodon (max 500 caratteri): tono diretto e personale, "
            "3-5 hashtag in coda, anche in inglese se il tema lo merita."),
    fonte_limite="Contatori indipendenti (novembre 2026): 500 di default, l'istanza puo' alzarlo",
))

registra(Canale(
    chiave="bluesky",
    etichetta="Bluesky",
    limite=300,
    hashtag_max=3,
    immagine=True,
    prompt=("Post per Bluesky (max 300 caratteri): asciutto e concreto, 2-3 hashtag, "
            "nessun tono promozionale."),
    fonte_limite="AT Protocol: 300 grafemi e 3.000 byte",
    nota_immagine="immagine ammessa fino a 1 MB, al massimo 4 per post",
    modello_url="https://bsky.app/intent/compose?text={testo}",
))

registra(Canale(
    chiave="telegram",
    etichetta="Telegram",
    limite=1024,
    hashtag_max=0,
    immagine=True,
    prompt=("Messaggio per un canale Telegram (max 1024 caratteri, perche' con l'immagine "
            "il testo diventa una didascalia): scorrevole, nessun hashtag."),
    fonte_limite=("Bot API di Telegram: didascalia con immagine max 1024 caratteri; "
                  "il messaggio di solo testo arriva a 4096"),
    nota_immagine="con la foto allegata la didascalia si ferma a 1024 caratteri",
))

registra(Canale(
    chiave="youtube",
    etichetta="YouTube (post Community)",
    limite=1500,
    hashtag_max=3,
    immagine=True,
    prompt=("Post per la scheda Community di YouTube (max 1500 caratteri): tono parlato, "
            "invita a guardare il video, 2-3 hashtag."),
    fonte_limite="Limite del compositore Community; nessuna API pubblica per pubblicarlo",
))
