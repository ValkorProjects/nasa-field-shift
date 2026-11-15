<script setup>
// Screen 2 · Crops
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import Stepper from '@/components/Stepper.vue'
import FieldThumb from '@/components/FieldThumb.vue'
import IllustrativeImg from '@/components/IllustrativeImg.vue'
import { state } from '@/data/store.js'

const router = useRouter()
const c = computed(() => state.data.crops)
const seasons = [
  { id: 'summer', label: 'Summer crop', months: '(Oct – Feb)' },
  { id: 'second', label: 'Second crop', months: '(Feb – Aug)' }
]
const sel = (season) => c.value[season].find((x) => x.id === state.crops[season])
</script>

<template>
  <AppShell active="fields" crumb="My fields › Field 1" title="Tell us what you grow">
    <div class="wiz">
      <div class="wl">
        <Stepper :cur="2" />
        <div class="q">What do you grow on Field 1?</div>
        <template v-for="s in seasons" :key="s.id">
          <div class="season" :id="`season-${s.id}`">{{ s.label }} <small>{{ s.months }}</small></div>
          <div class="crops" role="radiogroup" :aria-labelledby="`season-${s.id}`">
            <button v-for="crop in c[s.id]" :key="crop.id" :class="['crop', { sel: state.crops[s.id] === crop.id }]"
              role="radio" :aria-checked="state.crops[s.id] === crop.id" @click="state.crops[s.id] = crop.id">
              <IllustrativeImg :src="crop.img" :alt="crop.name" />
              <div class="cn">{{ crop.name }}</div>
            </button>
          </div>
        </template>
      </div>
      <div class="wr">
        <div class="mini">
          <FieldThumb field="1" w="340" h="210" />
          <span class="illmap" style="left:10px;right:auto">Illustrative image</span>
        </div>
        <div class="summary" aria-live="polite">
          <div class="h2" style="color:#fff">Your plan today</div>
          <div class="srot">
            <IllustrativeImg :src="sel('summer')?.img" cls="sq" :alt="sel('summer')?.name" /><span>→</span>
            <IllustrativeImg :src="sel('second')?.img" cls="sq" :alt="sel('second')?.name" />
          </div>
          <div class="srt"><span>{{ sel('summer')?.name }}</span><span>{{ sel('second')?.name }}</span></div>
          <p>Wrong? Just click another photo.</p>
        </div>
        <button class="btn green" style="margin-top:auto" @click="router.push('/field/1/soil')">Next: soil →</button>
        <button class="btn ghost" @click="router.push('/farm')">← Back</button>
      </div>
    </div>
  </AppShell>
</template>
