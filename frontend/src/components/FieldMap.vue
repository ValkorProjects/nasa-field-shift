<script setup>
// Real satellite map (Leaflet). Pan/zoom, search a place, NASA layers, draw and edit fields.
// mode: 'view' | 'draw' (click to add points) | 'edit' (drag the selected field's corners)
import { ref, shallowRef, watch, onMounted, onBeforeUnmount, computed } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { farm, fieldById, LAYERS, BASEMAP, areaHa, fmtHa } from '@/data/fields.js'
import { t } from '@/i18n'

const props = defineProps({
  layer: { type: String, default: 'photo' },
  mode: { type: String, default: 'view' },
  showFields: { type: Boolean, default: true },
  showControls: { type: Boolean, default: true }
})
const emit = defineEmits(['update:layer', 'select', 'drawn'])

const COL = {
  r: ['#ff4d4d', 'rgba(224,72,72,.28)'],
  y: ['#ffc21a', 'rgba(224,164,0,.28)'],
  g: ['#5ee06a', 'rgba(46,139,61,.22)'],
  new: ['#ffffff', 'rgba(255,255,255,.18)']
}

const el = ref(null)
const map = shallowRef(null)
let overlay = null
let fieldLayer = null
let editLayer = null
let drawLayer = null
const drawPts = ref([])

/* ---------- layers ---------- */
function setOverlay(id) {
  if (overlay) { map.value.removeLayer(overlay); overlay = null }
  const cfg = LAYERS[id]
  if (cfg) overlay = L.tileLayer(cfg.url, { maxNativeZoom: cfg.maxNativeZoom, maxZoom: 19, opacity: cfg.opacity, attribution: '' }).addTo(map.value)
}
const overlaySource = computed(() => LAYERS[props.layer]?.source)

/* ---------- fields ---------- */
function drawFields() {
  fieldLayer.clearLayers()
  if (!props.showFields) return
  for (const f of farm.fields) {
    const [stroke, fill] = COL[f.status] ?? COL.new
    const sel = f.id === farm.selectedId
    const poly = L.polygon(f.coords, {
      color: stroke, weight: sel ? 4 : 3, fillColor: fill, fillOpacity: 1,
      dashArray: sel ? '10 7' : null, bubblingMouseEvents: false
    })
    poly.bindTooltip(f.name, { permanent: true, direction: 'center', className: 'plabel-tt' })
    // while drawing, a click on an existing field still adds a corner (neighbouring fields share borders)
    poly.on('click', (e) => (props.mode === 'draw' ? onMapClick(e) : emit('select', f.id)))
    fieldLayer.addLayer(poly)
    if (f.status === 'r') {
      const east = f.coords.reduce((a, b) => (b[1] > a[1] ? b : a)) // pin the "!" to the field's east corner
      fieldLayer.addLayer(L.marker(east, {
        icon: L.divIcon({ className: 'risk-bang', html: '!', iconSize: [34, 34] }), interactive: false
      }))
    }
  }
}

/* ---------- edit (drag corners, drag midpoints to add, right-click to remove) ---------- */
function drawEditHandles() {
  editLayer.clearLayers()
  const f = fieldById(farm.selectedId)
  if (props.mode !== 'edit' || !f) return
  const vIcon = L.divIcon({ className: 'vtx', iconSize: [16, 16] })
  const mIcon = L.divIcon({ className: 'vtx mid', iconSize: [12, 12] })
  f.coords.forEach((c, i) => {
    const m = L.marker(c, { icon: vIcon, draggable: true, title: 'Drag to move · right-click to remove' })
    m.on('drag', (e) => { const p = e.target.getLatLng(); f.coords[i] = [p.lat, p.lng] })
    m.on('dragend', drawEditHandles)
    m.on('contextmenu', () => { if (f.coords.length > 3) { f.coords.splice(i, 1); drawEditHandles() } })
    editLayer.addLayer(m)
  })
  f.coords.forEach((c, i) => {
    const n = f.coords[(i + 1) % f.coords.length]
    const m = L.marker([(c[0] + n[0]) / 2, (c[1] + n[1]) / 2], { icon: mIcon, draggable: true, title: 'Drag to add a corner' })
    let idx = null
    m.on('dragstart', () => { f.coords.splice(i + 1, 0, [c[0], c[1]]); idx = i + 1 })
    m.on('drag', (e) => { const p = e.target.getLatLng(); f.coords[idx] = [p.lat, p.lng] })
    m.on('dragend', drawEditHandles)
    editLayer.addLayer(m)
  })
}

/* ---------- draw a new field ---------- */
function renderDraft() {
  drawLayer.clearLayers()
  if (props.mode !== 'draw' || !drawPts.value.length) return
  const pts = drawPts.value
  drawLayer.addLayer(L.polygon(pts, { color: '#ffffff', weight: 3, dashArray: '6 6', fillColor: '#ffffff', fillOpacity: 0.15, interactive: false }))
  pts.forEach((p, i) => drawLayer.addLayer(L.circleMarker(p, {
    radius: i === 0 ? 8 : 6, color: '#1f6bd1', weight: 3, fillColor: '#fff', fillOpacity: 1, bubblingMouseEvents: false
  }).on('click', () => { if (i === 0) finishDraw() })))
}
function onMapClick(e) {
  if (props.mode !== 'draw') return
  drawPts.value = [...drawPts.value, [e.latlng.lat, e.latlng.lng]]
}
function finishDraw() {
  // drop repeated corners (a double-click adds the same point twice)
  const pts = drawPts.value.filter((p, i, a) => {
    const q = a[(i + 1) % a.length]
    return i === a.length - 1 ? true : Math.hypot(p[0] - q[0], p[1] - q[1]) > 1e-6
  })
  if (pts.length < 3) return
  emit('drawn', pts)
  drawPts.value = []
}
const undoPoint = () => (drawPts.value = drawPts.value.slice(0, -1))
const draft = computed(() => ({ corners: drawPts.value.length, ha: fmtHa(areaHa(drawPts.value)) }))

/* ---------- search & location ---------- */
const query = ref('')
const searching = ref(false)
const searchMsg = ref('')
async function search() {
  if (!query.value.trim()) return
  searching.value = true; searchMsg.value = ''
  try {
    const url = `https://nominatim.openstreetmap.org/search?format=json&limit=1&countrycodes=br&q=${encodeURIComponent(query.value)}`
    const res = await fetch(url, { headers: { 'Accept-Language': 'en' } })
    const [hit] = await res.json()
    if (hit) map.value.flyToBounds([[+hit.boundingbox[0], +hit.boundingbox[2]], [+hit.boundingbox[1], +hit.boundingbox[3]]], { maxZoom: 15 })
    else searchMsg.value = 'Place not found'
  } catch { searchMsg.value = 'Search is offline' }
  searching.value = false
}
function myLocation() {
  navigator.geolocation?.getCurrentPosition(
    (p) => map.value.flyTo([p.coords.latitude, p.coords.longitude], 16),
    () => (searchMsg.value = 'Location not allowed')
  )
}

/* ---------- public helpers ---------- */
function fitField(id) {
  const f = fieldById(id)
  if (f && map.value) map.value.flyToBounds(f.coords, { padding: [60, 60], maxZoom: 17, duration: 0.6 })
}
function fitAll() {
  const all = farm.fields.flatMap((f) => f.coords)
  if (all.length) map.value.fitBounds(all, { padding: [50, 50], maxZoom: 16 })
  else map.value.setView([-23.5, -48.5], 7) // São Paulo state
}
defineExpose({ fitField, fitAll, finishDraw, undoPoint, draft })

/* ---------- lifecycle ---------- */
onMounted(() => {
  map.value = L.map(el.value, { zoomControl: false, attributionControl: true, maxZoom: 19 })
  L.tileLayer(BASEMAP.url, { maxZoom: 19, attribution: BASEMAP.attribution }).addTo(map.value)
  map.value.attributionControl.setPrefix(false)
  fieldLayer = L.layerGroup().addTo(map.value)
  editLayer = L.layerGroup().addTo(map.value)
  drawLayer = L.layerGroup().addTo(map.value)
  map.value.on('click', onMapClick)
  setOverlay(props.layer)
  drawFields()
  fitAll()
  // The side panel changes height (draw / edit / view), which resizes the map box.
  // Keep the top-left corner fixed so what is under the cursor does not jump.
  ro = new ResizeObserver(() => map.value?.invalidateSize({ pan: false }))
  ro.observe(el.value)
})
let ro = null
onBeforeUnmount(() => { ro?.disconnect(); map.value?.remove() })

watch(() => props.layer, setOverlay)
watch(() => [farm.fields, farm.selectedId, props.showFields], () => { drawFields() }, { deep: true })
watch(() => [farm.selectedId, props.mode], drawEditHandles)
watch(() => props.mode, (m) => {
  if (!map.value) return
  m === 'draw' ? map.value.doubleClickZoom.disable() : map.value.doubleClickZoom.enable()
  el.value.classList.toggle('drawing', m === 'draw')
  if (m !== 'draw') drawPts.value = []
})
watch(drawPts, renderDraft, { deep: true })

const layers = [
  { id: 'photo', label: 'map.photo' },
  { id: 'veg', label: 'map.veg' },
  { id: 'moist', label: 'map.moist', regional: true }
]
</script>

<template>
  <div class="mapbox">
    <div ref="el" class="lmap" @dblclick="mode === 'draw' && finishDraw()"></div>

    <div v-if="showControls" class="layer" role="group" aria-label="Map layer">
      <button v-for="l in layers" :key="l.id" :class="{ on: layer === l.id }" :aria-pressed="layer === l.id" @click="emit('update:layer', l.id)">
        {{ t(l.label) }}<span v-if="l.regional" class="tag sc-reg">{{ t('map.regional') }}</span>
      </button>
    </div>

    <form v-if="showControls" class="msearch" role="search" @submit.prevent="search">
      <input v-model="query" type="search" placeholder="Find a town or place in Brazil" aria-label="Find a place" />
      <button type="submit" :disabled="searching">{{ searching ? '…' : 'Go' }}</button>
      <button type="button" title="Go to my location" aria-label="Go to my location" @click="myLocation">◎</button>
      <span v-if="searchMsg" class="smsg">{{ searchMsg }}</span>
    </form>

    <div v-if="showControls" class="zoom">
      <button aria-label="Zoom in" @click="map.zoomIn()">+</button>
      <button aria-label="Zoom out" @click="map.zoomOut()">−</button>
      <button aria-label="Show all fields" title="Show all fields" @click="fitAll">⤢</button>
    </div>

    <!-- draw / edit controls live in the side panel so they never cover the map -->

    <div v-if="layer === 'moist'" class="legend">
      <span><i class="grad moist"></i>Dry → wet · whole region ({{ overlaySource }}), not your field</span>
    </div>
    <div v-else-if="layer === 'veg'" class="legend">
      <span><i class="grad veg"></i>Bare → dense plants · {{ overlaySource }}</span>
    </div>
    <div v-else-if="showFields" class="legend">
      <span><i style="background:#2e8b3d"></i>{{ t('map.fine') }}</span>
      <span><i style="background:#e0a400"></i>{{ t('map.attention') }}</span>
      <span><i style="background:#e04848"></i>{{ t('map.high') }}</span>
      <span><i style="background:#fff;border:1px solid #999"></i>New</span>
      <span class="lnote">sample colours</span>
    </div>
  </div>
</template>
