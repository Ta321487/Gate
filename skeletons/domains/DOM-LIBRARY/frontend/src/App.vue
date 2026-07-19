<template>
  <router-view />
</template>

<script setup>
</script>

<style>
:root {
  --portal-font-display: "Noto Serif SC", "Songti SC", "STSong", serif;
  --portal-font-ui: "DM Sans", "PingFang SC", "Noto Sans SC", "Microsoft YaHei", sans-serif;
}
html, body, #app { height: 100%; margin: 0; }
body {
  font-family: var(--portal-font-ui);
  background: var(--portal-bg, #eef3f5);
  color: var(--portal-ink, #15202b);
  -webkit-font-smoothing: antialiased;
}
</style>
