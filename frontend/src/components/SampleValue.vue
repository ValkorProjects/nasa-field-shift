<script setup>
// Renders a { value, sample } leaf. Sample values get the dotted yellow style.
// dotted=false: sample text labels shown plain (as in the reference screens).
import { computed } from 'vue'
const props = defineProps({ v: { type: [Object, String, Number], default: '[X]' }, dotted: { type: Boolean, default: true } })
const value = computed(() => (props.v && typeof props.v === 'object' ? props.v.value : props.v) ?? '[X]')
const sample = computed(() => (props.v && typeof props.v === 'object' ? props.v.sample !== false : true))
const title = computed(() => (props.v && typeof props.v === 'object' && props.v.source ? `Sample value · source: ${props.v.source}` : 'Sample value'))
</script>
<template>
  <span v-if="sample && dotted" class="ex" :title="title">{{ value }}</span>
  <span v-else>{{ value }}</span>
</template>
