<script setup>
// Small static satellite view of one field (non-interactive Leaflet map).
import { ref, onMounted, onBeforeUnmount, watch } from 'vue'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import { fieldById, LAYERS, BASEMAP } from '@/data/fields.js'

const props = defineProps({
  field: { type: String, default: '1' },
  w: { type: [Number, String], default: 92 },
  h: { type: [Number, String], default: 92 },
  layer: { type: String, default: 'photo' },
  pad: { type: Number, default: 8 }
})
const COL = { r: '#ff4d4d', y: '#ffc21a', g: '#5ee06a', new: '#ffffff' }
const el = ref(null)
let map = null, poly = null

function draw() {
  const f = fieldById(props.field)
  if (!map || !f) return
  poly?.remove()
  poly = L.polygon(f.coords, { color: COL[f.status] ?? '#fff', weight: 3, fill: false, interactive: false }).addTo(map)
  map.fitBounds(f.coords, { padding: [props.pad, props.pad], animate: false })
}

onMounted(() => {
  map = L.map(el.value, {
    zoomControl: false, attributionControl: false, dragging: false, scrollWheelZoom: false,
    doubleClickZoom: false, boxZoom: false, keyboard: false, touchZoom: false, zoomSnap: 0.25
  })
  L.tileLayer(BASEMAP.url, { maxZoom: 19 }).addTo(map)
  const o = LAYERS[props.layer]
  if (o) L.tileLayer(o.url, { maxNativeZoom: o.maxNativeZoom, maxZoom: 19, opacity: o.opacity }).addTo(map)
  draw()
})
onBeforeUnmount(() => map?.remove())
watch(() => [props.field, fieldById(props.field)?.coords], draw, { deep: true })
</script>

<template>
  <div ref="el" class="fthumb lthumb" :style="{ width: `${w}px`, height: `${h}px` }" role="img"
    :aria-label="`${fieldById(field)?.name ?? 'Field'}, satellite view`"></div>
</template>
