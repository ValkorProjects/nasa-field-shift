<script setup>
// One strategy: tag, name, traffic light, 2 photos, verdict, 5 indicator rows, priority fit, evidence.
import Icon from './Icon.vue'
import Chip from './Chip.vue'
import Answer from './Answer.vue'
import IllustrativeImg from './IllustrativeImg.vue'
import SampleValue from './SampleValue.vue'
import Tpl from './Tpl.vue'
import { t } from '@/i18n'
import { state } from '@/data/store.js'

defineProps({ s: { type: Object, required: true }, best: { type: Boolean, default: false } })
defineEmits(['details'])

const FIT = { Good: ['g', '✓'], OK: ['y', '~'], Poor: ['r', '✗'] }
const FIT_IC = { soil: 'erosion', water: 'drop', income: 'coin', cost: 'tool' }
</script>

<template>
  <article :class="['c2', `o${s.light}`, { best }]" :aria-label="`${s.tag}: ${s.name.value}, ${s.lightTxt}`">
    <div v-if="best" class="star">★ Best for you</div>
    <div class="c2h">
      <div><div class="k">{{ s.tag }}</div><div class="nm"><SampleValue :v="s.name" :dotted="false" /></div></div>
      <div class="light">{{ s.lightTxt }}</div>
    </div>
    <div class="pics2">
      <template v-for="(ph, i) in s.photos" :key="i">
        <span v-if="i" aria-hidden="true">→</span>
        <IllustrativeImg v-if="ph.img" :src="ph.img" :alt="ph.cap" />
        <div v-else class="img noimg" :aria-label="ph.cap">{{ ph.cap }}</div>
      </template>
    </div>
    <div class="pcap2"><span>{{ s.photos[0].cap }}</span><span>{{ s.photos[1].cap }}</span></div>
    <div v-if="s.catalog" :class="['catline', s.catalog.status]">
      <b>{{ s.catalog.statusTxt }}</b> · {{ s.catalog.note }}
      <a v-if="s.catalog.url" :href="s.catalog.url" target="_blank" rel="noopener">reference</a>
    </div>
    <div class="verdict"><SampleValue :v="s.verdict" :dotted="!!(state.data.meta?.live || state.data.meta?.sampleOnly)" /></div>

    <div v-for="r in s.rows" :key="r.icon" class="r2">
      <div class="r2l"><Icon :name="r.icon" /><span>{{ r.label }}</span></div>
      <Answer :v="r.answer" :tone="r.tone" />
      <Chip :scale="r.answer.scale" :source="r.answer.source" />
    </div>

    <div v-if="!s.fit" class="fitrow"><span>Your priorities</span><span class="nr">Not rated yet: left out of “Best for you”</span></div>
    <div v-else class="fitrow">
      <span :title="s.fitEstimate ? 'Estimate from this plan’s data (project rules, to be validated)' : ''">Your priorities<small v-if="s.fitEstimate"> · estimate</small></span>
      <span v-for="p in state.order" :key="p" :class="['f2', `f${FIT[s.fit[p]][0]}`]" :title="`${p}: ${s.fit[p]}`">
        <Icon :name="FIT_IC[p]" />{{ FIT[s.fit[p]][1] }}<span class="sr-only">{{ p }}: {{ s.fit[p] }}</span>
      </span>
    </div>

    <div class="ev2">
      <span v-if="s.nodata" class="nd2">{{ t('common.noFieldData') }}</span>
      <Chip :scale="s.evidence.scale" :source="s.evidence.source" />
      <Tpl :text="' ' + s.evidence.text" :n="s.evidence.n" />
    </div>
    <button class="btn small ghost" @click="$emit('details', s.id)">{{ t('common.seeDetails') }}</button>
  </article>
</template>
