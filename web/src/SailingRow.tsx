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

function Ferry() {
  return (
    <span className="marker">
      <svg viewBox="0 0 30 18" width="38" height="23" aria-hidden="true">
        <rect className="funnel" x="9" y="1" width="3.5" height="5.5" rx="0.8" />
        <rect x="14.5" y="3" width="7" height="4" rx="1" />
        <rect x="5.5" y="6" width="17" height="4.5" rx="1" />
        <path d="M1 10 H29 L25.5 16 H4 Z" />
        <g className="windows">
          <rect x="8" y="7.6" width="2" height="1.4" rx="0.4" />
          <rect x="11.5" y="7.6" width="2" height="1.4" rx="0.4" />
          <rect x="15" y="7.6" width="2" height="1.4" rx="0.4" />
          <rect x="18.5" y="7.6" width="2" height="1.4" rx="0.4" />
        </g>
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
