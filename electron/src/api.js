const API_BASE_URL = import.meta.env.VITE_FLOATVOCAB_API_URL || "http://127.0.0.1:8000";

async function request(path, options = {}) {
  let response;
  let lastError;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    try {
      response = await fetch(`${API_BASE_URL}${path}`, {
        headers: {
          "Content-Type": "application/json",
          ...(options.headers || {}),
        },
        ...options,
      });
      break;
    } catch (error) {
      lastError = error;
      await new Promise((resolve) => setTimeout(resolve, 250 * (attempt + 1)));
    }
  }
  if (!response) {
    throw lastError || new Error("Failed to fetch");
  }
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed: ${response.status}`);
  }
  if (response.status === 204) {
    return null;
  }
  return response.json();
}

export const api = {
  health: () => request("/health"),
  plan: () => request("/plan"),
  savePlan: (payload) => request("/plan", { method: "PUT", body: JSON.stringify(payload) }),
  saveFloatStyle: (payload) => request("/plan/float-style", { method: "PUT", body: JSON.stringify(payload) }),
  setGlobalTranslation: (enabled) =>
    request("/plan/global-translation", { method: "PUT", body: JSON.stringify({ enabled }) }),
  profile: () => request("/profile"),
  saveProfile: (payload) => request("/profile", { method: "PUT", body: JSON.stringify(payload) }),
  appSettings: () => request("/app-settings"),
  saveAppSettings: (payload) => request("/app-settings", { method: "PUT", body: JSON.stringify(payload) }),
  cloudConfig: () => request("/cloud/config"),
  cloudSession: () => request("/cloud/session"),
  cloudSignup: (payload) => request("/cloud/signup", { method: "POST", body: JSON.stringify(payload) }),
  cloudLogin: (payload) => request("/cloud/login", { method: "POST", body: JSON.stringify(payload) }),
  cloudLogout: () => request("/cloud/logout", { method: "POST" }),
  cloudSyncStatus: () => request("/cloud/sync/status"),
  cloudSyncUpload: () => request("/cloud/sync/upload", { method: "POST" }),
  cloudSyncDownload: () => request("/cloud/sync/download", { method: "POST" }),
  languages: () => request("/languages"),
  lexicons: (languageCode) => request(`/lexicons${languageCode ? `?language_code=${encodeURIComponent(languageCode)}` : ""}`),
  nextCard: () => request("/cards/next"),
  review: (wordId, rating) => request("/reviews", { method: "POST", body: JSON.stringify({ word_id: wordId, rating }) }),
  stats: () => request("/stats"),
  recentWords: (lexiconId, limit = 80) => request(`/words/recent?lexicon_id=${encodeURIComponent(lexiconId)}&limit=${limit}`),
  latestNews: (languageCode, limit = 10) =>
    request(`/news/latest?limit=${limit}${languageCode ? `&language_code=${languageCode}` : ""}`),
  refreshNews: (languageCode, limit = 10) =>
    request(`/news/latest/refresh?limit=${limit}${languageCode ? `&language_code=${languageCode}` : ""}`, { method: "POST" }),
  favorites: (languageCode) => request(`/news/favorites${languageCode ? `?language_code=${languageCode}` : ""}`),
};
