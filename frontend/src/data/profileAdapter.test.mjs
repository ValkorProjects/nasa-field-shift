// Run: node --test src/data/profileAdapter.test.mjs  (no dependencies; uses the real backend contract)
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { reactive, shallowRef, toRaw, computed } from 'vue'
import { toFieldData } from './profileAdapter.js'
import { countDryAutumns, countFrostYears, frostWord, rainWord, textureFromGroup, slopeClass, pickPlantingWindow, weeksUntil } from './rules.js'

const load = (p) => JSON.parse(readFileSync(new URL(p, import.meta.url), 'utf8'))
const sample = load('../../public/data/field-1.sample.json')
const contract = load('../api/mock/field-profile.json')
const field = { id: 'f9', name: 'Field 9' }
const ctx = { nextCrop: 'corn', crops: { summer: 'soy', second: 'corn' }, areaHa: 26.2 }

test('rules on the real contract', () => {
  const rows = contract.weather_summary.data.by_year_month
  assert.deepEqual(countDryAutumns(rows), { hit: 7, total: 10 })
  assert.deepEqual(countFrostYears(rows), { hit: 3, total: 10 })
  assert.equal(frostWord(3, 10, 'corn').text, 'Sometimes')
  assert.equal(frostWord(3, 10, 'wheat').text, 'Often')
  assert.equal(rainWord(7, 10).text, 'Often too little')
  assert.equal(textureFromGroup('media'), 'medium')
  assert.equal(textureFromGroup('muito_argilosa'), 'clay')
  assert.equal(slopeClass(5), 'gentle')
  assert.equal(weeksUntil('2027-01-15', '2027-02-12'), 4)
  assert.deepEqual(pickPlantingWindow(contract.planting.data.corn, '2027-01-15'), { start: '2027-01-15', end: '2027-03-11' })
})

test('ready profile: real leaves, terrain coming soon, sample kept elsewhere', () => {
  const d = toFieldData(sample, contract, field, ctx)
  assert.equal(d.alert.rain_years.value, '7 of 10')
  assert.equal(d.alert.rain_years.sample, false)
  assert.equal(d.alert.frost_years.value, '3 of 10')
  assert.equal(d.alert.active, true)
  assert.equal(d.soil.texture_est.value, 'medium')
  assert.equal(d.soil.slope_sat.pending, true)
  assert.equal(d.soil.slope_sat.value, 'Coming soon')
  assert.equal(d.field.area_ha.value, 26.2)
  assert.equal(d.field.harvest.sample, true) // no source
  assert.equal(d.strategies[0].rows[0].answer.value, 'Often too little')
  assert.equal(d.alert.planting.value, 'Jan 15')
  assert.equal(d.info.weatherNote, 'Weather from Taquarituba, SP, 1.5 km away')
  assert.equal(d.confidence.rules[0].ok, true)
  assert.equal(d.confidence.agree_pct.unavailable != null, true)
  assert.equal(sample.alert.rain_years.sample, true) // sample not mutated
})

test('unavailable blocks never show Field 1 numbers', () => {
  const bad = structuredClone(contract)
  for (const k of ['weather_summary', 'events', 'planting']) Object.assign(bad[k], { status: 'unavailable', reason: 'NASA POWER is down', data: null })
  Object.assign(bad.soil, { status: 'no_data', reason: 'No soil data here', data: null })
  const d = toFieldData(sample, bad, field, ctx)
  assert.equal(d.alert.rain_years.value, 'Not available')
  assert.equal(d.alert.rain_years.unavailable, 'NASA POWER is down')
  assert.equal(d.alert.active, false)
  assert.equal(d.soil.texture_est.unavailable, 'No soil data here')
  assert.equal(d.details.b.evidence[0].n.value, 'Not available')
  assert.equal(d.confidence.rules[0].ok, false)
})

test('mock profile and missing profile', () => {
  const m = toFieldData(sample, { ...contract, mock: true }, field, ctx)
  assert.equal(m.meta.sampleOnly, true)
  assert.equal(m.alert.rain_years.sample, true)
  const n = toFieldData(sample, null, field, ctx)
  assert.equal(n.alert.rain_years.unavailable, 'Loading field data…')
})

test('reactive (Proxy) sample does not break the adapter', () => {
  const d = toFieldData(reactive(structuredClone(sample)), contract, field, ctx)
  assert.equal(d.alert.rain_years.value, '7 of 10')
  // same path as the store: shallowRef + computed inside a reactive object
  const ref = shallowRef(structuredClone(sample))
  const st = reactive({ data: computed(() => toFieldData(toRaw(ref.value), reactive({ ...contract }), field, { ...ctx, crops: reactive(ctx.crops) })) })
  assert.equal(st.data.soil.texture_est.value, 'medium')
})

test('no profile: mock falls back to sample, api shows loading or the real error', () => {
  const m = toFieldData(sample, null, field, { ...ctx, apiMode: 'mock', loading: true })
  assert.equal(m.meta.sampleOnly, true)
  const l = toFieldData(sample, null, field, { ...ctx, apiMode: 'api', loading: true })
  assert.equal(l.meta.loading, true)
  assert.equal(l.alert.unavailable, undefined) // no flash of "not available"
  const e = toFieldData(sample, null, field, { ...ctx, apiMode: 'api', error: 'Could not reach the backend. Is it running?' })
  assert.equal(e.meta.loading, false)
  assert.equal(e.alert.unavailable, 'Could not reach the backend. Is it running?')
  assert.equal(e.soil.texture_est.unavailable, 'Could not reach the backend. Is it running?')
  assert.equal(e.strategies[0].lightTxt, 'Not checked')
})

test('sampling notes and texts', () => {
  const p = structuredClone(contract)
  p.weather_summary.source = { ...p.weather_summary.source, sampling: 'nearest_demo_point', location_name: 'Itapeva, SP', distance_km: 12 }
  p.soil.source = { ...p.soil.source, sampling: 'curated_rural_pixel', distance_km: 3.2 }
  let d = toFieldData(sample, p, field, ctx)
  assert.equal(d.info.weatherNote, 'Weather from Itapeva, SP, 12 km away')
  assert.equal(d.info.soilNote, 'Soil from a verified rural pixel 3.2 km away')
  p.soil.source.sampling = 'nearest_neighbor'
  d = toFieldData(sample, p, field, ctx)
  assert.match(d.info.soilNote, /nearest valid pixel, 3.2 km/)
  // verdict has no unsourced income claim; why uses the real counts
  assert.doesNotMatch(d.strategies[0].verdict.value, /income/i)
  assert.match(d.details.current.why, /7 of the last 10/)
  assert.equal(d.details.current.sampleText, true)
  // title follows the chosen crop
  assert.match(d.alert.title, /^Corn /)
  d = toFieldData(sample, p, field, { ...ctx, nextCrop: 'wheat' })
  assert.match(d.alert.title, /^Wheat /)
  d = toFieldData(sample, p, field, { ...ctx, nextCrop: 'cover' })
  assert.doesNotMatch(d.alert.title, /^Corn /)
})
