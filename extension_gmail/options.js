const RETRY_INTERVAL_STORAGE_KEY = "retryIntervalMs";
const DEFAULT_RETRY_SECONDS = 60;
const HEALTH_URL = "http://127.0.0.1:8765/health";

const input = document.getElementById("retry-seconds");
const button = document.getElementById("save-button");
const checkButton = document.getElementById("check-button");
const status = document.getElementById("save-status");
const serverStatus = document.getElementById("server-status");

function loadOptions() {
  chrome.storage.local.get(
    { [RETRY_INTERVAL_STORAGE_KEY]: DEFAULT_RETRY_SECONDS * 1000 },
    (items) => {
      input.value = Math.round(Number(items[RETRY_INTERVAL_STORAGE_KEY]) / 1000);
    }
  );
}

function saveOptions() {
  const seconds = Math.max(5, Number(input.value) || DEFAULT_RETRY_SECONDS);
  chrome.storage.local.set({ [RETRY_INTERVAL_STORAGE_KEY]: seconds * 1000 }, () => {
    input.value = seconds;
    status.textContent = "Guardado.";
    setTimeout(() => {
      status.textContent = "";
    }, 1800);
  });
}

function setServerStatus(isOnline, text) {
  serverStatus.className = `status-pill ${isOnline ? "online" : "offline"}`;
  serverStatus.textContent = text;
}

async function checkServer() {
  setServerStatus(false, "Comprobando...");
  try {
    const response = await fetch(HEALTH_URL, { method: "GET" });
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
