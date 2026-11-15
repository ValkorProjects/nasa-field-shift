<script setup>
// Answer phrased from the farmer's point of view. tone: g = good, y = watch out, r = bad.
import SampleValue from './SampleValue.vue'
defineProps({ v: { type: [Object, String], required: true }, tone: { type: String, required: true } })
</script>
<template>
  <span :class="['ans', `a${tone}`]"><i aria-hidden="true"></i><SampleValue :v="v" :dotted="false" /></span>
</template>
