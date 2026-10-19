import { describe, expect, it } from 'vitest'
import { paragraphs, routeFor, type Route } from './notice'

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
