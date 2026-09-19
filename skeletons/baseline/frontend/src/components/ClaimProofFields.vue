<template>
  <div class="claim-proof">
    <el-form-item label="凭证类型" required>
      <el-select v-model="form.proofType" placeholder="选择类型" style="width: 100%">
        <el-option label="特征描述" value="desc" />
        <el-option label="照片说明" value="photo" />
        <el-option label="购买凭证" value="receipt" />
      </el-select>
    </el-form-item>
    <el-form-item label="凭证内容" required>
      <el-input
        v-model="form.proofContent"
        type="textarea"
        :rows="3"
        maxlength="500"
        show-word-limit
        placeholder="如物品特征、照片链接或购买凭证说明"
      />
    </el-form-item>
  </div>
</template>

<script setup>
import { reactive } from 'vue'

const form = reactive({ proofType: 'desc', proofContent: '' })

function payload() {
  return {
    proofType: form.proofType,
    proofContent: (form.proofContent || '').trim(),
  }
}

function reset() {
  form.proofType = 'desc'
  form.proofContent = ''
}

defineExpose({ payload, reset, form })
</script>
