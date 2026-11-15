// The farmer's fields (talhões): polygons drawn on the real satellite map.
// Stored in the browser (localStorage) for now; exported as GeoJSON for the Python pipeline.
import { reactive, computed, watch } from 'vue'

const KEY = 'fieldshift.fields.v2'

// Sample fields so the demo flow works out of the box: 3 crop fields traced on the satellite
// image near Taquarituba, southwest São Paulo state. They are examples, not a real farm's records.
// Only Field 1 has sample analysis data (field-1.sample.json). Status colours are sample values.
const SAMPLE = [
  { id: '1', name: 'Field 1', status: 'r', coords: [[-23.53727, -49.23343], [-23.53639, -49.23096], [-23.54013, -49.22559], [-23.54219, -49.22796], [-23.54042, -49.23182]] },
  { id: '2', name: 'Field 2', status: 'g', coords: [[-23.5296, -49.23074], [-23.52862, -49.22871], [-23.52852, -49.2257], [-23.5296, -49.2242], [-23.53196, -49.22441], [-23.53245, -49.22678], [-23.53216, -49.22999], [-23.53098, -49.23085]] },
  { id: '3', name: 'Field 3', status: 'y', coords: [[-23.53354, -49.23429], [-23.53334, -49.23214], [-23.5357, -49.22999], [-23.53668, -49.23128], [-23.53727, -49.23332], [-23.53629, -49.23418]] }
]

function load() {
  try {
    const raw = localStorage.getItem(KEY)
    if (raw) {
      const list = JSON.parse(raw)
      if (Array.isArray(list)) return list
    }
  } catch { /* storage blocked or corrupt: use the sample */ }
  return structuredClone(SAMPLE)
}

export const farm = reactive({
  fields: load(),
  selectedId: '1'
})

watch(() => farm.fields, (v) => {
  try { localStorage.setItem(KEY, JSON.stringify(v)) } catch { /* ignore */ }
}, { deep: true })

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
  const f = { id: `f${Date.now()}`, name: `Field ${n}`, status: 'new', coords }
  farm.fields.push(f)
  farm.selectedId = f.id
  return f
}

export function removeField(id) {
  farm.fields = farm.fields.filter((f) => f.id !== id)
  if (farm.selectedId === id) farm.selectedId = farm.fields[0]?.id ?? null
}

export function resetSample() {
  farm.fields = structuredClone(SAMPLE)
  farm.selectedId = '1'
}

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
export const fieldPath = (sub, id = farm.selectedId) => `/field/${id}/${sub}`

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
