(function exposeServerConfig(globalObject) {
  "use strict";

  const SERVER_BASE_URL_STORAGE_KEY = "serverBaseUrl";
  const DEFAULT_SERVER_BASE_URL = "http://127.0.0.1:8766";
  const LOOPBACK_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);

  function normalizeServerBaseUrl(value) {
    const candidate = String(value || DEFAULT_SERVER_BASE_URL).trim();
    let url;
    try {
      url = new URL(candidate);
    } catch (error) {
      throw new Error("La URL del servidor no es válida.");
    }
    if (
      !["http:", "https:"].includes(url.protocol) ||
      url.username ||
      url.password ||
      (url.pathname !== "/" && url.pathname !== "") ||
      url.search ||
      url.hash
    ) {
      throw new Error("Usa un origen HTTP(S) sin ruta, usuario, consulta ni fragmento.");
    }
    if (
      url.protocol === "http:" &&
      !LOOPBACK_HOSTS.has(url.hostname.toLowerCase())
    ) {
      throw new Error("HTTP solo se admite en local; usa HTTPS para un backend remoto.");
    }
    return url.origin;
  }

  function permissionOrigin(value) {
    const origin = normalizeServerBaseUrl(value);
    const url = new URL(origin);
    if (url.protocol !== "https:") {
      return null;
    }
    return `${origin}/*`;
  }

  function getServerBaseUrl() {
    return new Promise((resolve) => {
      if (
        typeof chrome === "undefined" ||
        !chrome.storage ||
        !chrome.storage.local
      ) {
        resolve(DEFAULT_SERVER_BASE_URL);
        return;
      }
      chrome.storage.local.get(
        { [SERVER_BASE_URL_STORAGE_KEY]: DEFAULT_SERVER_BASE_URL },
        (items) => {
          try {
            resolve(normalizeServerBaseUrl(items[SERVER_BASE_URL_STORAGE_KEY]));
          } catch (error) {
            resolve(DEFAULT_SERVER_BASE_URL);
          }
        }
      );
    });
  }

  const api = {
    DEFAULT_SERVER_BASE_URL,
    SERVER_BASE_URL_STORAGE_KEY,
    getServerBaseUrl,
    normalizeServerBaseUrl,
    permissionOrigin
  };
  globalObject.PhishingServerConfig = api;
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api;
  }
})(typeof globalThis !== "undefined" ? globalThis : this);
