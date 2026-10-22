import {strict as assert} from 'node:assert'
import {test} from 'node:test'
import {localDayUtcBounds} from './date-range.ts'

test('summer day follows Chisinau UTC+3', () => {
  assert.deepEqual(localDayUtcBounds('2026-07-13'), {
    start: '2026-07-12T21:00:00.000Z',
    end: '2026-07-13T20:59:59.999Z',
  })
})

test('winter day follows Chisinau UTC+2', () => {
  assert.deepEqual(localDayUtcBounds('2026-01-13'), {
    start: '2026-01-12T22:00:00.000Z',
    end: '2026-01-13T21:59:59.999Z',
  })
})

test('autumn clock change includes the full 25-hour day', () => {
  assert.deepEqual(localDayUtcBounds('2026-10-25'), {
    start: '2026-10-24T21:00:00.000Z',
    end: '2026-10-25T21:59:59.999Z',
  })
})
