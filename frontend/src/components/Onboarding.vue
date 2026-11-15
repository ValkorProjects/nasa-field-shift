<script setup>
// Welcome tour (issue #38): 4 short steps, can be skipped, reopened from Help.
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import Icon from './Icon.vue'
import { finishOnboarding, activeProfile } from '@/data/account.js'
import { MVP_TOWNS } from '@/data/areas.js'

const STEPS = [
  {
    icon: 'leaf', title: 'What RollCrop does',
    body: [
      'For each of your fields, RollCrop compares the crop rotation you use today with two alternatives.',
      'It looks at past rain, frost, soil and plant cover, and at what matters most to you (income, soil, water…).',
      'It supports your decision and your agronomist. It does not replace them.'
    ]
  },
  {
    icon: 'map', title: 'Draw your area',
    body: [
      `This MVP works in ${MVP_TOWNS}, where we loaded the satellite data (yellow outline on the map).`,
      'Click “Draw a new field” and click each corner of your field. The area is computed from the map.',
      'You can also explore any other place in Brazil. There we use live data only, and the results are not validated.'
    ]
  },
  {
    icon: 'cal', title: 'How to read the results',
    body: [
      '“7 of the last 10 years” means it happened in 7 of the past 10 years. These are past records, not a forecast.',
      'Values with a dotted yellow line are still examples. Labels say how detailed each number is: your field, your area or an estimate.',
      'Always check with your agronomist before you buy seed or change your plan.'
    ]
  },
  {
    icon: 'info', title: 'Where the data comes from',
    body: [
      'NASA POWER: past daily weather (rain, temperature). NASA MODIS and SMAP: plant cover and soil moisture on the map.',
      'NASA SRTM: elevation and slope (coming soon). SoilGrids (ISRIC, not NASA): soil.',
      'IBGE and CONAB: yields, prices and costs. “How we calculated” lists every source and its limits.'
    ]
  }
]

const i = ref(0)
const step = computed(() => STEPS[i.value])
const last = computed(() => i.value === STEPS.length - 1)
const next = () => (last.value ? finishOnboarding() : i.value++)
const onKey = (e) => { if (e.key === 'Escape') finishOnboarding() }
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="onb-back" role="presentation">
    <div class="onb" role="dialog" aria-modal="true" aria-labelledby="onb-title">
      <div class="onb-top">
        <span class="onb-hi">Welcome, {{ activeProfile?.nick }}</span>
        <button class="lnk" @click="finishOnboarding">Skip</button>
      </div>
      <div class="onb-ic"><Icon :name="step.icon" /></div>
      <h2 id="onb-title">{{ step.title }}</h2>
      <p v-for="(b, k) in step.body" :key="k">{{ b }}</p>
      <div class="onb-foot">
        <div class="onb-dots" aria-label="Step">
          <button v-for="(s, k) in STEPS" :key="k" :class="{ on: k === i }" :aria-label="`Step ${k + 1}: ${s.title}`" :aria-current="k === i ? 'step' : null" @click="i = k"></button>
        </div>
        <button v-if="i > 0" class="btn ghost small" @click="i--">Back</button>
        <button class="btn green small" @click="next">{{ last ? 'Start' : 'Next' }}</button>
      </div>
    </div>
  </div>
</template>
