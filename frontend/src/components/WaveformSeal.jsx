import React from "react";

/**
 * Signature element: a waveform rendered as a seal outline.
 * Dashed amber while pending, solid teal fill once stored.
 */
export default function WaveformSeal({ stored = true, size = 56 }) {
  // Deterministic-looking pseudo waveform bars
  const bars = [4, 9, 14, 8, 18, 11, 6, 15, 10, 5, 13, 7];

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      role="img"
      aria-label={stored ? "Verified" : "Pending storage"}
    >
      <circle
        cx="28"
        cy="28"
        r="25"
        fill={stored ? "var(--teal)" : "none"}
        fillOpacity={stored ? 0.12 : 0}
        stroke={stored ? "var(--teal)" : "var(--amber)"}
        strokeWidth="1.5"
        strokeDasharray={stored ? "none" : "3 3"}
      />
      {bars.map((h, i) => {
        const x = 10 + i * 3;
        const y = 28 - h / 2;
        return (
          <rect
            key={i}
            x={x}
            y={y}
            width="1.6"
            height={h}
            rx="0.8"
            fill={stored ? "var(--teal)" : "var(--amber)"}
          />
        );
      })}
    </svg>
  );
}
