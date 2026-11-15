"""L'articolo di umanesimodigitale.info: l'anatomia in nove parti, come markup Gutenberg.

Il modello non e' inventato qui: e' quello verificato sul sito e conservato in
`umanesimodogitale/manutenzione/MODELLO-ARTICOLO.md`, con il markup validato di
apertura (Spectra) e FAQ. Le due cose che `wp_write_blocks` non sa generare —
`uagb/container`, `uagb/info-box` — stanno qui come markup, ed e' la ragione per
cui questo file esiste.

Palette del sito: nero #0C0D0D, verde #379557, chiaro #D9E1DA, grigio scuro #5B5F5C,
grigio chiaro #818484. Cinque colori, non uno di piu': le sfumature si fanno con rgba().
"""

from __future__ import annotations

import json
import re

NERO = "#0C0D0D"
VERDE = "#379557"
CHIARO = "#D9E1DA"
GRIGIO_SCURO = "#5B5F5C"
GRIGIO_CHIARO = "#818484"

RIF_INVITO = 5923          # pattern sincronizzato: newsletter, rivista, canale, nota AI
LARGHEZZA_ARTICOLO = 1800  # le immagini del corpo su questo sito arrivano larghe cosi'


# --------------------------------------------------------------------------- #
# Pezzi semplici
# --------------------------------------------------------------------------- #

def blocco_paragrafo(testo: str) -> str:
    return f"<!-- wp:paragraph -->\n<p>{testo}</p>\n<!-- /wp:paragraph -->\n"


def blocco_h2(titolo: str) -> str:
    return (f'<!-- wp:heading -->\n<h2 class="wp-block-heading">{titolo}</h2>\n'
            f'<!-- /wp:heading -->\n')


def blocco_separatore() -> str:
    return ('<!-- wp:separator -->\n'
            '<hr class="wp-block-separator has-alpha-channel-opacity"/>\n'
            '<!-- /wp:separator -->\n')


def blocco_spaziatore() -> str:
    return '<!-- wp:spacer {"height":"40px"} -->\n<div style="height:40px" aria-hidden="true" class="wp-block-spacer"></div>\n<!-- /wp:spacer -->\n'


def blocco_invito() -> str:
    """Il pattern sincronizzato in fondo. Non e' un pezzo da riscrivere: e' un riferimento."""
    return f'<!-- wp:block {{"ref":{RIF_INVITO}}} /-->\n'


def blocco_immagine(immagine: dict, *, dopo_testo: str = "") -> str:
    """Un'immagine del corpo. `immagine` ha id, url, alt, didascalia (facoltativa)."""
    id_ = immagine.get("id") or 0
    url = immagine.get("url", "")
    alt = (immagine.get("alt") or "").replace('"', "&quot;")
    classe = f" wp-image-{id_}" if id_ else ""
    didascalia = immagine.get("didascalia") or ""
    figcaption = (f'<figcaption class="wp-element-caption">{didascalia}</figcaption>'
                  if didascalia else "")
    attributi = {"sizeSlug": "large", "linkDestination": "none", "align": "center"}
    if id_:
        attributi["id"] = id_
    corpo = (f'<figure class="wp-block-image aligncenter size-large">'
             f'<img src="{url}" alt="{alt}" class="{classe.strip()}" '
             f'width="{LARGHEZZA_ARTICOLO}" height="{int(LARGHEZZA_ARTICOLO * 0.56)}"/>'
             f'{figcaption}</figure>')
    return f'<!-- wp:image {json.dumps(attributi)} -->\n{corpo}\n<!-- /wp:image -->\n'


def blocco_html(contenuto: str) -> str:
    return f"<!-- wp:html -->\n{contenuto}\n<!-- /wp:html -->\n"


# --------------------------------------------------------------------------- #
# L'apertura (il «modulo info»)
# --------------------------------------------------------------------------- #

def apertura(copertina: dict | None, gancio: str, sintesi: str, primo_paragrafo: str) -> str:
    """`uagb/container` con dentro `uagb/info-box`: copertina, titolo-gancio, occhiello.

    Tre cose che si sbagliano sempre:
    - l'occhiello sta in `tempHeadingDesc` ed e' HTML: corsivo di sintesi, poi il paragrafo;
    - la copertina va dichiarata DUE volte: nell'oggetto `iconImage` (per l'editor) e come
      `<img>` nel markup (per la pagina). Senza `<img>` non si vede niente;
    - il trattino di `--ast-global-color-4` si scrive `\\u002d` perche' un commento HTML
      non puo' contenere `--`: scritto letterale, il commento si chiude a meta' e il
      blocco si perde.
    """
    copertina = copertina or {}
    id_ = copertina.get("id") or 0
    url = copertina.get("url", "")
    alt = (copertina.get("alt") or "").replace('"', "&quot;")
    titolo_img = (copertina.get("titolo") or "").replace('"', "&quot;")
    desc = f"<em>{sintesi}</em><br>{primo_paragrafo}"

    icona = {
        "id": id_, "url": url, "alt": alt, "title": titolo_img,
        "mime": copertina.get("mime", "image/webp"),
        "width": copertina.get("larghezza", 1400),
        "height": copertina.get("altezza", 1400),
        "sizes": {"full": {"url": url,
                           "width": copertina.get("larghezza", 1400),
                           "height": copertina.get("altezza", 1400)}},
    }
    attributi_container = {
        "block_id": "a7c2f10b",
        "backgroundType": "color",
        "backgroundColor": "var(\\u002d\\u002dast-global-color-4)",
        "variationSelected": True,
        "isBlockRootParent": True,
    }
    attributi_info = {
        "classMigrate": True,
        "tempHeadingDesc": desc,
        "headingColor": VERDE,
        "source_type": "image" if url else "none",
        "block_id": "b9d4e231",
        "imageAlt": alt,
        "imageSize": "full",
        "imgTagWidth": copertina.get("larghezza", 1400),
        "btnBorderTopWidth": 1, "btnBorderLeftWidth": 1,
        "btnBorderRightWidth": 1, "btnBorderBottomWidth": 1,
        "btnBorderStyle": "solid", "btnBorderColor": "#333",
    }
    if url:
        attributi_info["iconImage"] = icona

    immagine = (f'<div class="uagb-ifb-image-content"><img src="{url}" alt="{alt}" '
                f'width="{copertina.get("larghezza", 1400)}" '
                f'height="{copertina.get("altezza", 1400)}" loading="lazy" '
                f'class="uagb-ifb-image"/></div>' if url else "")

    return (
        f'<!-- wp:uagb/container {json.dumps(attributi_container, ensure_ascii=False)} -->\n'
        f'<div class="wp-block-uagb-container uagb-block-a7c2f10b alignfull uagb-is-root-container">'
        f'<div class="uagb-container-inner-blocks-wrap">'
        f'<!-- wp:uagb/info-box {json.dumps(attributi_info, ensure_ascii=False)} -->\n'
        f'<div class="wp-block-uagb-info-box uagb-block-b9d4e231 uagb-infobox__content-wrap  '
        f'uagb-infobox-icon-above-title uagb-infobox-image-valign-top">'
        f'<div class="uagb-ifb-content">{immagine}'
        f'<div class="uagb-ifb-title-wrap"><h3 class="uagb-ifb-title">{gancio}</h3></div>'
        f'<p class="uagb-ifb-desc">{desc}</p></div></div>\n'
        f'<!-- /wp:uagb/info-box --></div></div>\n'
        f'<!-- /wp:uagb/container -->\n'
    )


# --------------------------------------------------------------------------- #
# Le FAQ a scomparsa
# --------------------------------------------------------------------------- #

CSS_FAQ = """<style>
.ud-faq{max-width:820px;margin:0 auto;font-family:inherit}
.ud-faq details{background:#D9E1DA;border:1px solid #5B5F5C;border-left:4px solid #379557;border-radius:10px;margin:0 0 12px 0;overflow:hidden}
.ud-faq summary{list-style:none;cursor:pointer;position:relative;padding:14px 46px 14px 16px;color:#0C0D0D;font-weight:600;font-size:1rem;line-height:1.35;font-family:inherit}
.ud-faq summary::-webkit-details-marker{display:none}
.ud-faq summary::marker{content:""}
.ud-faq summary::after{content:"+";position:absolute;right:16px;top:50%;transform:translateY(-50%);color:#379557;font-size:1.5rem;font-weight:700;line-height:1}
.ud-faq details[open] summary::after{content:"\\2013"}
.ud-faq details[open] summary{border-bottom:1px solid rgba(91,95,92,.35)}
.ud-faq details p{margin:0;padding:14px 16px;color:#5B5F5C;font-size:.95rem;line-height:1.65}
@media (max-width:640px){.ud-faq summary{padding:12px 42px 12px 14px}}
</style>"""


def faq_html(domande: list[tuple[str, str]]) -> str:
    """Il blocco `html` delle FAQ: CSS con prefisso `.ud-faq` + una card per domanda.

    Il CSS e' *scoped* perche' non tocchi il resto del sito, e sta **dentro** il blocco:
    gli stili in linea non bastano, perche' il segno `+`/`-` e' uno pseudo-elemento e
    lo stato aperto e' `details[open]`, e nessuno dei due si raggiunge con `style=""`.

    Regola del sito: **niente `&` nel codice in linea** — WordPress lo converte in
    `&#038;` in modo discontinuo e il comportamento si perde in silenzio.
    """
    voci = "".join(
        f"<details><summary>{domanda}</summary><p>{risposta}</p></details>\n"
        for domanda, risposta in domande
    )
    return f'{CSS_FAQ}\n<div class="ud-faq">\n{voci}</div>'


def blocco_faq(domande: list[tuple[str, str]]) -> str:
    return blocco_html(faq_html(domande))


# --------------------------------------------------------------------------- #
# L'assemblaggio
# --------------------------------------------------------------------------- #

def testo_a_paragrafi(grezzo: str) -> list[str]:
    """Da testo semplice a paragrafi pronti per i blocchi.

    Tre sole trasformazioni, e nessuna riscrittura: via i richiami numerici `[1]`
    (che resterebbero senza la lista che li spiega), `**x**` → `<strong>`, `*x*` → `<em>`.
    Il corpo non si ritrascrive: ritrascriverlo introduce refusi che l'autore non ha scritto.
    """
    testo = re.sub(r"\[\d+\]", "", grezzo)
    testo = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", testo, flags=re.S)
    testo = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<em>\1</em>", testo, flags=re.S)
    pezzi = [re.sub(r"\s{2,}", " ", p).strip() for p in re.split(r"\n\s*\n", testo)]
    return [p for p in pezzi if p]


def componi(*, copertina: dict | None, gancio: str, sintesi: str,
            paragrafi: list[str], sezioni: list[tuple[int, str]] | None = None,
            immagini_corpo: list[dict] | None = None, faq: list[tuple[str, str]] | None = None,
            intro_faq: str = "", nota_fonte: str = "", invito: bool = True) -> str:
    """L'articolo intero, nelle nove parti, nell'ordine del modello.

    **Trappola del montaggio, da non ripetere:** l'apertura si prende il **primo
    paragrafo**, quindi gli indici delle sezioni si riferiscono ai paragrafi a partire
    dal **secondo**. Con gli indici sbagliati di uno, il primo titolo manca, ogni sezione
    porta il titolo della successiva e l'ultimo finisce sul penultimo paragrafo.
    """
    if not paragrafi:
        raise ValueError("l'articolo non ha paragrafi: non c'e' niente da comporre")

    sezioni = sezioni or []
    titoli: dict[int, str] = {}
    for indice, testo_titolo in sezioni:
        indice = int(indice)
        if indice in titoli:
            raise ValueError(
                f"due titoli di sezione cadono sullo stesso paragrafo ({indice}): "
                f"«{titoli[indice]}» e «{testo_titolo}». Un titolo senza paragrafo sotto "
                "non e' una sezione: togli il secondo, o scrivi un paragrafo sotto di lui."
            )
        titoli[indice] = testo_titolo
    if 0 in titoli:
        raise ValueError(
            "una sezione non puo' aprire sul paragrafo 0: quel paragrafo va dentro "
            "l'apertura. Gli indici delle sezioni partono da 1."
        )

    pezzi = [apertura(copertina, gancio, sintesi, paragrafi[0]), blocco_separatore()]

    # le immagini del corpo: chi le passa puo' dire dopo quale paragrafo (1-based),
    # altrimenti si distribuiscono da sole nel corpo, senza ammassarsi in fondo
    da_mettere = list(immagini_corpo or [])
    for n, immagine in enumerate(da_mettere):
        if not immagine.get("dopo"):
            passo = max(2, (len(paragrafi) - 1) // (len(da_mettere) + 1))
            immagine["dopo"] = min(len(paragrafi) - 1, passo * (n + 1))
    dopo = {int(i.get("dopo", 0)): i for i in da_mettere}

    for indice in range(1, len(paragrafi)):
        if indice in titoli:
            pezzi.append(blocco_h2(titoli[indice]))
        pezzi.append(blocco_paragrafo(paragrafi[indice]))
        if indice in dopo:
            pezzi.append(blocco_immagine(dopo[indice]))

    if faq:
        pezzi.append(blocco_h2("Domande frequenti"))
        if intro_faq:
            pezzi.append(blocco_paragrafo(f"<em>{intro_faq}</em>"))
        pezzi.append(blocco_faq(faq))

    if nota_fonte:
        pezzi.append(blocco_paragrafo(f"<em>{nota_fonte}</em>"))

    if invito:
        pezzi.append(blocco_invito())

    return "".join(pezzi)


# --------------------------------------------------------------------------- #
# Le validazioni: prima di creare, non dopo
# --------------------------------------------------------------------------- #

def _blocchi(markup: str) -> list[tuple[str, str]]:
    """Ogni commento di blocco con il suo JSON: (nome, json_grezzo)."""
    return re.findall(r"<!--\s*wp:([a-z0-9/-]+)\s*(\{.*?\})?\s*/?-->", markup, re.S)


def valida(markup: str) -> dict:
    """Tre controlli che si fanno **prima** di creare la bozza.

    Un attributo JSON malformato non da' errore: produce un blocco invalido che in
    editor si apre vuoto. Per questo si prova a leggerlo, blocco per blocco.
    """
    problemi: list[str] = []

    for nome, grezzo in _blocchi(markup):
        if not grezzo:
            continue
        try:
            json.loads(grezzo)
        except json.JSONDecodeError as errore:
            problemi.append(f"blocco «{nome}»: JSON non leggibile ({errore.msg})")

    for contenuto in re.findall(r"<!-- wp:html -->(.*?)<!-- /wp:html -->", markup, re.S):
        quanti = contenuto.count("&")
        if quanti:
            problemi.append(
                f"blocco html: {quanti} «&» nel codice in linea. WordPress li converte in "
                "&#038; in modo discontinuo e il comportamento si perde senza un errore."
            )

    identificatori = re.findall(r'"block_id"\s*:\s*"([^"]+)"', markup)
    for identificatore in {i for i in identificatori if identificatori.count(i) > 1}:
        problemi.append(f"block_id duplicato: {identificatore} (due blocchi si scambiano gli stili)")

    if re.search(r"<h1[\s>]", markup):
        problemi.append("c'e' un h1 nel corpo: l'h1 e' il titolo, lo mette WordPress")
    if "uagb-ifb-desc" in markup and not re.search(r"<em>.*?</em>", markup, re.S):
        problemi.append("l'occhiello non comincia con la frase-sintesi in corsivo")

    return {
        "ok": not problemi,
        "problemi": problemi,
        "h2": markup.count("wp-block-heading"),
        "immagini": markup.count("<img"),
        "blocchi_html": len(re.findall(r"<!-- wp:html -->", markup)),
        "byte": len(markup.encode("utf-8")),
    }


def titoli(markup: str) -> list[str]:
    """L'elenco dei titoli, per controllare che siano in ordine e senza salti."""
    fuori: list[str] = []
    if re.search(r"<h1[\s>]", markup):
        fuori.append("h1")
    for livello, testo in re.findall(r"<h([1-6])[^>]*>(.*?)</h\1>", markup, re.S):
        fuori.append(f"h{livello}: {re.sub(r'<[^>]+>', '', testo).strip()}")
    return fuori
