// Builds public/data/conab-costs.json from CONAB's cost-of-production series (free, open data).
// CONAB has no API: it publishes one .xls per crop, one sheet per reference town and season.
//
//   Source page: https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/planilhas-de-custos-de-producao/copy_of_agricolas
//
// Run (from frontend/):
//   npm i --no-save xlsx@0.18.5
//   node scripts/build-conab-costs.cjs
// Downloads the files, reads every sheet, geocodes each town once (OpenStreetMap Nominatim, 1 request/s)
// and writes public/data/conab-costs.json.
const fs = require('fs')
const path = require('path')
const XLSX = require('xlsx')

const BASE = 'https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas'
const FILES = {
  corn2: `${BASE}/milho/milho_2a_safra_serie_historica_2005-2026.xls`,
  wheat: `${BASE}/seriehistoricacustostrigo1998a2025.xls`
}
const OUT = path.join(__dirname, '..', 'public', 'data', 'conab-costs.json')
// CONAB abbreviates some town names in the sheet titles
const FULL_NAME = {
  'P. do Leste': 'Primavera do Leste',
  'C. Novo do Parecis': 'Campo Novo do Parecis',
  'M. Cândido Rondon': 'Marechal Cândido Rondon',
  'São  Luis Gonzaga': 'São Luiz Gonzaga',
  'São Luis Gonzaga': 'São Luiz Gonzaga'
}
const sleep = (ms) => new Promise((r) => setTimeout(r, ms))

const brl = (s) => Number(String(s).replace(/\./g, '').replace(',', '.'))
function readSheet(ws) {
  const rows = XLSX.utils.sheet_to_json(ws, { header: 1, blankrows: false })
  const text = (i) => String(rows[i]?.[0] ?? '').trim()
  const find = (re) => rows.find((r) => re.test(String(r[0] ?? '')))?.[1]
  const yieldTxt = rows.flat().map(String).find((c) => /Produtividade M[ée]dia/i.test(c)) || ''
  const month = rows.flat().map(String).find((c) => /M[êe]s\/Ano/i.test(c)) || ''
  const out = {
    system: text(1),
    month: month.replace(/M[êe]s\/Ano:\s*/i, '').trim(),
    yield_kg_ha: brl((yieldTxt.match(/([\d.,]+)\s*kg/i) || [])[1]),
    variable: find(/^CUSTO VARI[ÁA]VEL/i),
    operational: find(/^CUSTO OPERACIONAL/i),
    total: find(/^CUSTO TOTAL/i)
  }
  return Number.isFinite(out.variable) && out.variable > 0 ? out : null
}

async function geocode(name, uf) {
  const q = new URLSearchParams({ format: 'json', limit: '1', countrycodes: 'br', city: name, state: uf, country: 'Brazil' })
  const res = await fetch(`https://nominatim.openstreetmap.org/search?${q}`, { headers: { 'User-Agent': 'field-shift-data-build/1.0' } })
  const [hit] = await res.json()
  await sleep(1100)
  return hit ? [+(+hit.lat).toFixed(4), +(+hit.lon).toFixed(4)] : null
}

;(async () => {
  const prev = fs.existsSync(OUT) ? JSON.parse(fs.readFileSync(OUT, 'utf8')) : null
  const coords = Object.fromEntries((prev?.locations ?? []).map((l) => [`${l.name}-${l.uf}`, [l.lat, l.lon]]))
  const crops = {}
  const locations = {}
  for (const [crop, url] of Object.entries(FILES)) {
    console.log('download', url)
    const buf = Buffer.from(await (await fetch(url)).arrayBuffer())
    const wb = XLSX.read(buf, { type: 'buffer' })
    const byLoc = {}
    for (const sheet of wb.SheetNames) {
      const m = sheet.match(/^(.*)-([A-Z]{2})-(\d{4})(?:-(\d{2}))?$/)
      if (!m) continue
      const name = FULL_NAME[m[1]] ?? m[1].replace(/\s+/g, ' ').trim()
      const r = readSheet(wb.Sheets[sheet])
      if (!r) continue
      const key = `${name}-${m[2]}`
      ;(byLoc[key] ??= { name, uf: m[2], seasons: [] }).seasons.push({ season: m[4] ? `${m[3]}-${m[4]}` : m[3], ...r })
      locations[key] ??= { name, uf: m[2] }
    }
    for (const l of Object.values(byLoc)) l.seasons.sort((a, b) => a.season.localeCompare(b.season))
    crops[crop] = { url, towns: byLoc }
  }
  for (const [key, l] of Object.entries(locations)) {
    const c = coords[key] ?? (await geocode(l.name, l.uf))
    if (!c) console.warn('no coordinates for', key)
    ;[l.lat, l.lon] = c ?? [null, null]
  }
  const out = {
    source: 'CONAB – Custos de produção, série histórica (agricultura). Free to use with attribution.',
    page: 'https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/planilhas-de-custos-de-producao/copy_of_agricolas',
    built: new Date().toISOString().slice(0, 10),
    units: 'R$ per hectare, nominal (value of the season month); yield in kg/ha',
    locations: Object.entries(locations).map(([key, l]) => ({ key, ...l })),
    crops: Object.fromEntries(Object.entries(crops).map(([crop, c]) => [crop, {
      url: c.url,
      towns: Object.fromEntries(Object.entries(c.towns).map(([k, t]) => [k, t.seasons.map((s) => ({
        season: s.season, month: s.month, system: s.system, yield_kg_ha: s.yield_kg_ha,
        variable: Math.round(s.variable), operational: Math.round(s.operational), total: Math.round(s.total)
      }))]))
    }]))
  }
  fs.writeFileSync(OUT, JSON.stringify(out, null, 1))
  console.log('wrote', OUT, Object.keys(locations).length, 'towns')
})()
