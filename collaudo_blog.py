"""Collaudo del canale blog (umanesimodigitale.info).

Prova tutto il percorso tranne l'ultimo gesto: genera l'articolo, le FAQ e i campi
SEO con chiamate **vere** al modello, compone il markup, lo valida e chiede
l'anteprima della pubblicazione. **Non crea nessuna bozza sul sito**: quello e' un
gesto dell'utente, e un collaudo non deve lasciare residui su un sito vivo.

    py -3.14 collaudo_blog.py
"""
import json
import pathlib
import sys
import time
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:8796"
INTESTAZIONI = {"X-Social-Studio": "1", "Content-Type": "application/json"}
QUI = pathlib.Path(__file__).resolve().parent

OK, KO = [], []


def check(nome, condizione, extra=""):
    (OK if condizione else KO).append(nome)
    print(("  OK   " if condizione else "  FAIL ") + nome + (f"  [{extra}]" if extra else ""))


def leggi(percorso, tentativi=30):
    for _ in range(tentativi):
        try:
            with urllib.request.urlopen(BASE + percorso, timeout=180) as risposta:
                return json.loads(risposta.read())
        except Exception:
            time.sleep(1)
    raise SystemExit("servizio non raggiungibile: " + percorso)


def posta(percorso, corpo):
    richiesta = urllib.request.Request(BASE + percorso, data=json.dumps(corpo).encode(),
                                       headers=INTESTAZIONI, method="POST")
    try:
        with urllib.request.urlopen(richiesta, timeout=280) as risposta:
            return json.loads(risposta.read())
    except urllib.error.HTTPError as errore:
        return {"ok": False, "_http": errore.code, "motivo": errore.read().decode()[:300]}


FONTE = {
    "tipo": "testo", "titolo": "",
    "testo": ("Il divario digitale non riguarda solo la copertura della rete: riguarda le "
              "competenze. Molti adulti hanno uno smartphone ma non sanno usare i servizi "
              "pubblici digitali, e restano fuori dalle decisioni che li riguardano. "
              "Alfabetizzare significa rendere capaci di usare e di giudicare gli strumenti, "
              "non solo di possederli. I percorsi che funzionano sono brevi, locali e "
              "continuativi, con esercizi sugli strumenti reali delle persone. La scuola e "
              "le biblioteche sono i luoghi naturali dove questo accade."),
}

print("=" * 62)
print(" COLLAUDO — il canale blog (umanesimodigitale.info)")
print("=" * 62)

print("\n1. il canale si distingue dagli altri")
canali = leggi("/api/canali")["canali"]
blog = [c for c in canali if c.get("tipo") == "blog"]
check("c'e' un canale di tipo blog", len(blog) == 1, blog[0]["etichetta"] if blog else "nessuno")
b = blog[0] if blog else {}
check("ha chiave ed etichetta giuste",
      b.get("chiave") == "umanesimodigitale" and "Umanesimodigitale" in (b.get("etichetta") or ""),
      b.get("etichetta"))
check("e' «pronto» (il token c'e')", bool(b.get("pronto")), b.get("motivo_pronto") or "")
check("gli altri canali restano social",
      sum(1 for c in canali if c.get("tipo") == "social") == len(canali) - 1)

print("\n2. il canale verso il sito risponde (sola lettura)")
stato = leggi("/api/blog/stato")
check("il sito risponde", bool(stato.get("collegato")), stato.get("sito") or stato.get("motivo", ""))
check("arrivano le categorie", len(stato.get("categorie") or []) > 20,
      f"{len(stato.get('categorie') or [])} categorie")
check("arrivano i conteggi dei post", isinstance(stato.get("bozze"), int),
      f"{stato.get('pubblicati')} pubblicati · {stato.get('bozze')} bozze")
testo_risposta = json.dumps(stato, ensure_ascii=False).lower()
check("il token non finisce nella risposta", "93a" not in testo_risposta and "token" not in testo_risposta)

print("\n3. genera l'articolo (chiamata vera al modello)")
articolo = posta("/api/blog/articolo", {"fonte": FONTE, "parametri": {"tono": "caldo"}})
if not articolo.get("ok"):
    check("l'articolo si genera", False, json.dumps(articolo, ensure_ascii=False)[:200])
    print("\ncollaudo interrotto: senza articolo il resto non ha senso")
    sys.exit(1)
check("l'articolo si genera", True)
check("ha titolo, gancio, sintesi, slug",
      all(articolo.get(k) for k in ("titolo", "gancio", "sintesi", "slug")))
check("il corpo ha almeno 4 paragrafi", articolo.get("paragrafi", 0) >= 4,
      f"{articolo.get('paragrafi')} paragrafi")
check("le sezioni sono almeno 2", len(articolo.get("sezioni") or []) >= 2,
      str(articolo.get("sezioni")))
check("nessun titolo orfano", not articolo.get("orfani"), str(articolo.get("orfani")))
check("il corpo comincia col lede, non con un titolo",
      not articolo["testo"].lstrip().startswith("## "))
print(f"      titolo : {articolo['titolo']}")
print(f"      gancio : {articolo['gancio']}")
print(f"      sezioni: {articolo['sezioni']}")

print("\n4. le FAQ")
faq = posta("/api/blog/faq", {"testo": articolo["testo"], "titolo": articolo["titolo"]})
check("le FAQ si generano", bool(faq.get("ok")), faq.get("motivo", "")[:120])
if faq.get("ok"):
    quante = faq.get("quante", 0)
    check("sono da 3 a 5", 3 <= quante <= 5, str(quante))
    check("ogni risposta e' autosufficiente (almeno 100 caratteri)",
          all(len(v["risposta"]) >= 100 for v in faq["faq"]),
          str([len(v["risposta"]) for v in faq["faq"]]))
    check("il blocco usa <details> (a scomparsa)", "<details>" in faq["blocco"])
    check("il CSS e' scoped (.ud-faq)", ".ud-faq" in faq["blocco"])
    check("niente «&» nel blocco html (regola del sito)", "&" not in faq["blocco"])
    check("il blocco comincia con wp:html", faq["blocco"].lstrip().startswith("<!-- wp:html -->"))
    for v in faq["faq"][:2]:
        print(f"      D: {v['domanda']}")

print("\n5. i campi SEO (misurati, non stimati)")
seo = posta("/api/blog/seo", {"titolo": articolo["titolo"], "testo": articolo["testo"],
                              "sintesi": articolo["sintesi"]})
check("i campi SEO si generano", bool(seo.get("ok")), seo.get("motivo", "")[:120])
if seo.get("ok"):
    check("SEO title entro 60", len(seo["seo_title"]) <= 60, f"{len(seo['seo_title'])} caratteri")
    check("meta description entro 160", len(seo["seo_description"]) <= 160,
          f"{len(seo['seo_description'])} caratteri")
    check("c'e' la parola chiave", bool(seo.get("focus_keyword")))
    print(f"      SEO title ({len(seo['seo_title'])}/60): {seo['seo_title']}")
    print(f"      description ({len(seo['seo_description'])}/160): {seo['seo_description']}")
    print(f"      keyword: {seo['focus_keyword']}")
    print(f"      corretto dopo sforamento: {seo.get('corretto_dopo_sforamento')}")

print("\n6. l'anteprima delle FAQ = il markup pubblicato")
if faq.get("ok"):
    rifatto = posta("/api/blog/faq-html", {"faq": faq["faq"]})
    check("il blocco si ricostruisce dalle FAQ mostrate", bool(rifatto.get("ok")))
    check("e' identico a quello generato", rifatto.get("blocco") == faq.get("blocco"))

print("\n7. l'anteprima della pubblicazione (NON tocca il sito)")
pubblicazione = {
    "canale": "umanesimodigitale",
    "titolo": articolo["titolo"], "testo": articolo["testo"],
    "gancio": articolo["gancio"], "sintesi": articolo["sintesi"], "slug": articolo["slug"],
    "seo_title": seo.get("seo_title", ""), "seo_description": seo.get("seo_description", ""),
    "focus_keyword": seo.get("focus_keyword", ""),
    "faq": faq.get("faq", []),
    "intro_faq": "Domande frequenti sull'alfabetizzazione digitale.",
    "categorie": [35], "allegati": [], "immagini_corpo": [],
}
prep = posta("/api/prepara", pubblicazione)
p = prep.get("preparazione") or {}
bloccanti = [x for x in (p.get("problemi") or []) if x.get("bloccante")]
check("l'anteprima risponde", bool(prep.get("ok")))
check("dice cosa pubblicherebbe", p.get("paragrafi", 0) >= 4 and p.get("faq", 0) >= 3,
      f"{p.get('paragrafi')} paragrafi · {p.get('faq')} faq")
check("non ci sono problemi bloccanti", not bloccanti,
      bloccanti[0]["testo"] if bloccanti else "")
check("avverte che manca la copertina (avviso, non blocco)",
      any("copertina" in x["testo"] for x in (p.get("problemi") or [])))
for x in (p.get("problemi") or []):
    print(f"      {'BLOCCA ' if x.get('bloccante') else 'avviso '} {x['testo']}")

print("\n8. il markup che finirebbe nella bozza")
sys.path.insert(0, str(QUI / "backend"))
from canali.umanesimodigitale import sezioni_di          # noqa: E402
from umanesimo import articolo as art                     # noqa: E402

corpo = sezioni_di(articolo["testo"])
markup = art.componi(
    copertina=None, gancio=articolo["gancio"], sintesi=articolo["sintesi"],
    paragrafi=corpo["paragrafi"], sezioni=corpo["sezioni"],
    faq=[(v["domanda"], v["risposta"]) for v in faq.get("faq", [])],
    intro_faq=pubblicazione["intro_faq"],
)
controllo = art.valida(markup)
check("le validazioni passano", controllo["ok"], "; ".join(controllo["problemi"])[:160])
titoli = art.titoli(markup)
check("un solo h1 (nessuno nel corpo)", not any(t == "h1" for t in titoli))
check("i titoli sono in ordine h3 → h2", titoli[0].startswith("h3") and
      all(t.startswith(("h2", "h3")) for t in titoli))
check("la sezione FAQ si chiama «Domande frequenti»",
      any("Domande frequenti" in t for t in titoli))
check("c'e' il pattern invito in fondo",
      markup.rstrip().endswith(f'<!-- wp:block {{"ref":{art.RIF_INVITO}}} /-->'))
check("nessun colore fuori dalla palette",
      not any(c in markup for c in ("#03a07a", "#1b1f29", "#eaeaea", "#ffffff", "#000000")))
print(f"      {controllo['byte']} byte · {controllo['h2']} sezioni · "
      f"{controllo['immagini']} immagini · {controllo['blocchi_html']} blocchi html")
for t in titoli:
    print(f"      {t}")

print("\n" + "=" * 62)
print(f" PASS={len(OK)}  FAIL={len(KO)}")
if KO:
    print(" FALLITI:")
    for nome in KO:
        print("   -", nome)
print(" Nessuna bozza e' stata creata sul sito.")
print("=" * 62)
