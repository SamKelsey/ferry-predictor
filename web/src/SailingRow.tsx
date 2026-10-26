import type { CSSProperties } from 'react'
import { localTime, outlook, type Sailing } from './predictions'

type Props = {
  sailing: Sailing
  now: number
  index: number
  disrupted: boolean
}


export function SailingRow({ sailing, now, index, disrupted }: Props) {
  const cancelled = sailing.status === 'CANCELLED'
  const passed = !cancelled && Date.parse(sailing.rescheduled_departs ?? sailing.departs) < now
  // On a disrupted day only CalMac can say what sails, including whether a past sailing really left.
  const paused = disrupted && !cancelled
  const departed = passed && !paused
  const chance = sailing.chance_of_sailing
  const state = cancelled ? 'cancelled' : departed ? 'departed' : paused ? 'paused' : chance === null ? 'unknown' : outlook(chance)

  return (
    <li className={`sailing ${state}${passed ? ' passed' : ''}`} style={{ '--index': index } as CSSProperties}>
      <div className="times">
        <span className="departs">{localTime(sailing.departs)}</span>
        <span className="arrives">arrives {localTime(sailing.arrives)}</span>
      </div>

      <div className="verdict">
        {cancelled && <span className="headline">Cancelled by CalMac</span>}
        {departed && <span className="headline">Departed</span>}
        {!cancelled && !departed && !paused && chance !== null && (
          <>
            <span className="chance">{Math.round(chance * 100)}%</span>
            <span className="reading">
              <span className="meaning">chance it sails</span>
              <span className="headline">Ferry {outlook(chance)}</span>
            </span>
            <span className="track" aria-hidden="true" style={{ '--chance': `${chance * 100}%` } as CSSProperties}>
              <span className="sea" />
              <span className="fill" />
              <Ferry />
              {state === 'likely' && <Celebration />}
            </span>
          </>
        )}
      </div>

      <div className="notes">
        {sailing.status === 'DELAYED' && sailing.rescheduled_departs && (
          <span className="status">Delayed to {localTime(sailing.rescheduled_departs)}</span>
        )}
        {!['SCHEDULED', 'CANCELLED', 'DELAYED'].includes(sailing.status) && (
          <span className="status">CalMac: {sailing.status.toLowerCase().replaceAll('_', ' ')}</span>
        )}
        {sailing.gust_knots !== null && !cancelled && !departed && !paused && <span>Gusts {sailing.gust_knots} kn</span>}
      </div>
    </li>
  )
}

/** A little ferry in CalMac's colours: black hull with a red waterline, white decks and a red funnel with a yellow disc. */
function Ferry() {
  return (
    <span className="marker">
      <svg viewBox="0 0 52 28" width="40" height="22" aria-hidden="true">
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
    </span>
  )
}

const CONFETTI_PIECES = 10

function Celebration() {
  return (
    <span className="celebration">
      {Array.from({ length: CONFETTI_PIECES }, (_, piece) => (
        <span key={piece} className="confetti" style={{ '--piece': piece } as CSSProperties} />
      ))}
      <span className="toot">toot toot!</span>
    </span>
  )
}
