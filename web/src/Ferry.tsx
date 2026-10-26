/** A little ferry in CalMac's colours: black hull with a red waterline, white decks and a red funnel with a yellow disc. */
export function FerryDrawing({ width, height }: { width: number; height: number }) {
  return (
    <svg className="ferry" viewBox="0 0 52 28" width={width} height={height} aria-hidden="true">
      <g className="smoke">
        <circle cx="21" cy="0.5" r="1.8" />
        <circle cx="17.2" cy="-1.2" r="1.3" />
        <circle cx="14.2" cy="-2.4" r="0.9" />
      </g>
      <g className="outline">
        <path className="hull" d="M2 17 H49.5 L47 23.6 Q46.5 25 45 25 H6 Q4 25 3.4 23.6 Z" />
        <path className="decks" d="M7.5 17 V12 Q7.5 10.6 9 10.6 H38.5 L42.5 14 V17 Z" />
        <path className="decks" d="M16.5 10.6 V8.2 Q16.5 7 17.7 7 H35.5 L38.6 10.6 Z" />
        <path className="funnel" d="M20.6 7 L21.4 1.6 H26.4 L27 7 Z" />
      </g>
      <path className="waterline" d="M3.6 23.4 H46.6 L46.2 24.3 Q45.8 25 45 25 H6 Q4.6 25 3.9 24.2 Z" />
      <rect className="funnel-top" x="21.35" y="1.6" width="5.1" height="1.7" />
      <circle className="disc" cx="23.9" cy="4.9" r="1.35" />
      <circle className="lion" cx="23.9" cy="4.9" r="0.55" />
      <g className="windows">
        {[10, 13, 16, 19, 22, 25, 28, 31, 34].map((x) => <rect key={x} x={x} y="12.9" width="1.8" height="1.4" rx="0.4" />)}
        <path d="M31 8.2 H35.6 L36.7 9.5 H31 Z" />
      </g>
      <path className="mast" d="M33.5 7 V3.2" />
    </svg>
  )
}
