import React, { useState } from "react";
import { verifyDetection } from "../api.js";
import { describe, explorerUrl } from "../verifyResult.js";

const ICONS = { pass: "✓", fail: "✗", warn: "!" };

export default function VerifyPanel({ detectionId, onClose }) {
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);

  async function handleFile(e) {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setResult(null);
    try {
      const { ok, status, body } = await verifyDetection(detectionId, file);
      if (body && "verified" in body) {
        setResult({ kind: "verdict", verified: body.verified, body });
      } else {
        // Rate limited, too large, unknown id...: not a verdict on the audio.
        setResult({ kind: "refused", text: body?.detail || `Request failed (${status}).` });
      }
    } catch {
      setResult({ kind: "refused", text: "Verification request failed." });
    } finally {
      setBusy(false);
      e.target.value = "";
    }
  }

  const verdict = result?.kind === "verdict" ? describe(result.body) : null;
  const explorer = verdict && result.body.onchain?.checked ? explorerUrl(result.body.onchain) : null;

  return (
    <div className="verify-overlay" role="dialog" aria-label="Verify detection">
      <div className="verify-panel">
        <button className="btn-close" onClick={onClose} aria-label="Close">
          ×
        </button>
        <h3>Verify detection #{detectionId}</h3>
        <p>Upload the original audio file to check it against the stored and on-chain records.</p>

        <label className="upload-drop small">
          <input type="file" accept="audio/*" onChange={handleFile} disabled={busy} hidden />
          <span>{busy ? "Checking…" : "Choose audio file"}</span>
        </label>

        {verdict && (
          <div className={`result ${result.verified ? "result-match" : "result-mismatch"}`}>
            <p className="verify-headline">{verdict.headline}</p>
            <ul className="verify-checks">
              {verdict.checks.map((c) => (
                <li key={c.text} className={`check-${c.status}`}>
                  <span aria-hidden="true">{ICONS[c.status]}</span> {c.text}
                </li>
              ))}
            </ul>
            {explorer && (
              <a className="verify-explorer" href={explorer} target="_blank" rel="noreferrer">
                View the contract on Polygonscan ↗
              </a>
            )}
          </div>
        )}
        {result?.kind === "refused" && <p className="result result-mismatch">{result.text}</p>}
      </div>
    </div>
  );
}
