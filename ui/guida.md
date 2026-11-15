# Guida di Social Studio

## Novità di questa versione (0.5.0)

- **Il blog è una destinazione, non un social.** Scegliendo *Umanesimodigitale.info*
  compare un pannello suo (4b) con i pezzi che solo un articolo ha: due immagini nel
  corpo, le FAQ a scomparsa, i campi SEO. Il tasto finale dice **Deposita la bozza** e
  crea la bozza su WordPress — la pubblicazione resta una tua decisione.
- **Il modello non si scrive più: si sceglie.** In Configurazione prima il *provider*,
  poi il modello dal suo catalogo, raggruppato per editore. Un nome sbagliato di un
  carattere non dà errore: dà un guasto alla prima generazione. Adesso non si sbaglia.
- **Le FAQ hanno l'anteprima vera.** Quello che vedi nell'anteprima **è** il markup che
  finisce nell'articolo: non due cose che possono divergere.

## Versione 0.4.0

- **La consegna manuale si spiega da sola.** Scegliendo una rete compare la riga che dice
  come si consegna il post *su quella rete*: per Facebook "prima il testo, poi l'immagine",
  per Instagram "si pubblica dall'app del telefono", per Telegram "pubblica da qui".
- **Il tasto non mente.** Dice *Apri il compositore* solo quando l'indirizzo porta davvero
  il testo dentro (X, LinkedIn, Threads, Bluesky); per le altre dice *Apri Facebook*,
  *Apri Instagram*, perché apre soltanto il sito.
- **`1. Copia il testo` nella zona di invio**, in ordine col tasto dell'immagine: il
  flusso a copia-incolla sta tutto in un posto e si legge da sinistra a destra.
- `Copia il testo` copia **quello che hai corretto a mano**, non la versione generata.

## Versione 0.3.0

- **X in modalità compositore, per scelta.** L'API di X è a pagamento e l'app non
  insiste più: prepara testo e immagine, apre il compositore, e l'allegato lo fai tu.
  Nessun costo, nessuna carta di credito. L'interruttore è in Configurazione, e resta
  spento di default.
- **L'immagine a portata di mano.** Due tasti nuovi sotto l'anteprima: **Copia
  l'immagine** (poi Ctrl+V nel riquadro del post, senza cercare file) e **Apri la
  cartella** (si apre con il file già selezionato, da trascinare).
- L'anteprima **non ti rimprovera più le credenziali di X**: una scelta non è un difetto.

## Versione 0.2.0

- **Tre reti pubblicano davvero**: X/Twitter (API ufficiale, serve la tua app), e ora
  **Telegram** e **Mastodon**, collegati con le credenziali già presenti negli altri
  progetti. Le altre sei restano in consegna manuale.
- Il tasto di invio ora **dice su quale rete pubblica** (*Pubblica su Telegram*) e la
  nota sotto mostra **su quale canale o account scriverà**, letto dalla rete prima di
  inviare qualsiasi cosa.
- Il tasto non dipende più da una chiamata di rete: se Telegram o Mastodon non
  rispondono, il tasto resta disponibile e l'avviso lo dice, invece di dichiarare il
  canale "non collegato".
- **Cambiare social non perde più quello che hai scritto a mano**: passando a un'altra
  rete, le correzioni di quella precedente vengono salvate e ritrovate.

## Versione 0.1.0

- **Prima versione.** Un solo posto dove partire da un testo, da un link o da un video,
  e da lì adattare titolo e testo a ogni social e pubblicare.
- **X/Twitter pubblica davvero**, con l'API ufficiale (OAuth 2.0).
- **Due immagini possibili**: la tua, oppure una card generata dall'app con testo nitido.
- **Nessuna pubblicazione automatica**: l'anteprima non manda niente, e il tasto di
  invio si preme una volta sola dopo aver letto che cosa esce.

## A che cosa serve

Social Studio prende un materiale di partenza e lo trasforma in post pronti per le reti
social, con il tono e i limiti di ciascuna. Niente viene pubblicato senza un tuo gesto
esplicito, e niente viene inventato: se manca la chiave del modello l'app si ferma e lo dice.

## Il giro di lavoro, in sei passi

### 1. Da dove parte il testo

- **Un testo da rivisitare** — incolli quello che hai già scritto e lo fai riscrivere
  con lo stile che scegli.
- **Un link** — l'app legge la pagina. Con la chiave **Firecrawl** impostata legge
  meglio; senza, legge la pagina direttamente. **Brave**, se presente, aggiunge
  contesto dal web.
- **Un video YouTube** — il testo viene dalla **trascrizione automatica** del video.
  Se il video non ha sottotitoli, l'app lo dice e ti chiede di incollare il testo:
  non inventa nulla.

### 2. Stile e parametri

Tono, pubblico, lunghezza, lingua, emoji, hashtag, punto di vista e un campo libero di
indicazioni. I parametri si leggono dal modulo in pagina; il tasto *Ripristina i
predefiniti* rimette i valori di partenza — che sono tuoi, quindi non vengono mai
sovrascritti d'ufficio.

La casella **Cerca sul web per arricchire** è accesa di default e vale per il link e per
il video.

### 3. Titolo e testo

*Genera titolo e testo* produce il materiale di partenza. **Entrambi i campi sono
modificabili**: quello che pubblichi è quello che leggi nella pagina, non una copia
nascosta. Ogni campo ha il suo tasto **Copia**.

### 4. Adatta al social

Scegli la rete fra quelle in elenco. Il titolo e il testo vegono riscritti con le regole
di quella rete e il suo tetto di caratteri. Il contatore dice quanti caratteri restano;
se sfori, **il testo non viene troncato**: te lo dice e lo accorci tu.

Ogni versione resta salvata: se torni su quel social la ritrovi come l'avevi lasciata.

Fra le destinazioni c'è anche **Umanesimodigitale.info**, che non è un social: scegliendolo
compare il pannello **4b** (vedi sotto).

### 4b. La destinazione blog (Umanesimodigitale.info)

Un articolo non è un post: ha un titolo-gancio, una frase-sintesi, delle FAQ e dei campi
SEO che un social non ha. Per questo il pannello è suo, e compare solo scegliendolo.

- **Due immagini nel corpo** (facoltative): vanno *dentro* il testo, dopo un paragrafo, e
  ognuna vuole il suo `alt` — serve a chi non vede l'immagine. La copertina della sezione 5
  diventa invece l'immagine in evidenza e quella dell'apertura.
- **FAQ a scomparsa**: *Genera le FAQ* scrive da 3 a 5 domande con risposta
  autosufficiente. **L'anteprima è il markup che si pubblica**: non sono due cose che
  possono divergere. Correggi domande e risposte a mano e l'anteprima segue.
- **Campi SEO**: *Genera titolo e descrizione* rispetta i tetti del sito (60 e 160
  caratteri) e li **misura**, non li stima: se il modello sfora glielo si dice con il
  numero vero e riscrive.
- **I titoli di sezione si scrivono con il prefisso `## `** dentro il testo: una riga che
  comincia così diventa un titolo di sezione. Il primo paragrafo va nell'apertura, quindi
  la prima sezione non può cadere lì (l'app te lo dice).
- **Il tasto finale dice `Deposita la bozza`**, non `Pubblica`: crea la bozza su WordPress
  con categorie, immagine in evidenza e campi SEO già dentro, e ti restituisce l'ID e il
  link di anteprima. **La pubblicazione la fai tu da wp-admin.**

### 5. Immagine

Due vie, entrambe legittime:

- **Carica una tua immagine** (PNG, JPG, WEBP, GIF).
- **Genera una card** dall'app: grafica con testo nitido sulla tavolozza del progetto,
  in formato orizzontale 16:9, quadrato o verticale 4:5. Non è un'immagine generata da un
  modello di intelligenza artificiale: è disegno, quindi non va dichiarata come sintetica.

### 6. Anteprima e invio

**Il giro è in due tempi, sempre.**

1. *Anteprima* non manda niente. Dice che cosa uscirebbe, **a nome di chi**, quante
   misure ha, quali allegati porta, il costo stimato, e i **problemi** con i numeri
   esatti. Anche quando dice di no, l'anteprima risponde normalmente: i problemi sono la
   risposta a una domanda, non un guasto.
2. *Pubblica* esegue, e ci si arriva solo dopo aver premuto e confermato.

*Nota:* per X il costo stimato è di circa **0,015 USD** per un post di testo o con
immagine, ma sale a circa **0,20 USD se il testo contiene un indirizzo web**. Se pubblichi
articoli con il link in chiaro, sappi che quell'URL costa tredici volte il resto.

## Che cosa è collegato e che cosa no

| Social | Stato | Come si pubblica |
|---|---|---|
| **Telegram** | **collegato** (Bot API) | *Pubblica su Telegram* — con foto diventa una didascalia |
| **Mastodon** | **collegato** (REST API) | *Pubblica su Mastodon* — caricamento immagine compreso |
| X / Twitter | **compositore, per scelta** (l'API è a pagamento) | *Apri il compositore* + **Copia l'immagine** → Ctrl+V |
| LinkedIn | manuale | *Anteprima* → *Apri il compositore* |
| Facebook | manuale | *Anteprima* → copia il testo |
| Instagram | manuale | serve un'immagine JPEG; pubblica dall'app del telefono |
| Threads | manuale | *Anteprima* → *Apri il compositore* |
| Bluesky | manuale | *Anteprima* → *Apri il compositore* |
| YouTube (post Community) | manuale | non esiste API pubblica per pubblicarlo |
| **Umanesimodigitale.info** | **collegato** (WordPress via MCP) | *Deposita la bozza* — l'articolo, non un post |

Il tasto di invio è **spento** quando la rete scelta non è pronta, e la ragione è scritta
sotto. Un canale in consegna manuale non sparisce: resta in elenco e offre *Apri il
compositore*.

### La consegna manuale, in pratica

Per le reti che si pubblicano dal compositore (X, LinkedIn, Instagram, Threads, Bluesky,
Facebook, YouTube) il giro è questo:

1. **Adatta** il testo alla rete, correggilo, poi premi **Anteprima**.
2. Premi **Apri il compositore**: si apre la pagina di pubblicazione **con il testo già
   dentro**.
3. Per l'immagine: premi **Copia l'immagine** e poi **Ctrl+V** nel riquadro del post,
   oppure **Apri la cartella** e trascina il file dentro.
4. Pubblica tu.

Il primo passaggio è anche l'ultimo: **il compositore non porta le immagini** (l'indirizzo
di X accetta solo testo), quindi l'immagine va sempre allegata a mano. I due tasti nuovi
servono esattamente a non farla cercare.

**Attenzione all'ordine, quando la rete non precompila il post.** Negli appunti di Windows
ci sta una cosa per volta: se copi l'immagine, il testo che avevi copiato prima non c'è
più. Quindi prima **1. Copia il testo** e incollalo nel riquadro del post, poi **Copia
l'immagine** e incollala. L'app te lo scrive nella riga della consegna, per la rete che hai
scelto.

**Chi precompila e chi no:**

| Precompilano il testo nell'indirizzo | Aprono solo il sito |
|---|---|
| X · LinkedIn · Threads · Bluesky | **Facebook** · Instagram · Mastodon · Telegram · YouTube |

Per le seconde, il tasto dice *Apri Facebook* e non *Apri il compositore*: un'etichetta che
promette una cosa che non succede è peggio di un'etichetta povera.

**X, in particolare.** L'API di X è a pagamento dal 6 febbraio 2026 (circa 0,015 $ per
post, e **0,20 $ se il testo contiene un link**). L'app è impostata per **non usarla**:
l'interruttore sta in Configurazione ed è spento. Se un giorno cambi idea, i valori
dell'app X si incollano lì accanto e si accende il tasto *Pubblica su X* — ma nessun
costo parte da solo.

Collegare una rete all'API richiede che tu crei una **app sviluppatore** su quella rete e,
per Meta/TikTok/YouTube, che passi una **revisione**. Si fa una rete alla volta, quando
serve davvero.

### Vincoli dell'immagine, che dipendono dalla rete

L'app te li scrive accanto ai problemi dell'anteprima, perché cambiano da rete a rete:

- **Instagram** — l'API pubblica **solo JPEG**: una PNG viene rifiutata. La didascalia si
  ferma a 2.200 caratteri e si pubblicano al massimo 100 post ogni 24 ore.
- **Bluesky** — l'immagine non può superare **1 MB**, al massimo 4 per post.
- **Threads** — immagine fino a 8 MB, JPEG o PNG.
- **Telegram** — con la foto allegata il testo diventa una **didascalia e si ferma a 1.024
  caratteri**; solo senza immagine arriva a 4.096.
- **X** — fino a 4 foto, JPEG/PNG/WEBP/GIF, 5 MB ciascuna; i limiti del **video** dipendono
  dall'account che pubblica (Premium o no), non dal piano API.

## Configurazione

- **Chiave del provider** — obbligatoria per generare. Si imposta nella scheda
  Configurazione; resta in `config.json`, che non finisce mai in git.
- **Provider e modello** — il modello **non si scrive: si sceglie**. Prima il *provider*
  (OpenRouter, OpenAI, Google, Groq, DeepSeek, Mistral, xAI, Together, o un indirizzo tuo),
  poi il modello dal suo catalogo, **raggruppato per editore** e con i **gratuiti segnati**.
  Il campo *Indirizzo del provider* cambia da solo scegliendo il provider: si tocca solo
  per «Altro». Se il catalogo non si legge (chiave assente, provider senza elenco
  pubblico), il campo **torna scrivibile con il motivo accanto** — un menu vuoto
  bloccherebbe, un campo libero no. Un modello salvato che non è più in catalogo resta in
  elenco con la scritta *(non più in elenco)*, così non ti ritrovi selezionato un altro
  modello senza accorgertene.
- **Firecrawl / Brave** — per la lettura arricchita delle fonti.
- **X** — servono il *Client ID* e il *Client Secret* di una app creata su
  [console.x.com](https://console.x.com) con **OAuth 2.0** attivo e questo callback
  registrato esattamente: `http://localhost:8080/callback`. Poi premi **Accedi a X**: si
  apre il browser, e viene autorizzato **l'account con cui sei loggato nel browser** — se
  pubblichi per un altro account, cambia account prima di autorizzare.

Le chiavi non escono mai dall'app: la pagina le riceve sempre vuote e sa solo dirti se
ci sono. Un campo lasciato vuoto in Configurazione vuol dire *non cambiare*.

## Dove stanno le cose

```text
Social/
  backend/            il servizio (sola libreria standard)
    server.py         entry point: py -3.14 backend/server.py
    config.py         lettura, fusione e mascheramento dei segreti
    parametri.py      i parametri della generazione, dichiarati come dati
    generazione.py    OpenRouter: scrive il testo e lo adatta al social
    fonti.py          legge link e video (Firecrawl, Brave, trascrizione)
    immagini.py       carica e genera le immagini
    canali/           un modulo per rete; X pubblica davvero
  ui/                 pagina, stile, logica e questa guida
  xpost/              il motore di pubblicazione su X (usabile anche da riga di comando)
  config.json         chiavi e impostazioni  (non in git)
  data/               allegati, lavoro in corso, registro  (non in git)
  logs/
  avvia_social_studio.bat / ferma_social_studio.bat
```

## Registro

La scheda **Registro** elenca che cosa è uscito davvero, con il collegamento al post.
Si legge dal disco, non da X: serve a rispondere a "cosa ho pubblicato?" anche a
collegamento staccato.

## Problemi frequenti

- **"Manca la chiave di OpenRouter"** — l'app non inventa contenuti: impostala in
  Configurazione e riprova.
- **"Nessuna trascrizione disponibile"** — il video non ha sottotitoli. Incolla il testo
  a mano nell'origine "Un testo da rivisitare".
- **Il login di X non completa** — controlla che il callback registrato sull'app sia
  esattamente `http://localhost:8080/callback` e che la porta 8080 non sia occupata.
- **X dice che mancano le credenziali** — hai salvato il *Client ID*? Il tasto *Accedi a X*
  non parte senza.
- **Il testo sfora il tetto** — accorcialo a mano: l'app non tronca, perché tagliare
  cambia il senso senza dirtelo.
