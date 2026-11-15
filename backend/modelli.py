"""L'elenco dei modelli da scegliere, invece di un campo da digitare a mano.

Il modello non si scrive: si sceglie. Ma l'elenco dipende dal **provider**, e il
provider e' l'indirizzo di base a cui si parla (`llm.orUrl`). Questo modulo tiene
le due cose insieme: dato il provider, si legge il suo catalogo e si restituisce
normalizzato.

Tutti i provider qui elencati parlano la stessa lingua (`/chat/completions` e
`/models` in forma OpenAI), che e' quella che l'app usa gia'. Anthropic non c'e'
perche' non la parla: se serve, va attraverso OpenRouter.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

# id, nome, indirizzo di base, se il catalogo si legge senza chiave
PROVIDER = [
    {"id": "openrouter", "nome": "OpenRouter", "url": "https://openrouter.ai/api/v1",
     "aperto": True, "nota": "una chiave sola, centinaia di modelli di tutti gli editori"},
    {"id": "openai", "nome": "OpenAI", "url": "https://api.openai.com/v1",
     "aperto": False, "nota": "solo i modelli OpenAI"},
    {"id": "google", "nome": "Google Gemini", "url": "https://generativelanguage.googleapis.com/v1beta/openai",
     "aperto": False, "nota": "endpoint in forma OpenAI"},
    {"id": "groq", "nome": "Groq", "url": "https://api.groq.com/openai/v1",
     "aperto": False, "nota": "modelli veloci, piano gratuito"},
    {"id": "deepseek", "nome": "DeepSeek", "url": "https://api.deepseek.com/v1",
     "aperto": False, "nota": ""},
    {"id": "mistral", "nome": "Mistral", "url": "https://api.mistral.ai/v1",
     "aperto": False, "nota": ""},
    {"id": "xai", "nome": "xAI (Grok)", "url": "https://api.x.ai/v1", "aperto": False, "nota": ""},
    {"id": "together", "nome": "Together", "url": "https://api.together.xyz/v1",
     "aperto": False, "nota": ""},
    {"id": "custom", "nome": "Altro (un indirizzo mio)", "url": "",
     "aperto": True, "nota": "per un server locale o un provider non in elenco"},
]

PER_CUI = {p["id"]: p for p in PROVIDER}
DURATA_CACHE = 3600          # il catalogo cambia lentamente: un'ora
CACHE: dict[str, tuple[float, dict]] = {}


class ModelliError(Exception):
    """Il catalogo non si e' potuto leggere: il motivo e' in chiaro."""


def catalogo_provider(conf: dict) -> dict:
    """I provider offerti e quale risulta scelto adesso, letto dall'indirizzo salvato."""
    indirizzo_ora = ((conf.get("llm") or {}).get("orUrl") or "").strip()
    return {
        "provider": PROVIDER,
        "attuale": provider_di(indirizzo_ora),
        "indirizzo": indirizzo_ora,
    }


def provider_di(url: str) -> str:
    """Quale provider e' un indirizzo? Serve a preselezionare la tendina."""
    indirizzo = (url or "").strip().rstrip("/")
    if not indirizzo:
        return "openrouter"
    for p in PROVIDER:
        if p["url"] and p["url"].rstrip("/") == indirizzo:
            return p["id"]
    for p in PROVIDER:                      # ripiego: il dominio
        if p["url"] and p["url"].split("//")[-1].split("/")[0] in indirizzo:
            return p["id"]
    return "custom"


def indirizzo(provider_id: str, conf: dict) -> str:
    """L'indirizzo di base del provider scelto (per «altro»: quello in configurazione)."""
    if provider_id == "custom":
        return ((conf.get("llm") or {}).get("orUrl") or "").strip().rstrip("/")
    scelto = PER_CUI.get(provider_id)
    if not scelto:
        raise ModelliError(f"provider sconosciuto: {provider_id}")
    return scelto["url"].rstrip("/")


def _raggruppa(identificatore: str, nome: str) -> str:
    """Il gruppo per la tendina: l'editore. Su OpenRouter e' il prefisso dell'id."""
    if "/" in identificatore:
        return identificatore.split("/")[0]
    if ":" in nome:
        return nome.split(":")[0].strip()
    return "altri"


def _gratuito(modello: dict) -> bool:
    identificatore = modello.get("id", "")
    if identificatore.endswith(":free"):
        return True
    prezzo = modello.get("pricing") or {}
    try:
        return float(prezzo.get("prompt", 1) or 1) == 0 and float(prezzo.get("completion", 1) or 1) == 0
    except (TypeError, ValueError):
        return False


def modelli(provider_id: str, conf: dict, *, forza: bool = False) -> dict:
    """Il catalogo del provider, normalizzato e ordinato per editore."""
    base = indirizzo(provider_id, conf)
    if not base:
        raise ModelliError(
            "per «Altro» serve prima un indirizzo: scrivilo e salva, poi l'elenco arriva"
        )
    adesso = time.time()
    salvato = CACHE.get(base)
    if salvato and not forza and adesso - salvato[0] < DURATA_CACHE:
        return salvato[1]

    chiave = ((conf.get("llm") or {}).get("orKey") or "").strip()
    intestazioni = {"Accept": "application/json", "User-Agent": "social-studio"}
    if chiave:
        intestazioni["Authorization"] = "Bearer " + chiave

    richiesta = urllib.request.Request(base + "/models", headers=intestazioni)
    try:
        with urllib.request.urlopen(richiesta, timeout=60) as risposta:
            dati = json.loads(risposta.read().decode("utf-8", "ignore"))
    except urllib.error.HTTPError as errore:
        dettaglio = errore.read(300).decode("utf-8", "ignore")
        raise ModelliError(
            f"{PER_CUI.get(provider_id, {}).get('nome', provider_id)}: HTTP {errore.code} "
            f"leggendo l'elenco dei modelli. {dettaglio[:200]}"
        ) from None
    except (urllib.error.URLError, TimeoutError) as errore:
        raise ModelliError(f"elenco non raggiungibile: {errore}") from None
    except json.JSONDecodeError:
        raise ModelliError("il provider ha risposto in un formato non leggibile") from None

    grezzi = dati.get("data") if isinstance(dati, dict) else dati
    if not isinstance(grezzi, list):
        raise ModelliError("la risposta non contiene un elenco di modelli")

    fuori = []
    for m in grezzi:
        if not isinstance(m, dict) or not m.get("id"):
            continue
        fuori.append({
            "id": str(m["id"]),
            "nome": str(m.get("name") or m["id"]),
            "gruppo": _raggruppa(str(m["id"]), str(m.get("name") or "")),
            "contesto": m.get("context_length") or 0,
            "gratuito": _gratuito(m),
        })
    if not fuori:
        raise ModelliError("il provider non ha restituito nessun modello")

    fuori.sort(key=lambda m: (m["gruppo"].lower(), m["nome"].lower()))
    esito = {
        "provider": provider_id,
        "indirizzo": base,
        "quanti": len(fuori),
        "quanti_gratuiti": sum(1 for m in fuori if m["gratuito"]),
        "modelli": fuori,
    }
    CACHE[base] = (adesso, esito)
    return esito
