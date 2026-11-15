<script setup>
// Top banner. Mock mode: everything is sample data. Api mode with the field profile loaded: the
// screens mix real data (NASA POWER, SoilGrids, IBGE, CONAB) with sample values (dotted).
import { computed } from 'vue'
import { t } from '@/i18n'
import { apiMode } from '@/api/index.js'
import { profileOf } from '@/data/store.js'
import { farm } from '@/data/fields.js'

const mixed = computed(() => {
  if (apiMode.value !== 'api') return false
  const e = profileOf(farm.selectedId)
  return e?.status === 'ready' && !e.profile?.mock
})
</script>
<template>
  <div :class="['banner', { mixed }]" role="note">
    <template v-if="mixed">
      <b>{{ t('banner.mixedLead') }}</b> · {{ t('banner.mixedText') }} <span class="ex">{{ t('banner.dotted') }}</span> {{ t('banner.mixedTail') }}
    </template>
    <template v-else>
      <b>{{ t('banner.lead') }}</b> · {{ t('banner.text') }} <span class="ex">{{ t('banner.dotted') }}</span> {{ t('banner.tail') }}
    </template>
  </div>
</template>
