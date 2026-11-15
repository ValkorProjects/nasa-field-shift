<script setup>
// On every screen except the map: shows why a field has no data (422 / backend down / network) and
// lets the farmer retry or switch to sample data. The map has its own message.
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { profileOf, ensureProfile } from '@/data/store.js'
import { selected } from '@/data/fields.js'
import { apiMode } from '@/api/index.js'

const route = useRoute()
const p = computed(() => profileOf(selected.value?.id))
const useSample = () => { apiMode.value = 'mock' }
const show = computed(() => p.value?.status === 'error' && !route.path.startsWith('/farm'))
</script>
<template>
  <div v-if="show" class="banner" role="alert">
    <b>No data for {{ selected?.name }}.</b> {{ p.error }}
    <button class="btn ghost small" style="width:auto;display:inline-block;margin-left:8px" @click="ensureProfile(selected, { force: true })">Try again</button>
    <button class="btn ghost small" style="width:auto;display:inline-block;margin-left:4px" @click="useSample">Use sample data</button>
  </div>
</template>
