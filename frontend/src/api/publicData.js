// Free public APIs used by the Costs screens. All of them allow browser calls (CORS) and need no key.
//
//  · IBGE SIDRA (servicodados.ibge.gov.br/api/v3/agregados)
//      839  – Municipal Agricultural Production (PAM): 2nd-crop corn area, production, yield
//      1612 – PAM, all temporary crops: production and value → price received by farmers
//      7060 – IPCA (consumer prices): 12-month change for food, chicken, eggs…
//  · IBGE localidades – municipality code from its name
//  · NASA POWER (power.larc.nasa.gov) – monthly rain (PRECTOTCORR) to find dry autumns
//  · OpenStreetMap Nominatim – which municipality a field is in
//
// Responses are cached in localStorage for 24 h so the demo keeps working with a weak connection.

const IBGE = 'https://servicodados.ibge.gov.br/api'
const TTL = 24 * 3600 * 1000

export const SOURCES = {
  pam: { name: 'IBGE PAM', url: 'https://sidra.ibge.gov.br/pesquisa/pam/tabelas' },
  ipca: { name: 'IBGE IPCA', url: 'https://sidra.ibge.gov.br/tabela/7060' },
  power: { name: 'NASA POWER', url: 'https://power.larc.nasa.gov/' }
}

// IBGE product codes
export const PRODUCTS = {
  corn2: { table: 839, cls: 114254, label: '2nd-crop corn' }, // Milho (em grão) – 2ª safra
  corn: { table: 1612, cls: 2711, label: 'corn' },
  wheat: { table: 1612, cls: 2716, label: 'wheat' },
  soybean: { table: 1612, cls: 2713, label: 'soybean' }
}
export const IPCA_ITEMS = { food: 7170, chicken: 107617, eggs: 7355, pork: 7287, milk: 12393 }

function cacheGet(key) {
  try {
    const hit = JSON.parse(localStorage.getItem(key))
    if (hit && Date.now() - hit.t < TTL) return hit.v
  } catch { /* storage blocked */ }
  return undefined
}
function cacheSet(key, v) {
  try { localStorage.setItem(key, JSON.stringify({ t: Date.now(), v })) } catch { /* full or blocked */ }
}

async function getJson(url, { signal, headers } = {}) {
  const key = 'fieldshift.pub.' + url
  const cached = cacheGet(key)
  if (cached !== undefined) return cached
  const res = await fetch(url, { signal, headers })
  if (!res.ok) throw new Error(`${new URL(url).host} answered ${res.status}`)
  const v = await res.json()
  cacheSet(key, v)
  return v
}

// IBGE marks missing values as "-", "...", "X" (secret) etc.
const num = (s) => (s != null && /^-?\d+(\.\d+)?$/.test(String(s)) ? Number(s) : null)

/**
 * One SIDRA query. Returns { [variableId]: { [locationId]: { [year]: number|null } } }.
 * loc: 'N6[3553807]' (municipality) · 'N3[35]' (state) · 'N1[all]' (Brazil); several joined with '|'.
 */
export async function sidra(table, vars, loc, { periods = '-10', cls, opt } = {}) {
  const q = new URLSearchParams({ localidades: loc })
  if (cls) q.set('classificacao', cls)
  const url = `${IBGE}/v3/agregados/${table}/periodos/${periods}/variaveis/${vars.join('|')}?${q}`
  const data = await getJson(url, opt)
  const out = {}
  for (const v of data) {
    const byLoc = (out[v.id] = {})
    for (const r of v.resultados) {
      for (const s of r.series) {
        const key = r.classificacoes?.length ? `${s.localidade.id}:${Object.keys(r.classificacoes[0].categoria)[0]}` : s.localidade.id
        byLoc[key] = Object.fromEntries(Object.entries(s.serie).map(([y, x]) => [y, num(x)]))
      }
    }
  }
  return out
}

/** Municipality (IBGE code, name, state) for a point. Nominatim reverse → IBGE localidades by name. */
export async function municipalityAt(lat, lon, opt) {
  const r = await getJson(
    `https://nominatim.openstreetmap.org/reverse?format=jsonv2&zoom=10&lat=${lat.toFixed(4)}&lon=${lon.toFixed(4)}`,
    { ...opt, headers: { 'Accept-Language': 'pt-BR' } }
  )
  const a = r.address || {}
  const name = a.city || a.town || a.municipality || a.village
  const uf = (a['ISO3166-2-lvl4'] || '').replace('BR-', '')
  if (!name || !uf) throw new Error('Could not find the municipality of this field')
  const list = await getJson(`${IBGE}/v1/localidades/estados/${uf}/municipios`, opt)
  const norm = (s) => s.normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase()
  const m = list.find((x) => norm(x.nome) === norm(name))
  if (!m) throw new Error(`IBGE has no municipality called ${name} (${uf})`)
  const ufId = String(m.id).slice(0, 2)
  return { id: String(m.id), name: m.nome, uf, ufId }
}

/**
 * April + May rain (mm) per year from NASA POWER, and which years were dry:
 * a dry autumn = April–May rain at least 25 % below the 2001–last-year average.
 */
export async function autumnRain(lat, lon, { from = 2001, to = new Date().getFullYear() - 1, opt } = {}) {
  const url = `https://power.larc.nasa.gov/api/temporal/monthly/point?parameters=PRECTOTCORR&community=AG` +
    `&longitude=${lon.toFixed(2)}&latitude=${lat.toFixed(2)}&start=${from}&end=${to}&format=JSON`
  const data = await getJson(url, opt)
  const s = data?.properties?.parameter?.PRECTOTCORR
  if (!s) throw new Error('NASA POWER returned no rain data')
  const years = {}
  for (const [k, mmPerDay] of Object.entries(s)) {
    const y = k.slice(0, 4), m = k.slice(4)
    if (mmPerDay < 0) continue // -999 = no data
    if (m === '04') (years[y] ??= {}).apr = mmPerDay * 30
    if (m === '05') (years[y] ??= {}).may = mmPerDay * 31
  }
  const mm = Object.fromEntries(
    Object.entries(years).filter(([, v]) => v.apr != null && v.may != null).map(([y, v]) => [y, Math.round(v.apr + v.may)])
  )
  const vals = Object.values(mm)
  const mean = vals.reduce((a, b) => a + b, 0) / vals.length
  const dry = Object.keys(mm).filter((y) => mm[y] < 0.75 * mean)
  return { mm, mean: Math.round(mean), dry, period: `${from}–${to}`, url }
}
