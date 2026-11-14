# Guida di Social Studio

## Novità di questa versione (0.1.0)

- **Prima versione.** L'app nasce da una richiesta precisa: un solo posto dove partire
  da un testo, da un link o da un video, e da lì adattare titolo e testo a ogni social
  e pubblicare.
- **X/Twitter pubblica davvero**, con l'API ufficiale (OAuth 2.0). Gli altri social
  restano in **consegna manuale**: l'app prepara tutto, la pubblicazione la fai tu.
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
| X / Twitter | **collegato** (API ufficiale) | dal tasto *Pubblica su X* |
| LinkedIn | manuale | *Anteprima* → *Apri il compositore* |
| Facebook | manuale | *Anteprima* → copia il testo |
| Instagram | manuale | serve un'immagine; pubblica dall'app del telefono |
| Threads | manuale | *Anteprima* → *Apri il compositore* |
| Mastodon | manuale | copia il testo nella tua istanza |
| Bluesky | manuale | *Anteprima* → *Apri il compositore* |
| Telegram | manuale | copia il testo nel canale |
| YouTube (post Community) | manuale | non esiste API pubblica per pubblicarlo |

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

- **Chiave OpenRouter** — obbligatoria per generare. Si imposta nella scheda
  Configurazione; resta in `config.json`, che non finisce mai in git.
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
