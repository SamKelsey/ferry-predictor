import type { CSSProperties } from 'react'
import { FerryDrawing } from './Ferry'
import { ForecastHistory } from './ForecastHistory'
import { localTime, outlook, type Sailing } from './predictions'

type Props = {
  sailing: Sailing
  now: number
  today: string
  index: number
  disrupted: boolean
  /** Whether the visitor turned on Deep dive, which charts how each sailing's forecast has moved. */
  deepDive: boolean
}


export function SailingRow({ sailing, now, today, index, disrupted, deepDive }: Props) {
  const cancelled = sailing.status === 'CANCELLED'
  const passed = !cancelled && Date.parse(sailing.rescheduled_departs ?? sailing.departs) < now
  // On a disrupted day only CalMac can say what sails, including whether a past sailing really left.
  const paused = disrupted && !cancelled
  const departed = passed && !paused
  const chance = sailing.chance_of_sailing
  const state = cancelled ? 'cancelled' : departed ? 'departed' : paused ? 'paused' : chance === null ? 'unknown' : outlook(chance)
  // In Deep dive the chart takes the wave's place, ferry and all, once there's history to chart.
  const charted = deepDive && !paused && (sailing.history?.length ?? 0) > 0

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
            {!charted && (
              <span className="track" aria-hidden="true" style={{ '--chance': `${chance * 100}%` } as CSSProperties}>
                <span className="sea" />
                <span className="fill" />
                <span className="marker">
                  <FerryDrawing width={40} height={22} />
                </span>
                {state === 'likely' && <Celebration />}
              </span>
            )}
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

      {charted && <ForecastHistory sailing={sailing} today={today} index={index} />}
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
