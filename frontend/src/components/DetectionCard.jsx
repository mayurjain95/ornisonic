import React, { useEffect, useState } from "react";
import WaveformSeal from "./WaveformSeal.jsx";
import { getSpeciesImage } from "../species.js";

function shortHash(hash) {
  if (!hash) return "—";
  return `${hash.slice(0, 8)}…${hash.slice(-6)}`;
}

function formatTimestamp(unixSeconds) {
  if (!unixSeconds) return "just now";
  return new Date(unixSeconds * 1000).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  });
}

export default function DetectionCard({ detection, onVerify }) {
  const {
    species,
    scientific_name,
    confidence,
    iucn_status,
    ipfs_cid,
    audio_hash,
    detection_id,
  } = detection;

  const [imageUrl, setImageUrl] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setImageUrl(null);
    getSpeciesImage(species, scientific_name).then((url) => {
      if (!cancelled) setImageUrl(url);
    });
    return () => {
      cancelled = true;
    };
  }, [species, scientific_name]);

  return (
    <div className="card">
      <div className="card-photo">
        {imageUrl ? (
          <img src={imageUrl} alt={species || scientific_name} />
        ) : (
          <div className="card-photo-placeholder">
            <WaveformSeal stored={Boolean(ipfs_cid)} size={40} />
          </div>
        )}
        {imageUrl && (
          <div className="card-photo-badge">
            <WaveformSeal stored={Boolean(ipfs_cid)} size={24} />
          </div>
        )}
      </div>

      <div className="card-top">
        <div className="card-title">
          <h3>{species || scientific_name}</h3>
          <p className="scientific-name">{scientific_name}</p>
        </div>
        <span className={`status-pill status-${(iucn_status || "").toLowerCase()}`}>
          {iucn_status}
        </span>
      </div>

      <dl className="card-data">
        <div>
          <dt>Confidence</dt>
          <dd>{confidence ? `${Math.round(confidence * 100)}%` : "—"}</dd>
        </div>
        <div>
          <dt>Audio hash</dt>
          <dd className="mono">{shortHash(audio_hash)}</dd>
        </div>
        <div>
          <dt>IPFS</dt>
          <dd className="mono">
            {ipfs_cid ? (
              <a
                href={`https://gateway.pinata.cloud/ipfs/${ipfs_cid}`}
                target="_blank"
                rel="noreferrer"
              >
                {shortHash(ipfs_cid)}
              </a>
            ) : (
              "—"
            )}
          </dd>
        </div>
        <div>
          <dt>Recorded</dt>
          <dd>{detection.timestamp ? formatTimestamp(detection.timestamp) : "pending"}</dd>
        </div>
      </dl>

      {typeof detection_id === "number" && (
        <button className="btn-ghost" onClick={() => onVerify(detection_id)}>
          Verify this record
        </button>
      )}
    </div>
  );
}
