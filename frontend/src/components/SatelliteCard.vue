<script setup>
// 2025 season seen by NASA satellites (backend: /api/ndvi, /api/soil-moisture, /api/surface-temperature).
// Area statistics of the Itaberá–Itapeva study area (AppEEARS extract), never a measurement of the field.
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import Chip from './Chip.vue'
import { apiMode, getSatellite2025 } from '@/api/index.js'
import { centroidOf } from '@/data/fields.js'

const props = defineProps({ field: { type: Object, default: null } })
const st = ref({ status: 'idle' })
let ctrl = null

async function load() {
  ctrl?.abort()
  if (apiMode.value !== 'api' || !props.field) { st.value = { status: 'idle' }; return }
  ctrl = new AbortController()
  const c = centroidOf(props.field.coords)
  st.value = { status: 'loading' }
  try {
    const r = await getSatellite2025(c.lat, c.lon, { signal: ctrl.signal })
    st.value = r.ndvi || r.moisture || r.lst ? { status: 'ok', ...r } : { status: 'none', error: r.error }
  } catch (e) {
    if (e.name !== 'AbortError') st.value = { status: 'none', error: e }
  }
}
watch(() => [props.field?.id, JSON.stringify(props.field?.coords), apiMode.value], load, { immediate: true })
onBeforeUnmount(() => ctrl?.abort())

const MONTH = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const fmt = (iso) => { const [, m, d] = iso.split('-'); return `${MONTH[+m - 1]} ${+d}` }

// sparkline points for a series of numbers
function spark(vals, w = 220, h = 40) {
  const v = vals.filter((x) => typeof x === 'number')
  if (v.length < 2) return ''
  const lo = Math.min(...v), hi = Math.max(...v), span = hi - lo || 1
  return vals.map((x, i) => `${(i / (vals.length - 1)) * w},${h - 3 - ((x - lo) / span) * (h - 6)}`).join(' ')
}

const ndvi = computed(() => {
  const c = st.value.ndvi?.composites ?? []
  if (!c.length) return null
  const max = c.reduce((a, b) => (b.mean > a.mean ? b : a)), min = c.reduce((a, b) => (b.mean < a.mean ? b : a))
  return { pts: spark(c.map((x) => x.mean)), max, min }
})
const moisture = computed(() => {
  const d = st.value.moisture?.daily ?? []
  const byMonth = Array.from({ length: 12 }, (_, m) => d.filter((x) => +x.date.slice(5, 7) === m + 1 && x.rootzone).map((x) => x.rootzone.mean))
  const means = byMonth.map((a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : null))
  const valid = means.map((v, i) => [v, i]).filter(([v]) => v != null)
  if (!valid.length) return null
  const dry = valid.reduce((a, b) => (b[0] < a[0] ? b : a)), wet = valid.reduce((a, b) => (b[0] > a[0] ? b : a))
  return { pts: spark(means.map((v) => v ?? valid[0][0])), dry: { m: MONTH[dry[1]], v: dry[0] }, wet: { m: MONTH[wet[1]], v: wet[0] } }
})
const lst = computed(() => {
  const d = st.value.lst?.daily ?? []
  const nights = d.filter((x) => x.night)
  if (!nights.length) return null
  const cold = nights.filter((x) => x.night.mean <= 3)
  const coldest = nights.reduce((a, b) => (b.night.mean < a.night.mean ? b : a))
  return { nights: nights.length, cold: cold.length, coldest }
})
</script>

<template>
  <div v-if="st.status !== 'idle'" class="card satcard">
    <div class="sat-h">
      <b>2025 season seen by NASA satellites</b>
      <span class="tag sc-reg">study area · not your field</span>
    </div>
    <div v-if="st.status === 'loading'" class="fnote" role="status">Reading the 2025 satellite records…</div>
    <div v-else-if="st.status === 'none'" class="fnote">
      {{ st.error?.status === 404 ? 'The 2025 satellite extract covers only the Itaberá–Itapeva study area (about 15 × 15 km between the two towns). This field is outside it.' : `Satellite records not available: ${st.error?.message ?? 'no data'}` }}
    </div>
    <template v-else>
      <div v-if="ndvi" class="sat-row">
        <div class="sat-l"><span>Plant cover (NDVI)</span><Chip scale="area" source="MODIS 250 m" /></div>
        <svg viewBox="0 0 220 40" class="spark" aria-hidden="true"><polyline :points="ndvi.pts" /></svg>
        <div class="sat-v">greenest {{ fmt(ndvi.max.date) }} ({{ ndvi.max.mean.toFixed(2) }}) · lowest {{ fmt(ndvi.min.date) }} ({{ ndvi.min.mean.toFixed(2) }})</div>
      </div>
      <div v-if="moisture" class="sat-row">
        <div class="sat-l"><span>Root-zone soil moisture</span><Chip scale="area" source="SMAP 9 km" /></div>
        <svg viewBox="0 0 220 40" class="spark blue" aria-hidden="true"><polyline :points="moisture.pts" /></svg>
        <div class="sat-v">driest {{ moisture.dry.m }} ({{ moisture.dry.v.toFixed(3) }} m³/m³) · wettest {{ moisture.wet.m }} ({{ moisture.wet.v.toFixed(3) }})</div>
      </div>
      <div v-if="lst" class="sat-row">
        <div class="sat-l"><span>Cold nights at the ground</span><Chip scale="area" source="MODIS 1 km" /></div>
        <div class="sat-v big"><b>{{ lst.cold }}</b> of {{ lst.nights }} mostly clear nights ≤ 3 °C · coldest {{ fmt(lst.coldest.date) }} ({{ lst.coldest.night.mean.toFixed(1) }} °C)</div>
      </div>
      <div class="fnote">2025 only, averaged over the study area. Ground surface is colder than the 2 m air used for frost in the plans. Past records, not a forecast.</div>
    </template>
  </div>
</template>

<style scoped>
.satcard { display: flex; flex-direction: column; gap: 8px }
.sat-h { display: flex; justify-content: space-between; align-items: center; gap: 8px; font-size: 14px; color: #123346 }
.sat-row { display: grid; grid-template-columns: 1fr; gap: 3px; border-top: 1px solid #edf1ec; padding-top: 7px }
.sat-l { display: flex; justify-content: space-between; align-items: center; font-size: 13px; font-weight: 700; color: #2f3d31 }
.sat-v { font-size: 12.5px; font-weight: 600; color: #4b5a4c }
.sat-v.big b { font-size: 18px; color: #123346 }
.spark { width: 100%; height: 40px }
.spark polyline { fill: none; stroke: #42a147; stroke-width: 2.5; stroke-linejoin: round }
.spark.blue polyline { stroke: #1f6bd1 }
</style>
