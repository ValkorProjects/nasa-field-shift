<script setup>
// Screen 6 · side drawer (560 px) over the dimmed results.
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import Icon from './Icon.vue'
import Chip from './Chip.vue'
import Tpl from './Tpl.vue'
import SampleValue from './SampleValue.vue'
import ConfidenceCard from './ConfidenceCard.vue'
import AgronomistNote from './AgronomistNote.vue'
import { state, strategy, bestId } from '@/data/store.js'
import { t } from '@/i18n'

const props = defineProps({ option: { type: String, required: true } })
const emit = defineEmits(['close'])
const s = computed(() => strategy(props.option))
const d = computed(() => state.data.details[props.option])
const isBest = computed(() => bestId.value === props.option)

const closeBtn = ref(null)
const onKey = (e) => e.key === 'Escape' && emit('close')
onMounted(() => { document.addEventListener('keydown', onKey); closeBtn.value?.focus() })
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="backdrop" @click="emit('close')"></div>
  <aside v-if="s && d" class="drawer d2" role="dialog" aria-modal="true" :aria-label="`Details: ${s.name.value}`">
    <div class="dh">
      <div>
        <div class="k">{{ s.tag }}<template v-if="isBest"> · best for you</template></div>
        <div class="dname"><SampleValue :v="s.name" :dotted="false" /></div>
      </div>
      <button ref="closeBtn" class="close" aria-label="Close details" @click="emit('close')"><Icon name="x" /></button>
    </div>
    <div class="dwhy" v-html="d.why"></div>
    <div class="dsec">
      <h3>What the data shows</h3>
      <div v-for="e in d.evidence" :key="e.text" class="evr2">
        <Icon :name="e.icon" /><b><Tpl :text="e.text" :n="e.n" /></b><Chip :scale="e.chip.scale" :source="e.chip.source" />
      </div>
      <div v-if="d.nodata" class="nd2 big"><Icon name="info" /><span><b>{{ t('common.noFieldData') }}.</b> {{ d.nodata }}</span></div>
    </div>
    <div class="tri">
      <div class="tg"><h3><Icon name="check" />Good</h3><ul><li v-for="x in d.good" :key="x" v-html="x"></li></ul></div>
      <div class="tr"><h3><Icon name="warn" />Watch out</h3><ul><li v-for="x in d.watch" :key="x" v-html="x"></li></ul></div>
      <div class="tb"><h3><Icon name="help" />We don't know</h3><ul><li v-for="x in d.unknown" :key="x" v-html="x"></li></ul></div>
    </div>
    <ConfidenceCard />
    <AgronomistNote />
  </aside>
</template>
