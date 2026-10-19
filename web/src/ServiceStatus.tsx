import { label, paragraphs, type Route } from './notice'
import { dayLabel, localDate, localTime } from './predictions'

type Props = {
  route: Route
  today: string
}

export function ServiceStatus({ route, today }: Props) {
  const [lead] = route.notices
  if (!lead) return null

  return (
    <details className={`service-status ${route.status.toLowerCase().replaceAll('_', '-')}`}>
      <summary>
        <span className="dot" aria-hidden="true" />
        <span className="service-label">{label(route.status)}</span>
        {lead.reason && <span className="service-reason">{lead.reason}</span>}
        <span className="chevron" aria-hidden="true" />
      </summary>

      <div className="notices">
        {route.notices.map((n) => (
          <article key={`${n.title}-${n.updated_at}`} className="notice">
            <h3>
              {n.title}
              <span>Updated {updated(n.updated_at, today)}</span>
            </h3>
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
          </article>
        ))}
      </div>
    </details>
  )
}

function updated(instant: string, today: string): string {
  const day = localDate(instant)
  return day === today ? localTime(instant) : `${dayLabel(day, today)} ${localTime(instant)}`
}
