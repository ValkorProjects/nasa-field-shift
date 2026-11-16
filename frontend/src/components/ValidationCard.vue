<script setup>
// Validation metrics from GET /api/validation for the selected field (or Itapeva when there is none):
// data coverage, stability of the planting windows (leave one season out), 2025 cross-checks.
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import Chip from './Chip.vue'
import { apiMode, getValidation, PRESET_LOCATIONS } from '@/api/index.js'
import { selected, centroidOf } from '@/data/fields.js'

const st = ref({ status: 'idle' })
const where = computed(() => {
  const f = selected.value
  if (f) { const c = centroidOf(f.coords); return { name: f.name, lat: c.lat, lon: c.lon } }
  return PRESET_LOCATIONS[0]
})
let ctrl = null
async function load() {
  ctrl?.abort()
  if (apiMode.value !== 'api') { st.value = { status: 'mock' }; return }
  ctrl = new AbortController()
  st.value = { status: 'loading' }
  try {
    st.value = { status: 'ok', v: await getValidation(where.value.lat, where.value.lon, { signal: ctrl.signal }) }
  } catch (e) {
    if (e.name !== 'AbortError') st.value = { status: 'error', error: e.message }
  }
}
watch(() => [where.value.lat, where.value.lon, apiMode.value], load, { immediate: true })
onBeforeUnmount(() => ctrl?.abort())

const pct = (x) => (x == null ? '—' : `${Math.round(x * 100)} %`)
const minCov = computed(() => (st.value.v ? Math.min(...Object.values(st.value.v.history.coverage)) : null))
const CROP = { corn: 'Second-crop corn (frost)', soybean: 'Soybean (white mold)' }
function stabilityText(s) {
  if (!s.recommended_days) return 'No low-risk planting days in these records.'
  if (s.recommended_stability >= 0.8) return `The best-time window is stable: it barely changes when any one year is removed (${s.recommended_stability.toFixed(2)}).`
  if (s.recommended_stability >= 0.5) return `The best-time window moves when some years are removed (${s.recommended_stability.toFixed(2)}): use it as a guide.`
  return `The best-time window depends on a single year (${s.recommended_stability.toFixed(2)}): treat it as uncertain.`
}
</script>

<template>
  <div class="card valcard">
    <div class="h2">How much to trust these numbers</div>
    <p class="pp">Checks for <b>{{ where.name }}</b>, computed by our backend from NASA data.</p>
    <div v-if="st.status === 'mock'" class="fnote">Validation metrics need the live backend (api mode). This version shows sample data.</div>
    <div v-else-if="st.status === 'loading'" class="fnote" role="status">Computing the checks…</div>
    <div v-else-if="st.status === 'error'" class="fnote warn" role="alert">Checks not available: {{ st.error }}</div>
    <template v-else-if="st.status === 'ok'">
      <div class="vrow">
        <b>Data coverage</b>
        <span>{{ pct(minCov) }} of the days 2015–2024 have valid rain, temperature and humidity.</span>
        <Chip scale="area" :source="`NASA POWER · ${st.v.history.mode}`" />
      </div>
      <div v-for="s in st.v.stability" :key="s.crop" class="vrow">
        <b>{{ CROP[s.crop] }}</b>
        <span>{{ pct(s.level_agreement) }} of the planting dates keep their level when any one of the {{ s.seasons }} years is removed. {{ stabilityText(s) }}</span>
        <Chip scale="est" source="leave one year out" />
      </div>
      <template v-if="st.v.cross_checks_2025?.status === 'ok'">
        <div class="vrow">
          <b>Frost, 2025: air vs ground</b>
          <span>NASA POWER (air) and MODIS (ground, at night) agree on {{ pct(st.v.cross_checks_2025.frost.agreement) }} of {{ st.v.cross_checks_2025.frost.days_compared }} nights with satellite data.
            Cold in both: {{ st.v.cross_checks_2025.frost.cold_both }} · only the ground: {{ st.v.cross_checks_2025.frost.cold_only_modis }} · only the air: {{ st.v.cross_checks_2025.frost.cold_only_power }}.</span>
          <Chip scale="area" source="POWER + MODIS" />
        </div>
        <div class="vrow">
          <b>Dry autumn, 2025: rain vs soil</b>
          <span>April–May 2025 rain {{ st.v.cross_checks_2025.dry_autumn.power_rain_apr_may_2025_mm }} mm (mean {{ st.v.cross_checks_2025.dry_autumn.power_rain_apr_may_mean_mm }} mm);
            SMAP root-zone moisture {{ st.v.cross_checks_2025.dry_autumn.smap_rootzone_apr_may_2025 }} vs {{ st.v.cross_checks_2025.dry_autumn.smap_rootzone_rest_2025 }} m³/m³ the rest of the year.
            <b>{{ st.v.cross_checks_2025.dry_autumn.agree ? 'Both say it was drier.' : 'They disagree.' }}</b></span>
          <Chip scale="area" source="POWER + SMAP" />
        </div>
        <div v-if="st.v.cross_checks_2025.vegetation?.consistent != null" class="vrow">
          <b>Crop season, 2025: plant cover</b>
          <span>NDVI of the area was lowest on {{ st.v.cross_checks_2025.vegetation.lowest.date }} ({{ st.v.cross_checks_2025.vegetation.lowest.ndvi }}) and highest on {{ st.v.cross_checks_2025.vegetation.highest.date }} ({{ st.v.cross_checks_2025.vegetation.highest.ndvi }}).
            <b>{{ st.v.cross_checks_2025.vegetation.consistent ? 'It follows a summer-crop calendar, as the plans assume.' : 'It does not follow the summer-crop calendar the plans assume.' }}</b></span>
          <Chip scale="area" source="MODIS NDVI 250 m" />
        </div>
      </template>
      <div v-else class="vrow"><b>2025 satellite cross-checks</b><span>{{ st.v.cross_checks_2025?.reason }}</span></div>
      <details class="vth">
        <summary>How we rate each plan (estimates, to be validated with agronomists)</summary>
        <ul>
          <li><b>Rain in April–May:</b> share of dry autumns (April + May &lt; 150 mm, NASA POWER), only if the crop lists a drought risk in our catalog: ≥ 50 % often, ≥ 20 % sometimes.</li>
          <li><b>Frost:</b> share of years with a day ≤ 3 °C in June–August, only if the crop lists frost: corn ≥ 50 % / 20 %, winter cereals ≥ 30 % / 10 %.</li>
          <li><b>Rain washing soil away:</b> field slope from NASA SRTM 30 m (flat &lt; 3 %, gentle &lt; 8 %, steep) × how much the plan covers the soil.</li>
          <li><b>Priorities:</b> protect soil = straw or living cover, lower on steep fields · save water = dry-autumn exposure · income = grain to sell, lower with a red risk · low cost = cover crops are cheaper.</li>
        </ul>
      </details>
      <details class="vth">
        <summary>Thresholds we use (project estimates, to be validated with agronomists)</summary>
        <ul><li v-for="(t, k) in st.v.thresholds" :key="k"><b>{{ k.replace(/_/g, ' ') }}:</b> {{ t }}</li></ul>
      </details>
    </template>
  </div>
</template>

<style scoped>
.valcard { display: flex; flex-direction: column; gap: 8px }
.vrow { display: grid; grid-template-columns: 210px 1fr auto; gap: 10px; align-items: start; border-top: 1px solid #edf1ec; padding-top: 8px; font-size: 13.5px; line-height: 1.45 }
.vrow b { color: #123346 }
.vth { font-size: 13px; margin-top: 4px }
.vth summary { cursor: pointer; font-weight: 700; color: #3c4c3e }
.vth ul { margin: 6px 0 0 18px; padding: 0 }
</style>
