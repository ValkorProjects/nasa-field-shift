<script setup>
import { state } from './data/store.js'
</script>
<template>
  <div v-if="state.error" class="boot">Could not load field data: {{ state.error }}</div>
  <div v-else-if="state.loading" class="boot">Loading…</div>
  <router-view v-else />
</template>
