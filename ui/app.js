"use strict";
/* Social Studio — logica dell'interfaccia.
   Regola che vale in tutto il file: quello che esce e' quello che si legge nella
   pagina. Prima di preparare o pubblicare si legge il DOM, non la copia in memoria. */

const INTESTAZIONE = { "X-Social-Studio": "1" };
const CHIAVE_CORRENTE = "social-studio-corrente";

const stato = {
  origine: "testo",
  fonte: null,
  parametri: {},
  parametriElenco: [],
  titolo: "",
  testo: "",
  canale: null,
  canali: [],
  adattati: {},
  allegati: [],
  preparazione: null,
  xCollegato: false,
  statoCanali: {},
  blog: null,
};

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));

/* ------------------------------------------------------------------ rete */

async function chiedi(percorso, opzioni) {
  const risposta = await fetch(percorso, opzioni || {});
  const testo = await risposta.text();
  let dati = null;
  try { dati = testo ? JSON.parse(testo) : null; } catch (e) { dati = null; }
  if (!risposta.ok) {
    const motivo = (dati && dati.errore) || testo || ("HTTP " + risposta.status);
    throw new Error(motivo);
  }
  return dati;
}

function inviaJson(percorso, corpo) {
  return chiedi(percorso, {
    method: "POST",
    headers: Object.assign({ "Content-Type": "application/json" }, INTESTAZIONE),
    body: JSON.stringify(corpo || {}),
  });
}

/* --------------------------------------------------------------- utilita */

function scappa(t) {
  return String(t == null ? "" : t)
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function avviso(messaggio, male) {
  const scatola = $("#avvisi");
  const nodo = document.createElement("div");
  nodo.className = "avviso" + (male ? " male" : "");
  nodo.textContent = messaggio;
  scatola.appendChild(nodo);
  setTimeout(() => nodo.remove(), 9000);
}

function scrivi(sel, testo, classe) {
  const nodo = $(sel);
  if (!nodo) return;
  nodo.textContent = testo || "";
  nodo.className = "esito-tenue" + (classe ? " " + classe : "");
}

function contatore(testo, limite) {
  const n = (testo || "").length;
  if (!limite) return n + " caratteri";
  const resto = limite - n;
  return n + " / " + limite + " caratteri " + (resto < 0 ? "(" + (-resto) + " oltre il tetto)" : "(" + resto + " liberi)");
}

/* ------------------------------------------------------- finestra unica  */

function apriFinestra(titolo, nodoContenuto) {
  $("#finestra-titolo").textContent = titolo;
  const corpo = $("#finestra-corpo");
  corpo.innerHTML = "";
  corpo.appendChild(nodoContenuto);
  corpo.scrollTop = 0;
  $("#velo").classList.remove("nascosto");
  $("#finestra-chiudi").focus();
}

function chiudiFinestra() {
  $("#velo").classList.add("nascosto");
}

/* ------------------------------------------------ mini markdown (guida)  */

function rendiMarkdown(testo) {
  const contenitore = document.createElement("div");
  const righe = String(testo || "").replace(/\r\n/g, "\n").split("\n");
  let indice = 0;

  function enfasi(s) {
    return scappa(s)
      .replace(/`([^`]+)`/g, "<code>$1</code>")
      .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  }

  while (indice < righe.length) {
    const riga = righe[indice];

    if (riga.trim().startsWith("```")) {
      const linguaggio = riga.trim().slice(3);
      indice += 1;
      const blocco = [];
      while (indice < righe.length && !righe[indice].trim().startsWith("```")) {
        blocco.push(righe[indice]); indice += 1;
      }
      indice += 1;
      const pre = document.createElement("pre");
      const code = document.createElement("code");
      if (linguaggio) code.className = "lingua-" + linguaggio;
      code.textContent = blocco.join("\n");
      pre.appendChild(code);
      contenitore.appendChild(pre);
      continue;
    }

    if (/^\s*\|.*\|\s*$/.test(riga) && indice + 1 < righe.length && /^\s*\|[\s:|-]+\|\s*$/.test(righe[indice + 1])) {
      const tabella = document.createElement("table");
      const celle = (r) => r.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());
      const testa = document.createElement("tr");
      celle(riga).forEach((c) => {
        const th = document.createElement("th");
        th.innerHTML = enfasi(c);
        testa.appendChild(th);
      });
      const thead = document.createElement("thead"); thead.appendChild(testa);
      tabella.appendChild(thead);
      indice += 2;
      const corpo = document.createElement("tbody");
      while (indice < righe.length && /^\s*\|.*\|\s*$/.test(righe[indice])) {
        const tr = document.createElement("tr");
        celle(righe[indice]).forEach((c) => {
          const td = document.createElement("td");
          td.innerHTML = enfasi(c);
          tr.appendChild(td);
        });
        corpo.appendChild(tr);
        indice += 1;
      }
      tabella.appendChild(corpo);
      contenitore.appendChild(tabella);
      continue;
    }

    const titolo = /^(#{1,4})\s+(.*)$/.exec(riga);
    if (titolo) {
      const h = document.createElement("h" + titolo[1].length);
      h.innerHTML = enfasi(titolo[2]);
      contenitore.appendChild(h);
      indice += 1;
      continue;
    }

    if (/^\s*[-*]\s+/.test(riga)) {
      const ul = document.createElement("ul");
      while (indice < righe.length && /^\s*[-*]\s+/.test(righe[indice])) {
        const li = document.createElement("li");
        li.innerHTML = enfasi(righe[indice].replace(/^\s*[-*]\s+/, ""));
        ul.appendChild(li);
        indice += 1;
      }
      contenitore.appendChild(ul);
      continue;
    }

    if (/^\s*\d+\.\s+/.test(riga)) {
      const ol = document.createElement("ol");
      while (indice < righe.length && /^\s*\d+\.\s+/.test(righe[indice])) {
        const li = document.createElement("li");
        li.innerHTML = enfasi(righe[indice].replace(/^\s*\d+\.\s+/, ""));
        ol.appendChild(li);
        indice += 1;
      }
      contenitore.appendChild(ol);
      continue;
    }

    if (riga.trim() === "") { indice += 1; continue; }

    const p = document.createElement("p");
    p.innerHTML = enfasi(riga);
    contenitore.appendChild(p);
    indice += 1;
  }
  return contenitore;
}

/* --------------------------------------------------------------- avvio   */

document.addEventListener("DOMContentLoaded", avvia);

async function avvia() {
  collegaEventi();
  collegaLinguette();
  await caricaStato();
  await caricaParametri();
  await caricaCanali();
  attivaOrigine("testo");
  await riprendiCorrente();
  await aggiornaStatoX();
  disegnaContatoreBase();
  aggiornaTasti();
}

function collegaLinguette() {
  $$(".linguetta").forEach((tasto) => {
    tasto.addEventListener("click", () => apriArea(tasto.dataset.tab));
  });
  window.addEventListener("hashchange", () => apriAreaDallIndirizzo());
  apriAreaDallIndirizzo();
}

function apriArea(nome) {
  $$(".linguetta").forEach((t) => t.classList.toggle("attiva", t.dataset.tab === nome));
  $$(".area").forEach((a) => a.classList.toggle("attiva", a.id === "tab-" + nome));
  if (nome === "registro") caricaRegistro();
  history.replaceState(null, "", "#" + nome);
}

function apriAreaDallIndirizzo() {
  const nome = (location.hash || "#crea").slice(1);
  if (["crea", "config", "registro"].includes(nome)) apriArea(nome);
}

async function caricaStato() {
  try {
    const info = await chiedi("/api/stato");
    const chiavi = info.chiavi || {};
    const pezzi = [];
    pezzi.push(chiavi.openrouter
      ? "<b>OpenRouter</b> pronto · " + scappa(chiavi.modello)
      : "<span class=\"manca\">OpenRouter: chiave assente</span>");
    pezzi.push(chiavi.firecrawl ? "Firecrawl ok" : "<span class=\"manca\">Firecrawl assente</span>");
    pezzi.push(chiavi.brave ? "Brave ok" : "<span class=\"manca\">Brave assente</span>");
    pezzi.push("resta su <b>127.0.0.1:" + info.porta + "</b>");
    $("#riga-stato").innerHTML = pezzi.join(" &nbsp;·&nbsp; ");
  } catch (e) {
    $("#riga-stato").textContent = "servizio non raggiungibile: " + e.message;
  }
}

async function caricaParametri() {
  const dati = await chiedi("/api/parametri");
  stato.parametriElenco = dati.parametri;
  stato.parametri = Object.assign({}, dati.predefiniti);
  disegnaParametri();
}

function disegnaParametri() {
  const scatola = $("#modulo-parametri");
  scatola.innerHTML = "";
  stato.parametriElenco.forEach((p) => {
    const campo = document.createElement("div");
    campo.className = "campo-parametro" + (p.tipo === "testo_lungo" ? " largo" : "");
    const valore = stato.parametri[p.chiave];

    if (p.tipo === "booleana") {
      const etichetta = document.createElement("label");
      etichetta.className = "campo-casella";
      const casella = document.createElement("input");
      casella.type = "checkbox";
      casella.id = "param-" + p.chiave;
      casella.checked = !!valore;
      casella.addEventListener("change", () => { stato.parametri[p.chiave] = casella.checked; });
      const testo = document.createElement("span");
      testo.textContent = p.etichetta;
      etichetta.appendChild(casella); etichetta.appendChild(testo);
      campo.appendChild(etichetta);
      if (p.nota) {
        const nota = document.createElement("div");
        nota.className = "nota"; nota.style.marginLeft = "25px";
        nota.textContent = p.nota;
        campo.appendChild(nota);
      }
    } else {
      const etichetta = document.createElement("label");
      etichetta.className = "etichetta";
      etichetta.setAttribute("for", "param-" + p.chiave);
      etichetta.textContent = p.etichetta;
      campo.appendChild(etichetta);

      let controllo;
      if (p.tipo === "scelta") {
        controllo = document.createElement("select");
        p.valori.forEach((v) => {
          const opzione = document.createElement("option");
          opzione.value = v; opzione.textContent = v;
          if (v === valore) opzione.selected = true;
          controllo.appendChild(opzione);
        });
      } else if (p.tipo === "numero") {
        controllo = document.createElement("input");
        controllo.type = "number";
        controllo.min = p.min; controllo.max = p.max; controllo.step = p.passo || 1;
        controllo.value = valore;
      } else if (p.tipo === "testo_lungo") {
        controllo = document.createElement("textarea");
        controllo.rows = 3;
        controllo.value = valore || "";
      } else {
        controllo = document.createElement("input");
        controllo.type = "text";
        controllo.value = valore || "";
      }
      controllo.id = "param-" + p.chiave;
      controllo.addEventListener("change", () => {
        stato.parametri[p.chiave] = (p.tipo === "numero") ? Number(controllo.value) : controllo.value;
      });
      controllo.addEventListener("input", () => {
        if (p.tipo === "testo_lungo" || p.tipo === "text") stato.parametri[p.chiave] = controllo.value;
      });
      campo.appendChild(controllo);
      if (p.nota) {
        const nota = document.createElement("div");
        nota.className = "nota"; nota.textContent = p.nota;
        campo.appendChild(nota);
      }
    }
    scatola.appendChild(campo);
  });
}

function leggiModulo() {
  const valori = {};
  stato.parametriElenco.forEach((p) => {
    const nodo = $("#param-" + p.chiave);
    if (!nodo) { valori[p.chiave] = stato.parametri[p.chiave]; return; }
    if (p.tipo === "booleana") valori[p.chiave] = nodo.checked;
    else if (p.tipo === "numero") valori[p.chiave] = Number(nodo.value);
    else valori[p.chiave] = nodo.value;
  });
  return valori;
}

async function caricaCanali() {
  const dati = await chiedi("/api/canali");
  stato.canali = dati.canali;
  const griglia = $("#griglia-canali");
  griglia.innerHTML = "";
  stato.canali.forEach((c) => {
    const tasto = document.createElement("button");
    tasto.type = "button";
    tasto.className = "canale";
    tasto.dataset.canale = c.chiave;
    tasto.innerHTML = scappa(c.etichetta) +
      "<span class=\"pallino\">" + c.limite + " car." + (c.collegato ? " · collegato" : "") + "</span>";
    tasto.title = c.fonte_limite;
    tasto.addEventListener("click", () => scegliCanale(c.chiave));
    griglia.appendChild(tasto);
  });
}

function scegliCanale(chiave) {
  // Prima di cambiare canale si salva quello che l'utente ha scritto a mano:
  // altrimenti bastava guardare un'altra rete per perdere le correzioni.
  if (stato.canale && stato.canale !== chiave) {
    const t = $("#adattato-testo").value;
    const g = $("#adattato-titolo").value;
    if (t || g) stato.adattati[stato.canale] = { titolo: g, testo: t };
  }
  stato.canale = chiave;
  $$(".canale").forEach((b) => b.classList.toggle("attivo", b.dataset.canale === chiave));
  const c = stato.canali.find((x) => x.chiave === chiave);
  $("#blocco-adattato").classList.remove("nascosto");
  $("#adattato-nome").textContent = c.etichetta;
  const salvato = stato.adattati[chiave];
  $("#adattato-titolo").value = salvato ? salvato.titolo : "";
  $("#adattato-testo").value = salvato ? salvato.testo : "";
  $("#tasto-adatta").textContent = salvato ? "Riadatta a questo social" : "Adatta a questo social";
  disegnaContatoreAdattato();
  stato.preparazione = null;
  aggiornaTasti();
  aggiornaStatoCanale(chiave);

  // Il pannello dell'articolo compare solo se la destinazione e' un blog: per i social
  // resta nascosto, e con lui i pezzi che solo un articolo ha.
  const blog = canaleBlog();
  $("#pannello-blog").classList.toggle("nascosto", !blog);
  $("#blog-esito-bozza").classList.add("nascosto");
  if (blog) caricaBlogStato();
}

/* Lo stato del collegamento e' del canale scelto, non di X: prima si leggeva
   "collegato a X" per qualunque rete, e con Telegram e Mastodon attivi il tasto
   di invio restava spento per colpa di un altro canale. */
async function aggiornaStatoCanale(chiave) {
  const c = stato.canali.find((x) => x.chiave === chiave);
  if (!c || !c.collegato) {
    stato.statoCanali[chiave] = { collegato: false, manuale: true };
    aggiornaTasti();
    return;
  }
  try {
    const controllo = new AbortController();
    const scadenza = setTimeout(() => controllo.abort(), 20000);
    stato.statoCanali[chiave] = await chiedi("/api/canale/" + chiave + "/stato",
                                             { signal: controllo.signal });
    clearTimeout(scadenza);
  } catch (e) {
    // La sonda e' un di piu': se non risponde, si dice e basta, in parole comprensibili.
    // Il tasto resta com'e', perche' non dipende da lei.
    stato.statoCanali[chiave] = {
      sondaFallita: true,
      motivo: "non sono riuscito a leggere su quale account scrivere: la rete non ha risposto in tempo. Si puo' pubblicare lo stesso.",
    };
  }
  aggiornaTasti();
}

/* ---------------------------------------------------------------- origine */

function collegaEventi() {
  document.querySelectorAll(".segmento").forEach((b) => {
    b.addEventListener("click", () => attivaOrigine(b.dataset.origine));
  });
  $("#tasto-leggi").addEventListener("click", leggiLink);
  $("#tasto-leggi-video").addEventListener("click", leggiVideo);
  $("#tasto-predefiniti").addEventListener("click", ripristinaPredefiniti);
  $("#tasto-genera").addEventListener("click", genera);
  $("#tasto-adatta").addEventListener("click", adatta);
  $("#tasto-genera-immagine").addEventListener("click", generaImmagine);
  $("#tasto-togli-immagine").addEventListener("click", togliImmagine);
  $("#tasto-copia-testo").addEventListener("click", (e) => copiaTestoPost(e.currentTarget));
  $("#tasto-copia-immagine-2").addEventListener("click", (e) =>
    immagineSulSistema("/api/allegato/copia").then((fatto) => {
      if (fatto) {
        const prima = e.currentTarget.textContent;
        e.currentTarget.textContent = "Copiata";
        setTimeout(() => { e.currentTarget.textContent = prima; }, 1500);
      }
    }));
  $("#tasto-copia-immagine").addEventListener("click", () => immagineSulSistema("/api/allegato/copia"));
  $("#tasto-cartella-immagine").addEventListener("click", () => immagineSulSistema("/api/allegato/cartella"));
  $("#file-immagine").addEventListener("change", caricaImmagine);
  $("#tasto-prepara").addEventListener("click", prepara);
  $("#tasto-invia").addEventListener("click", invia);
  $("#tasto-apri").addEventListener("click", apriCompositore);
  $("#tasto-guida").addEventListener("click", apriGuida);
  $("#finestra-chiudi").addEventListener("click", chiudiFinestra);
  $("#finestra-chiudi-2").addEventListener("click", chiudiFinestra);
  $("#tasto-genera-articolo").addEventListener("click", blogGeneraArticolo);
  $("#blog-genera-faq").addEventListener("click", blogGeneraFaq);
  $("#blog-aggiorna-anteprima").addEventListener("click", aggiornaAnteprimaFaq);
  $("#blog-genera-seo").addEventListener("click", blogGeneraSeo);
  $("#blog-aggiungi-immagine").addEventListener("click", blogAggiungiImmagine);
  $("#blog-seo-title").addEventListener("input", disegnaContatoriSeo);
  $("#blog-seo-description").addEventListener("input", disegnaContatoriSeo);
  $("#blog-gancio").addEventListener("input", programmaSalvataggio);
  $("#blog-sintesi").addEventListener("input", programmaSalvataggio);
  $("#velo").addEventListener("click", (e) => { if (e.target.id === "velo") chiudiFinestra(); });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") chiudiFinestra(); });
  $$("[data-copia]").forEach((b) => {
    b.addEventListener("click", () => copiaCampo(b.dataset.copia, b));
  });
  $("#campo-testo").addEventListener("input", () => { disegnaContatoreBase(); programmaSalvataggio(); });
  $("#campo-titolo").addEventListener("input", programmaSalvataggio);
  $("#adattato-testo").addEventListener("input", () => { disegnaContatoreAdattato(); programmaSalvataggio(); });
  $("#adattato-titolo").addEventListener("input", programmaSalvataggio);
  $("#tasto-salva-llm").addEventListener("click", salvaConfigLlm);
  $("#tasto-salva-x").addEventListener("click", salvaConfigX);
  $("#tasto-salva-firma").addEventListener("click", salvaConfigFirma);
  $("#tasto-login-x").addEventListener("click", loginX);
  $("#tasto-aggiorna-registro").addEventListener("click", caricaRegistro);
}

function attivaOrigine(nome) {
  stato.origine = nome;
  $$(".segmento").forEach((b) => b.classList.toggle("attivo", b.dataset.origine === nome));
  $("#blocco-testo").classList.toggle("nascosto", nome !== "testo");
  $("#blocco-link").classList.toggle("nascosto", nome !== "link");
  $("#blocco-video").classList.toggle("nascosto", nome !== "video");
  const spiegazioni = {
    testo: "Incolla il testo che vuoi riscrivere con lo stile che scegli sotto.",
    link: "L'app legge la pagina e ne ricava il testo. Con Firecrawl se la chiave e' impostata, altrimenti legge la pagina direttamente.",
    video: "Il testo viene dalla trascrizione automatica del video, poi riscritto con lo stile scelto.",
  };
  $("#origine-spiegazione").textContent = spiegazioni[nome];
}

async function leggiLink() {
  const url = $("#ingresso-link").value.trim();
  if (!url) { scrivi("#esito-lettura", "Serve un indirizzo.", "male"); return; }
  scrivi("#esito-lettura", "Sto leggendo la pagina…");
  try {
    const esito = await inviaJson("/api/fonte", {
      tipo: "link", url: url, ricerca_web: leggiModulo().ricerca_web,
    });
    if (!esito.ok) { scrivi("#esito-lettura", esito.motivo, "male"); return; }
    stato.fonte = esito.fonte;
    stato.titolo = esito.fonte.titolo || "";
    stato.testo = "";
    $("#campo-titolo").value = stato.titolo;
    $("#ingresso-testo").value = esito.fonte.testo;
    scrivi("#esito-lettura", "Letta con: " + esito.fonte.via + " · " + esito.fonte.testo.length + " caratteri.", "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-lettura", "Lettura non riuscita: " + e.message, "male");
  }
}

async function leggiVideo() {
  const url = $("#ingresso-video").value.trim();
  if (!url) { scrivi("#esito-lettura-video", "Serve un indirizzo.", "male"); return; }
  scrivi("#esito-lettura-video", "Sto leggendo il video e la sua trascrizione…");
  try {
    const esito = await inviaJson("/api/fonte", {
      tipo: "video", url: url, ricerca_web: leggiModulo().ricerca_web,
    });
    if (!esito.ok) { scrivi("#esito-lettura-video", esito.motivo, "male"); return; }
    stato.fonte = esito.fonte;
    stato.titolo = esito.fonte.titolo || "";
    $("#campo-titolo").value = stato.titolo;
    $("#ingresso-testo").value = esito.fonte.testo;
    scrivi("#esito-lettura-video",
      "Trascrizione con: " + esito.fonte.via + " · " + esito.fonte.testo.length + " caratteri.", "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-lettura-video", "Lettura non riuscita: " + e.message, "male");
  }
}

function ripristinaPredefiniti() {
  chiedi("/api/parametri").then((dati) => {
    stato.parametri = Object.assign({}, dati.predefiniti);
    disegnaParametri();
    avviso("Parametri riportati ai valori predefiniti.");
  });
}

/* ------------------------------------------------------------ generazione */

function prontoPerGenerare() {
  const parametri = leggiModulo();
  if (stato.origine === "testo") {
    const testo = $("#ingresso-testo").value.trim();
    if (testo.length < 40) return "Incolla un testo di almeno qualche riga.";
    stato.fonte = { tipo: "testo", titolo: $("#campo-titolo").value.trim(), testo: testo, via: "incollato" };
  } else if (!stato.fonte || stato.fonte.tipo === "testo") {
    return "Prima leggi la fonte (link o video): senza contenuto l'app non inventa niente.";
  }
  return "";
}

async function genera() {
  const problema = prontoPerGenerare();
  if (problema) { scrivi("#esito-genera", problema, "male"); return; }
  scrivi("#esito-genera", "Sto scrivendo…");
  $("#tasto-genera").disabled = true;
  try {
    const esito = await inviaJson("/api/genera", {
      fonte: stato.fonte, parametri: leggiModulo(),
    });
    if (!esito.ok) { scrivi("#esito-genera", esito.motivo, "male"); return; }
    stato.titolo = esito.titolo;
    stato.testo = esito.testo;
    stato.adattati = {};
    $("#campo-titolo").value = esito.titolo;
    $("#campo-testo").value = esito.testo;
    $("#imm-titolo").value = esito.titolo;
    disegnaContatoreBase();
    if (stato.canale) scegliCanale(stato.canale);
    scrivi("#esito-genera", "Fatto: " + esito.testo.length + " caratteri. Controlla e correggi prima di adattare.", "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-genera", "Generazione non riuscita: " + e.message, "male");
  } finally {
    $("#tasto-genera").disabled = false;
    aggiornaTasti();
  }
}

async function adatta() {
  if (!stato.canale) { scrivi("#esito-adatta", "Scegli prima un social.", "male"); return; }
  const testo = $("#campo-testo").value.trim();
  if (!testo) { scrivi("#esito-adatta", "Non c'e' ancora un testo da adattare.", "male"); return; }
  scrivi("#esito-adatta", "Sto adattando…");
  $("#tasto-adatta").disabled = true;
  try {
    const esito = await inviaJson("/api/adatta", {
      canale: stato.canale, titolo: $("#campo-titolo").value, testo: testo, parametri: leggiModulo(),
    });
    if (!esito.ok) { scrivi("#esito-adatta", esito.motivo, "male"); return; }
    $("#adattato-titolo").value = esito.titolo;
    $("#adattato-testo").value = esito.testo;
    stato.adattati[stato.canale] = { titolo: esito.titolo, testo: esito.testo };
    disegnaContatoreAdattato();
    const m = esito.misure;
    scrivi("#esito-adatta", m.entro
      ? "Fatto: " + m.caratteri + " caratteri, dentro il tetto."
      : "Fatto, ma il modello ha sforato: " + m.caratteri + " su " + m.limite + ". Accorcia a mano.", m.entro ? "ok" : "male");
    stato.preparazione = null;
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-adatta", "Adattamento non riuscito: " + e.message, "male");
  } finally {
    $("#tasto-adatta").disabled = false;
    aggiornaTasti();
  }
}

/* ---------------------------------------------------------------- immagini */

async function caricaImmagine() {
  const file = $("#file-immagine").files[0];
  if (!file) return;
  const dati = new FormData();
  dati.append("media", file, file.name);
  try {
    const risposta = await fetch("/api/immagine/carica", { method: "POST", headers: INTESTAZIONE, body: dati });
    const esito = await risposta.json();
    if (!esito.ok) { scrivi("#esito-immagine", esito.motivo, "male"); return; }
    stato.allegati = [esito];
    mostraImmagine();
    scrivi("#esito-immagine", "Caricata: " + esito.nome + " (" + esito.larghezza + "x" + esito.altezza + ")", "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-immagine", "Caricamento non riuscito: " + e.message, "male");
  }
}

async function generaImmagine() {
  try {
    const esito = await inviaJson("/api/immagine/genera", {
      titolo: $("#imm-titolo").value || $("#campo-titolo").value,
      sottotitolo: $("#imm-sottotitolo").value,
      formato: $("#imm-formato").value,
    });
    if (!esito.ok) { scrivi("#esito-immagine", esito.motivo, "male"); return; }
    stato.allegati = [esito];
    mostraImmagine();
    scrivi("#esito-immagine", "Generata: " + esito.larghezza + "x" + esito.altezza + " · " + esito.via, "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#esito-immagine", "Generazione non riuscita: " + e.message, "male");
  }
}

function mostraImmagine() {
  const corrente = stato.allegati[0];
  const nodo = $("#immagine-corrente");
  if (corrente) {
    nodo.src = "/api/allegati/" + encodeURIComponent(corrente.nome) + "?t=" + Date.now();
    nodo.classList.remove("nascosto");
  } else {
    nodo.classList.add("nascosto");
    nodo.removeAttribute("src");
  }
  $("#tasto-togli-immagine").disabled = !corrente;
  $("#tasto-copia-immagine").disabled = !corrente;
  $("#tasto-cartella-immagine").disabled = !corrente;
}

/* Porta l'immagine a portata di mano: negli appunti (Ctrl+V nel compositore) o
   nella cartella aperta con il file selezionato. Serve al flusso manuale, perche'
   l'indirizzo del compositore non porta con se' le immagini. */
async function immagineSulSistema(rotta) {
  const corrente = stato.allegati[0];
  if (!corrente) {
    scrivi("#esito-immagine", "Nessuna immagine da usare.", "male");
    return false;
  }
  try {
    const esito = await inviaJson(rotta, { percorso: corrente.percorso });
    scrivi("#esito-immagine", esito.ok ? esito.messaggio : esito.motivo, esito.ok ? "ok" : "male");
    return !!esito.ok;
  } catch (e) {
    scrivi("#esito-immagine", "Non riuscito: " + e.message, "male");
    return false;
  }
}

function togliImmagine() {
  stato.allegati = [];
  $("#file-immagine").value = "";
  mostraImmagine();
  scrivi("#esito-immagine", "Nessuna immagine allegata.");
  stato.preparazione = null;
  aggiornaTasti();
  programmaSalvataggio();
}

/* --------------------------------------------------- due tempi: prepara/invia */

function testoDelPost() {
  if (stato.canale) {
    const dalCampo = $("#adattato-testo").value.trim();
    if (dalCampo) return dalCampo;
  }
  return $("#campo-testo").value.trim();
}

function titoloDelPost() {
  if (stato.canale) {
    const dalCampo = $("#adattato-titolo").value.trim();
    if (dalCampo) return dalCampo;
  }
  return $("#campo-titolo").value.trim();
}

function pacchetto() {
  const corpo = {
    canale: stato.canale,
    titolo: titoloDelPost(),
    testo: testoDelPost(),
    allegati: stato.allegati.map((a) => a.percorso),
  };
  if (canaleBlog()) {
    const b = statoBlog();
    Object.assign(corpo, {
      gancio: $("#blog-gancio").value.trim(),
      sintesi: $("#blog-sintesi").value.trim(),
      slug: $("#blog-slug").value.trim(),
      focus_keyword: $("#blog-focus-keyword").value.trim(),
      seo_title: $("#blog-seo-title").value.trim(),
      seo_description: $("#blog-seo-description").value.trim(),
      intro_faq: b.intro_faq,
      faq: b.faq,
      categorie: Array.from($("#blog-categorie").selectedOptions).map((o) => Number(o.value)),
      immagini_corpo: b.immagini_corpo.map((x) => x.percorso),
      alt_immagini: b.immagini_corpo.map((x) => ({ file: x.percorso, alt: x.alt || "" })),
    });
  }
  return corpo;
}

async function prepara() {
  if (!stato.canale) { scrivi("#esito-invio", "Scegli un social.", "male"); return; }
  const corpo = pacchetto();
  if (!corpo.testo) { scrivi("#esito-invio", "Non c'e' testo da inviare.", "male"); return; }
  scrivi("#esito-invio", "Sto preparando l'anteprima…");
  try {
    const esito = await inviaJson("/api/prepara", corpo);
    stato.preparazione = esito.preparazione;
    disegnaAnteprima(esito.preparazione);
    scrivi("#esito-invio", "Anteprima pronta. Non e' stato pubblicato niente.", "ok");
  } catch (e) {
    scrivi("#esito-invio", "Anteprima non riuscita: " + e.message, "male");
  }
  aggiornaTasti();
}

function disegnaAnteprima(p) {
  const scatola = $("#anteprima-esito");
  scatola.innerHTML = "";
  scatola.classList.remove("nascosto");
  const bloccanti = (p.problemi || []).filter((x) => x.bloccante);
  scatola.classList.toggle("ok-anteprima", bloccanti.length === 0);

  const titolo = document.createElement("h4");
  titolo.textContent = p.tipo === "blog" ? "Che cosa verrebbe depositato" : "Che cosa uscirebbe";
  scatola.appendChild(titolo);

  // Il blog non e' un social: le righe utili sono altre. «A nome di» e «costo» non
  // dicono niente per un articolo, mentre contano i paragrafi, le sezioni, le FAQ e
  // se i due campi SEO stanno dentro i loro tetti (60 e 160).
  const m = p.misure || {};
  let righe;
  if (p.tipo === "blog") {
    const seo_t = (m.seo_title || {}).caratteri || 0;
    const seo_d = (m.seo_description || {}).caratteri || 0;
    const faq = p.faq || 0;
    righe = [
      ["Destinazione", p.etichetta + " (WordPress)"],
      ["Cosa succede", "si deposita una BOZZA: non esce niente in pubblico"],
      ["Titolo", p.titolo || "(nessuno)"],
      ["Corpo", (p.paragrafi || 0) + " paragrafi \u00b7 " + ((p.sezioni || []).length) + " sezioni"],
      ["FAQ", faq ? (faq + " domande, a scomparsa") : "nessuna: la sezione non verra' creata"],
      ["SEO title", seo_t + " / 60 caratteri" + (seo_t > 60 ? " \u2014 oltre il tetto" : "")],
      ["Meta description", seo_d + " / 160 caratteri" + (seo_d > 160 ? " \u2014 oltre il tetto" : "")],
      ["Copertina", (p.copertina && p.copertina.length) ? p.copertina.join(", ") : "nessuna"],
      ["Immagini nel corpo", (p.immagini_corpo && p.immagini_corpo.length)
        ? p.immagini_corpo.join(", ") : "nessuna"],
      ["Categorie", (p.categorie && p.categorie.length) ? p.categorie.join(", ") : "nessuna"],
    ];
  } else {
    righe = [
      ["Social", p.etichetta],
      ["A nome di", p.a_nome_di || (p.collegato ? "account non collegato" : "consegna manuale")],
      ["Titolo", p.titolo || "(nessuno)"],
      ["Misure", m.caratteri + " / " + m.limite + " caratteri" +
        (m.entro ? "" : " \u2014 oltre il tetto di " + (m.caratteri - m.limite))],
      ["Allegati", (p.allegati && p.allegati.length) ? p.allegati.join(", ") : "nessuno"],
    ];
    if (p.costo_stimato_usd != null) {
      righe.push(["Costo stimato", "~" + p.costo_stimato_usd.toFixed(3) + " USD"]);
    }
  }
  righe.forEach(([k, v]) => {
    const r = document.createElement("p");
    r.className = "riga";
    r.innerHTML = "<b>" + scappa(k) + ":</b> " + scappa(v);
    scatola.appendChild(r);
  });

  const anteprima = document.createElement("div");
  anteprima.className = "blocco-testo-anteprima";
  anteprima.textContent = p.testo;
  scatola.appendChild(anteprima);

  if (p.problemi && p.problemi.length) {
    const t = document.createElement("h4");
    t.textContent = "Problemi";
    scatola.appendChild(t);
    const ul = document.createElement("ul");
    ul.className = "elencoproblemi";
    p.problemi.forEach((x) => {
      const li = document.createElement("li");
      li.textContent = (x.bloccante ? "da risolvere — " : "avviso — ") + x.testo;
      li.style.color = x.bloccante ? "" : "var(--grigio-chiaro)";
      ul.appendChild(li);
    });
    scatola.appendChild(ul);
  }
}

async function invia() {
  if (!stato.canale) return;
  const corpo = pacchetto();
  const nome = (stato.canali.find((c) => c.chiave === stato.canale) || {}).etichetta || stato.canale;
  const blog = canaleBlog();

  // Il blog non pubblica: deposita una bozza. La domanda da fare e' un'altra, e va
  // detta: chi legge "Pubblica" e si trova una bozza non ha capito, chi legge "bozza"
  // e si trova online ha perso qualcosa.
  let domanda;
  if (blog) {
    const righe = corpo.testo.split("\n").map((r) => r.trim()).filter(Boolean);
    const sezioni = righe.filter((r) => r.startsWith("## ")).length;
    domanda = "Creo la BOZZA su " + nome + "?\n\n" +
      "Il sito non pubblica niente: la bozza resta da rivedere e la pubblichi tu da wp-admin.\n\n" +
      "\u2022 Titolo: " + (corpo.titolo || "(nessuno)") + "\n" +
      "\u2022 Corpo: " + (righe.length - sezioni) + " paragrafi, " + sezioni + " sezioni\n" +
      "\u2022 FAQ: " + corpo.faq.length + " domande\n" +
      "\u2022 Copertina: " + (corpo.allegati.length ? "si'" : "no") +
      " \u00b7 immagini nel corpo: " + corpo.immagini_corpo.length;
  } else {
    domanda = "Pubblico davvero su " + nome + "?\n\n" + corpo.testo.slice(0, 400) +
      (corpo.testo.length > 400 ? "\u2026" : "") +
      "\n\n(allegati: " + (corpo.allegati.length || "nessuno") + ")";
  }
  const conferma = window.confirm(domanda);
  if (!conferma) { scrivi("#esito-invio", "Annullato: non e' stato pubblicato niente."); return; }

  scrivi("#esito-invio", blog ? "Sto componendo e depositando la bozza\u2026" : "Sto pubblicando\u2026");
  $("#tasto-invia").disabled = true;
  try {
    const risposta = await inviaJson("/api/invia", corpo);
    const e = risposta.esito || {};
    if (e.pubblicato && e.bozza) {
      scrivi("#esito-invio", "Bozza creata: ID " + e.id, "ok");
      mostraBozza(e);
      caricaRegistro();
    } else if (e.pubblicato) {
      scrivi("#esito-invio", "Pubblicato: " + e.permalink, "ok");
      avviso("Pubblicato su " + nome + ": " + e.permalink);
      caricaRegistro();
    } else if (e.manuale) {
      scrivi("#esito-invio", e.motivo, "male");
      if (e.url_compositore) window.open(e.url_compositore, "_blank");
    } else {
      scrivi("#esito-invio", e.motivo || "Pubblicazione non riuscita.", "male");
    }
  } catch (e) {
    scrivi("#esito-invio", "Pubblicazione non riuscita: " + e.message, "male");
  } finally {
    aggiornaTasti();
  }
}

function apriCompositore() {
  if (!stato.preparazione || !stato.preparazione.url_compositore) return;
  window.open(stato.preparazione.url_compositore, "_blank");
  const ha_immagine = stato.allegati.length > 0;
  scrivi("#esito-invio", ha_immagine
    ? "Compositore aperto col testo dentro. Per l'immagine: premi Copia l'immagine e incolla con Ctrl+V."
    : "Compositore aperto col testo dentro.", "ok");
}

/* Copia il post che uscirebbe ADESSO, letto dal campo: non una copia in memoria. */
async function copiaTestoPost(tasto) {
  const testo = testoDelPost();
  if (!testo) { avviso("Non c'e' ancora un testo da copiare.", true); return; }
  try {
    await navigator.clipboard.writeText(testo);
    const prima = tasto.textContent;
    tasto.textContent = "Copiato";
    setTimeout(() => { tasto.textContent = prima; }, 1500);
    scrivi("#esito-invio", "Testo negli appunti: incollalo nel riquadro del post.", "ok");
  } catch (e) {
    avviso("Non riesco a copiare da solo: seleziona il testo nel campo e usa Ctrl+C.", true);
  }
}

async function copiaCampo(id, tasto) {
  const nodo = $("#" + id);
  if (!nodo) return;
  const testo = nodo.value;
  try {
    await navigator.clipboard.writeText(testo);
    const prima = tasto.textContent;
    tasto.textContent = "Copiato";
    setTimeout(() => { tasto.textContent = prima; }, 1500);
  } catch (e) {
    nodo.select();
    avviso("Non riesco a copiare da solo: il testo e' selezionato, copia con Ctrl+C.", true);
  }
}

/* ------------------------------------------------------------- contatori  */

function disegnaContatoreBase() {
  const nodo = $("#contatore-base");
  const n = $("#campo-testo").value.length;
  nodo.textContent = n + " caratteri";
  nodo.classList.remove("oltre");
}

function disegnaContatoreAdattato() {
  const c = stato.canali.find((x) => x.chiave === stato.canale);
  if (!c) return;
  const nodo = $("#adattato-contatore");
  const n = $("#adattato-testo").value.length;
  nodo.textContent = contatore($("#adattato-testo").value, c.limite);
  nodo.classList.toggle("oltre", n > c.limite);
}

/* --------------------------------------------------------------- tasti   */

function aggiornaTasti() {
  const c = stato.canali.find((x) => x.chiave === stato.canale);
  const c_e = !!c;
  const s = stato.statoCanali[stato.canale] || {};
  // `pronto` e' un fatto locale (client + credenziali presenti), non una sonda di
  // rete: la sonda serve solo a mostrare su quale account si scrive.
  const collegato = !!(c_e && c.pronto);

  const blog = canaleBlog();
  $("#tasto-prepara").disabled = !c_e;
  $("#tasto-invia").disabled = !collegato;
  // Per il blog il tasto non "pubblica": deposita una bozza. Chiamarlo "Pubblica"
  // sarebbe la bugia peggiore di tutta l'interfaccia.
  $("#tasto-invia").textContent = collegato
    ? (blog ? "Deposita la bozza su " + c.etichetta : "Pubblica su " + c.etichetta)
    : (blog ? "Deposita la bozza" : "Pubblica");
  $("#tasto-apri").disabled = !c_e || !(stato.preparazione && stato.preparazione.url_compositore);
  $("#tasto-copia-testo").disabled = !c_e || !!blog;
  $("#tasto-copia-immagine-2").disabled = !c_e || !!blog || !stato.allegati.length;
  // Un tasto che dice "Apri il compositore" quando apre solo il sito e' una bugia:
  // l'etichetta segue cio' che l'indirizzo porta davvero.
  $("#tasto-apri").textContent = c_e
    ? (c.testo_nel_collegamento ? "Apri il compositore" : "Apri " + c.etichetta)
    : "Apri";
  $("#nota-consegna").textContent = (c_e && c.nota_consegna) ? c.nota_consegna : "";

  const motivi = [];
  if (!c_e) {
    motivi.push("scegli un social nel punto 4 per preparare o pubblicare");
  } else if (!c.pronto) {
    motivi.push(c.motivo_pronto || (c.etichetta + " non e' pronto a pubblicare"));
  } else if (s.sondaFallita) {
    motivi.push(s.motivo);
  } else if (s.motivo) {
    motivi.push("attenzione: " + s.motivo);
  }
  if (collegato && s.account) motivi.unshift("scrive su " + s.account);
  motivi.push("pubblica solo quello che leggi nel campo Post");
  // Nota permanente, su un elemento suo: prima scriveva sullo stesso posto del
  // messaggio dell'operazione, e dopo la prima volta non si aggiornava piu'.
  $("#nota-invio").textContent = "Nota: " + motivi.join(" · ");
}

/* ------------------------------------------------------ configurazione   */

async function caricaConfig() {
  const conf = await chiedi("/api/config");
  const llm = conf.llm || {};
  const ricerca = conf.ricerca || {};
  const segreti = conf._segreti_presenti || {};
  CONFIG_LLM = llm;

  const modulo = $("#modulo-llm");
  modulo.innerHTML = "";
  modulo.appendChild(campo("Chiave del provider", "conf-orKey", "password", "",
    segreti["llm.orKey"] ? "presente: lascia vuoto per non cambiarla" : "assente"));

  // Il provider viene prima del modello: e' lui che decide quali modelli esistono.
  modulo.appendChild(scatolaEtichettata("conf-provider", "Provider", "conf-provider-nota", ""));
  modulo.appendChild(scatolaEtichettata("conf-orModel", "Modello",
    "conf-orModel-nota", "quello che scrive i testi"));
  modulo.appendChild(scatolaEtichettata("conf-orModelAdatta", "Modello per l'adattamento",
    "conf-orModelAdatta-nota", "facoltativo: se resta vuoto si usa il modello sopra"));
  modulo.appendChild(campo("Indirizzo del provider", "conf-orUrl", "text", llm.orUrl || "",
    "cambia da solo scegliendo il provider: si tocca solo per «Altro»"));

  modulo.appendChild(campo("Chiave Firecrawl", "conf-firecrawlKey", "password",
    "", segreti["ricerca.firecrawlKey"] ? "presente" : "assente"));
  modulo.appendChild(campo("Chiave Brave", "conf-braveKey", "password",
    "", segreti["ricerca.braveKey"] ? "presente" : "assente"));

  $("#modulo-x").innerHTML = "";
  $("#modulo-x").appendChild(campo("Client ID dell'app X", "conf-x-client_id", "text", (conf.canali.x || {}).client_id || ""));
  $("#modulo-x").appendChild(campo("Client Secret", "conf-x-client_secret", "password",
    "", segreti["canali.x.client_secret"] ? "presente: lascia vuoto per non cambiarlo" : "assente"));
  $("#conf-x-api").checked = ((conf.canali.x || {}).modalita || "compositore") !== "compositore";

  $("#modulo-firma").innerHTML = "";
  $("#modulo-firma").appendChild(campo("Firma in coda ai post (facoltativa)", "conf-firma", "text",
    (conf.pubblicazione || {}).firma || ""));
  $("#modulo-firma").appendChild(campo("Lingua predefinita", "conf-lingua", "text",
    (conf.pubblicazione || {}).lingua || "it"));

  await riempiProvider();
  await riempiModelli();
}

/* ------------------------------------------------------------ i modelli ---
   Il modello non si scrive: si sceglie. L'elenco dipende dal provider, e il
   provider e' l'indirizzo salvato. Se l'elenco non arriva (provider senza
   catalogo pubblico, chiave assente, rete giu') si torna al campo scrivibile:
   un menu vuoto bloccherebbe l'utente, un campo libero no. */

let CONFIG_LLM = {};

function scatolaEtichettata(id, etichetta, idNota, nota) {
  const scatola = document.createElement("div");
  scatola.className = "campo-parametro";
  const lab = document.createElement("label");
  lab.className = "etichetta";
  lab.setAttribute("for", id);
  lab.textContent = etichetta;
  const posto = document.createElement("div");
  posto.id = id + "-posto";
  scatola.appendChild(lab);
  scatola.appendChild(posto);
  const n = document.createElement("div");
  n.className = "nota";
  n.id = idNota;
  n.textContent = nota || "";
  scatola.appendChild(n);
  return scatola;
}

function mettiScelta(id, voci, selezionato, vuoto) {
  const posto = $("#" + id + "-posto");
  posto.innerHTML = "";
  const sel = document.createElement("select");
  sel.id = id;
  if (vuoto) sel.appendChild(new Option(vuoto, ""));
  const gruppi = {};
  voci.forEach((v) => {
    const opzione = new Option(v.etichetta, v.valore);
    if (v.gruppo) {
      if (!gruppi[v.gruppo]) {
        gruppi[v.gruppo] = document.createElement("optgroup");
        gruppi[v.gruppo].label = v.gruppo;
        sel.appendChild(gruppi[v.gruppo]);
      }
      gruppi[v.gruppo].appendChild(opzione);
    } else {
      sel.appendChild(opzione);
    }
  });
  // Un modello salvato che non e' piu' in elenco non deve sparire in silenzio:
  // si aggiunge come voce, dicendolo. Altrimenti si salverebbe un'altra cosa.
  if (selezionato && !Array.from(sel.options).some((o) => o.value === selezionato)) {
    sel.appendChild(new Option(selezionato + "  (non piu' in elenco)", selezionato));
  }
  sel.value = selezionato || "";
  posto.appendChild(sel);
  return sel;
}

function mettiTesto(id, valore) {
  const posto = $("#" + id + "-posto");
  posto.innerHTML = "";
  const inp = document.createElement("input");
  inp.type = "text";
  inp.id = id;
  inp.value = valore || "";
  posto.appendChild(inp);
  return inp;
}

async function riempiProvider() {
  try {
    const esito = await chiedi("/api/providers");
    const sel = mettiScelta("conf-provider",
      (esito.provider || []).map((p) => ({ valore: p.id, etichetta: p.nome })),
      esito.attuale || "openrouter", "");
    const scelto = (esito.provider || []).find((p) => p.id === sel.value) || {};
    $("#conf-provider-nota").textContent = scelto.nota || "";
    sel.addEventListener("change", async () => {
      const p = (esito.provider || []).find((x) => x.id === sel.value) || {};
      $("#conf-provider-nota").textContent = p.nota || "";
      if (p.url) $("#conf-orUrl").value = p.url;          // l'indirizzo segue il provider
      await riempiModelli();
    });
  } catch (e) {
    scrivi("#esito-llm", "Non riesco a leggere i provider: " + e.message, "male");
  }
}

async function riempiModelli(forza) {
  const provider = valoreDi("conf-provider") || "openrouter";
  const dove = $("#conf-orModel-nota");
  if (dove) dove.textContent = "sto leggendo l'elenco dei modelli\u2026";
  try {
    const esito = await chiedi("/api/modelli?provider=" + encodeURIComponent(provider) +
                               (forza ? "&forza=1" : ""));
    if (!esito.ok || !(esito.modelli || []).length) {
      const motivo = esito.motivo || "elenco non disponibile";
      mettiTesto("conf-orModel", CONFIG_LLM.orModel || "");
      mettiTesto("conf-orModelAdatta", CONFIG_LLM.orModelAdatta || "");
      if (dove) dove.textContent = "elenco a tendina non disponibile (" + motivo +
        "): il modello si scrive a mano";
      return;
    }
    const voci = esito.modelli.map((m) => ({
      valore: m.id,
      etichetta: m.nome + (m.gratuito ? "  \u00b7 gratis" : ""),
      gruppo: m.gruppo,
    }));
    mettiScelta("conf-orModel", voci, CONFIG_LLM.orModel, "\u2014 scegli un modello \u2014");
    mettiScelta("conf-orModelAdatta", voci, CONFIG_LLM.orModelAdatta, "\u2014 usa lo stesso \u2014");
    if (dove) {
      dove.textContent = esito.quanti + " modelli da " + esito.indirizzo +
        (esito.quanti_gratuiti ? " \u00b7 " + esito.quanti_gratuiti + " gratuiti" : "") +
        " \u00b7 raggruppati per editore";
    }
  } catch (e) {
    mettiTesto("conf-orModel", CONFIG_LLM.orModel || "");
    if (dove) dove.textContent = "elenco non raggiungibile (" + e.message + "): si scrive a mano";
  }
}

function campo(etichetta, id, tipo, valore, nota) {
  const scatola = document.createElement("div");
  scatola.className = "campo-parametro";
  const lab = document.createElement("label");
  lab.className = "etichetta"; lab.setAttribute("for", id); lab.textContent = etichetta;
  const inp = document.createElement("input");
  inp.type = tipo; inp.id = id; inp.value = valore || "";
  scatola.appendChild(lab); scatola.appendChild(inp);
  if (nota) {
    const n = document.createElement("div");
    n.className = "nota"; n.textContent = nota;
    scatola.appendChild(n);
  }
  return scatola;
}

function valoreDi(id) { const n = $("#" + id); return n ? n.value.trim() : ""; }

async function salvaConfigLlm() {
  try {
    await inviaJson("/api/config", {
      llm: {
        orKey: valoreDi("conf-orKey"),
        orUrl: valoreDi("conf-orUrl"),
        orModel: valoreDi("conf-orModel"),
        orModelAdatta: valoreDi("conf-orModelAdatta"),
      },
      ricerca: { firecrawlKey: valoreDi("conf-firecrawlKey"), braveKey: valoreDi("conf-braveKey") },
    });
    scrivi("#esito-llm", "Salvato.", "ok");
    await caricaStato();
    await caricaConfig();
  } catch (e) { scrivi("#esito-llm", e.message, "male"); }
}

async function salvaConfigX() {
  try {
    await inviaJson("/api/config", {
      canali: {
        x: {
          client_id: valoreDi("conf-x-client_id"),
          client_secret: valoreDi("conf-x-client_secret"),
          modalita: $("#conf-x-api").checked ? "api" : "compositore",
        },
      },
    });
    scrivi("#esito-x", $("#conf-x-api").checked
      ? "Salvato: X pubblichera' tramite l'API."
      : "Salvato: X si prepara qui e si pubblica dal compositore.", "ok");
    await caricaConfig();
    await aggiornaStatoX();
  } catch (e) { scrivi("#esito-x", e.message, "male"); }
}

async function salvaConfigFirma() {
  try {
    await inviaJson("/api/config", {
      pubblicazione: { firma: valoreDi("conf-firma"), lingua: valoreDi("conf-lingua") },
    });
    scrivi("#esito-firma", "Salvato.", "ok");
    await caricaConfig();
  } catch (e) { scrivi("#esito-firma", e.message, "male"); }
}

async function aggiornaStatoX() {
  try {
    const s = await chiedi("/api/x/stato");
    stato.xCollegato = !!s.collegato;
    $("#stato-x").textContent = s.collegato
      ? "Collegato: " + s.account
      : (s.in_corso ? "Accesso in corso: completa l'autorizzazione nel browser." : "Non collegato. " + (s.motivo || ""));
    $("#stato-x").className = "esito-tenue" + (s.collegato ? " ok" : "");
  } catch (e) {
    $("#stato-x").textContent = "Stato di X non leggibile: " + e.message;
  }
  aggiornaTasti();
}

async function loginX() {
  scrivi("#esito-x", "Apro il browser…");
  try {
    const esito = await inviaJson("/api/x/login", {});
    if (!esito.avviato) { scrivi("#esito-x", esito.motivo, "male"); return; }
    scrivi("#esito-x", esito.messaggio);
    for (let i = 0; i < 60; i += 1) {
      await new Promise((r) => setTimeout(r, 2000));
      const s = await chiedi("/api/x/stato");
      if (s.collegato) { scrivi("#esito-x", "Collegato: " + s.account, "ok"); break; }
      if (!s.in_corso) { scrivi("#esito-x", s.motivo || "Accesso non completato.", "male"); break; }
    }
    await aggiornaStatoX();
  } catch (e) { scrivi("#esito-x", e.message, "male"); }
}

/* --------------------------------------------------------------- registro */

async function caricaRegistro() {
  const scatola = $("#elenco-registro");
  scatola.innerHTML = "";
  try {
    const dati = await chiedi("/api/pubblicazioni");
    if (!dati.pubblicazioni.length) {
      scatola.innerHTML = "<p class=\"esito-tenue\">Nessuna pubblicazione registrata.</p>";
      return;
    }
    dati.pubblicazioni.forEach((p) => {
      const voce = document.createElement("div");
      voce.className = "voce-registro";
      const q = document.createElement("div");
      q.className = "quando";
      q.textContent = (p.quando || "") + " · " + (p.etichetta || p.canale);
      const t = document.createElement("div");
      t.className = "testo"; t.textContent = p.testo || "";
      voce.appendChild(q); voce.appendChild(t);
      if (p.permalink) {
        const a = document.createElement("a");
        a.href = p.permalink; a.target = "_blank"; a.rel = "noopener"; a.textContent = p.permalink;
        voce.appendChild(a);
      }
      scatola.appendChild(voce);
    });
  } catch (e) {
    scatola.innerHTML = "<p class=\"esito-tenue\">Registro non leggibile: " + scappa(e.message) + "</p>";
  }
}

/* ------------------------------------------------------------------- guida */

async function apriGuida() {
  try {
    const risposta = await fetch("/api/guida");
    const testo = await risposta.text();
    apriFinestra("Guida di Social Studio", rendiMarkdown(testo));
  } catch (e) {
    apriFinestra("Guida", rendiMarkdown("Guida non leggibile: " + e.message));
  }
}

/* --------------------------------------------- lavoro in corso (autosalva) */

let timerSalvataggio = null;

function programmaSalvataggio() {
  if (timerSalvataggio) clearTimeout(timerSalvataggio);
  timerSalvataggio = setTimeout(salvaCorrente, 1200);
}

function salvaCorrente() {
  const dati = {
    origine: stato.origine,
    fonte: stato.fonte,
    parametri: leggiModulo(),
    titolo: $("#campo-titolo").value,
    testo: $("#campo-testo").value,
    canale: stato.canale,
    adattati: stato.adattati,
    allegati: stato.allegati,
  };
  try { localStorage.setItem(CHIAVE_CORRENTE, JSON.stringify(dati)); } catch (e) { /* niente */ }
  inviaJson("/api/corrente", dati).catch(() => { /* il salvataggio non deve disturbare */ });
}

async function riprendiCorrente() {
  let dati = null;
  try {
    const remoto = await chiedi("/api/corrente");
    if (remoto && (remoto.testo || remoto.fonte)) dati = remoto;
  } catch (e) { dati = null; }
  if (!dati) {
    try {
      const locale = localStorage.getItem(CHIAVE_CORRENTE);
      if (locale) dati = JSON.parse(locale);
    } catch (e) { dati = null; }
  }
  if (!dati) { await caricaConfig(); await aggiornaStatoX(); return; }

  attivaOrigine(dati.origine || "testo");
  stato.fonte = dati.fonte || null;
  stato.adattati = dati.adattati || {};
  stato.allegati = dati.allegati || [];
  if (dati.fonte && dati.fonte.testo) $("#ingresso-testo").value = dati.fonte.testo;
  if (dati.fonte && dati.fonte.url) {
    if (dati.fonte.tipo === "video") $("#ingresso-video").value = dati.fonte.url;
    else if (dati.fonte.tipo === "link") $("#ingresso-link").value = dati.fonte.url;
  }
  $("#campo-titolo").value = dati.titolo || "";
  $("#campo-testo").value = dati.testo || "";
  if (dati.parametri) {
    stato.parametri = Object.assign(stato.parametri, dati.parametri);
    disegnaParametri();
  }
  mostraImmagine();
  await caricaConfig();
  if (dati.canale) scegliCanale(dati.canale);
  if (dati.testo) avviso("Ho ripreso il lavoro dell'ultima volta.");
}


/* ==================================================================== blog */

/* Il blog non e' un social: ha un pannello suo, che compare solo quando la
   destinazione e' un articolo. Queste funzioni non si mescolano con quelle dei
   post: leggono e scrivono campi che i social non hanno. */

function canaleBlog() {
  const c = stato.canali.find((x) => x.chiave === stato.canale);
  return c && c.tipo === "blog" ? c : null;
}

function statoBlog() {
  if (!stato.blog) {
    stato.blog = { faq: [], intro_faq: "", immagini_corpo: [], categorie: [],
                   html_faq: "", blocco_faq: "" };
  }
  return stato.blog;
}

async function caricaBlogStato() {
  scrivi("#blog-stato", "Guardo il collegamento con il sito\u2026");
  try {
    const s = await chiedi("/api/blog/stato");
    const b = statoBlog();
    if (!s.ok) { scrivi("#blog-stato", s.motivo || "canale non disponibile", "male"); return; }
    scrivi("#blog-stato",
      "Collegato a " + s.sito + ": " + s.pubblicati + " articoli pubblicati, " +
      s.bozze + " bozze in attesa. Qui si deposita una bozza, mai una pubblicazione.", "ok");
    b.categorie = s.categorie || [];
    $("#blog-categorie").innerHTML = b.categorie
      .map((c) => '<option value="' + c.id + '">' + scappa(c.nome) + "</option>").join("");
  } catch (e) {
    scrivi("#blog-stato", "Non riesco a leggere lo stato del sito: " + e.message, "male");
  }
}

async function blogGeneraArticolo() {
  if (!stato.fonte) {
    scrivi("#esito-genera", "Prima leggi la fonte (testo, link o video) nel punto 1.", "male");
    return;
  }
  scrivi("#esito-genera", "Sto scrivendo l'articolo\u2026 (puo' volerci un minuto)");
  $("#tasto-genera-articolo").disabled = true;
  try {
    const esito = await inviaJson("/api/blog/articolo",
                                  { fonte: stato.fonte, parametri: leggiModulo() });
    if (!esito.ok) { scrivi("#esito-genera", esito.motivo, "male"); return; }
    $("#campo-titolo").value = esito.titolo;
    $("#campo-testo").value = esito.testo;
    $("#blog-gancio").value = esito.gancio;
    $("#blog-sintesi").value = esito.sintesi;
    $("#blog-slug").value = esito.slug;
    disegnaContatoreBase();
    const quante = (esito.sezioni || []).length;
    scrivi("#esito-genera",
      "Articolo scritto: " + esito.paragrafi + " paragrafi, " + quante + " sezioni. " +
      "Correggilo qui sotto: quello che pubblichi e' quello che leggi.", "ok");
    if (esito.orfani && esito.orfani.length) {
      avviso("Attenzione: " + esito.orfani.length + " titolo/i di sezione senza testo sotto: " +
             esito.orfani.join(" · "), true);
    }
  } catch (e) {
    scrivi("#esito-genera", "Non riuscito: " + e.message, "male");
  } finally {
    $("#tasto-genera-articolo").disabled = false;
    programmaSalvataggio();
  }
}

async function blogGeneraFaq() {
  const testo = testoDelPost();
  if (!testo) { scrivi("#blog-esito-faq", "Prima serve il testo dell'articolo.", "male"); return; }
  scrivi("#blog-esito-faq", "Sto scrivendo le domande\u2026");
  $("#blog-genera-faq").disabled = true;
  try {
    const esito = await inviaJson("/api/blog/faq",
                                  { testo: testo, titolo: titoloDelPost() });
    const b = statoBlog();
    if (!esito.ok) {
      scrivi("#blog-esito-faq", esito.motivo || "Non riuscito.", "male");
      if (esito.faq) { b.faq = esito.faq; disegnaBlogFaq(); }
      return;
    }
    b.faq = esito.faq;
    b.html_faq = esito.html;
    b.blocco_faq = esito.blocco;
    scrivi("#blog-esito-faq",
      esito.quante + " domande. Puoi correggerle qui sotto: l'anteprima segue.", "ok");
    disegnaBlogFaq();
  } catch (e) {
    scrivi("#blog-esito-faq", "Non riuscito: " + e.message, "male");
  } finally {
    $("#blog-genera-faq").disabled = false;
  }
}

function disegnaBlogFaq() {
  const b = statoBlog();
  const nodo = $("#blog-faq-lista");
  if (!nodo) return;
  const pezzi = [
    '<label for="blog-faq-intro">Frase di apertura della sezione <span class="esito-tenue">facoltativa</span></label>',
    '<textarea id="blog-faq-intro" rows="2" placeholder="Che cosa rispondono queste domande">' +
      scappa(b.intro_faq || "") + "</textarea>",
  ];
  b.faq.forEach((voce, i) => {
    pezzi.push('<div class="coppia-faq">' +
      '<label>Domanda ' + (i + 1) + "</label>" +
      '<input type="text" data-faq-d="' + i + '" value="' + scappa(voce.domanda) + '">' +
      "<label>Risposta</label>" +
      '<textarea rows="3" data-faq-r="' + i + '">' + scappa(voce.risposta) + "</textarea>" +
      '<button type="button" class="tasto tasto-tenue" data-faq-togli="' + i + '">Togli questa domanda</button>' +
      "</div>");
  });
  nodo.innerHTML = pezzi.join("");

  const intro = $("#blog-faq-intro");
  if (intro) {
    intro.addEventListener("input", () => {
      statoBlog().intro_faq = intro.value;
      programmaSalvataggio();
    });
  }
  nodo.querySelectorAll("[data-faq-d]").forEach((n) =>
    n.addEventListener("input", () => {
      statoBlog().faq[Number(n.dataset.faqD)].domanda = n.value;
      programmaAggiornamentoAnteprima();
    }));
  nodo.querySelectorAll("[data-faq-r]").forEach((n) =>
    n.addEventListener("input", () => {
      statoBlog().faq[Number(n.dataset.faqR)].risposta = n.value;
      programmaAggiornamentoAnteprima();
    }));
  nodo.querySelectorAll("[data-faq-togli]").forEach((n) =>
    n.addEventListener("click", () => {
      statoBlog().faq.splice(Number(n.dataset.faqTogli), 1);
      disegnaBlogFaq();
    }));

  $("#blog-aggiorna-anteprima").disabled = !b.faq.length;
  aggiornaAnteprimaFaq();
}

let attesaAnteprima = null;
function programmaAggiornamentoAnteprima() {
  clearTimeout(attesaAnteprima);
  attesaAnteprima = setTimeout(aggiornaAnteprimaFaq, 700);
}

async function aggiornaAnteprimaFaq() {
  const b = statoBlog();
  const chiare = b.faq.filter((v) => v.domanda.trim() && v.risposta.trim());
  if (!chiare.length) {
    $("#blog-faq-anteprima").innerHTML = "";
    $("#blog-faq-html").value = "";
    return;
  }
  try {
    const esito = await inviaJson("/api/blog/faq-html", { faq: chiare });
    if (!esito.ok) { scrivi("#blog-esito-faq", esito.motivo, "male"); return; }
    // L'anteprima E' il markup che si pubblica: non due cose che possono divergere.
    $("#blog-faq-anteprima").innerHTML = esito.html;
    $("#blog-faq-html").value = esito.blocco;
    b.blocco_faq = esito.blocco;
  } catch (e) {
    scrivi("#blog-esito-faq", "Anteprima non riuscita: " + e.message, "male");
  }
}

async function blogGeneraSeo() {
  const testo = testoDelPost();
  if (!testo) { scrivi("#blog-esito-seo", "Prima serve il testo dell'articolo.", "male"); return; }
  scrivi("#blog-esito-seo", "Sto scrivendo i campi SEO\u2026");
  $("#blog-genera-seo").disabled = true;
  try {
    const esito = await inviaJson("/api/blog/seo", {
      titolo: titoloDelPost(), testo: testo, sintesi: $("#blog-sintesi").value.trim(),
    });
    if (!esito.ok) { scrivi("#blog-esito-seo", esito.motivo, "male"); return; }
    $("#blog-seo-title").value = esito.seo_title;
    $("#blog-seo-description").value = esito.seo_description;
    $("#blog-focus-keyword").value = esito.focus_keyword;
    if (!$("#blog-slug").value) $("#blog-slug").value = esito.slug || "";
    disegnaContatoriSeo();
    const nota = esito.corretto_dopo_sforamento
      ? " Il modello aveva sforato: l'ho fatto riscrivere." : "";
    scrivi("#blog-esito-seo", "Fatto." + nota + " I tetti sono misurati qui, non stimati.", "ok");
  } catch (e) {
    scrivi("#blog-esito-seo", "Non riuscito: " + e.message, "male");
  } finally {
    $("#blog-genera-seo").disabled = false;
    programmaSalvataggio();
  }
}

function disegnaContatoriSeo() {
  const titolo = $("#blog-seo-title").value.length;
  const descrizione = $("#blog-seo-description").value.length;
  const t = $("#blog-seo-title-contatore");
  const d = $("#blog-seo-description-contatore");
  t.textContent = titolo + " / 60";
  t.classList.toggle("oltre", titolo > 60);
  d.textContent = descrizione + " / 160";
  d.classList.toggle("oltre", descrizione > 160);
}

function disegnaBlogImmagini() {
  const b = statoBlog();
  const nodo = $("#blog-immagini");
  if (!nodo) return;
  nodo.innerHTML = b.immagini_corpo.map((im, i) =>
    '<div class="allegato-mini">' +
      '<img src="/api/allegati/' + encodeURIComponent(im.nome) + '?t=' + Date.now() + '" alt="">' +
      '<span class="esito-tenue">' + scappa(im.nome) + "</span>" +
      '<label>testo alternativo (alt)</label>' +
      '<input type="text" data-img-alt="' + i + '" value="' + scappa(im.alt || "") + '" ' +
        'placeholder="Che cosa mostra questa immagine">' +
      '<button type="button" class="tasto tasto-tenue" data-img-togli="' + i + '">Rimuovi</button>' +
    "</div>").join("");
  nodo.querySelectorAll("[data-img-alt]").forEach((n) =>
    n.addEventListener("input", () => {
      statoBlog().immagini_corpo[Number(n.dataset.imgAlt)].alt = n.value;
      programmaSalvataggio();
    }));
  nodo.querySelectorAll("[data-img-togli]").forEach((n) =>
    n.addEventListener("click", () => {
      statoBlog().immagini_corpo.splice(Number(n.dataset.imgTogli), 1);
      disegnaBlogImmagini();
    }));
}

async function blogAggiungiImmagine() {
  const b = statoBlog();
  if (b.immagini_corpo.length >= 2) {
    scrivi("#blog-esito-immagine", "Le immagini nel corpo sono al massimo due.", "male");
    return;
  }
  const file = $("#blog-file-immagine").files[0];
  if (!file) { scrivi("#blog-esito-immagine", "Scegli prima un file.", "male"); return; }
  scrivi("#blog-esito-immagine", "Sto caricando\u2026");
  try {
    const dati = new FormData();
    dati.append("media", file, file.name);
    const risposta = await fetch("/api/immagine/carica",
                                { method: "POST", headers: INTESTAZIONE, body: dati });
    const esito = await risposta.json();
    if (!esito.ok) { scrivi("#blog-esito-immagine", esito.motivo, "male"); return; }
    b.immagini_corpo.push(Object.assign({}, esito, { alt: "" }));
    $("#blog-file-immagine").value = "";
    disegnaBlogImmagini();
    scrivi("#blog-esito-immagine",
      "Aggiunta (" + esito.larghezza + "x" + esito.altezza + "). Scrivile l'alt: serve a chi non vede.",
      "ok");
    programmaSalvataggio();
  } catch (e) {
    scrivi("#blog-esito-immagine", "Caricamento non riuscito: " + e.message, "male");
  }
}

function mostraBozza(e) {
  const nodo = $("#blog-esito-bozza");
  const passi = (e.passi || []).map((p) => "<li>" + scappa(p) + "</li>").join("");
  const resa = e.resa || {};
  $("#blog-bozza-messaggio").innerHTML =
    scappa(e.motivo || "Bozza depositata.") + (e.id ? " \u00b7 ID " + e.id : "") +
    (passi ? '<ul class="elenco-passi">' + passi + "</ul>" : "") +
    (resa.parole ? '<span class="esito-tenue">Resa reale: ' + resa.parole + " parole, " +
      (resa.immagini || 0) + " immagini, " + ((resa.titoli || []).length) + " titoli.</span>" : "");
  const link = $("#blog-anteprima-link");
  if (e.anteprima) {
    link.href = e.anteprima;
    link.textContent = "Apri l'anteprima della bozza";
    link.classList.remove("nascosto");
  } else {
    link.classList.add("nascosto");
  }
  nodo.classList.remove("nascosto");
  nodo.scrollIntoView({ behavior: "smooth", block: "nearest" });
}
