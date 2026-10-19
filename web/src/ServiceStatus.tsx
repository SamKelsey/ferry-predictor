import { label, paragraphs, type Route } from './notice'
import { dayLabel, localDate, localTime } from './predictions'

type Props = {
  route: Route
  today: string
}

export function ServiceStatus({ route, today }: Props) {
  return (
    <section className={`service-status ${route.status.toLowerCase().replaceAll('_', '-')}`} aria-label="CalMac service status">
      <p className="service-line">
        <span className="badge">{label(route.status)}</span>
        <span className="service-source">per CalMac</span>
      </p>

      {route.notices.map((n) => (
        <details key={`${n.title}-${n.updated_at}`} className="notice">
          <summary>
            <span className="notice-title">{n.title}</span>
            <span className="notice-meta">
              {n.reason && <>{n.reason} · </>}
              updated {updated(n.updated_at, today)}
            </span>
          </summary>
          {paragraphs(n.detail).map((p, i) => (
            <p key={i}>
              {p.map((s, j) =>
                s.href ? (
                  <a key={j} href={s.href}>
                    {s.text}
                  </a>
                ) : s.bold ? (
                  <strong key={j}>{s.text}</strong>
                ) : (
                  s.text
                ),
              )}
            </p>
          ))}
        </details>
      ))}
    </section>
  )
}

function updated(instant: string, today: string): string {
  const day = localDate(instant)
  return day === today ? localTime(instant) : `${dayLabel(day, today)} ${localTime(instant)}`
}
