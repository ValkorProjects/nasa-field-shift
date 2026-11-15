// Builds public/data/crop-catalog.json from the backend crop catalog (backend/data/crops/*.csv, generated
// from the team's 55-crop São Paulo spreadsheet). The front end uses it to build the alternative plans
// from the farmer's own crops (Results screen). Run from frontend/: node scripts/build-crop-catalog-json.cjs
const fs = require('fs')
const path = require('path')

const SRC = path.join(__dirname, '..', '..', 'backend', 'data', 'crops')
const OUT = path.join(__dirname, '..', 'public', 'data', 'crop-catalog.json')

// Minimal RFC 4180 CSV reader (quoted fields may contain commas and quotes)
function readCsv(file) {
  const text = fs.readFileSync(path.join(SRC, file), 'utf8').replace(/\r\n/g, '\n')
  const rows = []
  let row = [], field = '', q = false
  for (let i = 0; i < text.length; i++) {
    const c = text[i]
    if (q) {
      if (c === '"' && text[i + 1] === '"') { field += '"'; i++ } else if (c === '"') q = false
      else field += c
    } else if (c === '"') q = true
    else if (c === ',') { row.push(field); field = '' }
    else if (c === '\n') { row.push(field); rows.push(row); row = []; field = '' }
    else field += c
  }
  if (field || row.length) { row.push(field); rows.push(row) }
  const [head, ...data] = rows.filter((r) => r.length > 1)
  return data.map((r) => Object.fromEntries(head.map((h, i) => [h, r[i] ?? ''])))
}

// The spreadsheet's evidence text is Portuguese; the app shows a short English status + the source link.
//   alternatives: "A: milho documentado em outro recorte; B: hipótese" → part for A or B
function evidenceStatus(edge) {
  let t = edge.evidence.toLowerCase()
  if (edge.origin === 'alt_a' || edge.origin === 'alt_b') {
    const letter = edge.origin === 'alt_a' ? 'a' : 'b'
    const parts = Object.fromEntries(t.split(';').map((p) => p.trim()).filter((p) => /^(a|b|a e b):/.test(p))
      .flatMap((p) => { const [k, v] = p.split(/:(.*)/); return k === 'a e b' ? [['a', v], ['b', v]] : [[k, v]] }))
    if (parts[letter]) t = parts[letter]
  }
  if (edge.to_key === 'sorghum' && /sorgo: candidato condicional/.test(t)) return { status: 'hypothesis', note: 'Conditional candidate in the starting pairs: compare water and critical stages first' }
  if (/hip[oó]tese/.test(t)) return { status: 'hypothesis', note: 'Hypothesis to validate on the field (general reference)' }
  if (/brasil central/.test(t)) return { status: 'documented', note: 'Documented for central Brazil; still to validate in São Paulo' }
  if (/reforma/.test(t)) return { status: 'documented', note: 'Documented for sugarcane renewal' }
  if (/descrita/.test(t)) return { status: 'documented', note: 'Described succession; benefit on your field not proven' }
  if (/documentad|estudad/.test(t)) return { status: 'documented', note: 'Documented in another setting; to validate locally' }
  return { status: 'hypothesis', note: 'Hypothesis to validate on the field' }
}

const crops = Object.fromEntries(readCsv('crops.csv').map((c) => [c.key, {
  label: c.label_en, type: c.crop_type, decision: c.decision_type, url: c.url, quantitative: c.quantitative === '1'
}]))
const covers = Object.fromEntries(readCsv('covers.csv').map((c) => [c.key, { label: c.label_en }]))
const edges = readCsv('rotation_edges.csv').map((e) => ({
  from: e.from_key, to: e.to_key, via: e.via_key, origin: e.origin, url: e.url, ...evidenceStatus(e)
}))

fs.writeFileSync(OUT, JSON.stringify({
  source: 'backend/data/crops (generated from rotacoes_agricolas_SP_55_culturas.xlsx); qualitative base, not a field recipe',
  crops, covers, edges
}))
console.log('wrote', OUT, Object.keys(crops).length, 'crops,', edges.length, 'edges')
