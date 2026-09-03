export function createSubmitGuard() {
  let inFlight = false
  let current = null

  return {
    begin(value) {
      const message = String(value ?? '').trim()
      if (!message || inFlight) return false
      inFlight = true
      current = message
      return true
    },
    finish() {
      inFlight = false
      current = null
    },
    reset() {
      inFlight = false
      current = null
    },
    get active() {
      return inFlight
    },
    get value() {
      return current
    },
  }
}
