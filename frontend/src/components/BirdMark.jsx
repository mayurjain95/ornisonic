import React from "react";

/**
 * Hero illustration: a perched songbird mid-call, rendered in the same
 * thin-stroke line-art language as WaveformSeal (amber body, teal song rings).
 */
export default function BirdMark({ size = 220 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 220 220"
      role="img"
      aria-label="Songbird illustration"
    >
      {/* song rings */}
      <g stroke="var(--teal)" strokeOpacity="0.55" fill="none" strokeDasharray="2 5">
        <path d="M150 70 Q170 62 184 70" strokeWidth="1.5" />
        <path d="M150 58 Q178 45 198 58" strokeWidth="1.5" />
        <path d="M150 46 Q186 28 212 46" strokeWidth="1.5" />
      </g>

      {/* branch */}
      <path
        d="M18 178 Q80 168 120 178 T210 172"
        fill="none"
        stroke="var(--surface-raised)"
        strokeWidth="5"
        strokeLinecap="round"
      />

      {/* tail */}
      <path
        d="M62 138 L26 152 L64 150 Z"
        fill="var(--surface)"
        stroke="var(--amber)"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />

      {/* body */}
      <path
        d="M64 150
           C58 118 76 88 112 82
           C148 76 172 96 174 122
           C176 146 156 168 126 172
           C96 176 68 172 64 150 Z"
        fill="var(--surface)"
        stroke="var(--amber)"
        strokeWidth="1.75"
      />

      {/* wing */}
      <path
        d="M86 128 C104 118 130 118 150 132 C132 140 108 142 88 138 Z"
        fill="var(--surface-raised)"
        stroke="var(--amber)"
        strokeWidth="1.25"
        opacity="0.9"
      />

      {/* head */}
      <circle cx="150" cy="96" r="26" fill="var(--surface)" stroke="var(--amber)" strokeWidth="1.75" />

      {/* beak */}
      <path d="M174 92 L192 88 L174 102 Z" fill="var(--teal)" stroke="var(--teal)" strokeWidth="1" strokeLinejoin="round" />

      {/* eye */}
      <circle cx="156" cy="90" r="2.6" fill="var(--bone)" />

      {/* legs */}
      <path d="M112 172 L108 182 M108 182 L102 180 M108 182 L112 186" stroke="var(--amber)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
      <path d="M140 172 L142 183 M142 183 L136 182 M142 183 L146 187" stroke="var(--amber)" strokeWidth="1.5" fill="none" strokeLinecap="round" />
    </svg>
  );
}
