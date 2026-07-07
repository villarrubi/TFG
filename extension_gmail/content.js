const SERVER_URL = "http://127.0.0.1:8765/analyze";
const WIDGET_ID = "tfg-phishing-widget";
const BADGE_ID = "tfg-phishing-badge";
const DETAILS_ID = "tfg-phishing-details";

let lastFingerprint = "";
let debounceTimer = null;

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

function findSubjectContainer() {
  return document.querySelector(".ha h2.hP") || document.querySelector("h2.hP") || document.querySelector("div[role='main']");
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

function ensureBadge() {
  let badge = document.getElementById(BADGE_ID);
  if (!badge) {
    badge = document.createElement("button");
    badge.id = BADGE_ID;
    badge.type = "button";
    badge.setAttribute("aria-expanded", "false");
    badge.addEventListener("click", toggleDetails);
    ensureWidget().appendChild(badge);
  }
  return badge;
}

function ensureDetails() {
  let details = document.getElementById(DETAILS_ID);
  if (!details) {
    details = document.createElement("div");
    details.id = DETAILS_ID;
    details.hidden = true;
    ensureWidget().appendChild(details);
  }
  return details;
}

function setBadge(state, text) {
  const badge = ensureBadge();
  if (!badge) {
    return;
  }
  badge.className = `tfg-phishing-badge ${state}`;
  badge.textContent = text;
}

function toggleDetails() {
  const details = ensureDetails();
  const badge = ensureBadge();
  if (!details || !badge || details.dataset.empty === "true") {
    return;
  }
  details.hidden = !details.hidden;
  badge.setAttribute("aria-expanded", String(!details.hidden));
}

function renderDetails(result) {
  const details = ensureDetails();
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
  details.innerHTML = "";
  lines.forEach((line) => {
    const paragraph = document.createElement("p");
    paragraph.textContent = line;
    details.appendChild(paragraph);
  });
}

async function analyzeVisibleEmail() {
  const payload = getEmailPayload();
  if (!payload) {
    return;
  }

  const currentFingerprint = fingerprint(payload);
  if (currentFingerprint === lastFingerprint) {
    return;
  }
  lastFingerprint = currentFingerprint;

  setBadge("loading", "Analizando phishing...");
  const details = ensureDetails();
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
    const score = Number(result.risk_score || 0).toFixed(1);
    setBadge(result.is_phishing ? "danger" : "safe", `${result.label}: ${score}%`);
    renderDetails(result);
  } catch (error) {
    setBadge("offline", "Detector local apagado");
    const offlineDetails = ensureDetails();
    if (offlineDetails) {
      offlineDetails.dataset.empty = "false";
      offlineDetails.innerHTML = "<p>Arranca el servidor local con python src/gmail_extension_server.py.</p>";
    }
  }
}

function scheduleAnalysis() {
  clearTimeout(debounceTimer);
  debounceTimer = setTimeout(analyzeVisibleEmail, 700);
}

setBadge("loading", "Detector cargado");
const observer = new MutationObserver(scheduleAnalysis);
observer.observe(document.documentElement, { childList: true, subtree: true });
scheduleAnalysis();
