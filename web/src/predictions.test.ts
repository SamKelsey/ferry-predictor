import { describe, expect, it } from 'vitest'
import { dayLabel, days, localDate, localTime, onRoute, outlook, type Sailing } from './predictions'

function sailing(origin: string, destination: string, departs = '2026-10-18T09:15:00.000Z'): Sailing {
  return {
    origin,
    destination,
    departs,
    arrives: departs,
    rescheduled_departs: null,
    status: 'SCHEDULED',
    gust_knots: null,
    chance_of_sailing: null,
  }
}

describe('localTime', () => {
  it.each([
    { name: 'summer time is an hour ahead of UTC', instant: '2026-10-18T09:15:00.000Z', expected: '10:15' },
    { name: 'winter time matches UTC', instant: '2026-12-01T09:15:00.000Z', expected: '09:15' },
  ])('$name', ({ instant, expected }) => {
    expect(localTime(instant)).toBe(expected)
  })
})

describe('localDate', () => {
  it.each([
    { name: 'late evening stays on the same day', instant: '2026-10-17T22:30:00Z', expected: '2026-10-17' },
    { name: 'just after midnight in summer time is the next day', instant: '2026-10-17T23:30:00Z', expected: '2026-10-18' },
    { name: 'after the clocks go back', instant: '2026-10-25T23:30:00Z', expected: '2026-10-25' },
  ])('$name', ({ instant, expected }) => {
    expect(localDate(instant)).toBe(expected)
  })
})

describe('dayLabel', () => {
  it.each([
    { date: '2026-10-17', expected: 'Today' },
    { date: '2026-10-18', expected: 'Tomorrow' },
    { date: '2026-10-19', expected: 'Mon 19 Oct' },
    { date: '2026-10-26', expected: 'Mon 26 Oct' },
  ])('$date is $expected', ({ date, expected }) => {
    expect(dayLabel(date, '2026-10-17')).toBe(expected)
  })
})

describe('days', () => {
  it('lists each UK date once, in order', () => {
    const sailings = [
      sailing('Troon', 'Brodick', '2026-10-18T23:30:00Z'),
      sailing('Troon', 'Brodick', '2026-10-18T09:15:00Z'),
      sailing('Brodick', 'Troon', '2026-10-18T07:00:00Z'),
    ]
    expect(days(sailings)).toEqual(['2026-10-18', '2026-10-19'])
  })
})

describe('onRoute', () => {
  it.each([
    { name: 'Troon to Brodick is Troon to Arran', s: sailing('Troon', 'Brodick'), port: 'Troon', direction: 'To Arran', expected: true },
    { name: 'Brodick to Troon is Troon from Arran', s: sailing('Brodick', 'Troon'), port: 'Troon', direction: 'From Arran', expected: true },
    { name: 'Brodick to Troon is not Troon to Arran', s: sailing('Brodick', 'Troon'), port: 'Troon', direction: 'To Arran', expected: false },
    { name: 'Ardrossan sailings are not on the Troon route', s: sailing('Ardrossan', 'Brodick'), port: 'Troon', direction: 'To Arran', expected: false },
  ] as const)('$name', ({ s, port, direction, expected }) => {
    expect(onRoute(s, port, direction)).toBe(expected)
  })
})

describe('outlook', () => {
  it.each([
    { chance: 0.97, expected: 'likely' },
    { chance: 0.9, expected: 'likely' },
    { chance: 0.89, expected: 'hopeful' },
    { chance: 0.7, expected: 'hopeful' },
    { chance: 0.69, expected: 'possible' },
    { chance: 0.5, expected: 'possible' },
    { chance: 0.49, expected: 'doubtful' },
    { chance: 0.4, expected: 'doubtful' },
    { chance: 0.39, expected: 'unlikely' },
  ])('$chance is $expected', ({ chance, expected }) => {
    expect(outlook(chance)).toBe(expected)
  })
})
