// localStorage wrapped in try/catch. If the browser blocks storage (private window, policy, quota),
// the app keeps working with an in-memory copy for this visit.
const memory = new Map()
let available = null

function check() {
  if (available !== null) return available
  try {
    const k = '__fieldshift_probe__'
    localStorage.setItem(k, '1')
    localStorage.removeItem(k)
    available = true
  } catch {
    available = false
  }
  return available
}

export const storageAvailable = () => check()

export function getJSON(key, fallback = null) {
  try {
    const raw = check() ? localStorage.getItem(key) : memory.get(key)
    return raw == null ? fallback : JSON.parse(raw)
  } catch {
    return fallback
  }
}

export function setJSON(key, value) {
  const raw = JSON.stringify(value)
  memory.set(key, raw)
  try { if (check()) localStorage.setItem(key, raw) } catch { /* full or blocked: memory copy stays */ }
}

export function remove(key) {
  memory.delete(key)
  try { if (check()) localStorage.removeItem(key) } catch { /* ignore */ }
}

// Every key of this app (prefix fieldshift.), for "sign out and clear data".
export function keysWithPrefix(prefix) {
  const keys = new Set([...memory.keys()].filter((k) => k.startsWith(prefix)))
  try {
    if (check()) for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i)
      if (k?.startsWith(prefix)) keys.add(k)
    }
  } catch { /* ignore */ }
  return [...keys]
}
