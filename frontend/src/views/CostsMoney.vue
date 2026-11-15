<script setup>
// Screen 9 · Costs: your money.
// Loss (FAO-33): 1 − Ya/Ym = Ky (1 − ETa/ETm); R$ lost = area × yield × loss% × price.
// The backend computes the real per-plan values; here the farmer can type their own numbers
// and we show the simple loss estimate for the current plan when all of them are filled.
import { computed, reactive, ref, nextTick } from 'vue'
import AppShell from '@/components/AppShell.vue'
import CostTabs from '@/components/CostTabs.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import SampleValue from '@/components/SampleValue.vue'
import { state } from '@/data/store.js'
import { fieldById, areaHa, fmtHa } from '@/data/fields.js'

const m = computed(() => state.data.money)
const plans = computed(() => state.data.strategies)

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
  const r = num('area') * num('yield') * (num('loss') / 100) * num('price')
  return Number.isFinite(r) ? Math.round(r).toLocaleString('en-US') : null
})
</script>

<template>
  <AppShell active="fields" crumb="My fields › Field 1 › Costs" title="What if nothing changes?">
    <div class="cost">
      <CostTabs active="money" />

      <div class="headline">
        <div class="hic"><Icon name="warn" /></div>
        <div>
          <div class="hk">If you keep corn and the autumn is dry</div>
          <div class="hv">Field 1 could lose
            <b v-if="userLoss">R$ {{ userLoss }}</b>
            <b v-else>R$ <SampleValue :v="m.at_risk_min" /> – <SampleValue :v="m.at_risk_max" /></b>
          </div>
          <div class="hs">
            <template v-if="userLoss">With your numbers. </template>
            Compared with a normal year. Dry autumns happened in <SampleValue :v="m.dry_years" /> years.
            <Chip scale="area" source="GPM" /> Past records, not a forecast.
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
          <div class="pnote">{{ p.money.note }}</div>
        </div>
      </div>

      <div class="card">
        <div class="inh"><div class="h2" style="margin:0">Numbers we used</div><span>Filled from public data. Click a number to use your own.</span></div>
        <div class="inps">
          <div v-for="inp in m.inputs" :key="inp.id" class="inp">
            <span :id="`lbl-${inp.id}`">{{ inp.label }}</span>
            <input v-if="editing === inp.id" ref="inputEl" class="inedit" type="number" min="0" step="any"
              :aria-labelledby="`lbl-${inp.id}`" :value="typeof val(shown(inp)) === 'number' ? val(shown(inp)) : ''"
              @blur="commit(inp.id, $event)" @keydown.enter="$event.target.blur()" @keydown.esc="editing = null" />
            <button v-else class="inbtn" :aria-label="`Change ${inp.label}`" @click="edit(inp.id)">
              <b><span>{{ inp.prefix }}<SampleValue :v="shown(inp)" />{{ inp.suffix }}</span><Icon name="pencil" /></b>
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
      <div class="disc"><Icon name="info" />Estimate for planning only, not financial advice. Prices and costs change. Check with your agronomist or farm advisor.</div>
    </div>
  </AppShell>
</template>
