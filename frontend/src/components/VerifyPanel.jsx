import React, { useState } from "react";
import { verifyDetection } from "../api.js";

export default function VerifyPanel({ detectionId, onClose }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const { ok, body } = await verifyDetection(detectionId, file);
      setResult(ok ? "match" : "mismatch");
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
        {result === "error" && <p className="result result-mismatch">Verification request failed.</p>}
      </div>
    </div>
  );
}
