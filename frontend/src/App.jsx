import React, { useEffect, useState, useCallback } from "react";
import UploadPanel from "./components/UploadPanel.jsx";
import DetectionCard from "./components/DetectionCard.jsx";
import VerifyPanel from "./components/VerifyPanel.jsx";
import BirdMark from "./components/BirdMark.jsx";
import { fetchDetections } from "./api.js";
import "./App.css";

export default function App() {
  const [detections, setDetections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [verifyingId, setVerifyingId] = useState(null);

  const load = useCallback(async () => {
    try {
      const data = await fetchDetections();
      setDetections(data.detections || []);
      setError(null);
    } catch (err) {
      setError("Could not reach the backend. Is it running on port 8000?");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function handleNewMatches(matches) {
    setDetections((prev) => [...matches, ...prev]);
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="hero-glow" aria-hidden="true" />
        <div className="hero-text">
          <p className="eyebrow">Field verification network</p>
          <h1>Ornisonic</h1>
          <p className="subhead">
            Endangered-species audio detections, hashed and stored the moment
            they happen — so anyone can re-verify the original recording later.
          </p>
        </div>
        <div className="hero-bird" aria-hidden="true">
          <BirdMark size={220} />
        </div>
      </header>

      <UploadPanel onResult={handleNewMatches} />

      <main className="feed">
        {loading && <p className="feed-status">Loading detections…</p>}
        {error && <p className="feed-status error">{error}</p>}
        {!loading && !error && detections.length === 0 && (
          <p className="feed-status">No detections stored yet. Upload a clip to get started.</p>
        )}
        <div className="feed-grid">
          {detections.map((d, i) => (
            <DetectionCard
              key={d.detection_id ?? `${d.scientific_name}-${i}`}
              detection={d}
              onVerify={setVerifyingId}
            />
          ))}
        </div>
      </main>

      {verifyingId !== null && (
        <VerifyPanel detectionId={verifyingId} onClose={() => setVerifyingId(null)} />
      )}
    </div>
  );
}
