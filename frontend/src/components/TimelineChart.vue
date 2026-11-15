<script setup>
// Planting timeline (issue #7): planting windows and critical-event periods on the same date axis.
import { computed } from 'vue'

const props = defineProps({
  season: { type: Object, required: true },   // { start, end } ISO dates
  windows: { type: Array, default: () => [] }, // { start, end, level: recommended|risky|avoid }
  events: { type: Array, default: () => [] },  // { type, label, start, end, years_hit, years_total }
  today: { type: String, default: null }       // ISO date
})

const W = 1000, X0 = 170, X1 = 985, ROW = 46, TOP = 34
const day = (s) => Date.parse(`${s}T00:00:00Z`)
const t0 = computed(() => day(props.season.start))
const t1 = computed(() => day(props.season.end) + 864e5)
const x = (s) => X0 + ((day(s) - t0.value) / (t1.value - t0.value)) * (X1 - X0)
const xEnd = (s) => x(new Date(day(s) + 864e5).toISOString().slice(0, 10))
const clampW = (a, b) => Math.max(2, b - a)

const LEVEL = {
  recommended: { fill: '#2e8b3d', text: '#fff', label: 'Best time' },
  risky: { fill: '#e0a400', text: '#3d2c00', label: 'Risky' },
  avoid: { fill: 'url(#tl-hatch)', text: '#7a1f1f', label: 'Avoid' }
}
const EVENT_COL = { frost: '#4a52b3', white_mold: '#7a4aa8' }

const rows = computed(() => [{ kind: 'plant', label: 'When to plant' }, ...props.events.map((e) => ({ kind: 'event', label: e.label, e }))])
const H = computed(() => TOP + rows.value.length * ROW + 30)

const months = computed(() => {
  const out = []
  const d = new Date(t0.value)
  d.setUTCDate(1)
  while (d.getTime() < t1.value) {
    const iso = d.toISOString().slice(0, 10)
    if (d.getTime() >= t0.value) out.push({ x: x(iso), label: d.toLocaleString('en-US', { month: 'short', timeZone: 'UTC' }), year: d.getUTCMonth() === 0 ? d.getUTCFullYear() : null })
    d.setUTCMonth(d.getUTCMonth() + 1)
  }
  return out
})
const todayX = computed(() => (props.today && day(props.today) >= t0.value && day(props.today) < t1.value ? x(props.today) : null))
const fmt = (s) => new Date(day(s)).toLocaleDateString('en-US', { month: 'short', day: 'numeric', timeZone: 'UTC' })
</script>

<template>
  <figure class="tl">
    <svg :viewBox="`0 0 ${W} ${H}`" width="100%" role="img"
      :aria-label="`Timeline. ${windows.map((w) => `${LEVEL[w.level]?.label}: ${fmt(w.start)} to ${fmt(w.end)}`).join('. ')}. ${events.map((e) => `${e.label}: ${fmt(e.start)} to ${fmt(e.end)}, ${e.years_hit} of ${e.years_total} years`).join('. ')}`">
      <defs>
        <pattern id="tl-hatch" width="10" height="10" patternTransform="rotate(45)" patternUnits="userSpaceOnUse">
          <rect width="10" height="10" fill="#fde1e1" /><line x1="0" y1="0" x2="0" y2="10" stroke="#e04848" stroke-width="4" />
        </pattern>
      </defs>

      <!-- month grid -->
      <g v-for="m in months" :key="m.x">
        <line :x1="m.x" :x2="m.x" :y1="TOP - 8" :y2="H - 26" stroke="#e1e7dd" />
        <text :x="m.x + 4" :y="H - 10" class="tl-mo">{{ m.label }}<tspan v-if="m.year" class="tl-yr" dx="4">{{ m.year }}</tspan></text>
      </g>

      <!-- event bands span all rows so overlap with planting is easy to see -->
      <rect v-for="e in events" :key="`band-${e.type}`" :x="x(e.start)" :y="TOP - 8" :width="clampW(x(e.start), xEnd(e.end))"
        :height="H - TOP - 18" :fill="EVENT_COL[e.type] ?? '#555'" opacity=".08" />

      <g v-for="(r, i) in rows" :key="r.label" :transform="`translate(0, ${TOP + i * ROW})`">
        <text x="0" y="22" class="tl-rl">{{ r.label }}</text>
        <rect :x="X0" y="4" :width="X1 - X0" :height="ROW - 14" rx="8" fill="#f5f7f3" />
        <template v-if="r.kind === 'plant'">
          <g v-for="w in windows" :key="w.start">
            <rect :x="x(w.start)" y="4" :width="clampW(x(w.start), xEnd(w.end))" :height="ROW - 14" rx="7"
              :fill="LEVEL[w.level]?.fill ?? '#999'" :stroke="w.level === 'avoid' ? '#e04848' : 'none'" />
            <text v-if="xEnd(w.end) - x(w.start) > (LEVEL[w.level]?.label.length ?? 6) * 8.5 + 14" :x="x(w.start) + 8" y="25" class="tl-seg"
              :fill="LEVEL[w.level]?.text">{{ LEVEL[w.level]?.label }}</text>
          </g>
        </template>
        <template v-else>
          <rect :x="x(r.e.start)" y="4" :width="clampW(x(r.e.start), xEnd(r.e.end))" :height="ROW - 14" rx="7"
            :fill="EVENT_COL[r.e.type] ?? '#555'" />
          <text :x="x(r.e.start) + 8" y="25" class="tl-seg" fill="#fff">{{ r.e.years_hit }} of {{ r.e.years_total }} years</text>
        </template>
      </g>

      <g v-if="todayX !== null">
        <line :x1="todayX" :x2="todayX" :y1="TOP - 14" :y2="H - 26" stroke="#12301c" stroke-width="2" stroke-dasharray="4 3" />
        <text :x="todayX" :y="TOP - 18" text-anchor="middle" class="tl-today">Today</text>
      </g>
    </svg>
    <figcaption class="tl-leg">
      <span><i style="background:#2e8b3d"></i>Best time to plant</span>
      <span><i style="background:#e0a400"></i>Risky</span>
      <span><i class="hatch"></i>Avoid</span>
      <span v-for="e in events" :key="`leg-${e.type}`"><i :style="{ background: EVENT_COL[e.type] }"></i>{{ e.label }} (past years)</span>
    </figcaption>
  </figure>
</template>

<style scoped>
.tl { margin: 0 }
.tl-mo { font: 700 12px Inter, sans-serif; fill: #617061 }
.tl-yr { font-weight: 800; fill: #12301c }
.tl-rl { font: 800 14px Inter, sans-serif; fill: #16241a }
.tl-seg { font: 800 13px Inter, sans-serif }
.tl-today { font: 800 12px Inter, sans-serif; fill: #12301c }
.tl-leg { display: flex; flex-wrap: wrap; gap: 14px; font-size: 13px; font-weight: 700; color: #3c4c3e; margin-top: 6px }
.tl-leg span { display: flex; align-items: center; gap: 6px }
.tl-leg i { width: 14px; height: 14px; border-radius: 4px; display: block }
.tl-leg i.hatch { background: repeating-linear-gradient(45deg, #fde1e1 0 4px, #e04848 4px 7px) }
</style>
