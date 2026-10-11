<template>
  <div class="thanks card">
    <h1>{{ title }}</h1>
    <p class="lead">{{ lead }}</p>
    <el-button type="primary" @click="$router.push('/survey/mine')">{{ backLabel }}</el-button>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { getSchema } from '../utils/domainSchema.js'

const schema = computed(() => getSchema() || {})
const labels = computed(() => schema.value.labels || {})
const title = computed(() => labels.value.surveyThanksTitle || '感谢填写')
const lead = computed(
  () => labels.value.surveyThanksLead || '您的答卷已提交，感谢参与本次调查。',
)
const backLabel = computed(() => labels.value.surveyThanksBackLabel || '查看我的答卷')
</script>

<style scoped>
.thanks { max-width: 520px; margin: 2rem auto; padding: 2rem; text-align: center; }
.lead { color: var(--el-text-color-secondary); margin: 1rem 0 1.5rem; line-height: 1.6; }
</style>
