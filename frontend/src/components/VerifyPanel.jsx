import React, { useState } from "react";
import { verifyDetection } from "../api.js";

export default function VerifyPanel({ detectionId, onClose }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [limitMessage, setLimitMessage] = useState(null);

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const { ok, status, body } = await verifyDetection(detectionId, file);
      if (status === 429 || status === 413) {
        // Rate limited or file too large: not a verdict on the audio.
        setLimitMessage(body?.detail || "Request refused; please try again later.");
        setResult("limited");
      } else {
        setResult(ok ? "match" : "mismatch");
      }
    } catch {
      setResult("error");
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  return (
    <div className="verify-overlay" role="dialog" aria-label="Verify detection">
      <div className="verify-panel">
        <button className="btn-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <h3>Verify detection #{detectionId}</h3>
        <p>Upload the original audio file to check it against the stored record.</p>

        <label className="upload-drop small">
          <input type="file" accept="audio/*" onChange={handleFile} disabled={busy} hidden />
          <span>{busy ? "Checking…" : "Choose audio file"}</span>
        </label>

        {result === "match" && <p className="result result-match">Verified — hash matches stored record.</p>}
        {result === "mismatch" && (
          <p className="result result-mismatch">No match — this file does not match the stored record.</p>
        )}
        {result === "limited" && <p className="result result-mismatch">{limitMessage}</p>}
        {result === "error" && <p className="result result-mismatch">Verification request failed.</p>}
      </div>
    </div>
  );
}
