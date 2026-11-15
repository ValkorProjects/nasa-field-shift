<script setup>
// First access (issue #38): create a local profile. Only a nickname, no password, no personal data.
import { ref, nextTick, onMounted } from 'vue'
import { account, createProfile, switchProfile, importProfile, NICK_MAX } from '@/data/account.js'
import { storageAvailable } from '@/data/storage.js'

const nick = ref('')
const err = ref('')
const input = ref(null)
const fileIn = ref(null)
onMounted(() => nextTick(() => input.value?.focus()))

function start() {
  try { createProfile(nick.value) } catch (e) { err.value = e.message }
}
async function onImport(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  try { await importProfile(file) } catch (x) { err.value = x.message }
}
</script>

<template>
  <main class="welcome">
    <div class="wl-card">
      <img src="/img/brand/rollcrop-logo.png" alt="RollCrop" width="240" height="109" />
      <h1>Plan your next crop with past NASA data</h1>
      <p class="wl-lead">RollCrop compares your crop rotation with two alternatives, using past weather, soil and plant data
        for your field. It supports you and your agronomist; it does not replace them.</p>
      <form class="wl-form" @submit.prevent="start">
        <label for="nick">Choose a nickname</label>
        <div class="wl-row">
          <input id="nick" ref="input" v-model="nick" :maxlength="NICK_MAX" autocomplete="off" placeholder="e.g. João's farm" />
          <button class="btn green" type="submit" :disabled="!nick.trim()">Start</button>
        </div>
        <p v-if="err" class="wl-err" role="alert">{{ err }}</p>
        <p class="wl-note">No password and no personal data: your nickname and your fields stay only in this browser.
          <template v-if="!storageAvailable()"> This browser blocks storage, so they will be lost when you close the tab.</template></p>
      </form>
      <div class="wl-more">
        <template v-if="account.profiles.length">
          <span>Or continue as</span>
          <button v-for="p in account.profiles" :key="p.id" class="lnk" @click="switchProfile(p.id)">{{ p.nick }}</button>
          <span>·</span>
        </template>
        <button class="lnk" @click="fileIn.click()">Import a profile (JSON)</button>
        <input ref="fileIn" type="file" accept="application/json,.json" hidden @change="onImport" />
      </div>
      <p class="wl-foot">NASA Space Apps Challenge 2026 · theme “Field Shift: Adapting Farms with NASA Data”</p>
    </div>
  </main>
</template>
