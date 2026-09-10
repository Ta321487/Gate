<template>
  <div
    class="content-loading"
    :class="{ 'is-compact': compact }"
    :aria-busy="true"
    :aria-label="label"
  >
    <div class="skel-stack content-loading-bars">
      <div
        v-for="i in rows"
        :key="i"
        class="skel"
        :class="block ? 'skel-block' : 'skel-row-bar'"
      />
    </div>
    <p v-if="showLabel" class="small muted content-loading-label">{{ label }}</p>
  </div>
</template>

<script setup>
defineProps({
  /** 骨架条数 */
  rows: { type: Number, default: 3 },
  /** 无障碍与可选文案 */
  label: { type: String, default: '加载中' },
  /** 是否显示文案（默认隐藏，靠骨架表达） */
  showLabel: { type: Boolean, default: false },
  /** 更矮间距，适合面板内嵌 */
  compact: { type: Boolean, default: false },
  /** 用块状骨架（图/画布区） */
  block: { type: Boolean, default: false },
})
</script>

<style scoped>
.content-loading {
  padding: 12px 0;
  animation: status-in 0.25s ease-out;
}
.content-loading.is-compact {
  padding: 8px 0;
}
.content-loading-bars {
  gap: 10px;
}
.content-loading.is-compact .content-loading-bars {
  gap: 8px;
}
.content-loading-label {
  margin: 10px 0 0;
}
</style>
