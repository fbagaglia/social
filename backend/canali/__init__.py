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


class CanaleConPonte(Canale):
    """Un canale che pubblica davvero: il ponte dice l'account e invia.

    Il modulo del ponte si importa dentro i metodi: cosi' l'elenco dei canali si
    legge anche quando un ponte non e' utilizzabile, e un errore di import non
    impedisce di disegnare la pagina.
    """

    nome_modulo = ""

    def ponte(self):
        from importlib import import_module

        return import_module("canali." + self.nome_modulo)

    def prepara(self, pubblicazione: dict, conf: dict) -> dict:
        base = super().prepara(pubblicazione, conf)
        try:
            base["a_nome_di"] = self.ponte().account(conf)
        except BaseException as errore:  # i ponti escono con eccezioni proprie o SystemExit
            base["a_nome_di"] = None
            gia_detto = any(("credenzial" in x["testo"].lower() or "manca" in x["testo"].lower())
                            for x in base["problemi"])
            if not gia_detto:
                base["problemi"] = base["problemi"] + [{"bloccante": True, "testo": str(errore)}]
        return base

    def invia(self, pubblicazione: dict, conf: dict) -> dict:
        problemi = [x for x in self.problemi(pubblicazione, conf) if x.get("bloccante")]
        if problemi:
            return {"pubblicato": False, "motivo": problemi[0]["testo"], "problemi": problemi}
        try:
            return self.ponte().pubblica(pubblicazione, conf)
        except BaseException as errore:  # idem: SystemExit non e' un Exception
            return {"pubblicato": False, "motivo": str(errore)}


class CanaleX(CanaleConPonte):
    nome_modulo = "x"

    def problemi(self, pubblicazione: dict, conf: dict) -> list[dict]:
        problemi = super().problemi(pubblicazione, conf)
        costo = self.ponte().costo_stimato(pubblicazione.get("testo", ""))
        if costo > self.ponte().COSTO_TESTO_O_MEDIA:
            problemi.append({
                "bloccante": False,
                "testo": (f"il testo contiene un indirizzo web: su X questo post costa circa "
                          f"${costo:.2f} invece di ${self.ponte().COSTO_TESTO_O_MEDIA:.3f}. "
                          "Se vuoi risparmiare, togli il link dal testo (mettilo nell'immagine "
                          "o in bio) e ripubblica l'anteprima."),
            })
        return problemi

    def prepara(self, pubblicazione: dict, conf: dict) -> dict:
        base = super().prepara(pubblicazione, conf)
        base["costo_stimato_usd"] = self.ponte().costo_stimato(pubblicazione.get("testo", ""))
        return base

    def url_compositore(self, pubblicazione: dict) -> str:
        # Testo soltanto: l'intent di X non allega immagini.
        return "https://x.com/intent/post?text=" + _testo_url(pubblicazione.get("testo", ""))


class CanaleTelegram(CanaleConPonte):
    nome_modulo = "telegram"

    def limite_effettivo(self, pubblicazione: dict) -> int:
        # Con la foto il testo diventa una didascalia: 1024. Senza, il messaggio
        # arriva a 4096. Un posto solo decide, cosi' anteprima e problemi concordano.
        return self.limite if pubblicazione.get("allegati") else 4096

    def problemi(self, pubblicazione: dict, conf: dict) -> list[dict]:
        problemi = super().problemi(pubblicazione, conf)
        if not pubblicazione.get("allegati"):
            problemi.append({
                "bloccante": False,
                "testo": ("senza immagine Telegram accetta fino a 4096 caratteri; allega una "
                          "foto e la didascalia si fermera' a 1024"),
            })
        return problemi


class CanaleMastodon(CanaleConPonte):
    nome_modulo = "mastodon"


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

registra(CanaleMastodon(
    chiave="mastodon",
    collegato=True,
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

registra(CanaleTelegram(
    chiave="telegram",
    collegato=True,
    etichetta="Telegram",
    limite=1024,
    hashtag_max=0,
    immagine=True,
    prompt=("Messaggio per un canale Telegram: scorrevole, nessun hashtag. Con la foto "
            "allegata il testo diventa una didascalia e si ferma a 1024 caratteri."),
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
