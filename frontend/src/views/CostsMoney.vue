<script setup>
// Screen 9 · Costs: your money.
// Loss (FAO-33): 1 − Ya/Ym = Ky (1 − ETa/ETm); R$ lost = area × yield × loss% × price.
// Numbers come from free public data (IBGE PAM, NASA POWER; see data/costs.js).
// The farmer can type their own numbers; the headline always uses what is shown.
import { computed, reactive, ref, nextTick, onMounted } from 'vue'
import AppShell from '@/components/AppShell.vue'
import CostTabs from '@/components/CostTabs.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import SampleValue from '@/components/SampleValue.vue'
import PublicDataNote from '@/components/PublicDataNote.vue'
import { state } from '@/data/store.js'
import { fieldById, areaHa, fmtHa } from '@/data/fields.js'
import { costs, loadCosts, withCosts } from '@/data/costs.js'

onMounted(() => loadCosts())
const real = computed(() => costs.status === 'ok')

const data = computed(() => withCosts(state.data))
const m = computed(() => data.value.money)
const plans = computed(() => data.value.strategies)

// farmer's own numbers (override the public data)
const own = reactive({})
const editing = ref(null)
const inputEl = ref(null)
async function edit(id) {
  editing.value = id
  await nextTick()
  inputEl.value?.[0]?.focus()
}
function commit(id, e) {
  const n = parseFloat(String(e.target.value).replace(',', '.'))
  if (Number.isFinite(n) && n >= 0) own[id] = n
  else delete own[id]
  editing.value = null
}
// Field area comes from the polygon drawn on the map (real, not sample).
const mapArea = computed(() => {
  const f = fieldById('1')
  return f ? { value: +fmtHa(areaHa(f.coords)), sample: false, source: 'your map', scale: 'field' } : null
})
const shown = (inp) => {
  if (inp.id in own) return { value: own[inp.id], sample: false }
  if (inp.id === 'area' && mapArea.value) return mapArea.value
  return inp.v
}
const num = (id) => {
  const inp = m.value.inputs.find((i) => i.id === id)
  const v = val(shown(inp))
  return typeof v === 'number' ? v : NaN
}
function val(x) { return x && typeof x === 'object' ? x.value : x }

const userLoss = computed(() => {
  // same number as the Results money bar until the farmer types their own
  if (real.value && !typedOwn.value) return m.value.at_risk_min.value
  const r = num('area') * num('yield') * (num('loss') / 100) * num('price')
  return Number.isFinite(r) ? (Math.round(r / 100) * 100).toLocaleString('en-US') : null
})
const neg = (x) => String(val(x)).startsWith('-')
const brl = (x) => (neg(x) ? `−R$ ${String(val(x)).slice(1)}` : `R$ ${val(x)}`)
const typedOwn = computed(() => Object.keys(own).length > 0)
const editValue = (inp) => {
  const v = val(shown(inp))
  return typeof v === 'number' && !inp.v.empty ? v : ''
}
</script>

<template>
  <AppShell active="fields" crumb="My fields › Field 1 › Costs" title="What if nothing changes?">
    <div class="cost">
      <CostTabs active="money" />
      <PublicDataNote />

      <div class="headline">
        <div class="hic"><Icon name="warn" /></div>
        <div>
          <div class="hk">If you keep corn and the autumn is dry</div>
          <div class="hv">Field 1 could lose
            <b v-if="userLoss">R$ {{ userLoss }}</b>
            <b v-else>R$ <SampleValue :v="m.at_risk_min" /> – <SampleValue :v="m.at_risk_max" /></b>
          </div>
          <div class="hs">
            <template v-if="typedOwn">With your numbers. </template>
            Compared with a normal year. Dry autumns happened in <SampleValue :v="m.dry_years" /> years.
            <Chip scale="area" :source="real ? 'NASA POWER' : 'GPM'" />
            <template v-if="real && m.worst_year">In the worst one ({{ m.worst_year.value }}) the loss would be R$ {{ m.at_risk_max.value }}.</template>
            Past records, not a forecast.
          </div>
        </div>
      </div>

      <div class="pcs">
        <div v-for="p in plans" :key="p.id" :class="['pc', `o${p.light}`, { cur: p.id === 'current' }]">
          <div v-if="p.id === 'current'" class="star red">If nothing changes</div>
          <div class="k">{{ p.tag }}</div>
          <div class="nm"><SampleValue :v="p.name" :dotted="false" /></div>
          <div class="dry"><span>In a dry autumn</span><b>R$ <SampleValue :v="p.money.dry" /></b></div>
          <div class="mini2">
            <div><span>Normal autumn</span><b>R$ <SampleValue :v="p.money.normal" /></b></div>
            <div><span>10-year average</span><b>R$ <SampleValue :v="p.money.avg" /></b></div>
          </div>
          <div v-if="real && p.money.net_normal" class="netrow" :title="`Cost to grow: ${p.money.cost.source}`">
            After the cost to grow (R$ {{ p.money.cost.value }}):
            <b :class="{ neg: neg(p.money.net_normal) }">{{ brl(p.money.net_normal) }}</b> normal · <b :class="{ neg: neg(p.money.net_dry) }">{{ brl(p.money.net_dry) }}</b> dry
          </div>
          <div class="pnote">{{ p.money.note }}<template v-if="real && p.money.loss != null"> Past dry autumns cut it by {{ p.money.loss }}%.</template></div>
        </div>
      </div>
      <div v-if="real" class="pcfoot">Income from the second crop on your {{ val(shown(m.inputs[0])) }} ha: past yields of this town × the price farmers received.
        Cost to grow = CONAB cash cost per hectare in the nearest reference town<template v-for="c in costs.info.costRefs" :key="c.crop"> · {{ c.crop }}: {{ c.town }}-{{ c.uf }}, {{ c.month }}, {{ c.km }} km</template>.</div>

      <div class="card">
        <div class="inh"><div class="h2" style="margin:0">Numbers we used</div><span>Filled from public data. Click a number to use your own.</span></div>
        <div class="inps">
          <div v-for="inp in m.inputs" :key="inp.id" class="inp">
            <span :id="`lbl-${inp.id}`">{{ inp.label }}</span>
            <input v-if="editing === inp.id" ref="inputEl" class="inedit" type="number" min="0" step="any"
              :aria-labelledby="`lbl-${inp.id}`" :value="editValue(inp)"
              @focus="$event.target.select()" @blur="commit(inp.id, $event)" @keydown.enter="$event.target.blur()" @keydown.esc="editing = null" />
            <button v-else class="inbtn" :aria-label="`Change ${inp.label}`" @click="edit(inp.id)">
              <b v-if="inp.v.empty && !(inp.id in own)"><span class="typeyours">Type yours</span><Icon name="pencil" /></b>
              <b v-else><span>{{ inp.prefix }}<SampleValue :v="shown(inp)" />{{ inp.suffix }}</span><Icon name="pencil" /></b>
            </button>
            <Chip v-if="!(inp.id in own)" :scale="inp.v.scale" :source="inp.v.source" />
            <span v-else class="chip2 c-field" title="your own number">your number</span>
          </div>
        </div>
      </div>

      <div class="notr2">
        <b>Not counted in R$, but real:</b>
        <span class="chipx"><Icon name="erosion" />Soil kept on the field</span>
        <span class="chipx"><Icon name="nitro" />Nitrogen for the next soybean</span>
        <span class="chipx"><Icon name="straw" />Straw that holds water</span>
      </div>
      <div class="disc"><Icon name="info" />Town and state averages, not your farm's records. Estimate for planning only, not financial advice. Prices and costs change. Check with your agronomist or farm advisor.</div>
    </div>
  </AppShell>
</template>
