<script setup>
import { t } from '@/i18n'
</script>
<template>
  <div class="banner" role="note">
    <b>{{ t('banner.lead') }}</b> · {{ t('banner.text') }} <span class="ex">{{ t('banner.dotted') }}</span> {{ t('banner.tail') }}
  </div>
</template>
