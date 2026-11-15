<script setup>
// "How sure are we?" — 4 checks. 4 = High, 2–3 = Medium, 0–1 = Low.
import Icon from './Icon.vue'
import { confidence } from '@/data/store.js'
</script>

<template>
  <div class="conf2">
    <div class="cfh">
      <div>
        <div class="h2" style="margin:0">How sure are we?</div>
        <span class="cfr"><span class="ex">{{ confidence.met }} of {{ confidence.total }}</span> checks passed · 4 = High, 2–3 = Medium, 0–1 = Low</span>
      </div>
      <span :class="['lvl', `l${confidence.tone}`]"><i class="d"></i>{{ confidence.level }}</span>
    </div>
    <div v-for="r in confidence.rules" :key="r.text" :class="['cr', r.ok ? 'ok' : 'no']">
      <Icon :name="r.ok ? 'check' : 'x'" /><span>{{ r.text }}<span class="sr-only">{{ r.ok ? ' (passed)' : ' (not passed)' }}</span></span>
    </div>
  </div>
</template>
