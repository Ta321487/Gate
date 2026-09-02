<template>
  <div>
    <div class="panel artifacts-files">
      <div class="panel-hd">
        <h3>产物</h3>
        <span class="small muted">交付文件与工作区路径</span>
      </div>
      <div class="panel-bd artifacts-file-grid">
        <div class="file-row" style="margin:0">
          <div class="file-row-main">
            <strong>{{ zipFileName }}</strong>
            <span class="small muted">{{ zipLockHint }}</span>
          </div>
          <n-button size="small" :disabled="!canDownload" :title="downloadBlockedReason" @click="downloadZip">
            {{ canDownload ? '下载' : '锁定' }}
          </n-button>
        </div>
        <div class="file-row" style="margin:0">
          <div class="file-row-main">
            <strong>工程目录</strong>
            <span class="small muted mono file-path">{{ p.workspace_path || '尚未生成' }}</span>
          </div>
          <CopyIconButton v-if="p.workspace_path" :text="p.workspace_path" tip="复制路径" />
        </div>
        <div class="file-row" style="margin:0">
          <div class="file-row-main">
            <strong>填岛拆解计划</strong>
            <span class="small muted">{{ fillPlanHint }}</span>
          </div>
          <span
            class="btn-tip-wrap"
            :title="p.workspace_path ? '只预览 Unit 拆解，不调大模型、不执行填岛' : '生成工作区后可预览填岛拆解'"
          >
            <n-button text size="small" :disabled="!p.workspace_path" :loading="fillPlanLoading" @click="openFillPlan">
              查看
            </n-button>
          </span>
        </div>
        <div class="file-row" style="margin:0">
          <div class="file-row-main">
            <strong>生成配置</strong>
            <span class="small muted">匹配与生成参数</span>
          </div>
          <div class="row" style="margin:0;gap:6px">
            <CopyIconButton :text="specText" tip="复制配置" />
            <n-button text size="small" @click="showSpec = true">查看</n-button>
          </div>
        </div>
        <DefensePptArtifactRow />
      </div>
    </div>

    <div class="panel mt-16">
      <div class="panel-hd">
        <h3>对照视图</h3>
        <span class="small muted">
          {{ artifactsFrozen ? '工程重新生成中 · 导出类操作暂不可用' : '库表 · 论文材料 · 交付复审 · 质量检查 · 答辩 PPT · 仅运营端验收' }}
        </span>
      </div>
      <div class="panel-bd" style="padding-top:4px">
        <n-tabs v-model:value="artifactView" type="line" size="small" @update:value="onArtifactView">
          <n-tab-pane name="db" tab="数据库">
            <div class="artifact-pane stack">
              <p v-if="artifactLoading" class="small muted">加载中…</p>
              <div class="row" style="justify-content:space-between;align-items:center;gap:12px">
                <div class="small">
                  <span class="muted">库名</span> · <span class="mono">{{ p.db_name || '—' }}</span>
                  <CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" />
                  <span class="pill" :class="schema ? 'pill-green' : 'pill-neutral'" style="margin-left:8px">
                    {{ schema ? '已解析' : (p.workspace_path ? (artifactLoading ? '加载中' : '暂无表结构') : '未生成') }}
                  </span>
                </div>
                <div class="row" style="margin:0;gap:8px">
                  <label v-if="schema?.tables?.length" class="type-mode-switch small">
                    <n-switch v-model:value="typeParenMode" size="small" :disabled="artifactsFrozen" />
                    <span class="muted">{{ typeParenMode ? '类型 varchar(60)' : '类型分列 varchar | 60' }}</span>
                  </label>
                  <n-button
                    size="small"
                    :disabled="!schema?.tables?.length || artifactsFrozen"
                    :loading="erLoading"
                    :title="artifactsFrozen ? artifactsFrozenReason : undefined"
                    @click="openEr"
                  >E-R 图</n-button>
                </div>
              </div>
              <div class="small muted">数据表结构 · 建议 6～15 张表 · E-R 供「数据库设计」章节 · 中文名改完点勾或回车保存（只影响论文/E-R，不改库表英文标识）</div>
              <template v-if="schema?.tables?.length">
                <div class="small">当前 <strong>{{ schema.tables.length }}</strong> 张
                  <span :class="(schema.tables.length >= 6 && schema.tables.length <= 13) ? 'muted' : 'text-danger'">
                    （{{ schema.tables.length >= 6 && schema.tables.length <= 15 ? '符合' : '不符合' }} 6~15）
                  </span>
                  <span
                    v-if="schemaErGapCount > 0"
                    class="pill pill-amber"
                    style="margin-left:8px"
                    title="展示名仍含英文，改完点勾或回车保存"
                  >中文缺口 {{ schemaErGapCount }}</span>
                  <span v-else class="pill pill-green" style="margin-left:8px">中文名齐全</span>
                </div>
                <div class="table-list">
                  <div v-for="t in schema.tables" :key="t.name" class="table-card">
                    <div
                      class="table-card-hd"
                      :class="{ collapsed: isTableCollapsed(t.name) }"
                      role="button"
                      tabindex="0"
                      :title="isTableCollapsed(t.name) ? '展开列' : '折叠列'"
                      @click="toggleTable(t.name)"
                      @keyup.enter="toggleTable(t.name)"
                    >
                      <span class="table-caret" aria-hidden="true">{{ isTableCollapsed(t.name) ? '▸' : '▾' }}</span>
                      <span class="mono">{{ t.name }}</span>
                      <span class="zh-edit-wrap" @click.stop>
                        <input
                          class="zh-edit table-zh"
                          :class="{ 'zh-gap': labelLooksLatin(t.label || t.name) }"
                          :value="t.label || ''"
                          :placeholder="t.name"
                          :disabled="artifactsFrozen || erLabelSaving"
                          :title="artifactsFrozen ? artifactsFrozenReason : '改中文实体名'"
                          @keydown.enter.prevent="($event) => commitTableZh(t, $event.target)"
                        />
                        <button
                          type="button"
                          class="zh-ok-btn"
                          :disabled="artifactsFrozen || erLabelSaving"
                          title="保存中文名"
                          aria-label="保存中文名"
                          @mousedown.prevent
                          @click="($event) => commitTableZh(t, $event.currentTarget.previousElementSibling)"
                        >
                          <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                            <path fill="currentColor" d="M9.55 17.6 4.9 12.95l1.4-1.4 3.25 3.25 7.15-7.15 1.4 1.4z" />
                          </svg>
                        </button>
                      </span>
                      <span class="small muted">{{ t.columns?.length || 0 }} 列</span>
                      <CopyIconButton class="table-copy" :text="tableCopyText(t)" tip="复制本表（可贴 Word 转表格）" />
                    </div>
                    <ul
                      v-show="!isTableCollapsed(t.name)"
                      class="table-cols"
                      :class="{ 'split-type': !typeParenMode }"
                    >
                      <li class="table-cols-hd">
                        <span>字段名</span>
                        <span>中文名</span>
                        <span>类型</span>
                        <span v-if="!typeParenMode">长度</span>
                      </li>
                      <li v-for="c in t.columns" :key="c.name" :class="{ pk: c.pk, fk: c.fk }">
                        <span class="col-name">{{ c.name }}</span>
                        <span class="zh-edit-wrap">
                          <input
                            class="zh-edit col-zh"
                            :class="{ 'zh-gap': labelLooksLatin(c.label || c.name) }"
                            :value="c.label || ''"
                            :placeholder="c.name"
                            :disabled="artifactsFrozen || erLabelSaving"
                            :title="artifactsFrozen ? artifactsFrozenReason : '改中文属性名'"
                            @keydown.enter.prevent="($event) => commitColZh(t, c, $event.target)"
                          />
                          <button
                            type="button"
                            class="zh-ok-btn"
                            :disabled="artifactsFrozen || erLabelSaving"
                            title="保存中文名"
                            aria-label="保存中文名"
                            @mousedown.prevent
                            @click="($event) => commitColZh(t, c, $event.currentTarget.previousElementSibling)"
                          >
                            <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                              <path fill="currentColor" d="M9.55 17.6 4.9 12.95l1.4-1.4 3.25 3.25 7.15-7.15 1.4 1.4z" />
                            </svg>
                          </button>
                        </span>
                        <template v-if="typeParenMode">
                          <span class="col-type muted">{{ parseMysqlType(c.type).full }}</span>
                        </template>
                        <template v-else>
                          <span class="col-type muted">{{ parseMysqlType(c.type).base }}</span>
                          <span class="col-len muted">{{ parseMysqlType(c.type).len || '—' }}</span>
                        </template>
                      </li>
                    </ul>
                  </div>
                </div>
                <div v-if="schema.relations?.length" class="rel-list">
                  <div class="parse-sec-hd">推断联系</div>
                  <div v-for="(r, i) in schema.relations" :key="i" class="rel-row">
                    <span class="mono">{{ r.left }}</span>
                    <span class="muted">{{ r.card_left }}</span>
                    —〈
                    <span class="zh-edit-wrap zh-edit-wrap--rel">
                      <input
                        class="zh-edit rel-zh"
                        :class="{ 'zh-gap': labelLooksLatin(r.label || r.name) }"
                        :value="r.label || r.name || ''"
                        :placeholder="r.name"
                        :disabled="artifactsFrozen || erLabelSaving"
                        :title="artifactsFrozen ? artifactsFrozenReason : '改中文联系名'"
                        @keydown.enter.prevent="($event) => commitRelZh(r, $event.target)"
                      />
                      <button
                        type="button"
                        class="zh-ok-btn"
                        :disabled="artifactsFrozen || erLabelSaving"
                        title="保存中文名"
                        aria-label="保存中文名"
                        @mousedown.prevent
                        @click="($event) => commitRelZh(r, $event.currentTarget.previousElementSibling)"
                      >
                        <svg viewBox="0 0 24 24" width="12" height="12" aria-hidden="true">
                          <path fill="currentColor" d="M9.55 17.6 4.9 12.95l1.4-1.4 3.25 3.25 7.15-7.15 1.4 1.4z" />
                        </svg>
                      </button>
                    </span>
                    〉—
                    <span class="muted">{{ r.card_right }}</span>
                    <span class="mono">{{ r.right }}</span>
                    <span class="small muted">via {{ r.via }}</span>
                  </div>
                </div>
              </template>
              <p v-else class="small muted">生成工作区后可查看表结构与 E-R 图。</p>
            </div>

          </n-tab-pane>

          <n-tab-pane name="thesis" tab="论文材料">
            <div class="artifact-pane stack">
              <p v-if="artifactLoading" class="small muted">加载中…</p>
              <p class="small muted mb-8">
                贴说明书用：功能模块图（系统设计）· 软件测试用例（系统测试）。均按交付菜单推导，不发明功能。
              </p>
              <div class="thesis-cards">
                <div class="thesis-card">
                  <div class="thesis-card-hd">
                    <strong>功能模块图</strong>
                    <span
                      class="pill"
                      :class="artifactsFrozen ? 'pill-amber' : (modulesOk ? 'pill-green' : 'pill-neutral')"
                    >
                      {{
                        artifactsFrozen
                          ? '生成中'
                          : (modulesOk ? '可导出' : (p.workspace_path ? '待生成' : '未生成'))
                      }}
                    </span>
                  </div>
                  <p class="small muted">按业务 / 按端切换 · 黑白线框 · 复制 PNG 或下载矢量</p>
                  <n-button
                    size="small"
                    type="primary"
                    :disabled="!modulesOk || artifactsFrozen"
                    :loading="modLoading"
                    :title="artifactsFrozen ? artifactsFrozenReason : undefined"
                    @click="openModules"
                  >打开模块图</n-button>
                </div>
                <div class="thesis-card">
                  <div class="thesis-card-hd">
                    <strong>软件测试用例</strong>
                    <span
                      class="pill"
                      :class="artifactsFrozen ? 'pill-amber' : (modulesOk ? 'pill-green' : 'pill-neutral')"
                    >
                      {{
                        artifactsFrozen
                          ? '生成中'
                          : (modulesOk ? '可导出' : (p.workspace_path ? '待生成' : '未生成'))
                      }}
                    </span>
                  </div>
                  <p class="small muted">5～9 字段模板可选（默认 6）· 复制表格 / Markdown</p>
                  <n-button
                    size="small"
                    type="primary"
                    :disabled="!modulesOk || artifactsFrozen"
                    :loading="tcLoading"
                    :title="artifactsFrozen ? artifactsFrozenReason : undefined"
                    @click="openTestcases"
                  >打开测试用例</n-button>
                </div>
              </div>
            </div>

          </n-tab-pane>

          <n-tab-pane name="api" tab="学生端 API">
            <div class="artifact-pane stack">
              <p v-if="artifactLoading" class="small muted">加载中…</p>
              <div class="row" style="justify-content:space-between;align-items:center;gap:12px">
                <div class="small">
                  <template v-if="apis">
                    <strong>{{ apis.count }}</strong> 条 ·
                    <span class="muted">{{ apis.controller_count }} 个接口模块</span>
                    <span v-if="apis.flow_marked" class="pill pill-green" style="margin-left:8px">
                      主流程 {{ apis.flow_marked }}
                    </span>
                  </template>
                  <span v-else class="pill pill-neutral">{{ p.workspace_path ? (artifactLoading ? '加载中' : '暂无接口清单') : '未生成' }}</span>
                </div>
                <div class="row" style="margin:0;gap:8px">
                  <span
                    class="btn-tip-wrap"
                    :title="apis && p.workspace_path ? '对已启动预览跑主路径探测，不启停进程' : '需有工作区与接口清单；预览请到运行页启动'"
                  >
                    <n-button
                      size="small"
                      type="primary"
                      :loading="apiSmokeBusy"
                      :disabled="!apis || !p.workspace_path"
                      @click="runApiSmoke"
                    >全量冒烟</n-button>
                  </span>
                  <n-input
                    v-model:value="apiQuery"
                    size="small"
                    clearable
                    placeholder="筛选路径 / 方法 / 处理函数"
                    style="width:220px"
                    :disabled="!apis"
                  />
                  <CopyIconButton
                    v-if="apiCopyText"
                    :text="apiCopyText"
                    tip="复制接口地址"
                  />
                </div>
              </div>
              <div class="small muted">
                自动扫描学生工程接口，便于对照主流程验收；仅供运营端查看，不含于交付包。
                复制为「方法 + 路径」；联调请用「运行」页的后端地址（需先登录预览）。
                「全量冒烟」按本域 flow_api 模拟页面主路径点击（可多链：借+约、收藏等），只探测已启动预览，不会自动启停；启停请到「运行」页。
                全量表「可达」= 打到学生后端；业务成败看上方「主流程」。
              </div>
              <div v-if="apiSmokeFactoryHint" class="banner fail" style="margin:0">
                <h4>工厂提示</h4>
                <p class="small">{{ apiSmokeFactoryHint }}</p>
                <div class="row mt-12">
                  <n-button size="small" type="primary" @click="tab = 'runtime'">前往运行</n-button>
                </div>
              </div>
              <div v-if="apiSmokeResult" class="stack" style="gap:10px">
                <div class="row" style="margin:0;gap:8px;flex-wrap:wrap;align-items:center">
                  <span class="pill" :class="apiSmokeResult.ok ? 'pill-green' : 'pill-red'">
                    {{ apiSmokeResult.ok ? '冒烟通过' : '冒烟未过' }}
                  </span>
                  <span class="small muted">{{ apiSmokeResult.summary }}</span>
                </div>
                <div class="row" style="margin:0;gap:8px;flex-wrap:wrap">
                  <span class="pill pill-red">学生失败 {{ apiSmokeResult.student_failures ?? 0 }}</span>
                  <span class="pill pill-amber">工厂错 {{ apiSmokeResult.factory_errors ?? 0 }}</span>
                  <span class="pill pill-neutral">跳过 {{ apiSmokeResult.skipped ?? 0 }}</span>
                </div>
                <div v-if="apiSmokeResult.main_flow?.length" class="table-list">
                  <div class="table-card">
                    <div class="table-card-hd">
                      <span>主流程</span>
                      <span class="small muted">{{ apiSmokeResult.main_flow.length }} 步</span>
                    </div>
                    <ul class="api-cols api-smoke-cols">
                      <li class="api-cols-hd">
                        <span>步骤</span>
                        <span>结果</span>
                        <span>来源</span>
                        <span>说明</span>
                      </li>
                      <li
                        v-for="(s, i) in apiSmokeResult.main_flow"
                        :key="'mf-' + i"
                        :class="smokeRowClass(s)"
                      >
                        <span class="mono">{{ s.name }}</span>
                        <span>
                          <span class="pill" :class="smokePillClass(s)">{{ smokeStatusLabel(s) }}</span>
                        </span>
                        <span class="small">{{ s.error_source || '—' }}</span>
                        <span class="small smoke-detail">{{ smokeDetailText(s) }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
                <div v-if="apiSmokeResult.endpoints?.length" class="table-list">
                  <div class="table-card">
                    <div class="table-card-hd">
                      <span>全量探测</span>
                      <span class="small muted">{{ apiSmokeResult.endpoints.length }} 条</span>
                    </div>
                    <ul class="api-cols api-smoke-cols">
                      <li class="api-cols-hd">
                        <span>方法</span>
                        <span>路径</span>
                        <span>结果</span>
                        <span>说明</span>
                      </li>
                      <li
                        v-for="(e, i) in apiSmokeResult.endpoints"
                        :key="'ep-' + i"
                        :class="smokeRowClass(e)"
                      >
                        <span class="api-method" :data-m="e.method">{{ e.method }}</span>
                        <span class="mono api-path">{{ e.filled_path || e.path }}</span>
                        <span>
                          <span class="pill" :class="smokePillClass(e)">{{ smokeStatusLabel(e) }}</span>
                          <span v-if="e.http_status" class="small muted" style="margin-left:6px">{{ e.http_status }}</span>
                        </span>
                        <span class="small smoke-detail">{{ smokeDetailText(e) }}</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
              <div v-if="apis?.api_style_notes?.length" class="small muted" style="padding:10px 12px;border:1px solid var(--border-color);border-radius:8px;line-height:1.55">
                <div style="margin-bottom:6px;color:var(--fg)">
                  <strong>本课题传参风格</strong>
                  <span v-if="apis.api_style" class="mono" style="margin-left:8px">
                    item_ref={{ apis.api_style.item_ref }} · cart_mutate={{ apis.api_style.cart_mutate }}
                  </span>
                  <span v-if="apis.style_hidden" class="pill pill-neutral" style="margin-left:8px">
                    已隐藏变体 {{ apis.style_hidden }}
                  </span>
                </div>
                <ul style="margin:0;padding-left:1.2em">
                  <li v-for="(n, i) in apis.api_style_notes" :key="i">{{ n }}</li>
                </ul>
              </div>
              <div v-if="apis?.surfaces?.length" class="api-surface-bar row" style="margin:0;gap:6px">
                <button
                  type="button"
                  class="api-chip"
                  :class="{ active: apiSurface === 'all' }"
                  @click="apiSurface = 'all'"
                >全部 {{ apis.count }}</button>
                <button
                  v-for="s in apis.surfaces"
                  :key="s.id"
                  type="button"
                  class="api-chip"
                  :class="{ active: apiSurface === s.id }"
                  @click="apiSurface = s.id"
                >{{ s.label }} {{ s.count }}</button>
              </div>
              <template v-if="filteredApiGroups.length">
                <div class="table-list">
                  <div v-for="g in filteredApiGroups" :key="g.controller" class="table-card">
                    <div
                      class="table-card-hd"
                      :class="{ collapsed: isApiCollapsed(g.controller) }"
                      role="button"
                      tabindex="0"
                      @click="toggleApi(g.controller)"
                      @keyup.enter="toggleApi(g.controller)"
                    >
                      <span class="table-caret" aria-hidden="true">{{ isApiCollapsed(g.controller) ? '▸' : '▾' }}</span>
                      <span class="mono">{{ g.controller }}</span>
                      <span v-if="g.base" class="table-zh mono">{{ g.base }}</span>
                      <span class="small muted">{{ g.endpoints.length }} 条</span>
                      <CopyIconButton
                        class="table-copy"
                        :text="apiGroupCopyText(g)"
                        tip="复制本组地址"
                      />
                    </div>
                    <ul v-show="!isApiCollapsed(g.controller)" class="api-cols">
                      <li class="api-cols-hd">
                        <span>方法</span>
                        <span>路径</span>
                        <span>处理函数</span>
                        <span>面</span>
                        <span>契约</span>
                      </li>
                      <li v-for="(ep, i) in g.endpoints" :key="i">
                        <span class="api-method" :data-m="ep.method">{{ ep.method }}</span>
                        <span class="mono api-path">{{ ep.path }}</span>
                        <span class="muted">{{ ep.handler }}</span>
                        <span class="small">{{ ep.surface_label }}</span>
                        <span>
                          <span
                            v-for="k in ep.flow_keys"
                            :key="k"
                            class="api-flow-tag"
                          >{{ k }}</span>
                          <span v-if="!ep.flow_keys?.length" class="muted">—</span>
                        </span>
                      </li>
                    </ul>
                  </div>
                </div>
              </template>
              <p v-else-if="apis" class="small muted">无匹配接口，试试清空筛选。</p>
              <p v-else class="small muted">生成完成后可在此对照学生端接口清单。</p>
            </div>

          </n-tab-pane>

          <n-tab-pane name="review" tab="交付复审">
            <div class="artifact-pane">
              <DeliveryReviewPane
                :project-id="p.id"
                :delivery-review="p.delivery_review || {}"
                :disabled="artifactsFrozen || !p.workspace_path"
                :reload="load"
              />
            </div>

          </n-tab-pane>

          <n-tab-pane name="gates" tab="质量检查">
            <div class="artifact-pane stack">
              <div class="row" style="justify-content:space-between;align-items:center">
                <div class="small">
                  质量检查 · 下载条件
                  <span class="pill" :class="canDownload ? 'pill-green' : 'pill-red'" style="margin-left:8px">
                    {{ canDownload ? '可下载' : '暂不可下载' }}
                  </span>
                </div>
              </div>
              <p class="small muted" style="margin:0">
                机器质检未通过时不可下载。工程变更后请在「交付复审」验圈并合卷。人工履约标记在页头操作。
              </p>
              <n-data-table :columns="gateCols" :data="gateRows" :bordered="false" size="small" />
              <div class="parse-sec-hd mt-12">清单实装验收</div>
              <p class="small muted" style="margin:0 0 8px">
                扫描已生成工程，核对 Spec 清单各项是否在 ZIP 中有对应路由/实现（与生成前「措辞核对」不是同一检查）。
              </p>
              <n-data-table :columns="checkCols" :data="checkRows" :bordered="false" size="small" />
            </div>
          </n-tab-pane>

          <n-tab-pane name="ppt" tab="答辩 PPT">
            <DefensePptComparePane />
          </n-tab-pane>
        </n-tabs>
      </div>
    </div>
  </div>
</template>

<script setup>
import { bindPd } from './bindPd'
import CopyIconButton from '../../components/CopyIconButton.vue'
import DeliveryReviewPane from '../../components/DeliveryReviewPane.vue'
import DefensePptArtifactRow from '../../components/defensePpt/DefensePptArtifactRow.vue'
import DefensePptComparePane from '../../components/defensePpt/DefensePptComparePane.vue'
const {
  FILL_UNIT_KIND_ZH, FILL_UNIT_STATUS_ZH, PORTAL_HOME_FALLBACK, TYPE_PAREN_KEY, _runtimeSettled, _tailLines, ack, ackMainPath,
  alreadyBaked, apiCopyText, apiGroupCopyText, apiQuery, apiSmokeBusy, apiSmokeFactoryHint, apiSmokeResult, apiSurface,
  apis, applyFillSnapshot, archDomainDeviant, archOptions, artifactLoading, artifactView, artifactsFrozen, artifactsFrozenReason,
  authEntryDisplay, backendAddr, canDownload, canDownloadAndDeliver, canMarkDelivered, canMarkReady, canUndoDelivery, cancelCurrent,
  catalog, checkCols, checkRows, chromeOptions, collapsedApis, collapsedTables, commitColZh, commitRelZh,
  commitTableZh, confirmDelete, confirmHint, confirmMatch, confirmPreGenerate, currentJob, deleteBlocked,
  deleteBlockedReason, deleting, deliveryBusy, deliveryMark, deviant, displayConf, domCascaderOptions, downloadAndDeliver,
  downloadBlockedReason, downloadZip, downloadZipLabel, entryOptions, erDownloadBase, erEntity, erEntityOptions, erLabelSaving,
  erLayoutKey, erLoading, erMode, erSvgSource, failedBannerTitle, fetchErSvg, fetchModSvg, fillEventSource,
  fillLiveCols, fillLiveRows, fillLiveSnap, fillLiveSummary, fillLiveVisible, fillPlanCols, fillPlanHint,
  fillPlanLoading, fillPlanRows, filteredApiGroups, filteredLog, form, formatSize, frontendAddr, gateCols,
  gateRows, genState, genSuccessBannerHint, genSuccessBannerTitle, goArtifacts, isApiCollapsed, isTableCollapsed, jobActing,
  jobInFlight, keepDb, keywordHits, labelLooksLatin, layoutOptions, llmOptions, load, loadApis,
  loadArtifactView, loadError, loadErrorCode, loadLog, loadSchema, logFilter, logLoading, logReqSeq,
  logSide, logSides, logText, markDelivery, matchAltsText, matchBusy, matchMeta, matchPath,
  matchPillClass, matchPillText, matchSourceLabel, matchWarnings, modDownloadBase, modLayoutKey, modLoading, modSvgSource,
  modulesLayout, modulesMeta, modulesOk, narrativeDualText, normalizeStepStatus, onArchDomChange, onArtifactView, onDelete,
  onErEntity, onErMode, onModulesLayout, onPathChange, onTcFields, openEr, openFillPlan, openModules,
  openPreview, openTestcases, p, parseMysqlType, passwordHashOptions, pathEntryDeviant, pathSceneDeviant, persistenceDeviant,
  persistenceLabel, persistenceOptions, planSteps, pollFailStreak, pollInFlight, pollSyncHint, pollTimer, portalHomeOptions,
  preGenBusy, preGenReady, preGenStackWarnings, preGenTechDual, proposal, proposalDiff, putErLabelPatch, recommendedArchesText,
  refreshJob, refreshRuntime, reload, reloadErSvg, reloadModSvg, reloadTestcases, resetMatch, retryCurrent,
  roleSpecText, route, router, rt, rtAction, rtAllBusy, rtAnyBusy, rtAnyLive,
  rtBeLive, rtBothLive, rtBusyBe, rtBusyFe, rtCanRestartAll, rtCanStartAll, rtCanStopAll, rtFeLive,
  rtGenerating, rtPendingAll, rtStartBlockedReason, runApiSmoke, runGenerateJob, runtimeCanStop, runtimeLogView, runtimeStatusLabel,
  runtimeStatusPill, runtimeTransient, saveSoft, sceneOptions, schema, schemaErGapCount, securityDeviant, securityLabel,
  securityOn, securityOptions, showDelete, showEr, showFillPlan, showJobSteps, showModules, showPreGenerate,
  showSoftBakePanel, showSpec, showTestcases, smokeDetailFromAxios, smokeDetailText, smokePillClass, smokeRowClass, smokeStatusLabel,
  softApplying, softBakeHint, softSaving, softThemeWireStyle, softVisualWireStyle, specText, startFillEvents, startGenerate,
  startPoll, statusLabel, statusPill, stepStatusLabel, stepStatusMark, stopFillEvents, stopPoll, tab,
  tableCopyText, tcColumns, tcCount, tcDownloadBase, tcFields, tcLoading, tcMarkdown, tcRows,
  themeOptions, toggleApi, toggleTable, toggleUnlock, typeParenMode, typefaceOptions, undoDelivery, undoDeliveryLabel,
  unlocked, viewActive, viewEpoch, warningText, zipFileName, zipLockHint,
} = bindPd()
</script>
