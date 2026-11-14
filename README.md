# Social — pubblicare testo + immagine sui social, da Hermes

Progetto per mettere a punto, in modo ripetibile, **come Hermes pubblica un post
(testo + immagine)** sui canali social. Si comincia da **X / Twitter**.

```
Social/
├── README.md            ← questo file: mappa delle tecniche e stato del progetto
├── TECNICHE-X.md        ← playbook X/Twitter: cosa e' verificato, cosa no, con fonti
├── xpost/               ← implementazione della via "API ufficiale X" (solo stdlib)
│   ├── config.py
│   ├── auth.py          ← OAuth 2.0 PKCE, cache del token, refresh
│   ├── api.py           ← upload immagine + creazione post
│   └── cli.py           ← CLI: login / whoami / draft / list / show / publish
├── outbox/              ← i post preparati e da approvare (bozze JSON + immagini)
└── .state/              ← token e credenziali locali (in .gitignore, mai in chat)
```

## Regola che vale sempre

**Nessuna pubblicazione automatica.** Hermes prepara testo + immagine e li deposita
in `outbox/`; la pubblicazione e' un comando esplicito (`publish`) che l'utente
decide. E' la stessa regola che regge gli altri canali (YouTube, console contenuti).

## Le tre tecniche, in breve

| # | Tecnica | Credenziali | Immagine | Costo | Chi vede i dati |
|---|---|---|---|---|---|
| **A** | **API ufficiale X v2** (implementata qui) | app X developer + login OAuth2 | si | pay-per-use (~$0.015/post) | solo X |
| **B** | **MCP X ufficiale** (`api.x.com/mcp` via bridge `xurl`) | app X developer + login OAuth2 | da verificare | pay-per-use | solo X |
| **C** | **Passaggio manuale** (intent URL + file pronti) | nessuna | si, a mano | 0 | nessuno |
| D | MCP/plug-in di terzi (PostSider, AdaptlyPost, Postel, Postiz self-hosted) | account sul servizio | si | abbonamento/crediti | il terzo |

Dettaglio, limiti e fonti: `TECNICHE-X.md`.

## Stato

- [x] Ricognizione verificata alla fonte (docs.x.com, OpenAPI v2.174) — 14 nov 2026
- [x] Via **A** implementata end-to-end (login → upload → post), solo libreria standard
- [ ] Creazione dell'app su console.x.com e `login` (serve una decisione dell'utente)
- [ ] Primo post reale di prova
- [ ] Canale successivo: LinkedIn (l'MCP X e' solo X; per gli altri si riparte da capo)

## Uso (dopo il login)

```bash
python -m xpost login      # una volta sola: apre il browser, salva il token
python -m xpost whoami     # controlla su quale account stai operando

# prepara una bozza (non pubblica nulla)
python -m xpost draft --text "..." --image foto.png --source https://francobagaglia.it/blog/...

python -m xpost list                 # elenca le bozze
python -m xpost show latest          # testo + immagine pronti da incollare a mano
python -m xpost publish latest       # INVIA davvero (chiede conferma)
```

Nessuna dipendenza esterna: solo la libreria standard di Python 3.11+.
