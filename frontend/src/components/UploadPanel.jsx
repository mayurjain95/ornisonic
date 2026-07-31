import React, { useState } from "react";
import { uploadAudio } from "../api.js";
import { getSpeciesImage } from "../species.js";

function iucnSearchUrl(scientificName) {
  return `https://www.iucnredlist.org/search?query=${encodeURIComponent(scientificName)}&searchType=species`;
}

export default function UploadPanel({ onResult }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState(null);
  const [bestGuess, setBestGuess] = useState(null);
  const [bestGuessImage, setBestGuessImage] = useState(null);
  const [isDragging, setIsDragging] = useState(false);

  async function processFile(file) {
    if (!file) return;

    setBusy(true);
    setMessage(null);
    setBestGuess(null);
    setBestGuessImage(null);
    try {
      const result = await uploadAudio(file);
      if (result.status === "no_endangered_species_detected") {
        setMessage("No watchlist match — Ornisonic only flags species on the IUCN endangered list.");
        const guess = result.best_guess || null;
        setBestGuess(guess);
        if (guess) {
          getSpeciesImage(guess.species, guess.scientific_name).then(setBestGuessImage);
        }
      } else {
        setMessage(`Stored ${result.matches.length} detection(s).`);
        onResult(result.matches);
      }
    } catch (err) {
      setMessage(`Upload failed: ${err.message}`);
    } finally {
      setBusy(false);
    }
  }

  function handleInputChange(e) {
    const file = e.target.files?.[0];
    processFile(file);
    e.target.value = "";
  }

  function handleDragOver(e) {
    e.preventDefault();
    if (!busy) setIsDragging(true);
  }

  function handleDragLeave(e) {
    e.preventDefault();
    setIsDragging(false);
  }

  function handleDrop(e) {
    e.preventDefault();
    setIsDragging(false);
    if (busy) return;
    const file = e.dataTransfer.files?.[0];
    processFile(file);
  }

  return (
    <div className="upload-panel">
      <label
        className={`upload-drop${isDragging ? " dragging" : ""}`}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
      >
        <input type="file" accept="audio/*" onChange={handleInputChange} disabled={busy} hidden />
        <span>{busy ? "Analyzing clip…" : "Drop a field recording, or click to choose one"}</span>
      </label>
      <p className="upload-hint">
        Only matches against the IUCN endangered watchlist — common species won't return a result.
      </p>
      {message && <p className="upload-message">{message}</p>}
      {bestGuess && (
        <div className="upload-guess">
          {bestGuessImage ? (
            <img className="upload-guess-thumb" src={bestGuessImage} alt={bestGuess.species} />
          ) : (
            <span className="upload-guess-thumb upload-guess-thumb-empty" aria-hidden="true" />
          )}
          <p>
            Closest predicted match: <em>{bestGuess.species}</em> (
            {Math.round(bestGuess.confidence * 100)}% confidence) —{" "}
            <a href={iucnSearchUrl(bestGuess.scientific_name)} target="_blank" rel="noreferrer">
              check its IUCN status
            </a>
          </p>
        </div>
      )}
    </div>
  );
}
