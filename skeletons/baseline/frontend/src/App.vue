<template>
  <router-view />
</template>

<script setup>
</script>

<style>
:root {
  /* 标题：衬线中文 · 正文：Plus Jakarta（英）+ Noto Sans SC（中） */
  --portal-font-display: "Noto Serif SC", "Source Han Serif SC", "Songti SC", "STSong", serif;
  --portal-font-ui: "Plus Jakarta Sans", "Noto Sans SC", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
}
html, body, #app { height: 100%; margin: 0; }
body {
  font-family: var(--portal-font-ui);
  background: var(--portal-bg, #eef3f5);
  color: var(--portal-ink, #15202b);
  font-weight: 400;
  line-height: 1.55;
  letter-spacing: 0.01em;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
  text-rendering: optimizeLegibility;
}
</style>
