<template>
  <div>
    <p class="lead">{{ pageLead }}</p>
    <p v-if="!posts.length" class="lead">{{ emptyHint }}</p>
    <template v-else>
      <el-form label-position="top" class="form">
        <el-form-item :label="postLabel">
          <el-select v-model="postId" style="width: 280px" @change="loadKeys">
            <el-option v-for="p in posts" :key="p.id" :label="p.label" :value="p.id" />
          </el-select>
        </el-form-item>
        <el-checkbox-group v-model="checked">
          <el-checkbox v-for="m in menus" :key="m.key" :label="m.key">{{ m.label }}</el-checkbox>
        </el-checkbox-group>
        <div class="actions">
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
        </div>
      </el-form>
    </template>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import http from '../../api/http'
import { getSchema, isSuperOnlyMenu, schemaMenus } from '../../utils/domainSchema.js'
import { clerkPosts } from '../../utils/staffPosts.js'

const labels = computed(() => getSchema()?.labels || {})
const pageLead = computed(
  () => labels.value.roleMenusLead || '在岗位已有菜单上勾选增减；全部取消则恢复原岗位菜单。',
)
const emptyHint = computed(() => labels.value.roleMenusEmptyHint || '当前没有可配置的办理岗')
const postLabel = computed(() => labels.value.roleMenusPostLabel || '岗位')

const posts = computed(() => clerkPosts())
const postId = ref('')
const checked = ref([])
const saving = ref(false)

const menus = computed(() =>
  schemaMenus('admin').filter((m) => m && m.key && m.key !== 'profile' && !isSuperOnlyMenu(m)),
)

function packKeys(id) {
  const post = posts.value.find((p) => p.id === id)
  const packMenus = getSchema()?.staffPackMenus || {}
  const keys = new Set()
  for (const pk of post?.packs || []) {
    for (const k of packMenus[pk] || []) keys.add(k)
  }
  if (!keys.size) keys.add('dashboard')
  return [...keys]
}

async function loadKeys() {
  if (!postId.value) return
  const res = await http.get('/api/admin/role-menus', { params: { staffPost: postId.value } })
  const d = res.data || {}
  checked.value = d.usePacks ? packKeys(postId.value) : (d.keys || [])
}

async function save() {
  saving.value = true
  try {
    await http.put('/api/admin/role-menus', { staffPost: postId.value, keys: checked.value })
    ElMessage.success(checked.value.length ? '已保存' : '已恢复为原岗位菜单')
    loadKeys()
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  postId.value = posts.value[0]?.id || ''
  if (postId.value) loadKeys()
})
</script>

<style scoped>
.lead { margin: 0 0 12px; color: var(--el-text-color-secondary); font-size: 13px; }
.form { max-width: 720px; }
.actions { margin-top: 16px; }
.el-checkbox { margin: 0 16px 10px 0; }
</style>
