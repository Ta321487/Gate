<template>
  <div>
    <h2>鉴定签署</h2>
    <p class="lead">上传签章图并勾选同意完成签署；非 CA、非法大大等第三方电子签平台。</p>
    <el-form label-width="100px" class="form" @submit.prevent>
      <el-form-item label="签署标题" required>
        <el-input v-model="form.title" placeholder="如：实习鉴定确认" maxlength="200" />
      </el-form-item>
      <el-form-item label="关联单据">
        <el-input-number v-model="form.ticketId" :min="0" controls-position="right" placeholder="可选周报ID" />
      </el-form-item>
      <el-form-item label="签章图" required>
        <el-upload :show-file-list="false" accept="image/*" :http-request="onUpload">
          <el-button>上传图片</el-button>
        </el-upload>
        <img v-if="form.signImageUrl" :src="form.signImageUrl" class="preview" alt="签章预览" />
      </el-form-item>
      <el-form-item label="说明">
        <el-input v-model="form.remark" type="textarea" :rows="2" maxlength="255" />
      </el-form-item>
      <el-form-item>
        <el-checkbox v-model="form.agreed">我已阅读并同意本次签署内容（签署留痕）</el-checkbox>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" :loading="saving" @click="submit">提交签署</el-button>
      </el-form-item>
    </el-form>

    <h3>我的签署记录</h3>
    <el-table :data="list" stripe>
      <el-table-column prop="signedAt" label="时间" width="180" />
      <el-table-column prop="title" label="标题" min-width="140" />
      <el-table-column prop="ticketId" label="单据ID" width="90" />
      <el-table-column label="签章" width="100">
        <template #default="{ row }">
          <el-image v-if="row.signImageUrl" :src="row.signImageUrl" style="width: 48px; height: 48px" fit="contain" />
        </template>
      </el-table-column>
      <el-table-column prop="agreed" label="同意" width="70">
        <template #default="{ row }">{{ row.agreed ? '是' : '否' }}</template>
      </el-table-column>
    </el-table>
    <el-pagination
      v-if="total > size"
      class="pager"
      layout="prev, pager, next"
      :total="total"
      :page-size="size"
      v-model:current-page="page"
      @current-change="load"
    />
  </div>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = 10
const saving = ref(false)
const form = reactive({
  title: '实习鉴定确认',
  ticketId: 0,
  signImageUrl: '',
  remark: '',
  agreed: false,
})

async function load() {
  const res = await http.get('/api/e-sign/mine', { params: { page: page.value, size } })
  const data = res.data?.data || res.data || {}
  list.value = data.list || []
  total.value = data.total || 0
}

async function onUpload(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  const url = res.data?.data?.url || res.data?.url
  if (!url) throw new Error('上传失败')
  form.signImageUrl = url
  ElMessage.success('已上传')
}

async function submit() {
  saving.value = true
  try {
    await http.post('/api/e-sign/submit', {
      title: form.title,
      ticketId: form.ticketId || undefined,
      signImageUrl: form.signImageUrl,
      remark: form.remark,
      agreed: form.agreed,
    })
    ElMessage.success('签署已留痕')
    form.signImageUrl = ''
    form.agreed = false
    form.remark = ''
    page.value = 1
    await load()
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e?.message || '提交失败')
  } finally {
    saving.value = false
  }
}

watch(page, load)
onMounted(load)
</script>

<style scoped>
.lead { color: var(--el-text-color-secondary); margin: 0.25rem 0 1rem; }
.form { max-width: 520px; margin-bottom: 1.5rem; }
.preview { display: block; margin-top: 0.5rem; max-height: 96px; border: 1px solid var(--el-border-color); }
.pager { margin-top: 1rem; }
</style>
