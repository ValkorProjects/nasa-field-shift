// Adapter: POST /api/field/profile → the field JSON the screens read (same shape as field-1.sample.json).
// Pure (no Vue). Starts from the sample and overwrites only the leaves that have a real source;
// everything without a source stays `sample: true` (dotted on screen).
//   real leaf        { value, sample:false, source, scale, mode }
//   failed block     { value:'Not available', sample:false, unavailable:'<reason>', source, scale }
//   terrain pending  { value:'Coming soon', sample:false, pending:true, ... }
import {
  countDryAutumns, countFrostYears, frostWord, rainWord, ofText, textureFromGroup, slopeClass,
  pickPlantingWindow, weeksUntil, fmtDay, alertActive, alertTitle, confidenceRules
} from './rules.js'

export const real = (value, source, scale, mode = null) => ({ value, sample: false, source, scale, mode })
export const missing = (reason, source, scale) => ({ value: 'Not available', sample: false, unavailable: reason || 'Not available', source, scale })
const pending = (source = 'NASADEM / SRTM (in progress)') => ({ value: 'Coming soon', sample: false, pending: true, source, scale: 'field' })

const POWER = 'NASA POWER'
const SOILGRIDS = 'SoilGrids 250 m'
const okBlock = (b) => b?.status === 'ok'

// "Jan 15, 2027" → "2027-01-15"
function scenarioIso(sample) {
  const d = new Date(`${sample.scenario?.today?.value ?? ''} 12:00 UTC`)
  return isNaN(d) ? null : d.toISOString().slice(0, 10)
}

function weatherNote(src) {
  if (src?.sampling !== 'nearest_demo_point') return null
  return `Weather from ${src.location_name ?? 'a nearby point'}, ${src.distance_km} km away`
}
function soilNote(src) {
  if (!src || src.sampling === 'requested' || src.sampling == null) return null
  return src.sampling === 'curated_rural_pixel'
    ? `Soil from a verified rural pixel ${src.distance_km} km away`
    : `Soil from the nearest valid pixel, ${src.distance_km} km away`
}

const byIcon = (list, icon) => list?.find((x) => x.icon === icon)

export function toFieldData(sample, profile, field, ctx = {}) {
  const data = JSON.parse(JSON.stringify(sample)) // plain copy (works even if `sample` is a Vue proxy)
  const name = field?.name ?? sample.field.name.value
  const today = scenarioIso(sample)
  data.field.name = { value: name, sample: false, source: 'user', scale: null }
  data.meta = { ...data.meta, fieldId: field?.id ?? data.meta?.fieldId, live: false, sampleOnly: false }

  const setArea = (ha) => {
    data.field.area_ha = real(ha, 'your map', 'field', 'computed')
    const inp = data.money.inputs.find((i) => i.id === 'area')
    if (inp) inp.v = real(ha, 'your map', 'field', 'computed')
  }

  // Mock mode (VITE_API_MODE=mock): the contract sample is not this field's data. Sample stays dotted.
  // Also the case while the mock profile is still loading (nothing real to wait for).
  if (profile?.mock === true || (!profile && ctx.apiMode === 'mock')) {
    if (typeof ctx.areaHa === 'number') setArea(+ctx.areaHa.toFixed(1))
    data.alert.title = alertTitle({ rain: true, frost: false }, name, 'Corn')
    data.meta.sampleOnly = true
    data.profile = profile ?? null
    data.blocks = {}
    data.info = {}
    return data
  }

  data.meta.live = true
  // No profile: still loading (api mode) or failed (ctx.error). Every block counts as unavailable,
  // with the real reason; while loading the screens show "loading", not an error.
  const loading = !profile && !ctx.error
  data.meta.loading = loading
  const noProfile = ctx.error || 'Loading field data…'
  const p = profile ?? {
    field: null,
    weather_summary: { status: 'unavailable', reason: noProfile, source: null },
    soil: { status: 'unavailable', reason: noProfile, source: null },
    terrain: { status: 'pending', source: null }
  }

  /* ---- field ---- */
  const fa = okBlock(p.field) ? p.field.data.area_ha : ctx.areaHa
  if (typeof fa === 'number') setArea(+fa.toFixed(1))

  /* ---- crops chosen by the farmer (UI) ---- */
  const cropName = (season) => sample.crops[season]?.find((c) => c.id === ctx.crops?.[season])?.name
  if (cropName('summer')) data.field.summer = { value: cropName('summer'), sample: false, source: 'user', scale: null }
  if (cropName('second')) data.field.next = { value: cropName('second'), sample: false, source: 'user', scale: null }

  /* ---- terrain (issues #11/#12) ---- */
  const terrain = p.terrain
  const slopePct = okBlock(terrain) ? terrain.data?.slope_pct?.mean : null
  const cls = slopeClass(slopePct)
  const slopeLeaf = (what) => {
    if (cls == null) return pending(terrain?.source?.dataset ? 'NASADEM / SRTM (in progress)' : undefined)
    return real(what === 'pct' ? +slopePct.toFixed(1) : cls, 'NASADEM 30 m', 'field', terrain.source?.mode)
  }
  data.field.slope = slopeLeaf('class')
  data.field.slope_pct = slopeLeaf('pct')
  data.soil.slope_sat = slopeLeaf('class')
  data.soil.slope_pct = slopeLeaf('pct')

  /* ---- soil ---- */
  const soil = p.soil
  if (okBlock(soil)) {
    const tex = textureFromGroup(soil.data?.profile?.texture_group)
    data.soil.texture_est = tex
      ? real(tex, SOILGRIDS, 'est', soil.source?.mode)
      : missing('Soil texture group not recognised', SOILGRIDS, 'est')
  } else {
    data.soil.texture_est = missing(soil?.reason, SOILGRIDS, 'est')
  }
  // drainage_est has no source yet: stays sample.

  /* ---- weather ---- */
  const w = p.weather_summary
  const wOk = okBlock(w)
  const wMode = w?.source?.mode
  const rows = wOk ? w.data?.by_year_month ?? [] : []
  const rain = wOk ? countDryAutumns(rows) : null
  const frost = wOk ? countFrostYears(rows) : null
  const noCover = 'Not enough valid days in the record'
  const wLeaf = (text, c) => (!wOk ? missing(w?.reason, POWER, 'area')
    : c?.total ? real(text, POWER, 'area', wMode) : missing(noCover, POWER, 'area'))

  data.alert.rain_years = wLeaf(rain && ofText(rain), rain)
  data.alert.frost_years = wLeaf(frost && ofText(frost), frost)
  data.money.dry_years = wLeaf(rain && ofText(rain, { last: true }), rain)

  // planting: only for crops that have a recommendation (corn, soybean)
  const rec = ctx.nextCrop && okBlock(p.planting) ? p.planting.data?.[ctx.nextCrop] : null
  if (!wOk) {
    data.field.planting = data.alert.planting = missing(w?.reason, POWER, 'area')
    data.alert.weeks = missing(w?.reason, POWER, 'area')
  } else if (rec || ctx.nextCrop === 'corn' || ctx.nextCrop === 'soybean') {
    const win = rec ? pickPlantingWindow(rec, today) : null
    if (win) {
      data.field.planting = real(fmtDay(win.start), POWER, 'area', wMode)
      data.alert.planting = real(fmtDay(win.start), POWER, 'area', wMode)
      data.alert.weeks = real(String(weeksUntil(today, win.start)), POWER, 'area', wMode)
    } else {
      const why = 'No recommended planting window left this season'
      data.field.planting = data.alert.planting = data.alert.weeks = missing(why, POWER, 'area')
    }
  } // other crops: planting and weeks stay sample

  // alert (rules)
  const a = alertActive(wOk && rain.total && frost.total ? { rain, frost } : null)
  data.alert.active = a.active
  data.alert.level = a.level
  data.alert.live = true
  if (!wOk) {
    if (!loading) data.alert.unavailable = w?.reason || 'Not available'
    data.alert.title = loading ? 'Checking the weather records…' : 'Pre-planting check not available'
  } else {
    // The rain/frost rules read the record for the crop the farmer picked as second crop (corn or wheat);
    // for other choices the title does not name a crop.
    const titleCrop = { corn: 'Corn', wheat: 'Wheat', soybean: 'Soybean' }[ctx.nextCrop] ?? null
    data.alert.title = a.active ? alertTitle(a, name, titleCrop) : `No big weather risk found for ${name}`
  }

  // strategies: rain and frost rows (current plan = corn, option A = wheat); the rest stays sample
  const cur = data.strategies.find((s) => s.id === 'current')
  const setRow = (s, icon, word, c) => {
    const r = byIcon(s?.rows, icon)
    if (!r) return
    if (!wOk) { r.answer = missing(w?.reason, POWER, 'area'); r.tone = 'y'; return }
    if (!word) { r.answer = missing(noCover, POWER, 'area'); r.tone = 'y'; return }
    r.answer = real(word.text, POWER, 'area', wMode)
    r.tone = word.tone
  }
  const rw = rain && rainWord(rain.hit, rain.total)
  const fwCorn = frost && frostWord(frost.hit, frost.total, 'corn')
  setRow(cur, 'rain', rw)
  setRow(cur, 'frost', fwCorn)
  setRow(data.strategies.find((s) => s.id === 'a'), 'frost', frost && frostWord(frost.hit, frost.total, 'wheat'))
  if (cur && wOk && rw && fwCorn) {
    const tones = [rw.tone, fwCorn.tone]
    cur.light = tones.includes('r') ? 'r' : tones.includes('y') ? 'y' : 'g'
    cur.lightTxt = { r: 'Risky', y: 'Caution', g: 'Good' }[cur.light]
    // Only what the real records say (no income claim: that part has no source).
    const bits = []
    if (rw.tone !== 'g') bits.push(`corn ${rw.tone === 'r' ? 'often' : 'sometimes'} gets too little rain in April–May`)
    if (fwCorn.tone !== 'g') bits.push(`frost ${fwCorn.tone === 'r' ? 'often' : 'sometimes'} hits in June–August`)
    const txt = bits.length ? `In the past records, ${bits.join(' and ')}.` : 'Rain and frost records look fine for this plan.'
    cur.verdict = real(txt, 'project rules', 'area', wMode)
  } else if (cur) {
    cur.light = 'y'
    cur.lightTxt = 'Not checked'
    cur.verdict = missing(w?.reason, POWER, 'area')
  }

  // Drawer texts (why / good / watch / unknown) are example text from the sample. Say so on screen,
  // and never contradict the numbers: the current plan's "why" is rebuilt from the real counts and
  // the "watch" lines about dry autumn / frost are dropped when the rules do not confirm them.
  for (const d of Object.values(data.details)) d.sampleText = true
  const dc = data.details.current
  if (dc && wOk) {
    const parts = []
    if (rain?.total) parts.push(`April–May rain was low in ${ofText(rain, { last: true })} years`)
    if (frost?.total) parts.push(`frost hit in June–August in ${ofText(frost, { last: true })} years`)
    dc.why = `This is what you plan today. Past records: ${parts.join(' and ')}.`
    if (rw && rw.tone === 'g') dc.watch = dc.watch.filter((x) => !/Dry April/i.test(x))
    if (fwCorn && fwCorn.tone === 'g') dc.watch = dc.watch.filter((x) => !/frost/i.test(x))
  } else if (dc) {
    dc.why = 'This is what you plan today. The rain and frost records are not available for this field.'
    dc.watch = dc.watch.filter((x) => !/Dry April|frost/i.test(x))
  }
  const da = data.details.a
  if (da && frost && frostWord(frost.hit, frost.total, 'wheat')?.tone === 'g') da.watch = da.watch.filter((x) => !/frost/i.test(x))

  // drawer evidence
  for (const d of Object.values(data.details)) {
    for (const e of d.evidence) {
      if (e.icon === 'rain') {
        e.n = wLeaf(rain && ofText(rain, { last: true }), rain)
        e.chip = { scale: 'area', source: `${POWER} ~50 km` }
      } else if (e.icon === 'frost') {
        e.text = 'Frost in June–August in {n} years'
        e.n = wLeaf(frost && ofText(frost, { last: true }), frost)
      } else if (e.icon === 'slope') {
        e.text = 'Field slope: {n}'
        e.n = cls == null ? pending() : real(`${cls} (${slopePct.toFixed(1)}%)`, 'NASADEM 30 m', 'field', terrain.source?.mode)
      }
    }
  }

  // confidence
  const rules = confidenceRules({ years: rain?.total ?? 0, weatherOk: wOk })
  data.confidence.rules = rules
  data.confidence.agree_pct = missing('A second rain source is not available yet', 'second rain source', 'area')

  data.profile = profile
  data.blocks = {
    weather: { status: w?.status, reason: w?.reason, source: w?.source },
    soil: { status: soil?.status, reason: soil?.reason, source: soil?.source },
    terrain: { status: terrain?.status, reason: terrain?.reason, source: terrain?.source }
  }
  data.info = {
    weatherNote: wOk ? weatherNote(w.source) : null,
    soilNote: okBlock(soil) ? soilNote(soil.source) : null,
    locationName: p.field?.data?.location_name ?? null,
    generatedAt: profile?.generated_at ?? null
  }
  return data
}
