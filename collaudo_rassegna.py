"""Collaudo della rassegna stampa.

Dalla textarea dei link alla pagina impaginata: estrazione degli indirizzi, miniature,
abstract complessivo (il trend), card in griglia, validazioni, e l'area dell'interfaccia.
La prova completa legge due fonti vere e chiama il modello: dura una ventina di secondi.

    py -3.14 collaudo_rassegna.py
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
QUI = pathlib.Path(__file__).resolve().parent
PROVE = QUI / "profili_prova"
PROVE.mkdir(exist_ok=True)
sys.path.insert(0, str(QUI / "backend"))

OK, KO = [], []


def check(nome, condizione, extra=""):
    (OK if condizione else KO).append(nome)
    print(("  OK   " if condizione else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


def posta(percorso, corpo, timeout=280):
    richiesta = urllib.request.Request(
        BASE + percorso, data=json.dumps(corpo).encode(),
        headers={"X-Social-Studio": "1", "Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(richiesta, timeout=timeout) as risposta:
            return json.loads(risposta.read())
    except urllib.error.HTTPError as errore:
        return {"ok": False, "_http": errore.code, "motivo": errore.read().decode()[:300]}


print("=" * 62)
print(" COLLAUDO — la rassegna stampa")
print("=" * 62)

import rassegna                                                    # noqa: E402

print("\n1. gli indirizzi: riconosciuti, ripuliti, senza doppioni")
prova = ("Guarda:\nhttps://umanesimodigitale.info/ ,\n"
         "https://umanesimodigitale.info/   (di nuovo)\n"
         "e https://www.youtube.com/watch?v=aircAruvnKk.\n"
         "Non e' un indirizzo: www.esempio.it")
trovati = rassegna.link_da_testo(prova)
check("si riconoscono solo gli indirizzi con schema", len(trovati) == 2, str(trovati))
check("il doppione si toglie", trovati.count("https://umanesimodigitale.info/") == 1)
check("la punteggiatura finale non resta appesa",
      all(not u.endswith((".", ",")) for u in trovati))
check("il dominio si legge bene",
      rassegna.dominio("https://www.umanesimodigitale.info/pagina") == "umanesimodigitale.info")
check("il tetto di voci si rispetta", len(rassegna.link_da_testo(
    "\n".join(f"https://esempio{i}.it/" for i in range(20)))) <= rassegna.VOCI_MAX)

print("\n2. le miniature")
check("YouTube: indirizzo fisso, senza leggere niente",
      rassegna.miniatura("https://www.youtube.com/watch?v=aircAruvnKk")
      == "https://img.youtube.com/vi/aircAruvnKk/hqdefault.jpg")
check("anche il formato corto youtu.be", "aircAruvnKk" in
      rassegna.miniatura("https://youtu.be/aircAruvnKk"))
pagina = rassegna._scarica_pagina("https://umanesimodigitale.info/")
mini = rassegna.miniatura("https://umanesimodigitale.info/", pagina) if pagina else ""
if not mini:
    # Lettura di rete: se il sito ha strozzato la richiesta, si riprova una volta
    # prima di dichiarare che la funzione non va.
    time.sleep(3)
    pagina = rassegna._scarica_pagina("https://umanesimodigitale.info/")
    mini = rassegna.miniatura("https://umanesimodigitale.info/", pagina) if pagina else ""
check("un blog: la miniatura si legge dalla pagina", bool(mini),
      (mini[:80] if mini else f"pagina di {len(pagina)} byte, nessun og:image"))

print("\n3. l'impaginazione (senza modello, con voci scritte a mano)")
markup = rassegna.componi(
    titolo="Che cosa emerge questa settimana",
    data="15 novembre 2026",
    sintesi="Le notizie raccolte convergono su un punto: la competenza conta piu' dello strumento.",
    occhiello="Rassegna stampa",
    firma="A cura di Franco Bagaglia",
    voci=[
        {"url": "https://esempio.it/uno", "dominio": "esempio.it", "titolo": "Prima notizia",
         "abstract": "Il primo abstract, autosufficiente in due o tre frasi.",
         "miniatura": "https://esempio.it/a.jpg"},
        {"url": "https://esempio.it/due", "dominio": "esempio.it", "titolo": "Seconda notizia",
         "abstract": "Il secondo abstract.", "miniatura": ""},
    ])
controllo = rassegna.valida(markup)
check("le validazioni passano", controllo["ok"], "; ".join(controllo["problemi"]))
check("c'e' il titolo, la data e l'abstract complessivo",
      "ud-rassegna-titolo" in markup and "15 novembre 2026" in markup and "ud-rassegna-sintesi" in markup)
check("ci sono due card", controllo["voci"] == 2)
check("una card senza miniatura regge lo stesso", controllo["con_miniatura"] == 1)
check("nessun colore fuori palette",
      not any(c in markup for c in ("#03a07a", "#1b1f29", "#eaeaea", "#ffffff", "#000000")))
check("niente script", "<script" not in markup.lower())
check("il foglio di stile non contiene «&»",
      not any("&" in b for b in __import__("re").findall(r"<style[^>]*>(.*?)</style>", markup, __import__("re").S)))
check("la griglia diventa una colonna sotto i 640px", "@media (max-width:640px)" in markup)
check("il testo pericoloso si neutralizza",
      "&lt;script&gt;" in rassegna.componi(titolo="<script>alert(1)</script>", data="",
                                           sintesi="", voci=[
        {"url": "https://a.it", "dominio": "a.it", "titolo": "x", "abstract": "y", "miniatura": ""}]))

print("\n4. la rassegna vera, con due fonti lette davvero")
t0 = time.time()
esito = posta("/api/rassegna", {
    "testo": "https://umanesimodigitale.info/\nhttps://www.youtube.com/watch?v=aircAruvnKk",
    "titolo": "", "data": "", "firma": "A cura di Franco Bagaglia",
})
durata = time.time() - t0
check("la rassegna si compone", bool(esito.get("ok")), str(esito.get("motivo"))[:150])
if esito.get("ok"):
    check("ha un titolo", bool(esito.get("titolo")), esito.get("titolo", "")[:70])
    check("ha la data di oggi in italiano", bool(esito.get("data")), esito.get("data"))
    sintesi = esito.get("sintesi") or ""
    check("l'abstract complessivo e' un testo, non un elenco",
          len(sintesi) > 300 and "\n" not in sintesi.strip(), f"{len(sintesi)} caratteri")
    check("una voce per ogni fonte letta", len(esito["voci"]) == 2)
    check("ogni voce ha titolo e abstract",
          all(v.get("titolo") and len(v.get("abstract", "")) > 80 for v in esito["voci"]))
    check("ogni voce ha la sua miniatura",
          all(v.get("miniatura") for v in esito["voci"]),
          str([bool(v.get("miniatura")) for v in esito["voci"]]))
    check("i due domini sono diversi e reali",
          len({v["dominio"] for v in esito["voci"]}) == 2,
          str([v["dominio"] for v in esito["voci"]]))
    check("i controlli sul markup passano", (esito.get("controllo") or {}).get("ok"))
    print(f"      {durata:.0f}s · {len(esito['html'])} byte · titolo: «{esito['titolo'][:60]}»")
    print(f"      trend: {sintesi[:150]}…")
    (QUI / "outbox" / "rassegna").mkdir(parents=True, exist_ok=True)
    (QUI / "outbox" / "rassegna" / "collaudo.html").write_text(esito["html"], encoding="utf-8")

print("\n5. le fonti illeggibili non fanno saltare tutto")
misto = posta("/api/rassegna", {
    "testo": "https://umanesimodigitale.info/\nhttps://questo-dominio-non-esiste-12345.it/pagina",
    "titolo": "Prova con una fonte rotta", "data": "1 gennaio 2026",
    "firma": "", "occhiello": "Rassegna stampa"})
check("con una fonte rotta la rassegna esce lo stesso", bool(misto.get("ok")),
      str(misto.get("motivo"))[:150])
if misto.get("ok"):
    check("la fonte rotta viene dichiarata", len(misto.get("non_lette") or []) == 1,
          str(misto.get("non_lette")))
    check("le voci sono solo quelle lette", len(misto["voci"]) == 1)

print("\n6. l'area dell'interfaccia")
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    pagina_ui = browser.new_page(viewport={"width": 1500, "height": 1100})
    errori = []
    pagina_ui.on("pageerror", lambda e: errori.append("pageerror: " + str(e)))
    pagina_ui.on("console", lambda m: errori.append("console: " + m.text) if m.type == "error" else None)

    pagina_ui.goto(BASE + "/#rassegna", wait_until="networkidle", timeout=60000)
    check("la linguetta «Rassegna stampa» c'e'",
          pagina_ui.locator(".linguetta[data-tab=rassegna]").count() == 1)
    check("l'area si apre", pagina_ui.is_visible("#tab-rassegna"))
    check("c'e' la textarea dei link", pagina_ui.locator("#rassegna-link").count() == 1)
    check("ci sono i campi facoltativi",
          all(pagina_ui.locator(s).count() == 1 for s in
              ("#rassegna-titolo", "#rassegna-data", "#rassegna-firma")))
    check("l'anteprima parte nascosta",
          pagina_ui.evaluate("() => document.getElementById('riquadro-rassegna-esito').classList.contains('nascosto')"))

    # il conteggio degli indirizzi
    pagina_ui.fill("#rassegna-link", "https://a.it/1\nhttps://b.it/2\nhttps://a.it/1")
    pagina_ui.wait_for_timeout(300)
    conteggio = pagina_ui.inner_text("#rassegna-conteggio")
    check("il conteggio mostra gli indirizzi unici", "2 indirizzi" in conteggio, conteggio)

    # la rassegna vera, dal tasto
    pagina_ui.fill("#rassegna-link", "https://umanesimodigitale.info/")
    pagina_ui.fill("#rassegna-titolo", "")
    pagina_ui.click("#tasto-rassegna")
    for _ in range(180):
        if "Fatta" in pagina_ui.inner_text("#esito-rassegna") or "Non riuscit" in pagina_ui.inner_text("#esito-rassegna"):
            break
        pagina_ui.wait_for_timeout(1000)
    esito_ui = pagina_ui.inner_text("#esito-rassegna")
    check("il tasto compone la rassegna", "Fatta" in esito_ui, esito_ui[:110])
    if "Fatta" in esito_ui:
        check("l'anteprima si apre",
              not pagina_ui.evaluate("() => document.getElementById('riquadro-rassegna-esito').classList.contains('nascosto')"))
        check("l'anteprima contiene la rassegna vera",
              pagina_ui.locator("#rassegna-anteprima .ud-rassegna-card").count() >= 1)
        check("il codice e' nel campo, pronto da copiare",
              pagina_ui.input_value("#rassegna-html").startswith("<style>"))
        check("il riepilogo dice titolo, data e voci",
              "·" in pagina_ui.inner_text("#rassegna-riepilogo"),
              pagina_ui.inner_text("#rassegna-riepilogo")[:100])
        check("l'anteprima porta il CSS della rassegna",
              "ud-rassegna" in pagina_ui.evaluate("() => document.getElementById('rassegna-anteprima').innerHTML"))
        pagina_ui.click("#tasto-vedi-html")
        pagina_ui.wait_for_timeout(300)
        check("il codice si puo' mostrare",
              pagina_ui.is_visible("#rassegna-html"))

    pagina_ui.set_viewport_size({"width": 1500, "height": 1500})
    pagina_ui.screenshot(path=str(PROVE / "rassegna-area.png"), full_page=True)
    check("nessun errore JavaScript", not errori, "; ".join(errori[:2]))
    browser.close()

print("\n" + "=" * 62)
print(f" PASS={len(OK)}  FAIL={len(KO)}")
if KO:
    print(" FALLITI:")
    for n in KO:
        print("   -", n)
print("=" * 62)
