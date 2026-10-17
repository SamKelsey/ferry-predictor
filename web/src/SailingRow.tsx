import type { CSSProperties } from 'react'
import { localTime, outlook, type Outlook, type Sailing } from './predictions'

const OUTLOOK_WORDS: Record<Outlook, string> = {
  likely: 'Ferry likely',
  'some-risk': 'Ferry hopeful',
  'at-risk': 'Ferry doubtful',
  unlikely: 'Ferry unlikely',
}

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
            <span className="headline">{OUTLOOK_WORDS[outlook(chance)]}</span>
            <span className="track" aria-hidden="true">
              <span className="marker" style={{ left: `${chance * 100}%` }} />
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
