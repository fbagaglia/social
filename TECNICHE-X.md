# Playbook X / Twitter — pubblicare testo + immagine

Tutto quanto segue e' **verificato alla fonte** il **14 novembre 2026** su
`docs.x.com` (documentazione ufficiale) e sulla specifica OpenAPI `v2.174`.
Dove una cifra viene da un'analisi di terzi (X non pubblica un listino unico),
e' dichiarato.

---

## 1. I fatti che decidono il progetto

### 1.1 Il tier gratuito non esiste piu'

- **6 febbraio 2026**: X ha sostituito i tier a canone con il **pay-per-usage**
  (crediti) come default per tutti i nuovi sviluppatori. Basic ($200/mese) e Pro
  ($5.000/mese) restano **solo per chi era gia' abbonato**: ai nuovi iscritti sono
  chiusi. *(fonte: docs.x.com › pricing, ripreso da socialcrawl.dev e postproxy.dev)*
- Il vecchio free tier era in scrittura (~1.500 post/mese, ~50 letture/24h, niente
  ricerca): **non e' piu' ottenibile**.
- Accesso gratuito solo per app "for-good public utility", caso per caso.

**Conseguenza:** la via A/B richiede una carta di credito e un budget, anche minimo.
Non e' piu' "gratis come una volta".

### 1.2 Costo per post (stima da analisi di terze parti, non da listino ufficiale)

| Azione | Costo indicativo |
|---|---|
| Creare un post di solo testo o con media | **~$0,015** |
| Creare un post **che contiene un URL** | **~$0,20** |
| Leggere un proprio post / i propri follower | ~$0,001 |
| Leggere un post di terzi | ~$0,005 |

> Il salto dell'URL (~1.900% in un repricing dell'aprile 2026) e' il dato piu'
> importante per chi pubblica articoli con il link in chiaro.
> *(fonte: blotato.com / socialcrawl.dev, che citano docs.x.com › pricing)*

**Tecnica che ne segue:** il link a `francobagaglia.it` costa 13 volte il post.
Alternative: accettarlo (~$0,20 e' comunque poco), mettere il link **dentro
l'immagine**, o tenerlo in bio / post fissato. Va deciso, non subito.

### 1.3 L'upload immagine e' finalmente in v2

Per anni l'unico modo di allegare un'immagine era l'endpoint v1.1. **Ora esiste in
v2** ed e' documentato:

```
POST https://api.x.com/2/media/upload
  media           il file (base64 in JSON, byte grezzi in multipart)
  media_category  tweet_image  (JPG, PNG, GIF, WEBP — max 5 MB)
                  tweet_gif    (GIF animato — max 15 MB)
  → { "data": { "id": "<media_id>", "media_key": "...", "size": N, ... } }

POST https://api.x.com/2/tweets
  { "text": "...", "media": { "media_ids": ["<media_id>"] } }
  → 201 { "data": { "id": "<post_id>", "text": "..." } }
```

Limiti: **fino a 4 foto**, oppure 1 GIF animata, oppure 1 video per post.
I limiti di durata/size del **video** dipendono dall'account che pubblica
(Premium o no), non dal piano API.

*(fonte: docs.x.com › x-api/media/upload-media, › x-api/posts/create-post,
OpenAPI v2.174)*

### 1.4 Autenticazione: OAuth 2.0 PKCE con contesto utente

Serve per pubblicare (un Bearer app-only **non** puo' agire come utente).

- Authorize: `https://x.com/i/oauth2/authorize`
- Token: `https://api.x.com/2/oauth2/token` (form-urlencoded)
- Scope necessari: `tweet.read tweet.write users.read media.write`
  **+ `offline.access`** per ottenere il refresh token (senza, il token vive 2 ore).
- **Client confidenziale** (Web App / Automated App / bot): si usa
  `Authorization: Basic base64(client_id:client_secret)` e il `client_id` **non**
  va nel body.
- **Client pubblico** (Native App / SPA): niente secret, `client_id` nel body.
- Il `redirect_uri` deve combaciare **esattamente** con un callback registrato
  sull'app.
- L'`auth_code` scade in **30 secondi**: va scambiato subito.

*(fonte: docs.x.com › fundamentals/authentication/oauth-2-0/authorization-code)*

---

## 2. L'MCP ufficiale di X — cos'e' e cosa (non) sappiamo

X espone un MCP server ospitato: **`https://api.x.com/mcp`**. Non lo si collega
direttamente (X non ha dynamic client registration ne' discovery MCP nativa):
si passa dal bridge locale **`xurl mcp`** (pacchetto npm `@xdevplatform/xurl`,
`npx` — nessuna installazione separata), che possiede l'identita' dell'app, fa il
login OAuth2 PKCE una volta e rinnova il token da solo.

- Oltre **200 endpoint** esposti come tool MCP.
- Esiste la modalita' `?read_only=true`: i tool di scrittura vengono **esclusi** —
  quindi in modalita' normale **i tool di scrittura ci sono**.
- Categoria dichiarata "Articles": *create draft Articles e publish*. La tabella
  delle capacita' pubblica **non elenca** la creazione di un post normale ne'
  l'upload di media come tool MCP.

**Onesta' tecnica:** la documentazione ufficiale conferma che i tool di scrittura
esistono, ma **non pubblica la lista dei tool**. Che `upload_media` + `create_post`
siano esposti via MCP **non e' verificato**: va provato con un handshake reale
(si vede subito con `xurl mcp https://api.x.com/mcp` e un `tools/list`).

**Il bridge e' locale e i dati non passano da terzi**: le credenziali restano sulla
macchina e viaggiano solo come Bearer verso `api.x.com`. Sotto questo profilo e'
pari alla via A, con in piu' la comodita' di avere i tool dentro l'agente.
Requisiti: app X + Node (`npx`) + una volta il browser per il login.

*(fonte: docs.x.com › tools/mcp)*

---

## 3. La tecnica a costo zero: passaggio manuale

Se non si vuole (ancora) aprire un account developer:

- **Intent URL** — `https://x.com/intent/post?text=<testo>&url=<link>` apre il
  compositore con testo e link gia' dentro. Verificato: risponde 307 verso il
  login se non si e' autenticati, poi atterra sul compositore.
  **Non supporta immagini**: l'allegato resta manuale.
- **Consegna file** — Hermes scrive testo (`.txt`) e immagine in `outbox/` e li
  presenta in chat; l'utente incolla e allega. Zero credenziali, zero costi,
  zero terzi.

E' la stessa forma adottata per i post Community di YouTube: l'agente prepara,
l'umano pubblica. Buona per rodare il formato prima di pagare l'API.

---

## 4. Canal di terzi (per completezza, non raccomandati qui)

Tutti richiedono un account sul servizio e **fanno passare testo e immagine dal
loro server**, con OAuth loro, non vostro.

| Servizio | Tipo | Copre |
|---|---|---|
| **Postiz** (open source, self-hosted) | si installa in casa, si creano le proprie app social | X + 9 altri |
| PostSider | MCP ospitato, OAuth | 30+ reti |
| AdaptlyPost | MCP ospitato, OAuth | 14 reti |
| BulkPublish | MCP ospitato, 80 tool | 15 reti |
| Postel | MCP ospitato, OAuth | X, LinkedIn, Bluesky, Mastodon |
| mbelinky/x-mcp-server, Infatoshi/x-mcp | MCP locali su GitHub | X, con `upload_media`/`post_tweet` |

Postiz self-hosted e' l'unico che tiene i dati in casa **e** copre piu' piattaforme;
in cambio va mantenuto (server, app per ogni rete, backup, aggiornamenti).

---

## 5. Cosa resta da decidere

1. **Aprire l'app su console.x.com?** (serve per A e B; pay-per-use, carta)
2. **Quale account** pubblica: `@francobagaglia`? (il login autorizza l'account
   con cui si e' loggati nel browser — controllare prima di autorizzare)
3. **Il link nell'immagine o nel testo?** (~$0,20 vs ~$0,015 per post)
4. **Solo X, o si vuole da subito la via multi-piattaforma** (Postiz self-hosted)?
5. **Classificazione AI Act art. 50**: se il post e' generato da un modello e
   contiene un'immagine sintetica, va dichiarato.
