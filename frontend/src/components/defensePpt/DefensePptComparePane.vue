<template>
  <div class="artifact-pane stack defense-ppt-compare">
    <p v-if="pptLoading" class="small muted">加载中…</p>

    <template v-else-if="!pptHasDeck">
      <div class="empty-hint">
        <div class="empty-title">还没有答辩 PPT</div>
        <div class="empty-desc">到「一键生成」填写封面信息后生成。此处只做预览、改稿与导出。</div>
        <n-button size="small" class="mt-12" @click="goGeneratePpt">前往一键生成</n-button>
      </div>
    </template>

    <template v-else>
      <DefensePptDirtyBanner
        v-if="pptBizDirty && !dirtyDismissed"
        :syncing="pptActing === 'sync'"
        @sync="onSync"
        @diff="onDiff"
        @dismiss="dirtyDismissed = true"
      />

      <div class="row" style="justify-content:space-between;align-items:flex-start;gap:12px;flex-wrap:wrap">
        <div class="row" style="margin:0;gap:8px;flex-wrap:wrap;align-items:flex-end">
          <div>
            <label class="field-label">主题</label>
            <n-select
              v-model:value="pptSkin.theme"
              :options="themeSelectOpts"
              style="width:200px"
              size="small"
              @update:value="applyPptSkin"
            />
          </div>
          <div>
            <label class="field-label">版式族</label>
            <n-select
              v-model:value="pptSkin.layout_family"
              :options="layoutSelectOpts"
              style="width:180px"
              size="small"
              @update:value="applyPptSkin"
            />
          </div>
          <span class="small muted">换皮不标脏</span>
        </div>
        <div class="row" style="margin:0;gap:8px;flex-wrap:wrap">
          <n-button size="small" :loading="pptActing === 'check'" @click="runPptCheck">检查</n-button>
          <n-button size="small" :loading="pptActing === 'sync'" @click="onSync">按工程更新业务页</n-button>
          <n-button
            size="small"
            type="primary"
            :disabled="pptBizDirty"
            :loading="pptActing === 'export'"
            @click="exportPptx"
          >
            导出 PPTX
          </n-button>
        </div>
      </div>

      <div class="ppt-compare-grid">
        <div class="ppt-page-rail">
          <button
            v-for="(pg, idx) in pptDeck?.pages || []"
            :key="pg.id"
            type="button"
            class="ppt-page-item"
            :class="{ active: pptPageIndex === idx }"
            @click="pptPageIndex = idx"
          >
            {{ idx + 1 }}. {{ pg.title }}
          </button>
        </div>

        <div class="ppt-slide-stage">
          <DefensePptSlidePreview
            :page="pptCurrentPage"
            :cover="pptDeck?.cover || pptCover"
            :deck-title="pptDeck?.title || p?.title || '毕业设计答辩'"
            :layout-family="pptSkin.layout_family"
            :project-id="p?.id || ''"
            @save-bullet="onSaveBullet"
            @toggle-lock="onToggleLock"
          />
          <div
            v-if="pptCurrentPage?.role === 'demo'"
            class="row mt-8"
            style="gap:8px;flex-wrap:wrap"
          >
            <n-button
              size="small"
              secondary
              :loading="pptActing === 'shot'"
              @click="capturePptScreenshot(pptCurrentPage.id)"
            >
              采当前页（半自动）
            </n-button>
            <label style="margin:0;cursor:pointer">
              <n-button size="small" secondary tag="span">上传替换</n-button>
              <input type="file" accept="image/*" hidden @change="onUploadShot" />
            </label>
          </div>
        </div>

        <div class="ppt-side-pane stack">
          <div class="parse-sec-hd">证据 / 检查</div>
          <ul class="ppt-evidence-list">
            <li v-for="ref in pageRefs" :key="ref" class="small">
              <span class="pill pill-teal">{{ ref }}</span>
            </li>
            <li v-if="!pageRefs.length" class="small muted">本页无 source_refs</li>
          </ul>
          <p v-if="pptCurrentPage?.figure?.missing" class="small" style="color:var(--red)">
            缺主流程截图 · 导出将被阻断
          </p>
          <p class="small muted">
            点改要点后可锁定（locked），「按工程更新」将跳过锁定块。
          </p>
        </div>
      </div>
    </template>

    <DefensePptCheckModal
      v-model:show="showPptCheck"
      :result="pptCheckResult"
      :exporting="pptActing === 'export'"
      :can-export="pptCanExport"
      @export="exportPptx"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { bindPd } from '../../views/projectDetail/bindPd'
import { message } from '../../api.js'
import { readBlobAsDataUrl } from '../../ppt/badgeKnockout.js'
import { PPT_THEME_OPTIONS, PPT_LAYOUT_OPTIONS } from '../../ppt/deckDefaults.js'
import DefensePptDirtyBanner from './DefensePptDirtyBanner.vue'
import DefensePptSlidePreview from './DefensePptSlidePreview.vue'
import DefensePptCheckModal from './DefensePptCheckModal.vue'

const {
  tab,
  p,
  pptLoading,
  pptHasDeck,
  pptBizDirty,
  pptActing,
  pptSkin,
  pptDeck,
  pptCover,
  pptPageIndex,
  pptCurrentPage,
  pptCheckResult,
  showPptCheck,
  pptCanExport,
  goGeneratePpt,
  loadPptDeck,
  applyPptSkin,
  syncPptBiz,
  runPptCheck,
  exportPptx,
  savePptBullet,
  togglePptBulletLock,
  capturePptScreenshot,
  uploadPptScreenshot,
} = bindPd()

const dirtyDismissed = ref(false)

const themeSelectOpts = computed(() =>
  PPT_THEME_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
)
const layoutSelectOpts = computed(() =>
  PPT_LAYOUT_OPTIONS.map((o) => ({ label: o.label, value: o.value })),
)

const pageRefs = computed(() => {
  const set = new Set()
  for (const b of pptCurrentPage.value?.bullets || []) {
    for (const r of b.source_refs || []) set.add(r)
  }
  return [...set]
})

watch(
  () => pptBizDirty.value,
  (v) => {
    if (v) dirtyDismissed.value = false
  },
)

async function onSync() {
  await syncPptBiz()
  dirtyDismissed.value = true
}

function onDiff() {
  message.info('差异对照：业务指纹变化项由后端提供；当前展示脏标与锁定块提示')
}

async function onSaveBullet(bulletId, text) {
  if (!pptCurrentPage.value) return
  await savePptBullet(pptCurrentPage.value.id, bulletId, text)
}

async function onToggleLock(bulletId) {
  if (!pptCurrentPage.value) return
  await togglePptBulletLock(pptCurrentPage.value.id, bulletId)
}

async function onUploadShot(e) {
  const file = e.target?.files?.[0]
  if (!file || !pptCurrentPage.value) return
  const dataUrl = await readBlobAsDataUrl(file)
  await uploadPptScreenshot(pptCurrentPage.value.id, dataUrl)
  e.target.value = ''
}

// 进入子页时拉 deck
loadPptDeck()
</script>

<style scoped>
.field-label {
  display: block;
  font-size: 12px;
  margin-bottom: 4px;
  color: var(--muted);
}
.empty-hint { padding: 48px 20px; text-align: center; }
.empty-title { font-size: 14px; font-weight: 600; color: var(--ink-2); margin-bottom: 6px; }
.empty-desc { font-size: 12px; color: var(--muted); }
</style>
