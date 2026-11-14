# API ufficiali di pubblicazione (testo + immagine) — verifica al 14 novembre 2026

Progetto: app locale per pubblicare post (testo + immagine) su più reti.
Ambito: **solo API UFFICIALI di pubblicazione** (no scraping). Ogni riga dichiara la data
della fonte consultata e l'URL ufficiale. Dove un dato non è stato verificato alla fonte è
scritto **NON VERIFICATO**.

Legenda colonna "Accesso": **Self-serve** = un singolo sviluppatore parte subito, senza
revisione; **Con revisione** = serve un'app review / audit / verifica aziendale / approvazione.

---

## Tabella

| Rete | API ufficiale sì/no | Auth | Accesso self-serve o con revisione | Limiti/costi | Fonte URL (data consultazione) |
|---|---|---|---|---|---|
| **X / Twitter** | Sì (X API v2) | OAuth 2.0 (user) — scope `tweet.read tweet.write users.read media.write` + `offline.access` | Self-serve, ma **niente tier gratuito** (rimosso dal 6 feb 2026): pay-per-use a crediti, serve carta | ~**$0,015/post** (testo o con media), **~$0,20 se il testo contiene un URL**. Media: `POST /2/media/upload`, `media_category=tweet_image` (JPG/PNG/GIF/WEBP, max 5 MB) o `tweet_gif` (max 15 MB). Max 4 foto / 1 GIF / 1 video. Post: `POST /2/tweets` con `media.media_ids` | https://docs.x.com/x-api/media/upload-media · https://docs.x.com/x-api/posts/create-post (verificato 14 nov 2026) |
| **LinkedIn — profilo personale** | Sì (Posts API / UGC) | OAuth 2.0 (member) — scope `w_member_social` | **Self-serve**: nel Developer Portal aggiungi il prodotto "Share on LinkedIn" → ottieni `w_member_social`, nessuna review | Endpoint `POST https://api.linkedin.com/rest/posts` (o `v2/ugcPosts`). Immagine: carichi l'asset e usi `urn:li:image:…`. Limiti caratteri: **NON VERIFICATO** | https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/share-on-linkedin (doc Marketing October 2026) |
| **LinkedIn — pagina aziendale** | Sì (Posts API) | OAuth 2.0 — scope `w_organization_social` (richiede ruolo admin/CONTENT_ADMIN sulla pagina) | **Con revisione**: serve il prodotto **Community Management API** ("Apply for Community Management API") | Stesso endpoint `POST /rest/posts` con `author: urn:li:organization:…`. Header `Linkedin-Version: YYYYMM` + `X-Restli-Protocol-Version: 2.0.0`. Versioni deprecate: la 202511 va in sunset il 16 nov 2026 | https://learn.microsoft.com/en-us/linkedin/marketing/increasing-access?view=li-lms-2026-10 · https://learn.microsoft.com/en-us/linkedin/marketing/community-management/shares/posts-api (ultimo agg. 13/05/2026) |
| **Facebook Page** | Sì (Pages API) | OAuth 2.0 + **Page access token** — permessi `pages_manage_posts`, `pages_read_engagement`, `pages_read_user_engagement` (+`publish_video`) | **Self-serve** se pubblichi su una Page di cui sei admin (Standard Access, nessuna review). Per utenti senza ruolo sulla app → **Advanced Access + App Review + business verification** | Testo: `POST /page_id/feed`. Foto: `POST /page_id/photos` con `url` + `message`. Scheduling 10 min–30 gg. Limiti immagine: **NON VERIFICATI** | https://developers.facebook.com/documentation/pages-api/posts (Updated Apr 17, 2026) · https://developers.facebook.com/docs/graph-api/overview/access-levels (Updated 6 lug 2023) |
| **Instagram (Business/Creator)** | Sì (Instagram Platform — Content Publishing) | OAuth 2.0 (Facebook Login for Business **oppure** Instagram Login) — permessi `instagram_content_publish` + `instagram_basic` (o `instagram_business_content_publish`) | **Self-serve** se l'app serve solo un business tuo (Standard Access, App Review NON richiesta). Per servire più business (tech provider) → **Advanced Access + App Review (+ business verification)** | Flusso a 2 passi: `POST /<IG_ID>/media` (container con `image_url` su server pubblico) → `POST /<IG_ID>/media_publish`. Limite: **100 post pubblicati via API / 24h** (caroselli = 1). **Solo JPEG**. Richiede Page Publishing Authorization | https://developers.facebook.com/documentation/instagram-platform/content-publishing (Updated Oct 20, 2026) · https://developers.facebook.com/documentation/instagram-platform/app-review (Updated Jun 30, 2026) |
| **Threads** | Sì (Threads API) | OAuth 2.0 (Threads user access token: short 1 h → long 60 gg) — permessi `threads_basic`, `threads_content_publish` | Per i **tester/ruoli** dell'app: nessuna review. Per utenti senza ruolo: **ogni permesso deve passare App Review** e l'app deve essere pubblicata | Container: `POST https://graph.threads.com/v1.0/<user>/threads` (`media_type=IMAGE`, `image_url`, `text`) → `POST /<user>/threads_publish`. Limiti: **250 post/24h**, testo **500 caratteri**, immagine JPEG/PNG max **8 MB** | https://developers.facebook.com/documentation/threads/overview (Updated Dec 22, 2025) · https://developers.facebook.com/documentation/threads/get-started (Updated Jun 30, 2026) |
| **TikTok** | Sì (Content Posting API) | OAuth 2.0 (user access token) — scope `video.publish` (deve essere approvato) | **Con revisione**: per pubblicare pubblicamente serve un **audit** del client. I client NON revisionati possono postare **solo in modalità privata** (`SELF_ONLY`) | Endpoint `POST https://open.tiktokapis.com/v2/post/publish/content/init/` con `post_mode=DIRECT_POST`, `media_type=PHOTO` (foto via URL su dominio verificato). Limite: **6 richieste/min per access token**; caption max **2200 caratteri UTF-16** | https://developers.tiktok.com/doc/content-posting-api-get-started (Last updated Aug 4, 2026) · https://developers.tiktok.com/doc/content-posting-api-reference-direct-post (Last updated Oct 27, 2026) |
| **YouTube — video** | Sì (YouTube Data API v3) | OAuth 2.0 | **Self-serve** (progetto Google Cloud). La verifica OAuth serve se rendi l'app pubblica; per uso tuo/in Testing no. Tempi medi di verifica: **NON VERIFICATO** | `videos.insert` (upload resumable). Quota 2026: bucket dedicato `videos.insert` = **100 upload/giorno** di default, costo **1**; altri endpoint 10.000 unità/giorno combinate | https://developers.google.com/youtube/v3/determine_quota_cost · https://developers.google.com/youtube/v3/docs |
| **YouTube — post Community** | **No** | — | — | La YouTube Data API v3 **non espone** un endpoint per creare post Community. Eventuali API ufficiali alternative: **NON VERIFICATO** | https://developers.google.com/youtube/v3/docs (nessuna risorsa `communityPosts`; verificato 14 nov 2026) |
| **Pinterest** | Sì (API v5) | OAuth 2.0 (Authorization Code / Client Credentials) | **Con revisione** per pubblicare davvero: prima Trial access (app approvata), poi **Standard access** con **revisione manuale + video demo**. I Pin creati in Trial sono **sandbox** (visibili solo al creatore) | `POST /v5/pins`. Rate limit: Trial = per app/giorno; Standard = per minuto/utente/app. Nota: app registrate dal **14 set 2026** possono ricevere HTTP 403 `PINNER_DATA_ACCESS_DENIED` | https://developers.pinterest.com/docs/key-concepts/access-tiers/ · https://developers.pinterest.com/docs/getting-started/set-up-authentication-and-authorization/ (verificato 14 nov 2026) |
| **Reddit** | Sì | OAuth 2.0 | **Self-serve** (registri l'app e parti). Termini per l'uso commerciale: **NON VERIFICATI qui** | `POST /api/submit` con `kind=image` (title max **300 caratteri**); l'immagine va prima caricata (`POST /api/media/asset.json`). Rate limit free access: **100 query/min per OAuth client id**. Traffico senza OAuth viene bloccato | https://support.reddithelp.com/hc/en-us/articles/16160319875092-Reddit-Data-API-Wiki · https://www.reddit.com/dev/api/ (verificato 14 nov 2026) |
| **Mastodon** | Sì (REST API) | OAuth 2.0 (registri l'app via `POST /api/v1/apps`, poi OAuth) — scope `write:statuses`, `write:media` | **Self-serve**: nessuna app review, nessun gatekeeper (dipende dall'istanza) | Upload: `POST /api/v1/media` → `POST /api/v1/statuses` con `media_ids`. Rate limit default: **300 richieste/5 min per account**; upload media **30/30 min**. I limiti li fissa ogni istanza | https://docs.joinmastodon.org/client/token/ (ultimo agg. 10 ott 2024) · https://docs.joinmastodon.org/methods/media/ · https://docs.joinmastodon.org/api/rate-limits/ (ultimo agg. 20 nov 2022) |
| **Bluesky** | Sì (AT Protocol / `com.atproto`) | **App password** + `com.atproto.server.createSession` → access JWT (Bearer). Non OAuth per il PDS pubblico | **Self-serve**: crei un'app password dal profilo, nessuna review | Upload: `com.atproto.repo.uploadBlob` → `com.atproto.repo.createRecord` (`app.bsky.feed.post` con embed `app.bsky.embed.images`). Limiti: testo **300 graphemes e 3000 byte**; immagine max **1.000.000 byte**; fino a **4 immagini** | https://atproto.com/blog/create-post · https://github.com/bluesky-social/atproto (lexicon `app.bsky.feed.post`, `app.bsky.embed.images`) (verificato 14 nov 2026) |
| **Telegram** | Sì (Bot API) | **Bot token** da @BotFather (nessun OAuth) | **Self-serve**: crei un bot e parti subito | `POST https://api.telegram.org/bot<token>/sendPhoto` (foto + `caption`). Limiti: foto max **10 MB**, larghezza+altezza max **10000**, ratio max **20**; caption **0–1024 caratteri** | https://core.telegram.org/bots/api#sendphoto (verificato 14 nov 2026) |
| **Discord** | Sì (API) | **Bot token** (Developer Portal), header `Authorization: Bot <token>` | **Self-serve**: crei l'app/bot e parti subito | `POST /channels/{channel.id}/messages` (`content` + `attachments`). Limiti: `content` max **2000 caratteri**; fino a **10 embed**; dimensione richiesta max **25 MiB**; ~**50 req/s** per bot | https://docs.discord.com/developers/resources/message · https://docs.discord.com/developers/topics/rate-limits (verificato 14 nov 2026) |
| **Google Business Profile** | Sì (Business Profile API) | OAuth 2.0 | **Con revisione**: bisogna **richiedere l'accesso** via form di contatto e attendere l'approvazione; l'API è pensata per aziende grandi/terze parti | `POST /v4/{parent=accounts/*/locations/*}/localPosts` (crea un local post). Limiti specifici e costi: **NON VERIFICATI** | https://developers.google.com/my-business/reference/rest · https://developers.google.com/my-business/content/prereqs (Last updated 2026-08-28) · https://support.google.com/business/answer/6333473 |
| **Tumblr** | Sì (API v2) | **OAuth 1.0a** (e anche OAuth 2.0 disponibile) | **Self-serve**: registri l'app per ottenere le chiavi OAuth | `POST /v2/blog/{blog}/posts` (Neue Post Format) o `/post` (legacy). Limiti: **1.000 chiamate/ora per consumer key**; **250 post pubblicati/giorno per utente**; **250 immagini/giorno per utente** | https://www.tumblr.com/docs/en/api/v2 (verificato 14 nov 2026) |

---

## Le 3 reti più facili per partire

Tutte self-serve, gratuite, senza revisione: bot token o registrazione app, e si pubblica subito
testo + immagine.

1. **Telegram** — bot token da @BotFather, `sendPhoto` con `caption`. Nessuna approvazione, nessun costo.
2. **Discord** — bot token dal Developer Portal, `POST /channels/{id}/messages` con allegato. Nessuna approvazione, nessun costo.
3. **Mastodon** — registri l'app via `POST /api/v1/apps` (OAuth 2.0), poi upload media + status. Nessun gatekeeper.
   *Menzione:* **Bluesky** (app password, `uploadBlob` + `createRecord`) e **Reddit** (OAuth, `POST /api/submit`) sono anch'esse self-serve e gratuite.

X è self-serve ma **non più gratuito** (pay-per-use dal 6 feb 2026): va messo a parte.

## Le reti che richiedono revisione (app review / audit / verifica)

- **Meta — Instagram, Threads, Facebook Page**: se l'app serve utenti che **non** hanno un ruolo
  sulla app, ogni permesso di pubblicazione richiede **App Review**, e l'Advanced Access richiede
  una **business verification** (dal 1 feb 2023). Se l'app serve solo un business tuo (Standard
  Access) non serve review.
- **TikTok**: **audit** obbligatorio per pubblicare pubblicamente; i client non revisionati
  postano solo in modalità privata.
- **Pinterest**: da Trial a **Standard access** con **revisione manuale + video demo**; in Trial i
  Pin sono sandbox.
- **LinkedIn — pagina aziendale**: serve il prodotto **Community Management API** (domanda di
  accesso). Il profilo personale invece è self-serve.
- **Google Business Profile**: **richiesta di accesso** e attesa di approvazione.
- **YouTube (video)**: verifica OAuth se l'app diventa pubblica; per uso personale in Testing no.
