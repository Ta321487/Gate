<template>
  <div class="ppt-stage">
    <p class="small muted mb-12">
      答辩 PPT 在论文材料之后单独开跑：先填封面信息生成，再预览改稿与导出（不进学生 ZIP）。
    </p>
    <DefensePptLaunchPanel />
    <div class="mt-16">
      <DefensePptComparePane />
    </div>
  </div>
</template>

<script setup>
import DefensePptLaunchPanel from '../../components/defensePpt/DefensePptLaunchPanel.vue'
import DefensePptComparePane from '../../components/defensePpt/DefensePptComparePane.vue'
</script>

<style scoped>
.mb-12 {
  margin-bottom: 12px;
}
.mt-16 {
  margin-top: 16px;
}
</style>
