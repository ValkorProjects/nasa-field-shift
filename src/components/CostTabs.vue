<script setup>
defineProps({ active: { type: String, required: true } })
const tabs = [
  { id: 'money', label: 'Your money', to: '/field/1/costs' },
  { id: 'big', label: 'Big picture: food prices', to: '/field/1/costs/big-picture' }
]
</script>
<template>
  <nav class="tabs" aria-label="Costs">
    <router-link v-for="t in tabs" :key="t.id" :to="t.to" :class="['tab', { on: t.id === active }]" :aria-current="t.id === active ? 'page' : null">{{ t.label }}</router-link>
  </nav>
</template>
