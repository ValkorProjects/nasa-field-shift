<script setup>
// Renders a { value, sample } leaf. Sample values get the dotted yellow style.
// dotted=false: sample text labels shown plain (as in the reference screens).
import { computed } from 'vue'
const props = defineProps({ v: { type: [Object, String, Number], default: '[X]' }, dotted: { type: Boolean, default: true } })
const value = computed(() => (props.v && typeof props.v === 'object' ? props.v.value : props.v) ?? '[X]')
const sample = computed(() => (props.v && typeof props.v === 'object' ? props.v.sample !== false : true))
const obj = computed(() => (props.v && typeof props.v === 'object' ? props.v : null))
const MODE_TXT = { mock: 'NASA data from offline copy', cache: 'NASA data from cache', live: 'Live data' }
const title = computed(() => {
  const v = obj.value
  if (v?.unavailable) return v.unavailable
  if (v?.pending) return 'Coming soon: satellite terrain data is in progress'
  if (v && v.sample === false) return [v.source, MODE_TXT[v.mode]].filter(Boolean).join(' · ') || undefined
  return v?.source ? `Sample value · source: ${v.source}` : 'Sample value'
})
const flag = computed(() => (obj.value?.unavailable ? 'na' : obj.value?.pending ? 'soon' : null))
</script>
<template>
  <span v-if="flag" :class="['nodata', flag]" :title="title">{{ value }}</span>
  <span v-else-if="sample && dotted" class="ex" :title="title">{{ value }}</span>
  <span v-else :title="sample ? undefined : title">{{ value }}</span>
</template>
