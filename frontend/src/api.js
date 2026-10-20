// Dev: "/api", proxied to the local backend by vite.config.js.
// Production builds: the Cloud Run URL from frontend/.env.production.
const BASE = import.meta.env.VITE_API_BASE ?? "/api";

export async function uploadAudio(file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/upload`, { method: "POST", body: form });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || `server returned ${res.status}`);
  }
  return res.json();
}

export async function fetchDetections() {
  const res = await fetch(`${BASE}/detections`);
  if (!res.ok) throw new Error(`Failed to load detections: ${res.status}`);
  return res.json();
}

export async function verifyDetection(id, file) {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${BASE}/verify/${id}`, { method: "POST", body: form });
  return { ok: res.ok, status: res.status, body: await res.json().catch(() => null) };
}
