<script setup>
import { t } from '@/i18n'
defineProps({ src: String, cls: { type: String, default: '' }, alt: { type: String, default: 'Illustrative photo' } })
</script>
<template>
  <div v-if="src" :class="['img', cls]"><img :src="src" :alt="alt" /><span class="ill">{{ t('common.illustrative') }}</span></div>
  <div v-else :class="['img', 'noimg', cls]" role="img" :aria-label="alt">{{ alt }}</div>
</template>
