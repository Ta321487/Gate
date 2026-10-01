/**
 * 填岛计划预览 + SSE 快照（挂入 useProjectDetail）。
 */
import { computed, ref } from 'vue'
import { api, message } from '../../api'
import { statusPillNode } from '../../opsShared'
import { FILL_UNIT_KIND_ZH, FILL_UNIT_STATUS_ZH } from './pdLabels'

/**
 * @param {object} deps
 * @param {import('vue').Ref} deps.p
 */
export function usePdFillLive({ p }) {
  const showFillPlan = ref(false)
  const fillPlanLoading = ref(false)
  const fillPlanRows = ref([])
  const fillPlanCols = [
    { title: 'Unit ID', key: 'id', width: 160, ellipsis: { tooltip: true } },
    { title: '类型', key: 'kind', width: 120 },
    { title: '状态', key: 'status', width: 88 },
    { title: '预算字符', key: 'budget_chars', width: 88 },
    { title: '来源', key: 'source_refs', ellipsis: { tooltip: true } },
  ]
  const fillLiveSnap = ref(null)
  const fillLiveCols = [
    { title: 'Unit', key: 'id', width: 150, ellipsis: { tooltip: true } },
    { title: '类型', key: 'kind', width: 110 },
    {
      title: '状态',
      key: 'status',
      width: 88,
      render: (r) => statusPillNode(
        FILL_UNIT_STATUS_ZH[r.status] || r.status,
        r.status === 'done'
          ? 'pill-green'
          : r.status === 'failed'
            ? 'pill-red'
            : r.status === 'running'
              ? 'pill-teal'
              : r.status === 'skipped'
                ? 'pill-neutral'
                : 'pill-neutral',
      ),
    },
  ]
  const fillLiveRows = computed(() => {
    const units = fillLiveSnap.value?.units
    if (!units || typeof units !== 'object') return []
    return Object.values(units).map((u) => ({
      id: u.id,
      kind: FILL_UNIT_KIND_ZH[u.kind] || u.kind,
      status: u.status || 'pending',
    }))
  })
  const fillLiveVisible = computed(() => fillLiveRows.value.length > 0)
  const fillLiveSummary = computed(() => {
    const s = fillLiveSnap.value
    if (!s?.total) return ''
    const parts = [`填岛 ${s.done || 0}/${s.total}`]
    if (s.running) parts.push(`进行中 ${s.running}`)
    if (s.failed) parts.push(`失败 ${s.failed}`)
    if (s.phase === 'done') parts.push('已合并')
    if (s.phase === 'failed') parts.push('填岛中断')
    return parts.join(' · ')
  })
  const fillPlanHint = computed(() => {
    if (!p.value?.workspace_path) return '生成工作区后可预览'
    if (fillPlanRows.value.length) return `共 ${fillPlanRows.value.length} 个 Unit`
    return '点击预览拆解粒度'
  })

  let fillEventSource = null

  function applyFillSnapshot(event) {
    if (!event || event.type === 'heartbeat') return
    if (event.type === 'snapshot') {
      fillLiveSnap.value = {
        phase: event.phase || 'idle',
        units: event.units || {},
        total: event.total || 0,
        done: event.done || 0,
        failed: event.failed || 0,
        running: event.running || 0,
        error: event.error || '',
      }
      if (showFillPlan.value && fillLiveRows.value.length) {
        fillPlanRows.value = fillLiveRows.value.map((r) => ({
          ...r,
          status: FILL_UNIT_STATUS_ZH[r.status] || r.status,
          budget_chars: fillLiveSnap.value?.units?.[r.id]?.budget_chars,
          source_refs: (fillLiveSnap.value?.units?.[r.id]?.source_refs || []).join(' · ') || '—',
        }))
      }
      if (['done', 'failed'].includes(event.phase)) {
        stopFillEvents()
      }
    }
  }

  function stopFillEvents() {
    if (fillEventSource) {
      fillEventSource.close()
      fillEventSource = null
    }
  }

  function startFillEvents() {
    if (!p.value?.id || fillEventSource) return
    const url = api.fillEventsUrl(p.value.id)
    const es = new EventSource(url)
    fillEventSource = es
    es.onmessage = (ev) => {
      try {
        applyFillSnapshot(JSON.parse(ev.data))
      } catch {
        /* ignore malformed frame */
      }
    }
    es.onerror = () => {
      /* EventSource 自动重连；轮询仍作兜底 */
    }
  }

  async function openFillPlan() {
    if (!p.value?.workspace_path || fillPlanLoading.value) return
    fillPlanLoading.value = true
    try {
      const res = await api.getFillPlan(p.value.id)
      const plan = res?.data?.plan || res?.plan
      const units = plan?.units || []
      fillPlanRows.value = units.map((u) => ({
        id: u.id,
        kind: FILL_UNIT_KIND_ZH[u.kind] || u.kind,
        status: FILL_UNIT_STATUS_ZH[u.status] || u.status || '—',
        budget_chars: u.budget_chars,
        source_refs: (u.source_refs || []).join(' · ') || '—',
      }))
      showFillPlan.value = true
    } catch (e) {
      message.error(e?.response?.data?.detail || e?.message || '无法加载填岛计划')
    } finally {
      fillPlanLoading.value = false
    }
  }

  return {
    showFillPlan,
    fillPlanLoading,
    fillPlanRows,
    fillPlanCols,
    fillLiveSnap,
    fillLiveCols,
    fillLiveRows,
    fillLiveVisible,
    fillLiveSummary,
    fillPlanHint,
    fillEventSource,
    applyFillSnapshot,
    startFillEvents,
    stopFillEvents,
    openFillPlan,
  }
}
