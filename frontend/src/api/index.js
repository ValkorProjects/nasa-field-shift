// API access with a mock/real flag (issue #6).
//   VITE_API_MODE=mock → sample JSON in ./mock (default)
//   VITE_API_MODE=api  → GET /api/recommendation (Vite proxies /api to the backend in dev)
// The contract is documented in docs/contract-example.json.
import { ref } from 'vue'
import corn from './mock/corn.json'
import soybean from './mock/soybean.json'

const MOCKS = { corn, soybean }
// `npm run dev:api` (vite --mode api) or VITE_API_MODE=api switch to the real backend.
export const apiMode = ref(import.meta.env.VITE_API_MODE === 'api' || import.meta.env.MODE === 'api' ? 'api' : 'mock')

// Demo locations (issue #7: start with 2–3 predefined points). Your own fields are added in the UI.
export const PRESET_LOCATIONS = [
  { id: 'taquarituba', name: 'Taquarituba, SP', lat: -23.53, lon: -49.24 },
  { id: 'itapeva', name: 'Itapeva, SP', lat: -23.98, lon: -48.88 },
  { id: 'capao-bonito', name: 'Capão Bonito, SP', lat: -24.01, lon: -48.35 }
]

export const CROPS = [
  { id: 'corn', label: 'Second-crop corn', img: '/img/milho.jpg', risk: 'Frost / cold' },
  { id: 'soybean', label: 'Soybean', img: '/img/soja.jpg', risk: 'White mold' }
]

const wait = (ms, signal) => new Promise((resolve, reject) => {
  const t = setTimeout(resolve, ms)
  signal?.addEventListener('abort', () => { clearTimeout(t); reject(new DOMException('Aborted', 'AbortError')) })
})

function mockRecommendation({ lat, lon, crop, name }) {
  const base = MOCKS[crop]
  if (!base) throw new Error(`No sample data for crop "${crop}"`)
  const r = structuredClone(base)
  r.location = { name: name ?? `${lat.toFixed(2)}, ${lon.toFixed(2)}`, lat, lon }
  r.source.mode = 'mock'
  return r
}

export async function getRecommendation({ lat, lon, crop, name }, { signal } = {}) {
  if (apiMode.value === 'mock') {
    await wait(350, signal) // so the loading state is visible in the demo
    return mockRecommendation({ lat, lon, crop, name })
  }
  const q = new URLSearchParams({ lat: lat.toFixed(4), lon: lon.toFixed(4), crop })
  let res
  try {
    res = await fetch(`/api/recommendation?${q}`, { signal, headers: { Accept: 'application/json' } })
  } catch (e) {
    if (e.name === 'AbortError') throw e
    throw new Error('Could not reach the backend. Is it running?')
  }
  if (res.status >= 500) throw new Error(`The backend is not answering (${res.status}). Is it running? In dev, /api is sent to VITE_BACKEND_URL.`)
  if (!res.ok) throw new Error(`Backend answered ${res.status} ${res.statusText}`.trim())
  const data = await res.json()
  if (name && data.location && !data.location.name) data.location.name = name
  return data
}
