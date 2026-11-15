<script setup>
// Common layout: top menu + page title + page body (issue #38: no side bar, no global sample banner;
// every value that is still an example keeps its own dotted mark and label).
// The "overlay" slot (drawer / modal) sits above the whole screen.
import TopNav from './TopNav.vue'
import TopBar from './TopBar.vue'
import DataNotice from './DataNotice.vue'
defineProps({ active: String, crumb: String, title: String })
</script>
<template>
  <section class="screen">
    <TopNav />
    <div class="main">
      <DataNotice />
      <TopBar :crumb="crumb" :title="title"><slot name="top" /></TopBar>
      <slot />
    </div>
    <slot name="overlay" />
  </section>
</template>
