<script setup>
// Renders "text with {n} inside" where {n} is a sample value leaf.
import SampleValue from './SampleValue.vue'
defineProps({ text: { type: String, required: true }, n: { type: [Object, String, Number], default: null } })
</script>
<template>
  <template v-for="(part, i) in text.split('{n}')" :key="i"><SampleValue v-if="i > 0" :v="n" />{{ part }}</template>
</template>
