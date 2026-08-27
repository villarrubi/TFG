const RETRY_INTERVAL_STORAGE_KEY = "retryIntervalMs";
const DEFAULT_RETRY_SECONDS = 60;

const input = document.getElementById("retry-seconds");
const serverInput = document.getElementById("server-base-url");
const button = document.getElementById("save-button");
const checkButton = document.getElementById("check-button");
const status = document.getElementById("save-status");
const serverStatus = document.getElementById("server-status");

function loadOptions() {
  chrome.storage.local.get(
    {
      [RETRY_INTERVAL_STORAGE_KEY]: DEFAULT_RETRY_SECONDS * 1000,
      [PhishingServerConfig.SERVER_BASE_URL_STORAGE_KEY]:
        PhishingServerConfig.DEFAULT_SERVER_BASE_URL
    },
    (items) => {
      input.value = Math.round(Number(items[RETRY_INTERVAL_STORAGE_KEY]) / 1000);
      serverInput.value = items[PhishingServerConfig.SERVER_BASE_URL_STORAGE_KEY];
    }
  );
}

function persistOptions(seconds, serverBaseUrl) {
  chrome.storage.local.set({
    [RETRY_INTERVAL_STORAGE_KEY]: seconds * 1000,
    [PhishingServerConfig.SERVER_BASE_URL_STORAGE_KEY]: serverBaseUrl
  }, () => {
    input.value = seconds;
    serverInput.value = serverBaseUrl;
    status.className = "save-status";
    status.textContent = "Guardado.";
    setTimeout(() => {
      status.textContent = "";
    }, 1800);
  });
}

function saveOptions() {
  const seconds = Math.max(5, Number(input.value) || DEFAULT_RETRY_SECONDS);
  let serverBaseUrl;
  try {
    serverBaseUrl = PhishingServerConfig.normalizeServerBaseUrl(serverInput.value);
  } catch (error) {
    status.className = "save-status error";
    status.textContent = error.message;
    return;
  }
  const permissionOrigin = PhishingServerConfig.permissionOrigin(serverBaseUrl);
  if (!permissionOrigin) {
    persistOptions(seconds, serverBaseUrl);
    return;
  }
  if (!chrome.permissions || !chrome.permissions.request) {
    status.className = "save-status error";
    status.textContent = "No se pudo solicitar permiso para el servidor remoto.";
    return;
  }
  chrome.permissions.request({ origins: [permissionOrigin] }, (granted) => {
    if (!granted) {
      status.className = "save-status error";
      status.textContent = "Permiso denegado para acceder al backend remoto.";
      return;
    }
    persistOptions(seconds, serverBaseUrl);
  });
}

function setServerStatus(isOnline, text) {
  serverStatus.className = `status-pill ${isOnline ? "online" : "offline"}`;
  serverStatus.textContent = text;
}

async function checkServer() {
  setServerStatus(false, "Comprobando...");
  try {
    const serverBaseUrl = PhishingServerConfig.normalizeServerBaseUrl(serverInput.value);
    const response = await fetch(`${serverBaseUrl}/health`, { method: "GET" });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json();
    setServerStatus(true, `Activo (${data.mode || "sin modo"})`);
  } catch (error) {
    setServerStatus(false, "No responde");
  }
}

button.addEventListener("click", saveOptions);
checkButton.addEventListener("click", checkServer);
loadOptions();
checkServer();
