<script setup>
// Screen 1 · Mark field. Real satellite map: draw, edit, rename and delete your fields.
// /farm/alert also opens the pre-planting alert (screen 7).
import { ref, computed, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import Stepper from '@/components/Stepper.vue'
import FieldMap from '@/components/FieldMap.vue'
import FieldThumb from '@/components/FieldThumb.vue'
import SampleValue from '@/components/SampleValue.vue'
import Icon from '@/components/Icon.vue'
import PrePlantingAlert from '@/components/PrePlantingAlert.vue'
import { state, profileOf, ensureProfile } from '@/data/store.js'
import { apiMode } from '@/api/index.js'
import { fieldStatus } from '@/data/rules.js'
import { farm, selected, addField, removeField, resetSample, downloadGeoJSON, areaHa, fmtHa, fieldPath } from '@/data/fields.js'

const route = useRoute()
const router = useRouter()
const mapRef = ref(null)
const mode = ref('view') // view | draw | edit
const showAlert = computed(() => route.meta.alert === true)
const d = computed(() => state.data)
const f = computed(() => selected.value)
// Profile of the selected field (POST /api/field/profile). Field 1 in mock mode has none: it shows the demo sample.
const p = computed(() => profileOf(f.value?.id))
const demo = computed(() => !d.value?.meta?.live) // sample JSON shown as is (mock mode)
// First load shows the waiting message; a new border keeps the previous profile on screen while it updates.
const loading = computed(() => p.value?.status === 'loading' && !p.value.profile)
const updating = computed(() => p.value?.status === 'loading' && !!p.value.profile)
const failed = computed(() => p.value?.status === 'error')
const pillKey = computed(() => (demo.value ? f.value?.status : fieldStatus(d.value)) ?? 'new')
const blocks = computed(() => d.value?.blocks ?? {})
const useSample = () => { apiMode.value = 'mock' }
const retry = () => ensureProfile(f.value, { force: true })
const PILL = { g: ['pg', 'Looks fine'], y: ['py', 'Needs attention'], r: ['pr', 'High risk'], new: ['pn2', 'Not analysed yet'] }

function select(id) {
  if (mode.value === 'draw') return
  farm.selectedId = id
  mode.value = 'view'
  mapRef.value?.fitField(id)
}
function startDraw() { mode.value = 'draw' }
async function onDrawn(coords) {
  const nf = addField(coords)
  mode.value = 'view'
  await nextTick()
  mapRef.value?.fitField(nf.id)
}
function del() {
  if (!f.value) return
  if (window.confirm(`Delete ${f.value.name}? This cannot be undone.`)) { removeField(f.value.id); mode.value = 'view' }
}
function reset() {
  if (window.confirm('Replace your fields with the 3 sample fields?')) { resetSample(); mode.value = 'view'; nextTick(() => mapRef.value?.fitAll()) }
}
</script>

<template>
  <AppShell :active="showAlert ? 'alerts' : 'farm'" crumb="My farm" title="Your farm from above">
    <template v-if="!showAlert">
      <div class="resh" style="padding:14px 26px 0"><Stepper :cur="1" /></div>
      <div class="content" style="padding-top:12px">
        <FieldMap ref="mapRef" v-model:layer="state.layer" :mode="mode"
          @select="select" @drawn="onDrawn" />

        <div class="panel">
          <!-- drawing -->
          <div v-if="mode === 'draw'" class="card" role="status">
            <div class="h2">Draw a new field</div>
            <p class="pp">Move the map to your farm (drag, zoom or search a town). Then click once on each corner of the field.
              Click the first corner again, or double-click, to close it.</p>
            <div class="draftinfo">
              <b>{{ mapRef?.draft.corners ?? 0 }}</b> corners · <b>{{ mapRef?.draft.ha ?? '0.0' }}</b> ha
            </div>
            <button class="btn green small" :disabled="(mapRef?.draft.corners ?? 0) < 3" @click="mapRef.finishDraw()">Finish field</button>
            <div class="factions">
              <button class="btn ghost small" :disabled="!mapRef?.draft.corners" @click="mapRef.undoPoint()">Undo last corner</button>
              <button class="btn ghost small" @click="mode = 'view'">Cancel</button>
            </div>
          </div>

          <!-- selected field -->
          <div v-else-if="f" class="card">
            <div class="thumbrow">
              <FieldThumb :key="f.id" :field="f.id" />
              <div style="flex:1;min-width:0">
                <input v-model="f.name" class="fname" aria-label="Field name" maxlength="40" />
                <div class="t-sub">
                  {{ fmtHa(areaHa(f.coords)) }} ha · from your map
                  <template v-if="!loading && !failed"> · slope from satellite: <SampleValue :v="d.field.slope" :dotted="false" /></template>
                </div>
              </div>
            </div>
            <div v-if="loading" class="fnote" role="status">Fetching NASA data for this field…</div>
            <div v-else-if="failed" class="fnote warn" role="alert">
              Could not get the data for this field: {{ p.error }}
              <div class="factions">
                <button class="btn ghost small" @click="retry">Try again</button>
                <button class="btn ghost small" @click="useSample">Use sample data</button>
              </div>
            </div>
            <template v-else>
              <div class="kv"><span>Summer crop now</span><b><SampleValue :v="d.field.summer" :dotted="false" /> · harvest <SampleValue :v="d.field.harvest" /></b></div>
              <div class="kv"><span>Next crop planned</span><b><SampleValue :v="d.field.next" :dotted="false" /> · planting from <SampleValue :v="d.field.planting" /></b></div>
              <div v-if="updating" class="fnote" role="status">Updating the data for the new border…</div>
              <div v-if="d.meta.sampleOnly" class="fnote">Sample values for the demo: they were not computed for this field. Use the real backend (<code>npm run dev:api</code>) for NASA data.</div>
              <div v-if="!demo" class="fnote">
                <span :class="['pill', PILL[pillKey][0]]" style="margin:0 6px 0 0">{{ PILL[pillKey][1] }}</span>
                <template v-if="d.alert.unavailable">Pre-planting check not available: {{ d.alert.unavailable }}</template>
                <template v-else>Rain and frost from {{ d.profile?.weather_summary?.source?.dataset }} past records.</template>
              </div>
              <div v-if="d.info?.weatherNote" class="fnote">{{ d.info.weatherNote }}</div>
              <div v-if="blocks.soil && blocks.soil.status !== 'ok'" class="fnote">Soil not available for this field: {{ blocks.soil.reason }}</div>
              <div v-else-if="d.info?.soilNote" class="fnote">{{ d.info.soilNote }}</div>
            </template>
            <div v-if="mode === 'edit'" class="fnote" role="status">
              <b>Drag the white corners</b> to fix the border. Drag a small blue dot to add a corner. Right-click a corner to remove it.
            </div>
            <div class="factions">
              <button class="btn ghost small" :aria-pressed="mode === 'edit'" @click="mode = mode === 'edit' ? 'view' : 'edit'">
                <Icon name="pencil" /> {{ mode === 'edit' ? 'Done' : 'Fix the border' }}
              </button>
              <button class="btn danger small" @click="del"><Icon name="x" /> Delete</button>
            </div>
          </div>

          <div v-else class="card">
            <div class="h2">No fields yet</div>
            <p class="pp">Find your farm on the map and draw your first field.</p>
          </div>

          <div v-if="f && !loading && !failed && d.alert.active && !d.meta.sampleOnly && mode !== 'draw'" class="alert alert-click" role="button" tabindex="0"
            @click="router.push('/farm/alert')" @keydown.enter.space.prevent="router.push('/farm/alert')">
            <div class="aic"><Icon name="warn" /></div>
            <div><b>{{ f.name }} needs a look before planting</b>
              <p>Past rain records show dry autumns here. Compare options before you buy seed.</p></div>
          </div>

          <button v-if="f && !loading && !failed && mode !== 'draw'" class="btn green" @click="router.push(fieldPath('crops'))">This is my field — next →</button>
          <button v-if="mode !== 'draw'" class="btn ghost" @click="startDraw"><Icon name="pencil" /> Draw a new field</button>

          <div class="card list">
            <div class="h2">Your fields ({{ farm.fields.length }})</div>
            <div v-for="x in farm.fields" :key="x.id" :class="['row', { on: x.id === farm.selectedId }]"
              role="button" tabindex="0" @click="select(x.id)" @keydown.enter.prevent="select(x.id)">
              <FieldThumb :field="x.id" :w="44" :h="44" :pad="3" />
              <span>{{ x.name }}<small>{{ fmtHa(areaHa(x.coords)) }} ha</small></span>
              <span :class="['pill', PILL[x.status][0]]">{{ PILL[x.status][1] }}</span>
            </div>
            <div class="tools">
              <button @click="downloadGeoJSON">Download fields (GeoJSON)</button>
              <button @click="reset">Reset sample fields</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- Screen 7: map in "Plant cover", alert modal on top -->
    <div v-else class="content"><FieldMap layer="veg" :show-controls="false" /></div>

    <template #overlay>
      <PrePlantingAlert v-if="showAlert" @close="router.push('/farm')" @compare="router.push(fieldPath('results'))" />
    </template>
  </AppShell>
</template>
