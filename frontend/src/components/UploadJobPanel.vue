<template>
  <div v-if="jobs.length" class="panel mb-16">
    <div class="panel-hd">
      <h3>上传任务</h3>
      <span class="small muted">{{ hint }}</span>
    </div>
    <div class="panel-bd stack" style="gap:14px">
      <div v-for="job in jobs" :key="job.id" class="upload-job">
        <div class="row" style="justify-content:space-between;margin-bottom:6px;gap:8px">
          <div style="min-width:0">
            <div style="font-weight:600;line-height:1.35">{{ job.name }}</div>
            <div class="small muted">
              <slot name="meta" :job="job">{{ defaultMeta(job) }}</slot>
            </div>
          </div>
          <div class="row" style="gap:6px;flex-shrink:0">
            <slot name="actions" :job="job" />
          </div>
        </div>
        <slot name="progress" :job="job">
          <div class="progress">
            <i :style="{ width: (Number(job.pct) || 0) + '%', background: barColor(job) }" />
          </div>
        </slot>
        <div v-if="job.error" class="small warn" style="margin-top:6px">{{ job.error }}</div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { uploadJobBarColor } from '../utils/uploadJobUi'

const props = defineProps({
  jobs: { type: Array, default: () => [] },
  hint: { type: String, default: '' },
  /** 无 meta 插槽时：`(job) => string` */
  metaFn: { type: Function, default: null },
})

function defaultMeta(job) {
  return typeof props.metaFn === 'function' ? props.metaFn(job) : ''
}

function barColor(job) {
  return uploadJobBarColor(job)
}
</script>
