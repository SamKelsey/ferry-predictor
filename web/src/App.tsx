import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react'
import mark from './mark.svg'
import { routeFor, routeOn } from './notice'
import { SailingRow } from './SailingRow'
import { ServiceStatus } from './ServiceStatus'
import {
  dayLabel,
  days,
  daysBetween,
  load,
  localDate,
  onRoute,
  type Direction,
  type Port,
  type Predictions,
} from './predictions'

const PORTS: Port[] = ['Troon', 'Ardrossan']
const DIRECTIONS: Direction[] = ['To Brodick', 'From Brodick']
const UNCERTAIN_FROM_DAYS = 3
const EMAIL = 'samjkelsey1@gmail.com'
const COPIED_FOR_MS = 2000
const SERVICE_STATUS = 'https://www.calmac.co.uk/service-status'

export function App() {
  const [predictions, setPredictions] = useState<Predictions | null>(null)
  const [failed, setFailed] = useState(false)
  const [port, setPort] = useState<Port>('Troon')
  const [direction, setDirection] = useState<Direction>('To Brodick')
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
  const [from, to] = direction === 'To Brodick' ? [port, 'Brodick'] : ['Brodick', port]
  const route = routeOn(routeFor(predictions.routes, port), selected)
  const disrupted = route?.status !== undefined && route.status !== 'NORMAL'
  // Notices react to what's happening now, so only today's predictions give way to them.
  const paused = disrupted && ahead === 0

  return (
    <Page>
      <nav className="controls" aria-label="Route">
        <Choice label="Which way?" options={DIRECTIONS} value={direction} onChange={setDirection} />
        <Choice label={direction === 'To Brodick' ? 'Sailing from' : 'Sailing to'} options={PORTS} value={port} onChange={setPort} />
      </nav>

      <h2 className="crossing">
        {from} <span aria-label="to">→</span> {to}
      </h2>

      {route && <ServiceStatus key={`${port}-${selected}`} route={route} today={today} />}

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

      {disrupted && sailings.some((s) => s.status !== 'CANCELLED') && (
        <p className={`disruption-note${paused ? ' paused' : ''}`}>
          <span>{paused ? 'Predictions paused due to disruption' : 'Disruption noted for this day, so double-check'}</span>
          <a href={SERVICE_STATUS}>Check CalMac</a>
        </p>
      )}

      {sailings.length === 0 ? (
        <p className="message">No sailings on this route that day.</p>
      ) : (
        <ol className="sailings" key={`${port}-${direction}-${selected}`}>
          {sailings.map((s, i) => (
            <SailingRow key={s.departs} sailing={s} now={now} index={i} disrupted={paused} />
          ))}
        </ol>
      )}
    </Page>
  )
}

function Page({ children }: { children: ReactNode }) {
  return (
    <main className="page">
      <header className="masthead">
        <p className="wordmark">
          <img src={mark} alt="" width="22" height="22" />
          Ferry Likely
        </p>
        <h1>Will the Arran ferry sail?</h1>
      </header>

      {children}

      <section className="about">
        <h2>Help me make it better</h2>
        <p>
          I built this model after my family moved to Arran and I had to navigate the ferries! It combines weather
          forecasts with CalMac's records of every Arran sailing since 2021. Shoutout to CalMac for sharing such
          fantastic data to build this with!
        </p>
        <p>Spotted a problem, or got something you'd like added? Contribute to the code, or drop me an email.</p>
        <div className="contact">
          <a className="github" href="https://github.com/SamKelsey/ferry-predictor">
            Contribute on GitHub
          </a>
          <CopyEmail />
        </div>
      </section>

      <footer className="small-print">
        <p>
          Not affiliated with CalMac. Always check{' '}
          <a href="https://www.calmac.co.uk/service-status">CalMac's service status</a> before you travel.
        </p>
        <p>
          Weather data by <a href="https://open-meteo.com/">Open-Meteo.com</a> (
          <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>).
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
  const selected = options.indexOf(value)
  return (
    <div className="step" role="group" aria-label={label}>
      <span className="step-label">{label}</span>
      <div className="choice" style={{ '--options': options.length, '--selected': selected } as CSSProperties}>
        <span className="thumb" data-selected={selected} aria-hidden="true" />
        {options.map((option) => (
          <button key={option} aria-pressed={option === value} onClick={() => onChange(option)}>
            {option}
          </button>
        ))}
      </div>
    </div>
  )
}

function CopyEmail() {
  const [copied, setCopied] = useState(false)
  const address = useRef<HTMLSpanElement>(null)

  async function copy() {
    try {
      await navigator.clipboard.writeText(EMAIL)
      setCopied(true)
      setTimeout(() => setCopied(false), COPIED_FOR_MS)
    } catch {
      window.getSelection()?.selectAllChildren(address.current!)
    }
  }

  return (
    <span className="email">
      <span ref={address}>{EMAIL}</span>
      <button onClick={copy}>{copied ? 'Copied!' : 'Copy'}</button>
    </span>
  )
}
