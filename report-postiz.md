# Postiz self-hosted come hub di pubblicazione — report

Contesto: Windows 11, niente Docker "per ora", Node 24 e Python 3.14 disponibili.
Domanda: adottare Postiz self-hosted come hub unico invece di scrivere un client per ogni rete.
Regola: ogni affermazione ha l'URL della fonte; ciò che non è verificabile è marcato NON VERIFICATO.

---

## 1. Reti coperte per la PUBBLICAZIONE

Postiz pubblica (non solo analytics) su ~30+ reti. La pagina API ufficiale elenca
esplicitamente **32 piattaforme** con il relativo `__type`:

X (Twitter), LinkedIn (profilo e pagina), Facebook, Instagram (FB-linked e standalone),
Threads, TikTok, YouTube, Pinterest, Reddit, Bluesky, Mastodon, Lemmy, Warpcast (Farcaster),
Nostr, Telegram, Discord, Slack, VK, Google My Business, Dribbble, Kick, Twitch, Whop, Skool,
Medium, Dev.to, Hashnode, WordPress, Listmonk.

Fonti:
- https://docs.postiz.com/public-api/introduction ("Supported Platforms (32 total)")
- https://github.com/gitroomhq/postiz-app (README: "Schedule posts to:" + "30+ channels")
- https://postiz.com/ (FAQ "What social media channels does Postiz support?")

Nota: il CLI dichiara "28+ platforms" (https://docs.postiz.com/cli/introduction), coerente con lo stesso set.

---

## 2. Self-hosted: servono le proprie app sviluppatore?

**Sì per il self-hosted, no per Postiz Cloud.** La distinzione è netta e dichiarata dal progetto stesso:

| Area | Postiz Cloud | Postiz Open-source (self-hosted) |
|---|---|---|
| Social platform apps | App pre-approvate per ogni canale, pronte all'uso | **Crei le tue developer app su ogni piattaforma e passi la loro approvazione** (Meta, YouTube, TikTok possono richiedere settimane) |

Fonti:
- https://github.com/gitroomhq/postiz-app (tabella "Postiz Cloud vs. Open-source")
- https://postiz.com/ (FAQ: "Self-hosting means you provision the server, **create your own developer apps on each social network**, and handle updates, backups, and API approvals yourself")
- https://docs.postiz.com/self-host/providers/overview

Dettaglio operativo (self-hosted), da https://docs.postiz.com/self-host/providers/overview:
- **10 piattaforme NON richiedono configurazione**: l'utente fornisce le credenziali nel dialog di Postiz.
  Sono: Bluesky, Lemmy, Nostr, Medium, Dev.to, Hashnode, WordPress, Listmonk, Moltbook, Skool (via browser extension).
- **Tutte le altre richiedono una developer app** registrata sul portale della piattaforma, con le chiavi
  impostate come variabili d'ambiente sull'istanza. Redirect URI sempre nella forma
  `{FRONTEND_URL}/integrations/social/{provider}`.
- Nota: la pagina "installation/overview" dice "Eight platforms need no configuration at all"
  (https://docs.postiz.com/self-host/installation/overview) mentre la pagina providers/overview ne elenca dieci.
  Discrepanza nella documentazione ufficiale, non risolta alla fonte.

Opzionale a pagamento: Postiz offre un servizio di app-approval (non obbligatorio) per chi non vuole
gestire le review; Facebook/Instagram/Threads/YouTube costano di più perché richiedono più giri di review
(https://postiz.com/pricing, FAQ "I want the self-hosted service. Why do I need to pay for app approval?").

**Implicazione chiave:** self-hostare Postiz NON elimina il lavoro per-rete di registrazione/approvazione
delle app OAuth. Elimina il lavoro di *scrittura e manutenzione del codice di pubblicazione* per ogni rete.

---

## 3. Requisiti di installazione self-hosted

Da https://docs.postiz.com/self-host/installation/system-requirements e
https://docs.postiz.com/self-host/installation/docker-compose:

- **Docker**: il percorso canonico è Docker Compose (`git clone https://github.com/gitroomhq/postiz-docker-compose` + `docker compose up`).
- **Servizi esterni richiesti** (4):
  - PostgreSQL ≥ 14
  - Redis ≥ 6
  - **Temporal** (richiesto dalla v2.12.0; incluso nel docker-compose ufficiale)
  - Object storage: opzionale (`STORAGE_PROVIDER=local`, oppure Cloudflare R2)
- **Hardware minimo**: 2 vCPU / 2 GB RAM (all-in-one, uso leggero); raccomandato 4 vCPU / 8 GB.
- **Porte default**: container Postiz `5000` (compose mappa host `4007:5000`); backend Nest `3000`;
  frontend Next `4200`; Temporal `7233`, Temporal UI `8080`.
- **HTTPS in produzione**: obbligatorio (cookie sicuri) dietro reverse proxy.

**Si può installare su Windows senza Docker?**
**NON VERIFICATO.** La documentazione ufficiale offre solo percorsi basati su Docker o "from source":
Docker Compose, Docker standalone, Kubernetes/Helm, dev container VS Code, e Development Environment
(https://docs.postiz.com/self-host/installation/overview). Il percorso "Development Environment"
(https://docs.postiz.com/self-host/installation/development) esegue il monorepo da sorgente ma
**richiede comunque PostgreSQL, Redis e Temporal** come servizi esterni (variabili `DATABASE_URL`,
`REDIS_URL`, `TEMPORAL_ADDRESS`). Non esiste una guida ufficiale "Windows nativo senza Docker".
Su Windows le opzioni pratiche non documentate ufficialmente sarebbero Docker Desktop (WSL2) oppure
avviare a mano Postgres+Redis+Temporal — entrambe fuori dalla documentazione ufficiale.

---

## 4. API HTTP / server MCP per un'altra applicazione locale

**Sì, entrambi**, e sono utilizzabili da un'app esterna.

**REST API pubblica** — https://docs.postiz.com/public-api/introduction
- Endpoint esempi (cloud): `https://api.postiz.com/public/v1/integrations`, `/posts`, `/upload`.
- Autenticazione: header `Authorization: <api-key>`, **oppure** token OAuth2 (prefisso `pos_`).
- Rate limit: **90 richieste/ora** sull'endpoint di creazione post (100 su cloud); il self-hoster può
  regolarlo con la variabile `API_LIMIT`.
- Per self-hosted la base URL è la tua istanza. Il CLI lo conferma: `export POSTIZ_API_URL=https://your-postiz-server.com`
  (https://docs.postiz.com/cli/introduction). *Il valore esatto del path pubblico sull'istanza self-hosted
  non è scritto in modo esplicito nelle pagine lette → NON VERIFICATO al dettaglio; il CLI/API usano l'URL dell'istanza.*

**Server MCP** — https://docs.postiz.com/mcp/introduction
- Espone **13 tool** (integrationList, schedulePostTool, postsListTool, generateImageTool, clippingTool, ecc.).
- Self-hosted: "The MCP server starts as part of the Postiz backend and is reachable at
  `/mcp` (Bearer auth), `/mcp/:apiKey` (key in URL), and `/mcp-oauth` (OAuth-protected)."
  Il reverse proxy deve inoltrare questi path e supportare streaming HTTP.
- Auth: API key (Bearer o in URL) oppure token OAuth2 (`pos_`).

Conclusione: un'app locale può pilotare Postiz via REST API **o** via MCP, senza usare la UI web.
Esiste anche un CLI ufficiale (`npm install -g postiz`) e una skill per agenti (`npx skills add gitroomhq/postiz-agent`).

---

## 5. Licenza e vincoli

- **AGPL-3.0.** Il file LICENSE e il README lo dichiarano: "This repository's source code is available under the AGPL-3.0 license."
  Fonte: https://github.com/gitroomhq/postiz-app (sezione License + badge "License AGPL 3.0").
- Conferma dalla pagina prodotto: "published on GitHub under the AGPL-3.0 license" (https://postiz.com/, FAQ "Is Postiz open-source?").
- Il progetto dichiara: "We do not 'gate' features or limit the license."
  (https://github.com/gitroomhq/postiz-app, sezione "Postiz Cloud vs. Open-source").
- **Vincolo pratico dell'AGPL-3.0**: è copyleft di rete — se offri il software modificato come servizio
  in rete ad altri, devi rilasciare il sorgente. Per un uso **locale/privato** (il tuo caso) questo non
  crea obblighi verso terzi. Uso personale = nessun costo di licenza.

---

## 6. Alternative self-hosted

**Mixpost** (https://github.com/inovector/mixpost — https://mixpost.app/pricing)
- Licenza: **MIT** (Lite, open source). Le versioni Pro/Enterprise sono "source-available" (una volta pagate).
- Stack: **PHP 8.3+, MySQL, Redis, Nginx/Apache** (Laravel + Vue), non Node. Docker opzionale.
- Copertura pubblicazione:
  - **Lite (gratis)**: Facebook Pages, X, Mastodon.
  - **Pro ($299 una tantum)**: + Instagram (post/reel/stories), LinkedIn, YouTube, TikTok, Pinterest,
    Threads, Bluesky, Pixelfed, Google Business Profile.
- Ha API e **server MCP** (Pro/Enterprise). Multi-tenant, white-label.

**Socioboard** (https://github.com/Socioboard-developers/Socioboard-5.0 — https://github.com/socioboard/socioboard-core)
- "Commercial and Open Source", "It supports **nine** social media networks" (descrizione repo ufficiale).
- L'app hosted di terze parti dichiara sei reti: Facebook, Instagram, LinkedIn, Pinterest, X, YouTube
  (https://socialk.it/en/alternatives/socioboard). *Elenco delle nove reti della versione core non letto
  direttamente alla fonte → NON VERIFICATO nel dettaglio.*
- Progetto decisamente più vecchio/meno attivo di Postiz (ultima release Mixpost 2.6.0 a marzo 2026; Postiz
  rilascia quasi ogni giorno — vedi https://github.com/gitroomhq/postiz-app/releases).

**Altri nominati ma non verificati a fondo**: Postiz stesso cita in README lo sponsor ChatbotX
(ManyChat self-hosted) ma non è un publisher sociale → NON rilevante.

---

## Raccomandazione finale

**Conviene Postiz self-hosted per questo caso? DIPENDE — NO come prima scelta immediata su questo PC, SÌ se accetti il vincolo Docker e pubblichi su molte reti.**

Motivo, in breve:
- Il punto di forza reale è un **hub unico con REST API + MCP**: la tua app locale scrive a un solo
  contratto (https://docs.postiz.com/public-api/introduction) invece di N client per N reti. Questo è
  esattamente il risparmio che cerchi.
- Il costo nascosto: il self-hosted **richiede Docker + Postgres + Redis + Temporal** e **le tue developer
  app approvate su ogni rete** (https://github.com/gitroomhq/postiz-app). Su Windows 11 "senza Docker"
  non esiste un percorso ufficiale (NON VERIFICATO). E l'approvazione Meta/YouTube/TikTok "può richiedere
  settimane" — cioè rimetti dentro, in forma di burocrazia, parte del lavoro per-rete che volevi evitare.
- Quindi: se pubblichi su poche reti con API semplici (Bluesky, Mastodon, Telegram, X), scrivere client
  diretti è più leggero dell'intero stack Postiz. Se pubblichi su molte reti (5+), l'hub ripaga.

**Condizioni che renderebbero Postiz self-hosted preferibile (2-3):**
1. **Pubblichi su 5+ reti** e vuoi un solo endpoint (REST/MCP) da chiamare dalla tua app — il risparmio di
   manutenzione dei client per-rete supera il costo dello stack.
2. **Accetti Docker** (Docker Desktop/WSL2 su Windows, o una VM Linux/VPS) con Postgres+Redis+Temporal:
   è il requisito non negoziabile, e rimuove il vincolo "no Docker per ora".
3. **Sei disposto a registrare e far approvare le developer app per ogni rete** (settimane per Meta/YouTube/TikTok),
   oppure a pagare il servizio di app-approval opzionale di Postiz.

Se nessuna delle tre è vera ora, la scelta pragmatica è: client diretti per le 2-3 reti prioritarie,
e rivalutare Postiz self-hosted quando il numero di reti o la complessità OAuth cresce.
