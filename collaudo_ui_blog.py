"""Collaudo del pannello blog nell'interfaccia.

Verifica le tre cose chieste, nell'ordine in cui l'utente le usa: le due immagini del
corpo, le FAQ a scomparsa con l'anteprima, i campi SEO — e il tasto che deposita la bozza.
**Non preme "Deposita la bozza"**: creerebbe un articolo sul sito vivo.

    py -3.14 collaudo_ui_blog.py
"""
import pathlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
PROVE = pathlib.Path(__file__).resolve().parent / "profili_prova"
PROVE.mkdir(exist_ok=True)

TESTO = """Il divario digitale non e' solo accesso alla rete: e' potere decisionale.

## Che cosa significa alfabetizzare
Il primo paragrafo spiega il contesto con un termine in **grassetto** e uno in *corsivo*.
Il secondo paragrafo entra nel merito della questione.

## Perche' riguarda la democrazia
Il terzo paragrafo porta un esempio concreto.
Il quarto paragrafo allarga lo sguardo al contesto piu' ampio.

## Cosa fare adesso
Il quinto paragrafo raccoglie le fila e dice da dove cominciare."""

OK, KO = [], []


def check(nome, condizione, extra=""):
    (OK if condizione else KO).append(nome)
    print(("  OK   " if condizione else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    pagina = browser.new_page(viewport={"width": 1500, "height": 1100})
    errori = []
    pagina.on("pageerror", lambda e: errori.append("pageerror: " + str(e)))
    pagina.on("console", lambda m: errori.append("console: " + m.text) if m.type == "error" else None)

    pagina.goto(BASE + "/#crea", wait_until="networkidle", timeout=60000)
    pagina.evaluate("() => { try { localStorage.clear(); } catch (e) {} }")
    pagina.reload(wait_until="networkidle")

    print("\n1. il pannello compare solo per il blog")
    # L'app ripristina l'ultimo canale usato, quindi non si puo' pretendere che il
    # pannello parta nascosto: si verifica che la sua visibilita' SEGUA il canale.
    check("la visibilita' del pannello segue il canale gia' scelto",
          pagina.evaluate("""() => {
            const c = document.querySelector('.canale.attivo');
            const blog = c && c.dataset.canale === 'umanesimodigitale';
            const nascosto = document.getElementById('pannello-blog').classList.contains('nascosto');
            return blog ? !nascosto : nascosto;
          }"""),
          pagina.evaluate("() => (document.querySelector('.canale.attivo')||{}).dataset?.canale"))
    pagina.click(".canale[data-canale=telegram]")
    pagina.wait_for_timeout(600)
    check("scegliendo un social resta nascosto",
          pagina.evaluate("() => document.getElementById('pannello-blog').classList.contains('nascosto')"))

    pagina.click(".canale[data-canale=umanesimodigitale]")
    for _ in range(40):
        if "Collegato a" in pagina.inner_text("#blog-stato"):
            break
        pagina.wait_for_timeout(500)
    check("scegliendo il blog compare",
          not pagina.evaluate("() => document.getElementById('pannello-blog').classList.contains('nascosto')"))
    stato_blog = pagina.inner_text("#blog-stato")
    check("dice a quale sito e' collegato", "Collegato a" in stato_blog, stato_blog[:110])
    check("dice che deposita bozze, non pubblicazioni", "bozze" in stato_blog)
    opzioni = pagina.evaluate("() => document.getElementById('blog-categorie').options.length")
    check("le categorie del sito arrivano nella tendina", opzioni > 20, f"{opzioni} categorie")

    check("il tasto non dice «Pubblica» ma «Deposita la bozza»",
          "Deposita la bozza" in pagina.inner_text("#tasto-invia"),
          pagina.inner_text("#tasto-invia"))
    check("i tasti di copia sono spenti (il blog non si consegna a mano)",
          pagina.evaluate("() => document.getElementById('tasto-copia-testo').disabled"))

    print("\n2. il testo dell'articolo")
    pagina.fill("#campo-testo", TESTO)
    pagina.wait_for_timeout(300)

    print("\n3. le FAQ a scomparsa, con l'anteprima")
    check("il tasto «Aggiorna l'anteprima» e' spento senza domande",
          pagina.evaluate("() => document.getElementById('blog-aggiorna-anteprima').disabled"))
    pagina.click("#blog-genera-faq")
    # Aspettare la parola "domande" non serve: compare gia' in "Sto scrivendo le
    # domande…". Si aspetta che le domande esistano davvero, o che arrivi un errore.
    for _ in range(150):
        if pagina.evaluate("() => document.querySelectorAll('#blog-faq-lista [data-faq-d]').length") > 0:
            break
        if "Non riuscito" in pagina.inner_text("#blog-esito-faq"):
            break
        pagina.wait_for_timeout(1000)
    esito_faq = pagina.inner_text("#blog-esito-faq")
    check("le FAQ si generano", "correggerle" in esito_faq or "domande." in esito_faq, esito_faq[:130])
    quante = pagina.evaluate("() => document.querySelectorAll('#blog-faq-lista [data-faq-d]').length")
    check("le domande sono modificabili a mano", quante >= 3, f"{quante} domande")
    check("l'anteprima mostra card a scomparsa",
          pagina.evaluate("() => document.querySelectorAll('#blog-faq-anteprima details').length") >= 3)
    check("l'anteprima usa il CSS scoped del sito",
          "ud-faq" in pagina.evaluate("() => document.getElementById('blog-faq-anteprima').innerHTML"))
    blocco = pagina.input_value("#blog-faq-html")
    check("c'e' il blocco HTML pronto", blocco.startswith("<!-- wp:html -->"), blocco[:40])
    check("il blocco non ha tag globali (niente &)",
          "&" not in blocco)
    check("il blocco contiene <details>/<summary>", "<details><summary>" in blocco)

    print("\n4. correggere a mano aggiorna l'anteprima (= quello che si pubblica)")
    pagina.fill("#blog-faq-lista [data-faq-d='0']", "Domanda riscritta a mano?")
    pagina.wait_for_timeout(1600)
    check("l'anteprima segue la correzione",
          "Domanda riscritta a mano?" in pagina.evaluate(
              "() => document.getElementById('blog-faq-anteprima').innerHTML"))
    check("anche il blocco HTML segue",
          "Domanda riscritta a mano?" in pagina.input_value("#blog-faq-html"))

    print("\n5. i campi SEO, con i tetti misurati")
    pagina.click("#blog-genera-seo")
    for _ in range(120):
        if "Fatto" in pagina.inner_text("#blog-esito-seo"):
            break
        pagina.wait_for_timeout(1000)
    check("i campi SEO si generano", "Fatto" in pagina.inner_text("#blog-esito-seo"),
          pagina.inner_text("#blog-esito-seo")[:110])
    seo_t = pagina.input_value("#blog-seo-title")
    seo_d = pagina.input_value("#blog-seo-description")
    check("il SEO title sta entro 60", len(seo_t) <= 60, f"{len(seo_t)} caratteri")
    check("la meta description sta entro 160", len(seo_d) <= 160, f"{len(seo_d)} caratteri")
    check("il contatore mostra il tetto",
          "/ 60" in pagina.inner_text("#blog-seo-title-contatore"),
          pagina.inner_text("#blog-seo-title-contatore"))
    check("la parola chiave arriva", bool(pagina.input_value("#blog-focus-keyword")))
    check("lo slug arriva", bool(pagina.input_value("#blog-slug")))
    pagina.fill("#blog-seo-title", "x" * 64)
    pagina.wait_for_timeout(200)
    check("il contatore segnala lo sforamento",
          "oltre" in pagina.get_attribute("#blog-seo-title-contatore", "class"),
          pagina.get_attribute("#blog-seo-title-contatore", "class"))
    pagina.fill("#blog-seo-title", seo_t)

    print("\n6. le due immagini del corpo")
    check("c'e' il caricamento per le immagini del corpo",
          pagina.evaluate("() => !!document.getElementById('blog-file-immagine')"))
    check("la griglia delle immagini del corpo e' vuota all'inizio",
          pagina.evaluate("() => document.getElementById('blog-immagini').children.length") == 0)

    print("\n7. l'anteprima della pubblicazione (non deposita niente)")
    pagina.click("#tasto-prepara")
    for _ in range(60):
        if "Anteprima pronta" in pagina.inner_text("#esito-invio"):
            break
        pagina.wait_for_timeout(500)
    check("l'anteprima risponde", "Anteprima pronta" in pagina.inner_text("#esito-invio"))
    anteprima = pagina.inner_text("#anteprima-esito")
    check("l'anteprima dice che si deposita una bozza",
          "bozza" in anteprima.lower(), anteprima[:160])
    check("conta paragrafi e FAQ",
          "paragrafi" in anteprima and "faq" in anteprima.lower())
    check("il tasto «Deposita la bozza» e' acceso",
          not pagina.evaluate("() => document.getElementById('tasto-invia').disabled"))

    pagina.set_viewport_size({"width": 1500, "height": 2600})
    scatto = PROVE / "pannello-blog.png"
    pagina.screenshot(path=str(scatto), full_page=True)
    print("\nschermata:", scatto)
    check("nessun errore JavaScript", not errori, "; ".join(errori[:2]))
    browser.close()

print(f"\n=== PASS={len(OK)}  FAIL={len(KO)} ===")
print("FALLITI:", KO or "nessuno")
print("Nessuna bozza e' stata creata sul sito.")
