<script setup>
// Screen 7 · modal over the map (Plant cover layer). GPM/POWER = past records, SMAP = regional context.
import { computed, onMounted, onBeforeUnmount, ref } from 'vue'
import Icon from './Icon.vue'
import Chip from './Chip.vue'
import FieldThumb from './FieldThumb.vue'
import SampleValue from './SampleValue.vue'
import { state } from '@/data/store.js'

const emit = defineEmits(['close', 'compare'])
const a = computed(() => state.data.alert)
const NDVI = ['#a5532a', '#d9b25c', '#f1ec9a', '#9fd06a', '#3f9a3a', '#14582a']

const first = ref(null)
const onKey = (e) => e.key === 'Escape' && emit('close')
onMounted(() => { document.addEventListener('keydown', onKey); first.value?.focus() })
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<template>
  <div class="overlay" @click.self="emit('close')">
    <div class="modal m2" role="alertdialog" aria-modal="true" aria-labelledby="alert-title">
      <div class="mleft">
        <FieldThumb field="1" w="300" h="520" layer="veg" :pad="30" />
        <div class="mcap">
          Field 1 · plant cover
          <div class="scale"><i v-for="c in NDVI" :key="c" :style="{ background: c }"></i></div>
          <div class="sl"><span>Bare</span><span>Dense</span></div>
          <div class="ill2">Illustrative image</div>
        </div>
      </div>
      <div class="mright">
        <div class="redtop"><div class="aic"><Icon name="warn" /></div>Before planting · Field 1</div>
        <h2 id="alert-title">{{ a.title }}</h2>
        <p class="lead">Planting starts <SampleValue :v="a.planting" />, in about <SampleValue :v="a.weeks" /> weeks. You still have time to change.</p>
        <div class="fact">
          <Icon name="rain" cls="fi" />
          <div class="fn"><SampleValue :v="a.rain_years" /></div>
          <div><b>years had too little rain in April–May</b><span class="rsub">Past records, not a forecast</span><Chip scale="area" :source="a.rain_years.source" /></div>
        </div>
        <div class="fact">
          <Icon name="frost" cls="fi" />
          <div class="fn"><SampleValue :v="a.frost_years" /></div>
          <div><b>years had frost in June</b><span class="rsub">Late corn can be hurt</span><Chip scale="area" :source="a.frost_years.source" /></div>
        </div>
        <div class="ctx"><Icon name="drop" /><span><SampleValue :v="a.smap_context" :dotted="false" /></span><Chip scale="area" :source="a.smap_context.source" /></div>
        <div class="btns">
          <button ref="first" class="btn green" @click="emit('compare')">Compare 3 plans</button>
          <button class="btn ghost" style="width:170px" @click="emit('close')">OK, got it</button>
        </div>
        <div class="tiny">Check with your agronomist before you decide. · <router-link class="lnk" :to="{ path: '/planting', query: { loc: 'field-1', crop: 'corn' } }">See the best planting dates →</router-link></div>
      </div>
    </div>
  </div>
</template>
