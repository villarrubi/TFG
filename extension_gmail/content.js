const SERVER_URL = "http://127.0.0.1:8765/analyze";
const WIDGET_ID = "tfg-phishing-widget";
const CARD_ID = "tfg-phishing-card";
const STATUS_ID = "tfg-phishing-status";
const SCORE_ID = "tfg-phishing-score";
const VERDICT_ID = "tfg-phishing-verdict";
const BAR_ID = "tfg-phishing-bar";
const SUMMARY_ID = "tfg-phishing-summary";
const SIGNALS_ID = "tfg-phishing-signals";
const META_ID = "tfg-phishing-meta";
const TOGGLE_ID = "tfg-phishing-toggle";
const DETAILS_ID = "tfg-phishing-details";
const MINIMIZE_ID = "tfg-phishing-minimize";
const DISMISS_ID = "tfg-phishing-dismiss";
const RETRY_INTERVAL_STORAGE_KEY = "retryIntervalMs";
const DEFAULT_RETRY_INTERVAL_MS = 60000;

let lastFingerprint = "";
let dismissedFingerprint = "";
let debounceTimer = null;
let retryTimer = null;

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
  return textOf(body);
}

function getHtmlBody(root) {
  const body = root.querySelector(".a3s.aiL") || root.querySelector(".a3s");
  return body ? body.innerHTML : "";
}

function getAnchors(root) {
  return Array.from(root.querySelectorAll(".a3s a[href], .ii a[href]"))
    .map((anchor) => ({
      text: textOf(anchor),
      href: anchor.href
    }))
    .filter((anchor) => anchor.href && !anchor.href.startsWith("mailto:"));
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
  const urls = Array.from(new Set([...getUrlsFromText(body), ...anchors.map((anchor) => anchor.href)]));

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
  return [payload.subject, payload.from, payload.body.slice(0, 500), payload.urls.join("|")].join("::");
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

  const header = createElement("div", "tfg-phishing-header");
  const titleBlock = createElement("div", "tfg-phishing-title-block");
  titleBlock.appendChild(createElement("div", "tfg-phishing-kicker", "TFG Phishing Guard"));
  titleBlock.appendChild(createElement("div", "tfg-phishing-title", "Analisis de este correo"));

  const status = createElement("div", "tfg-phishing-status", "Cargando");
  status.id = STATUS_ID;
  const actions = createElement("div", "tfg-phishing-actions");
  const minimize = createElement("button", "tfg-phishing-icon-button", "-");
  minimize.id = MINIMIZE_ID;
  minimize.type = "button";
  minimize.title = "Minimizar panel";
  minimize.addEventListener("click", toggleMinimized);
  const dismiss = createElement("button", "tfg-phishing-icon-button", "x");
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
  const score = createElement("div", "tfg-phishing-score", "--%");
  score.id = SCORE_ID;
  const verdict = createElement("div", "tfg-phishing-verdict", "Detector cargado");
  verdict.id = VERDICT_ID;
  main.appendChild(score);
  main.appendChild(verdict);

  const barTrack = createElement("div", "tfg-phishing-bar-track");
  const bar = createElement("div", "tfg-phishing-bar");
  bar.id = BAR_ID;
  barTrack.appendChild(bar);

  const summary = createElement("div", "tfg-phishing-summary", "Abre un correo para analizarlo.");
  summary.id = SUMMARY_ID;
  const signals = createElement("div", "tfg-phishing-signals");
  signals.id = SIGNALS_ID;
  const meta = createElement("div", "tfg-phishing-meta", "Sin comprobacion todavia");
  meta.id = META_ID;

  const toggle = createElement("button", "tfg-phishing-toggle", "Ver detalles");
  toggle.id = TOGGLE_ID;
  toggle.type = "button";
  toggle.setAttribute("aria-expanded", "false");
  toggle.addEventListener("click", toggleDetails);

  const details = createElement("div", "tfg-phishing-details");
  details.id = DETAILS_ID;
  details.hidden = true;
  details.dataset.empty = "true";

  card.appendChild(header);
  card.appendChild(main);
  card.appendChild(barTrack);
  card.appendChild(summary);
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
  toggle.textContent = details.hidden ? "Ver detalles" : "Ocultar detalles";
}

function renderDetails(result) {
  const details = document.getElementById(DETAILS_ID);
  const toggle = document.getElementById(TOGGLE_ID);
  if (!details) {
    return;
  }

  const activeSignals = Object.entries(result.signals || {})
    .filter(([, value]) => value)
    .map(([name]) => name.replaceAll("_", " "));
  const explanations = Array.isArray(result.explanation)
    ? result.explanation.filter((line) => !line.startsWith("No se") && !line.startsWith("El asunto no") && !line.startsWith("No hay"))
    : [];

  const lines = [
    result.description,
    ...explanations.slice(0, 4),
    activeSignals.length ? `Señales activas: ${activeSignals.slice(0, 6).join(", ")}.` : ""
  ].filter(Boolean);

  details.dataset.empty = lines.length ? "false" : "true";
  if (toggle) {
    toggle.disabled = !lines.length;
    toggle.textContent = "Ver detalles";
    toggle.setAttribute("aria-expanded", "false");
  }
  details.hidden = true;
  details.innerHTML = "";
  lines.forEach((line) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = line;
    details.appendChild(paragraph);
  });
  renderSignalChips(activeSignals);
}

function renderSignalChips(activeSignals) {
  const container = document.getElementById(SIGNALS_ID);
  if (!container) {
    return;
  }
  container.innerHTML = "";
  if (!activeSignals.length) {
    const chip = createElement("span", "tfg-phishing-chip muted", "Sin señales activas");
    container.appendChild(chip);
    return;
  }
  activeSignals.slice(0, 4).forEach((signal) => {
    const chip = createElement("span", "tfg-phishing-chip", signal);
    container.appendChild(chip);
  });
  if (activeSignals.length > 4) {
    container.appendChild(createElement("span", "tfg-phishing-chip muted", `+${activeSignals.length - 4}`));
  }
}

function clearSignalChips(text) {
  const container = document.getElementById(SIGNALS_ID);
  if (!container) {
    return;
  }
  container.innerHTML = "";
  container.appendChild(createElement("span", "tfg-phishing-chip muted", text));
}

async function analyzeVisibleEmail(options = {}) {
  const payload = getEmailPayload();
  if (!payload) {
    return;
  }

  const currentFingerprint = fingerprint(payload);
  showCardForCurrentEmail(currentFingerprint);
  if (dismissedFingerprint === currentFingerprint) {
    return;
  }
  if (!options.force && currentFingerprint === lastFingerprint) {
    return;
  }

  clearOfflineRetry();
  setPanel("loading", {
    status: "Analizando",
    scoreText: "--%",
    scoreValue: 0,
    verdict: "Revisando contenido y enlaces",
    summary: "El detector local esta evaluando el correo abierto.",
    meta: "Comprobando ahora"
  });
  clearSignalChips("Analizando");
  const details = document.getElementById(DETAILS_ID);
  if (details) {
    details.hidden = true;
    details.dataset.empty = "true";
    details.innerHTML = "";
  }

  try {
    const response = await fetch(SERVER_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const result = await response.json();
    lastFingerprint = currentFingerprint;
    const score = Number(result.risk_score || 0).toFixed(1);
    const state = result.is_phishing ? "danger" : "safe";
    setPanel(state, {
      status: result.is_phishing ? "Riesgo alto" : "Riesgo bajo",
      scoreText: `${score}%`,
      scoreValue: Number(score),
      verdict: result.is_phishing ? "Posible phishing" : "No parece phishing",
      summary: result.is_phishing
        ? "Hay senales suficientes para tratar este mensaje con cautela."
        : "No se han encontrado senales fuertes de phishing en los datos visibles.",
      meta: `Ultima comprobacion: ${new Date().toLocaleTimeString()}`
    });
    renderDetails(result);
  } catch (error) {
    setPanel("offline", {
      status: "Sin conexion",
      scoreText: "--%",
      scoreValue: 0,
      verdict: "Detector local apagado",
      summary: "Arranca el servidor Python para activar el analisis.",
      meta: `Ultimo intento: ${new Date().toLocaleTimeString()}`
    });
    clearSignalChips("Sin conexion");
    const offlineDetails = document.getElementById(DETAILS_ID);
    const toggle = document.getElementById(TOGGLE_ID);
    if (offlineDetails) {
      offlineDetails.dataset.empty = "false";
      offlineDetails.innerHTML = "<p>Arranca el servidor local con python src/gmail_extension_server.py.</p><p>La extension volvera a comprobar la conexion automaticamente.</p>";
    }
    if (toggle) {
      toggle.disabled = false;
      toggle.textContent = "Ver detalles";
    }
    lastFingerprint = "";
    scheduleOfflineRetry();
  }
}

function scheduleAnalysis() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(analyzeVisibleEmail, 700);
}

ensureCard();
setPanel("loading", {
  status: "Preparado",
  scoreText: "--%",
  scoreValue: 0,
  verdict: "Detector cargado",
  summary: "Abre un correo en Gmail para iniciar el analisis.",
  meta: "Sin comprobacion todavia"
});
clearSignalChips("Esperando correo");
const observer = new MutationObserver(scheduleAnalysis);
observer.observe(document.documentElement, { childList: true, subtree: true });
scheduleAnalysis();
