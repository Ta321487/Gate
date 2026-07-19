<template>
  <div class="skel-page" :aria-busy="true" aria-label="加载中">
    <div v-if="variant === 'detail'" class="skel-stack">
      <div class="skel skel-back" />
      <div class="skel-head">
        <div class="skel-stack" style="flex:1">
          <div class="skel skel-title" />
          <div class="skel skel-line short" />
        </div>
        <div class="skel-row">
          <div class="skel skel-btn" />
          <div class="skel skel-btn" />
        </div>
      </div>
      <div class="skel skel-tabs" />
      <div class="panel skel-panel">
        <div class="panel-hd"><div class="skel skel-hd" /></div>
        <div class="panel-bd skel-stack">
          <div class="skel skel-line" />
          <div class="skel skel-line" />
          <div class="skel skel-line med" />
          <div class="skel skel-block" />
        </div>
      </div>
    </div>

    <div v-else-if="variant === 'dashboard'" class="skel-stack">
      <div class="skel skel-title" />
      <div class="skel skel-line short" />
      <div class="skel-stats">
        <div v-for="i in 4" :key="i" class="stat skel-stat">
          <div class="skel skel-line tiny" />
          <div class="skel skel-value" />
          <div class="skel skel-line tiny" />
        </div>
      </div>
      <div class="panel skel-panel">
        <div class="panel-hd"><div class="skel skel-hd" /></div>
        <div class="panel-bd skel-stack">
          <div v-for="i in rows" :key="i" class="skel skel-row-bar" />
        </div>
      </div>
    </div>

    <div v-else class="skel-stack">
      <div class="skel skel-title" />
      <div class="skel skel-line short" />
      <div class="panel skel-panel">
        <div class="panel-hd"><div class="skel skel-hd" /></div>
        <div class="panel-bd skel-stack">
          <div v-for="i in rows" :key="i" class="skel skel-row-bar" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
defineProps({
  /** detail | dashboard | list */
  variant: { type: String, default: 'list' },
  rows: { type: Number, default: 5 },
})
</script>
