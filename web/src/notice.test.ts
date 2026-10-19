import { describe, expect, it } from 'vitest'
import { disrupted, paragraphs, routeFor, routeOn, type Notice, type Route } from './notice'

describe('paragraphs', () => {
  it('splits on blank lines and keeps bold text', () => {
    const detail =
      'Due to MV Caledonian Isles assisting in an ongoing emergency incident, the following sailings are **cancelled**:\r\n\r\n**Depart** Ardrossan:  07:00, 09:45'
    expect(paragraphs(detail)).toEqual([
      [
        { text: 'Due to MV Caledonian Isles assisting in an ongoing emergency incident, the following sailings are ' },
        { text: 'cancelled', bold: true },
        { text: ':' },
      ],
      [{ text: 'Depart', bold: true }, { text: ' Ardrossan:  07:00, 09:45' }],
    ])
  })

  it.each([
    {
      name: 'inline links keep their target',
      detail: '[view online](https://www.calmac.co.uk/timetables) now',
      expected: [{ text: 'view online', href: 'https://www.calmac.co.uk/timetables' }, { text: ' now' }],
    },
    {
      name: 'reference links without a target become plain text',
      detail: '[View the amended timetable.][2]',
      expected: [{ text: 'View the amended timetable.' }],
    },
    {
      name: 'links that are not web addresses become plain text',
      detail: '[click](javascript:alert(1))',
      expected: [{ text: 'click' }, { text: ')' }],
    },
  ])('$name', ({ detail, expected }) => {
    expect(paragraphs(detail)).toEqual([expected])
  })

  it('joins single line breaks and drops empty paragraphs', () => {
    expect(paragraphs('one\n two\n \n\n\n')).toEqual([[{ text: 'one two' }]])
  })
})

describe('routeFor', () => {
  const routes: Route[] = [
    { route: 'ARD', status: 'DISRUPTIONS', notices: [] },
    { route: 'TRO', status: 'NORMAL', notices: [] },
  ]

  it.each([
    { port: 'Ardrossan', expected: 'DISRUPTIONS' },
    { port: 'Troon', expected: 'NORMAL' },
  ] as const)('$port', ({ port, expected }) => {
    expect(routeFor(routes, port)?.status).toBe(expected)
  })

  it('is missing from older predictions files', () => {
    expect(routeFor(undefined, 'Troon')).toBeUndefined()
  })
})

describe('disrupted', () => {
  function notice(status: Notice['status'], starts = '2026-10-19T05:14:00.000Z', ends = '2026-10-19T23:00:00.000Z'): Notice {
    return { title: 'Monday 19 October', status, reason: null, starts, ends, updated_at: starts, detail: '' }
  }

  function route(...notices: Notice[]): Route {
    return { route: 'ARD', status: 'DISRUPTIONS', notices }
  }

  it.each([
    { name: 'a sailing later that day', notices: [notice('DISRUPTIONS')], departs: '2026-10-19T11:30:00.000Z', expected: true },
    { name: 'a sailing before the notice was posted', notices: [notice('DISRUPTIONS')], departs: '2026-10-19T05:00:00.000Z', expected: true },
    { name: 'all sailings cancelled', notices: [notice('ALL_SAILINGS_CANCELLED')], departs: '2026-10-19T11:30:00.000Z', expected: true },
    { name: 'a sailing the next day', notices: [notice('DISRUPTIONS')], departs: '2026-10-20T07:30:00.000Z', expected: false },
    { name: 'a sailing the day before', notices: [notice('DISRUPTIONS')], departs: '2026-10-18T11:30:00.000Z', expected: false },
    {
      name: 'a long be-aware notice',
      notices: [notice('BE_AWARE', '2026-10-17T23:00:00.000Z', '2027-01-19T00:00:00.000Z')],
      departs: '2026-10-19T11:30:00.000Z',
      expected: false,
    },
  ])('$name: $expected', ({ notices, departs, expected }) => {
    expect(disrupted(route(...notices), departs)).toBe(expected)
  })

  it('is false without route information', () => {
    expect(disrupted(undefined, '2026-10-19T11:30:00.000Z')).toBe(false)
  })
})

describe('routeOn', () => {
  function notice(status: Notice['status'], starts: string, ends: string): Notice {
    return { title: status, status, reason: null, starts, ends, updated_at: starts, detail: '' }
  }

  const route: Route = {
    route: 'TRO',
    status: 'DISRUPTIONS',
    notices: [
      notice('DISRUPTIONS', '2026-10-19T06:06:00.000Z', '2026-10-19T23:00:00.000Z'),
      notice('BE_AWARE', '2026-10-17T23:00:00.000Z', '2027-01-19T00:00:00.000Z'),
    ],
  }

  it.each([
    { day: '2026-10-19', status: 'DISRUPTIONS', titles: ['DISRUPTIONS', 'BE_AWARE'] },
    { day: '2026-10-20', status: 'BE_AWARE', titles: ['BE_AWARE'] },
    { day: '2026-10-17', status: 'NORMAL', titles: [] },
  ])('$day is $status', ({ day, status, titles }) => {
    const on = routeOn(route, day)
    expect(on?.status).toBe(status)
    expect(on?.notices.map((n) => n.title)).toEqual(titles)
  })
})
