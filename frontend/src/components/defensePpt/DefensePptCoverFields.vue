<template>
  <div>
    <div class="parse-sec-hd">封面信息（全部必填 · 写入 cover 页）</div>
    <div class="grid-2" style="gap:12px">
      <div>
        <label class="field-label">学校 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.school" placeholder="例：XX 大学" @update:value="emitChange" />
      </div>
      <div>
        <label class="field-label">学院 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.college" placeholder="例：计算机学院" @update:value="emitChange" />
      </div>
      <div>
        <label class="field-label">班级 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.class_name" placeholder="例：软件 2201" @update:value="emitChange" />
      </div>
      <div>
        <label class="field-label">姓名 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.student_name" placeholder="学生姓名" @update:value="emitChange" />
      </div>
      <div>
        <label class="field-label">学号 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.student_id" placeholder="学号" @update:value="emitChange" />
      </div>
      <div>
        <label class="field-label">指导教师 <span class="req">*</span></label>
        <n-input v-model:value="modelValue.advisor" placeholder="导师姓名" @update:value="emitChange" />
      </div>
      <div style="grid-column:1 / -1">
        <DefensePptBadgeSlot
          :model-value="modelValue.badge_data_url"
          @update:model-value="onBadge"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import DefensePptBadgeSlot from './DefensePptBadgeSlot.vue'

const props = defineProps({
  modelValue: { type: Object, required: true },
})
const emit = defineEmits(['change'])

function emitChange() {
  emit('change')
}

function onBadge(url) {
  props.modelValue.badge_data_url = url
  emit('change')
}
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 13px;
  margin-bottom: 6px;
  color: var(--ink-2);
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
}
@media (max-width: 700px) {
  .grid-2 { grid-template-columns: 1fr; }
}
</style>
