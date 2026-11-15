<script setup>
// Screen 8 · How we calculated
import AppShell from '@/components/AppShell.vue'
import Chip from '@/components/Chip.vue'

const kinds = [
  { scale: 'field', b: 'Measured on your field', s: 'Satellite pixels of 30 m. The most precise.' },
  { scale: 'area', b: 'Data for your area', s: 'Pixels of 9 to 50 km. Shows the region, not your field.' },
  { scale: 'est', b: 'Estimate', s: 'We combine data or use public maps. Less sure.' },
  { scale: 'book', b: 'Crop knowledge', s: 'General facts about each crop. Not measured.' }
]
const rows = [
  ['Rain in April–May, heavy-rain months', 'NASA GPM IMERG', 'area', '~10 km · daily · 20+ years', 'Past rain only, not a forecast'],
  ['Soil moisture', 'NASA SMAP', 'area', '9 km · since 2015', 'Never a measurement of your field'],
  ['Bare soil, plant cover, crop history', 'NASA HLS (Landsat + Sentinel-2)', 'field', '30 m · every 2–3 days', 'Clouds leave gaps in summer'],
  ['Frost', 'NASA POWER', 'area', '~50 km · daily · 40+ years', 'Low spots can be colder'],
  ['Slope', 'NASADEM', 'field', '30 m', 'Does not see terraces'],
  ['Rain washing soil away', 'GPM + NASADEM + HLS + soil type', 'est', 'Relative: low / some / high', 'Not tons of soil lost'],
  ['Soil type, drainage', 'Your answers, or public soil maps', 'est', 'Maps ~250 m', 'Lower confidence'],
  ['Nitrogen, water needs, crop calendars', 'Crop knowledge tables', 'book', 'General', 'Not measured on your field'],
  ['Prices, costs, harvest area', 'CEPEA · CONAB · IBGE', 'area', 'Region / state', 'Past data, no price forecast']
]
</script>

<template>
  <AppShell active="how" crumb="How we calculated" title="How we calculated">
    <div class="howpg">
      <div class="card">
        <div class="h2">4 kinds of data</div>
        <div class="kinds">
          <div v-for="k in kinds" :key="k.scale"><Chip :scale="k.scale" /><b>{{ k.b }}</b><span>{{ k.s }}</span></div>
        </div>
      </div>
      <div class="card">
        <div class="h2">Where RollCrop works</div>
        <div class="howmodes">
          <div><b>MVP area: Itaberá and Itapeva (SP)</b>
            <span>Where the team loaded the satellite data. Fields must be inside these two towns (yellow outline on the map).
              Data comes from live calls, saved copies of them (cache) or the downloaded demo data (shown as "mock").</span></div>
          <div><b>Exploratory mode: anywhere else in Brazil</b>
            <span>Live data only: no downloaded data is used. If a source does not answer, that block says "not available"; it is never replaced by examples.
              Calendars and alerts were validated for São Paulo state only.</span></div>
        </div>
      </div>
      <div class="card">
        <div class="h2">What we show and where it comes from</div>
        <table class="tbl t2">
          <thead><tr><th scope="col">What you see</th><th scope="col">Data</th><th scope="col">How detailed</th><th scope="col">Limit</th></tr></thead>
          <tbody>
            <tr v-for="r in rows" :key="r[0]"><td><b>{{ r[0] }}</b></td><td><Chip :scale="r[2]" :source="r[1]" /></td><td>{{ r[3] }}</td><td>{{ r[4] }}</td></tr>
          </tbody>
        </table>
      </div>
      <div class="howb">
        <div class="card">
          <div class="h2">How "How sure are we?" works</div>
          <p class="pp">4 checks: enough years of data · data from your field (not only the area) · sources agree · your soil information. <b>4 = High, 2–3 = Medium, 0–1 = Low.</b></p>
          <div class="h2" style="margin-top:8px">How "Best for you" works</div>
          <p class="pp">Each plan gets Good / OK / Poor for each priority. Your 1st priority counts 4, then 3, 2, 1.</p>
        </div>
        <div class="card">
          <div class="h2">Always check on your farm</div>
          <ul class="ul"><li>Soil test</li><li>Low spots where frost settles</li><li>Seed, input and grain prices</li><li>Your machines and labor</li><li>Planting-window rules and insurance</li></ul>
          <p class="pp ai">Prototype made with AI assistance. Images are illustrative, not AI-generated.</p>
        </div>
      </div>
    </div>
  </AppShell>
</template>
