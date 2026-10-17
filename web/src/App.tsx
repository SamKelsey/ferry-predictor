import { useEffect, useState, type ReactNode } from 'react'
import { SailingRow } from './SailingRow'
import {
  dayLabel,
  days,
  daysBetween,
  load,
  localDate,
  localTime,
  onRoute,
  type Direction,
  type Port,
  type Predictions,
} from './predictions'

const PORTS: Port[] = ['Troon', 'Ardrossan']
const DIRECTIONS: Direction[] = ['To Arran', 'From Arran']
const UNCERTAIN_FROM_DAYS = 3

export function App() {
  const [predictions, setPredictions] = useState<Predictions | null>(null)
  const [failed, setFailed] = useState(false)
  const [port, setPort] = useState<Port>('Troon')
  const [direction, setDirection] = useState<Direction>('To Arran')
  const [day, setDay] = useState<string | null>(null)

  useEffect(() => {
    load().then(setPredictions, () => setFailed(true))
  }, [])

  if (failed) {
    return <Page><p className="message">The forecast couldn't be loaded. Try again in a few minutes.</p></Page>
  }
  if (!predictions) {
    return <Page><p className="message">Loading the forecast…</p></Page>
  }

  const now = Date.now()
  const today = localDate(new Date(now))
  const available = days(predictions.sailings)
  const selected = day !== null && available.includes(day) ? day : available[0]
  const ahead = daysBetween(today, selected)
  const sailings = predictions.sailings.filter((s) => onRoute(s, port, direction) && localDate(s.departs) === selected)
  const [from, to] = direction === 'To Arran' ? [port, 'Brodick'] : ['Brodick', port]

  return (
    <Page updated={predictions.generated_at}>
      <nav className="controls" aria-label="Route">
        <Choice label="Which way?" options={DIRECTIONS} value={direction} onChange={setDirection} />
        <Choice label={direction === 'To Arran' ? 'Sailing from' : 'Sailing to'} options={PORTS} value={port} onChange={setPort} />
      </nav>

      <h2 className="crossing">
        {from} <span aria-label="to">→</span> {to}
      </h2>

      <nav className="days" aria-label="Day">
        {available.map((d) => (
          <button key={d} aria-pressed={d === selected} onClick={() => setDay(d)}>
            {dayLabel(d, today)}
          </button>
        ))}
      </nav>

      {ahead >= UNCERTAIN_FROM_DAYS && (
        <p className="caution">This is {ahead} days away, so the weather could still change a lot. Check back nearer the day.</p>
      )}

      {sailings.length === 0 ? (
        <p className="message">No sailings on this route that day.</p>
      ) : (
        <>
          <div className="scale" aria-hidden="true">
            <span>Ferry unlikely</span>
            <span>Ferry likely</span>
          </div>
          <ol className="sailings" key={`${port}-${direction}-${selected}`}>
            {sailings.map((s, i) => (
              <SailingRow key={s.departs} sailing={s} now={now} index={i} />
            ))}
          </ol>
        </>
      )}
    </Page>
  )
}

function Page({ children, updated }: { children: ReactNode; updated?: string }) {
  return (
    <main className="page">
      <header className="masthead">
        <p className="eyebrow">Unofficial forecast · Firth of Clyde</p>
        <h1>Will the Arran ferry sail?</h1>
      </header>

      {children}

      <footer className="small-print">
        <p>
          Not affiliated with CalMac. Always check{' '}
          <a href="https://www.calmac.co.uk/service-status">CalMac's service status</a> before you travel.
        </p>
        <p>
          Chances come from a model trained on CalMac's records of past sailings and the weather forecasts made at
          the time. It can't foresee breakdowns or crew shortages.
        </p>
        <p>
          Weather forecast by <a href="https://open-meteo.com/">Open-Meteo.com</a>, licensed under{' '}
          <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>.
          {updated && <> Updated at {localTime(updated)}.</>}{' '}
          <a href="https://github.com/SamKelsey/ferry-predictor">Source</a>.
        </p>
      </footer>
    </main>
  )
}

type ChoiceProps<T extends string> = {
  label: string
  options: T[]
  value: T
  onChange: (value: T) => void
}

function Choice<T extends string>({ label, options, value, onChange }: ChoiceProps<T>) {
  return (
    <div className="step" role="group" aria-label={label}>
      <span className="step-label">{label}</span>
      <div className="choice">
        {options.map((option) => (
          <button key={option} aria-pressed={option === value} onClick={() => onChange(option)}>
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}
