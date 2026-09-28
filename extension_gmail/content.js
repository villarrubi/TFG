const WIDGET_ID = "tfg-phishing-widget";
const CARD_ID = "tfg-phishing-card";
const STATUS_ID = "tfg-phishing-status";
const SCORE_ID = "tfg-phishing-score";
const VERDICT_ID = "tfg-phishing-verdict";
const BAR_ID = "tfg-phishing-bar";
const SUMMARY_ID = "tfg-phishing-summary";
const ADVICE_ID = "tfg-phishing-advice";
const SIGNALS_ID = "tfg-phishing-signals";
const META_ID = "tfg-phishing-meta";
const TOGGLE_ID = "tfg-phishing-toggle";
const DETAILS_ID = "tfg-phishing-details";
const MINIMIZE_ID = "tfg-phishing-minimize";
const DISMISS_ID = "tfg-phishing-dismiss";
const RETRY_INTERVAL_STORAGE_KEY = "retryIntervalMs";
const DEFAULT_RETRY_INTERVAL_MS = 60000;
const MAX_FIELD_CHARS = 200000;
const MAX_LIST_ITEMS = 100;

let lastFingerprint = "";
let dismissedFingerprint = "";
let debounceTimer = null;
let retryTimer = null;
let analysisRequestId = 0;
let pendingFingerprint = "";

function textOf(element) {
  return element ? element.textContent.replace(/\s+/g, " ").trim() : "";
}

function getOpenMessageRoot() {
  return (
    document.querySelector("div[role='main'] div.adn.ads") ||
    document.querySelector("div[role='main'] div[aria-label][data-message-id]") ||
    document.querySelector("div[role='main']")
  );
}

function getSubject() {
  return textOf(document.querySelector("h2.hP")) || textOf(document.querySelector("[data-thread-perm-id] h2"));
}

function getSender(root) {
  const sender =
    root.querySelector(".gD[email]") ||
    root.querySelector("[email]") ||
    root.querySelector(".go");
  if (!sender) {
    return "";
  }
  return sender.getAttribute("email") || sender.getAttribute("name") || textOf(sender);
}

function getBody(root) {
  const body =
    root.querySelector(".a3s.aiL") ||
    root.querySelector(".a3s") ||
    root.querySelector("[dir='ltr']");
  return textOf(body).slice(0, MAX_FIELD_CHARS);
}

function getHtmlBody(root) {
  const body = root.querySelector(".a3s.aiL") || root.querySelector(".a3s");
  return body ? body.innerHTML.slice(0, MAX_FIELD_CHARS) : "";
}

function getAnchors(root) {
  return Array.from(root.querySelectorAll(".a3s a[href], .ii a[href]"))
    .map((anchor) => ({
      text: textOf(anchor),
      href: anchor.href
    }))
    .filter((anchor) => anchor.href && !anchor.href.startsWith("mailto:"))
    .slice(0, MAX_LIST_ITEMS);
}

function getUrlsFromText(text) {
  const matches = text.match(/https?:\/\/[^\s<>"')]+/gi);
  return matches ? Array.from(new Set(matches)) : [];
}

function getEmailPayload() {
  const root = getOpenMessageRoot();
  if (!root) {
    return null;
  }
  const body = getBody(root);
  const subject = getSubject();
  const sender = getSender(root);
  const anchors = getAnchors(root);
  const urls = Array.from(
    new Set([...getUrlsFromText(body), ...anchors.map((anchor) => anchor.href)])
  ).slice(0, MAX_LIST_ITEMS);

  if (!subject && !sender && body.length < 20) {
    return null;
  }

  return {
    subject,
    from: sender,
    body,
    html_body: getHtmlBody(root),
    anchors,
    urls
  };
}

function fingerprint(payload) {
  // Un cambio al final del texto o en el HTML también puede cambiar los indicios.
  return JSON.stringify(payload);
}

function getRetryIntervalMs() {
  return new Promise((resolve) => {
    if (typeof chrome === "undefined" || !chrome.storage || !chrome.storage.local) {
      resolve(DEFAULT_RETRY_INTERVAL_MS);
      return;
    }
    chrome.storage.local.get({ [RETRY_INTERVAL_STORAGE_KEY]: DEFAULT_RETRY_INTERVAL_MS }, (items) => {
      const interval = Number(items[RETRY_INTERVAL_STORAGE_KEY]);
      resolve(Number.isFinite(interval) && interval >= 5000 ? interval : DEFAULT_RETRY_INTERVAL_MS);
    });
  });
}

async function scheduleOfflineRetry() {
  clearTimeout(retryTimer);
  const interval = await getRetryIntervalMs();
  retryTimer = setTimeout(() => analyzeVisibleEmail({ force: true }), interval);
}

function clearOfflineRetry() {
  clearTimeout(retryTimer);
  retryTimer = null;
}

function ensureWidget() {
  let widget = document.getElementById(WIDGET_ID);
  if (!widget) {
    widget = document.createElement("div");
    widget.id = WIDGET_ID;
    document.body.appendChild(widget);
  }
  return widget;
}

function createElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) {
    element.className = className;
  }
  if (text) {
    element.textContent = text;
  }
  return element;
}

function ensureCard() {
  let card = document.getElementById(CARD_ID);
  if (card) {
    return card;
  }

  card = createElement("section", "tfg-phishing-card loading");
  card.id = CARD_ID;
  card.setAttribute("aria-live", "polite");
  card.setAttribute("aria-label", "Análisis de phishing del correo visible");
  card.tabIndex = 0;

  const header = createElement("div", "tfg-phishing-header");
  const titleBlock = createElement("div", "tfg-phishing-title-block");
  titleBlock.appendChild(createElement("div", "tfg-phishing-kicker", "TFG Phishing Guard"));
  titleBlock.appendChild(createElement("div", "tfg-phishing-title", "Análisis de este correo"));

  const status = createElement("div", "tfg-phishing-status", "Cargando");
  status.id = STATUS_ID;
  const actions = createElement("div", "tfg-phishing-actions");
  const minimize = createElement("button", "tfg-phishing-icon-button", "−");
  minimize.id = MINIMIZE_ID;
  minimize.type = "button";
  minimize.title = "Minimizar panel";
  minimize.addEventListener("click", toggleMinimized);
  const dismiss = createElement("button", "tfg-phishing-icon-button", "×");
  dismiss.id = DISMISS_ID;
  dismiss.type = "button";
  dismiss.title = "Ocultar hasta cambiar de correo";
  dismiss.addEventListener("click", dismissCurrentEmail);
  actions.appendChild(status);
  actions.appendChild(minimize);
  actions.appendChild(dismiss);
  header.appendChild(titleBlock);
  header.appendChild(actions);

  const main = createElement("div", "tfg-phishing-main");
  const scoreBlock = createElement("div", "tfg-phishing-score-block");
  const score = createElement("div", "tfg-phishing-score", "—%");
  score.id = SCORE_ID;
  scoreBlock.appendChild(score);
  scoreBlock.appendChild(createElement("div", "tfg-phishing-score-label", "Índice de riesgo"));
  const verdict = createElement("div", "tfg-phishing-verdict", "Detector cargado");
  verdict.id = VERDICT_ID;
  main.appendChild(scoreBlock);
  main.appendChild(verdict);

  const barTrack = createElement("div", "tfg-phishing-bar-track");
  const bar = createElement("div", "tfg-phishing-bar");
  bar.id = BAR_ID;
  barTrack.appendChild(bar);

  const summary = createElement("div", "tfg-phishing-summary", "Abre un correo para analizarlo.");
  summary.id = SUMMARY_ID;
  const advice = createElement("div", "tfg-phishing-advice");
  advice.id = ADVICE_ID;
  advice.hidden = true;
  const signals = createElement("div", "tfg-phishing-signals");
  signals.id = SIGNALS_ID;
  const meta = createElement("div", "tfg-phishing-meta", "Sin comprobacion todavia");
  meta.id = META_ID;

  const toggle = createElement("button", "tfg-phishing-toggle", "Ver detalles");
  toggle.id = TOGGLE_ID;
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", "false");
  toggle.setAttribute("aria-controls", DETAILS_ID);
  toggle.addEventListener("click", toggleDetails);

  const details = createElement("div", "tfg-phishing-details");
  details.id = DETAILS_ID;
  details.hidden = true;
  details.dataset.empty = "true";

  card.appendChild(header);
  card.appendChild(main);
  card.appendChild(barTrack);
  card.appendChild(summary);
  card.appendChild(advice);
  card.appendChild(signals);
  card.appendChild(meta);
  card.appendChild(toggle);
  card.appendChild(details);
  ensureWidget().appendChild(card);
  return card;
}

function setPanel(state, data) {
  const card = ensureCard();
  const wasMinimized = card.classList.contains("minimized");
  const status = document.getElementById(STATUS_ID);
  const score = document.getElementById(SCORE_ID);
  const verdict = document.getElementById(VERDICT_ID);
  const summary = document.getElementById(SUMMARY_ID);
  const bar = document.getElementById(BAR_ID);
  const meta = document.getElementById(META_ID);

  card.className = `tfg-phishing-card ${state}`;
  if (wasMinimized) {
    card.classList.add("minimized");
  }
  status.textContent = data.status;
  score.textContent = data.scoreText;
  verdict.textContent = data.verdict;
  summary.textContent = data.summary;
  bar.style.width = `${Math.max(0, Math.min(100, data.scoreValue))}%`;
  meta.textContent = data.meta || meta.textContent;
}

function toggleMinimized() {
  const card = ensureCard();
  const button = document.getElementById(MINIMIZE_ID);
  card.classList.toggle("minimized");
  const minimized = card.classList.contains("minimized");
  button.textContent = minimized ? "+" : "-";
  button.title = minimized ? "Expandir panel" : "Minimizar panel";
}

function dismissCurrentEmail() {
  const payload = getEmailPayload();
  if (payload) {
    dismissedFingerprint = fingerprint(payload);
  }
  ensureCard().hidden = true;
}

function showCardForCurrentEmail(currentFingerprint) {
  const card = ensureCard();
  if (dismissedFingerprint !== currentFingerprint) {
    card.hidden = false;
  }
}

function toggleDetails() {
  const details = document.getElementById(DETAILS_ID);
  const toggle = document.getElementById(TOGGLE_ID);
  if (!details || !toggle || details.dataset.empty === "true") {
    return;
  }
  details.hidden = !details.hidden;
  toggle.setAttribute("aria-expanded", String(!details.hidden));
  toggle.textContent = details.hidden ? (toggle.dataset.label || "Ver detalles") : "Ocultar detalles";
}

function renderDetails(result) {
  const details = document.getElementById(DETAILS_ID);
  const toggle = document.getElementById(TOGGLE_ID);
  if (!details) {
    return;
  }

  // El servidor relaciona explícitamente cada motivo con su señal activa.
  // No deducir si una frase es positiva o negativa por sus primeras palabras.
  const guidance = result.guidance || {
    summary: "No se han recibido motivos detallados para este resultado.",
    findings: [],
    actions: ["Confirma cualquier petición de dinero o claves por un canal conocido."],
    context: [],
    limits: "La puntuación por sí sola no confirma que un correo sea auténtico."
  };
  const findings = guidance.findings || [];
  document.getElementById(SUMMARY_ID).textContent = guidance.summary;
  const advice = document.getElementById(ADVICE_ID);
  advice.replaceChildren(createElement("strong", "", "Qué hacer ahora"));
  const actions = createElement("ul");
  (guidance.actions || []).slice(0, 2).forEach((action) => {
    actions.appendChild(createElement("li", "", action));
  });
  advice.appendChild(actions);
  advice.hidden = false;

  details.dataset.empty = "false";
  if (toggle) {
    toggle.disabled = false;
    toggle.dataset.label = findings.length === 1
      ? "Ver el indicio y su recomendación"
      : findings.length
        ? `Ver los ${findings.length} indicios y sus recomendaciones`
        : "Ver alcance del análisis";
    toggle.textContent = toggle.dataset.label;
    toggle.setAttribute("aria-expanded", "false");
  }
  details.hidden = true;
  details.replaceChildren();
  findings.forEach((finding) => {
    const item = createElement("div", "tfg-phishing-finding");
    item.appendChild(createElement("strong", "", finding.title));
    item.appendChild(createElement("p", "", finding.detail));
    item.appendChild(createElement("p", "tfg-phishing-next-step", `Qué hacer: ${finding.action}`));
    details.appendChild(item);
  });
  (guidance.context || []).forEach((note) => details.appendChild(createElement("p", "", note)));
  details.appendChild(createElement("strong", "", "Alcance del análisis"));
  details.appendChild(createElement("p", "", "Se analiza lo visible en Gmail. No se verifican las cabeceras completas, la autenticidad del remitente ni los destinos de los enlaces."));
  details.appendChild(createElement("p", "", guidance.limits));
  details.appendChild(createElement("p", "", "La puntuación es un índice de riesgo, no una probabilidad calibrada."));

  const container = document.getElementById(SIGNALS_ID);
  container.replaceChildren();
  container.hidden = !findings.length;
  if (findings.length) container.appendChild(createElement("strong", "", "Principales indicios"));
  const list = createElement("ul");
  findings.slice(0, 3).forEach((finding) => {
    list.appendChild(createElement("li", "", finding.title));
  });
  container.appendChild(list);
}

function clearSignalChips(text) {
  const container = document.getElementById(SIGNALS_ID);
  if (!container) {
    return;
  }
  container.innerHTML = "";
  container.hidden = false;
  container.appendChild(createElement("span", "tfg-phishing-chip muted", text));
}

async function analyzeVisibleEmail(options = {}) {
  const payload = getEmailPayload();
  if (!payload) {
    clearOfflineRetry();
    lastFingerprint = "";
    pendingFingerprint = "";
    analysisRequestId += 1;
    const card = document.getElementById(CARD_ID);
    if (card) card.hidden = true;
    return;
  }

  const currentFingerprint = fingerprint(payload);
  showCardForCurrentEmail(currentFingerprint);
  if (dismissedFingerprint === currentFingerprint) {
    return;
  }
  if (!options.force && (currentFingerprint === lastFingerprint || currentFingerprint === pendingFingerprint)) {
    return;
  }

  clearOfflineRetry();
  const requestId = ++analysisRequestId;
  pendingFingerprint = currentFingerprint;
  const isCurrentMessage = () => {
    const visible = getEmailPayload();
    return requestId === analysisRequestId && visible &&
      fingerprint(visible) === currentFingerprint && dismissedFingerprint !== currentFingerprint;
  };
  const advice = document.getElementById(ADVICE_ID);
  advice.hidden = true;
  advice.replaceChildren();
  setPanel("loading", {
    status: "Analizando",
    scoreText: "—%",
    scoreValue: 0,
    verdict: "Revisando contenido y enlaces",
    summary: "El backend central está evaluando el correo abierto.",
    meta: "Comprobando ahora"
  });
  clearSignalChips("Analizando");
  const toggle = document.getElementById(TOGGLE_ID);
  toggle.disabled = true;
  toggle.textContent = "Analizando…";
  toggle.setAttribute("aria-expanded", "false");
  const details = document.getElementById(DETAILS_ID);
  if (details) {
    details.hidden = true;
    details.dataset.empty = "true";
    details.innerHTML = "";
  }

  try {
    const serverBaseUrl = await PhishingServerConfig.getServerBaseUrl();
    const response = await fetch(`${serverBaseUrl}/analyze`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      let message = `El backend respondió HTTP ${response.status}.`;
      try {
        const errorPayload = await response.json();
        if (errorPayload && errorPayload.error) {
          message = String(errorPayload.error);
        }
      } catch (parseError) {
        // El código HTTP sigue siendo suficiente si el cuerpo no es JSON.
      }
      const requestError = new Error(message);
      requestError.retryable = response.status >= 500 || response.status === 429;
      throw requestError;
    }
    const result = await response.json();
    if (!isCurrentMessage()) return;
    lastFingerprint = currentFingerprint;
    const score = Number(result.risk_score || 0).toFixed(1);
    const state = result.is_phishing ? "danger" : "safe";
    setPanel(state, {
      status: result.is_phishing ? "Riesgo alto" : "Riesgo bajo",
      scoreText: `${score}%`,
      scoreValue: Number(score),
      verdict: result.is_phishing ? "Posible phishing" : "Sin alerta de phishing",
      summary: result.is_phishing
        ? "Hay señales suficientes para tratar este mensaje con cautela."
        : "No se han encontrado señales fuertes de phishing en los datos visibles.",
      meta: `Última comprobación: ${new Date().toLocaleTimeString()}`
    });
    renderDetails(result);
  } catch (error) {
    if (!isCurrentMessage()) return;
    const retryable = error.retryable !== false;
    setPanel("offline", {
      status: retryable ? "Sin conexión" : "Solicitud rechazada",
      scoreText: "—%",
      scoreValue: 0,
      verdict: retryable ? "Backend central no disponible" : "No se pudo analizar el correo",
      summary: retryable
        ? "Arranca el backend Python para activar el análisis."
        : error.message,
      meta: `Último intento: ${new Date().toLocaleTimeString()}`
    });
    clearSignalChips(retryable ? "Sin conexión" : "Entrada rechazada");
    const offlineDetails = document.getElementById(DETAILS_ID);
    const toggle = document.getElementById(TOGGLE_ID);
    if (offlineDetails) {
      offlineDetails.dataset.empty = "false";
      offlineDetails.innerHTML = retryable
        ? "<p>Arranca el backend central con <code>python src/backend_server.py</code>.</p><p>La extensión volverá a comprobar la conexión automáticamente.</p>"
        : "<p>Revisa el tamaño y los campos visibles del correo antes de reintentar.</p>";
    }
    if (toggle) {
      toggle.disabled = false;
      toggle.dataset.label = "Ver detalles";
      toggle.textContent = "Ver detalles";
    }
    lastFingerprint = "";
    if (retryable) {
      scheduleOfflineRetry();
    }
  } finally {
    if (requestId === analysisRequestId) pendingFingerprint = "";
  }
}

function scheduleAnalysis() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(analyzeVisibleEmail, 700);
}

ensureCard();
setPanel("loading", {
  status: "Preparado",
  scoreText: "—%",
  scoreValue: 0,
  verdict: "Detector cargado",
  summary: "Abre un correo en Gmail para iniciar el análisis.",
  meta: "Sin comprobación todavía"
});
clearSignalChips("Esperando correo");
const observer = new MutationObserver((mutations) => {
  const widget = document.getElementById(WIDGET_ID);
  if (mutations.some((mutation) => !widget || !widget.contains(mutation.target))) {
    scheduleAnalysis();
  }
});
observer.observe(document.documentElement, { childList: true, subtree: true });
scheduleAnalysis();
