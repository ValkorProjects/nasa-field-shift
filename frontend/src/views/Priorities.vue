<script setup>
// Screen 4 · Priorities: drag the cards or use the arrows. The best option updates live.
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import AppShell from '@/components/AppShell.vue'
import Stepper from '@/components/Stepper.vue'
import Icon from '@/components/Icon.vue'
import { state, bestId, bestIfIncomeFirst, strategy, priorityLabel } from '@/data/store.js'
import { fieldPath, selected } from '@/data/fields.js'

const router = useRouter()
const items = computed(() => state.order.map((id) => state.data.priorities.items.find((p) => p.id === id)))

function move(from, to) {
  if (to < 0 || to >= state.order.length || from === to) return
  const o = [...state.order]
  const [x] = o.splice(from, 1)
  o.splice(to, 0, x)
  state.order = o
}

// HTML5 drag & drop
const dragFrom = ref(null)
const over = ref(null)
function onDrop(i) {
  if (dragFrom.value !== null) move(dragFrom.value, i)
  dragFrom.value = over.value = null
}

const best = computed(() => strategy(bestId.value))
const alt = computed(() => strategy(bestIfIncomeFirst.value))
const label = (s) => `${s.tag} · ${s.name.value}`
</script>

<template>
  <AppShell active="fields" :crumb="`My fields › ${selected?.name}`" title="Choose your priorities">
    <div class="wiz">
      <div class="wl">
        <Stepper :cur="4" />
        <div class="q">What matters most to you?</div>
        <p class="lead">Put the most important at the top. Drag the cards or use the arrows.</p>
        <ol class="prios" aria-label="Your priorities, most important first" style="list-style:none">
          <li v-for="(p, i) in items" :key="p.id"
            :class="['prio', { dragging: dragFrom === i, over: over === i && dragFrom !== i }]"
            draggable="true"
            @dragstart="dragFrom = i" @dragend="dragFrom = over = null"
            @dragover.prevent="over = i" @drop.prevent="onDrop(i)">
            <div class="pn">{{ i + 1 }}</div>
            <Icon name="grip" cls="grip" />
            <div class="pi"><Icon :name="p.icon" /></div>
            <div class="pt"><b>{{ p.label }}</b><span>{{ p.desc }}</span></div>
            <div class="pud">
              <button :disabled="i === 0" :aria-label="`Move ${p.label} up`" @click="move(i, i - 1)"><Icon name="up" /></button>
              <button :disabled="i === items.length - 1" :aria-label="`Move ${p.label} down`" @click="move(i, i + 1)"><Icon name="down" /></button>
            </div>
          </li>
        </ol>
      </div>
      <div class="wr">
        <div class="card preview" aria-live="polite">
          <div class="k">With this order, the best option is</div>
          <div class="pvname">{{ label(best) }}</div>
          <p class="pp">Because you put <b>{{ priorityLabel(state.order[0]) }}</b> and <b>{{ priorityLabel(state.order[1]) }}</b> first.</p>
          <div v-if="state.order[0] !== 'income'" class="whatif">
            <b>If you put Income first:</b> {{ alt.id !== best.id ? `${label(alt)} would be first.` : `${best.tag} would still be first.` }}
          </div>
          <div class="how">How we rank: each option gets Good / OK / Poor for each priority. Higher priorities count more (4, 3, 2, 1).</div>
        </div>
        <button class="btn green" style="margin-top:auto" @click="router.push(fieldPath('results'))">See results →</button>
        <button class="btn ghost" @click="router.push(fieldPath('soil'))">← Back</button>
      </div>
    </div>
  </AppShell>
</template>
