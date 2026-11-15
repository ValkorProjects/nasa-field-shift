<script setup>
import { t } from '@/i18n'
defineProps({ src: String, cls: { type: String, default: '' }, alt: { type: String, default: 'Illustrative photo' } })
</script>
<template>
  <div :class="['img', cls]"><img :src="src" :alt="alt" /><span class="ill">{{ t('common.illustrative') }}</span></div>
</template>
