<script setup>
// When to plant (issue #7): choose a place + crop → GET /api/recommendation →
// planting windows and critical events on one timeline, explanations, NASA POWER attribution.
import { ref, computed, watch, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import Icon from '@/components/Icon.vue'
import Chip from '@/components/Chip.vue'
import IllustrativeImg from '@/components/IllustrativeImg.vue'
import TimelineChart from '@/components/TimelineChart.vue'
import AgronomistNote from '@/components/AgronomistNote.vue'
import { getRecommendation, apiMode, PRESET_LOCATIONS, CROPS } from '@/api/index.js'
import { farm } from '@/data/fields.js'
import { state } from '@/data/store.js'

const route = useRoute()
const router = useRouter()

// Locations: the 3 demo points + the farmer's own fields (polygon centroid).
const centroid = (coords) => coords.reduce((a, [la, lo]) => [a[0] + la / coords.length, a[1] + lo / coords.length], [0, 0])
const locations = computed(() => [
  ...farm.fields.map((f) => {
    const [lat, lon] = centroid(f.coords)
    return { id: `field-${f.id}`, name: f.name, group: 'Your fields', lat, lon }
  }),
  ...PRESET_LOCATIONS.map((p) => ({ ...p, group: 'MVP places' }))
])
const locId = computed({
  get: () => (locations.value.some((l) => l.id === route.query.loc) ? route.query.loc : locations.value[0]?.id),
  set: (v) => router.replace({ query: { ...route.query, loc: v } })
})
const crop = computed({
  get: () => (CROPS.some((c) => c.id === route.query.crop) ? route.query.crop : 'corn'),
  set: (v) => router.replace({ query: { ...route.query, crop: v } })
})
const loc = computed(() => locations.value.find((l) => l.id === locId.value))

// Fetch with loading / error states; a new choice cancels the request in flight.
const data = ref(null)
const loading = ref(false)
const error = ref(null)
let ctrl = null
async function load() {
  if (!loc.value) return
  ctrl?.abort()
  ctrl = new AbortController()
  loading.value = true
  error.value = null
  try {
    data.value = await getRecommendation({ lat: loc.value.lat, lon: loc.value.lon, crop: crop.value, name: loc.value.name }, { signal: ctrl.signal })
  } catch (e) {
    if (e.name === 'AbortError') return
    error.value = e.message
    data.value = null
  }
  loading.value = false
}
watch([() => loc.value?.id, crop, apiMode], load, { immediate: true })
onBeforeUnmount(() => ctrl?.abort())

function useSample() { apiMode.value = 'mock' }

// "Today" = the scenario's example date
const today = computed(() => {
  const d = new Date(`${state.data?.scenario.today.value ?? ''} 12:00`)
  return isNaN(d) ? null : d.toISOString().slice(0, 10)
})
const fmt = (s) => new Date(`${s}T12:00:00Z`).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
const LEVEL = { recommended: ['g', 'Best time'], risky: ['y', 'Risky'], avoid: ['r', 'Avoid'] }
const MODE = {
  live: ['lg', 'Live data'],
  cache: ['ly', 'From cache'],
  mock: ['ly', 'Sample data (mock)']
}
const cropInfo = computed(() => CROPS.find((c) => c.id === crop.value))
</script>

<template>
  <AppShell active="plant" crumb="My fields › When to plant" title="When to plant">
    <div class="plantpg">
      <!-- choices -->
      <div class="card pchoose">
        <div class="pc-loc">
          <label class="ql" for="loc">1. Where?</label>
          <select id="loc" v-model="locId" class="psel">
            <optgroup v-for="g in ['Your fields', 'Demo places']" :key="g" :label="g">
              <option v-for="l in locations.filter((x) => x.group === g)" :key="l.id" :value="l.id">{{ l.name }}</option>
            </optgroup>
          </select>
          <span class="pc-coord" v-if="loc">{{ loc.lat.toFixed(3) }}, {{ loc.lon.toFixed(3) }}</span>
        </div>
        <div class="pc-crop">
          <div class="ql" id="crop-q">2. Which crop?</div>
          <div class="pcrops" role="radiogroup" aria-labelledby="crop-q">
            <button v-for="c in CROPS" :key="c.id" :class="['pcrop', { sel: crop === c.id }]" role="radio"
              :aria-checked="crop === c.id" @click="crop = c.id">
              <IllustrativeImg :src="c.img" :alt="c.label" cls="pcimg" />
              <span><b>{{ c.label }}</b><small>Main risk: {{ c.risk }}</small></span>
            </button>
          </div>
        </div>
      </div>

      <!-- loading -->
      <div v-if="loading && !data" class="card pstate" role="status" aria-live="polite">
        <div class="spinner" aria-hidden="true"></div>Checking past weather for {{ loc?.name }}…
      </div>

      <!-- error -->
      <div v-else-if="error" class="card pstate perr" role="alert">
        <div class="aic"><Icon name="warn" /></div>
        <div>
          <b>We could not get the recommendation.</b>
          <p>{{ error }}</p>
          <div class="factions">
            <button class="btn green small" @click="load">Try again</button>
            <button v-if="apiMode === 'api'" class="btn ghost small" @click="useSample">Use sample data</button>
          </div>
        </div>
      </div>

      <!-- result -->
      <template v-else-if="data">
        <div :class="['card', 'precom', { busy: loading }]" aria-live="polite">
          <div class="bstar" aria-hidden="true"><Icon name="cal" /></div>
          <div>
            <div class="k">{{ data.crop_label ?? cropInfo?.label }} · {{ data.location?.name }}</div>
            <div class="psum">{{ data.recommendation.summary }}</div>
            <p class="pp" style="margin:0">{{ data.recommendation.explanation }}</p>
          </div>
        </div>

        <div class="card">
          <div class="h2">Planting windows and risky periods</div>
          <p class="pp">Colored bands at the bottom show when the risk happened in past years. Plant so the sensitive stage of the crop stays out of them.</p>
          <TimelineChart :season="data.season" :windows="data.windows" :events="data.events" :today="today" />
        </div>

        <div class="mrow">
          <div class="card" style="flex:1.2">
            <div class="h2">Why these dates</div>
            <div v-for="w in data.windows" :key="w.start" class="pwin">
              <span :class="['lvl', `l${LEVEL[w.level]?.[0] ?? 'y'}`]"><i class="d"></i>{{ LEVEL[w.level]?.[1] ?? w.level }}</span>
              <div><b>{{ fmt(w.start) }} – {{ fmt(w.end) }}</b><span>{{ w.explanation }}</span></div>
            </div>
          </div>
          <div class="card" style="flex:1">
            <div class="h2">Critical events in past years</div>
            <div v-for="e in data.events" :key="e.type" class="pevt">
              <div class="fn">{{ e.years_hit }} of {{ e.years_total }}</div>
              <div>
                <b>{{ e.label }} · {{ fmt(e.start) }} – {{ fmt(e.end) }}</b>
                <p class="pe-x">{{ e.explanation }}</p>
                <small v-if="e.threshold">Rule: {{ e.threshold }}</small>
                <Chip scale="area" source="NASA POWER" />
              </div>
            </div>
          </div>
        </div>

        <!-- NASA attribution (required on every screen of this flow) -->
        <div class="nasa-src">
          <Icon name="info" />
          <span>
            <b>Data: <a :href="data.source.url" target="_blank" rel="noopener">{{ data.source.dataset }}</a></b>
            ({{ data.source.url.replace(/^https?:\/\//, '').replace(/\/$/, '') }}) ·
            {{ data.source.parameters?.join(', ') }} · {{ data.source.period }}. {{ data.source.note }}
          </span>
          <span :class="['lvl', MODE[data.source.mode]?.[0] ?? 'ly']"><i class="d"></i>{{ MODE[data.source.mode]?.[1] ?? data.source.mode }}</span>
        </div>

        <details class="rawjson">
          <summary>Raw response ({{ apiMode === 'api' ? 'GET /api/recommendation' : 'mock' }})</summary>
          <pre>{{ JSON.stringify(data, null, 2) }}</pre>
        </details>

        <AgronomistNote />
      </template>
    </div>
  </AppShell>
</template>
