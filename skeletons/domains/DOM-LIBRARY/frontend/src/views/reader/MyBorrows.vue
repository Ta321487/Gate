<template>
  <div>
    <section class="hero">
      <div class="hero-row">
        <div>
          <h1>我的借阅</h1>
          <p>查看申请进度、应还日期与催还提醒；逾期请尽快归还。</p>
        </div>
        <div class="tools">
          <el-select v-model="status" clearable placeholder="全部状态" style="width:140px" @change="load">
            <el-option label="待审核" value="pending" />
            <el-option label="已借出" value="approved" />
            <el-option label="已驳回" value="rejected" />
            <el-option label="已归还" value="returned" />
            <el-option label="逾期" value="overdue" />
          </el-select>
          <el-button @click="load">刷新</el-button>
        </div>
      </div>
    </section>

    <div class="list">
      <article
        v-for="row in list"
        :key="row.id"
        class="card"
        :class="{ warn: row.status === 'overdue' || row.remindedAt }"
      >
        <div class="mark">{{ (row.bookTitle || '?').slice(0, 1) }}</div>
        <div class="meta">
          <h3>{{ row.bookTitle }}</h3>
          <p class="sub">
            单号 {{ row.id }} · 申请于 {{ row.applyAt }}
            <template v-if="row.dueAt"> · 应还 {{ row.dueAt }}</template>
            <template v-if="row.fineYuan > 0"> · 罚款 {{ row.fineYuan }} 元</template>
          </p>
          <p v-if="row.status === 'rejected' && row.remark" class="tip">驳回原因：{{ row.remark }}</p>
          <p v-if="row.remindMsg" class="tip">{{ row.remindMsg }}</p>
          <div class="row">
            <el-tag size="small" :type="tagType(row.status)" effect="plain">{{ statusText(row.status) }}</el-tag>
            <el-button
              v-if="row.status === 'approved' || row.status === 'overdue'"
              type="primary"
              size="small"
              @click="ret(row)"
            >归还</el-button>
          </div>
        </div>
      </article>
    </div>

    <div v-if="!list.length" class="empty">还没有借阅记录。</div>
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
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const status = ref(null)

const map = { pending: '待审核', approved: '已借出', rejected: '已驳回', returned: '已归还', overdue: '逾期' }
function statusText(s) { return map[s] || s }
function tagType(s) {
  return ({ pending: 'warning', approved: 'success', rejected: 'danger', returned: 'info', overdue: 'danger' })[s] || 'info'
}

async function load() {
  const res = await http.get('/api/borrows', {
    params: { page: page.value, size: size.value, status: status.value || undefined },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function ret(row) {
  const tip = row.fineYuan > 0
    ? `确认归还《${row.bookTitle}》？逾期预估罚款 ${row.fineYuan} 元。`
    : `确认归还《${row.bookTitle}》？`
  await ElMessageBox.confirm(tip, '归还')
  await http.post(`/api/borrows/${row.id}/return`)
  ElMessage.success('已归还')
  load()
}

onMounted(load)
</script>

<style scoped>
.hero {
  margin-bottom: 22px;
  padding: 8px 0 4px;
}
.hero-row {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 16px;
  flex-wrap: wrap;
}
.hero h1 {
  margin: 0 0 8px;
  font-size: 28px;
  letter-spacing: -0.03em;
  color: var(--portal-ink, #15202b);
}
.hero p {
  margin: 0;
  color: var(--portal-muted, #6b7c8a);
  font-size: 14px;
}
.tools { display: flex; gap: 8px; flex-wrap: wrap; }
.list { display: flex; flex-direction: column; gap: 12px; }
.card {
  display: flex;
  gap: 14px;
  background: var(--portal-surface, #fff);
  border: 1px solid var(--portal-line, #dfe7ec);
  border-radius: 10px;
  padding: 14px 16px;
  transition: border-color 0.15s, box-shadow 0.15s;
}
.card.warn {
  border-color: color-mix(in srgb, #c24141 45%, var(--portal-line, #dfe7ec));
  background: color-mix(in srgb, #fff5f4 70%, var(--portal-surface, #fff));
}
.mark {
  width: 48px;
  height: 64px;
  border-radius: 6px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  background: var(--portal-cover, linear-gradient(160deg, #0b6e75, #08545a));
  color: #fff;
  font-weight: 700;
  font-size: 18px;
}
.meta {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.meta h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--portal-ink, #15202b);
}
.sub {
  margin: 0;
  color: var(--portal-muted, #8a9aa6);
  font-size: 12px;
  line-height: 1.45;
}
.tip {
  margin: 0;
  color: #b42318;
  font-size: 13px;
  line-height: 1.4;
}
.row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-top: auto;
}
.empty {
  text-align: center;
  color: var(--portal-muted, #8a9aa6);
  padding: 48px 0;
}
.pager {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
@media (max-width: 560px) {
  .hero h1 { font-size: 22px; }
}
</style>
