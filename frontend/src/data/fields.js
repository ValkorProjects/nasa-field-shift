// The farmer's fields (talhões): polygons drawn on the real satellite map.
// Saved in the browser under the active local profile (account.js); exported as GeoJSON.
// The app starts with no field (issue #38): the farmer draws their own.
// Each field keeps the map mode it was drawn in (issue #39): 'mvp' (Itaberá + Itapeva, may use the
// team's downloaded data) or 'explore' (elsewhere in Brazil, live data only).
import { reactive, computed, watch } from 'vue'
import { account, profileKey } from './account.js'
import { getJSON, setJSON } from './storage.js'

const valid = (f) => f && typeof f.id === 'string' && Array.isArray(f.coords) && f.coords.length >= 3

function loadFields() {
  if (!account.activeId) return []
  const list = getJSON(profileKey('fields'), [])
  return Array.isArray(list) ? list.filter(valid) : []
}

export const farm = reactive({
  fields: loadFields(),
  selectedId: null,
  scope: account.activeId ? getJSON(profileKey('scope'), 'mvp') : 'mvp' // map mode for new fields
})
farm.selectedId = farm.fields[0]?.id ?? null

// another profile → its own fields and map mode
watch(() => account.activeId, () => {
  farm.fields = loadFields()
  farm.selectedId = farm.fields[0]?.id ?? null
  farm.scope = getJSON(profileKey('scope'), 'mvp')
})
watch(() => farm.fields, (v) => { if (account.activeId) setJSON(profileKey('fields'), v) }, { deep: true })
watch(() => farm.scope, (v) => { if (account.activeId) setJSON(profileKey('scope'), v) })

/* Geodesic polygon area (m²) on the WGS84 sphere — same formula Leaflet.draw uses. */
export function areaM2(coords) {
  const R = 6378137, rad = Math.PI / 180
  let a = 0
  for (let i = 0; i < coords.length; i++) {
    const [lat1, lng1] = coords[i]
    const [lat2, lng2] = coords[(i + 1) % coords.length]
    a += (lng2 - lng1) * rad * (2 + Math.sin(lat1 * rad) + Math.sin(lat2 * rad))
  }
  return Math.abs((a * R * R) / 2)
}
export const areaHa = (coords) => (coords?.length >= 3 ? areaM2(coords) / 10000 : 0)
export const fmtHa = (ha) => (ha >= 100 ? Math.round(ha).toString() : ha.toFixed(1))

export const fieldById = (id) => farm.fields.find((f) => f.id === id)
export const selected = computed(() => fieldById(farm.selectedId))

export function addField(coords) {
  const n = farm.fields.reduce((m, f) => Math.max(m, parseInt(f.name.replace(/\D/g, '')) || 0), 0) + 1
  const f = { id: `f${Date.now()}`, name: `Field ${n}`, status: 'new', scope: farm.scope, coords }
  farm.fields.push(f)
  farm.selectedId = f.id
  return f
}

export function removeField(id) {
  farm.fields = farm.fields.filter((f) => f.id !== id)
  if (farm.selectedId === id) farm.selectedId = farm.fields[0]?.id ?? null
}

export function removeAllFields() {
  farm.fields = []
  farm.selectedId = null
}

// Map mode of a field (fields drawn before issue #39 count as MVP)
export const fieldScope = (f) => (f?.scope === 'explore' ? 'explore' : 'mvp')

// One field as a GeoJSON Feature ([lng, lat] order, closed ring). Body of POST /api/field/profile.
export function toFeature(f) {
  return {
    type: 'Feature',
    properties: { id: f.id, name: f.name, area_ha: +areaHa(f.coords).toFixed(2) },
    geometry: { type: 'Polygon', coordinates: [[...f.coords, f.coords[0]].map(([lat, lng]) => [lng, lat])] }
  }
}

// Area centroid of [lat, lng] coords (local equirectangular projection). Falls back to the vertex mean.
export function centroidOf(coords) {
  const lat0 = coords.reduce((s, c) => s + c[0], 0) / coords.length
  const lng0 = coords.reduce((s, c) => s + c[1], 0) / coords.length
  const k = Math.cos((lat0 * Math.PI) / 180)
  let a = 0, cx = 0, cy = 0
  for (let i = 0; i < coords.length; i++) {
    const x1 = (coords[i][1] - lng0) * k, y1 = coords[i][0] - lat0
    const x2 = (coords[(i + 1) % coords.length][1] - lng0) * k, y2 = coords[(i + 1) % coords.length][0] - lat0
    const cr = x1 * y2 - x2 * y1
    a += cr; cx += (x1 + x2) * cr; cy += (y1 + y2) * cr
  }
  if (Math.abs(a) < 1e-12) return { lat: lat0, lon: lng0 }
  return { lat: lat0 + cy / (3 * a), lon: lng0 + cx / (3 * a) / k }
}

// Same geometry → same key (used to avoid refetching the profile).
export const geomKey = (f) => (f ? JSON.stringify(f.coords) : '')

// Route of a screen of the selected field, e.g. fieldPath('crops') → /field/1/crops
export const fieldPath = (sub, id = farm.selectedId) => (id ? `/field/${id}/${sub}` : '/farm') // no field yet: back to the map

// GeoJSON FeatureCollection ([lng, lat] order, closed rings).
export function toGeoJSON() {
  return { type: 'FeatureCollection', features: farm.fields.map(toFeature) }
}

export function downloadGeoJSON() {
  const blob = new Blob([JSON.stringify(toGeoJSON(), null, 2)], { type: 'application/geo+json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'fields.geojson'
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

// Map layers. Satellite photo = Esri World Imagery; the other two are real NASA GIBS layers
// (regional scale, shown as context — the per-field numbers come from the pipeline JSON).
export const LAYERS = {
  photo: null,
  veg: {
    url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/MODIS_Terra_NDVI_8Day/default/default/GoogleMapsCompatible_Level9/{z}/{y}/{x}.png',
    maxNativeZoom: 9, opacity: 0.75, source: 'NASA MODIS NDVI · 250 m'
  },
  moist: {
    url: 'https://gibs.earthdata.nasa.gov/wmts/epsg3857/best/SMAP_L4_Analyzed_Surface_Soil_Moisture/default/default/GoogleMapsCompatible_Level6/{z}/{y}/{x}.png',
    maxNativeZoom: 6, opacity: 0.6, source: 'NASA SMAP L4 · 9 km'
  }
}
export const BASEMAP = {
  url: 'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  attribution: 'Imagery © Esri, Maxar, Earthstar Geographics · NASA GIBS'
}
