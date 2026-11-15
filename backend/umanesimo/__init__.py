"""Il canale verso umanesimodigitale.info (WordPress + AI Engine, via MCP).

Tre pezzi, ognuno con un compito solo:
- `mcp`    — parlare col sito: handshake, chiamate ai tool, ritentativi;
- `articolo` — l'anatomia dell'articolo e il suo markup, con le validazioni;
- `media`  — caricare un'immagine (due passi, indirizzo monouso).
"""

from . import articolo, media, mcp  # noqa: F401

__all__ = ["articolo", "media", "mcp"]
