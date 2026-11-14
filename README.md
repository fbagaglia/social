# Social Studio — un testo, una immagine, tutti i social

App **locale** per pubblicare sui social (testo + immagine) dalla tua macchina.
Si comincia da un testo, da un link o da un video; si sceglie lo stile, si genera, si adatta
al singolo social e si pubblica — solo dopo aver letto che cosa esce.

```text
Social/
├── avvia_social_studio.bat   ← avvio (servizio + pagina)
├── ferma_social_studio.bat   ← chiusura
├── README.md                 ← questo file
├── TECNICHE-X.md             ← playbook X: cosa è verificato e cosa no, con fonti
├── API-SOCIAL-2026-11.md     ← accesso alle API di 17 reti, verificato alla fonte
├── report-postiz.md          ← valutazione di Postiz come hub self-hosted
├── collaudo_ui.py            ← batteria end-to-end (38 controlli, Playwright)
├── backend/
│   ├── server.py             ← entry point (http.server, sola libreria standard)
│   ├── config.py             ← lettura, fusione e mascheramento dei segreti
│   ├── parametri.py          ← i parametri della generazione, dichiarati come dati
│   ├── generazione.py        ← OpenRouter: scrive il testo e lo adatta al social
│   ├── fonti.py              ← legge link e video (Firecrawl, Brave, trascrizione)
│   ├── immagini.py           ← carica e genera le immagini
│   ├── stato.py              ← lavoro in corso e registro delle pubblicazioni
│   └── canali/               ← un modulo per rete; base.py è l'interfaccia
├── ui/                       ← pagina, stile, logica, guida in-app, icona
├── xpost/                    ← il MOTORE di pubblicazione su X (usabile anche da CLI)
├── config.json               ← chiavi e impostazioni (GITIGNORED)
├── data/                     ← allegati, lavoro in corso, registro (GITIGNORED)
└── logs/
```

## Avvio

```bash
avvia_social_studio.bat          # oppure:
py -3.14 backend/server.py       # il servizio resta in primo piano
```

Poi la pagina è su <http://127.0.0.1:8796/>. Ascolta **solo su 127.0.0.1**.

Serve la **chiave OpenRouter** in Configurazione: senza, l'app non inventa contenuti — si
ferma e lo dice. La ricerca web (Firecrawl, con Brave come alternativa) è accesa di default.

## Regola che vale sempre

**Nessuna pubblicazione automatica, e il giro è in due tempi.**
*Anteprima* non manda niente: dice che cosa uscirebbe, a nome di chi, le misure, gli
allegati, il costo stimato e i problemi con i numeri esatti. *Pubblica* esegue, e ci si
arriva solo dopo un secondo gesto. È la stessa regola degli altri canali (YouTube, console
contenuti).

## Che cosa è collegato

| Social | Stato | Come si pubblica |
|---|---|---|
| **Telegram** | **collegato** — Bot API | tasto *Pubblica su Telegram* |
| **Mastodon** | **collegato** — REST API | tasto *Pubblica su Mastodon* |
| **X / Twitter** | client pronto, manca l'app sviluppatore | tasto *Pubblica su X* |
| LinkedIn · Facebook · Instagram · Threads · Bluesky · YouTube | anteprima + consegna manuale | *Apri il compositore* / copia il testo |

Le credenziali di Telegram e Mastodon sono state prese dai progetti esistenti
(`Ultimate Crea post completo/config.json` → blocco `social`) e copiate in `config.json`
con uno script che legge e scrive senza mai stamparle. La presenza si verifica in locale;
l'account e il canale di destinazione si leggono dalla rete **prima** di inviare qualsiasi
cosa, e si vedono nella nota sotto i tasti.

Le nove reti hanno ciascuna il proprio tetto di caratteri e i propri vincoli sull'immagine,
verificati alla fonte (vedi `API-SOCIAL-2026-11.md`). L'app li mostra nell'anteprima.

**Perché non tutto collegato:** le reti "facili" (LinkedIn profilo, Facebook Page,
Instagram di un business proprio, Mastodon, Bluesky, Telegram, Reddit, Discord, Tumblr)
sono self-serve, ma Threads, TikTok, Pinterest, la pagina aziendale LinkedIn e Google
Business richiedono una **revisione**. Si collega una rete alla volta, quando serve.
L'architettura a canali regge entrambe le strade: aggiungere una rete è un modulo in
`backend/canali/`.

## Uso da riga di comando (il motore X)

Il pacchetto `xpost/` resta usabile da solo, ed è ciò che l'app chiama:

```bash
python -m xpost login      # una volta sola: apre il browser, salva il token
python -m xpost whoami     # controlla su quale account stai operando
python -m xpost draft --text "..." --image foto.png --source https://francobagaglia.it/blog/...
python -m xpost show latest --intent     # testo + intent URL, per la via manuale
python -m xpost publish latest           # INVIA davvero (chiede conferma)
```

## Collaudo

```bash
py -3.14 collaudo_ui.py    # servizio già avviato; 38 controlli su browser vero
```

Cosa copre: stato iniziale della pagina, le tre origini, generazione vera da OpenRouter,
adattamento a X, immagine generata e visibile nel browser, anteprima, mascheramento delle
chiavi, nessun errore JavaScript in console. La batteria azzera lo stato prima di misurare,
quindi si può ripetere.

Dipendenza usata **solo** dal collaudo: Playwright. L'app gira con la sola libreria standard.

## Documentazione

- **`TECNICHE-X.md`** — il playbook di X: endpoint, OAuth, costi, l'MCP ufficiale e cosa non è verificato.
- **`API-SOCIAL-2026-11.md`** — l'accesso alle API di 17 reti: auth, self-serve o revisione, limiti, fonti.
- **`report-postiz.md`** — Postiz self-hosted come hub: cosa copre, cosa serve, se conviene.
- **`ui/guida.md`** — la guida in-app (tasto ❓), con il registro delle novità.
