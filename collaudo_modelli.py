"""Collaudo del menu a tendina dei modelli (area Configurazione).

Verifica tre cose: che l'elenco arrivi dal provider, che la tendina sia davvero una
tendina raggruppata per editore, e che se l'elenco non arriva il campo torni
scrivibile invece di restare un menu vuoto che blocca l'utente.

    py -3.14 collaudo_modelli.py
"""
import json
import pathlib
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
PROVE = pathlib.Path(__file__).resolve().parent / "profili_prova"
PROVE.mkdir(exist_ok=True)

OK, KO = [], []


def check(nome, condizione, extra=""):
    (OK if condizione else KO).append(nome)
    print(("  OK   " if condizione else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


def leggi(percorso, tentativi=30):
    for _ in range(tentativi):
        try:
            with urllib.request.urlopen(BASE + percorso, timeout=180) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(1)
    raise SystemExit("servizio non raggiungibile: " + percorso)


print("=" * 62)
print(" COLLAUDO — il menu a tendina dei modelli")
print("=" * 62)

print("\n1. i provider offerti")
prov = leggi("/api/providers")
elenco = prov.get("provider") or []
check("l'elenco dei provider arriva", len(elenco) >= 5, f"{len(elenco)} provider")
check("il provider attuale e' dedotto dall'indirizzo", prov.get("attuale") == "openrouter",
      prov.get("attuale"))
check("c'e' la voce per un indirizzo proprio",
      any(p["id"] == "custom" for p in elenco))
for p in elenco[:4]:
    print(f"      {p['id']:<12} {p['nome']}")

print("\n2. l'elenco dei modelli del provider")
mod = leggi("/api/modelli?provider=openrouter")
check("il catalogo arriva", mod.get("ok") and mod.get("quanti", 0) > 100,
      f"{mod.get('quanti')} modelli")
check("i modelli hanno id, nome e gruppo",
      all(m.get("id") and m.get("nome") and m.get("gruppo") for m in mod["modelli"][:20]))
check("i gratuiti sono riconosciuti", mod.get("quanti_gratuiti", 0) > 0,
      f"{mod.get('quanti_gratuiti')} gratuiti")
check("e' ordinato per editore",
      [m["gruppo"] for m in mod["modelli"]] == sorted([m["gruppo"] for m in mod["modelli"]],
                                                      key=str.lower))
gruppi = sorted({m["gruppo"] for m in mod["modelli"]})
print(f"      {len(gruppi)} editori: {', '.join(gruppi[:10])}…")

print("\n3. il modello salvato adesso e' in elenco?")
import sys
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent / "backend"))
import config as cfg                                            # noqa: E402
salvato = (cfg.leggi().get("llm") or {}).get("orModel", "")
presente = any(m["id"] == salvato for m in mod["modelli"])
check("il modello in configurazione esiste nel catalogo", presente, salvato or "(nessuno)")

print("\n4. un provider senza chiave valida: l'errore e' una risposta, non un guasto")
sbagliato = leggi("/api/modelli?provider=openai")
check("risponde comunque (200 con ok:false)", sbagliato.get("ok") is False,
      str(sbagliato.get("motivo"))[:110])
check("spiega il motivo e non restituisce modelli", not sbagliato.get("modelli"))

print("\n5. l'interfaccia: la tendina e' una tendina")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    pagina = browser.new_page(viewport={"width": 1500, "height": 1100})
    errori = []
    pagina.on("pageerror", lambda e: errori.append("pageerror: " + str(e)))
    pagina.on("console", lambda m: errori.append("console: " + m.text) if m.type == "error" else None)

    pagina.goto(BASE + "/#config", wait_until="networkidle", timeout=60000)
    for _ in range(60):
        if pagina.evaluate("() => !!document.getElementById('conf-provider')"):
            break
        pagina.wait_for_timeout(500)
    for _ in range(60):
        nota = pagina.inner_text("#conf-orModel-nota")
        if "modelli da" in nota or "a mano" in nota or "non raggiungibile" in nota:
            break
        pagina.wait_for_timeout(500)

    check("il campo provider e' una tendina",
          pagina.evaluate("() => document.getElementById('conf-provider').tagName") == "SELECT")
    quanti_prov = pagina.evaluate("() => document.getElementById('conf-provider').options.length")
    check("la tendina dei provider e' popolata", quanti_prov >= 5, f"{quanti_prov} voci")
    check("il provider salvato e' preselezionato",
          pagina.evaluate("() => document.getElementById('conf-provider').value") == "openrouter")

    tag_modello = pagina.evaluate("() => (document.getElementById('conf-orModel')||{}).tagName")
    check("il campo modello e' una tendina, non un campo da digitare", tag_modello == "SELECT",
          str(tag_modello))
    quanti_mod = pagina.evaluate("() => (document.getElementById('conf-orModel')||{}).options?.length || 0")
    check("la tendina dei modelli e' popolata", quanti_mod > 100, f"{quanti_mod} voci")
    gruppi_ui = pagina.evaluate(
        "() => document.querySelectorAll('#conf-orModel optgroup').length")
    check("i modelli sono raggruppati per editore", gruppi_ui > 5, f"{gruppi_ui} gruppi")
    nota = pagina.inner_text("#conf-orModel-nota")
    check("la nota dice quanti modelli e da dove", "modelli da" in nota, nota[:100])
    scelto = pagina.evaluate("() => document.getElementById('conf-orModel').value")
    check("il modello salvato e' selezionato nella tendina", scelto == salvato,
          f"{scelto} (salvato: {salvato})")

    check("c'e' anche la tendina per il modello di adattamento",
          pagina.evaluate("() => document.getElementById('conf-orModelAdatta').tagName") == "SELECT")
    check("il campo dell'indirizzo resta (serve solo per «Altro»)",
          pagina.evaluate("() => !!document.getElementById('conf-orUrl')"))

    print("\n6. cambiando provider l'elenco cambia — e se non arriva si scrive a mano")
    pagina.select_option("#conf-provider", "openai")
    for _ in range(40):
        nota2 = pagina.inner_text("#conf-orModel-nota")
        if "a mano" in nota2 or "modelli da" in nota2:
            break
        pagina.wait_for_timeout(500)
    tag_dopo = pagina.evaluate("() => (document.getElementById('conf-orModel')||{}).tagName")
    check("un provider senza catalogo leggibile lascia il campo scrivibile",
          tag_dopo == "INPUT", f"e' diventato {tag_dopo}: {pagina.inner_text('#conf-orModel-nota')[:80]}")
    check("l'indirizzo segue il provider scelto",
          "openai.com" in pagina.input_value("#conf-orUrl"),
          pagina.input_value("#conf-orUrl"))
    check("il campo non resta vuoto e bloccato",
          pagina.evaluate("() => !!document.getElementById('conf-orModel')"))

    pagina.set_viewport_size({"width": 1500, "height": 1400})
    scatto = PROVE / "config-modelli.png"
    pagina.screenshot(path=str(scatto), full_page=True)
    print("\nschermata:", scatto)
    check("nessun errore JavaScript", not errori, "; ".join(errori[:2]))
    browser.close()

print("\n" + "=" * 62)
print(f" PASS={len(OK)}  FAIL={len(KO)}")
if KO:
    print(" FALLITI:")
    for n in KO:
        print("   -", n)
print("=" * 62)
