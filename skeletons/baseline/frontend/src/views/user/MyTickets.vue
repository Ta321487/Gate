<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>{{ plural }}</h1>
          <p>提交申请并查看受理进度。</p>
        </div>
        <div class="tools">
          <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
            <el-option v-for="(lab, key) in states" :key="key" :label="lab" :value="key" />
          </el-select>
          <el-button v-if="!archiveMode" type="primary" @click="openApply">{{ verbs.apply || '提交' }}</el-button>
          <el-button v-else type="primary" @click="$router.push('/archive')">去检索申请</el-button>
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
    </section>

    <div class="list">
      <article v-for="row in list" :key="row.id" class="card">
        <div class="mark">{{ (row.title || '?').slice(0, 1) }}</div>
        <div class="meta">
          <h3>{{ row.title || ('单号 ' + row.id) }}</h3>
          <p class="sub">
            单号 {{ row.id }} · 申请于 {{ row.applyAt }}
            <template v-if="row.typeName"> · {{ row.typeName }}</template>
            <template v-if="row.location"> · {{ row.location }}</template>
          </p>
          <div v-if="row.remark" class="tip">
            <template v-if="row.status === 'rejected'">驳回原因：</template>
            <template v-else-if="richRemark">内容：</template>
            <template v-else-if="row.status === 'approved' || row.status === 'returned' || row.status === 'overdue'">说明：</template>
            <RichTextView v-if="richRemark" :html="row.remark" compact />
            <template v-else>{{ row.remark }}</template>
          </div>
          <div class="row">
            <el-tag size="small" :type="tagType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag>
            <el-button
              v-if="row.status === 'approved' || row.status === 'overdue'"
              type="primary"
              size="small"
              @click="finish(row)"
            >{{ verbs.return || '完成' }}</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">
      {{ archiveMode ? '还没有记录，请先在检索页申请。' : '还没有记录，点击右上角提交。' }}
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, prev, pager, next"
        :total="total"
        @current-change="load"
      />
    </div>

    <el-dialog v-model="visible" :title="verbs.apply || '提交'" width="520px">
      <el-form :model="form" label-width="88px" require-asterisk-position="right">
        <el-form-item label="标题" required>
          <el-input v-model="form.title" maxlength="80" placeholder="简要描述问题" />
        </el-form-item>
        <template v-if="lookup.enabled">
          <el-form-item :label="lookup.typeLabel" required>
            <el-select v-model="form.typeId" filterable placeholder="请选择" style="width:100%">
              <el-option v-for="t in types" :key="t.id" :label="t.name" :value="t.id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="lookup.siteLabel" required>
            <el-select v-model="form.siteId" filterable placeholder="请选择" style="width:100%" @change="onSiteChange">
              <el-option v-for="s in sites" :key="s.id" :label="s.name" :value="s.id" />
            </el-select>
          </el-form-item>
          <el-form-item :label="lookup.unitLabel" required>
            <el-select v-model="form.roomId" filterable placeholder="请先选上级" style="width:100%" :disabled="!form.siteId">
              <el-option v-for="u in units" :key="u.id" :label="u.code || u.name" :value="u.id" />
            </el-select>
          </el-form-item>
        </template>
        <el-form-item v-else label="地点" required>
          <el-input v-model="form.location" maxlength="64" placeholder="如 3 栋 201" />
        </el-form-item>
        <el-form-item label="说明">
          <el-input v-model="form.remark" type="textarea" :rows="3" maxlength="400" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="submit">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import RichTextView from '../../components/RichTextView.vue'
import { getSchema, ticketCopy } from '../../utils/domainSchema.js'

const ticket = ticketCopy()
const verbs = computed(() => ticket.verbs || {})
const states = computed(() => ticket.states || {
  pending: '待受理', approved: '处理中', rejected: '已驳回', returned: '已完成',
})
const plural = computed(() => ticket.labelPlural || ticket.label || '我的单据')
const archiveMode = computed(() => (getSchema().capabilities || []).includes('archive'))
const richRemark = computed(() => !!ticket.richRemark)

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)
const visible = ref(false)
const lookup = reactive({
  enabled: false,
  siteLabel: '楼栋',
  unitLabel: '房间',
  typeLabel: '类型',
})
const sites = ref([])
const units = ref([])
const types = ref([])
const form = reactive({
  title: '',
  location: '',
  remark: '',
  typeId: null,
  siteId: null,
  roomId: null,
})

function statusText(s) { return states.value[s] || s }
function tagType(s) {
  return ({ pending: 'warning', approved: 'success', rejected: 'danger', returned: 'info', overdue: 'danger' })[s] || 'info'
}

async function loadLookup() {
  try {
    const meta = await http.get('/api/lookups/meta')
    const m = meta.data || meta
    Object.assign(lookup, {
      enabled: !!m.enabled,
      siteLabel: m.siteLabel || '楼栋',
      unitLabel: m.unitLabel || '房间',
      typeLabel: m.typeLabel || '类型',
    })
    if (!lookup.enabled) return
    const [sRes, tRes] = await Promise.all([
      http.get('/api/lookups/sites'),
      http.get('/api/lookups/types'),
    ])
    sites.value = sRes.data || sRes || []
    types.value = tRes.data || tRes || []
  } catch {
    lookup.enabled = false
  }
}

async function onSiteChange() {
  form.roomId = null
  units.value = []
  if (!form.siteId) return
  const res = await http.get('/api/lookups/units', { params: { siteId: form.siteId } })
  units.value = res.data || res || []
}

async function load() {
  const res = await http.get('/api/tickets', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

function openApply() {
  Object.assign(form, {
    title: '', location: '', remark: '', typeId: null, siteId: null, roomId: null,
  })
  units.value = []
  visible.value = true
}

async function submit() {
  if (!form.title.trim()) {
    ElMessage.warning('请填写标题')
    return
  }
  if (lookup.enabled) {
    if (!form.typeId) {
      ElMessage.warning(`请选择${lookup.typeLabel}`)
      return
    }
    if (!form.siteId) {
      ElMessage.warning(`请选择${lookup.siteLabel}`)
      return
    }
    if (!form.roomId) {
      ElMessage.warning(`请选择${lookup.unitLabel}`)
      return
    }
  } else if (!form.location.trim()) {
    ElMessage.warning('请填写地点')
    return
  }
  await http.post('/api/tickets/apply', {
    title: form.title,
    remark: form.remark,
    location: form.location,
    typeId: form.typeId,
    roomId: form.roomId,
  })
  ElMessage.success('已提交')
  visible.value = false
  load()
}

async function finish(row) {
  await ElMessageBox.confirm(`确认${verbs.value.return || '完结'}「${row.title}」？`, '确认')
  await http.post(`/api/tickets/${row.id}/complete`)
  ElMessage.success('已更新')
  load()
}

onMounted(async () => {
  await loadLookup()
  await load()
})
</script>

<style scoped>
.hero { margin-bottom: 18px; }
.hero-row { display: flex; justify-content: space-between; gap: 16px; align-items: flex-start; flex-wrap: wrap; }
.hero h1 { margin: 0 0 6px; font-size: 22px; }
.hero p { margin: 0; color: #64748b; font-size: 13px; }
.tools { display: flex; gap: 8px; flex-wrap: wrap; }
.list { display: flex; flex-direction: column; gap: 12px; }
.card {
  display: flex; gap: 14px; padding: 16px; background: #fff;
  border: 1px solid #e2e8f0; border-radius: 12px;
}
.mark {
  width: 44px; height: 44px; border-radius: 10px; flex-shrink: 0;
  display: grid; place-items: center; font-weight: 700; color: #0369a1;
  background: #e0f2fe;
}
.meta { flex: 1; min-width: 0; }
.meta h3 { margin: 0 0 4px; font-size: 16px; }
.sub { margin: 0; color: #64748b; font-size: 12px; }
.tip { margin: 6px 0 0; color: #475569; font-size: 13px; }
.row { margin-top: 10px; display: flex; gap: 10px; align-items: center; }
.empty { text-align: center; color: #94a3b8; padding: 40px 0; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
</style>
