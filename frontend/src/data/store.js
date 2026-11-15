// App state: the field JSON (read-only data) + the farmer's answers (wizard state).
// The front only reads one pre-computed JSON per field. No satellite processing here.
import { reactive, computed, watch, shallowRef, toRaw } from 'vue'
import { apiMode, getFieldProfile } from '@/api/index.js'
import { farm, selected, toFeature, geomKey, areaHa, fieldScope } from './fields.js'
import { toFieldData } from './profileAdapter.js'
import { fieldStatus } from './rules.js'
import { withPlans, loadCatalog } from './strategies.js'

// Profile of each field (POST /api/field/profile):
//   { [fieldId]: { status: 'loading'|'ready'|'error', error, geom, profile } }
const profiles = reactive({})
export const profileOf = (id) => profiles[id] ?? null

// The sample JSON (Field 1). Field 1 in mock mode shows it as is (the demo); any other field is
// built from the sample + its profile by the adapter.
const sampleRef = shallowRef(null) // not deep-reactive: the adapter clones it

export const state = reactive({
  data: computed(() => dataFor(farm.selectedId)),
  loading: true,
  error: null,
  usingSample: true,
  // farmer's answers
  crops: { summer: null, second: null },
  soil: { texture: null, drainage: null, slope: null },
  order: [],
  orderChosen: false, // the farmer confirmed the order of priorities (issue #38: nothing pre-chosen)
  layer: 'photo'
})

// The 3 plans follow the farmer's crops (strategies.js); everything else comes from the sample or the profile.
function dataFor(id) {
  return withPlans(baseDataFor(id), state.crops)
}

function baseDataFor(id) {
  const sample = toRaw(sampleRef.value)
  if (!sample) return null
  const f = farm.fields.find((x) => x.id === id)
  if (!f || (apiMode.value === 'mock' && f.id === '1')) return sample
  const e = profiles[id]
  // A new border keeps the previous profile on screen until the new answer arrives.
  let profile = e?.status === 'error' ? null : e?.profile ?? null
  if (profile && !!profile.mock !== (apiMode.value === 'mock')) profile = null // profile of another mode
  return toFieldData(sample, profile, f, {
    nextCrop: state.crops.second, crops: state.crops, areaHa: areaHa(f.coords),
    apiMode: apiMode.value, error: e?.status === 'error' ? e.error : null, loading: !e || e.status === 'loading'
  })
}

async function tryJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url}: ${res.status}`)
  if (!(res.headers.get('content-type') || '').includes('json')) throw new Error(`${url}: not JSON`)
  return res.json()
}

// Real data (field-1.json) wins; falls back to field-1.sample.json.
export async function loadSample(id = '1') {
  state.loading = true
  loadCatalog() // crop catalog for the alternative plans (optional)
  try {
    let data
    try {
      data = await tryJson(`/data/field-${id}.json`)
      state.usingSample = false
    } catch {
      data = await tryJson(`/data/field-${id}.sample.json`)
      state.usingSample = true
    }
    sampleRef.value = data
    // Issue #38: start with nothing chosen. The order below is only how the cards are listed
    // until the farmer sorts them; results wait for orderChosen.
    state.crops = { summer: null, second: null }
    state.soil = { texture: null, drainage: null, slope: null }
    state.order = data.priorities.items.map((p) => p.id)
    state.orderChosen = false
  } catch (e) {
    state.error = e.message
  } finally {
    state.loading = false
  }
}

/* ---------- Field profile ---------- */
const ctrls = {}
const timers = {}
const EDIT_DEBOUNCE_MS = 700

// Fetches the profile of a field once per geometry. A changed border waits a moment (the farmer may
// still be dragging corners). Late answers of an older geometry are ignored.
export function ensureProfile(field, { force = false } = {}) {
  if (!field) return
  if (apiMode.value === 'mock' && field.id === '1') return
  const geom = `${geomKey(field)}|${apiMode.value}`
  const cur = profiles[field.id]
  if (!force && cur && cur.geom === geom && cur.status !== 'error') return
  const first = !cur
  profiles[field.id] = { status: 'loading', error: null, geom, profile: cur?.status === 'error' ? null : cur?.profile ?? null }
  clearTimeout(timers[field.id])
  ctrls[field.id]?.abort()
  const run = async () => {
    const ctrl = (ctrls[field.id] = new AbortController())
    try {
      const profile = await getFieldProfile({ feature: toFeature(field), name: field.name, scope: fieldScope(field) }, { signal: ctrl.signal })
      if (profiles[field.id]?.geom !== geom) return
      profiles[field.id] = { status: 'ready', error: null, geom, profile }
      const f = farm.fields.find((x) => x.id === field.id)
      if (f && !profile.mock) f.status = fieldStatus(dataFor(f.id))
    } catch (e) {
      if (e.name === 'AbortError' || profiles[field.id]?.geom !== geom) return
      profiles[field.id] = { status: 'error', error: e.message, geom, profile: null }
    }
  }
  if (first || force) run()
  else timers[field.id] = setTimeout(run, EDIT_DEBOUNCE_MS)
}

// Forget the profile of deleted fields (and cancel their requests).
watch(() => farm.fields.map((f) => f.id).join(','), () => {
  const ids = new Set(farm.fields.map((f) => f.id))
  for (const id of Object.keys(profiles)) {
    if (ids.has(id)) continue
    ctrls[id]?.abort(); clearTimeout(timers[id])
    delete ctrls[id]; delete timers[id]; delete profiles[id]
  }
})

// Any screen can be opened directly (/field/:id/...): the profile follows the selected field.
watch(() => [farm.selectedId, geomKey(selected.value), apiMode.value], () => ensureProfile(selected.value), { immediate: true })

// Plain value of a { value, sample, ... } leaf (or a raw value).
// Which wizard step still needs an answer (null when the farmer can see results).
export function missingStep() {
  if (!state.crops.summer || !state.crops.second) return 'crops'
  if (!state.soil.texture || !state.soil.drainage || !state.soil.slope) return 'soil'
  if (!state.orderChosen) return 'priorities'
  return null
}

export const val = (x) => (x && typeof x === 'object' && 'value' in x ? x.value : x)

/* ---------- "Best for you" ----------
 * Σ (Good=2, OK=1, Poor=0) × priority weight (4-3-2-1, by the farmer's order).
 * Ratings per strategy come from the JSON (to be validated by an agronomist).
 */
export function scoreStrategies(order = state.order) {
  const d = state.data
  if (!d) return []
  const { weights, points } = d.priorities
  return d.strategies
    .filter((s) => s.fit) // plans without RollCrop rules are "Not rated" and never ranked
    .map((s) => ({
      id: s.id,
      score: order.reduce((sum, p, i) => sum + (points[s.fit[p]] ?? 0) * (weights[i] ?? 0), 0)
    }))
    .sort((a, b) => b.score - a.score)
}

// A ranking needs at least 2 rated plans ("Not rated" plans are left out).
const ranked = (order) => { const r = scoreStrategies(order); return r.length >= 2 ? r[0].id : undefined }
export const bestId = computed(() => ranked())

// What would win if "income" were moved to the top of the current order.
export const bestIfIncomeFirst = computed(() => {
  const order = ['income', ...state.order.filter((p) => p !== 'income')]
  return ranked(order)
})

export const strategy = (id) => state.data?.strategies.find((s) => s.id === id)
export const priorityLabel = (id) => state.data?.priorities.items.find((p) => p.id === id)?.label

/* ---------- "How sure are we?" ----------
 * 4 checks: ≥10 years of data · main indicators field-level · GPM and POWER agree · local soil info.
 * 4 = High, 2–3 = Medium, 0–1 = Low.
 */
export const confidence = computed(() => {
  const rules = state.data?.confidence.rules ?? []
  const met = rules.filter((r) => r.ok).length
  const level = met === 4 ? 'High' : met >= 2 ? 'Medium' : 'Low'
  const tone = level === 'High' ? 'g' : level === 'Medium' ? 'y' : 'r'
  return { rules, met, total: rules.length, level, tone }
})
