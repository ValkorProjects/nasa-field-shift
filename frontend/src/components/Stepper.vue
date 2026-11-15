<script setup>
import { computed } from 'vue'
import { t } from '@/i18n'
import { fieldPath } from '@/data/fields.js'
defineProps({ cur: { type: Number, required: true } })
const routes = computed(() => ['/farm', fieldPath('crops'), fieldPath('soil'), fieldPath('priorities'), fieldPath('results')])
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
