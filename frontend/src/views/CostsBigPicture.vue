<script setup>
// Screen 10 · Costs: big picture. Shows the mechanism and past data only. Never predicts food prices.
import { computed } from 'vue'
import AppShell from '@/components/AppShell.vue'
import CostTabs from '@/components/CostTabs.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import SampleValue from '@/components/SampleValue.vue'
import { state } from '@/data/store.js'
import { fieldPath, selected } from '@/data/fields.js'

const r = computed(() => state.data.regional)
const chain = [
  { icon: 'rain', t: 'Dry autumn', d: 'Less rain in April–May in the region', scale: 'area', src: 'GPM' },
  { icon: 'leaf', t: 'Smaller corn harvest', d: 'Many farms lose grain at the same time', scale: 'est', src: 'crop facts + HLS' },
  { icon: 'coin', t: 'Corn costs more', d: 'Less corn on the market can raise its price', scale: 'area', src: 'CEPEA, past prices' },
  { icon: 'tool', t: 'Feed costs more', d: 'Corn is a main part of chicken, pig and dairy feed', scale: 'book', src: 'general fact' },
  { icon: 'bell', t: 'Food costs more', d: 'Chicken, eggs, pork and milk can cost more', scale: 'area', src: 'IBGE IPCA, past data' }
]
</script>

<template>
  <AppShell active="fields" :crumb="`My fields › ${selected?.name} › Costs`" title="What if nothing changes?">
    <div class="cost">
      <CostTabs active="big" />
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
          <div class="h2">If many farms in São Paulo keep corn <span class="tag sc-est">sample</span></div>
          <p class="pp">If <b><SampleValue :v="r.share" />%</b> of São Paulo's second-crop corn area has a dry autumn like the past ones:</p>
          <div class="scrow">
            <div><span class="sl2">Corn area hit</span><b><SampleValue :v="r.area" /> thousand ha</b><Chip scale="area" source="IBGE / CONAB" /></div>
            <div><span class="sl2">Corn lost</span><b><SampleValue :v="r.tonnes" /> thousand t</b><Chip scale="est" source="area × loss" /></div>
            <div><span class="sl2">São Paulo's share of Brazil's corn</span><b><SampleValue :v="r.share_br" />%</b><Chip scale="area" source="CONAB" /></div>
          </div>
          <div class="past"><b>It happened before:</b> in <SampleValue :v="r.past_year" />, the second-crop corn harvest fell <SampleValue :v="r.past_drop" />% and the corn price rose <SampleValue :v="r.past_price" />% in the next months. <Chip scale="area" source="CONAB + CEPEA" /></div>
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
