<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { fieldPath } from '@/data/fields.js'
import SampleValue from './SampleValue.vue'
import { t } from '@/i18n'
import { state } from '@/data/store.js'
defineProps({ active: String })
const items = computed(() => [
  { id: 'farm', icon: 'map', to: '/farm' },
  { id: 'fields', icon: 'list', to: fieldPath('crops') },
  { id: 'plant', icon: 'cal', to: '/planting' },
  { id: 'alerts', icon: 'bell', to: '/farm/alert', badge: 1, sketch: true },
  { id: 'how', icon: 'calc', to: '/how' },
  { id: 'help', icon: 'help', to: null, sketch: true }
])
</script>
<template>
  <aside class="side" aria-label="Main">
    <div class="logo"><img src="/img/brand/rollcrop-logo-light.png" :alt="t('app.name')" width="176" height="80" /></div>
    <template v-for="it in items" :key="it.id">
      <router-link v-if="it.to" :to="it.to" :class="['nav', { on: active === it.id }]">
        <Icon :name="it.icon" />{{ t(`nav.${it.id}`) }}
        <span v-if="it.badge" class="badge">{{ it.badge }}</span>
        <span v-if="it.sketch" class="sk">{{ t('nav.sketch') }}</span>
      </router-link>
      <div v-else class="nav disabled" aria-disabled="true">
        <Icon :name="it.icon" />{{ t(`nav.${it.id}`) }}<span class="sk">{{ t('nav.sketch') }}</span>
      </div>
    </template>
    <div class="spacer"></div>
    <div class="farm" v-if="state.data">
      <SampleValue :v="state.data.farm.name" :dotted="false" /><br />
      <small><SampleValue :v="state.data.farm.region" :dotted="false" /> · {{ t('nav.example') }}</small>
    </div>
  </aside>
</template>
