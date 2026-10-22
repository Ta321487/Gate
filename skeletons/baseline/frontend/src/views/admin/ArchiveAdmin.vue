<template>
  <div>
    <div class="toolbar">
      <el-input v-model="keyword" :placeholder="searchPlaceholder" clearable style="width:260px" @keyup.enter="load" />
      <template v-if="advancedFilterOn">
        <el-select v-model="listStatus" clearable :placeholder="adminLabels.listFilterStatus || '状态'" style="width:120px" @change="load">
          <el-option :label="adminLabels.listFilterStatusOn || '在用'" value="available" />
          <el-option :label="adminLabels.listFilterStatusOff || '停用'" value="off" />
        </el-select>
        <el-date-picker
          v-model="createdFrom"
          type="date"
          value-format="YYYY-MM-DD"
          :placeholder="adminLabels.listFilterFrom || '开始日期'"
          style="width:140px"
          @change="load"
        />
        <el-date-picker
          v-model="createdTo"
          type="date"
          value-format="YYYY-MM-DD"
          :placeholder="adminLabels.listFilterTo || '结束日期'"
          style="width:140px"
          @change="load"
        />
      </template>
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
      <el-button v-if="recycleOn" :type="recycleMode ? 'warning' : 'default'" @click="toggleRecycle">
        {{ recycleMode ? (adminLabels.recycleBinBack || '返回列表') : (adminLabels.recycleBinLabel || '回收站') }}
      </el-button>
      <el-button v-if="batchDeleteOn && !recycleMode" type="danger" plain :disabled="!pickedIds.length" @click="batchRemove">
        {{ adminLabels.batchDeleteLabel || '批量删除' }}（{{ pickedIds.length }}）
      </el-button>
      <el-button type="success" @click="openEdit()">新增{{ label }}</el-button>
      <el-button v-if="cinemaSnackOn && hasSeatLayout" @click="openSnackAdmin">{{ cinemaSnackLabel }}</el-button>
      <el-button @click="onExportClick">导出 Excel</el-button>
      <el-button @click="downloadTemplate">导入模板</el-button>
      <el-upload
        :show-file-list="false"
        accept=".xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        :http-request="onImport"
      >
        <el-button type="warning">导入 Excel</el-button>
      </el-upload>
    </div>
    <SchemaLabelHints :keys="archiveAdminHintKeys" />
    <p v-if="hotMode && hotRankOn" class="tip muted">{{ hotRankPageTitle }}：{{ hotRankPageLead }}</p>
    <p v-if="stallScoreSortOn && stallScoreHint" class="tip muted">{{ stallScoreLabel }}：{{ stallScoreHint }}</p>
    <ul v-if="importErrors.length" class="import-err">
      <li v-for="(e, i) in importErrors" :key="i">第 {{ e.line }} 行：{{ e.message }}</li>
    </ul>
    <p v-else-if="lastImportError" class="import-err">{{ lastImportError }}</p>
    <p v-if="recycleMode" class="tip muted">{{ adminLabels.recycleBinEmpty && !list.length ? adminLabels.recycleBinEmpty : (adminLabels.recycleBinLabel || '回收站') }}</p>
    <div class="table-scroll">
    <el-table :data="list" stripe @selection-change="onPicked">
      <el-table-column v-if="batchDeleteOn && !recycleMode" type="selection" width="42" />
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
          <span v-if="datingAlbumAuditOn && row.albumAuditStatus" class="muted">{{ albumAuditStatusText(row) }}</span>
          <el-button
            v-if="datingAlbumAuditOn && isSuper && String(row.albumAuditStatus || '') === 'pending'"
            link
            type="success"
            @click="albumAudit(row, 'approved')"
          >{{ albumAuditApproveAction }}</el-button>
          <el-button
            v-if="datingAlbumAuditOn && isSuper && String(row.albumAuditStatus || '') === 'pending'"
            link
            type="warning"
            @click="albumAudit(row, 'rejected')"
          >{{ albumAuditRejectAction }}</el-button>
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
            <el-image
              v-if="form.coverUrl"
              :src="form.coverUrl"
              class="cover-preview"
              fit="cover"
              :preview-src-list="[form.coverUrl]"
              preview-teleported
            />
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
                <el-image
                  :src="u"
                  fit="cover"
                  :preview-src-list="form.galleryImages"
                  :initial-index="i"
                  preview-teleported
                  style="width: 64px; height: 64px"
                />
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
        <template v-if="carpoolCampusDictOn">
          <el-form-item :label="carpoolCampusStartLabel">
            <el-select
              v-model="form.startCampus"
              filterable
              allow-create
              default-first-option
              clearable
              :placeholder="carpoolCampusPlaceholder"
              style="width:100%"
            >
              <el-option v-for="c in carpoolCampusOptions" :key="'cs' + c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <el-form-item :label="carpoolCampusEndLabel">
            <el-select
              v-model="form.endCampus"
              filterable
              allow-create
              default-first-option
              clearable
              :placeholder="carpoolCampusPlaceholder"
              style="width:100%"
            >
              <el-option v-for="c in carpoolCampusOptions" :key="'ce' + c" :label="c" :value="c" />
            </el-select>
          </el-form-item>
          <p v-if="carpoolCampusDictHint" class="form-hint">{{ carpoolCampusDictHint }}</p>
        </template>
        <el-form-item v-if="carpoolViaPointsOn" :label="carpoolViaPointsLabel">
          <el-input
            v-model="form.viaPoints"
            type="textarea"
            :rows="2"
            :placeholder="carpoolViaPointsPlaceholder"
          />
          <p v-if="carpoolViaPointsHint" class="form-hint">{{ carpoolViaPointsHint }}</p>
        </el-form-item>
        <el-form-item v-if="carpoolShareNoteOn" :label="carpoolShareNoteLabel">
          <el-input
            v-model="form.shareNote"
            type="textarea"
            :rows="2"
            :placeholder="carpoolShareNotePlaceholder"
          />
          <p v-if="carpoolShareNoteHint" class="form-hint">{{ carpoolShareNoteHint }}</p>
        </el-form-item>
        <el-form-item v-if="carpoolPrefNoteOn" :label="carpoolPrefNoteLabel">
          <el-input v-model="form.prefNote" :placeholder="carpoolPrefNotePlaceholder" />
          <p v-if="carpoolPrefNoteHint" class="form-hint">{{ carpoolPrefNoteHint }}</p>
        </el-form-item>
        <el-form-item v-if="carpoolLuggageOn" :label="carpoolLuggageCountLabel">
          <el-input-number v-model="form.luggageCount" :min="0" :max="99" controls-position="right" />
          <p v-if="carpoolLuggageCountHint" class="form-hint">{{ carpoolLuggageCountHint }}</p>
        </el-form-item>
        <el-form-item v-if="carpoolDepartRemindOn" :label="carpoolDepartRemindLeadLabel">
          <el-input-number
            v-model="form.remindBeforeMinutes"
            :min="0"
            :max="1440"
            controls-position="right"
          />
          <p v-if="carpoolDepartRemindHint" class="form-hint">{{ carpoolDepartRemindHint }}</p>
          <p class="form-hint">
            {{ carpoolDepartRemindTitle }}：
            <template v-if="Number(form.remindBeforeMinutes) > 0">
              出发前 {{ form.remindBeforeMinutes }} 分钟
              <template v-if="carpoolDepartRemindBody"> · {{ carpoolDepartRemindBody }}</template>
            </template>
            <template v-else>{{ carpoolDepartRemindNoneLabel }}</template>
          </p>
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
    <el-dialog v-model="exportPickOpen" :title="adminLabels.exportColumnsTitle || '选择导出列'" width="420px">
      <el-checkbox-group v-model="exportPickKeys">
        <el-checkbox v-for="c in exportColumnOptions" :key="c.key" :label="c.key">{{ c.label }}</el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="exportPickOpen = false">取消</el-button>
        <el-button type="primary" :disabled="!exportPickKeys.length" @click="confirmExport">
          {{ adminLabels.exportColumnsConfirm || '导出' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup src="./ArchiveAdmin.setup.js"></script>

<style scoped src="./ArchiveAdmin.css"></style>
