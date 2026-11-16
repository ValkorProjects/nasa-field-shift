// API access with a mock/real flag (issue #6). The mode comes from the .env file of each Vite mode:
//   npm run dev       → api, local backend (Vite proxies /api to http://localhost:8000)
//   npm run dev:mock  → mock, sample JSON in ./mock
//   vite build        → api, https://rollcrop-backend.vercel.app (VITE_API_BASE); Vercel previews → localhost
// Without VITE_API_MODE the app falls back to mock.
// The contract is documented in docs/contract-example.json.
import { ref } from 'vue'
import corn from './mock/corn.json'
import soybean from './mock/soybean.json'
import fieldProfile from './mock/field-profile.json'
import { centroidOf, areaHa } from '@/data/fields.js'

const MOCKS = { corn, soybean }
// `npm run dev:api` (vite --mode api) or VITE_API_MODE=api switch to the real backend.
export const apiMode = ref(import.meta.env.VITE_API_MODE === 'api' || import.meta.env.MODE === 'api' ? 'api' : 'mock')

// Where the backend lives. Empty in dev (Vite proxies /api). In a production build (e.g. Vercel, where there
// is no proxy) set VITE_API_BASE=https://your-backend.example.com; the backend allows CORS from any origin.
export const API_BASE = (import.meta.env.VITE_API_BASE ?? '').replace(/\/+$/, '')

// MVP places (issue #39: the MVP covers Itaberá and Itapeva, SP). Your own fields are added in the UI.
export const PRESET_LOCATIONS = [
  { id: 'itapeva', name: 'Itapeva, SP', lat: -23.98, lon: -48.88 },
  { id: 'itabera', name: 'Itaberá, SP', lat: -23.86, lon: -49.14 }
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
    res = await fetch(`${API_BASE}/api/recommendation?${q}`, { signal, headers: { Accept: 'application/json' } })
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

// One call per field (issue: field profile). Data only; the business rules live in src/data/rules.js.
// mock: the shipped contract sample, re-centred on the field; it is marked `mock: true` so the
//   adapter shows it as sample data. api: POST /api/field/profile (the backend returns real NASA/ISRIC data).
export async function getFieldProfile({ feature, name, scope = 'mvp' }, { signal } = {}) {
  if (apiMode.value === 'mock') {
    await wait(350, signal)
    const p = structuredClone(fieldProfile)
    const coords = feature.geometry.coordinates[0].slice(0, -1).map(([lng, lat]) => [lat, lng])
    const c = centroidOf(coords)
    p.field.data = { ...p.field.data, centroid: { lat: c.lat, lon: c.lon }, area_ha: +areaHa(coords).toFixed(2),
      vertex_count: coords.length, location_name: name ?? null }
    for (const k of ['field', 'weather_summary', 'events', 'planting', 'soil', 'terrain']) {
      if (p[k]?.source) p[k].source.mode = k === 'field' ? 'computed' : 'mock'
    }
    p.mock = true
    return p
  }
  // Browser-side timeout, combined with the caller's signal.
  const ctl = new AbortController()
  let timedOut = false
  const timer = setTimeout(() => { timedOut = true; ctl.abort() }, 35000)
  const onAbort = () => ctl.abort()
  if (signal?.aborted) ctl.abort(); else signal?.addEventListener('abort', onAbort)
  try {
    let res
    try {
      res = await fetch(`${API_BASE}/api/field/profile`, {
        method: 'POST', signal: ctl.signal,
        headers: { Accept: 'application/json', 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: feature, name, scope })
      })
    } catch (e) {
      if (timedOut) throw new Error('The backend took too long to answer. Try again.')
      if (e.name === 'AbortError') throw e
      throw new Error('Could not reach the backend. Is it running?')
    }
    if (res.status === 422) {
      let detail = ''
      try { const b = await res.json(); detail = typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail) } catch { /* no body */ }
      throw new Error(`This field shape is not valid: ${detail}`.trim())
    }
    if (res.status >= 500) throw new Error(`The backend is not answering (${res.status}). Is it running? In dev, /api is sent to VITE_BACKEND_URL.`)
    if (!res.ok) throw new Error(`Backend answered ${res.status} ${res.statusText}`.trim())
    try {
      return await res.json()
    } catch (e) {
      if (timedOut) throw new Error('The backend took too long to answer. Try again.')
      throw e
    }
  } finally {
    // Runs after the body is read, so the 35 s timer cannot abort a slow body read.
    clearTimeout(timer)
    signal?.removeEventListener('abort', onAbort)
  }
}

/* ---------- other backend routes (api mode only) ---------- */
async function getApi(path, { signal } = {}) {
  const res = await fetch(`${API_BASE}${path}`, { signal, headers: { Accept: 'application/json' } })
  if (!res.ok) {
    let detail = ''
    try { const b = await res.json(); detail = typeof b.detail === 'string' ? b.detail : '' } catch { /* no body */ }
    const e = new Error(detail || `The backend answered ${res.status}`)
    e.status = res.status
    throw e
  }
  return res.json()
}
const q = (lat, lon) => `lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}`

// GET /api/validation: data coverage, stability of the planting windows, 2025 cross-checks
export const getValidation = (lat, lon, opt) => getApi(`/api/validation?${q(lat, lon)}`, opt)

// 2025 NASA AppEEARS extract (Itaberá–Itapeva study area): NDVI, SMAP soil moisture, MODIS surface temperature.
// Each one may fail on its own (404 outside the study area).
// Study-area box of the AppEEARS extract (backend: in_study_area). Outside it the endpoints answer 404.
const SAT_BOX = { minLon: -49.06, maxLon: -48.91, minLat: -23.95, maxLat: -23.81 }
export const inSatelliteBox = (lat, lon) => lon >= SAT_BOX.minLon && lon <= SAT_BOX.maxLon && lat >= SAT_BOX.minLat && lat <= SAT_BOX.maxLat

export async function getSatellite2025(lat, lon, opt) {
  if (!inSatelliteBox(lat, lon)) return { ndvi: null, moisture: null, lst: null, error: null }
  const [ndvi, moisture, lst] = await Promise.allSettled([
    getApi(`/api/ndvi?${q(lat, lon)}`, opt),
    getApi(`/api/soil-moisture?${q(lat, lon)}`, opt),
    getApi(`/api/surface-temperature?${q(lat, lon)}&min_coverage=0.5`, opt)
  ])
  const val = (r) => (r.status === 'fulfilled' ? r.value : null)
  const err = [ndvi, moisture, lst].find((r) => r.status === 'rejected')?.reason ?? null
  return { ndvi: val(ndvi), moisture: val(moisture), lst: val(lst), error: err }
}
