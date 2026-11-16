// The 3 plans on the Results screen, built from the farmer's own crops (not a fixed example).
//   Current plan = the summer and second crops the farmer chose.
//   Options A and B = what our São Paulo crop catalog lists after the summer crop
//     (public/data/crop-catalog.json, from the team's 55-crop spreadsheet), each with its evidence
//     status: "documented" or "hypothesis to validate".
//   If the catalog gives fewer than 2 grain options, a cover crop fills the gap.
// Numbers only where RollCrop has rules: corn (rain + frost), wheat (frost) and the cover crop reuse
// their existing cards (real NASA POWER rows when the backend answered, sample values otherwise).
// Any other crop is "Not rated yet": no invented Good/OK/Poor, and it is left out of "Best for you".
import { shallowRef } from 'vue'
import { countDryAutumns, countFrostYears, rainWord, frostWord, ofText } from './rules.js'

export const catalog = shallowRef(null)
export async function loadCatalog() {
  try {
    const res = await fetch('/data/crop-catalog.json')
    if (res.ok) catalog.value = await res.json()
  } catch { /* no catalog: alternatives stay the sample ones */ }
}

// crop ids of the wizard → catalog keys
const KEY = { soy: 'soybean', corn: 'corn', beans: 'dry_bean', wheat: 'wheat', cover: 'cover', empty: 'fallow' }
// crops that have a card with RollCrop rules (id of the sample strategy to reuse)
const TEMPLATE = { corn: 'current', wheat: 'a', cover: 'b' }
const IMG = { soybean: '/img/soja.jpg', corn: '/img/milho.jpg', dry_bean: '/img/feijao.jpg', wheat: '/img/trigo.jpg', cover: '/img/cover.jpg', fallow: '/img/palha.jpg' }
const LABEL = { cover: 'Cover crop', fallow: 'Fallow (left empty)', dry_bean: 'Beans' }
const LEGUMES = new Set(['soybean', 'dry_bean', 'peanut']) // fix nitrogen (crop knowledge)
const RANK = { documented_pair: 0, alt_a: 1, alt_b: 2 }
const STATUS_TXT = { documented: 'Documented', hypothesis: 'Hypothesis to validate' }

const label = (key) => LABEL[key] ?? catalog.value?.crops?.[key]?.label ?? key
const leaf = (value, source, scale = null) => ({ value, sample: false, source, scale })

// Grain crops that can follow the summer crop, best evidence first (documented pairs, then A, then B)
function successors(summer) {
  const cat = catalog.value
  if (!cat) return []
  const ok = (k) => cat.crops[k]?.type === 'temporary' && cat.crops[k]?.decision === 'succession'
  const best = new Map()
  for (const e of cat.edges) {
    if (e.from !== summer || !ok(e.to) || e.to === summer) continue
    const cur = best.get(e.to)
    const better = !cur || (cur.status !== 'documented' && e.status === 'documented') ||
      (cur.status === e.status && RANK[e.origin] < RANK[cur.origin])
    if (better) best.set(e.to, e)
  }
  return [...best.values()].sort((a, b) =>
    (a.status === b.status ? 0 : a.status === 'documented' ? -1 : 1) || RANK[a.origin] - RANK[b.origin])
}

function notRated(base, crop) {
  const NA = 'RollCrop has no rules for this crop yet'
  return {
    ...base,
    light: 'x', lightTxt: 'Not rated',
    verdict: leaf(`No risk rules for ${label(crop).toLowerCase()} in RollCrop yet. Check the reference and your agronomist.`, 'crop catalog'),
    rows: base.rows.map((r) => ({ ...r, answer: { value: 'Not assessed', sample: false, unavailable: NA, source: 'no rules yet', scale: 'est' }, tone: 'x' })),
    fit: null,
    nodata: true,
    evidence: { scale: 'book', source: 'crop catalog', text: 'Listed in our São Paulo rotation catalog.', n: null }
  }
}

function buildPlan(data, id, tag, summer, crop, edge) {
  const tplId = TEMPLATE[crop]
  const tpl = data.strategies.find((s) => s.id === (tplId ?? 'current'))
  let s = structuredClone(tpl)
  let d = structuredClone(data.details[tplId ?? 'current'])
  if (!tplId) {
    s = notRated(s, crop)
    d = {
      why: `${label(crop)} is listed after ${label(summer).toLowerCase()} in our São Paulo rotation catalog.`,
      evidence: [], nodata: `RollCrop does not compute rain, frost or soil risks for ${label(crop).toLowerCase()} yet.`,
      good: [], watch: [], unknown: ['How this crop does on your field and in your area', 'Its income and costs here'],
      sampleText: false
    }
  }
  // the corn card's texts speak about "what you plan today": reword them when corn is an alternative
  if (tplId === 'current' && id !== 'current') {
    d.why = `Second-crop corn after ${label(summer).toLowerCase()}: it earns grain income, but it needs rain in April–May and fears frost in June–August.`
    if (s.verdict?.sample) s.verdict = { ...s.verdict, value: 'Grain income, but corn needs rain in April–May and fears frost.' }
  }
  // nitrogen: crop knowledge (legumes fix nitrogen), so it follows the plan's own crops
  const nitro = s.rows?.find((r) => r.icon === 'nitro')
  if (nitro) {
    const legumes = [summer, crop].filter((k) => LEGUMES.has(k)).map((k) => label(k))
    if (crop === 'cover') legumes.push('sunn hemp')
    nitro.answer = { value: legumes.length ? (legumes.length > 1 ? `Yes: ${legumes.join(' and ').toLowerCase()}` : `${legumes[0]} only`) : 'No legume', sample: false, source: 'crop fact', scale: 'book' }
    nitro.tone = legumes.length > 1 ? 'g' : legumes.length ? 'y' : 'r'
  }
  s.id = id
  s.tag = tag
  s.name = leaf(`${label(summer)} → ${label(crop)}`, edge ? 'crop catalog' : 'your answers')
  s.longName = `${label(summer).toLowerCase()} → ${label(crop).toLowerCase()}`
  s.photos = [{ img: IMG[summer] ?? null, cap: label(summer) }, { img: IMG[crop] ?? null, cap: label(crop) }]
  s.catalog = edge
    ? { status: edge.status, statusTxt: STATUS_TXT[edge.status], note: edge.note, url: edge.url }
    : crop === 'cover' ? { status: 'reference', statusTxt: 'Green-manure reference', note: 'Cover crop between seasons; choose the species for your window, water and pests', url: null } : null
  if (s.catalog) d.why = `${d.why} <br><small>Catalog: <b>${s.catalog.statusTxt}</b> · ${s.catalog.note}${s.catalog.url ? ` · <a href="${s.catalog.url}" target="_blank" rel="noopener">reference</a>` : ''}</small>`
  return [s, d]
}

/* ---------- independent rating of each plan with the field's NASA POWER records ----------
 * Each plan's second crop is checked against its own risks from the catalog (risk_keys):
 *   rain row  → dry autumns (April + May < 150 mm), only if the crop lists a drought risk
 *   frost row → frost years (a day ≤ 3 °C in June–August), only if the crop lists frost
 *   a risk the crop does not list → "Not a key risk"; a cover crop → "No grain at risk"
 * Light and verdict come from these two rows. Thresholds: rules.js (rainWord, frostWord). */
const DROUGHT = ['reproductive_drought', 'establishment_drought']
const FROST_SENSITIVE = new Set(['wheat', 'oat', 'barley', 'triticale']) // winter cereals: stricter frost scale

function weatherCounts(data) {
  const p = data?.profile
  const rows = p && !p.mock && p.weather_summary?.status === 'ok' ? p.weather_summary.data?.by_year_month : null
  if (!rows) return null
  const rain = countDryAutumns(rows), frost = countFrostYears(rows)
  return rain.total && frost.total ? { rain, frost, mode: p.weather_summary.source?.mode ?? null } : null
}

function rate(s, crop, counts) {
  const src = (word) => ({ sample: false, source: 'NASA POWER', scale: 'area', mode: counts.mode, value: word })
  const notKey = { value: 'Not a key risk', sample: false, source: 'crop catalog', scale: 'book' }
  const noGrain = { value: 'No grain at risk', sample: false, source: 'crop fact', scale: 'book' }
  const risks = crop === 'cover' ? [] : catalog.value?.crops?.[crop]?.risks ?? []
  const set = (icon, answer, tone) => { const r = s.rows.find((x) => x.icon === icon); if (r) { r.answer = answer; r.tone = tone } }
  const out = {}
  if (crop === 'cover' || crop === 'fallow') {
    set('rain', noGrain, 'g'); set('frost', noGrain, 'g')
  } else {
    if (risks.some((r) => DROUGHT.includes(r))) {
      const w = rainWord(counts.rain.hit, counts.rain.total); set('rain', src(w.text), w.tone); out.rain = w
    } else set('rain', notKey, 'g')
    if (risks.includes('frost')) {
      const w = frostWord(counts.frost.hit, counts.frost.total, FROST_SENSITIVE.has(crop) ? 'wheat' : 'corn'); set('frost', src(w.text), w.tone); out.frost = w
    } else set('frost', notKey, 'g')
  }
  const tones = [out.rain?.tone, out.frost?.tone].filter(Boolean)
  s.light = tones.includes('r') ? 'r' : tones.includes('y') ? 'y' : 'g'
  s.lightTxt = { r: 'Risky', y: 'Caution', g: 'Good' }[s.light]
  const name = label(crop).toLowerCase()
  const bits = []
  if (out.rain && out.rain.tone !== 'g') bits.push(`${name} ${out.rain.tone === 'r' ? 'often' : 'sometimes'} ${name.endsWith('s') ? 'get' : 'gets'} too little rain in April–May (${ofText(counts.rain, { last: true })} years)`)
  if (out.frost && out.frost.tone !== 'g') bits.push(`frost ${out.frost.tone === 'r' ? 'often' : 'sometimes'} hits in June–August (${ofText(counts.frost, { last: true })} years)`)
  s.verdict = { value: crop === 'cover' || crop === 'fallow' ? 'No grain to lose to dry autumns or frost.'
    : bits.length ? `In the past records, ${bits.join(' and ')}.` : `Rain and frost records look fine for ${name}.`,
    sample: false, source: 'NASA POWER + crop catalog', scale: 'area' }
  s.rated = true
}

/** The field data with the 3 plans rebuilt from the farmer's crops (unchanged until both are chosen). */
export function withPlans(data, crops) {
  if (!data?.strategies || !crops?.summer || !crops?.second) return data
  const summer = KEY[crops.summer] ?? crops.summer
  const second = KEY[crops.second] ?? crops.second

  const options = []
  for (const e of successors(summer)) if (e.to !== second && options.length < 2) options.push([e.to, e])
  if (options.length < 2 && second !== 'cover') options.push(['cover', null])
  if (!catalog.value) { // no catalog: keep the sample alternatives
    options.length = 0
    options.push(['wheat', null], ['cover', null])
  }

  const plans = [['current', 'Your current plan', second, null], ...options.slice(0, 2).map(([c, e], i) => [['a', 'b'][i], `Option ${'AB'[i]}`, c, e])]
  const strategies = [], details = {}
  const counts = weatherCounts(data)
  for (const [id, tag, crop, edge] of plans) {
    const [s, d] = buildPlan(data, id, tag, summer, crop, edge)
    if (counts) rate(s, crop, counts)
    strategies.push(s)
    details[id] = d
  }
  return { ...data, strategies, details }
}
