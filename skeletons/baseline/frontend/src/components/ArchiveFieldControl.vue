<template>
  <el-switch
    v-if="widget === 'switch'"
    :model-value="switchOn"
    inline-prompt
    active-text="开"
    inactive-text="关"
    @update:model-value="onSwitch"
  />
  <el-select
    v-else-if="widget === 'select'"
    :model-value="modelValue"
    clearable
    :placeholder="placeholder || `请选择${label}`"
    style="width:100%"
    @update:model-value="emit('update:modelValue', $event)"
  >
    <el-option v-for="opt in options" :key="opt" :label="opt" :value="opt" />
  </el-select>
  <el-date-picker
    v-else-if="widget === 'datetime'"
    :model-value="modelValue"
    v-bind="dateTimePickerProps(field)"
    style="width:100%"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <el-input-number
    v-else-if="widget === 'money'"
    :model-value="numValue"
    :min="0"
    :precision="2"
    :step="1"
    controls-position="right"
    style="width:100%"
    :value-on-clear="null"
    @update:model-value="onMoney"
  />
  <el-input-number
    v-else-if="widget === 'number'"
    :model-value="numValue"
    :min="0"
    :step="1"
    controls-position="right"
    style="width:100%"
    @update:model-value="emit('update:modelValue', $event ?? 0)"
  />
  <el-input
    v-else-if="widget === 'url'"
    :model-value="modelValue"
    type="url"
    placeholder="https://"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <el-input
    v-else-if="widget === 'textarea'"
    :model-value="modelValue"
    type="textarea"
    :rows="3"
    :placeholder="placeholder || label"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <RichTextEditor
    v-else-if="widget === 'richtext'"
    :model-value="modelValue"
    :placeholder="placeholder || `请输入${label}`"
    @update:model-value="emit('update:modelValue', $event)"
  />
  <el-input
    v-else
    :model-value="modelValue"
    :placeholder="placeholder || label"
    @update:model-value="emit('update:modelValue', $event)"
  />
</template>

<script setup>
import { computed } from 'vue'
import RichTextEditor from './RichTextEditor.vue'
import { dateTimePickerProps } from '../utils/dateTimeField.js'
import {
  archiveFieldWidget,
  archiveSwitchOn,
  archiveSwitchValue,
} from '../utils/archiveFieldWidget.js'

const props = defineProps({
  field: { type: Object, required: true },
  modelValue: { default: '' },
  stockAsToggle: { type: Boolean, default: false },
  bodyField: { type: String, default: '' },
  placeholder: { type: String, default: '' },
})
const emit = defineEmits(['update:modelValue'])

const widget = computed(() =>
  archiveFieldWidget(props.field, {
    stockAsToggle: props.stockAsToggle,
    bodyField: props.bodyField,
  }),
)
const label = computed(() => props.field?.label || props.field?.key || '')
const options = computed(() => {
  const raw = props.field?.options
  if (!Array.isArray(raw)) return []
  return raw.map((o) => (typeof o === 'object' && o != null ? (o.label ?? o.value) : o)).filter((x) => x != null && x !== '')
})
const switchOn = computed(() => archiveSwitchOn(props.modelValue))
const numValue = computed(() => {
  if (props.modelValue == null || props.modelValue === '') return null
  const n = Number(props.modelValue)
  return Number.isFinite(n) ? n : null
})

function onSwitch(v) {
  // stock / boolean / number 统一存 0|1，后端与库存列兼容
  emit('update:modelValue', archiveSwitchValue(!!v, { asNumber: true }))
}

function onMoney(v) {
  if (v == null || v === '') {
    emit('update:modelValue', '')
    return
  }
  emit('update:modelValue', String(v))
}
</script>
