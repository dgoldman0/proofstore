// api.js
//
// Simple wrapper around fetch for the proofstore Flask API. All methods
// return parsed JSON and throw errors for non‑OK responses.

const API_BASE = "/api";

async function api(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });

  // Read raw text first so we can handle empty bodies safely.
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;

  if (!res.ok) {
    // Prefer server-provided error if present
    const msg =
      (data && data.error) ||
      `${res.status} ${res.statusText}` +
        (text ? ` — ${text.slice(0, 300)}` : "");
    throw new Error(msg);
  }

  return data;
}
// -------- Elements --------

export function listElements(params = {}) {
  const q = new URLSearchParams(params).toString();
  return api(`/elements${q ? '?' + q : ''}`);
}

export function getElement(id) {
  return api(`/elements/${id}`);
}

export function createElement(payload) {
  return api('/elements', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export const updateElement = (id, payload) =>
  api(`/elements/${id}`, { method: "PATCH", body: JSON.stringify(payload) });
export function deleteElement(id) {
  return api(`/elements/${id}`, { method: 'DELETE' });
}

// -------- Tags --------

export function setTags(id, tags) {
  return api(`/elements/${id}/tags`, {
    method: 'PUT',
    body: JSON.stringify({ tags }),
  });
}

// -------- Links --------

export function listLinksForElement(id) {
  return api(`/elements/${id}/links`);
}

export function createLink(payload) {
  return api('/links', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
