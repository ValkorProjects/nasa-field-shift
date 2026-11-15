<script setup>
// No local profile yet → welcome screen (issue #38). First visit of a profile → welcome tour.
import { watch } from 'vue'
import { state } from './data/store.js'
import { account, activeProfile, isOnboarded } from './data/account.js'
import Welcome from './components/Welcome.vue'
import Onboarding from './components/Onboarding.vue'

watch(() => account.activeId, (id) => { if (id && !isOnboarded()) account.onboarding = true }, { immediate: true })
</script>
<template>
  <div v-if="state.error" class="boot">Could not load field data: {{ state.error }}</div>
  <div v-else-if="state.loading" class="boot">Loading…</div>
  <Welcome v-else-if="!activeProfile" />
  <template v-else>
    <router-view :key="account.activeId" />
    <Onboarding v-if="account.onboarding" />
  </template>
</template>
