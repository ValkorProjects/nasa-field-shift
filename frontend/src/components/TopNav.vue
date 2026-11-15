<script setup>
// Top menu (issue #38: replaces the side bar). Field steps follow the selected field; the profile
// menu on the right holds the local account (nickname only, data stays in this browser).
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import Icon from './Icon.vue'
import { t } from '@/i18n'
import { farm, selected, fieldPath } from '@/data/fields.js'
import { account, activeProfile, switchProfile, deleteProfile, clearAll, exportProfile, importProfile } from '@/data/account.js'
import { storageAvailable } from '@/data/storage.js'

const route = useRoute()
const router = useRouter()

const items = computed(() => {
  const has = !!selected.value
  const fp = (sub) => (has ? fieldPath(sub) : null)
  return [
    { id: 'farm', label: 'Map', icon: 'map', to: '/farm', on: route.path.startsWith('/farm') },
    { id: 'crops', label: 'Crops', to: fp('crops'), on: /\/crops$/.test(route.path) },
    { id: 'soil', label: 'Soil', to: fp('soil'), on: /\/soil$/.test(route.path) },
    { id: 'priorities', label: 'Priorities', to: fp('priorities'), on: /\/priorities$/.test(route.path) },
    { id: 'results', label: 'Results', to: fp('results'), on: /\/(results|costs)/.test(route.path) },
    { id: 'plant', label: 'When to plant', icon: 'cal', to: '/planting', on: route.path === '/planting' },
    { id: 'how', label: 'How we calculated', icon: 'calc', to: '/how', on: route.path === '/how' }
  ]
})
const fieldHint = computed(() => (selected.value ? `Steps for ${selected.value.name}` : 'Draw a field on the map first'))

// profile menu
const open = ref(false)
const menu = ref(null)
const fileIn = ref(null)
const others = computed(() => account.profiles.filter((p) => p.id !== account.activeId))
const close = (e) => { if (open.value && menu.value && !menu.value.contains(e.target)) open.value = false }
onMounted(() => document.addEventListener('click', close, true))
onBeforeUnmount(() => document.removeEventListener('click', close, true))

function pick(id) { switchProfile(id); open.value = false; router.push('/farm') }
function newProfile() { account.activeId = null; open.value = false } // App shows the welcome screen
function help() { account.onboarding = true; open.value = false }
function removeMe() {
  if (window.confirm(`Delete the profile "${activeProfile.value?.nick}" and its ${farm.fields.length} field(s) from this browser?`)) {
    deleteProfile(); open.value = false; router.push('/farm')
  }
}
function signOut() {
  if (window.confirm('Sign out and clear all RollCrop data from this browser (every profile and field)?')) {
    clearAll(); open.value = false; router.push('/farm')
  }
}
async function onImport(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  try { await importProfile(file); open.value = false; router.push('/farm') } catch (err) { window.alert(err.message) }
}
</script>

<template>
  <header class="topnav">
    <router-link to="/farm" class="tn-logo" aria-label="RollCrop home">
      <img src="/img/brand/rollcrop-logo.png" :alt="t('app.name')" width="106" height="48" />
    </router-link>
    <nav class="tn-links" aria-label="Main">
      <template v-for="(it, i) in items" :key="it.id">
        <span v-if="i === 1" class="tn-sep" :title="fieldHint" aria-hidden="true"></span>
        <router-link v-if="it.to" :to="it.to" :class="['tn-link', { on: it.on, step: !it.icon }]" :aria-current="it.on ? 'page' : null">
          <Icon v-if="it.icon" :name="it.icon" />{{ it.label }}
        </router-link>
        <span v-else class="tn-link step disabled" :title="fieldHint" aria-disabled="true">{{ it.label }}</span>
        <span v-if="i === 4" class="tn-sep" aria-hidden="true"></span>
      </template>
      <button type="button" class="tn-link" @click="help"><Icon name="help" />Help</button>
    </nav>

    <div ref="menu" class="tn-profile">
      <button type="button" class="tn-me" :aria-expanded="open" aria-haspopup="menu" @click="open = !open">
        <span class="tn-avatar" aria-hidden="true">{{ activeProfile?.nick?.[0]?.toUpperCase() ?? '?' }}</span>
        <span class="tn-nick">{{ activeProfile?.nick }}</span>
        <Icon name="down" />
      </button>
      <div v-if="open" class="tn-menu" role="menu">
        <div class="tn-note">Local profile: only a nickname. Your fields stay in this browser<span v-if="!storageAvailable()"> (storage is blocked: they are lost when you close the tab)</span>.</div>
        <button v-for="p in others" :key="p.id" role="menuitem" @click="pick(p.id)">Switch to {{ p.nick }}</button>
        <button role="menuitem" @click="newProfile">New profile</button>
        <button role="menuitem" @click="exportProfile">Export my fields (JSON)</button>
        <button role="menuitem" @click="fileIn.click()">Import a profile (JSON)</button>
        <button role="menuitem" @click="help">Show the welcome tour</button>
        <button role="menuitem" class="danger" @click="removeMe">Delete this profile</button>
        <button role="menuitem" class="danger" @click="signOut">Sign out and clear all data</button>
        <input ref="fileIn" type="file" accept="application/json,.json" hidden @change="onImport" />
      </div>
    </div>
  </header>
</template>
