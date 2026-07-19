<template>
  <el-container class="layout">
    <el-header class="header">
      <strong>{{ title }}</strong>
      <div class="right">
        <el-avatar v-if="avatarUrl" :size="28" :src="avatarUrl" />
        <span>{{ displayName }} · {{ role }}</span>
        <el-button v-if="profileEditable" link type="primary" @click="$router.push('/profile')">个人资料</el-button>
        <el-button link type="primary" @click="logout">退出</el-button>
      </div>
    </el-header>
    <el-main>
      <el-card>
        <div class="toolbar">
          <el-input v-model="keyword" placeholder="搜索" clearable style="width:220px" @clear="load" @keyup.enter="load" />
          <el-button type="primary" @click="load">查询</el-button>
          <el-upload :show-file-list="false" :http-request="onUpload" accept="image/*">
            <el-button>上传图片</el-button>
          </el-upload>
          <el-date-picker v-model="date" type="date" placeholder="选择日期" />
        </div>
        <el-table :data="list" stripe style="width:100%;margin-top:12px">
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="name" label="名称" />
          <el-table-column prop="status" label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'">{{ row.status === 'active' ? '启用' : '停用' }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
        <div class="pager">
          <el-pagination
            v-model:current-page="page"
            v-model:page-size="size"
            background
            layout="total, sizes, prev, pager, next"
            :total="total"
            :page-sizes="[10, 20, 50]"
            @current-change="load"
            @size-change="load"
          />
        </div>
      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import http from '../api/http'

const router = useRouter()
const title = ref(import.meta.env.VITE_APP_TITLE || '毕设系统')
const username = ref(localStorage.getItem('username') || '')
const role = ref(localStorage.getItem('role') || '')
const nickname = ref(localStorage.getItem('nickname') || '')
const avatarUrl = ref(localStorage.getItem('avatarUrl') || '')
const profileEditable = ref(localStorage.getItem('profileEditable') !== 'false')
const displayName = computed(() => nickname.value || username.value)
const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const date = ref(null)

async function load() {
  const res = await http.get('/api/items', { params: { page: page.value, size: size.value, keyword: keyword.value || undefined } })
  list.value = res.data.list
  total.value = res.data.total
}

async function onUpload(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  ElMessage.success('已上传：' + res.data.url)
}

function logout() {
  localStorage.clear()
  router.push('/login')
}

onMounted(load)
</script>

<style scoped>
.layout { min-height: 100%; }
.header { display: flex; align-items: center; justify-content: space-between; background: #fff; border-bottom: 1px solid #ebeef5; }
.right { display: flex; gap: 12px; align-items: center; color: #606266; font-size: 13px; }
.toolbar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
