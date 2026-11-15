<script setup>
// Screen 5 · Results (+ screen 6 drawer at /field/1/results/:option)
import { computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { loadCosts, withCosts } from '@/data/costs.js'
import AppShell from '@/components/AppShell.vue'
import Stepper from '@/components/Stepper.vue'
import Icon from '@/components/Icon.vue'
import ScaleLegend from '@/components/ScaleLegend.vue'
import StrategyCard from '@/components/StrategyCard.vue'
import StrategyDrawer from '@/components/StrategyDrawer.vue'
import SampleValue from '@/components/SampleValue.vue'
import AgronomistNote from '@/components/AgronomistNote.vue'
import { state, bestId, bestIfIncomeFirst, strategy, priorityLabel, confidence } from '@/data/store.js'
import { fieldPath, selected } from '@/data/fields.js'

const route = useRoute()
const router = useRouter()
const option = computed(() => route.params.option)
const best = computed(() => strategy(bestId.value))
const alt = computed(() => strategy(bestIfIncomeFirst.value))
const money = computed(() => withCosts(state.data).money)
const open = (id) => router.push(fieldPath(`results/${id}`))
const close = () => router.push(fieldPath('results'))
onMounted(() => loadCosts()) // money bar: public data (IBGE, NASA POWER)
</script>

<template>
  <AppShell active="fields" :crumb="`My fields › ${selected?.name} › Results`" :title="`3 plans for ${selected?.name}`">
    <div :class="['res2', { dim: option }]" :inert="option ? true : null">
      <div class="resh"><Stepper :cur="5" /></div>

      <div class="best2">
        <div class="bstar" aria-hidden="true">★</div>
        <div>
          <b>Best for you: {{ best.tag }}, {{ best.longName }}.</b>
          You chose <u>{{ priorityLabel(state.order[0]) }}</u> and <u>{{ priorityLabel(state.order[1]) }}</u> first.
          <span>
            <template v-if="state.order[0] !== 'income' && alt.id !== best.id">If Income came first, {{ alt.tag }} would be best. · </template>
            How sure are we: <b class="sure">{{ confidence.level }}</b>
            (<span class="ex">{{ confidence.met }} of {{ confidence.total }}</span> checks)
            <button class="lnk" @click="open(best.id)">why?</button>
          </span>
        </div>
        <button class="edit" @click="router.push(fieldPath('priorities'))"><Icon name="pencil" />Change priorities</button>
      </div>

      <ScaleLegend />

      <div class="cols2">
        <StrategyCard v-for="s in state.data.strategies" :key="s.id" :s="s" :best="s.id === best.id" @details="open" />
      </div>

      <div class="moneybar">
        <Icon name="coin" />
        <div>
          <b>What if nothing changes?</b>
          <span>If you keep corn and the autumn is dry, {{ selected?.name }} could lose
            <b>R$ <SampleValue :v="money.at_risk_min" /> – <SampleValue :v="money.at_risk_max" /></b>.</span>
        </div>
        <button class="btn red small" style="width:auto;padding:10px 18px" @click="router.push(fieldPath('costs'))">See the costs →</button>
      </div>

      <AgronomistNote />
    </div>

    <template #overlay>
      <StrategyDrawer v-if="option" :key="option" :option="option" @close="close" />
    </template>
  </AppShell>
</template>
