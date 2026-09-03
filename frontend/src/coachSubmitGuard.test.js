import test from 'node:test'
import assert from 'node:assert/strict'

import { createSubmitGuard } from './coachSubmitGuard.js'

test('createSubmitGuard blocks duplicate in-flight submissions', () => {
  const guard = createSubmitGuard()

  assert.equal(guard.begin('What is Python?'), true)
  assert.equal(guard.begin('What is Python?'), false)
  assert.equal(guard.begin('Another question'), false)

  guard.finish()

  assert.equal(guard.begin('Another question'), true)
})

test('createSubmitGuard ignores empty submissions', () => {
  const guard = createSubmitGuard()

  assert.equal(guard.begin('   '), false)
  assert.equal(guard.begin('Explain Python loops'), true)
  guard.finish()
})
