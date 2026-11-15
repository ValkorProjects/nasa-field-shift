<script setup>
import { SCALE_IC, SCALE_TXT } from '@/data/icons.js'
import { t } from '@/i18n'
const keys = ['field', 'area', 'book', 'est']
</script>
<template>
  <div class="slegend">
    <b>{{ t('scale.legend') }}</b>
    <span v-for="k in keys" :key="k"><span :class="['chip2', `c-${k}`]"><svg viewBox="0 0 24 24" aria-hidden="true" v-html="SCALE_IC[k]" /></span>{{ SCALE_TXT[k] }}</span>
    <router-link to="/how">{{ t('scale.how') }}</router-link>
  </div>
</template>
