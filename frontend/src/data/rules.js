// Business rules of the front. The backend only delivers data (POST /api/field/profile);
// every threshold and every sentence that interprets the data lives here.
// Pure functions, no Vue, no imports: easy to test in Node.

/* ---------- Rain in April–May ---------- */
// PROJECT HEURISTIC, source to be confirmed with an agronomist (not an official figure).
// A year counts as a "dry autumn" when April + May rain is below this many mm.
export const DRY_AUTUMN_MM = 150
export const AUTUMN_MONTHS = [4, 5]

// Rows come from weather_summary.data.by_year_month. A year without valid rain in both months is left out.
export function countDryAutumns(rows = []) {
  const years = new Map()
  for (const r of rows) {
    if (!AUTUMN_MONTHS.includes(r.month) || typeof r.prcp_mm !== 'number') continue
    const y = years.get(r.year) ?? { n: 0, mm: 0 }
    y.n += 1; y.mm += r.prcp_mm
    years.set(r.year, y)
  }
  let hit = 0, total = 0
  for (const y of years.values()) {
    if (y.n < AUTUMN_MONTHS.length) continue
    total += 1
    if (y.mm < DRY_AUTUMN_MM) hit += 1
  }
  return { hit, total }
}

/* ---------- Frost in June–August ---------- */
export const FROST_MONTHS = [6, 7, 8]

// Project heuristic, to be confirmed: a year counts when all three months have data; it is a hit with at least one frost day.
export function countFrostYears(rows = []) {
  const years = new Map()
  for (const r of rows) {
    if (!FROST_MONTHS.includes(r.month) || typeof r.frost_days !== 'number') continue
    const y = years.get(r.year) ?? { n: 0, days: 0 }
    y.n += 1; y.days += r.frost_days
    years.set(r.year, y)
  }
  let hit = 0, total = 0
  for (const y of years.values()) {
    if (y.n < FROST_MONTHS.length) continue
    total += 1
    if (y.days > 0) hit += 1
  }
  return { hit, total }
}

// Share of years (0–1) at which a crop starts to call it "Often" / "Sometimes". Heuristic: wheat is
// more sensitive to frost than corn. To be confirmed with an agronomist.
export const FROST_SENSITIVITY = {
  corn: { often: 0.5, sometimes: 0.2 },
  wheat: { often: 0.3, sometimes: 0.1 }
}

// Both word scales (frostWord, rainWord) and the "all three months" cut in countFrostYears are
// project heuristics, to be confirmed with an agronomist.
export function frostWord(hit, total, crop = 'corn') {
  if (!total) return null
  const t = FROST_SENSITIVITY[crop] ?? FROST_SENSITIVITY.corn
  const share = hit / total
  const word = share >= t.often ? 'Often' : share >= t.sometimes ? 'Sometimes' : 'Rarely'
  return { text: word, tone: word === 'Often' ? 'r' : word === 'Sometimes' ? 'y' : 'g' }
}

// Project heuristic, to be confirmed with an agronomist.
export function rainWord(hit, total) {
  if (!total) return null
  const share = hit / total
  if (share >= 0.5) return { text: 'Often too little', tone: 'r' }
  if (share >= 0.2) return { text: 'Sometimes too little', tone: 'y' }
  return { text: 'Usually enough', tone: 'g' }
}

export const ofText = (c, { last = false } = {}) => `${c.hit} of ${last ? 'the last ' : ''}${c.total}`

/* ---------- Soil ---------- */
const TEXTURE = { arenosa: 'sandy', media: 'medium', siltosa: 'medium', argilosa: 'clay', muito_argilosa: 'clay' }
export const textureFromGroup = (group) => TEXTURE[group] ?? null

// Slope class from the average slope in % (used when the terrain block is filled in).
export function slopeClass(pct) {
  if (typeof pct !== 'number' || !Number.isFinite(pct)) return null
  return pct < 3 ? 'flat' : pct < 8 ? 'gentle' : 'steep'
}

/* ---------- Planting ---------- */
// planting.data.<crop> is the same object as GET /api/recommendation. Choice: the first window that is
// "recommended" and has not ended yet; if it already started, the start shown is today.
export function pickPlantingWindow(rec, todayIso) {
  const w = (rec?.windows ?? []).find((x) => x.level === 'recommended' && (!todayIso || x.end >= todayIso))
  if (!w) return null
  return { start: todayIso && w.start < todayIso ? todayIso : w.start, end: w.end }
}

// Known limitation: the front counts weeks from the scenario's "today" (sample JSON), while the backend
// builds the windows with the real date (date.today()). If they differ, the first recommended window
// is cut by the scenario date here, not by the backend.
const DAY = 86400000
export function weeksUntil(todayIso, startIso) {
  const days = (Date.parse(`${startIso}T12:00:00Z`) - Date.parse(`${todayIso}T12:00:00Z`)) / DAY
  return Number.isFinite(days) ? Math.max(0, Math.round(days / 7)) : null
}

export function fmtDay(iso) {
  const d = new Date(`${iso}T12:00:00Z`)
  return isNaN(d) ? iso : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
}

/* ---------- Alert, status, confidence ---------- */
// counts: { rain: {hit,total}, frost: {hit,total} } or null when the weather is not available.
// Active when at least 3 in 10 years (30 %) had too little rain or frost. Heuristic.
export const ALERT_SHARE = 0.3

export function alertActive(counts) {
  if (!counts) return { active: false, level: null, rain: false, frost: false }
  const share = (c) => (c?.total ? c.hit / c.total : 0)
  const rain = share(counts.rain) >= ALERT_SHARE
  const frost = share(counts.frost) >= ALERT_SHARE
  const worst = Math.max(share(counts.rain), share(counts.frost))
  return { active: rain || frost, level: worst >= 0.5 ? 'r' : worst >= ALERT_SHARE ? 'y' : 'g', rain, frost }
}

export function alertTitle(a, name, crop = 'Corn') {
  if (!crop) {
    const what = a.rain && a.frost ? 'low rain and frost' : a.frost ? 'frost' : 'low rain'
    return `Past records show ${what} risk for your second crop on ${name}`
  }
  if (a.rain && a.frost) return `${crop} may get too little rain and be hurt by frost on ${name}`
  if (a.frost) return `${crop} may be hurt by frost on ${name}`
  return `${crop} may get too little rain on ${name}`
}

// Rules of "How sure are we?". `info` = { years, weatherOk, soilOk } derived by the adapter from the blocks.
export function confidenceRules({ years = 0, weatherOk = false, terrainOk = false, agree = null, soilAnswered = false } = {}) {
  return [
    years >= 10 ? { ok: true, text: '10+ years of rain data' } : { ok: false, text: 'Less than 10 years of rain data' },
    // field-level data: the slope from NASA SRTM 30 m inside the drawn field (weather stays ~50 km)
    terrainOk ? { ok: true, text: 'Field-level data: slope from NASA SRTM 30 m' }
      : { ok: false, text: weatherOk ? 'Only area data (no field-level slope yet)' : 'Weather data is not available for this field' },
    // sources agree: 2025 cross-checks of GET /api/validation (POWER vs MODIS frost, POWER vs SMAP dryness)
    agree === true ? { ok: true, text: 'NASA sources agree (POWER vs MODIS and SMAP, 2025)' }
      : agree === false ? { ok: false, text: 'NASA sources disagree for 2025 (POWER vs MODIS / SMAP)' }
        : { ok: false, text: 'No second source to cross-check here (2025 satellite area only)' },
    soilAnswered ? { ok: true, text: 'You told us your soil' } : { ok: false, text: 'Soil estimated from public maps' }
  ]
}

/* ---------- Plan ratings (estimates) ----------
 * Project heuristics, labelled as estimates on screen and to be validated with agronomists.
 * Priority fit (Good / OK / Poor) of a plan from its own data:
 *   soil   – straw of grasses (Poaceae) or a living cover protects the soil; a steep field (SRTM) lowers it
 *   water  – exposure of the second crop to dry autumns (NASA POWER rain row); no grain = Good
 *   income – grain to sell: Good, OK when a rain/frost row is red; cover crop or fallow: Poor
 *   cost   – cover crop or fallow: Good; grain crops: OK
 */
const LOWER = { Good: 'OK', OK: 'Poor', Poor: 'Poor' }
export function planFit({ noGrain = false, fallow = false, straw = false, slope = null, rainTone = null, worstTone = null } = {}) {
  let soil = noGrain && !fallow ? 'Good' : straw ? 'OK' : 'Poor'
  if (slope === 'steep') soil = LOWER[soil]
  const water = noGrain ? 'Good' : { g: 'Good', y: 'OK', r: 'Poor' }[rainTone] ?? 'OK'
  const income = noGrain ? 'Poor' : worstTone === 'r' ? 'OK' : 'Good'
  const cost = noGrain ? 'Good' : 'OK'
  return { soil, water, income, cost }
}

// Rain washing soil away: slope class (SRTM) × how much the plan covers the soil. Relative, never tons.
export function erosionWord(slope, cover) { // cover: 'living' | 'straw' | 'low' | 'bare'
  if (!slope) return null
  const score = { flat: 0, gentle: 1, steep: 2 }[slope] + { living: 0, straw: 0, low: 1, bare: 2 }[cover]
  return score <= 1 ? { text: 'Low risk', tone: 'g' } : score === 2 ? { text: 'Some risk', tone: 'y' } : { text: 'High risk', tone: 'r' }
}

// Pill of the field: r / y / g from the alert level; 'new' when there is no climate data.
export const fieldStatus = (data) => data?.alert?.level ?? 'new'
