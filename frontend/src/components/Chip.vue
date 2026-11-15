<script setup>
// 1 chip per indicator = scale icon + short source. Hover shows the full text.
import { SCALE_IC, SCALE_TXT } from '@/data/icons.js'
defineProps({ scale: { type: String, required: true }, source: { type: String, default: '' } })
</script>
<template>
  <span :class="['chip2', `c-${scale}`]" :title="source ? `${SCALE_TXT[scale]} · ${source}` : SCALE_TXT[scale]">
    <svg viewBox="0 0 24 24" aria-hidden="true" v-html="SCALE_IC[scale]" />{{ source }}<span v-if="!source" class="sr-only">{{ SCALE_TXT[scale] }}</span>
  </span>
</template>
