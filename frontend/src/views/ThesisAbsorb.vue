<template>
  <!-- 列表：壳对齐「项目」页 -->
  <div v-if="!detailId" class="surface-page">
    <div class="surface-toolbar">
      <div>
        <h1 class="page-title">终稿吸收</h1>
        <p class="page-desc">
          从终稿抽出需求与实现要点，标缺口后交给助手。
        </p>
      </div>
    </div>

    <div
      class="dropzone"
      :class="{ dragover, disabled: uploadBusy }"
      @dragover.prevent="dragover = true"
      @dragleave="dragover = false"
      @drop.prevent="onDrop"
    >
      <input
        type="file"
        accept=".pdf,.doc,.docx,.txt,.md"
        :disabled="uploadBusy"
        @change="onFileChange"
      />
      <div class="dropzone-icon">↑</div>
      <div class="dropzone-title">拖入终稿，或点击选择</div>
      <div class="dropzone-hint">PDF / Word / TXT · 单份上传</div>
    </div>

    <UploadJobPanel
      :jobs="uploadJobList"
      :hint="uploadQueueHint"
      :meta-fn="absorbJobMeta"
    >
      <template #actions="{ job }">
        <n-button
          v-if="job.status === 'done' && job.recordId"
          size="tiny"
          @click="openDoneJob(job)"
        >打开</n-button>
        <n-button
          v-if="job.status === 'done' || job.status === 'error'"
          text
          size="tiny"
          @click="dismissJob(job.id)"
        >移除</n-button>
      </template>
      <template #progress="{ job }">
        <!-- 有真 % 才定长条；上传无事件 / 抽取中 → 与 LongOpWait 同款走动条 -->
        <div
          v-if="job.status === 'uploading' && Number(job.pct) > 0"
          class="progress"
        ><i :style="{ width: job.pct + '%' }" /></div>
        <div
          v-else-if="job.status === 'uploading' || job.status === 'extracting'"
          class="sub-progress"
          aria-hidden="true"
        ><i /></div>
        <div
          v-else
          class="progress"
        ><i :style="{ width: '100%', background: jobBarColor(job) }" /></div>
      </template>
    </UploadJobPanel>

    <PageSkeleton v-if="!booted" variant="dashboard" :rows="4" />
    <template v-else>
      <div class="stats">
        <div
          class="stat clickable"
          :class="{ on: filterChipOn(filterMode, 'all') }"
          role="button"
          tabindex="0"
          @click="setFilter('all')"
          @keydown.enter="setFilter('all')"
        >
          <div class="label">全部</div>
          <div class="value">{{ itemList.length }}</div>
          <div class="hint">已上传的终稿</div>
        </div>
        <div
          class="stat clickable"
          :class="{ on: filterChipOn(filterMode, 'unknown') }"
          role="button"
          tabindex="0"
          @click="setFilter('unknown')"
          @keydown.enter="setFilter('unknown')"
        >
          <div class="label">待判断</div>
          <div class="value" :class="{ bad: unknownCount > 0 }">{{ unknownCount }}</div>
          <div class="hint">还没标覆盖</div>
        </div>
        <div
          class="stat clickable"
          :class="{ on: filterChipOn(filterMode, 'thin') }"
          role="button"
          tabindex="0"
          @click="setFilter('thin')"
          @keydown.enter="setFilter('thin')"
        >
          <div class="label">要点偏少</div>
          <div class="value" :class="{ bad: thinCount > 0 }">{{ thinCount }}</div>
          <div class="hint">抽到的功能不够</div>
        </div>
        <div
          class="stat clickable"
          :class="{ on: filterChipOn(filterMode, 'covered') }"
          role="button"
          tabindex="0"
          @click="setFilter('covered')"
          @keydown.enter="setFilter('covered')"
        >
          <div class="label">已齐</div>
          <div class="value">{{ coveredCount }}</div>
          <div class="hint">现有能力已覆盖</div>
        </div>
      </div>

      <div class="surface-tray projects-list-tray">
        <div class="surface-main-hd">
          <h2>终稿列表</h2>
          <div class="row" style="margin:0;gap:8px;flex-wrap:wrap">
            <n-button size="small" quaternary @click="maskTitles = !maskTitles">
              {{ maskTitles ? '显示题名' : '打码题名' }}
            </n-button>
            <n-button size="small" :loading="loading" @click="reload">刷新</n-button>
          </div>
        </div>
        <div class="row mb-12" style="justify-content:space-between;gap:8px;flex-wrap:wrap">
          <div class="filter-pills" role="group" aria-label="覆盖筛选">
            <button
              v-for="f in filters"
              :key="f.id"
              type="button"
              class="pill filter-pill"
              :class="[f.pill, { on: filterChipOn(filterMode, f.id) }]"
              @click="setFilter(f.id)"
            >{{ f.label }}</button>
          </div>
          <n-input
            v-model:value="q"
            clearable
            placeholder="搜索题名 / 文件名…"
            style="width:220px"
            @update:value="onSearch"
          />
        </div>
        <div v-if="!filteredItems.length" class="empty-hint">
          <div class="empty-title">{{ listEmptyCopy.title }}</div>
          <div class="empty-desc">{{ listEmptyCopy.desc }}</div>
        </div>
        <template v-else>
          <n-data-table
            :columns="listColumns"
            :data="pagedItems"
            :row-key="(r) => r.id"
            :bordered="false"
            size="small"
            :loading="loading"
          />
          <div class="small muted mt-12" style="display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap;align-items:center">
            <span>{{ filteredItems.length }} 条</span>
            <n-pagination
              v-model:page="page"
              v-model:page-size="pageSize"
              :item-count="filteredItems.length"
              :page-sizes="[10, 20, 50]"
              show-size-picker
              size="small"
            />
          </div>
        </template>
      </div>
    </template>
  </div>

  <!-- 详情：壳对齐「项目详情」——back + proj-head + detail-stage-body -->
  <template v-else>
    <ContentLoading v-if="detailLoading" :rows="5" compact show-label label="加载详情" />
    <div v-else-if="detail" class="surface-detail">
      <button type="button" class="back" @click="closeDetail">← 返回终稿列表</button>
      <div class="proj-head">
        <div class="proj-head-main">
          <div class="proj-title">{{ maskTitles ? '••••••••' : displayTitle(detail) }}</div>
          <div class="proj-meta">
            <span class="pill" :class="coverageClass(detail.coverage)">{{ coverageLabel(detail.coverage) }}</span>
            <span class="pill pill-neutral">{{ statusLabel(detail.status) }}</span>
            <span class="mono">{{ detail.display_no || ('#' + detail.id) }}</span>
            <span
              v-if="detail.public_id"
              class="mono muted"
              style="cursor:pointer"
              title="点击复制对账键"
              @click="copyText(detail.public_id)"
            >{{ detail.public_id }}</span>
            <span v-if="(detail.source_files || [])[0]" class="muted" :title="(detail.source_files || [])[0]">
              {{ (detail.source_files || [])[0] }}
            </span>
            <n-button text size="tiny" class="meta-tech-toggle" @click="maskTitles = !maskTitles">
              {{ maskTitles ? '显示题名' : '打码题名' }}
            </n-button>
          </div>
          <div v-if="detail.thin_features" class="proj-tech-extra">
            <n-checkbox v-model:checked="forceFeed">要点偏少仍复制</n-checkbox>
          </div>
        </div>
        <div class="proj-actions">
          <n-button size="small" :loading="detailLoading" @click="loadDetail">刷新</n-button>
          <template v-if="detail.status !== 'extracting'">
            <n-button size="small" :loading="reextracting" @click="doReextract">重新抽取</n-button>
            <n-button
              size="small"
              type="primary"
              :disabled="detail.thin_features && !forceFeed"
              :loading="feedBusy === (detail.public_id || detail.id)"
              @click="copyFeed(detail.public_id || detail.id)"
            >复制给助手</n-button>
          </template>
          <n-button type="error" secondary size="small" @click="doDelete">删除</n-button>
        </div>
      </div>

      <div v-if="detailOverlaps.length" class="ta-alert info mb-12">
        <div
          v-for="ov in detailOverlaps"
          :key="ov.id"
          class="row"
          style="gap:8px;align-items:flex-start;margin-bottom:6px"
        >
          <div style="flex:1;min-width:0">
            与「{{ maskTitles ? (`记录 #${ov.id}`) : overlapPeerLabel(ov) }}」有 {{ ov.overlap_count }} 处相近
            <div class="small muted">{{ (ov.overlap_lines || []).slice(0, 4).join('；') }}</div>
          </div>
          <n-button size="small" quaternary @click="openDetail(ov.id)">去看看</n-button>
        </div>
        <div class="small muted">相近记录各自保留</div>
      </div>

      <div v-if="detail.needs_reextract" class="ta-alert mb-12">
        <div class="row" style="justify-content:space-between;gap:12px;align-items:flex-start">
          <div style="flex:1;min-width:0">
            <div style="font-weight:600;margin-bottom:4px">抽取规则已更新</div>
            <div class="small muted">
              当前仍是上次结果 · 需重新抽取。
              <span v-if="(detail.reextract_reasons || []).length">
                {{ (detail.reextract_reasons || []).join('；') }}
              </span>
            </div>
          </div>
          <n-button
            size="small"
            type="primary"
            :loading="reextracting"
            @click="doReextract"
          >重新抽取</n-button>
        </div>
      </div>

      <!-- 长抽取 ≠ 短加载：用 LongOpWait（与启停/验收同款），禁止 ContentLoading 冒充 -->
      <div v-if="detail.status === 'extracting'" class="panel panel-quiet mb-12">
        <div class="panel-bd">
          <LongOpWait
            title="正在抽取"
            :started-at="detailExtractStartedAt"
            :phases="extractWaitPhases"
            :phase-seconds="[40, 120, 140]"
            hint="读文与扫图后由模型整理要点"
          />
        </div>
      </div>
      <div v-else class="detail-stage-body">
        <div class="panel panel-quiet mb-12">
          <div class="panel-hd"><h3>记录概要</h3></div>
          <div class="panel-bd">
            <div class="ta-id-grid">
              <div>
                <span class="ta-k">文档类型</span>
                <span :title="detail.role || undefined">{{ absorbRoleLabel(detail.role) }}</span>
              </div>
              <div>
                <span class="ta-k">抽取范围</span>
                <span :title="detail.focus || undefined">{{ absorbFocusLabel(detail.focus) }}</span>
              </div>
              <div><span class="ta-k">正文规模</span>{{ detail.char_count != null ? `${detail.char_count} 字` : '—' }}</div>
              <div>
                <span class="ta-k">图文对账</span>
                {{ figureStatusLabel }}
              </div>
              <div><span class="ta-k">功能要点</span>{{ featureCountHint }}</div>
            </div>
            <div class="mt-12">
              <div class="ta-section-label" style="margin-bottom:8px">文中技术栈</div>
              <div v-if="detailTechStack.length" class="ta-chips">
                <span
                  v-for="(t, i) in detailTechStack"
                  :key="`ts-${i}`"
                  class="pill pill-neutral ta-feat-pill"
                >{{ t }}</span>
              </div>
              <div v-else class="muted small">正文未点名常见技术选型</div>
            </div>
            <n-collapse class="mt-8">
              <n-collapse-item title="抽取元数据" name="tech">
                <div class="small muted mono">
                  抽取轮次 {{ detail.extract_round }} ·
                  抽取器 v{{ detail.extractor_version }} ·
                  内容指纹 {{ shortHash(detail.content_sha256) }}
                </div>
              </n-collapse-item>
            </n-collapse>
          </div>
        </div>

        <div class="panel panel-quiet mb-12">
          <div class="panel-hd">
            <h3>抽出的要点</h3>
            <div class="row" style="gap:6px">
              <n-button
                size="small"
                quaternary
                :title="machineUnlocked ? '重新锁定机器结果' : '解锁后可改要点 / 覆盖 / 补齐'"
                @click="toggleMachineUnlock"
              >{{ machineUnlocked ? '重新锁定' : '解锁调整' }}</n-button>
              <n-button
                v-if="machineUnlocked"
                size="small"
                type="primary"
                :loading="saving"
                @click="saveStructure"
              >保存要点</n-button>
            </div>
          </div>
          <div class="panel-bd" :class="{ 'ta-locked': !machineUnlocked }">
            <div class="lock-row" style="margin-bottom:10px">
              <span class="small muted">{{ machineUnlocked ? '要点 / 覆盖 / 补齐可调整' : '机器结果已锁定（文本框与按钮不可改）' }}</span>
            </div>
            <div v-if="detailWarnings.length" class="ta-alert mb-12">
              <div v-for="(w, i) in detailWarnings" :key="i">{{ w }}</div>
            </div>
            <div v-if="detail.thin_features" class="ta-alert mb-12">
              抽到的功能偏少（不足 {{ thinThreshold }} 条）。可「重新抽取」，或解锁后编辑从原文补几条。
            </div>

            <div class="ta-section-label">
              功能要点
              <span class="muted small" style="font-weight:400"> · {{ featureCountHint }}</span>
            </div>
            <div
              v-if="(machineUnlocked ? editFeatures : detailFeatureLines).length"
              class="ta-chips"
            >
              <span
                v-for="(f, i) in (machineUnlocked ? editFeatures : detailFeatureLines)"
                :key="`f-${i}`"
                class="pill pill-neutral ta-feat-pill"
              >
                {{ f }}
                <button
                  v-if="machineUnlocked"
                  type="button"
                  class="ta-feat-x"
                  aria-label="删除"
                  @click="editFeatures.splice(i, 1)"
                >×</button>
              </span>
            </div>
            <div v-else class="muted small">暂无</div>
            <div v-if="machineUnlocked" class="ta-add-row mt-8">
              <n-input
                v-model:value="featureAddText"
                size="small"
                placeholder="补一条要点"
                @keydown.enter.prevent="addFeatureLine"
              />
              <n-button size="small" @click="addFeatureLine">添加</n-button>
            </div>

            <div class="ta-section-label mt-16">不做 / 仅说明</div>
            <div
              v-if="(machineUnlocked ? editOut : detailOutLines).length"
              class="ta-chips"
            >
              <span
                v-for="(f, i) in (machineUnlocked ? editOut : detailOutLines)"
                :key="`o-${i}`"
                class="pill pill-neutral ta-feat-pill"
              >
                {{ f }}
                <button
                  v-if="machineUnlocked"
                  type="button"
                  class="ta-feat-x"
                  aria-label="删除"
                  @click="editOut.splice(i, 1)"
                >×</button>
              </span>
            </div>
            <div v-else class="muted small">暂无</div>
            <div v-if="machineUnlocked" class="ta-add-row mt-8">
              <n-input
                v-model:value="outAddText"
                size="small"
                placeholder="可空；写清不交或仅说明的项"
                @keydown.enter.prevent="addOutLine"
              />
              <n-button size="small" @click="addOutLine">添加</n-button>
            </div>

            <n-collapse class="mt-16">
              <n-collapse-item
                :title="`按章节${detailSections.length ? `（${detailSections.length}）` : ''}`"
                name="secs"
              >
                <div v-if="!detailSections.length" class="muted small">暂无</div>
                <div
                  v-for="(sec, i) in detailSections"
                  :key="i"
                  class="ta-sec-block"
                >
                  <div class="ta-sec-h">{{ sec.heading }}</div>
                  <div class="small muted ta-sec-lines">
                    {{ (sec.lines || []).slice(0, 8).join(' · ') || '（无摘句）' }}
                  </div>
                </div>
              </n-collapse-item>
              <n-collapse-item title="短摘录" name="excerpt">
                <pre class="spec-preview" style="max-height:160px">{{ detail.proposal?.excerpt || '暂无' }}</pre>
              </n-collapse-item>
            </n-collapse>
          </div>
        </div>

        <div class="panel panel-quiet mb-12">
          <div class="panel-hd">
            <h3>覆盖情况</h3>
            <span class="small muted">{{ machineUnlocked ? '可改预选' : '模型预选已锁定 · 上方解锁后可改' }}</span>
          </div>
          <div class="panel-bd" :class="{ 'ta-locked': !machineUnlocked, locked: !machineUnlocked }">
            <n-radio-group
              :value="detail.coverage"
              :disabled="!machineUnlocked"
              @update:value="onCoverage"
            >
              <n-radio-button value="unknown">待判断</n-radio-button>
              <n-radio-button value="covered">已齐</n-radio-button>
              <n-radio-button value="skin_gap">差说法</n-radio-button>
              <n-radio-button value="domain_gap">差能力</n-radio-button>
            </n-radio-group>
            <p v-if="detail.coverage === 'covered'" class="small muted mt-8" style="margin-bottom:0">
              现有能力已盖住主流程，一般不用新开能力。
            </p>
            <p v-else-if="detail.coverage === 'skin_gap'" class="small muted mt-8" style="margin-bottom:0">
              流程在，文案或演示数据不对 → 复制给助手时按「只补皮」。
            </p>
            <p v-else-if="detail.coverage === 'domain_gap'" class="small muted mt-8" style="margin-bottom:0">
              主流程盖不住 → 复制给助手时按「补能力」。
            </p>
            <p v-else class="small muted mt-8" style="margin-bottom:0">
              未跑大模型或吃不准时停在待判断；有预选可直接复制，拿不准就改一项。
            </p>
            <div
              v-if="(detail.coverage_hints || []).length"
              class="ta-coverage-hints mt-12"
            >
              <div class="ta-coverage-hints-hd">现厂速查</div>
              <p class="small muted" style="margin:4px 0 8px">
                对照用：同一份功能清单多次应一致；覆盖结论需人工确认，不算出包匹配。
              </p>
              <ul class="ta-coverage-hints-list">
                <li
                  v-for="h in detail.coverage_hints"
                  :key="h.domain_id"
                  class="ta-coverage-hint-item"
                >
                  <div class="ta-coverage-hint-title">
                    <strong>{{ h.label || h.domain_id }}</strong>
                    <span class="muted">{{ h.domain_id }} · 分 {{ h.score }}</span>
                  </div>
                  <div v-if="(h.hits || []).length" class="small">
                    命中：{{ (h.hits || []).join('、') }}
                  </div>
                  <div v-if="(h.flows || []).length" class="small muted">
                    流程：{{ (h.flows || []).join('；') }}
                  </div>
                  <div v-if="(h.caps || []).length" class="small muted">
                    默认能力：{{ (h.caps || []).join('、') }}
                  </div>
                </li>
              </ul>
            </div>
            <p
              v-else
              class="small muted mt-12"
              style="margin-bottom:0"
            >
              现厂速查：当前功能清单暂无稳定挂靠候选，覆盖请人工确认。
            </p>
            <n-input
              class="mt-12"
              v-model:value="coverageNote"
              type="textarea"
              :rows="2"
              :disabled="!machineUnlocked"
              placeholder="缺口备注（可选）"
              @blur="saveCoverageNote"
            />
          </div>
        </div>

        <div class="panel panel-quiet mb-12">
          <div class="panel-hd">
            <h3>补齐建议</h3>
            <div class="row" style="gap:8px;flex-wrap:wrap;align-items:center">
              <span class="small muted">{{ machineUnlocked ? '可增删改' : '已锁定 · 上方解锁后可改' }} · {{ draftsLlmHint }}</span>
              <n-button
                v-if="machineUnlocked"
                size="small"
                quaternary
                @click="refillDraftsFromExtract"
              >按抽取重填</n-button>
            </div>
          </div>
          <div class="panel-bd" :class="{ 'ta-locked': !machineUnlocked }">
            <div class="stage-grid grid-3 ta-draft-grid">
              <div class="ta-draft-col">
                <div class="ta-section-label">角色</div>
                <div v-if="draftRoles.length" class="ta-chips">
                  <template v-for="(f, i) in draftRoles" :key="`dr-${i}`">
                    <span
                      v-if="machineUnlocked && draftEdit?.kind === 'roles' && draftEdit.index === i"
                      class="ta-draft-edit-wrap"
                    >
                      <n-input
                        v-model:value="draftEdit.text"
                        size="tiny"
                        class="ta-draft-edit"
                        @keydown.enter.prevent="commitDraftEdit"
                        @keydown.esc.prevent="cancelDraftEdit"
                      />
                    </span>
                    <span
                      v-else
                      class="pill pill-neutral ta-feat-pill"
                      :class="{ 'ta-feat-pill--edit': machineUnlocked }"
                      :title="machineUnlocked ? '点击修改' : undefined"
                      @click="machineUnlocked && beginDraftEdit('roles', i)"
                    >
                      {{ f }}
                      <button
                        v-if="machineUnlocked"
                        type="button"
                        class="ta-feat-x"
                        aria-label="删除"
                        @click.stop="removeDraft('roles', i)"
                      >×</button>
                    </span>
                  </template>
                </div>
                <div v-else class="muted small">可空</div>
                <div v-if="machineUnlocked" class="ta-add-row mt-8">
                  <n-input
                    v-model:value="draftRoleAdd"
                    size="small"
                    placeholder="加一个角色"
                    @keydown.enter.prevent="addDraft('roles')"
                  />
                  <n-button size="small" @click="addDraft('roles')">添加</n-button>
                </div>
              </div>

              <div class="ta-draft-col">
                <div class="ta-section-label">实体</div>
                <div v-if="draftEntities.length" class="ta-chips">
                  <template v-for="(f, i) in draftEntities" :key="`de-${i}`">
                    <span
                      v-if="machineUnlocked && draftEdit?.kind === 'entities' && draftEdit.index === i"
                      class="ta-draft-edit-wrap"
                    >
                      <n-input
                        v-model:value="draftEdit.text"
                        size="tiny"
                        class="ta-draft-edit"
                        @keydown.enter.prevent="commitDraftEdit"
                        @keydown.esc.prevent="cancelDraftEdit"
                      />
                    </span>
                    <span
                      v-else
                      class="pill pill-neutral ta-feat-pill"
                      :class="{ 'ta-feat-pill--edit': machineUnlocked }"
                      :title="machineUnlocked ? '点击修改' : undefined"
                      @click="machineUnlocked && beginDraftEdit('entities', i)"
                    >
                      {{ f }}
                      <button
                        v-if="machineUnlocked"
                        type="button"
                        class="ta-feat-x"
                        aria-label="删除"
                        @click.stop="removeDraft('entities', i)"
                      >×</button>
                    </span>
                  </template>
                </div>
                <div v-else class="muted small">可空</div>
                <div v-if="machineUnlocked" class="ta-add-row mt-8">
                  <n-input
                    v-model:value="draftEntityAdd"
                    size="small"
                    placeholder="加一个实体"
                    @keydown.enter.prevent="addDraft('entities')"
                  />
                  <n-button size="small" @click="addDraft('entities')">添加</n-button>
                </div>
              </div>

              <div class="ta-draft-col">
                <div class="ta-section-label">功能</div>
                <div v-if="draftFeatures.length" class="ta-chips">
                  <template v-for="(f, i) in draftFeatures" :key="`df-${i}`">
                    <span
                      v-if="machineUnlocked && draftEdit?.kind === 'features' && draftEdit.index === i"
                      class="ta-draft-edit-wrap"
                    >
                      <n-input
                        v-model:value="draftEdit.text"
                        size="tiny"
                        class="ta-draft-edit"
                        @keydown.enter.prevent="commitDraftEdit"
                        @keydown.esc.prevent="cancelDraftEdit"
                      />
                    </span>
                    <span
                      v-else
                      class="pill pill-neutral ta-feat-pill"
                      :class="{ 'ta-feat-pill--edit': machineUnlocked }"
                      :title="machineUnlocked ? '点击修改' : undefined"
                      @click="machineUnlocked && beginDraftEdit('features', i)"
                    >
                      {{ f }}
                      <button
                        v-if="machineUnlocked"
                        type="button"
                        class="ta-feat-x"
                        aria-label="删除"
                        @click.stop="removeDraft('features', i)"
                      >×</button>
                    </span>
                  </template>
                </div>
                <div v-else class="muted small">可空</div>
                <div v-if="machineUnlocked" class="ta-add-row mt-8">
                  <n-input
                    v-model:value="draftFeatureAdd"
                    size="small"
                    placeholder="加一条功能"
                    @keydown.enter.prevent="addDraft('features')"
                  />
                  <n-button size="small" @click="addDraft('features')">添加</n-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="panel panel-quiet mb-12">
          <div class="panel-hd">
            <h3>论文库表 → schema.sql</h3>
            <div class="row" style="gap:8px;flex-wrap:wrap">
              <n-button
                size="small"
                :disabled="!(detail.draft_schema_sql || '').trim()"
                @click="copyText(detail.draft_schema_sql || '')"
              >复制 SQL</n-button>
            </div>
          </div>
          <div class="panel-bd">
            <p class="small muted" style="margin:0 0 8px">
              只收物理题注与字段表，同论文实现；不写进学生 ZIP。
              <template v-if="schemaMetaLine"> · {{ schemaMetaLine }}</template>
            </p>
            <div
              v-if="(detail.schema_extract_meta?.warnings || []).length"
              class="ta-schema-warns mb-8"
            >
              <div
                v-for="(w, wi) in detail.schema_extract_meta.warnings"
                :key="`sw-${wi}`"
                class="small"
                style="color: var(--warning-color, #b45309)"
              >{{ w }}</div>
            </div>
            <CodePreview
              v-if="(detail.draft_schema_sql || '').trim()"
              :code="detail.draft_schema_sql"
              lang="sql"
              extra-class="ta-pair-pre"
            />
            <div v-else class="muted small">尚未抽出可核对的 CREATE TABLE（缺题注或字段表时会空着落库）。</div>
          </div>
        </div>

        <div class="stage-grid grid-2 ta-feed-grid mb-12">
          <div class="panel panel-quiet">
            <div class="panel-hd">
              <h3>给助手</h3>
              <div class="row" style="gap:8px;flex-wrap:wrap">
                <n-button size="small" quaternary @click="markPatched">标记已处理</n-button>
                <n-button
                  size="small"
                  type="primary"
                  :disabled="detail.thin_features && !forceFeed"
                  :loading="feedBusy === (detail.public_id || detail.id)"
                  @click="copyFeed(detail.public_id || detail.id)"
                >复制给助手</n-button>
              </div>
            </div>
            <div class="panel-bd">
              <p class="small muted" style="margin:0 0 8px">按当前覆盖生成，可反复复制</p>
              <pre class="spec-preview ta-pair-pre">{{ detail.feed_markdown }}</pre>
            </div>
          </div>

          <div class="panel panel-quiet">
            <div class="panel-hd">
              <h3>反推成开题</h3>
              <n-button size="small" @click="copyText(detail.opening_draft)">
                复制开题草稿
              </n-button>
            </div>
            <div class="panel-bd">
              <p class="small muted" style="margin:0 0 8px">开题草稿（不含原题名）</p>
              <pre class="spec-preview ta-pair-pre">{{ detail.opening_draft }}</pre>
            </div>
          </div>
        </div>

        <div class="panel panel-quiet mb-12">
          <div class="panel-hd"><h3>试一下</h3></div>
          <div class="panel-bd">
            <n-collapse :key="`k2-${detail.coverage}`" :default-expanded-names="knife2Open ? ['k2'] : []">
              <n-collapse-item title="拿到「项目」页试匹配" name="k2">
                <p class="small muted" style="margin-top:0">
                  下载开题草稿到项目页试匹配（非正式建项）。
                </p>
                <n-button size="small" type="primary" secondary @click="confirmTrial">
                  下载并打开项目页
                </n-button>
              </n-collapse-item>
            </n-collapse>

            <div class="mt-16">
              <div class="ta-section-label">图与文字交叉</div>
              <p class="small muted" style="margin:0 0 8px">
                上传 / 重新抽取时自动跑：题注锚点 → 结构图 OCR → 与要点对账（只告警，不脑补进清单）。
              </p>
              <div class="small">{{ figureStatusLabel }}</div>
              <div v-if="figureLabelPreview.length" class="small muted mt-8">
                结构图标签：{{ figureLabelPreview.join('、') }}
              </div>
              <div v-else-if="detail.figure_extract_ready === false" class="small muted mt-8">
                {{ detail.figure_extract_hint || '图侧库未就绪，文字终稿可照常使用' }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
    <PageSkeleton v-else variant="detail" />
  </template>
</template>


<script setup>
import { computed, h, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton } from 'naive-ui'
import { api, message, confirm } from '../api'
import { debounce, filterChipOn } from '../opsShared'
import {
  cancelUploadJobAutoDismiss,
  scheduleUploadJobAutoDismiss,
} from '../utils/uploadJobDismiss'
import {
  absorbUploadJobPhaseLabel,
  uploadJobBarColor,
} from '../utils/uploadJobUi'
import { copyMaterialText } from '../utils/zhCopy'
import PageSkeleton from '../components/PageSkeleton.vue'
import UploadJobPanel from '../components/UploadJobPanel.vue'
import ContentLoading from '../components/ContentLoading.vue'
import LongOpWait from '../components/LongOpWait.vue'
import CodePreview from '../components/CodePreview.vue'

/** 详情页长抽取阶段（与后台读文→扫图→LLM 对齐，秒数仅推进高亮） */
const extractWaitPhases = [
  { key: 'read', label: '读文' },
  { key: 'fig', label: '扫图' },
  { key: 'llm', label: '整理要点' },
]

const route = useRoute()
const router = useRouter()

const booted = ref(false)
const loading = ref(false)
const dragover = ref(false)
const items = ref([])
const q = ref('')
/** all | unknown | covered | skin_gap | domain_gap | thin */
const filterMode = ref('all')
const maskTitles = ref(true)
const page = ref(1)
const pageSize = ref(20)
const thinThreshold = 3

/** 上传任务：上传段跟项目页真 %；抽取段跟 LongOpWait 走动条 + 已等待 */
const uploadJobs = ref([])
let uploadSeq = 0

const uploadJobList = computed(() => (Array.isArray(uploadJobs.value) ? uploadJobs.value : []))
const itemList = computed(() => (Array.isArray(items.value) ? items.value : []))

/** 仅字节上传中挡选文件；后台抽取不挡再传下一份 */
const uploadBusy = computed(() =>
  uploadJobList.value.some((j) => j.status === 'uploading'),
)

const uploadQueueHint = computed(() => {
  const n = uploadJobList.value.length
  if (!n) return ''
  if (uploadJobList.value.some((j) => j.status === 'extracting')) return '抽取中'
  if (uploadBusy.value) return '上传中'
  return `${n} 条`
})

const filters = [
  { id: 'all', label: '全部', pill: 'pill-neutral' },
  { id: 'unknown', label: '待判断', pill: 'pill-amber' },
  { id: 'covered', label: '已齐', pill: 'pill-green' },
  { id: 'skin_gap', label: '差说法', pill: 'pill-amber' },
  { id: 'domain_gap', label: '差能力', pill: 'pill-red' },
  { id: 'thin', label: '要点偏少', pill: 'pill-amber' },
]

const detailId = computed(() => {
  const id = route.params.id
  if (id == null || id === '') return null
  return String(id)
})
const detail = ref(null)
const detailLoading = ref(false)
/** 详情长抽取计时：优先本页上传任务 startedAt，否则用记录时间戳（刷新可续） */
const detailExtractStartedAt = computed(() => {
  const d = detail.value
  if (!d || d.status !== 'extracting') return 0
  const pid = String(d.public_id || '')
  const rid = d.id != null ? String(d.id) : ''
  const job = uploadJobList.value.find((j) => {
    if (j.status !== 'extracting') return false
    const jr = j.recordId != null ? String(j.recordId) : ''
    return (pid && jr === pid) || (rid && jr === rid)
  })
  if (job && Number(job.startedAt) > 0) return Number(job.startedAt)
  const iso = d.updated_at || d.created_at
  if (!iso) return 0
  const t = Date.parse(iso)
  return Number.isFinite(t) ? t : 0
})
const reextracting = ref(false)
const saving = ref(false)
const feedBusy = ref(null)
/** 匹配页同款：机器结果默认锁；解锁后要点/覆盖/补齐的文本框与按钮才可改 */
const machineUnlocked = ref(false)
const editFeatures = ref([])
const editOut = ref([])
const featureAddText = ref('')
const outAddText = ref('')
const coverageNote = ref('')
const draftRoles = ref([])
const draftEntities = ref([])
const draftFeatures = ref([])
const draftRoleAdd = ref('')
const draftEntityAdd = ref('')
const draftFeatureAdd = ref('')
/** { kind: 'roles'|'entities'|'features', index: number, text: string } */
const draftEdit = ref(null)
const forceFeed = ref(false)

const unknownCount = computed(() => itemList.value.filter((r) => r.coverage === 'unknown').length)
const thinCount = computed(() =>
  itemList.value.filter((r) => r.thin_features && r.status !== 'extracting').length,
)
const coveredCount = computed(() => itemList.value.filter((r) => r.coverage === 'covered').length)

const filteredItems = computed(() => {
  const list = itemList.value
  const mode = filterMode.value
  if (mode === 'all') return list
  if (mode === 'thin') return list.filter((r) => r.thin_features && r.status !== 'extracting')
  return list.filter((r) => r.coverage === mode)
})

/** 搜无 / 筛无 / 库空：三套空态，禁止搜不到也催上传 */
const listEmptyCopy = computed(() => {
  const hasQ = Boolean(String(q.value || '').trim())
  const filtered = filterMode.value !== 'all'
  if (hasQ) {
    return { title: '没有搜到终稿', desc: '换关键词或清空搜索' }
  }
  if (filtered) {
    return { title: '没有符合条件的终稿', desc: '换筛选看看' }
  }
  return { title: '还没有终稿', desc: '拖入上方上传区' }
})

const pagedItems = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredItems.value.slice(start, start + pageSize.value)
})

const knife2Open = computed(() => detail.value?.coverage === 'covered')

const detailOverlaps = computed(() =>
  Array.isArray(detail.value?.overlaps) ? detail.value.overlaps : [],
)
const detailTechStack = computed(() => {
  const raw = detail.value?.proposal?.tech_stack_lines
  if (!Array.isArray(raw)) return []
  return raw.map((x) => String(x || '').trim()).filter(Boolean)
})
const detailWarnings = computed(() =>
  Array.isArray(detail.value?.warnings) ? detail.value.warnings : [],
)
const schemaMetaLine = computed(() => {
  const m = detail.value?.schema_extract_meta
  if (!m || typeof m !== 'object') return ''
  const n = Number(m.table_count || 0)
  const c = Number(m.caption_count || 0)
  if (!c && !n) return ''
  const ok = m.homology_ok === false ? '同源未过' : '同源可对'
  return `题注 ${c} · 有列 ${n} · ${ok}`
})

const draftsLlmHint = computed(() => {
  const d = detail.value || {}
  if (d.absorb_used_llm) return '已用模型抽三栏'
  const skip = String(d.absorb_llm_skip || '').trim()
  const warn = detailWarnings.value.find(
    (w) => typeof w === 'string' && /未配置|已关闭|预算|大模型|Key/i.test(w),
  )
  if (skip || warn) {
    const why = warn || (
      skip === 'llm_no_key' ? '未配置 Key'
        : skip === 'llm_stage_off' ? '阶段已关闭'
          : skip === 'llm_budget' ? 'Token 预算用尽'
            : skip === 'llm_call_fail' ? '模型调用失败'
              : skip
    )
    return `未用模型（${why}）· 角色按端名、实体按表题注`
  }
  return '三栏以模型为主；未用模型时角色按端名、实体按表题注'
})
const detailFeatureLines = computed(() => {
  // 有大模型功能栏时优先展示，避免顶栏仍挂正则碎句
  const drafts = Array.isArray(detail.value?.draft_features)
    ? detail.value.draft_features
    : []
  if (drafts.length) return drafts
  return Array.isArray(detail.value?.proposal?.feature_lines)
    ? detail.value.proposal.feature_lines
    : []
})
const detailOutLines = computed(() =>
  Array.isArray(detail.value?.proposal?.out_scope_lines)
    ? detail.value.proposal.out_scope_lines
    : [],
)
const featureCountHint = computed(() => {
  const n = machineUnlocked.value
    ? (Array.isArray(editFeatures.value) ? editFeatures.value.length : 0)
    : detailFeatureLines.value.length
  return n ? `${n} 条` : '无'
})
const figureLabelPreview = computed(() => {
  const labs = detail.value?.proposal?.figure_labels
  if (!Array.isArray(labs)) return []
  return labs.map((x) => String(x || '').trim()).filter(Boolean).slice(0, 12)
})
const figureStatusLabel = computed(() => {
  const d = detail.value
  if (!d) return '—'
  const n = figureLabelPreview.value.length
  if (n) return `已对账 · 结构图标签 ${n}`
  if (d.has_figure_text) return '含图注 · 结构标签待解析'
  if (d.figure_extract_ready) return '待写入 · 请重新抽取'
  return '仅正文'
})

function absorbRoleLabel(v) {
  return ({ thesis: '终稿论文' })[v] || v || '—'
}

function absorbFocusLabel(v) {
  return ({ thesis_impl: '系统实现' })[v] || v || '—'
}
const detailSections = computed(() => {
  const secs = detail.value?.proposal?.sections
  if (!Array.isArray(secs)) return []
  return secs
    .filter((s) => s && typeof s === 'object')
    .map((s) => ({
      heading: s.heading || '',
      lines: Array.isArray(s.lines) ? s.lines : [],
    }))
})

function coverageLabel(v) {
  return ({ unknown: '待判断', covered: '已齐', skin_gap: '差说法', domain_gap: '差能力' })[v] || v
}

/** 覆盖状态 → 全局 pill 色类（勿删旧名 coverageClass，模板/热更新都靠它） */
function coverageClass(v) {
  return (
    {
      unknown: 'pill-neutral',
      covered: 'pill-green',
      skin_gap: 'pill-amber',
      domain_gap: 'pill-red',
    }[v] || 'pill-neutral'
  )
}

function coveragePillNode(v) {
  return h('span', { class: ['pill', coverageClass(v)] }, coverageLabel(v))
}

const listColumns = computed(() => [
  {
    title: '编号',
    key: 'display_no',
    width: 72,
    render(row) {
      return h('span', { class: 'mono', title: row.public_id || '' }, row.display_no || `#${row.id}`)
    },
  },
  {
    title: '题名',
    key: 'title',
    render(row) {
      const file = (row.source_files || [])[0] || ''
      const when = shortTime(row.created_at || row.updated_at)
      const titleKids = [
        h('span', maskTitles.value ? '••••••••' : displayTitle(row)),
      ]
      if (row.thin_features && row.status !== 'extracting') {
        titleKids.push(h('span', { class: 'pill pill-amber', style: 'margin-left:6px' }, '要点偏少'))
      }
      return h('div', { style: 'min-width:200px' }, [
        h('div', {
          style: 'font-weight:600;line-height:1.35;display:flex;align-items:center;flex-wrap:wrap;gap:4px',
        }, titleKids),
        file
          ? h('div', { class: 'small muted', style: 'margin-top:4px;word-break:break-all' }, file)
          : null,
        h('div', { class: 'small muted', style: 'margin-top:2px' }, `上传 ${when}`),
      ])
    },
  },
  {
    title: '文字/图注',
    key: 'figure',
    width: 96,
    render(row) {
      return h('span', { class: 'small' }, row.has_figure_text ? '含图注' : '文字')
    },
  },
  {
    title: '要点',
    key: 'feats',
    width: 64,
    render(row) {
      return h('span', String(row.feature_line_count ?? 0))
    },
  },
  {
    title: '覆盖',
    key: 'coverage',
    width: 96,
    render(row) {
      return coveragePillNode(row.coverage)
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 112,
    render(row) {
      return h('span', { class: 'small' }, statusLabel(row.status))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 168,
    render(row) {
      if (row.status === 'extracting') {
        return h('span', { class: 'small muted' }, '抽取中')
      }
      return h('div', { class: 'row', style: 'gap:4px;flex-wrap:wrap' }, [
        h(
          NButton,
          { size: 'tiny', quaternary: true, onClick: () => openDetail(row) },
          { default: () => '打开' },
        ),
        h(
          NButton,
          {
            size: 'tiny',
            quaternary: true,
            loading: feedBusy.value === (row.public_id || row.id),
            onClick: () => copyFeed(row.public_id || row.id),
          },
          { default: () => '复制给助手' },
        ),
      ])
    },
  },
])

function pushUnique(listRef, raw) {
  const v = String(raw || '').trim()
  if (!v) return false
  const arr = Array.isArray(listRef.value) ? listRef.value : []
  if (arr.includes(v)) return false
  listRef.value = [...arr, v]
  return true
}

function addFeatureLine() {
  if (pushUnique(editFeatures, featureAddText.value)) featureAddText.value = ''
}

function addOutLine() {
  if (pushUnique(editOut, outAddText.value)) outAddText.value = ''
}

function draftListRef(kind) {
  return ({ roles: draftRoles, entities: draftEntities, features: draftFeatures })[kind]
}

function addDraft(kind) {
  const map = {
    roles: [draftRoles, draftRoleAdd],
    entities: [draftEntities, draftEntityAdd],
    features: [draftFeatures, draftFeatureAdd],
  }
  const pair = map[kind]
  if (!pair) return
  const [listRef, addRef] = pair
  if (pushUnique(listRef, addRef.value)) {
    addRef.value = ''
    saveDrafts()
  }
}

function removeDraft(kind, index) {
  const listRef = draftListRef(kind)
  if (!listRef || !Array.isArray(listRef.value)) return
  if (draftEdit.value?.kind === kind && draftEdit.value.index === index) {
    draftEdit.value = null
  }
  listRef.value = listRef.value.filter((_, i) => i !== index)
  saveDrafts()
}

function beginDraftEdit(kind, index) {
  if (
    draftEdit.value
    && (draftEdit.value.kind !== kind || draftEdit.value.index !== index)
  ) {
    commitDraftEdit()
  }
  const listRef = draftListRef(kind)
  const cur = listRef?.value?.[index]
  if (cur == null) return
  draftEdit.value = { kind, index, text: String(cur) }
}

function cancelDraftEdit() {
  draftEdit.value = null
}

function commitDraftEdit() {
  const ed = draftEdit.value
  if (!ed) return
  const listRef = draftListRef(ed.kind)
  if (!listRef || !Array.isArray(listRef.value)) {
    draftEdit.value = null
    return
  }
  const next = String(ed.text || '').trim()
  const idx = ed.index
  draftEdit.value = null
  if (!next) {
    listRef.value = listRef.value.filter((_, i) => i !== idx)
    saveDrafts()
    return
  }
  const prev = listRef.value[idx]
  if (next === prev) return
  if (listRef.value.some((x, i) => i !== idx && x === next)) {
    message.warning('已有相同项')
    return
  }
  const copy = [...listRef.value]
  copy[idx] = next
  listRef.value = copy
  saveDrafts()
}

function onDraftPointerDown(e) {
  if (!draftEdit.value) return
  const el = e.target
  if (el?.closest?.('.ta-draft-edit-wrap')) return
  commitDraftEdit()
}

function onDraftDocKeydown(e) {
  if (!draftEdit.value) return
  if (e.key === 'Escape') {
    e.preventDefault()
    cancelDraftEdit()
  }
}

watch(draftEdit, async (v) => {
  if (!v) return
  await nextTick()
  document.querySelector('.ta-draft-edit-wrap input')?.focus?.()
})

function refillDraftsFromExtract() {
  // 恢复为服务端当前草稿（LLM/弱抽结果），禁止前端再掐「××管理」发明实体
  const d = detail.value || {}
  draftRoles.value = Array.isArray(d.draft_roles) ? [...d.draft_roles] : []
  draftEntities.value = Array.isArray(d.draft_entities) ? [...d.draft_entities] : []
  draftFeatures.value = Array.isArray(d.draft_features) ? [...d.draft_features] : []
  draftEdit.value = null
  saveDrafts()
  message.success('已恢复为当前抽取')
}

function statusLabel(v) {
  return (
    {
      extracting: '抽取中',
      review: '待核对',
      stored: '已抽取',
      fed: '已复制给助手',
      covered: '已齐',
      patched: '已处理',
    }[v] || v
  )
}

function looksLikeTocTitle(t) {
  const s = String(t || '').trim()
  if (!s) return true
  if (/^\d+(\.\d+)+\s*\S/.test(s)) return true
  if (/^第[一二三四五六七八九十百零〇\d]+[章节部分]/.test(s)) return true
  return false
}

function fileDisplayName(row) {
  const file = (row?.source_files || [])[0] || ''
  if (!file) return ''
  const stem = String(file).replace(/\.[^.]+$/, '')
  // 学号-姓名-题名.pdf → 题名
  const parts = stem.split('-')
  if (parts.length >= 3 && /^\d{6,}$/.test(parts[0])) {
    return parts.slice(2).join('-')
  }
  return stem
}

function displayTitle(row) {
  const t = row?.proposal?.title || ''
  if (t && !looksLikeTocTitle(t)) return t
  return fileDisplayName(row) || t || `记录 #${row?.id || ''}`
}

/** overlaps 条目：title/source_files 在顶层，不是 proposal 下 */
function overlapPeerLabel(ov) {
  const t = String(ov?.title || '').trim()
  if (t && !looksLikeTocTitle(t)) return t
  return fileDisplayName(ov) || t || `记录 #${ov?.id || ''}`
}

function shortTime(iso) {
  if (!iso) return '—'
  return String(iso).replace('T', ' ').slice(0, 16)
}

function shortHash(h) {
  if (!h) return '—'
  return `${String(h).slice(0, 10)}…`
}

async function reload() {
  loading.value = true
  try {
    const res = await api.thesisAbsorbList({
      q: q.value || undefined,
    })
    items.value = Array.isArray(res?.items) ? res.items : []
    page.value = 1
    hydrateExtractingJobs(items.value)
  } catch {
    items.value = Array.isArray(items.value) ? items.value : []
  } finally {
    loading.value = false
    booted.value = true
  }
}

function setFilter(mode) {
  filterMode.value = mode || 'all'
  page.value = 1
}

const onSearch = debounce(() => {
  page.value = 1
  reload()
}, 280)

function absorbJobMeta(job) {
  return `1 份终稿 · ${absorbUploadJobPhaseLabel(job)}`
}

const jobBarColor = uploadJobBarColor

/** 从列表取任务代理，避免改 plain 对象导致进度条不刷新 */
function findUploadJob(id) {
  const list = Array.isArray(uploadJobs.value) ? uploadJobs.value : []
  return list.find((j) => j.id === id) || null
}

function clearJobTimers(job) {
  if (job?.tick) {
    clearInterval(job.tick)
    job.tick = null
  }
  if (job?.fallbackTick) {
    clearTimeout(job.fallbackTick)
    job.fallbackTick = null
  }
  if (job?.pollTick) {
    clearTimeout(job.pollTick)
    job.pollTick = null
  }
}

function absorbExtractStartedAtMs(item) {
  const iso = item?.updated_at || item?.created_at
  if (!iso) return Date.now()
  const t = Date.parse(iso)
  return Number.isFinite(t) ? t : Date.now()
}

function trackExtractingJob(item) {
  if (!item || item.status !== 'extracting') return
  const recordId = item.public_id || item.id
  if (!recordId) return
  const fromMs = absorbExtractStartedAtMs(item)
  const existing = uploadJobList.value.find(
    (j) => String(j.recordId) === String(recordId) || String(j.recordId) === String(item.id),
  )
  if (existing) {
    // 续盯：沿用服务端开始时刻，禁止把已跑时长清零
    startExtractWait(existing.id, { fromMs, keepStartedAt: true })
    pollAbsorbExtract(existing.id)
    return
  }
  const jobId = `ta-poll-${recordId}`
  const name = (Array.isArray(item.source_files) && item.source_files[0]) || '终稿'
  const elapsedSec = Math.max(0, Math.floor((Date.now() - fromMs) / 1000))
  uploadJobs.value = [
    ...uploadJobList.value,
    {
      id: jobId,
      name,
      status: 'uploading',
      pct: 0,
      elapsedSec,
      startedAt: fromMs,
      recordId,
      error: '',
      tick: null,
      fallbackTick: null,
      pollTick: null,
    },
  ]
  startExtractWait(jobId, { fromMs })
  pollAbsorbExtract(jobId)
}

function hydrateExtractingJobs(list) {
  const rows = Array.isArray(list) ? list : []
  for (const item of rows) {
    if (item?.status === 'extracting') trackExtractingJob(item)
  }
}

async function pollAbsorbExtract(jobId) {
  const job = findUploadJob(jobId)
  if (!job?.recordId) return
  if (job.pollTick) {
    clearTimeout(job.pollTick)
    job.pollTick = null
  }
  try {
    const res = await api.thesisAbsorbGet(job.recordId, { poll: true })
    const item = res?.item
    if (!item) return
    if (item.status === 'extracting') {
      job.pollTick = setTimeout(() => pollAbsorbExtract(jobId), 2500)
      return
    }
    clearJobTimers(job)
    const failed = Array.isArray(item.warnings)
      && item.warnings.some((w) => String(w).startsWith('extract_fail:'))
    if (failed && item.status === 'review' && !(item.feature_line_count > 0)) {
      job.status = 'error'
      job.pct = 100
      job.error = '抽取失败'
      await reload()
      return
    }
    job.status = 'done'
    job.pct = 100
    message.success('已抽取')
    try {
      await reload()
    } catch {
      /* ignore */
    }
    if (!detailId.value) {
      dismissJob(job.id)
      openDetail(job.recordId)
    } else {
      scheduleUploadJobAutoDismiss(job, dismissJob)
      if (String(detailId.value) === String(job.recordId)
        || String(detail.value?.id) === String(item.id)) {
        detail.value = item
        syncEditors()
      }
    }
  } catch {
    const cur = findUploadJob(jobId)
    if (!cur || cur.status !== 'extracting') return
    cur.pollTick = setTimeout(() => pollAbsorbExtract(jobId), 3000)
  }
}

function startExtractWait(jobOrId, opts = {}) {
  const id = typeof jobOrId === 'string' ? jobOrId : jobOrId?.id
  const job = findUploadJob(id)
  if (!job) return
  const fromMs = Number(opts.fromMs)
  const keep = Boolean(opts.keepStartedAt)
  if (Number.isFinite(fromMs) && fromMs > 0) {
    // 续传 / hydrate：锚服务端进入抽取的时刻
    if (!keep || !job.startedAt || fromMs < job.startedAt) job.startedAt = fromMs
  } else if (job.status !== 'extracting' || !job.startedAt) {
    job.startedAt = Date.now()
  }
  job.status = 'extracting'
  job.elapsedSec = Math.max(0, Math.floor((Date.now() - job.startedAt) / 1000))
  if (job.tick) clearInterval(job.tick)
  job.tick = setInterval(() => {
    const cur = findUploadJob(job.id)
    if (!cur || cur.status !== 'extracting') {
      if (cur?.tick) {
        clearInterval(cur.tick)
        cur.tick = null
      }
      return
    }
    cur.elapsedSec = Math.max(0, Math.floor((Date.now() - cur.startedAt) / 1000))
  }, 1000)
}

function dismissJob(id) {
  const job = findUploadJob(id)
  cancelUploadJobAutoDismiss(job)
  clearJobTimers(job)
  const list = Array.isArray(uploadJobs.value) ? uploadJobs.value : []
  uploadJobs.value = list.filter((j) => j.id !== id)
}

function openDoneJob(job) {
  if (!job?.recordId || job.status !== 'done') return
  dismissJob(job.id)
  openDetail(job.recordId)
}

async function uploadOne(file) {
  if (!file || uploadBusy.value) return
  const jobId = `ta-${Date.now()}-${++uploadSeq}`
  const prev = Array.isArray(uploadJobs.value) ? uploadJobs.value : []
  uploadJobs.value = [
    ...prev,
    {
      id: jobId,
      name: file.name || '终稿',
      status: 'uploading',
      pct: 0,
      elapsedSec: 0,
      startedAt: 0,
      recordId: null,
      error: '',
      tick: null,
      fallbackTick: null,
    },
  ]
  // 无上传进度事件时：很快切到走动条抽取态，避免空进度条
  const seeded = findUploadJob(jobId)
  if (seeded) {
    seeded.fallbackTick = setTimeout(() => {
      const j = findUploadJob(jobId)
      if (!j) return
      j.fallbackTick = null
      if (j.status === 'uploading') startExtractWait(jobId)
    }, 800)
  }
  try {
    const res = await api.thesisAbsorbUpload(file, (e) => {
      const j = findUploadJob(jobId)
      if (!j || !e?.total) return
      if (j.fallbackTick) {
        clearTimeout(j.fallbackTick)
        j.fallbackTick = null
      }
      j.pct = Math.min(100, Math.round((e.loaded / e.total) * 100))
      if (e.loaded >= e.total) startExtractWait(jobId)
    })
    const job = findUploadJob(jobId)
    if (!job) return
    if (job.fallbackTick) {
      clearTimeout(job.fallbackTick)
      job.fallbackTick = null
    }
    job.recordId = res?.item?.public_id || res?.item?.id || null
    const st = res?.item?.status
    if (st === 'extracting' || res?.extract_queued) {
      startExtractWait(jobId)
      message.success(res?.message || '已接收，抽取中')
      // 抽取中不立刻全表 reload（会 kick+叠轮询）；本条先塞进列表，抽完再 reload
      const row = res?.item
      if (row?.id || row?.public_id) {
        const list = Array.isArray(items.value) ? items.value : []
        const hit = list.some(
          (x) =>
            (row.id != null && x.id === row.id)
            || (row.public_id && x.public_id === row.public_id),
        )
        if (!hit) items.value = [row, ...list]
      }
      pollAbsorbExtract(jobId)
      return
    }
    clearJobTimers(job)
    job.status = 'done'
    job.pct = 100
    message.success(res?.message || '已抽取')
    try {
      await reload()
    } catch {
      /* ignore */
    }
    if (job.recordId) {
      dismissJob(job.id)
      openDetail(job.recordId)
    } else {
      scheduleUploadJobAutoDismiss(job, dismissJob)
    }
  } catch (e) {
    const job = findUploadJob(jobId)
    if (!job) return
    clearJobTimers(job)
    job.status = 'error'
    job.pct = 100
    const detail = e?.response?.data?.detail
    job.error =
      (typeof detail === 'string' && detail)
      || e?.message
      || '上传失败'
  }
}

function onFileChange(ev) {
  const f = ev.target.files?.[0]
  ev.target.value = ''
  uploadOne(f)
}

function onDrop(ev) {
  dragover.value = false
  uploadOne(ev.dataTransfer?.files?.[0])
}

function openDetail(idOrRow) {
  if (idOrRow && typeof idOrRow === 'object' && idOrRow.status === 'extracting') {
    message.info('抽取中')
    return
  }
  let key = idOrRow
  if (idOrRow && typeof idOrRow === 'object') {
    key = idOrRow.public_id || idOrRow.id
  }
  router.push(`/thesis-absorb/${key}`)
}

function closeDetail() {
  detail.value = null
  machineUnlocked.value = false
  draftEdit.value = null
  router.push('/thesis-absorb')
}

let detailExtractTick = null

function clearDetailExtractPoll() {
  if (detailExtractTick) {
    clearTimeout(detailExtractTick)
    detailExtractTick = null
  }
}

function scheduleDetailExtractPoll() {
  clearDetailExtractPoll()
  if (!detailId.value || detail.value?.status !== 'extracting') return
  detailExtractTick = setTimeout(async () => {
    detailExtractTick = null
    if (!detailId.value) return
    try {
      const res = await api.thesisAbsorbGet(detailId.value, { poll: true })
      const item = res?.item
      if (!item) return
      detail.value = item
      if (item.status === 'extracting') {
        scheduleDetailExtractPoll()
        return
      }
      // 抽完再拉完整详情（重叠/喂稿）
      await loadDetail()
      message.success('已抽取')
      await reload()
    } catch {
      scheduleDetailExtractPoll()
    }
  }, 2000)
}

async function loadDetail() {
  clearDetailExtractPoll()
  if (!detailId.value) {
    detail.value = null
    return
  }
  detailLoading.value = true
  machineUnlocked.value = false
  draftEdit.value = null
  try {
    const res = await api.thesisAbsorbGet(detailId.value)
    detail.value = res?.item || null
    syncEditors()
    if (detail.value?.status === 'extracting') scheduleDetailExtractPoll()
  } catch {
    detail.value = null
  } finally {
    detailLoading.value = false
  }
}

function toggleMachineUnlock() {
  if (machineUnlocked.value) {
    machineUnlocked.value = false
    draftEdit.value = null
    syncEditors()
    message.success('已重新锁定')
    return
  }
  syncEditors()
  machineUnlocked.value = true
  message.success('已解锁，可改要点 / 覆盖 / 补齐')
}

function syncEditors() {
  const d = detail.value
  if (!d) return
  const draftFeats = Array.isArray(d.draft_features) ? d.draft_features : []
  const feats = draftFeats.length
    ? draftFeats
    : (Array.isArray(d.proposal?.feature_lines) ? d.proposal.feature_lines : [])
  const outs = Array.isArray(d.proposal?.out_scope_lines) ? d.proposal.out_scope_lines : []
  editFeatures.value = feats.map((s) => String(s).trim()).filter(Boolean)
  editOut.value = outs.map((s) => String(s).trim()).filter(Boolean)
  featureAddText.value = ''
  outAddText.value = ''
  coverageNote.value = d.coverage_note || ''
  draftRoles.value = (Array.isArray(d.draft_roles) ? d.draft_roles : [])
    .map((s) => String(s).trim())
    .filter(Boolean)
  draftEntities.value = (Array.isArray(d.draft_entities) ? d.draft_entities : [])
    .map((s) => String(s).trim())
    .filter(Boolean)
  draftFeatures.value = (Array.isArray(d.draft_features) ? d.draft_features : [])
    .map((s) => String(s).trim())
    .filter(Boolean)
  draftRoleAdd.value = ''
  draftEntityAdd.value = ''
  draftFeatureAdd.value = ''
}

async function doReextract() {
  if (!detailId.value) return
  reextracting.value = true
  try {
    const res = await api.thesisAbsorbReextract(detailId.value)
    detail.value = res.item
    syncEditors()
    if (res.item?.status === 'extracting' || res?.extract_queued) {
      message.success(res?.message || '重抽中')
      trackExtractingJob(res.item)
      return
    }
    if (res.item?.same_material_stable) message.info('与上次一致')
    else if (res.item?.extractor_bumped) message.warning('抽取规则已更新')
    else message.success('已重抽')
  } catch (e) {
    const detail = e?.response?.data?.detail
    message.error(
      (typeof detail === 'string' && detail) || e?.message || '重抽失败',
    )
  } finally {
    reextracting.value = false
  }
}

async function saveStructure() {
  if (!detailId.value) return
  saving.value = true
  try {
    const feats = (Array.isArray(editFeatures.value) ? editFeatures.value : [])
      .map((s) => String(s).trim())
      .filter(Boolean)
    const proposal = {
      ...(detail.value?.proposal || {}),
      feature_lines: feats,
      out_scope_lines: (Array.isArray(editOut.value) ? editOut.value : [])
        .map((s) => String(s).trim())
        .filter(Boolean),
    }
    const res = await api.thesisAbsorbPatch(detailId.value, {
      proposal,
      draft_features: feats,
    })
    detail.value = res.item
    machineUnlocked.value = false
    draftEdit.value = null
    syncEditors()
    message.success('要点已保存并锁定')
  } finally {
    saving.value = false
  }
}

async function onCoverage(v) {
  if (!detailId.value || !machineUnlocked.value) return
  const res = await api.thesisAbsorbPatch(detailId.value, { coverage: v })
  detail.value = res.item
  syncEditors()
}

async function saveCoverageNote() {
  if (!detailId.value || !machineUnlocked.value) return
  const res = await api.thesisAbsorbPatch(detailId.value, {
    coverage_note: coverageNote.value,
  })
  detail.value = res.item
}

async function saveDrafts() {
  if (!detailId.value) return
  const clean = (arr) =>
    (Array.isArray(arr) ? arr : []).map((s) => String(s).trim()).filter(Boolean)
  const res = await api.thesisAbsorbPatch(detailId.value, {
    draft_roles: clean(draftRoles.value),
    draft_entities: clean(draftEntities.value),
    draft_features: clean(draftFeatures.value),
  })
  detail.value = res.item
  // 增删改即时落库，保持解锁直到点「重新锁定」或「保存要点」
}

async function copyText(text) {
  try {
    await copyMaterialText(text || '')
    message.success('已复制')
  } catch {
    message.error('复制失败')
  }
}

async function copyFeed(id) {
  feedBusy.value = id
  try {
    const res = await api.thesisAbsorbFeed(id)
    const md = res.feed_markdown || res.item?.feed_markdown || ''
    await copyMaterialText(md)
    message.success('已复制给助手')
    if (detailId.value === id) {
      detail.value = res.item
      syncEditors()
    }
  } catch {
    message.error('复制失败')
  } finally {
    feedBusy.value = null
  }
}

async function markPatched() {
  if (!detailId.value) return
  const res = await api.thesisAbsorbPatch(detailId.value, { status: 'patched' })
  detail.value = res.item
  message.success('已标记处理')
}

async function confirmTrial() {
  const ok = await confirm(
    '下载开题草稿并打开项目页（非正式建项）。',
    {
      title: '试匹配',
      positiveText: '下载并打开项目页',
      negativeText: '取消',
    },
  )
  if (!ok) return
  const draft = detail.value?.opening_draft || ''
  const blob = new Blob([draft], { type: 'text/plain;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `thesis-absorb-${detail.value?.id || 'draft'}-opening.txt`
  a.click()
  URL.revokeObjectURL(a.href)
  router.push('/projects')
}

async function doDelete() {
  if (!detailId.value) return
  const ok = await confirm('确定删除这条终稿？删除后不可恢复。', {
    title: '删除终稿',
    positiveText: '删除',
    negativeText: '取消',
    type: 'error',
  })
  if (!ok) return
  await api.thesisAbsorbDelete(detailId.value)
  message.success('已删除')
  closeDetail()
  await reload()
}

watch(detailId, () => {
  loadDetail()
})

onMounted(async () => {
  document.addEventListener('pointerdown', onDraftPointerDown, true)
  document.addEventListener('keydown', onDraftDocKeydown)
  await reload()
  if (detailId.value) await loadDetail()
})

onUnmounted(() => {
  document.removeEventListener('pointerdown', onDraftPointerDown, true)
  document.removeEventListener('keydown', onDraftDocKeydown)
  clearDetailExtractPoll()
  for (const j of uploadJobList.value) {
    cancelUploadJobAutoDismiss(j)
    clearJobTimers(j)
  }
})
</script>

<style scoped>
.dropzone.disabled {
  opacity: 0.55;
  pointer-events: none;
}
.ta-alert {
  background: var(--banner-warn-bg, rgba(194, 120, 3, 0.1));
  border: 1px solid var(--banner-warn-line, rgba(194, 120, 3, 0.32));
  padding: 10px 12px;
  border-radius: var(--radius, 6px);
  font-size: 13px;
  color: var(--ink);
}
/* 相近记录：只提示不挡；中性信息态，勿跟 warn 黄条混 */
.ta-alert.info {
  background: var(--panel-quiet-bg, rgba(120, 130, 145, 0.1));
  border-color: var(--line, rgba(120, 130, 145, 0.28));
}
.ta-id-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 8px 16px;
  font-size: 13px;
}
.ta-k {
  display: inline-block;
  min-width: 52px;
  color: var(--muted, #888);
  margin-right: 6px;
}
.ta-section-label {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 6px;
}
.ta-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 8px;
  align-items: flex-start;
}
.ta-feat-pill {
  height: auto;
  min-height: 22px;
  max-width: 100%;
  padding: 3px 8px;
  white-space: normal;
  word-break: break-word;
  font-weight: 500;
  gap: 6px;
  line-height: 1.35;
}
.ta-feat-x {
  appearance: none;
  border: 0;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
  font-size: 14px;
  line-height: 1;
  padding: 0;
  margin: 0;
}
.ta-feat-x:hover {
  color: var(--ink);
}
.ta-feat-pill--edit {
  cursor: pointer;
}
.ta-locked {
  opacity: 0.92;
}
.ta-locked .ta-feat-pill {
  cursor: default;
}
.ta-coverage-hints-hd {
  font-size: 13px;
  font-weight: 600;
}
.ta-coverage-hints-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.ta-coverage-hint-item {
  padding: 8px 10px;
  border: 1px solid var(--panel-border, rgba(0, 0, 0, 0.06));
  border-radius: 6px;
  background: var(--panel-quiet-bg, rgba(0, 0, 0, 0.02));
}
.ta-coverage-hint-title {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  align-items: baseline;
  margin-bottom: 2px;
}
.ta-feed-grid {
  align-items: start;
}
.ta-feed-grid > .panel-quiet {
  min-width: 0;
}
.ta-pair-pre {
  max-height: 320px;
  margin: 0;
}
.ta-draft-grid {
  gap: 16px 20px;
}
.ta-draft-col {
  min-width: 0;
}
@media (max-width: 900px) {
  .ta-draft-grid {
    grid-template-columns: 1fr;
  }
}
.ta-draft-col .ta-add-row {
  max-width: none;
}
.ta-feat-pill--edit {
  cursor: text;
}
.ta-draft-edit-wrap {
  display: inline-flex;
  align-items: center;
  max-width: 12em;
  vertical-align: middle;
}
.ta-draft-edit {
  width: 12em;
  max-width: 100%;
}
.ta-add-row {
  display: flex;
  gap: 8px;
  align-items: center;
  max-width: 420px;
}
.ta-add-row .n-input {
  flex: 1;
  min-width: 0;
}
.ta-sec-block {
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--panel-border, rgba(0, 0, 0, 0.06));
}
.ta-sec-block:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}
.ta-sec-h {
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 2px;
}
.ta-sec-lines {
  line-height: 1.5;
  word-break: break-word;
}
.mt-8 {
  margin-top: 8px;
}
.mt-12 {
  margin-top: 12px;
}
.mt-16 {
  margin-top: 16px;
}
.mb-8 {
  margin-bottom: 8px;
}
.mb-12 {
  margin-bottom: 12px;
}
.mb-16 {
  margin-bottom: 16px;
}
.small {
  font-size: 12px;
}
.mono {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
</style>
