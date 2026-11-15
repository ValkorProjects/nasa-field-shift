<script setup>
import SampleValue from './SampleValue.vue'
import { t } from '@/i18n'
import { state } from '@/data/store.js'
defineProps({ crumb: String, title: String })
</script>
<template>
  <div class="top">
    <div><div class="crumb">{{ crumb }}</div><h1>{{ title }}</h1></div>
    <div class="topr"><slot /><div class="date">{{ t('top.exampleDate') }} <SampleValue :v="state.data?.scenario.today" /></div></div>
  </div>
</template>
