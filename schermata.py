"""Schermata con un canale collegato selezionato, per la consegna."""

import pathlib
from playwright.sync_api import sync_playwright

BASE = "http://127.0.0.1:8796"
USCITA = pathlib.Path(__file__).resolve().parent / "profili_prova" / "flusso-manuale-x.png"

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    pagina = b.new_page(viewport={"width": 1500, "height": 1100})
    pagina.goto(BASE + "/#crea", wait_until="networkidle", timeout=60000)
    pagina.fill("#ingresso-testo",
                "Il divario digitale non e' solo accesso alla rete: chi non sa usare gli strumenti "
                "non partecipa alle decisioni che lo riguardano. L'alfabetizzazione digitale e' una "
                "questione democratica, non tecnica.")
    pagina.click("#tasto-genera")
    for _ in range(90):
        if "Fatto" in pagina.inner_text("#esito-genera"):
            break
        pagina.wait_for_timeout(1000)
    pagina.click(".canale[data-canale=x]")
    for _ in range(40):
        if "compositore" in pagina.inner_text("#nota-invio"):
            break
        pagina.wait_for_timeout(400)
    pagina.click("#tasto-prepara")
    pagina.wait_for_timeout(6000)
    pagina.set_viewport_size({"width": 1500, "height": 2000})
    pagina.screenshot(path=str(USCITA), full_page=True)
    print("tasto:", repr(pagina.inner_text("#tasto-invia")),
          "| abilitato:", not pagina.evaluate("() => document.getElementById('tasto-invia').disabled"))
    print("nota :", pagina.inner_text("#nota-invio"))
    print("schermata:", USCITA)
    b.close()
