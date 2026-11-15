<script setup>
import { ICONS } from '@/data/icons.js'
defineProps({ name: { type: String, required: true }, cls: { type: String, default: 'ic' } })
</script>
<template>
  <svg :class="cls" viewBox="0 0 24 24" aria-hidden="true" v-html="ICONS[name]" />
</template>
