import type { Route } from './notice'

export type Sailing = {
  origin: string
  destination: string
  departs: string
  arrives: string
  rescheduled_departs: string | null
  status: string
  gust_knots: number | null
  chance_of_sailing: number | null
}

export type Predictions = {
  generated_at: string
  sailings: Sailing[]
  routes?: Route[]
}

export type Port = 'Troon' | 'Ardrossan'
export type Direction = 'To Brodick' | 'From Brodick'
export type Outlook = 'likely' | 'hopeful' | 'possible' | 'doubtful' | 'unlikely'

const LONDON = 'Europe/London'
const DAY_MS = 86_400_000
const time = new Intl.DateTimeFormat('en-GB', { timeZone: LONDON, hour: '2-digit', minute: '2-digit' })
const isoDate = new Intl.DateTimeFormat('en-CA', { timeZone: LONDON, year: 'numeric', month: '2-digit', day: '2-digit' })
const weekday = new Intl.DateTimeFormat('en-GB', { timeZone: 'UTC', weekday: 'short', day: 'numeric', month: 'short' })

export async function load(): Promise<Predictions> {
  const response = await fetch('predictions.json', { cache: 'no-cache' })
  if (!response.ok) {
    throw new Error(`predictions.json: ${response.status}`)
  }
  return response.json()
}

export function localTime(instant: string): string {
  return time.format(new Date(instant))
}

export function localDate(instant: string | number | Date): string {
  return isoDate.format(new Date(instant))
}

/** A UK date and time as 'YYYY-MM-DD HH:MM', which sorts in time order. */
export function localStamp(instant: string): string {
  return `${localDate(instant)} ${localTime(instant)}`
}

export function daysBetween(from: string, to: string): number {
  return Math.round((Date.parse(to) - Date.parse(from)) / DAY_MS)
}

export function dayLabel(date: string, today: string): string {
  const ahead = daysBetween(today, date)
  if (ahead === 0) return 'Today'
  if (ahead === 1) return 'Tomorrow'
  return weekday.format(new Date(date))
}

export function days(sailings: Sailing[]): string[] {
  return [...new Set(sailings.map((s) => localDate(s.departs)))].sort()
}

export function onRoute(sailing: Sailing, port: Port, direction: Direction): boolean {
  return direction === 'To Brodick'
    ? sailing.origin === port && sailing.destination === 'Brodick'
    : sailing.origin === 'Brodick' && sailing.destination === port
}

export function outlook(chance: number): Outlook {
  if (chance >= 0.9) return 'likely'
  if (chance >= 0.7) return 'hopeful'
  if (chance >= 0.5) return 'possible'
  if (chance >= 0.4) return 'doubtful'
  return 'unlikely'
}
