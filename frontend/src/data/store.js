// App state: the field JSON (read-only data) + the farmer's answers (wizard state).
// The front only reads one pre-computed JSON per field. No satellite processing here.
import { reactive, computed } from 'vue'

export const state = reactive({
  data: null,
  loading: true,
  error: null,
  usingSample: true,
  // farmer's answers
  crops: { summer: null, second: null },
  soil: { texture: null, drainage: null, slope: null },
  order: [],
  layer: 'photo'
})

async function tryJson(url) {
  const res = await fetch(url)
  if (!res.ok) throw new Error(`${url}: ${res.status}`)
  if (!(res.headers.get('content-type') || '').includes('json')) throw new Error(`${url}: not JSON`)
  return res.json()
}

// Real data (field-1.json) wins; falls back to field-1.sample.json.
export async function loadField(id = '1') {
  state.loading = true
  try {
    let data
    try {
      data = await tryJson(`/data/field-${id}.json`)
      state.usingSample = false
    } catch {
      data = await tryJson(`/data/field-${id}.sample.json`)
      state.usingSample = true
    }
    state.data = data
    state.crops = { ...data.crops.defaults }
    state.soil = { ...data.soil.defaults }
    state.order = [...data.priorities.defaultOrder]
  } catch (e) {
    state.error = e.message
  } finally {
    state.loading = false
  }
}

// Plain value of a { value, sample, ... } leaf (or a raw value).
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
    .map((s) => ({
      id: s.id,
      score: order.reduce((sum, p, i) => sum + (points[s.fit[p]] ?? 0) * (weights[i] ?? 0), 0)
    }))
    .sort((a, b) => b.score - a.score)
}

export const bestId = computed(() => scoreStrategies()[0]?.id)

// What would win if "income" were moved to the top of the current order.
export const bestIfIncomeFirst = computed(() => {
  const order = ['income', ...state.order.filter((p) => p !== 'income')]
  return scoreStrategies(order)[0]?.id
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
