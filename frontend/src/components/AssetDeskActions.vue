<template>
  <div class="row asset-desk-actions" style="gap:8px;flex-wrap:wrap">
    <n-button
      size="small"
      :loading="gapLoading"
      :disabled="checkDisabled"
      @click="$emit('check')"
    >
      {{ checkLabel }}
    </n-button>
    <slot name="extra" />
    <n-button
      size="small"
      :loading="migrating"
      title="仅追加缺失项，不覆盖已有记录"
      @click="$emit('migrate')"
    >
      {{ migrateLabel }}
    </n-button>
    <n-button size="small" type="primary" @click="$emit('create')">
      {{ createLabel }}
    </n-button>
  </div>
</template>

<script setup>
defineProps({
  gapLoading: { type: Boolean, default: false },
  migrating: { type: Boolean, default: false },
  checkDisabled: { type: Boolean, default: false },
  checkLabel: { type: String, default: '检查待补' },
  migrateLabel: { type: String, default: '导入种子' },
  createLabel: { type: String, default: '登记' },
})

defineEmits(['check', 'migrate', 'create'])
</script>
