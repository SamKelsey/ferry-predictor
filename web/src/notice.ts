import { localDate, type Port } from './predictions'

export type RouteStatus = 'NORMAL' | 'BE_AWARE' | 'DISRUPTIONS' | 'ALL_SAILINGS_CANCELLED'

export type Notice = {
  title: string
  status: RouteStatus
  reason: string | null
  starts: string
  ends: string
  updated_at: string
  detail: string
}

export type Route = {
  route: 'ARD' | 'TRO'
  status: RouteStatus
  notices: Notice[]
}

export type Span = { text: string; bold?: boolean; href?: string }

const ORDER: RouteStatus[] = ['NORMAL', 'BE_AWARE', 'DISRUPTIONS', 'ALL_SAILINGS_CANCELLED']
const SEVERE = ORDER.slice(2)

const ROUTES: Record<Port, Route['route']> = { Ardrossan: 'ARD', Troon: 'TRO' }

const LABELS: Record<RouteStatus, string> = {
  NORMAL: 'Sailing as normal',
  BE_AWARE: 'Be aware',
  DISRUPTIONS: 'Disruptions',
  ALL_SAILINGS_CANCELLED: 'All sailings cancelled',
}

// Bold text, inline links, and reference-style links whose targets CalMac doesn't send.
const INLINE = /\*\*(.+?)\*\*|\[([^\]]+)\]\(([^)\s]+)\)|\[([^\]]+)\]\[[^\]]*\]/g

export function routeFor(routes: Route[] | undefined, port: Port): Route | undefined {
  return routes?.find((r) => r.route === ROUTES[port])
}

/**
 * The route as it stands on one UK date: the disruption notices covering that day, and the worst of their statuses.
 * Be-aware notices are left out, as they often run for months about things like timetable changes.
 */
export function routeOn(route: Route | undefined, day: string): Route | undefined {
  if (!route) return undefined
  const notices = route.notices.filter(
    (n) => SEVERE.includes(n.status) && localDate(n.starts) <= day && day <= localDate(Date.parse(n.ends) - 1),
  )
  const status = notices.reduce<RouteStatus>((worst, n) => (ORDER.indexOf(n.status) > ORDER.indexOf(worst) ? n.status : worst), 'NORMAL')
  return { ...route, status, notices }
}

export function label(status: RouteStatus): string {
  return LABELS[status]
}

/** CalMac's Markdown notice as paragraphs of plain, bold and linked spans. */
export function paragraphs(detail: string): Span[][] {
  return detail
    .replaceAll('\r', '')
    .split(/\n\s*\n/)
    .map((p) => p.replace(/\s*\n\s*/g, ' ').trim())
    .filter(Boolean)
    .map(spans)
}

function spans(text: string): Span[] {
  const found: Span[] = []
  let at = 0
  for (const match of text.matchAll(INLINE)) {
    if (match.index > at) found.push({ text: text.slice(at, match.index) })
    const [, bold, linkText, href, referenced] = match
    if (bold !== undefined) found.push({ text: bold, bold: true })
    else if (href !== undefined && /^https?:\/\//.test(href)) found.push({ text: linkText, href })
    else found.push({ text: linkText ?? referenced })
    at = match.index + match[0].length
  }
  if (at < text.length) found.push({ text: text.slice(at) })
  return found
}
