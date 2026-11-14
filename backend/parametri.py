"""I parametri della generazione, dichiarati come DATI.

Il modulo in pagina lo disegna il JavaScript leggendo questa lista: aggiungere un
parametro e' una riga qui, e in interfaccia compare. Gli stessi dati li legge il
costruttore del prompt (`generazione.py`), cosi' i tre posti non divergono.
"""

from __future__ import annotations

# tipi ammessi: scelta | numero | booleana | multipla | testo_lungo
PARAMETRI = [
    {
        "chiave": "tono",
        "etichetta": "Tono",
        "tipo": "scelta",
        "predefinito": "professionale-umano",
        "valori": [
            "professionale-umano",
            "divulgativo",
            "riflessivo",
            "diretto",
            "ironico",
            "istituzionale",
        ],
        "nota": "Come deve suonare il testo, non quanto lungo deve essere.",
    },
    {
        "chiave": "pubblico",
        "etichetta": "Pubblico",
        "tipo": "scelta",
        "predefinito": "professionisti e studenti",
        "valori": [
            "professionisti e studenti",
            "docenti e formatori",
            "pubblico generico",
            "colleghi del settore",
            "decisori pubblici",
            "famiglie",
        ],
        "nota": "Chi legge: cambia il lessico e gli esempi.",
    },
    {
        "chiave": "lunghezza",
        "etichetta": "Lunghezza del testo di partenza (parole)",
        "tipo": "numero",
        "predefinito": 380,
        "min": 80,
        "max": 1500,
        "passo": 20,
        "nota": "Quanto deve essere lungo il testo base, prima dell'adattamento al social.",
    },
    {
        "chiave": "lingua",
        "etichetta": "Lingua",
        "tipo": "scelta",
        "predefinito": "it",
        "valori": ["it", "en"],
        "nota": "La lingua del testo generato.",
    },
    {
        "chiave": "ricerca_web",
        "etichetta": "Cerca sul web per arricchire",
        "tipo": "booleana",
        "predefinito": True,
        "nota": "Vale per l'input da link e da video. Firecrawl, con Brave come alternativa.",
    },
    {
        "chiave": "emoji",
        "etichetta": "Consenti emoji",
        "tipo": "booleana",
        "predefinito": False,
        "nota": "Se spenta, il testo resta senza emoji anche se il social le gradisce.",
    },
    {
        "chiave": "hashtag",
        "etichetta": "Aggiungi hashtag",
        "tipo": "booleana",
        "predefinito": True,
        "nota": "Nel testo base gli hashtag non entrano: li aggiunge l'adattamento al social, con il numero giusto per quella rete.",
    },
    {
        "chiave": "punto_di_vista",
        "etichetta": "Punto di vista",
        "tipo": "scelta",
        "predefinito": "prima persona",
        "valori": ["prima persona", "terza persona", "neutro"],
        "nota": "Come parla chi scrive.",
    },
    {
        "chiave": "istruzioni",
        "etichetta": "Indicazioni libere di stile",
        "tipo": "testo_lungo",
        "predefinito": "",
        "nota": "Tutto quello che vuoi imporre al testo: cosa tenere, cosa togliere, parole da usare o da evitare.",
    },
]

STILE_BASE = (
    "Tono diretto e scorrevole in italiano, frasi di media lunghezza, esempi concreti, "
    "struttura ordinata con sottotitoli dove serve."
)

# Il testo generato non deve mai contenere meta-introduzioni che parlano al lettore
# al posto del contenuto. Vale per ogni generazione, quindi sta qui una volta sola.
VIETATI = (
    "Non scrivere meta-introduzioni del tipo: Ecco, Di seguito, Questa e', Ti presento, "
    "In questo articolo. Non rivolgerti a chi ti ha dato il compito: il testo parla "
    "direttamente al lettore finale."
)


def predefiniti() -> dict:
    return {p["chiave"]: p["predefinito"] for p in PARAMETRI}


def normalizza(valori: dict | None) -> dict:
    """Riporta i valori ricevuti dentro i limiti dichiarati."""
    fuori = dict(predefiniti())
    for p in PARAMETRI:
        if not valori or p["chiave"] not in valori:
            continue
        valore = valori[p["chiave"]]
        if p["tipo"] == "booleana":
            fuori[p["chiave"]] = bool(valore)
        elif p["tipo"] == "numero":
            try:
                numero = int(valore)
            except (TypeError, ValueError):
                continue
            fuori[p["chiave"]] = max(p["min"], min(p["max"], numero))
        elif p["tipo"] == "scelta":
            fuori[p["chiave"]] = valore if valore in p["valori"] else p["predefinito"]
        else:
            fuori[p["chiave"]] = "" if valore is None else str(valore)
    return fuori
