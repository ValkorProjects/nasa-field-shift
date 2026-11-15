<script setup>
// Screen 10 · Costs: big picture. Shows the mechanism and past data only. Never predicts food prices.
// Numbers come from IBGE PAM, IBGE IPCA and NASA POWER (see data/costs.js).
import { computed, onMounted } from 'vue'
import AppShell from '@/components/AppShell.vue'
import CostTabs from '@/components/CostTabs.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import SampleValue from '@/components/SampleValue.vue'
import PublicDataNote from '@/components/PublicDataNote.vue'
import { state } from '@/data/store.js'
import { costs, loadCosts } from '@/data/costs.js'

onMounted(() => loadCosts())
const real = computed(() => costs.status === 'ok')
const r = computed(() => state.data.regional)
const ufName = computed(() => (real.value ? `${r.value.uf} state` : 'São Paulo'))
const signed = (x) => (typeof x === 'number' && x > 0 ? `+${x}` : x)
const chain = [
  { icon: 'rain', t: 'Dry autumn', d: 'Less rain in April–May in the region', scale: 'area', src: 'NASA POWER' },
  { icon: 'leaf', t: 'Smaller corn harvest', d: 'Many farms lose grain at the same time', scale: 'area', src: 'IBGE PAM' },
  { icon: 'coin', t: 'Corn costs more', d: 'Less corn on the market can raise its price', scale: 'area', src: 'IBGE PAM, past prices' },
  { icon: 'tool', t: 'Feed costs more', d: 'Corn is a main part of chicken, pig and dairy feed', scale: 'book', src: 'general fact' },
  { icon: 'bell', t: 'Food costs more', d: 'Chicken, eggs, pork and milk can cost more', scale: 'area', src: 'IBGE IPCA, past data' }
]
</script>

<template>
  <AppShell active="fields" crumb="My fields › Field 1 › Costs" title="What if nothing changes?">
    <div class="cost">
      <CostTabs active="big" />
      <PublicDataNote />
      <div class="bigintro"><b>One farm alone does not change food prices.</b> But when many farms in a region lose part of the harvest in the same dry season, it adds up.</div>

      <div class="card">
        <div class="h2">How a dry autumn can reach the store</div>
        <ol class="chain" style="list-style:none">
          <template v-for="(c, i) in chain" :key="c.t">
            <li class="link">
              <div class="lnum">{{ i + 1 }}</div>
              <div class="lic"><Icon :name="c.icon" /></div>
              <b>{{ c.t }}</b><span>{{ c.d }}</span>
              <Chip :scale="c.scale" :source="c.src" />
            </li>
            <li v-if="i < chain.length - 1" class="larr" aria-hidden="true">→</li>
          </template>
        </ol>
      </div>

      <div class="mrow">
        <div class="card scen">
          <div class="h2">If many farms in {{ ufName }} keep corn <span class="tag sc-est">{{ real ? 'scenario' : 'sample' }}</span></div>
          <p class="pp">If <b><SampleValue :v="r.share" />%</b> of {{ ufName }}'s second-crop corn area has a dry autumn like the past ones:</p>
          <div class="scrow">
            <div><span class="sl2">Corn area hit</span><b><SampleValue :v="r.area" /> thousand ha</b><Chip scale="area" :source="real ? r.area.source : 'IBGE / CONAB'" /></div>
            <div><span class="sl2">Corn lost</span><b><SampleValue :v="r.tonnes" /> thousand t</b><Chip scale="est" source="area × yield × loss" /></div>
            <div><span class="sl2">{{ ufName }}'s share of Brazil's second-crop corn</span><b><SampleValue :v="r.share_br" />%</b><Chip scale="area" :source="real ? r.share_br.source : 'CONAB'" /></div>
          </div>
          <div class="past"><b>It happened before:</b> in <SampleValue :v="r.past_year" />, the second-crop corn harvest fell <SampleValue :v="r.past_drop" />%
            <template v-if="real && r.past_rain != null">(April–May rain was {{ r.past_rain }} mm, against {{ r.rain_mean }} mm on average)</template>
            and the corn price received by farmers rose <SampleValue :v="r.past_price" />% against the year before.
            <template v-if="real && r.food">In December {{ r.food.year }}, food in shops cost {{ signed(r.food.food) }}% more than 12 months before (chicken {{ signed(r.food.chicken) }}%, eggs {{ signed(r.food.eggs) }}%).</template>
            <Chip scale="area" :source="real ? (r.food ? 'IBGE PAM + IPCA' : 'IBGE PAM') : 'CONAB + CEPEA'" />
            <template v-if="real"> Many things moved prices that year, not only the harvest.</template></div>
        </div>
        <div class="card cant">
          <div class="h2">What we can and can't say</div>
          <div class="cs ok"><Icon name="check" /><span>How much <b>your field</b> could lose</span></div>
          <div class="cs ok"><Icon name="check" /><span>How much <b>less corn</b> a region could harvest</span></div>
          <div class="cs ok"><Icon name="check" /><span>What happened to prices <b>in past dry years</b></span></div>
          <div class="cs no"><Icon name="x" /><span>We <b>can't predict</b> food prices. They also depend on Brazil and world markets, stocks, imports and the dollar.</span></div>
          <div class="cs no"><Icon name="x" /><span>NASA data shows rain, soil and plants, <b>not prices</b>.</span></div>
        </div>
      </div>

      <div class="good"><Icon name="leaf" /><span><b>Why it matters:</b> when many farms adapt their rotation to the weather, harvests become steadier. Steadier harvests help keep food supply stable.</span></div>
    </div>
  </AppShell>
</template>
