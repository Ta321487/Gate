<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" :placeholder="searchPlaceholder" clearable style="width:260px" @keyup.enter="load" />
      <el-switch
        v-if="softDelete"
        v-model="includeDeleted"
        inline-prompt
        :active-text="softCopy.include"
        :inactive-text="softCopy.on"
        @change="load"
      />
      <el-button type="primary" @click="load">查询</el-button>
      <el-button
        v-if="hotRankOn"
        :type="hotMode ? 'warning' : 'default'"
        @click="toggleHotMode"
      >{{ hotMode ? hotRankBackLabel : hotRankToggleLabel }}</el-button>
      <el-button type="success" @click="openEdit()">新增{{ label }}</el-button>
      <el-button v-if="cinemaSnackOn && hasSeatLayout" @click="openSnackAdmin">{{ cinemaSnackLabel }}</el-button>
      <el-button @click="exportCsv">导出 CSV</el-button>
      <el-button @click="downloadTemplate">导入模板</el-button>
      <el-upload
        :show-file-list="false"
        accept=".csv,text/csv"
        :http-request="onImport"
      >
        <el-button type="warning">导入 CSV</el-button>
      </el-upload>
    </div>
    <SchemaLabelHints :keys="archiveAdminHintKeys" />
    <p v-if="hotMode && hotRankOn" class="tip muted">{{ hotRankPageTitle }}：{{ hotRankPageLead }}</p>
    <p v-if="stallScoreSortOn && stallScoreHint" class="tip muted">{{ stallScoreLabel }}：{{ stallScoreHint }}</p>
    <p v-if="lastImportError" class="import-err">{{ lastImportError }}</p>
    <div class="table-scroll">
    <el-table :data="list" stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="title" :label="fieldLabel('title', '名称')" min-width="120" show-overflow-tooltip />
      <el-table-column v-if="viewCountOn" :label="viewCountLabel" width="90">
        <template #default="{ row }">{{ Number(row.viewCount) || 0 }}</template>
      </el-table-column>
      <el-table-column v-if="forumOpsOn" label="运营" width="150">
        <template #default="{ row }">
          <el-tag v-if="Number(row.pinTop) === 1" size="small" type="warning" effect="plain">{{ pinTopLabel }}</el-tag>
          <el-tag v-if="Number(row.essence) === 1" size="small" type="success" effect="plain">{{ essenceLabel }}</el-tag>
          <el-tag v-if="Number(row.locked) === 1" size="small" type="info" effect="plain">{{ lockedLabel }}</el-tag>
          <span v-if="!Number(row.pinTop) && !Number(row.essence) && !Number(row.locked)">—</span>
        </template>
      </el-table-column>
      <el-table-column v-if="downloadCountOn" :label="downloadCountLabel" width="100">
        <template #default="{ row }">{{ Number(row.downloadCount) || 0 }}</template>
      </el-table-column>
      <el-table-column :label="fieldLabel('author', '型号')" width="140">
        <template #default="{ row }">{{ formatAuthorCell(row.author) }}</template>
      </el-table-column>
      <el-table-column
        v-if="showIsbnCol"
        prop="isbn"
        :label="fieldLabel('isbn', '编号')"
        min-width="120"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{ isbnPlain(row.isbn) }}</template>
      </el-table-column>
      <el-table-column :label="fieldLabel(multiCategory ? 'categoryIds' : 'category', '分类')" min-width="120">
        <template #default="{ row }">
          {{
            (row.categoryNames?.length ? row.categoryNames.join('、') : row.categoryName) || '—'
          }}
        </template>
      </el-table-column>
      <el-table-column v-if="marketplace" label="店铺" min-width="120" show-overflow-tooltip>
        <template #default="{ row }">{{ row.shopName || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="hasMutex" prop="mutexCode" :label="fieldLabel('mutexCode', '互斥码')" width="110" />
      <el-table-column v-if="hasCheckin" prop="checkinCode" :label="fieldLabel('checkinCode', '签到码')" width="120">
        <template #default="{ row }">{{ row.checkinCode || '—' }}</template>
      </el-table-column>
      <el-table-column v-if="tagFilter" label="标签" min-width="120">
        <template #default="{ row }">
          <template v-if="tagColorOn && (row.tagNames || []).length">
            <span v-for="(name, i) in row.tagNames" :key="name + i" class="tag-chip">
              <span class="tag-dot" :style="{ background: tagColor(name) }" />{{ name }}
            </span>
          </template>
          <template v-else>{{ (row.tagNames || []).join('、') || '—' }}</template>
        </template>
      </el-table-column>
      <el-table-column v-if="showStock" :label="fieldLabel('stock', '库存')" width="110">
        <template #default="{ row }">
          <template v-if="stockAsToggle">
            <el-tag v-if="Number(row.stock) > 0" size="small" type="success" effect="plain">是</el-tag>
            <el-tag v-else size="small" type="info">否</el-tag>
          </template>
          <template v-else>
            <span :class="{ 'stock-warn': isLowStock(row) }">{{ row.stock }}</span>
            <el-tag v-if="isLowStock(row)" size="small" type="danger" effect="plain" class="warn-tag">预警</el-tag>
          </template>
        </template>
      </el-table-column>
      <el-table-column v-if="showShelfCol" label="上架" width="100">
        <template #default="{ row }">
          <el-tag size="small" :type="shelfTagType(row)" effect="plain">{{ shelfLabel(row) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column v-if="hasStartAt" prop="startAt" :label="fieldLabel('startAt', '开始时间')" width="170" />
      <el-table-column v-if="hasEndAt" prop="endAt" :label="fieldLabel('endAt', '结束')" width="170" />
      <el-table-column v-if="hasDeadline" prop="applyDeadlineAt" :label="fieldLabel('applyDeadlineAt', '截止')" width="170" />
      <el-table-column
        v-for="f in listExtraFields"
        :key="f.key"
        :prop="f.key"
        :label="f.label || f.key"
        min-width="100"
        show-overflow-tooltip
      >
        <template #default="{ row }">{{ formatArchiveScalar(f, row[f.key]) }}</template>
      </el-table-column>
      <el-table-column v-if="softDelete && !publishReview && !showShelfCol" label="状态" width="80">
        <template #default="{ row }">
          <el-tag v-if="row.deleted" size="small" type="info">{{ softCopy.off }}</el-tag>
          <el-tag v-else size="small" type="success" effect="plain">{{ softCopy.on }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" min-width="200" fixed="right">
        <template #default="{ row }">
          <div class="table-ops">
          <el-button link type="primary" @click="openEdit(row)">编辑</el-button>
          <el-button
            v-if="hospitalStopOn && canStopNotify(row)"
            link
            type="warning"
            @click="stopNotify(row)"
          >停诊退号</el-button>
          <el-button
            v-if="seatAttrsOn && hasSeatLayout"
            link
            type="primary"
            @click="openSeatAttrs(row)"
          >{{ seatAttrEditLabel }}</el-button>
          <el-button
            v-if="canReviewPublish && isSuper && isPendingReview(row)"
            link
            type="success"
            @click="approve(row)"
          >审核上架</el-button>
          <el-button
            v-if="canReviewPublish && isSuper && isPendingReview(row)"
            link
            type="warning"
            @click="reject(row)"
          >驳回</el-button>
          <el-button v-if="softDelete && row.deleted" link type="success" @click="restore(row)">恢复</el-button>
          <el-button v-else link type="danger" @click="remove(row)">{{ softDelete ? softCopy.verb : '删除' }}</el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
    </div>
    <div class="pager">
      <el-pagination
        v-model:current-page="page"
        v-model:page-size="size"
        background
        layout="total, sizes, prev, pager, next"
        :page-sizes="[10, 20, 50]"
        :total="total"
        @current-change="load"
        @size-change="load"
      />
    </div>
    <el-dialog
      v-model="visible"
      :title="form.id ? `编辑${label}` : `新增${label}`"
      :width="isbnRich ? '720px' : '480px'"
      destroy-on-close
    >
      <el-form :model="form" label-position="top" require-asterisk-position="right">
        <el-form-item :label="fieldLabel('title', '名称')" required>
          <ArchiveFieldControl
            :field="fieldMeta('title')"
            v-model="form.title"
            :placeholder="fieldLabel('title', '名称')"
          />
        </el-form-item>
        <el-form-item :label="fieldLabel('author', '型号')">
          <ArchiveFieldControl
            :field="{ ...fieldMeta('author'), key: 'author', label: fieldLabel('author', '型号') }"
            v-model="form.author"
          />
        </el-form-item>
        <el-form-item :label="fieldLabel('isbn', '编号')">
          <ArchiveFieldControl
            :field="{ ...fieldMeta('isbn'), key: 'isbn', label: fieldLabel('isbn', '编号'), type: isbnRich ? 'richtext' : fieldType('isbn') }"
            v-model="form.isbn"
            :body-field="archive.bodyField || ''"
          />
        </el-form-item>
        <el-form-item :label="fieldLabel(multiCategory ? 'categoryIds' : 'category', '分类')" required>
          <el-select
            v-if="!multiCategory"
            v-model="form.categoryId"
            style="width:100%"
            :placeholder="`请选择${fieldLabel('category', '分类')}`"
          >
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-select
            v-else
            v-model="form.categoryIds"
            multiple
            filterable
            clearable
            style="width:100%"
            :placeholder="`请选择${fieldLabel('categoryIds', '分类')}`"
          >
            <el-option-group
              v-for="g in categoriesByDimension"
              :key="g.dimension || '未分组'"
              :label="g.dimension || '未分组'"
            >
              <el-option v-for="c in g.items" :key="c.id" :label="c.name" :value="c.id" />
            </el-option-group>
          </el-select>
        </el-form-item>
        <el-form-item
          v-if="showStock"
          :label="fieldLabel('stock', '库存')"
          :required="!stockAsToggle"
        >
          <ArchiveFieldControl
            :field="{ ...fieldMeta('stock'), key: 'stock', label: fieldLabel('stock', '库存'), type: 'number' }"
            v-model="form.stock"
            :stock-as-toggle="stockAsToggle"
          />
        </el-form-item>
        <el-form-item v-if="softDelete && !isPendingReview(form)" :label="shelfFormLabel">
          <el-switch
            v-model="form.onShelf"
            inline-prompt
            :active-text="shelfSwitchOn"
            :inactive-text="shelfSwitchOff"
          />
        </el-form-item>
        <p v-if="scheduledPublishOn && publishAtHint" class="form-hint">{{ publishAtLabel }}：{{ publishAtHint }}</p>
        <p v-if="scheduledUnpublishOn && unpublishAtHint" class="form-hint">{{ unpublishAtLabel }}：{{ unpublishAtHint }}</p>
        <p v-if="offShelfReasonOn && offShelfReasonHint" class="form-hint">{{ offShelfReasonLabel }}：{{ offShelfReasonHint }}</p>
        <p v-if="shareCodeOn && shareCodeHint" class="form-hint">{{ shareCodeLabel }}：{{ shareCodeHint }}</p>
        <div v-if="episodeListOn && form.id" class="episode-admin">
          <p class="form-hint">{{ episodeAdminTitle }}</p>
          <el-button size="small" @click="loadEpisodes">刷新分集</el-button>
          <el-button size="small" type="primary" @click="openEpisodeEdit()">{{ episodeAddLabel }}</el-button>
          <ul class="ep-admin-list">
            <li v-for="ep in episodeRows" :key="ep.id">
              {{ ep.sortOrd }}. {{ ep.title }}
              <el-button link type="primary" @click="openEpisodeEdit(ep)">编辑</el-button>
              <el-button link type="danger" @click="removeEpisode(ep)">删除</el-button>
            </li>
          </ul>
        </div>
        <p v-else-if="softDelete && canReviewPublish && isPendingReview(form)" class="form-hint">
          待审核条目请用列表上的「审核上架」，不要用上下架开关。
        </p>
        <el-form-item v-if="hasMutex" :label="fieldLabel('mutexCode', '互斥码')">
          <el-input v-model="form.mutexCode" maxlength="32" :placeholder="`相同互斥码的${label}不可同选，可留空`" />
        </el-form-item>
        <el-form-item v-if="hasCheckin" :label="fieldLabel('checkinCode', checkinCodeLabel)">
          <p v-if="checkinCodeAdminHint" class="form-hint">{{ checkinCodeAdminHint }}</p>
          <div class="attach-row">
            <el-input v-model="form.checkinCode" maxlength="16" :placeholder="checkinCodeLabel" style="flex:1" />
            <el-button size="small" @click="genCheckin">生成</el-button>
          </div>
        </el-form-item>
        <el-form-item v-if="tagFilter" label="标签">
          <el-select v-model="form.tagIds" multiple filterable clearable placeholder="可选多个" style="width:100%">
            <el-option v-for="t in tags" :key="t.id" :label="t.name" :value="t.id" />
          </el-select>
        </el-form-item>
        <template v-if="hasStartAt || hasEndAt || hasDeadline">
          <el-form-item v-if="hasStartAt" :label="fieldLabel('startAt', '开始时间')" required>
            <el-date-picker
              v-model="form.startAt"
              v-bind="pickerProps('startAt')"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="hasEndAt" :label="fieldLabel('endAt', '结束时间')" required>
            <el-date-picker
              v-model="form.endAt"
              v-bind="pickerProps('endAt')"
              style="width:100%"
            />
          </el-form-item>
          <el-form-item v-if="hasDeadline" :label="fieldLabel('applyDeadlineAt', '截止')">
            <el-date-picker
              v-model="form.applyDeadlineAt"
              v-bind="pickerProps('applyDeadlineAt')"
              style="width:100%"
            />
          </el-form-item>
          <p v-if="scheduleNeedsClock" class="dt-hint">选日期后，点击面板<strong>上方时间</strong>再调时分；有步长时按格点选。</p>
        </template>
        <el-form-item
          v-for="f in extraFields"
          :key="f.key"
          :label="f.label || f.key"
        >
          <ArchiveFieldControl
            :field="f"
            v-model="form[f.key]"
            :body-field="archive.bodyField || ''"
          />
        </el-form-item>
        <el-form-item label="封面">
          <div class="cover-edit">
            <el-upload :show-file-list="false" accept="image/*" :http-request="onCover">
              <el-button size="small">上传</el-button>
            </el-upload>
            <img v-if="form.coverUrl" :src="form.coverUrl" class="cover-preview" alt="封面" />
            <span v-else class="muted">未上传</span>
          </div>
        </el-form-item>
        <el-form-item v-if="galleryOn" :label="galleryLabel">
          <div class="gallery-edit">
            <el-upload :show-file-list="false" accept="image/*" :http-request="onGalleryAdd">
              <el-button size="small" :disabled="form.galleryImages.length >= 9">添加图片</el-button>
            </el-upload>
            <div class="gallery-list">
              <div v-for="(u, i) in form.galleryImages" :key="i" class="gallery-item">
                <img :src="u" alt="" />
                <el-button link type="danger" size="small" @click="form.galleryImages.splice(i, 1)">移除</el-button>
              </div>
            </div>
            <p class="muted">最多 9 张；封面仍可单独设置。无封面时首张图集可作展示。</p>
          </div>
        </el-form-item>
        <el-form-item v-if="roomEquipOn" :label="equipSectionTitle">
          <el-select
            v-model="form.equipmentNames"
            multiple
            filterable
            clearable
            placeholder="从设备字典勾选"
            style="width: 100%"
          >
            <el-option v-for="n in equipOptions" :key="n" :label="n" :value="n" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog
      v-model="seatAttrVisible"
      :title="seatAttrEditLabel"
      width="640px"
      destroy-on-close
    >
      <p class="ops-hint">
        点击座位循环设置：普通 → {{ seatAttrCoupleLabel }} → {{ seatAttrAccessibleLabel }} → 普通
      </p>
      <div class="seat-attr-grid" :style="{ gridTemplateColumns: `repeat(${seatAttrCols}, 2.2rem)` }">
        <button
          v-for="seat in seatAttrSeats"
          :key="seat.seatCode"
          type="button"
          class="seat-attr-cell"
          :class="seat.seatAttr || 'plain'"
          @click="cycleSeatAttr(seat)"
        >
          {{ seat.seatCode }}
        </button>
      </div>
      <template #footer>
        <el-button @click="seatAttrVisible = false">取消</el-button>
        <el-button type="primary" :loading="seatAttrSaving" @click="saveSeatAttrs">保存</el-button>
      </template>
    </el-dialog>
    <el-dialog v-model="snackVisible" :title="cinemaSnackLabel" width="720px" destroy-on-close>
      <p v-if="cinemaSnackHint" class="ops-hint">{{ cinemaSnackHint }}</p>
      <el-table :data="snackRows" stripe size="small">
        <el-table-column prop="id" label="ID" width="60" />
        <el-table-column label="名称" min-width="140">
          <template #default="{ row }">
            <el-input v-model="row.title" maxlength="80" />
          </template>
        </el-table-column>
        <el-table-column label="售价" width="120">
          <template #default="{ row }">
            <el-input-number v-model="row.priceYuan" :min="0" :step="0.5" :precision="2" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="库存" width="110">
          <template #default="{ row }">
            <el-input-number v-model="row.stock" :min="0" :step="1" controls-position="right" />
          </template>
        </el-table-column>
        <el-table-column label="在售" width="90">
          <template #default="{ row }">
            <el-switch v-model="row.onSale" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="90">
          <template #default="{ row }">
            <el-button link type="primary" :loading="row._saving" @click="saveSnackRow(row)">{{ cinemaSnackSaveLabel }}</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="addSnackRow">新增卖品</el-button>
        <el-button type="primary" @click="snackVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import http from '../../api/http'
import ArchiveFieldControl from '../../components/ArchiveFieldControl.vue'
import SchemaLabelHints from '../../components/SchemaLabelHints.vue'
import { ARCHIVE_ADMIN_HINT_KEYS } from '../../utils/labelHintMount.js'
import { archiveCopy, formatArchiveScalar, getSchema, hasCap, isGalleryEnabled, softDeleteCopy } from '../../utils/domainSchema.js'
import { datePickerProps, dateTimePickerProps } from '../../utils/dateTimeField.js'
import { archiveFieldWidget } from '../../utils/archiveFieldWidget.js'
import { sanitizeHtml } from '../../utils/richHtml.js'
import { downloadCsv, stripBom } from '../../utils/csvDownload.js'
import { isValidIsbn } from '../../utils/isbn.js'

const archive = archiveCopy()
const softCopyBase = softDeleteCopy()
const marketplace = computed(() => !!getSchema()?.shopMarketplace)
const publishReview = computed(() => !!archive.publishReview)
const canReviewPublish = computed(() => marketplace.value || publishReview.value)
const softCopy = computed(() => {
  if (!marketplace.value) return softCopyBase
  return { ...softCopyBase, verb: '强制下架', off: '已强制下架', include: '含下架' }
})
/** 列表已有「上架」列时不再并列 softDelete「状态」，避免两套真相 */
const showShelfCol = computed(() => marketplace.value || publishReview.value)
const shelfFormLabel = computed(() => {
  if (marketplace.value) return '是否在售'
  return String(softCopy.value.verb || '').includes('下架') ? '上架状态' : '启用状态'
})
const shelfSwitchOn = computed(() => (marketplace.value ? '在售' : softCopy.value.on))
const shelfSwitchOff = computed(() => (marketplace.value ? '已下架' : softCopy.value.off))
const stockWarnBelow = computed(() => {
  const n = Number(getSchema()?.stockWarnBelow)
  return Number.isFinite(n) && n > 0 ? n : 10
})
const archiveAdminHintKeys = ARCHIVE_ADMIN_HINT_KEYS
const adminLabels = computed(() => getSchema()?.labels || {})
const thicken = computed(() => getSchema()?.tradeThicken || {})
const contentThicken = computed(() => getSchema()?.contentThicken || {})
const viewCountOn = computed(() => !!contentThicken.value.viewCount)
const viewCountLabel = computed(() => adminLabels.value.viewCountLabel || '阅读数')
const downloadCountOn = computed(() => !!contentThicken.value.hotByDownload)
const downloadCountLabel = computed(() => adminLabels.value.downloadCountLabel || '下载次数')
const hotRankOn = computed(() => !!contentThicken.value.hotRank)
const hotRankPageTitle = computed(() => adminLabels.value.hotRankPageTitle || '热门排行')
const hotRankPageLead = computed(() => adminLabels.value.hotRankPageLead || '按阅读次数从高到低排列。')
const hotRankToggleLabel = computed(() => adminLabels.value.hotRankToggleLabel || '看热门')
const hotRankBackLabel = computed(() => adminLabels.value.hotRankBackLabel || '全部')
const forumOpsOn = computed(
  () => !!(contentThicken.value.pinTop || contentThicken.value.essence || contentThicken.value.locked),
)
const pinTopLabel = computed(() => adminLabels.value.pinTopLabel || '置顶')
const essenceLabel = computed(() => adminLabels.value.essenceLabel || '精华')
const essencePointsRewardLabel = computed(
  () => adminLabels.value.essencePointsRewardLabel || '精华奖励积分',
)
const lockedLabel = computed(() => adminLabels.value.lockedLabel || '锁定')
const publishApproveNotifyTitle = computed(
  () => adminLabels.value.publishApproveNotifyTitle || '投稿已通过',
)
const scheduledPublishOn = computed(() => !!contentThicken.value.scheduledPublish)
const scheduledUnpublishOn = computed(() => !!contentThicken.value.scheduledUnpublish)
const publishAtLabel = computed(() => adminLabels.value.publishAtLabel || '定时发布')
const publishAtHint = computed(() => adminLabels.value.publishAtHint || '')
const unpublishAtLabel = computed(() => adminLabels.value.unpublishAtLabel || '定时撤回')
const unpublishAtHint = computed(() => adminLabels.value.unpublishAtHint || '')
const offShelfReasonOn = computed(() => !!contentThicken.value.offShelfReason)
const offShelfReasonLabel = computed(() => adminLabels.value.offShelfReasonLabel || '下架原因')
const offShelfReasonHint = computed(() => adminLabels.value.offShelfReasonHint || '')
const shareCodeOn = computed(() => !!contentThicken.value.shareCode)
const shareCodeLabel = computed(() => adminLabels.value.shareCodeLabel || '分享码')
const shareCodeHint = computed(() => adminLabels.value.shareCodeHint || '')
const episodeListOn = computed(() => !!contentThicken.value.episodeList)
const episodeAdminTitle = computed(() => adminLabels.value.episodeAdminTitle || '分集维护')
const episodeAddLabel = computed(() => adminLabels.value.episodeAddLabel || '新增分集')
const episodeUpdateNotifyHint = computed(() => adminLabels.value.episodeUpdateNotifyHint || '')
const episodeRows = ref([])
async function loadEpisodes() {
  if (!episodeListOn.value || !form.id) {
    episodeRows.value = []
    return
  }
  try {
    const res = await http.get(`/api/media-episodes/by-item/${form.id}`)
    episodeRows.value = res.data || res || []
  } catch {
    episodeRows.value = []
  }
}
async function openEpisodeEdit(row) {
  const title = row?.title || ''
  const { value } = await ElMessageBox.prompt('分集标题', row ? '编辑分集' : episodeAddLabel.value, {
    inputValue: title,
    confirmButtonText: '保存',
    cancelButtonText: '取消',
  })
  const t = (value || '').trim()
  if (!t) return
  let sortOrd = Number(row?.sortOrd) || episodeRows.value.length
  if (!row) {
    try {
      const { value: s } = await ElMessageBox.prompt('排序号', '分集排序', {
        inputValue: String(sortOrd),
        inputPattern: /^\d+$/,
        confirmButtonText: '下一步',
      })
      sortOrd = Number(s) || 0
    } catch { /* cancel sort → keep default */ }
  }
  await http.post('/api/media-episodes/admin', {
    id: row?.id || null,
    itemId: form.id,
    title: t,
    sortOrd,
    mediaUrl: row?.mediaUrl || '',
    notify: !row,
  })
  if (!row && episodeUpdateNotifyHint.value) {
    /* 新建默认通知；文案仅提示用 */
  }
  ElMessage.success('已保存分集')
  loadEpisodes()
}
async function removeEpisode(row) {
  await ElMessageBox.confirm(`删除分集「${row.title}」？`, '确认')
  await http.delete(`/api/media-episodes/admin/${row.id}`)
  ElMessage.success('已删除')
  loadEpisodes()
}
const hotMode = ref(false)
const seatAttrsOn = computed(() => !!thicken.value.seatAttrs)
const seatAttrEditLabel = computed(() => adminLabels.value.seatAttrEditLabel || '座位属性')
const seatAttrCoupleLabel = computed(() => adminLabels.value.seatAttrCoupleLabel || '情侣座')
const seatAttrAccessibleLabel = computed(() => adminLabels.value.seatAttrAccessibleLabel || '无障碍座')
const cinemaSnackOn = computed(() => !!thicken.value.cinemaSnack)
const cinemaSnackLabel = computed(() => adminLabels.value.cinemaSnackLabel || '卖品加购')
const cinemaSnackHint = computed(() => adminLabels.value.cinemaSnackHint || '')
const cinemaSnackSaveLabel = computed(() => adminLabels.value.cinemaSnackSaveLabel || '保存卖品')
const stallScoreSortOn = computed(() => !!thicken.value.stallScoreSort)
const stallScoreLabel = computed(() => adminLabels.value.stallScoreLabel || '档口评分')
const stallScoreHint = computed(() => adminLabels.value.stallScoreHint || '')
const seatAttrVisible = ref(false)
const seatAttrSaving = ref(false)
const seatAttrShowId = ref(0)
const seatAttrCols = ref(8)
const seatAttrSeats = ref([])
const snackVisible = ref(false)
const snackRows = ref([])
const tagColorOn = computed(() => !!adminLabels.value.tagColorHint)
const lastImportError = ref('')
function tagColor(name) {
  const s = String(name || '')
  let h = 0
  for (let i = 0; i < s.length; i += 1) h = (h * 31 + s.charCodeAt(i)) >>> 0
  return `hsl(${h % 360} 55% 48%)`
}
const isSuper = computed(() => localStorage.getItem('superAdmin') === 'true')
function isLowStock(row) {
  if (!marketplace.value || !row || stockAsToggle.value) return false
  return Number(row.stock) < stockWarnBelow.value
}
function isPendingReview(row) {
  return String(row?.status || '') === 'pending_review'
}
function shelfLabel(row) {
  const st = String(row?.status || '')
  if (st === 'pending_review') return '待审核'
  if (st === 'rejected') return '已驳回'
  if (st === 'sold_out') return adminLabels.value.showSoldOutLabel || '已售罄'
  if (st === 'unavailable' || row?.deleted) return '已下架'
  return '已上架'
}
function shelfTagType(row) {
  const st = String(row?.status || '')
  if (st === 'pending_review') return 'warning'
  if (st === 'rejected') return 'danger'
  if (st === 'unavailable' || row?.deleted) return 'info'
  return 'success'
}
const galleryOn = computed(() => isGalleryEnabled())
const galleryLabel = computed(() => getSchema()?.labels?.galleryLabel || '图集')
const roomEquipOn = computed(() => hasCap('room_equipment'))
const equipSectionTitle = computed(
  () => getSchema()?.labels?.roomEquipmentSectionTitle || '配套设备',
)
const equipOptions = ref([])
const label = computed(() => archive.label || '对象')
const fields = computed(() => archive.fields || [])
/** 内部备注标签（用户端不可见，管理端维护） */
const adminNoteLabel = computed(() => getSchema()?.labels?.adminNoteLabel || '内部备注')
const adminNoteHint = computed(() => getSchema()?.labels?.adminNoteHint || '')
void adminNoteLabel
void adminNoteHint
const checkinCodeLabel = computed(() => getSchema()?.labels?.checkinCodeLabel || '报到口令')
const checkinCodeAdminHint = computed(() => getSchema()?.labels?.checkinCodeAdminHint || '')
const hospitalStopOn = computed(
  () => !!(getSchema()?.reserveThicken?.hospitalStopNotify || getSchema()?.labels?.hospitalStopNotifyTitle),
)
const hospitalStopNotifyTitle = computed(() => getSchema()?.labels?.hospitalStopNotifyTitle || '科室停诊通知')
const hospitalStopNotifyBody = computed(() => getSchema()?.labels?.hospitalStopNotifyBody || '')
void hospitalStopNotifyBody
const hospitalStopCalendarHint = computed(() => getSchema()?.labels?.hospitalStopCalendarHint || '')
void hospitalStopCalendarHint
const deptIntroLabel = computed(() => getSchema()?.labels?.deptIntroLabel || '科室介绍')
const deptIntroHint = computed(() => getSchema()?.labels?.deptIntroHint || '')
void deptIntroLabel
void deptIntroHint
const queueEstimateLabel = computed(() => getSchema()?.labels?.queueEstimateLabel || '排队预估')
void queueEstimateLabel
const slotKindLabel = computed(() => getSchema()?.labels?.slotKindLabel || '号源类型')
const slotKindClinic = computed(() => getSchema()?.labels?.slotKindClinic || '门诊')
const slotKindLab = computed(() => getSchema()?.labels?.slotKindLab || '检验检查')
const slotKindHint = computed(() => getSchema()?.labels?.slotKindHint || '')
void slotKindLabel
void slotKindClinic
void slotKindLab
void slotKindHint
const patientProfileMenuLabel = computed(() => getSchema()?.labels?.patientProfileMenuLabel || '就诊人')
void patientProfileMenuLabel
const passHintLabel = computed(() => getSchema()?.labels?.passHintLabel || '通行证提示')
const passHintAdminHint = computed(() => getSchema()?.labels?.passHintAdminHint || '')
const parkingCarpassHint = computed(() => getSchema()?.labels?.parkingCarpassHint || '')
void passHintLabel
void passHintAdminHint
void parkingCarpassHint
const parkingPassMenuLabel = computed(() => getSchema()?.labels?.parkingPassMenuLabel || '停车次卡')
void parkingPassMenuLabel
const CORE_FIELD_KEYS = new Set([
  'title', 'author', 'isbn', 'category', 'stock',
  'mutexCode', 'checkinCode', 'startAt', 'endAt', 'applyDeadlineAt',
])
const extraFields = computed(() => fields.value.filter((f) => f?.key && !CORE_FIELD_KEYS.has(f.key)))
/** 列表展示的扩展列（排除富文本等过宽类型） */
const listExtraFields = computed(() =>
  extraFields.value.filter((f) => f.type !== 'richtext' && f.type !== 'hidden'),
)
const isbnRich = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  return f?.type === 'richtext' || archive.bodyField === 'isbn'
})
const showIsbnCol = computed(() => {
  const f = fields.value.find((x) => x.key === 'isbn')
  if (!f || f.type === 'hidden') return false
  return !isbnRich.value
})
function isbnPlain(v) {
  if (v == null || v === '') return '—'
  const s = String(v).replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim()
  return s || '—'
}
const hasSchedule = computed(() => fields.value.some((x) => x.key === 'startAt' || x.key === 'endAt'))
const hasStartAt = computed(() => fields.value.some((x) => x.key === 'startAt'))
const hasEndAt = computed(() => fields.value.some((x) => x.key === 'endAt'))
const hasDeadline = computed(() => fields.value.some((x) => x.key === 'applyDeadlineAt'))
const hasSeatLayout = computed(() => fields.value.some((x) => x.key === 'seatRows' || x.key === 'seatCols'))
const scheduleNeedsClock = computed(() =>
  ['startAt', 'endAt', 'applyDeadlineAt'].some(
    (key) => fieldType(key) === 'datetime' && fields.value.some((x) => x.key === key),
  ),
)
const hasMutex = computed(() => fields.value.some((x) => x.key === 'mutexCode'))
const hasCheckin = computed(() => fields.value.some((x) => x.key === 'checkinCode'))
const softDelete = computed(() => !!archive.softDelete)
const tagFilter = computed(() => !!archive.tagFilter)
const multiCategory = computed(() => !!archive.multiCategory || hasCap('multi_category'))
const categoriesByDimension = computed(() => {
  const groups = new Map()
  for (const c of categories.value || []) {
    const dim = (c.dimension || '').trim() || '未分组'
    if (!groups.has(dim)) groups.set(dim, [])
    groups.get(dim).push(c)
  }
  return [...groups.entries()].map(([dimension, items]) => ({ dimension, items }))
})
const stockDisplay = computed(() => archive.stockDisplay || 'count')
/** count：库存数字；available：可认领等余量；toggle：可读/可点播等开关；hidden：不展示 */
const stockAsToggle = computed(() => {
  if (stockDisplay.value === 'toggle') return true
  // 旧内容域 schema 仍写 available：无单据时按开关（失物招领等有 ticket_flow 仍用数字）
  if (stockDisplay.value === 'available') {
    const caps = getSchema()?.capabilities || []
    return !caps.includes('ticket_flow')
  }
  return false
})
const showStock = computed(() => {
  if (stockDisplay.value === 'hidden') return false
  const f = fields.value.find((x) => x.key === 'stock')
  if (f?.type === 'hidden') return false
  if (stockDisplay.value === 'available' || stockDisplay.value === 'toggle') return !!f
  return true
})

function fieldMeta(key) {
  return fields.value.find((x) => x.key === key) || { key }
}
function fieldType(key) {
  return fieldMeta(key).type || 'string'
}
function fieldLabel(key, fallback) {
  return fieldMeta(key).label || fallback
}
const searchPlaceholder = computed(() => {
  const parts = [fieldLabel('title', '名称'), fieldLabel('author', '型号')]
  const isbnF = fields.value.find((x) => x.key === 'isbn')
  if (isbnF && isbnF.type !== 'richtext' && isbnF.type !== 'hidden') {
    parts.push(isbnF.label || '编号')
  }
  return `搜索${parts.join(' / ')}`
})
function pickerProps(key) {
  const meta = fieldMeta(key)
  if (meta.type === 'date') return datePickerProps(meta)
  return dateTimePickerProps(meta)
}

/** 纯日期字段：API 若带回时分，截成 YYYY-MM-DD 喂给 date picker */
function calendarFormValue(key, raw) {
  if (raw == null || raw === '') return ''
  const s = String(raw).trim()
  if (fieldType(key) === 'date' && s.length >= 10) return s.slice(0, 10)
  return s
}

function formatAuthorCell(v) {
  return formatArchiveScalar({ ...fieldMeta('author'), key: 'author' }, v)
}

function extraDefault(f) {
  const w = archiveFieldWidget(f, { bodyField: archive.bodyField || '' })
  if (w === 'switch' || w === 'number' || w === 'money') return 0
  return ''
}

const list = ref([])
const total = ref(0)
const page = ref(1)
const size = ref(10)
const keyword = ref('')
const includeDeleted = ref(false)
const categories = ref([])
const tags = ref([])
const visible = ref(false)
const form = reactive({
  id: null,
  title: '',
  author: '',
  isbn: '',
  categoryId: null,
  categoryIds: [],
  stock: 1,
  status: '',
  onShelf: true,
  _wasDeleted: false,
  coverUrl: '',
  galleryImages: [],
  equipmentNames: [],
  startAt: '',
  endAt: '',
  applyDeadlineAt: '',
  mutexCode: '',
  checkinCode: '',
  tagIds: [],
})

function toggleHotMode() {
  hotMode.value = !hotMode.value
  page.value = 1
  load()
}

async function load() {
  const url = hotMode.value && hotRankOn.value ? '/api/archive/hot' : '/api/archive'
  const res = await http.get(url, {
    params: {
      page: page.value,
      size: size.value,
      keyword: hotMode.value ? undefined : (keyword.value || undefined),
      includeDeleted:
        !hotMode.value && softDelete.value && includeDeleted.value ? true : undefined,
      sortBy: hotMode.value && downloadCountOn.value
        ? 'downloadCount'
        : (hotMode.value && contentThicken.value.hotByPlay ? 'playCount' : undefined),
    },
  })
  list.value = res.data.list
  total.value = res.data.total
}

async function loadCats() {
  const res = await http.get('/api/categories')
  categories.value = res.data || res || []
}

async function loadTags() {
  if (!tagFilter.value) return
  try {
    const res = await http.get('/api/tags')
    tags.value = res.data || res || []
  } catch {
    tags.value = []
  }
}

async function loadEquipOptions() {
  if (!roomEquipOn.value) {
    equipOptions.value = []
    return
  }
  try {
    const res = await http.get('/api/equipment-dict/options')
    equipOptions.value = res.data || res || []
  } catch {
    equipOptions.value = []
  }
}

function genCheckin() {
  const n = Math.floor(1000 + Math.random() * 9000)
  form.checkinCode = `ACT${n}`
}

function openEdit(row) {
  const extras = {}
  for (const f of extraFields.value) {
    const raw = row?.[f.key] ?? extraDefault(f)
    extras[f.key] = f.type === 'date' && raw ? String(raw).slice(0, 10) : raw
  }
  if (row) {
    Object.assign(form, {
      id: row.id,
      title: row.title || '',
      author: row.author || '',
      isbn: row.isbn || '',
      categoryId: row.categoryId,
      categoryIds: [...(row.categoryIds || [])],
      stock: row.stock ?? 1,
      status: row.status || '',
      onShelf: !row.deleted,
      _wasDeleted: !!row.deleted,
      coverUrl: row.coverUrl || '',
      galleryImages: Array.isArray(row.galleryImages) ? [...row.galleryImages] : [],
      equipmentNames: Array.isArray(row.equipmentNames) ? [...row.equipmentNames] : [],
      startAt: calendarFormValue('startAt', row.startAt || ''),
      endAt: calendarFormValue('endAt', row.endAt || ''),
      applyDeadlineAt: calendarFormValue('applyDeadlineAt', row.applyDeadlineAt || ''),
      mutexCode: row.mutexCode || '',
      checkinCode: row.checkinCode || '',
      tagIds: [...(row.tagIds || [])],
      ...extras,
    })
  } else {
    Object.assign(form, {
      id: null,
      title: '',
      author: '',
      isbn: '',
      categoryId: categories.value[0]?.id || null,
      categoryIds: [],
      stock: 1,
      status: '',
      onShelf: true,
      _wasDeleted: false,
      coverUrl: '',
      galleryImages: [],
      equipmentNames: [],
      startAt: '',
      endAt: '',
      applyDeadlineAt: '',
      mutexCode: '',
      checkinCode: hasCheckin.value ? `ACT${Math.floor(1000 + Math.random() * 9000)}` : '',
      tagIds: [],
      ...extras,
    })
  }
  visible.value = true
  episodeRows.value = []
  if (form.id && episodeListOn.value) loadEpisodes()
}

async function save() {
  if (!form.title?.trim()) {
    ElMessage.warning('请填写名称')
    return
  }
  if (multiCategory.value) {
    if (!form.categoryIds?.length) {
      ElMessage.warning(`请选择${fieldLabel('categoryIds', '分类')}`)
      return
    }
  } else if (!form.categoryId) {
    ElMessage.warning(`请选择${fieldLabel('category', '分类')}`)
    return
  }
  if (hasStartAt.value && !form.startAt) {
    ElMessage.warning(`请填写${fieldLabel('startAt', '开始时间')}`)
    return
  }
  if (hasEndAt.value && !form.endAt) {
    ElMessage.warning(`请填写${fieldLabel('endAt', '结束时间')}`)
    return
  }
  if (getSchema()?.borrowThicken?.isbnValidate && !isValidIsbn(form.isbn)) {
    ElMessage.warning('ISBN 格式不正确，请核对后重试')
    return
  }
  const payload = { ...form }
  if (multiCategory.value) {
    payload.categoryId = form.categoryIds[0] || null
  } else {
    delete payload.categoryIds
  }
  delete payload.onShelf
  delete payload._wasDeleted
  if (isbnRich.value) payload.isbn = sanitizeHtml(form.isbn || '')
  let id = form.id
  if (form.id) await http.put(`/api/archive/${form.id}`, payload)
  else {
    const created = await http.post('/api/archive', payload)
    id = created?.id ?? created?.data?.id ?? null
  }
  if (softDelete.value && id && !isPendingReview(form)) {
    const wantOn = !!form.onShelf
    const wasOff = !!form._wasDeleted
    if (wantOn && wasOff) await http.post(`/api/archive/${id}/restore`)
    else if (!wantOn && !wasOff) {
      const reason = offShelfReasonOn.value ? String(form.offShelfReason || '').trim() : ''
      await http.delete(`/api/archive/${id}`, { data: { offShelfReason: reason } })
    }
  }
  ElMessage.success('已保存')
  visible.value = false
  load()
}

function canStopNotify(row) {
  if (!row || !row.id) return false
  const from = String(row.maintainFrom || row.maintain_from || '').trim()
  const to = String(row.maintainTo || row.maintain_to || '').trim()
  return !!(from || to)
}

async function stopNotify(row) {
  await ElMessageBox.confirm(
    `${hospitalStopNotifyTitle.value}：将取消维护期内预约并站内信通知用户。继续？`,
    '停诊退号',
    { type: 'warning' },
  )
  const res = await http.post(`/api/slots/items/${row.id}/stop-notify`)
  const n = res.data?.cancelled ?? res?.cancelled ?? 0
  ElMessage.success(`已退号 ${n} 笔`)
}

async function remove(row) {
  const verb = softDelete.value ? softCopy.value.verb : '删除'
  let reason = ''
  if (softDelete.value && offShelfReasonOn.value) {
    try {
      const { value } = await ElMessageBox.prompt(offShelfReasonHint.value || '请填写下架原因（可留空）', `${verb}「${row.title}」`, {
        inputValue: row.offShelfReason || '',
        confirmButtonText: verb,
        cancelButtonText: '取消',
      })
      reason = (value || '').trim()
    } catch {
      return
    }
  } else {
    await ElMessageBox.confirm(`确认${verb}「${row.title}」？`, '确认')
  }
  await http.delete(`/api/archive/${row.id}`, { data: { offShelfReason: reason } })
  ElMessage.success(softDelete.value ? `已${softCopy.value.verb}` : '已删除')
  load()
}

async function restore(row) {
  await http.post(`/api/archive/${row.id}/restore`)
  ElMessage.success('已恢复')
  load()
}

async function approve(row) {
  await ElMessageBox.confirm(`审核通过并上架「${row.title}」？`, publishReview.value ? '投稿审核' : '商品审核')
  await http.post(`/api/archive/${row.id}/approve`)
  ElMessage.success(
    publishReview.value
      ? `${publishApproveNotifyTitle.value}，已上架`
      : '已审核上架',
  )
  load()
}

async function reject(row) {
  await ElMessageBox.confirm(`驳回「${row.title}」？驳回后不公开展示。`, publishReview.value ? '投稿审核' : '商品审核')
  await http.post(`/api/archive/${row.id}/reject`)
  ElMessage.success('已驳回')
  load()
}

async function onCover(opt) {
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.coverUrl = res.data.url
  ElMessage.success('已上传')
}

async function onGalleryAdd(opt) {
  if (form.galleryImages.length >= 9) {
    ElMessage.warning('最多 9 张')
    return
  }
  const fd = new FormData()
  fd.append('file', opt.file)
  const res = await http.post('/api/upload', fd)
  form.galleryImages.push(res.data.url)
  if (!form.coverUrl) form.coverUrl = res.data.url
  ElMessage.success('已加入图集')
}

/** 核心列兜底中文名（schema 缺 label 时用） */
const FIELD_FALLBACK_LABELS = {
  title: '名称',
  author: '型号',
  isbn: '编号',
  category: '分类',
  stock: '库存',
  mutexCode: '互斥码',
  checkinCode: '签到码',
  startAt: '开始时间',
  endAt: '结束时间',
  applyDeadlineAt: '截止',
}

/**
 * 导入/导出列 = 当前领域 archive.fields 全量（hidden 除外）+ 可选标签。
 * 表头用领域中文 label；键与 ArchiveStore / updateItem 一致。
 */
function importColumns() {
  const cols = []
  const seen = new Set()
  for (const f of fields.value) {
    if (!f?.key || f.type === 'hidden') continue
    if (seen.has(f.key)) continue
    seen.add(f.key)
    cols.push({
      key: f.key,
      label: (f.label || FIELD_FALLBACK_LABELS[f.key] || f.key).trim(),
      type: f.type || 'string',
    })
  }
  for (const k of ['title', 'author', 'isbn', 'category', 'stock']) {
    if (seen.has(k)) continue
    if (k === 'stock' && !showStock.value) continue
    const meta = fields.value.find((f) => f?.key === k)
    if (meta?.type === 'hidden') continue
    seen.add(k)
    cols.push({ key: k, label: FIELD_FALLBACK_LABELS[k], type: k === 'stock' ? 'number' : 'string' })
  }
  if (tagFilter.value && !seen.has('tags')) {
    cols.push({ key: 'tags', label: '标签', type: 'string' })
  }
  return cols
}

function sampleForCol(col) {
  if (col.key === 'category') return `默认${col.label || fieldLabel('category', '分类')}`
  if (col.key === 'stock') return '1'
  if (col.key === 'tags') return ''
  if (col.key === 'checkinCode') return 'ACT1001'
  if (col.type === 'boolean' || col.type === 'switch') return '1'
  if (col.type === 'number') return '1'
  if (col.type === 'datetime') return '2026-07-21 09:00'
  if (col.type === 'date') return '2026-07-21'
  if (col.type === 'url') return 'https://example.com'
  if (col.type === 'textarea') return '示例说明'
  if (col.type === 'select' && Array.isArray(col.options) && col.options.length) {
    const o = col.options[0]
    return typeof o === 'object' && o != null ? (o.value ?? o.label) : o
  }
  return `示例${col.label}`
}

function exportCell(row, col) {
  if (col.key === 'category') return row.categoryName ?? ''
  if (col.key === 'tags') return (row.tagNames || []).join('、')
  const v = row[col.key]
  if (v == null || v === '') return ''
  const meta = { key: col.key, label: col.label, type: col.type }
  const shown = formatArchiveScalar(meta, v, '')
  return shown
}

function downloadTemplate() {
  const cols = importColumns()
  downloadCsv(
    `${label.value || 'archive'}_import_template.csv`,
    cols.map((c) => c.label),
    [cols.map(sampleForCol)],
  )
  ElMessage.success('已下载导入模板（UTF-8 BOM，Excel 可直接打开）')
}

/**
 * 把表头（领域中文 label 或英文 key）规范成后端 import 认可的 camelCase 键。
 * 兼容旧模板英文表头与当前领域导出的中文表头。
 */
function normalizeArchiveImportCsv(text) {
  const raw = stripBom(text)
  if (!raw.trim()) return raw
  const nl = raw.includes('\r\n') ? '\r\n' : raw.includes('\r') ? '\r' : '\n'
  const lines = raw.split(/\r\n|\n|\r/)
  const cols = importColumns()
  const alias = Object.create(null)
  cols.forEach((c) => {
    alias[c.key] = c.key
    alias[c.key.toLowerCase()] = c.key
    if (c.label) {
      alias[c.label] = c.key
      alias[c.label.toLowerCase()] = c.key
    }
  })
  ;[
    ['名称', 'title'], ['标题', 'title'], ['书名', 'title'],
    ['分类', 'category'], ['库存', 'stock'], ['数量', 'stock'],
    ['标签', 'tags'],
  ].forEach(([a, k]) => {
    if (!alias[a]) alias[a] = k
  })
  const headCells = splitCsvLineSimple(lines[0])
  const mapped = headCells.map((h) => {
    const t = String(h || '').trim()
    return alias[t] || alias[t.toLowerCase()] || t
  })
  lines[0] = mapped.map(csvEscapeCell).join(',')
  return lines.join(nl)
}

function splitCsvLineSimple(line) {
  const cells = []
  let cur = ''
  let inQuote = false
  for (let i = 0; i < line.length; i++) {
    const ch = line[i]
    if (ch === '"') {
      inQuote = !inQuote
    } else if ((ch === ',' && !inQuote) || ch === '\t') {
      cells.push(cur)
      cur = ''
    } else {
      cur += ch
    }
  }
  cells.push(cur)
  return cells
}

function csvEscapeCell(v) {
  let s = v == null ? '' : String(v)
  if (/[",\n\r]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

async function openSeatAttrs(row) {
  if (!row?.id) return
  seatAttrShowId.value = row.id
  seatAttrSaving.value = false
  try {
    const res = await http.get(`/api/seats/shows/${row.id}/map`)
    const data = res.data?.data || res.data || {}
    seatAttrCols.value = data.cols || row.seatCols || 8
    seatAttrSeats.value = (data.seats || []).map((s) => ({
      seatCode: s.seatCode,
      seatAttr: String(s.seatAttr || ''),
    }))
    seatAttrVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法加载座位图')
  }
}

function cycleSeatAttr(seat) {
  const cur = String(seat.seatAttr || '')
  if (cur === 'couple') seat.seatAttr = 'accessible'
  else if (cur === 'accessible') seat.seatAttr = ''
  else seat.seatAttr = 'couple'
}

async function saveSeatAttrs() {
  const attrs = {}
  for (const s of seatAttrSeats.value) {
    attrs[s.seatCode] = String(s.seatAttr || '')
  }
  seatAttrSaving.value = true
  try {
    await http.put(`/api/seats/shows/${seatAttrShowId.value}/attrs`, { attrs })
    ElMessage.success('座位属性已保存')
    seatAttrVisible.value = false
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    seatAttrSaving.value = false
  }
}

async function openSnackAdmin() {
  try {
    const res = await http.get('/api/seats/snacks/all')
    const list = res.data?.data || res.data || []
    snackRows.value = (Array.isArray(list) ? list : []).map((s) => ({
      id: s.id,
      title: s.title || '',
      priceYuan: Number(s.priceYuan || 0),
      stock: Number(s.stock || 0),
      onSale: String(s.status || 'on') === 'on',
      _saving: false,
    }))
    snackVisible.value = true
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '无法加载卖品')
  }
}

function addSnackRow() {
  snackRows.value = [
    ...snackRows.value,
    { id: 0, title: '', priceYuan: 0, stock: 0, onSale: true, _saving: false },
  ]
}

async function saveSnackRow(row) {
  if (!String(row.title || '').trim()) {
    ElMessage.warning('请填写卖品名称')
    return
  }
  row._saving = true
  try {
    const res = await http.put('/api/seats/snacks', {
      id: row.id || undefined,
      title: String(row.title).trim(),
      priceYuan: Number(row.priceYuan || 0),
      stock: Number(row.stock || 0),
      status: row.onSale ? 'on' : 'off',
    })
    const saved = res.data?.data || res.data || {}
    if (saved.id) row.id = saved.id
    ElMessage.success('已保存')
  } catch (e) {
    ElMessage.error(e?.response?.data?.message || e.message || '保存失败')
  } finally {
    row._saving = false
  }
}

async function exportCsv() {
  const res = await http.get('/api/archive', {
    params: { page: 1, size: 5000, keyword: keyword.value || undefined },
  })
  const rows = res.data?.list || []
  if (!rows.length) {
    ElMessage.warning('当前无数据可导出')
    return
  }
  const cols = importColumns()
  downloadCsv(
    `${label.value || 'archive'}_${Date.now()}.csv`,
    cols.map((c) => c.label),
    rows.map((row) => cols.map((c) => exportCell(row, c))),
  )
  ElMessage.success(`已导出 ${rows.length} 条（UTF-8，可用 Excel 直接打开）`)
}

async function onImport(opt) {
  const file = opt.file
  if (!file) return
  lastImportError.value = ''
  const text = normalizeArchiveImportCsv(await file.text())
  if (!text.trim()) {
    ElMessage.warning('文件为空')
    return
  }
  try {
    const res = await http.post('/api/archive/import', { csv: text })
    const r = res.data || {}
    const ok = r.ok || 0
    const fail = r.fail || 0
    if (fail > 0) {
      const sample = (r.errors || []).slice(0, 3).map((e) => `第${e.line}行: ${e.message}`).join('；')
      const hint = adminLabels.value.importRowErrorHint || adminLabels.value.leaveBalanceImportHint || ''
      lastImportError.value = [hint, `成功 ${ok} 条，失败 ${fail} 条。${sample}`].filter(Boolean).join(' ')
      ElMessage.warning(lastImportError.value)
    } else {
      ElMessage.success(`成功导入 ${ok} 条`)
    }
    await loadCats()
    await load()
  } catch (e) {
    const hint = adminLabels.value.importRowErrorHint || ''
    lastImportError.value = hint || (e?.response?.data?.message || e?.message || '导入失败')
    ElMessage.error(lastImportError.value)
  }
}

onMounted(async () => {
  await loadCats()
  await loadTags()
  await loadEquipOptions()
  await load()
})
</script>

<style scoped>
.toolbar { display: flex; gap: 8px; margin-bottom: 12px; flex-wrap: wrap; align-items: center; }
.ops-hint { margin: 0 0 10px; color: var(--el-text-color-secondary); font-size: 13px; }
.seat-attr-grid {
  display: grid;
  gap: 0.35rem;
  justify-content: center;
  margin: 0.5rem 0 0;
}
.seat-attr-cell {
  width: 2.2rem;
  height: 2.2rem;
  border: 1px solid var(--el-border-color);
  border-radius: 4px;
  font-size: 0.65rem;
  cursor: pointer;
  background: #fff;
  padding: 0;
}
.seat-attr-cell.couple { box-shadow: inset 0 0 0 2px #e6a23c; }
.seat-attr-cell.accessible { box-shadow: inset 0 0 0 2px #67c23a; }
.import-err { margin: 0 0 10px; color: #b45309; font-size: 13px; }
.tag-chip { display: inline-flex; align-items: center; gap: 4px; margin-right: 8px; }
.tag-dot { width: 8px; height: 8px; border-radius: 50%; display: inline-block; }
.pager { margin-top: 16px; display: flex; justify-content: flex-end; }
.stock-warn { color: #b91c1c; font-weight: 700; margin-right: 4px; }
.warn-tag { margin-left: 2px; }
.muted { margin-left: 8px; color: var(--portal-muted, #909399); font-size: 12px; }
.form-hint { margin: 6px 0 0; color: var(--portal-muted, #909399); font-size: 12px; line-height: 1.4; }
.cover-edit { display: flex; flex-direction: column; align-items: flex-start; gap: 8px; }
.cover-preview {
  width: 96px; height: 96px; object-fit: cover;
  border-radius: var(--portal-radius-sm, 8px);
  border: var(--portal-border-width, 1px) solid var(--portal-line, #e4e7ed);
  background: color-mix(in srgb, var(--portal-bg, #f5f7fa) 72%, var(--portal-surface, #fff));
}
.gallery-edit { display: flex; flex-direction: column; gap: 8px; width: 100%; }
.gallery-list { display: flex; flex-wrap: wrap; gap: 8px; }
.gallery-item {
  width: 88px; display: flex; flex-direction: column; align-items: center; gap: 4px;
}
.gallery-item img {
  width: 80px; height: 80px; object-fit: cover;
  border-radius: 8px; border: 1px solid #e4e7ed;
}
.attach-row { display: flex; gap: 8px; width: 100%; align-items: center; }
.dt-hint { margin: -4px 0 8px; font-size: 12px; color: #909399; line-height: 1.4; }
</style>
