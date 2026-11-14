"""Collaudo end-to-end dell'interfaccia con Playwright (browser vero, profilo nuovo).

Non prova il tasto "Pubblica" (serve il token X): prova tutto il resto, e il fatto che
quel tasto sia spento CON la motivazione scritta accanto.
"""

import pathlib
import sys
import urllib.request

from playwright.sync_api import sync_playwright

RADICE = pathlib.Path(__file__).resolve().parent
PROVE = RADICE / "profili_prova"
PROVE.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8796"

OK, KO = [], []


def check(nome, cond, extra=""):
    (OK if cond else KO).append(nome)
    print(("  OK   " if cond else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


def attesa(testo_sel, vecchio, timeout=90000):
    """Aspetta che il testo dentro un selettore cambi davvero."""
    import time
    fine = time.time() + timeout / 1000
    while time.time() < fine:
        attuale = testo_sel()
        if attuale and attuale != vecchio:
            return attuale
        time.sleep(0.4)
    return testo_sel()


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        pagina = browser.new_page(viewport={"width": 1500, "height": 1000})
        errori = []
        pagina.on("pageerror", lambda e: errori.append("pageerror: " + str(e)))
        pagina.on("console", lambda m: errori.append("console: " + m.text) if m.type == "error" else None)

        pagina.goto(BASE + "/#crea", wait_until="networkidle", timeout=60000)

        # La batteria deve poter girare piu' volte: l'app riprende il lavoro salvato
        # (e' una funzione voluta), quindi si azzera lo stato PRIMA di misurare.
        pagina.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
        azzera = urllib.request.Request(
            BASE + "/api/corrente", data=b"{}",
            headers={"X-Social-Studio": "1", "Content-Type": "application/json"}, method="POST")
        urllib.request.urlopen(azzera, timeout=15).read()
        pagina.reload(wait_until="networkidle", timeout=60000)

        # --- stato iniziale ---
        visibile_velo = pagina.evaluate(
            "() => getComputedStyle(document.getElementById('velo')).display")
        check("finestra (velo) NASCOSTA all'avvio", visibile_velo == "none", visibile_velo)

        check("area Crea attiva all'avvio",
              pagina.evaluate("() => !!document.querySelector('.linguetta.attiva[data-tab=\"crea\"]')"))

        stato = pagina.inner_text("#riga-stato")
        check("riga di stato dice che OpenRouter e' pronto", "OpenRouter" in stato, stato[:80])

        campi = pagina.eval_on_selector_all("#modulo-parametri .campo-parametro", "n => n.length")
        check("modulo parametri disegnato (9 campi)", campi == 9, str(campi))

        canali = pagina.eval_on_selector_all(".canale", "n => n.length")
        check("9 tasti canale disegnati", canali == 9, str(canali))

        tasti = pagina.eval_on_selector_all("#blocco-adattato button, #blocco-adattato input, #blocco-adattato textarea",
                                            "n => n.length")
        check("blocco adattato nascosto finche' non scegli un canale",
              pagina.evaluate("() => document.getElementById('blocco-adattato').classList.contains('nascosto')"))

        # --- lo stato iniziale dei tasti di invio, con la motivazione ---
        check("Pubblica disabilitato senza canale scelto",
              pagina.evaluate("() => document.getElementById('tasto-invia').disabled"))
        motivo = pagina.inner_text("#esito-invio")
        check("motivazione scritta in pagina (non solo un tooltip)", "scegli un social" in motivo, motivo[:90])

        # --- guida ---
        pagina.click("#tasto-guida")
        pagina.wait_for_selector("#velo:not(.nascosto)", timeout=15000)
        pre = pagina.eval_on_selector_all("#finestra-corpo pre", "n => n.length")
        testo_guida = pagina.inner_text("#finestra-corpo")
        check("guida: si apre nella finestra", pagina.evaluate(
            "() => getComputedStyle(document.getElementById('velo')).display") == "flex")
        check("guida: blocchi di codice resi come <pre>", pre >= 1, str(pre))
        check("guida: il registro delle novita' e' in testa", "Novit" in testo_guida[:400],
              testo_guida[:60].replace("\n", " "))
        check("guida: l'albero delle cartelle perde l'allineamento fuori da <pre>?",
              "backend/" in testo_guida)
        pagina.keyboard.press("Escape")
        check("guida: si chiude con Esc", pagina.evaluate(
            "() => getComputedStyle(document.getElementById('velo')).display") == "none")

        # --- le tre origini ---
        pagina.click(".segmento[data-origine=link]")
        check("origine link: compare il campo indirizzo",
              pagina.is_visible("#ingresso-link") and not pagina.is_visible("#ingresso-testo"))
        pagina.click(".segmento[data-origine=video]")
        check("origine video: compare il campo del video", pagina.is_visible("#ingresso-video"))
        pagina.click(".segmento[data-origine=testo]")
        check("origine testo: torna la casella di testo", pagina.is_visible("#ingresso-testo"))

        # --- generazione vera dal testo ---
        pagina.fill("#ingresso-testo",
                    "Il divario digitale non e' solo accesso alla rete: chi non sa usare gli strumenti "
                    "non partecipa alle decisioni che lo riguardano. L'alfabetizzazione digitale e' una "
                    "questione democratica, non tecnica. Servono percorsi lunghi, non corsi una tantum.")
        pagina.fill("#param-istruzioni", "Chiudi con una domanda.")
        pagina.click("#tasto-genera")
        attesa(lambda: pagina.inner_text("#esito-genera"), "Sto scrivendo…")
        titolo = pagina.input_value("#campo-titolo")
        testo = pagina.input_value("#campo-testo")
        check("genera: il titolo arriva nel campo", len(titolo) > 5, titolo[:70])
        check("genera: il testo arriva nel campo e' modificabile", len(testo) > 150, str(len(testo)) + " car")
        check("genera: il testo NON contiene meta-introduzioni vietate",
              not any(testo.strip().startswith(x) for x in ("Ecco", "Di seguito", "Questa e")),
              testo[:50])
        nodo_titolo = pagina.eval_on_selector("#imm-titolo", "n => n.value")
        check("l'immagine si precompila col titolo", nodo_titolo == titolo)

        # --- adattamento a X ---
        pagina.click(".canale[data-canale=x]")
        check("scegliendo X compare il blocco di adattamento",
              not pagina.evaluate("() => document.getElementById('blocco-adattato').classList.contains('nascosto')"))
        pagina.click("#tasto-adatta")
        attesa(lambda: pagina.inner_text("#esito-adatta"), "Sto adattando…")
        post_x = pagina.input_value("#adattato-testo")
        contatore = pagina.inner_text("#adattato-contatore")
        check("adatta: il post per X arriva nel campo", len(post_x) > 40, str(len(post_x)) + " car")
        check("adatta: il contatore mostra il tetto di X", "/ 280" in contatore, contatore)
        # Contratto (non fortuna): o sta dentro il tetto, o l app lo DICHIARA.
        # Il modello non conta i caratteri in modo affidabile: quello che si pretende
        # e che non sfori MAI in silenzio.
        avviso_sforo = "sforat" in pagina.inner_text("#esito-adatta").lower()
        check("adatta: dentro il tetto, oppure sforamento dichiarato",
              len(post_x) <= 280 or avviso_sforo,
              str(len(post_x)) + "/280 - dichiarato=" + str(avviso_sforo))

        # --- modifica a mano: quello che si legge e' quello che esce ---
        pagina.fill("#adattato-testo", "TEST MODIFICATO A MANO — questo deve uscire.")
        contatore_dopo = pagina.inner_text("#adattato-contatore")
        check("il campo e' modificabile e il contatore segue",
              "/ 280" in contatore_dopo and contatore_dopo.startswith("44"),
              contatore_dopo)

        # --- immagine generata ---
        pagina.fill("#imm-titolo", "Il divario digitale e' una questione democratica")
        pagina.fill("#imm-sottotitolo", "Alfabetizzazione, partecipazione, diritti")
        pagina.click("#tasto-genera-immagine")
        attesa(lambda: pagina.inner_text("#esito-immagine"), "Nessuna immagine allegata.")
        caricata = pagina.evaluate(
            "() => new Promise(r => { const i = document.getElementById('immagine-corrente');"
            " if (i.complete && i.naturalWidth > 0) return r([i.naturalWidth, i.naturalHeight]);"
            " i.onload = () => r([i.naturalWidth, i.naturalHeight]); i.onerror = () => r(null);"
            " setTimeout(() => r(null), 8000); })")
        check("immagine generata: si vede davvero nel browser", bool(caricata), str(caricata))
        check("tasto Rimuovi immagine ora attivo",
              not pagina.evaluate("() => document.getElementById('tasto-togli-immagine').disabled"))

        # --- anteprima ---
        pagina.click("#tasto-prepara")
        attesa(lambda: pagina.inner_text("#esito-invio"), "Sto preparando l'anteprima…")
        attesa(lambda: pagina.inner_text("#anteprima-esito"), "")
        anteprima = pagina.inner_text("#anteprima-esito")
        # il titolo ha text-transform: uppercase, quindi il browser restituisce maiuscolo
        check("anteprima: si apre il riquadro", "che cosa uscirebbe" in anteprima.lower())
        check("anteprima: dice a nome di chi", "A nome di" in anteprima)
        check("anteprima: mostra il testo che uscirebbe", "TEST MODIFICATO A MANO" in anteprima)
        check("anteprima: dichiara il problema delle credenziali",
              "credenziali" in anteprima, anteprima[-160:].replace("\n", " "))
        check("anteprima: NON ha pubblicato niente (Pubblica resta spento)",
              pagina.evaluate("() => document.getElementById('tasto-invia').disabled"))

        # --- cambio area e ritorno ---
        pagina.click(".linguetta[data-tab=config]")
        check("area Configurazione si apre", pagina.is_visible("#tab-config"))
        campi_conf = pagina.eval_on_selector_all("#modulo-llm input, #modulo-x input", "n => n.length")
        check("Configurazione: campi disegnati", campi_conf >= 7, str(campi_conf))
        segreta = pagina.input_value("#conf-orKey")
        check("Configurazione: la chiave NON e' in pagina", segreta == "", repr(segreta))
        pagina.click(".linguetta[data-tab=registro]")
        check("area Registro si apre", pagina.is_visible("#tab-registro"))
        pagina.click(".linguetta[data-tab=crea]")
        check("tornando a Crea il lavoro e' rimasto",
              pagina.input_value("#adattato-testo").startswith("TEST MODIFICATO"))

        # --- schermata ---
        pagina.set_viewport_size({"width": 1500, "height": 1600})
        scatto = PROVE / "collaudo-crea.png"
        pagina.screenshot(path=str(scatto), full_page=True)
        print("\nschermata:", scatto)

        check("nessun errore JavaScript in console", not errori, "; ".join(errori[:3]))
        browser.close()

    print(f"\n=== PASS={len(OK)}  FAIL={len(KO)} ===")
    if KO:
        print("FALLITI:")
        for nome in KO:
            print("  -", nome)
    return 1 if KO else 0


if __name__ == "__main__":
    sys.exit(main())
