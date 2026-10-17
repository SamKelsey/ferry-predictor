import type { CSSProperties } from 'react'
import { localTime, outlook, type Sailing } from './predictions'

type Props = {
  sailing: Sailing
  now: number
  index: number
}

export function SailingRow({ sailing, now, index }: Props) {
  const cancelled = sailing.status === 'CANCELLED'
  const departed = !cancelled && Date.parse(sailing.rescheduled_departs ?? sailing.departs) < now
  const chance = sailing.chance_of_sailing
  const state = cancelled ? 'cancelled' : departed ? 'departed' : chance === null ? 'unknown' : outlook(chance)

  return (
    <li className={`sailing ${state}`} style={{ '--index': index } as CSSProperties}>
      <div className="times">
        <span className="departs">{localTime(sailing.departs)}</span>
        <span className="arrives">arrives {localTime(sailing.arrives)}</span>
      </div>

      <div className="verdict">
        {cancelled && <span className="headline">Cancelled by CalMac</span>}
        {departed && <span className="headline">Departed</span>}
        {!cancelled && !departed && chance !== null && (
          <>
            <span className="chance">{Math.round(chance * 100)}%</span>
            <span className="reading">
              <span className="meaning">chance it sails</span>
              <span className="headline">Ferry {outlook(chance)}</span>
            </span>
            <span className="track" aria-hidden="true" style={{ '--chance': `${chance * 100}%` } as CSSProperties}>
              <span className="fill" />
              <span className="marker" />
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
        {sailing.gust_knots !== null && !cancelled && !departed && <span>Gusts {sailing.gust_knots} kn</span>}
      </div>
    </li>
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
