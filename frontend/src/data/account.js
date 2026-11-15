// Local account (issue #38): a nickname and the fields saved under it, only in this browser.
// It is NOT authentication: no password and no personal data. Several profiles can share a browser.
//   fieldshift.profiles          [{ id, nick, created }]
//   fieldshift.profile           active profile id
//   fieldshift.p.<id>.fields     the profile's fields (see fields.js)
//   fieldshift.p.<id>.scope      'mvp' | 'explore' (map mode, issue #39)
//   fieldshift.p.<id>.onboarded  true once the welcome tour was shown
import { reactive, computed } from 'vue'
import { getJSON, setJSON, remove, keysWithPrefix } from './storage.js'

const PREFIX = 'fieldshift.'
export const NICK_MAX = 30

export const account = reactive({
  profiles: getJSON(`${PREFIX}profiles`, []),
  activeId: getJSON(`${PREFIX}profile`, null),
  onboarding: false // the welcome tour is open
})
if (!account.profiles.some((p) => p.id === account.activeId)) account.activeId = account.profiles[0]?.id ?? null

export const activeProfile = computed(() => account.profiles.find((p) => p.id === account.activeId) ?? null)
export const profileKey = (name, id = account.activeId) => `${PREFIX}p.${id}.${name}`

function saveList() {
  setJSON(`${PREFIX}profiles`, account.profiles)
  setJSON(`${PREFIX}profile`, account.activeId)
}

export function createProfile(nick) {
  const clean = String(nick ?? '').trim().slice(0, NICK_MAX)
  if (!clean) throw new Error('Type a nickname')
  const p = { id: `u${Date.now().toString(36)}`, nick: clean, created: new Date().toISOString().slice(0, 10) }
  account.profiles.push(p)
  account.activeId = p.id
  saveList()
  account.onboarding = true // first access: show the welcome tour
  return p
}

export function switchProfile(id) {
  if (!account.profiles.some((p) => p.id === id)) return
  account.activeId = id
  saveList()
}

// Removes the profile and everything saved under it. Back to the welcome screen when none is left.
export function deleteProfile(id = account.activeId) {
  for (const k of keysWithPrefix(`${PREFIX}p.${id}.`)) remove(k)
  account.profiles = account.profiles.filter((p) => p.id !== id)
  if (account.activeId === id) account.activeId = account.profiles[0]?.id ?? null
  saveList()
}

// Sign out and clear every RollCrop key in this browser (all profiles, caches of public data).
export function clearAll() {
  for (const k of keysWithPrefix(PREFIX)) remove(k)
  account.profiles = []
  account.activeId = null
  account.onboarding = false
}

export const isOnboarded = () => getJSON(profileKey('onboarded'), false) === true
export function finishOnboarding() {
  setJSON(profileKey('onboarded'), true)
  account.onboarding = false
}

// Export / import one profile as JSON (nickname + fields + map mode). Nothing leaves the browser by itself.
export function exportProfile() {
  const p = activeProfile.value
  if (!p) return
  const data = { app: 'RollCrop', version: 1, nick: p.nick, fields: getJSON(profileKey('fields'), []), scope: getJSON(profileKey('scope'), 'mvp') }
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `rollcrop-${p.nick.replace(/[^\w-]+/g, '_')}.json`
  a.click()
  setTimeout(() => URL.revokeObjectURL(a.href), 1000)
}

export async function importProfile(file) {
  const data = JSON.parse(await file.text())
  if (data?.app !== 'RollCrop' || !Array.isArray(data.fields)) throw new Error('This is not a RollCrop profile file')
  const nick = String(data.nick || 'Imported').trim().slice(0, NICK_MAX) || 'Imported'
  const p = { id: `u${Date.now().toString(36)}`, nick, created: new Date().toISOString().slice(0, 10) }
  // write the data first, then switch: fields.js reloads when the active profile changes
  setJSON(profileKey('fields', p.id), data.fields.filter((f) => Array.isArray(f?.coords) && f.coords.length >= 3))
  setJSON(profileKey('scope', p.id), data.scope === 'explore' ? 'explore' : 'mvp')
  setJSON(profileKey('onboarded', p.id), true)
  account.profiles.push(p)
  account.activeId = p.id
  saveList()
  return p
}
