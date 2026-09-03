<template>
  <div class="page">
    <section class="hero card">
      <h1>{{ pageTitle }}</h1>
      <p>{{ pageLead }}</p>
      <p class="hint">日常对话请用右下角悬浮助手；本页可一键打开弹窗，并说明使用方式。</p>
      <div class="actions">
        <el-button type="primary" @click="openFloat">打开 AI 助手</el-button>
      </div>
    </section>
    <section class="card tips">
      <h2>能做什么</h2>
      <ul>
        <li>文字问答（知识库 + 只读查询本系统商品/订单/办理进度等）</li>
        <li>热门问答、满意度反馈、浏览器语音播报</li>
        <li>上传图片按品类匹配相关知识</li>
      </ul>
    </section>
  </div>
</template>

<script setup>
/** 菜单落地页：说明 + 打开全局悬浮弹窗（主交互在 AiAssistantFloat） */
import { computed, onMounted } from 'vue'
import { schemaLabels } from '../utils/domainSchema.js'

const OPEN_EVENT = 'thesis-open-ai-assistant'
const labels = computed(() => schemaLabels())
const pageTitle = computed(() => labels.value.aiAssistantPageTitle || 'AI智能助手')
const pageLead = computed(
  () =>
    labels.value.aiAssistantPageLead ||
    '对话咨询、知识问答；可上传图片按品类匹配知识；支持语音播报与满意度反馈。',
)

function openFloat() {
  window.dispatchEvent(new CustomEvent(OPEN_EVENT))
}

onMounted(() => {
  openFloat()
})
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.card {
  background: var(--portal-surface, #fff);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e2e8f0);
  border-radius: var(--portal-radius, 12px);
  padding: 18px 20px;
}
.hero h1 {
  margin: 0 0 8px;
  font-family: var(--portal-font-display);
  font-size: 26px;
  letter-spacing: -0.03em;
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #64748b);
  font-size: 14px;
  line-height: 1.55;
  max-width: 42em;
}
.hint {
  margin-top: 8px !important;
  font-size: 13px !important;
}
.actions {
  margin-top: 14px;
}
.tips h2 {
  margin: 0 0 10px;
  font-size: 15px;
}
.tips ul {
  margin: 0;
  padding-left: 1.2em;
  color: var(--portal-muted, #64748b);
  font-size: 14px;
  line-height: 1.7;
}
</style>
