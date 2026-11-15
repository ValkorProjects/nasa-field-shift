// Costs from free public data (replaces the sample numbers on the Costs screens and the Results money bar).
//
// Field 1's municipality → IBGE PAM yields of the last 10 harvests, NASA POWER April–May rain.
//   dry autumn   = April–May rain ≥ 25 % below average (NASA POWER, ~50 km)
//   normal yield = average yield in the other years · dry yield = average in dry years
//   loss         = 1 − dry yield / normal yield (worst = the worst dry year)
//   price        = value of production ÷ quantity, latest year (IBGE PAM, price received by farmers)
//   R$           = area (your map) × yield × price · second crop only, before costs
// If any API fails the screens keep the sample values and say so.
import { reactive } from 'vue'
import { state } from '@/data/store.js'
import { farm, fieldById, areaHa } from '@/data/fields.js'
import { sidra, municipalityAt, autumnRain, conabCost, PRODUCTS, IPCA_ITEMS, SOURCES } from '@/api/publicData.js'

const BAG_KG = 60
const SCENARIO_SHARE = 50 // % of the state's 2nd-crop corn area hit, for the "big picture" scenario
const FALLBACK = { lat: -23.53, lon: -49.24 } // Taquarituba (SP), when there is no field on the map

export const costs = reactive({ status: 'idle', error: null, key: null, muni: null, info: null })

const leaf = (value, source, scale = 'area', extra = {}) => ({ value, sample: false, source, scale, ...extra })
const mean = (a) => (a.length ? a.reduce((s, x) => s + x, 0) / a.length : NaN)
const money = (x) => Math.round(x / 100) * 100
const fmt = (x) => money(x).toLocaleString('en-US')
const MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
const enMonth = (s = '') => { const [m, y] = s.split('/'); const i = MESES.indexOf(m?.toLowerCase()); return i >= 0 ? `${MONTHS[i]} ${y}` : s }
const pct = (x) => Math.round(x * 100)

function fieldPoint() {
  const f = fieldById('1') ?? farm.fields[0]
  if (!f?.coords?.length) return { ...FALLBACK, area: NaN }
  const lat = mean(f.coords.map((c) => c[0]))
  const lon = mean(f.coords.map((c) => c[1]))
  return { lat, lon, area: areaHa(f.coords) }
}

/** Yields (kg/ha) by year; falls back to the state when the municipality has fewer than 5 harvests. */
function pickSeries(byLoc, muniKey, stateKey) {
  const m = byLoc?.[muniKey] ?? {}
  const n = Object.values(m).filter((v) => v != null).length
  return n >= 5 ? { s: m, level: 'muni' } : { s: byLoc?.[stateKey] ?? {}, level: 'state' }
}

/** normal / dry / worst yields given the dry years. */
function yieldStats(series, dryYears) {
  const yrs = Object.keys(series).filter((y) => series[y] != null)
  const dry = yrs.filter((y) => dryYears.includes(y))
  const wet = yrs.filter((y) => !dryYears.includes(y))
  const normal = mean(wet.map((y) => series[y]))
  const dryY = mean(dry.map((y) => series[y]))
  const worstYear = dry.reduce((a, y) => (a == null || series[y] < series[a] ? y : a), null)
  return {
    years: yrs, dryCount: dry.length, normal, dry: dryY, avg: mean(yrs.map((y) => series[y])),
    worst: worstYear ? series[worstYear] : NaN, worstYear,
    loss: Math.max(0, 1 - dryY / normal), worstLoss: Math.max(0, 1 - series[worstYear] / normal)
  }
}

/** Price per bag (R$) from value (thousand R$) ÷ quantity (t), latest year with both. */
function priceOf(qty, val) {
  const years = Object.keys(qty ?? {}).filter((y) => qty[y] && val?.[y]).sort()
  const y = years.at(-1)
  return y ? { perBag: ((val[y] * 1000) / qty[y]) * (BAG_KG / 1000), year: y } : null
}

export async function loadCosts({ force = false } = {}) {
  const p = fieldPoint()
  const key = `${p.lat.toFixed(3)},${p.lon.toFixed(3)},${p.area.toFixed(2)}`
  if (!force && costs.key === key && (costs.status === 'ok' || costs.status === 'loading')) return
  if (!state.data) return
  costs.status = 'loading'; costs.error = null; costs.key = key
  try {
    const muni = await municipalityAt(p.lat, p.lon)
    const N6 = `N6[${muni.id}]`, N3 = `N3[${muni.ufId}]`
    const [c2, crops, rain, cornCostRaw, wheatCostRaw] = await Promise.all([
      sidra(839, [112, 109, 214], `${N6}|${N3}|N1[all]`, { cls: `81[${PRODUCTS.corn2.cls}]` }),
      sidra(1612, [112, 214, 215], `${N6}|${N3}`, { cls: `81[${PRODUCTS.corn.cls},${PRODUCTS.wheat.cls}]` }),
      autumnRain(p.lat, p.lon),
      conabCost('corn2', p.lat, p.lon).catch(() => null),
      conabCost('wheat', p.lat, p.lon).catch(() => null)
    ])
    if (costs.key !== key) return // the field changed meanwhile
    const withMonth = (c) => c && { ...c, month: enMonth(c.month) }
    const cornCost = withMonth(cornCostRaw), wheatCost = withMonth(wheatCostRaw)

    const k = (loc, cls) => `${loc}:${cls}`
    const ibgeYears = Object.keys(c2[112]?.[k(muni.id, PRODUCTS.corn2.cls)] ?? {})
    const dryYears = rain.dry.filter((y) => ibgeYears.includes(y))
    const N = ibgeYears.filter((y) => rain.mm[y] != null).length

    // ---- crops ----
    const cornS = pickSeries(c2[112], k(muni.id, PRODUCTS.corn2.cls), k(muni.ufId, PRODUCTS.corn2.cls))
    const wheatS = pickSeries(crops[112], k(muni.id, PRODUCTS.wheat.cls), k(muni.ufId, PRODUCTS.wheat.cls))
    const corn = yieldStats(cornS.s, dryYears)
    const wheat = yieldStats(wheatS.s, dryYears)
    const priceLoc = (cls) => {
      const m = priceOf(crops[214]?.[k(muni.id, cls)], crops[215]?.[k(muni.id, cls)])
      return m ? { ...m, level: 'muni' } : { ...priceOf(crops[214]?.[k(muni.ufId, cls)], crops[215]?.[k(muni.ufId, cls)]), level: 'state' }
    }
    const cornP = priceLoc(PRODUCTS.corn.cls)
    const wheatP = priceLoc(PRODUCTS.wheat.cls)
    if (!Number.isFinite(corn.normal) || !cornP?.perBag) throw new Error(`IBGE has no corn data for ${muni.name}`)

    const where = (lvl) => (lvl === 'muni' ? muni.name : `${muni.uf} state`)
    const span = `${corn.years[0]}–${corn.years.at(-1)}`
    const srcY = (lvl) => `IBGE PAM ${span} · ${where(lvl)}`
    const area = p.area
    const income = (yKg, price) => area * (yKg / BAG_KG) * price

    // ---- screen 9: your money ----
    const m = state.data.money
    m.at_risk_min = leaf(fmt(income(corn.normal - corn.dry, cornP.perBag)), 'IBGE PAM + NASA POWER', 'est')
    m.at_risk_max = leaf(fmt(income(corn.normal - corn.worst, cornP.perBag)), 'IBGE PAM + NASA POWER', 'est')
    m.dry_years = leaf(`${corn.dryCount} of the last ${N}`, 'NASA POWER')
    m.worst_year = leaf(corn.worstYear, srcY(cornS.level))
    const inp = Object.fromEntries(m.inputs.map((i) => [i.id, i]))
    inp.yield.v = leaf(+(corn.normal / BAG_KG).toFixed(1), `IBGE PAM, normal years`)
    inp.price.v = leaf(+cornP.perBag.toFixed(2), `IBGE PAM ${cornP.year}`)
    inp.loss.v = leaf(+(corn.loss * 100).toFixed(1), 'IBGE + NASA POWER', 'est')
    const costSrc = (c) => `CONAB ${c.town}-${c.uf} ${c.month.split(' ')[1] ?? c.season}`
    inp.cost.v = cornCost
      ? leaf(cornCost.variable, costSrc(cornCost), 'area', { ref: cornCost })
      : { value: '—', sample: false, source: 'no recent CONAB data', scale: 'field', empty: true }

    for (const s of state.data.strategies) {
      const name = String(s.name?.value ?? s.name)
      const crop = /corn/i.test(name) ? { st: corn, pr: cornP, lvl: cornS.level, cost: cornCost }
        : /wheat/i.test(name) ? { st: wheat, pr: wheatP, lvl: wheatS.level, cost: wheatCost } : null
      if (!crop || !Number.isFinite(crop.st.normal) || !crop.pr?.perBag) {
        // cover crop: no grain to sell
        s.money.dry = leaf('0', 'no grain sold', 'book')
        s.money.normal = leaf('0', 'no grain sold', 'book')
        s.money.avg = leaf('0', 'no grain sold', 'book')
        continue
      }
      const src = `${srcY(crop.lvl)} × price ${crop.pr.year}`
      s.money.dry = leaf(fmt(income(crop.st.dry, crop.pr.perBag)), `${src} · ${crop.st.dryCount} dry years`, 'est')
      s.money.normal = leaf(fmt(income(crop.st.normal, crop.pr.perBag)), src)
      s.money.avg = leaf(fmt(income(crop.st.avg, crop.pr.perBag)), src)
      s.money.loss = pct(crop.st.loss)
      if (crop.cost) {
        // what is left after the cash cost to grow (CONAB variable cost: seed, fertiliser, sprays, machines, interest)
        const spent = area * crop.cost.variable
        s.money.cost = leaf(fmt(spent), costSrc(crop.cost))
        s.money.net_normal = leaf(fmt(income(crop.st.normal, crop.pr.perBag) - spent), `${src} − CONAB`, 'est')
        s.money.net_dry = leaf(fmt(income(crop.st.dry, crop.pr.perBag) - spent), `${src} − CONAB`, 'est')
      }
    }

    // ---- screen 10: big picture (state level) ----
    const stProd = c2[214]?.[k(muni.ufId, PRODUCTS.corn2.cls)] ?? {}
    const stArea = c2[109]?.[k(muni.ufId, PRODUCTS.corn2.cls)] ?? {}
    const brProd = c2[214]?.[k('1', PRODUCTS.corn2.cls)] ?? {}
    const yrs = Object.keys(stProd).filter((y) => stProd[y]).sort()
    const last = yrs.at(-1)
    let past = null
    for (let i = 1; i < yrs.length; i++) {
      const drop = 1 - stProd[yrs[i]] / stProd[yrs[i - 1]]
      if (!past || drop > past.drop) past = { year: yrs[i], prev: yrs[i - 1], drop }
    }
    // price change that year: state corn price (value ÷ quantity), same year vs year before
    const stQ = crops[214]?.[k(muni.ufId, PRODUCTS.corn.cls)] ?? {}
    const stV = crops[215]?.[k(muni.ufId, PRODUCTS.corn.cls)] ?? {}
    const pr = (y) => (stQ[y] && stV[y] ? stV[y] / stQ[y] : NaN)
    const priceRise = past ? pr(past.year) / pr(past.prev) - 1 : NaN

    const r = state.data.regional
    const stYield = stProd[last] / stArea[last] // t/ha
    r.share = leaf(SCENARIO_SHARE, 'scenario', 'est')
    r.area = leaf(Math.round((stArea[last] * SCENARIO_SHARE) / 100 / 1000), `IBGE PAM ${last} × ${SCENARIO_SHARE}%`)
    r.tonnes = leaf(Math.round((stArea[last] * SCENARIO_SHARE / 100 * stYield * corn.loss) / 1000), 'area × yield × loss', 'est')
    r.share_br = leaf(+((stProd[last] / brProd[last]) * 100).toFixed(1), `IBGE PAM ${last}`)
    r.uf = muni.uf
    if (past) {
      r.past_year = leaf(past.year, 'IBGE PAM')
      r.past_drop = leaf(pct(past.drop), 'IBGE PAM')
      r.past_price = leaf(Number.isFinite(priceRise) ? pct(priceRise) : '—', 'IBGE PAM, price received')
      r.past_rain = rain.dry.includes(past.year) ? rain.mm[past.year] : null
      r.rain_mean = rain.mean
      r.food = await foodPrices(past.year)
    }

    costs.muni = muni
    costs.info = {
      span, rainPeriod: rain.period, dryYears, rainMean: rain.mean, cornLevel: cornS.level,
      costRefs: [cornCost && { crop: 'corn', ...cornCost }, wheatCost && { crop: 'wheat', ...wheatCost }].filter(Boolean),
      sources: [SOURCES.pam, SOURCES.power, ...(cornCost || wheatCost ? [SOURCES.conab] : []), ...(r.food ? [SOURCES.ipca] : [])]
    }
    costs.status = 'ok'
  } catch (e) {
    if (costs.key !== key) return
    costs.status = 'error'
    costs.error = e.message || String(e)
  }
}

/** IPCA 12-month change in December of that year (the table starts in 2020). */
async function foodPrices(year) {
  if (+year < 2020) return null
  try {
    const ids = [IPCA_ITEMS.food, IPCA_ITEMS.chicken, IPCA_ITEMS.eggs]
    const d = await sidra(7060, [2265], 'N1[all]', { periods: `${year}12`, cls: `315[${ids.join(',')}]` })
    const v = (id) => d[2265]?.[`1:${id}`]?.[`${year}12`]
    const r1 = (x) => (x == null ? null : Math.round(x * 10) / 10)
    return { year, food: r1(v(IPCA_ITEMS.food)), chicken: r1(v(IPCA_ITEMS.chicken)), eggs: r1(v(IPCA_ITEMS.eggs)) }
  } catch {
    return null
  }
}
