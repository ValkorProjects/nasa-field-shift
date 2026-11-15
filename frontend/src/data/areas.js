// Map scope (issue #39). MVP = Itaberá + Itapeva (SP), where the team loaded the satellite data.
// Explore = anywhere in Brazil, live data only. Same rule as backend/areas.py: every vertex, the
// centroid and points along each edge must be inside the area (a field cut by the border is refused;
// a field across the border between the two towns is fine). The backend checks again (422).
import { reactive } from 'vue'
import { centroidOf } from './fields.js'

export const MVP_TOWNS = 'Itaberá and Itapeva (SP)'
export const MSG = {
  outsideMvp: `This MVP only works in ${MVP_TOWNS}, where we loaded the satellite data. You can explore other places in Brazil with live data.`,
  outsideBrazil: 'The field must be inside Brazil.',
  exploreBadge: 'Exploratory mode: live data only, outside the MVP area. Not validated for this region.',
  outsideSp: 'Calendars and alerts were validated for São Paulo state only.'
}
// Rough boxes for map limits (the real check uses the outlines)
export const BOUNDS = {
  mvp: [[-24.30, -49.45], [-23.49, -48.45]],
  brazil: [[-34.2, -74.5], [5.6, -34.3]]
}
const EDGE_SAMPLES = 8

export const areas = reactive({ mvp: null, brazil: null, error: null })

let loading = null
export function loadAreas() {
  loading ??= Promise.all(['mvp', 'brazil'].map((n) =>
    fetch(`/data/areas/${n}.geojson`).then((r) => {
      if (!r.ok) throw new Error(`${n}.geojson: ${r.status}`)
      return r.json()
    })
  )).then(([mvp, brazil]) => {
    areas.mvp = mvp
    areas.brazil = brazil
  }).catch((e) => { areas.error = e.message; loading = null })
  return loading
}

// [[[lon, lat], ...], ...] outer + holes, for every polygon of the collection
function polygons(fc) {
  const out = []
  for (const f of fc?.features ?? []) {
    const g = f.geometry
    for (const poly of g.type === 'Polygon' ? [g.coordinates] : g.coordinates) out.push(poly)
  }
  return out
}

function inRing(lon, lat, ring) {
  let inside = false
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [x1, y1] = ring[i], [x2, y2] = ring[j]
    if ((y1 > lat) !== (y2 > lat) && lon < x1 + ((lat - y1) * (x2 - x1)) / (y2 - y1)) inside = !inside
  }
  return inside
}

export function pointInArea(lat, lon, name) {
  return polygons(areas[name]).some(([outer, ...holes]) => inRing(lon, lat, outer) && !holes.some((h) => inRing(lon, lat, h)))
}

// coords: [[lat, lng], ...] (open ring, as stored in fields.js)
export function fieldInArea(coords, name) {
  if (!areas[name] || coords.length < 3) return false
  const c = centroidOf(coords)
  if (!pointInArea(c.lat, c.lon, name)) return false
  for (let i = 0; i < coords.length; i++) {
    const [la1, lo1] = coords[i], [la2, lo2] = coords[(i + 1) % coords.length]
    for (let k = 0; k <= EDGE_SAMPLES; k++) {
      const t = k / (EDGE_SAMPLES + 1)
      if (!pointInArea(la1 + (la2 - la1) * t, lo1 + (lo2 - lo1) * t, name)) return false
    }
  }
  return true
}

// null when the field is allowed in this scope, else the message to show
export function scopeProblem(coords, scope) {
  if (scope === 'explore') return fieldInArea(coords, 'brazil') ? null : MSG.outsideBrazil
  return fieldInArea(coords, 'mvp') ? null : MSG.outsideMvp
}

// São Paulo state, roughly: used only for the "validated for SP" note in explore mode
export const inSaoPauloBox = ({ lat, lon }) => lat >= -25.4 && lat <= -19.7 && lon >= -53.2 && lon <= -44.1
