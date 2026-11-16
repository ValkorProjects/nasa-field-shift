<script setup>
// Screen 3 · Soil. Every question has "I don't know" → estimate from public maps, lower confidence.
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import Stepper from '@/components/Stepper.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import SampleValue from '@/components/SampleValue.vue'
import { state } from '@/data/store.js'
import { fieldPath, selected } from '@/data/fields.js'

const router = useRouter()
const answered = computed(() => !!(state.soil.texture && state.soil.drainage && state.soil.slope))
const IDK = { id: 'idk', b: "I don't know", s: 'We estimate it' }

// Drawn soil texture: deterministic dots (coarse for sandy, fine for clay)
function texture(dot, n) {
  let seed = n * 7919
  const rnd = () => ((seed = (seed * 9301 + 49297) % 233280) / 233280)
  const count = { 1: 70, 2: 120, 3: 200 }[n]
  const sizes = { 1: [1.5, 2.5, 3.5], 2: [1.6], 3: [1] }[n]
  return Array.from({ length: count }, () => ({
    cx: 4 + rnd() * 92, cy: 4 + rnd() * 52, r: sizes[Math.floor(rnd() * sizes.length)], fill: dot
  }))
}

const questions = [
  { key: 'texture', label: '1. What is the soil like?', est: 'texture_est', options: [
    { id: 'sandy', b: 'Sandy', s: 'Loose, dries fast', bg: '#e8d3a3', dots: texture('#b99456', 1) },
    { id: 'medium', b: 'Medium', s: 'In between', bg: '#b98a5a', dots: texture('#8a5d34', 2) },
    { id: 'clay', b: 'Clay', s: 'Sticky when wet', bg: '#8f4a2e', dots: texture('#6b311c', 3) },
    { ...IDK, idkArt: true }] },
  { key: 'drainage', label: '2. After heavy rain, the water…', est: 'drainage_est', options: [
    { id: 'fast', b: 'Drains fast', s: 'Gone in hours' },
    { id: 'normal', b: 'Drains normally', s: 'Gone in a day' },
    { id: 'puddles', b: 'Stays in puddles', s: 'For days' },
    IDK] },
  { key: 'slope', label: '3. Is the field sloped?', options: [
    { id: 'flat', b: 'Flat', s: 'Almost no slope' },
    { id: 'gentle', b: 'Gentle slope', s: 'You can see it' },
    { id: 'steep', b: 'Steep', s: 'Hard for machines' },
    IDK] }
]
</script>

<template>
  <AppShell active="fields" :crumb="`My fields › ${selected?.name}`" title="Tell us about your soil">
    <div class="wiz">
      <div class="wl">
        <Stepper :cur="3" />
        <div class="q">Tell us about the soil on {{ selected?.name }}</div>
        <p class="lead">If you are not sure, choose "I don't know". We will estimate it from public maps, with lower confidence.</p>
        <div v-for="q in questions" :key="q.key" class="qrow">
          <div class="ql" :id="`q-${q.key}`">{{ q.label }}</div>
          <div class="choices" role="radiogroup" :aria-labelledby="`q-${q.key}`">
            <button v-for="o in q.options" :key="o.id" :class="['choice', { sel: state.soil[q.key] === o.id }]"
              role="radio" :aria-checked="state.soil[q.key] === o.id" @click="state.soil[q.key] = o.id">
              <svg v-if="o.dots" class="art" viewBox="0 0 100 60" preserveAspectRatio="none" aria-hidden="true">
                <rect width="100" height="60" :fill="o.bg" />
                <circle v-for="(c, i) in o.dots" :key="i" :cx="c.cx" :cy="c.cy" :r="c.r" :fill="c.fill" />
              </svg>
              <div v-else-if="o.idkArt" class="art idk" aria-hidden="true">?</div>
              <b>{{ o.b }}</b><span>{{ o.s }}</span>
            </button>
          </div>

          <!-- "I don't know" → estimate from public maps -->
          <div v-if="q.est && state.soil[q.key] === 'idk'" class="estnote">
            <Icon name="info" />Estimated from public maps:
            <template v-if="state.data.soil[q.est].unavailable">
              <b>Not available for this field</b> · {{ state.data.soil[q.est].unavailable }}
            </template>
            <template v-else>
              <b><SampleValue :v="state.data.soil[q.est]" :dotted="!!(state.data.meta?.live || state.data.meta?.sampleOnly)" /></b> · lower confidence
              <Chip scale="est" source="SoilGrids 250 m" />
              <span v-if="q.est === 'texture_est' && state.data.info?.soilNote"> · {{ state.data.info.soilNote }}</span>
            </template>
          </div>

          <!-- Slope is always suggested from NASA SRTM -->
          <div v-if="q.key === 'slope'" class="estnote ok">
            <Icon name="slope" />
            <template v-if="state.data.soil.slope_sat.pending">Satellite slope coming soon (terrain data in progress)</template>
            <template v-else>
              Satellite elevation suggests:
              <b><SampleValue :v="state.data.soil.slope_sat" /></b>
              <span>(<SampleValue :v="state.data.soil.slope_pct" />% average)</span>
              <Chip scale="field" source="NASA SRTM 30 m" />
            </template>
          </div>
        </div>
      </div>
      <div class="wr">
        <div class="card">
          <div class="h2">Why we ask</div>
          <p class="pp">Soil type, drainage and slope change how much rain soaks in and how much soil the rain can wash away.</p>
          <p class="pp">Satellites cannot see soil texture under the crop well. Your answer is better than our estimate.</p>
        </div>
        <div class="card">
          <div class="h2">Have a soil test?</div>
          <p class="pp">You can upload it later. It makes the result more certain.</p>
          <button class="btn ghost small" disabled>Upload soil test (coming soon)</button>
        </div>
        <div v-if="!answered" class="fnote" role="status">Answer the 3 questions ("I don't know" is fine).</div>
        <button class="btn green" style="margin-top:auto" :disabled="!answered" @click="router.push(fieldPath('priorities'))">Next: priorities →</button>
        <button class="btn ghost" @click="router.push(fieldPath('crops'))">← Back</button>
      </div>
    </div>
  </AppShell>
</template>
