import { useEffect, useRef, type CSSProperties } from 'react'
import { FerryDrawing } from './Ferry'
import { chartRange, dailyPercentiles, type Sailing } from './predictions'

const weekday = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', weekday: 'short' })
const dayOfMonth = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', day: 'numeric' })
const SAIL_MS = 1800
/** The share of the sail spent following the middle line; the rest is the hop to today's forecast. */
const ALONG_THE_LINE = 0.85

type Props = {
  sailing: Sailing
  today: string
  /** The sailing's place in the list, so the charts draw one after another. */
  index: number
}

/**
 * How a sailing's forecast has moved, day by day: the middle of each day's hourly forecasts as a line, the 10th and 90th
 * percentiles as thinner lines with the band between them shaded, and the ferry at today's forecast. When it appears, the lines
 * draw from left to right as the ferry sails along the middle one. The chart zooms to the range the forecasts used. The SVG
 * stretches to fit, so its strokes don't scale and the ferry is drawn over it in HTML.
 */
export function ForecastHistory({ sailing, today, index }: Props) {
  const plot = useRef<HTMLSpanElement>(null)
  const ferry = useRef<HTMLSpanElement>(null)
  const days = dailyPercentiles(sailing.history ?? [])
  const now = sailing.chance_of_sailing
  const [low, high] = chartRange([...days.flatMap((d) => [d.p10, d.p90]), ...(now === null ? [] : [now])])
  // A single day still draws as a short level line across the middle of the chart.
  const xs = days.length === 1 ? [0, 1] : days.map((_, i) => i)
  const x = (i: number) => (days.length === 1 ? [25, 75][i] : ((i + 0.5) / days.length) * 100)
  const at = (i: number) => days[Math.min(i, days.length - 1)]
  const y = (chance: number) => ((high - chance) / (high - low)) * 100
  const line = (key: 'p10' | 'p50' | 'p90') => xs.map((i, n) => `${n ? 'L' : 'M'}${x(i)} ${y(at(i)[key])}`).join(' ')
  const band = `${line('p90')} ${[...xs].reverse().map((i) => `L${x(i)} ${y(at(i).p10)}`).join(' ')} Z`
  const middle = xs.map((i) => ({ left: x(i), top: y(at(i).p50) }))
  const end = { left: x(xs[xs.length - 1]), top: y(now ?? at(xs[xs.length - 1]).p50) }

  useEffect(() => {
    if (!plot.current || !ferry.current || matchMedia('(prefers-reduced-motion: reduce)').matches) return
    const timing = { duration: SAIL_MS, delay: index * 45 + 150, easing: 'linear', fill: 'backwards' } as const
    const reveal = plot.current.animate([
      { clipPath: `inset(-30% ${100 - middle[0].left}% -30% 0)` },
      { clipPath: `inset(-30% ${100 - end.left - 2}% -30% 0)`, offset: ALONG_THE_LINE },
      { clipPath: 'inset(-30% 0 -30% 0)' },
    ], timing)
    const sail = ferry.current.animate([
      ...middle.map((p, n) => ({ left: `${p.left}%`, top: `${p.top}%`, offset: (ALONG_THE_LINE * n) / (middle.length - 1) })),
      { left: `${end.left}%`, top: `${end.top}%`, offset: 1 },
    ], timing)
    return () => {
      reveal.cancel()
      sail.cancel()
    }
  }, [sailing.departs, index])

  if (days.length === 0) return null
  const first = days[0]
  const last = days[days.length - 1]
  const summary = `The typical forecast went from ${percent(first.p50)} on ${label(first.date, today)} to ${percent(last.p50)} ${label(last.date, today).toLowerCase()}`

  return (
    <figure className="history">
      <span className="history-axis" aria-hidden="true">
        <span>{percent(high)}</span>
        <span>{percent((low + high) / 2)}</span>
        <span>{percent(low)}</span>
      </span>
      <span className="history-plot">
        <svg className="history-grid" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
          {[0, 50, 100].map((g) => <line key={g} x1={0} x2={100} y1={g} y2={g} />)}
        </svg>
        <span className="history-lines" ref={plot}>
          <svg viewBox="0 0 100 100" preserveAspectRatio="none" role="img" aria-label={summary}>
            <path className="history-band" d={band} />
            <path className="history-edge" d={line('p90')} />
            <path className="history-edge" d={line('p10')} />
            <path className="history-middle" d={line('p50')} />
          </svg>
        </span>
        {now !== null && (
          <span className="history-ferry" ref={ferry} style={{ left: `${end.left}%`, top: `${end.top}%` } as CSSProperties}>
            <FerryDrawing width={34} height={19} />
          </span>
        )}
      </span>
      <span className="history-days" aria-hidden="true">
        {days.map((day) => (
          <span key={day.date} className={day.date === today ? 'today' : undefined}>
            {day.date === today ? 'Today' : <>{weekday.format(new Date(day.date))}<br />{dayOfMonth.format(new Date(day.date))}</>}
          </span>
        ))}
      </span>
    </figure>
  )
}

function label(date: string, today: string): string {
  return date === today ? 'Today' : weekday.format(new Date(date))
}

function percent(chance: number): string {
  return `${Math.round(chance * 100)}%`
}
