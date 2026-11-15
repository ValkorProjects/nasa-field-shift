<script setup>
// Where the cost numbers come from, and the loading / error state of the public APIs.
import { costs, loadCosts } from '@/data/costs.js'
</script>

<template>
  <div v-if="costs.status === 'loading'" class="pubnote load" role="status">
    <span class="spin" aria-hidden="true"></span>Getting public data for your field (IBGE, NASA POWER)…
  </div>
  <div v-else-if="costs.status === 'error'" class="pubnote err" role="alert">
    <b>Could not get public data:</b> {{ costs.error }}. Showing sample values.
    <button class="lnk" @click="loadCosts({ force: true })">Try again</button>
  </div>
  <div v-else-if="costs.status === 'ok'" class="pubnote ok">
    <b>Public data for {{ costs.muni.name }} ({{ costs.muni.uf }})</b>
    <span>
      harvests {{ costs.info.span }}<template v-if="costs.info.cornLevel === 'state'"> (state average, the town has too few)</template>
      · dry autumn = April–May rain below {{ costs.info.threshold }} mm, same rule as the alert ({{ costs.info.rainPeriod }},
      {{ costs.info.rainFrom === 'backend' ? 'NASA POWER via our backend' : 'NASA POWER' }})
      · dry years: {{ costs.info.dryYears.join(', ') || 'none' }}
    </span>
    <span class="srcs">
      <a v-for="s in costs.info.sources" :key="s.name" :href="s.url" target="_blank" rel="noopener">{{ s.name }}</a>
    </span>
  </div>
</template>

<style scoped>
.pubnote{display:flex;flex-wrap:wrap;align-items:center;gap:4px 10px;font-size:13px;font-weight:600;border-radius:12px;padding:9px 14px;line-height:1.4}
.pubnote.ok{background:#eef6ec;border:1.5px solid #b9d9b2;color:#2f4a33}
.pubnote.load{background:#f4f6f3;border:1.5px solid #d9e0d7;color:#4b5a4c}
.pubnote.err{background:#fff3cf;border:1.5px solid #e0b84a;color:#5a4300}
.pubnote span{color:#4b5f4d}
.srcs{display:flex;gap:10px;margin-left:auto}
.srcs a{color:#1f6bd1;text-decoration:underline}
.spin{width:14px;height:14px;border-radius:50%;border:2.5px solid #c9d3c7;border-top-color:#2e8b3d;animation:pn-spin .8s linear infinite}
@keyframes pn-spin{to{transform:rotate(360deg)}}
.lnk{background:none;border:0;color:#1f6bd1;text-decoration:underline;font:inherit;cursor:pointer;padding:0}
</style>
