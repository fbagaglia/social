"""Collaudo del flusso Facebook: che cosa succede scegliendolo."""

import pathlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
PROVE = pathlib.Path(__file__).resolve().parent / "profili_prova"
PROVE.mkdir(exist_ok=True)

OK, KO = [], []


def check(nome, cond, extra=""):
    (OK if cond else KO).append(nome)
    print(("  OK   " if cond else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pagina = b.new_page(viewport={"width": 1500, "height": 1100})
    errori = []
    pagina.on("pageerror", lambda e: errori.append("pageerror: " + str(e)))
    pagina.on("console", lambda m: errori.append("console: " + m.text) if m.type == "error" else None)

    pagina.goto(BASE + "/#crea", wait_until="networkidle", timeout=60000)
    pagina.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    pagina.reload(wait_until="networkidle")

    # un testo vero, per lavorare su qualcosa di reale
    pagina.fill("#ingresso-testo",
                "Il divario digitale non e' solo accesso alla rete: chi non sa usare gli "
                "strumenti non partecipa alle decisioni che lo riguardano. L'alfabetizzazione "
                "digitale e' una questione democratica, non tecnica.")
    pagina.click("#tasto-genera")
    for _ in range(90):
        if "Fatto" in pagina.inner_text("#esito-genera"):
            break
        pagina.wait_for_timeout(1000)
    check("testo generato", len(pagina.input_value("#campo-testo")) > 300,
          str(len(pagina.input_value("#campo-testo"))) + " caratteri")

    pagina.click(".canale[data-canale=facebook]")
    pagina.wait_for_timeout(800)

    etichetta = pagina.inner_text("#tasto-apri")
    check("il tasto non dice 'compositore' se non porta il testo",
          etichetta.strip() == "Apri Facebook", etichetta)
    nota = pagina.inner_text("#nota-consegna")
    check("la rete spiega la sua consegna", "non ha un indirizzo che precompila" in nota, nota[:110])
    check("la consegna dice l'ordine (prima testo, poi immagine)",
          "1)" in nota and "2)" in nota, nota[-100:])
    check("il tasto Copia il testo e' attivo",
          not pagina.evaluate("() => document.getElementById('tasto-copia-testo').disabled"))

    # adatta a Facebook
    pagina.click("#tasto-adatta")
    for _ in range(90):
        if "Fatto" in pagina.inner_text("#esito-adatta"):
            break
        pagina.wait_for_timeout(1000)
    post = pagina.input_value("#adattato-testo")
    check("il post per Facebook arriva", len(post) > 100, str(len(post)) + " caratteri")

    # copia del testo: si legge il testo che uscirebbe, non una copia in memoria
    pagina.evaluate("() => { window.__copiato = null; navigator.clipboard.writeText = "
                    "(t) => { window.__copiato = t; return Promise.resolve(); }; }")
    pagina.fill("#adattato-testo", post + " [MODIFICATO A MANO]")
    pagina.click("#tasto-copia-testo")
    pagina.wait_for_timeout(600)
    copiato = pagina.evaluate("() => window.__copiato")
    check("Copia il testo copia la versione modificata a mano",
          copiato is not None and copiato.endswith("[MODIFICATO A MANO]"),
          str(copiato)[-40:] if copiato else "niente copiato")

    # immagine + copia negli appunti (prova vera, riletta dal servizio)
    pagina.click("#tasto-genera-immagine")
    for _ in range(40):
        if "Generata" in pagina.inner_text("#esito-immagine"):
            break
        pagina.wait_for_timeout(700)
    check("immagine generata", "Generata" in pagina.inner_text("#esito-immagine"),
          pagina.inner_text("#esito-immagine")[:70])
    check("il tasto Copia l'immagine e' attivo",
          not pagina.evaluate("() => document.getElementById('tasto-copia-immagine').disabled"))

    pagina.click("#tasto-copia-immagine")
    for _ in range(30):
        if "appunti" in pagina.inner_text("#esito-immagine"):
            break
        pagina.wait_for_timeout(700)
    check("l'immagine e' finita negli appunti di Windows",
          "appunti" in pagina.inner_text("#esito-immagine"),
          pagina.inner_text("#esito-immagine")[:90])

    check("i tre passi della consegna stanno in fila, nell'ordine giusto",
          pagina.evaluate("""() => {
            const b = (id) => Array.from(document.querySelectorAll('#tab-crea .barra-comandi button'))
                                   .findIndex(x => x.id === id);
            return b('tasto-copia-testo') < b('tasto-copia-immagine-2')
                && b('tasto-copia-immagine-2') < b('tasto-apri');
          }"""))
    check("il passo 2 e' attivo ora che l'immagine c'e'",
          not pagina.evaluate("() => document.getElementById('tasto-copia-immagine-2').disabled"))

    # anteprima: nessun problema bloccante, e il compositore disponibile
    pagina.click("#tasto-prepara")
    for _ in range(40):
        if "Anteprima pronta" in pagina.inner_text("#esito-invio"):
            break
        pagina.wait_for_timeout(700)
    check("anteprima pronta", "Anteprima pronta" in pagina.inner_text("#esito-invio"))
    check("il tasto Apri Facebook e' attivo",
          not pagina.evaluate("() => document.getElementById('tasto-apri').disabled"))
    check("Pubblica resta spento (Facebook non e' collegato via API)",
          pagina.evaluate("() => document.getElementById('tasto-invia').disabled"))

    pagina.set_viewport_size({"width": 1500, "height": 2200})
    scatto = PROVE / "flusso-facebook.png"
    pagina.screenshot(path=str(scatto), full_page=True)
    print("\nschermata:", scatto)
    check("nessun errore JavaScript", not errori, "; ".join(errori[:2]))
    b.close()

print(f"\n=== PASS={len(OK)}  FAIL={len(KO)} ===")
print("FALLITI:", KO or "nessuno")
