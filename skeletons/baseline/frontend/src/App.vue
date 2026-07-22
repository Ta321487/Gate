<template>
  <router-view />
</template>

<script setup>
</script>

<style>
html, body, #app { height: 100%; margin: 0; }
body {
  font-family: var(--portal-font-ui);
  background: var(--portal-bg, #eef3f5);
  color: var(--portal-ink, #15202b);
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: var(--portal-font-tracking, 0.01em);
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
</style>
