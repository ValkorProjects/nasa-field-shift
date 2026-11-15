<script setup>
import { t } from '@/i18n'
defineProps({ cur: { type: Number, required: true } })
const routes = ['/farm', '/field/1/crops', '/field/1/soil', '/field/1/priorities', '/field/1/results']
</script>
<template>
  <nav class="steps" aria-label="Steps">
    <template v-for="(s, i) in t('steps')" :key="s">
      <router-link :to="routes[i]" :class="['step', { done: i + 1 < cur, cur: i + 1 === cur }]" :aria-current="i + 1 === cur ? 'step' : null">
        <div class="n">{{ i + 1 < cur ? '✓' : i + 1 }}</div>{{ s }}
      </router-link>
      <div v-if="i < 4" :class="['sline', { on: i + 1 < cur }]"></div>
    </template>
  </nav>
</template>
