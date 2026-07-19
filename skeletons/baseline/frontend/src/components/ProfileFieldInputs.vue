<template>
  <template v-for="f in visibleFields" :key="f.key">
    <label v-if="f.storage === 'phone'" class="field" :class="{ wide: isWide(f) }">
      <span class="lab">{{ f.label }}<i v-if="isReq(f)" class="req" aria-hidden="true">*</i></span>
      <el-input
        :model-value="phone"
        :maxlength="f.maxLength || 20"
        :placeholder="f.placeholder || '手机号'"
        @update:model-value="$emit('update:phone', $event)"
      />
    </label>
    <label v-else class="field" :class="{ wide: isWide(f) }">
      <span class="lab">{{ f.label }}<i v-if="isReq(f)" class="req" aria-hidden="true">*</i></span>
      <el-select
        v-if="f.type === 'select'"
        :model-value="extras[f.key] || ''"
        clearable
        :placeholder="f.placeholder || `请选择${f.label}`"
        style="width: 100%"
        @update:model-value="(v) => patch(f.key, v)"
      >
        <el-option v-for="opt in f.options || []" :key="opt" :label="opt" :value="opt" />
      </el-select>
      <el-input
        v-else
        :model-value="extras[f.key] || ''"
        :maxlength="f.maxLength || 64"
        :placeholder="f.placeholder || f.label"
        @update:model-value="(v) => patch(f.key, v)"
      />
    </label>
  </template>
</template>

<script setup>
import { computed } from 'vue'
import { isProfileFieldRequired, isProfileFieldVisible } from '../utils/profileValidate.js'

const WIDE = new Set([
  'officeOrDorm', 'campusAddress', 'allergyNote', 'defaultRemark',
  'skinOrPrefer', 'usualPlace', 'labOrOffice', 'officeLoc', 'workUnit', 'orgName', 'orgOrClub',
  'campusAddress', 'offCampusAddress',
])

const props = defineProps({
  fields: { type: Array, default: () => [] },
  phone: { type: String, default: '' },
  extras: { type: Object, default: () => ({}) },
})
const emit = defineEmits(['update:phone', 'update:extras'])

const visibleFields = computed(() =>
  (props.fields || []).filter((f) => isProfileFieldVisible(f, props.extras)),
)

function isWide(f) {
  return !!(f && (WIDE.has(f.key) || (f.maxLength && f.maxLength >= 100)))
}

function isReq(f) {
  return isProfileFieldRequired(f, props.extras)
}

function patch(key, val) {
  const next = { ...props.extras, [key]: val ?? '' }
  // 切换身份等驱动字段时，清掉当前不可见的条件项，避免脏数据提交
  if (key === 'identityType' || key === 'readerType' || key === 'ownerType'
    || key === 'deliveryType' || key === 'pickupType') {
    for (const f of props.fields || []) {
      if (f.key === key || !f.visibleWhen) continue
      if (!isProfileFieldVisible(f, next)) next[f.key] = ''
    }
  }
  emit('update:extras', next)
}
</script>

<style scoped>
.field { display: flex; flex-direction: column; gap: 4px; min-width: 0; }
.lab {
  font-size: 13px;
  font-weight: 500;
  color: var(--portal-ink, #15202b);
}
.req {
  color: var(--el-color-danger, #f56c6c);
  margin-left: 2px;
  font-style: normal;
  font-weight: 600;
}
</style>
