<script setup>
// Common layout: SideNav + SampleDataBanner + TopBar + page body.
// The "overlay" slot (drawer / modal) sits above the whole screen.
import SideNav from './SideNav.vue'
import SampleDataBanner from './SampleDataBanner.vue'
import TopBar from './TopBar.vue'
defineProps({ active: String, crumb: String, title: String })
</script>
<template>
  <section class="screen">
    <SideNav :active="active" />
    <div class="main">
      <SampleDataBanner />
      <TopBar :crumb="crumb" :title="title"><slot name="top" /></TopBar>
      <slot />
    </div>
    <slot name="overlay" />
  </section>
</template>
