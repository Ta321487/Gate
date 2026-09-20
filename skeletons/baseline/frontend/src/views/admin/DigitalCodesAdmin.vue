<template>
  <div>
    <p class="hint">码池里的激活码或链接会在付款后发给买家。用完后系统会再生成。</p>
    <div class="toolbar">
      <el-button type="primary" @click="openCreate">添加</el-button>
      <el-button @click="load">刷新</el-button>
    </div>
    <el-table :data="list" stripe>
      <el-table-column prop="itemId" label="商品" width="80" />
      <el-table-column prop="kind" label="类型" width="90" />
      <el-table-column prop="codeValue" label="激活码" min-width="140" />
      <el-table-column prop="linkUrl" label="链接" min-width="160" />
      <el-table-column label="启用" width="80">
        <template #default="{ row }">{{ row.enabled ? '是' : '否' }}</template>
      </el-table-column>
    </el-table>
    <el-dialog v-model="visible" title="数字码" width="440px">
      <el-form label-width="80px">
        <el-form-item label="商品编号">
          <el-input-number v-model="form.itemId" :min="1" />
        </el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.kind">
            <el-option label="激活码" value="code" />
            <el-option label="下载链接" value="link" />
            <el-option label="课程权限" value="permit" />
          </el-select>
        </el-form-item>
        <el-form-item label="激活码">
          <el-input v-model="form.codeValue" maxlength="128" />
        </el-form-item>
        <el-form-item label="链接">
          <el-input v-model="form.linkUrl" maxlength="255" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.enabled" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const visible = ref(false)
const form = reactive({ itemId: 1, kind: 'code', codeValue: '', linkUrl: '', enabled: true })

async function load() {
  const res = await http.get('/api/digital/codes')
  list.value = res.data || []
}

function openCreate() {
  Object.assign(form, { itemId: 1, kind: 'code', codeValue: '', linkUrl: '', enabled: true })
  visible.value = true
}

async function save() {
  await http.post('/api/digital/codes', { ...form })
  ElMessage.success('已保存')
  visible.value = false
  await load()
}

onMounted(load)
</script>

<style scoped>
.hint, .empty { color: var(--el-text-color-secondary); }
.toolbar { margin-bottom: 12px; }
</style>
