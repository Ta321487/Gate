<template>
  <div v-if="p">
    <button class="back" @click="$router.push('/')">← 返回项目列表</button>
    <div class="proj-head">
      <div>
        <div class="proj-title">{{ p.title }}</div>
        <div class="proj-meta">
          <span class="pill" :class="statusPill">{{ statusLabel }}</span>
          <span>ID <span class="mono">{{ p.id }}</span><CopyIconButton :text="p.id" tip="复制项目 ID" /></span>
          <span>{{ p.archetype }} · {{ p.domain }}</span>
          <span class="mono">{{ p.db_name }}</span><CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" />
        </div>
      </div>
      <div class="proj-actions">
        <n-button size="small" :disabled="!canDownload" :title="downloadBlockedReason" @click="downloadZip">
          {{ downloadZipLabel }}
        </n-button>
        <n-button type="error" secondary size="small" :disabled="deleteBlocked" :title="deleteBlockedReason" @click="onDelete">删除</n-button>
      </div>
    </div>

    <n-tabs v-model:value="tab" type="line" animated>
      <!-- Match -->
      <n-tab-pane name="match" tab="匹配确认">
        <div class="file-row">
          <span>源材料：<strong>{{ p.source_filename }}</strong> · {{ formatSize(p.source_size) }}</span>
          <n-button text size="small" @click="$router.push('/')">另建项目</n-button>
        </div>
        <div class="banner success">
          <h4>推荐匹配已给出</h4>
          <p class="small muted">确认后开始生成。骨架 / 领域改动需先解锁。</p>
        </div>
        <div v-if="matchWarnings.length" class="banner warn">
          <h4>匹配说明（请看一眼）</h4>
          <ul class="warn-list">
            <li v-for="(w, i) in matchWarnings" :key="i">{{ warningText(w) }}</li>
          </ul>
        </div>
        <div class="grid-2">
          <div class="panel">
            <div class="panel-hd">
              <h3>推荐匹配</h3>
              <span class="pill" :class="matchPillClass">{{ matchPillText }}</span>
            </div>
            <div class="panel-bd">
              <div class="rec-box">
                <div class="rec-title">系统推荐（置信度 {{ p.confidence.toFixed(2) }}）</div>
                <div class="rec-main">{{ p.recommended_arch }} × {{ p.recommended_domain }}</div>
                <div class="rec-sub" v-if="keywordHits.length">命中：{{ keywordHits.join(' / ') }}</div>
                <div class="rec-sub" v-if="p.spec?.out_of_mvp?.length">砍项：{{ p.spec.out_of_mvp.join('、') }}</div>
              </div>
              <div class="lock-row">
                <span class="small muted">{{ unlocked ? '骨架 / 领域可改' : '骨架 / 领域已锁定' }}</span>
                <div class="row">
                  <n-button size="small" @click="toggleUnlock">{{ unlocked ? '重新锁定' : '解锁覆盖' }}</n-button>
                  <n-button v-if="unlocked || deviant" text size="small" @click="resetMatch">恢复推荐</n-button>
                </div>
              </div>
              <div class="grid-2">
                <div class="field" :class="{ locked: !unlocked }">
                  <n-form-item label="骨架">
                    <n-select v-model:value="form.archetype" :options="archOptions" :disabled="!unlocked" @update:value="onArchDomChange" />
                  </n-form-item>
                </div>
                <div class="field" :class="{ locked: !unlocked }">
                  <n-form-item label="领域">
                    <n-select v-model:value="form.domain" :options="domOptions" :disabled="!unlocked" @update:value="onArchDomChange" />
                  </n-form-item>
                </div>
                <n-form-item label="行业配色">
                  <n-select v-model:value="form.theme" :options="themeOptions" @update:value="saveSoft" />
                </n-form-item>
                <n-form-item label="LLM 业务岛">
                  <n-select v-model:value="form.llm" :options="llmOptions" @update:value="saveSoft" />
                </n-form-item>
                <n-form-item label="密码">
                  <n-select v-model:value="form.passwordHash" :options="passwordHashOptions" @update:value="saveSoft" />
                </n-form-item>
              </div>
              <div class="confidence">
                <span class="small muted">置信度</span>
                <div class="bar"><i :style="{ width: displayConf * 100 + '%', background: displayConf >= 0.75 ? 'var(--green)' : 'var(--amber)' }" /></div>
                <strong>{{ displayConf.toFixed(2) }}</strong>
                <span v-if="deviant" class="small muted">覆盖后降级 · 推荐 {{ (p.confidence || 0).toFixed(2) }}</span>
              </div>
              <div class="override-banner" :class="{ show: unlocked || deviant, danger: deviant }">
                {{ deviant ? '当前与推荐不一致，请确认后再生成。' : '骨架 / 领域可改。无把握请恢复推荐。' }}
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>解析摘要 · Spec 预览</h3>
              <div class="row" style="margin:0;gap:6px">
                <CopyIconButton :text="specText" tip="复制 JSON" />
                <n-button text size="small" @click="showSpec = true">查看</n-button>
              </div>
            </div>
            <div class="panel-bd parse-panel">
              <div class="parse-block">
                <div class="parse-label">开题解析</div>
                <div class="parse-title">{{ proposal.title || p.title }}</div>
                <p v-if="proposal.background" class="parse-bg">{{ proposal.background }}</p>
                <div v-if="keywordHits.length" class="parse-hits">
                  <span v-for="h in keywordHits" :key="h" class="hit-chip">{{ h }}</span>
                </div>
                <div v-if="proposal.feature_lines?.length" class="parse-sec">
                  <div class="parse-sec-hd">开题功能点</div>
                  <ol class="parse-list">
                    <li v-for="(line, i) in proposal.feature_lines" :key="i">{{ line }}</li>
                  </ol>
                </div>
                <div v-if="proposal.out_scope_lines?.length" class="parse-sec">
                  <div class="parse-sec-hd">开题写明不在本期</div>
                  <ul class="parse-list plain">
                    <li v-for="(line, i) in proposal.out_scope_lines" :key="i">{{ line }}</li>
                  </ul>
                </div>
                <details v-if="proposal.excerpt" class="parse-excerpt">
                  <summary>原文摘录 · {{ proposal.char_count || proposal.excerpt.length }} 字</summary>
                  <pre>{{ proposal.excerpt }}</pre>
                </details>
                <p v-if="!proposal.excerpt && !proposal.feature_lines?.length" class="small muted">暂无开题正文摘要（源文件不可读时可另建项目）</p>
              </div>
              <div class="parse-block">
                <div class="parse-label">生成 Spec</div>
                <dl class="spec-dl">
                  <div><dt>角色</dt><dd>{{ roleSpecText }}</dd></div>
                  <div><dt>实体</dt><dd>{{ (p.spec?.entities || []).join('、') || '—' }}</dd></div>
                  <div><dt>主流程</dt><dd>{{ (p.spec?.flows || []).join('；') || '—' }}</dd></div>
                  <div><dt>基线</dt><dd>{{ (p.spec?.baseline || []).join('、') || '—' }}</dd></div>
                  <div v-if="p.spec?.out_of_mvp?.length"><dt>砍项</dt><dd>{{ p.spec.out_of_mvp.join('、') }}</dd></div>
                  <div><dt>配色</dt><dd>{{ p.spec?.theme_label || p.theme }}</dd></div>
                  <div><dt>登录入口</dt><dd>{{ p.spec?.auth_entry_mode_label || '—' }}<template v-if="p.spec?.auth_role_widget_label"> · {{ p.spec.auth_role_widget_label }}</template></dd></div>
                </dl>
              </div>
            </div>
          </div>
        </div>
        <div class="gate" :class="{ ok: ack }">
          <n-checkbox v-model:checked="ack" :disabled="p.match_confirmed">
            {{ confirmHint }}
          </n-checkbox>
        </div>
        <div class="row mt-16">
          <n-button type="primary" size="large" :disabled="!ack || p.match_confirmed" @click="confirmMatch">
            {{ deviant ? '确认覆盖并继续' : '确认并继续' }}
          </n-button>
        </div>
      </n-tab-pane>

      <!-- Generate -->
      <n-tab-pane name="generate" tab="一键生成">
        <div v-if="genState === 'idle'">
          <div class="panel mb-16">
            <div class="panel-bd">
              <div class="row-between">
                <div>
                  <div style="font-weight:600;margin-bottom:4px">{{ p.match_confirmed ? '匹配已确认 · 可以生成' : '请先完成匹配确认' }}</div>
                  <div class="small muted">bake 为主 · LLM 仅填业务岛 · 门禁不过禁止 ZIP</div>
                </div>
                <n-button type="primary" size="large" :disabled="!p.match_confirmed" @click="startGenerate">一键生成</n-button>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>生成流水线</h3>
              <span class="small muted">{{ planSteps.length }} 步 · 顺序执行</span>
            </div>
            <div class="panel-bd">
              <ol class="step-rail">
                <li v-for="(s, i) in planSteps" :key="i" class="pending">
                  <div class="step-rail-track" aria-hidden="true">
                    <span class="step-ico">{{ i + 1 }}</span>
                  </div>
                  <div class="step-body">
                    <div class="step-title">{{ s.t }}</div>
                    <div class="meta">{{ s.m }}</div>
                  </div>
                </li>
              </ol>
            </div>
          </div>
        </div>
        <div v-else-if="genState === 'running'">
          <div class="panel mb-16">
            <div class="panel-bd">
              <div class="row-between" style="margin-bottom:10px">
                <div style="font-weight:600">正在生成…</div>
                <div class="small muted">Job #{{ currentJob?.id }} · {{ currentJob?.progress || 0 }}%</div>
              </div>
              <div class="progress" style="height:8px"><i :style="{ width: (currentJob?.progress || 0) + '%' }" /></div>
              <p v-if="pollSyncHint" class="small muted mt-12">{{ pollSyncHint }}</p>
              <div class="row mt-12">
                <n-button size="small" type="error" secondary @click="cancelCurrent">取消任务</n-button>
                <n-button size="small" @click="tab = 'logs'">打开日志</n-button>
              </div>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>流水线进度</h3>
              <span class="small muted">{{ currentJob?.progress || 0 }}%</span>
            </div>
            <div class="panel-bd">
              <ol class="step-rail">
                <li
                  v-for="s in (currentJob?.steps || [])"
                  :key="s.key"
                  :class="s.status || 'pending'"
                >
                  <div class="step-rail-track" aria-hidden="true">
                    <span class="step-ico">{{
                      s.status === 'done' ? '✓'
                      : s.status === 'run' ? ''
                      : s.status === 'fail' ? '!'
                      : '·'
                    }}</span>
                  </div>
                  <div class="step-body">
                    <div class="step-title">{{ s.title }}</div>
                    <div class="meta">{{ s.meta || stepStatusLabel(s.status) }}</div>
                  </div>
                </li>
              </ol>
            </div>
          </div>
        </div>
        <div v-else-if="(genState === 'success' || genState === 'live') && canDownload" class="banner success">
          <h4>{{ genState === 'live' ? '已生成 · 预览运行中' : '生成完成 · 门禁全过 · 可交付' }}</h4>
          <p class="small muted">{{ genState === 'live' ? '前后端已启动，可打开预览或下载 ZIP。' : 'ZIP 已解锁。请到「运行」预览后再交付。' }}</p>
          <div class="row mt-12">
            <n-button type="primary" size="small" @click="tab = 'runtime'">前往运行</n-button>
            <n-button size="small" @click="goArtifacts('gates')">查看门禁</n-button>
            <n-button size="small" @click="downloadZip">下载 ZIP</n-button>
            <n-button size="small" @click="startGenerate">重新生成</n-button>
          </div>
        </div>
        <div v-else-if="genState === 'success' || genState === 'live'" class="banner fail">
          <h4>已生成 · 门禁回退 · 禁止下载</h4>
          <p class="small muted">工作区与当前门禁不一致（常见于骨架升级后）。请重新生成，或到「产物」查看未过项。</p>
          <div class="row mt-12">
            <n-button type="primary" size="small" @click="startGenerate">重新生成</n-button>
            <n-button size="small" @click="goArtifacts('gates')">查看门禁</n-button>
            <n-button size="small" @click="tab = 'runtime'">前往运行</n-button>
          </div>
        </div>
        <div v-else class="banner fail">
          <h4>门禁未过 · 禁止交付</h4>
          <p class="small muted">{{ currentJob?.error || '主流程 / 功能清单未通过则禁止下载 ZIP。' }}</p>
          <div class="row mt-12">
            <n-button type="primary" size="small" @click="retryCurrent">从失败步骤重试</n-button>
            <n-button size="small" @click="goArtifacts('gates')">查看门禁</n-button>
            <n-button size="small" @click="tab = 'logs'">查看日志</n-button>
          </div>
        </div>
      </n-tab-pane>

      <!-- Runtime -->
      <n-tab-pane name="runtime" tab="运行">
        <div class="row-between mb-16">
          <span class="small muted">库 <span class="mono">{{ p.db_name || '—' }}</span><CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" /></span>
          <div class="row" style="margin:0">
            <n-button
              size="small"
              :type="rtCanStartAll && !rtAnyLive ? 'primary' : 'default'"
              :disabled="!rtCanStartAll"
              :loading="rtPendingAll==='start'"
              @click="rtAction('all','start')"
            >全部启动</n-button>
            <n-button
              size="small"
              :type="rtBothLive ? 'primary' : 'default'"
              :disabled="!rtCanStopAll"
              :loading="rtPendingAll==='stop'"
              @click="rtAction('all','stop')"
            >全部关闭</n-button>
            <n-button
              size="small"
              :disabled="!rtCanRestartAll"
              :loading="rtPendingAll==='restart'"
              @click="rtAction('all','restart')"
            >全部重启</n-button>
            <n-button size="small" :disabled="rt.frontend_status !== 'healthy' || rtBusyFe" @click="openPreview">打开预览</n-button>
            <CopyIconButton
              v-if="rt.preview_url && rt.frontend_status === 'healthy'"
              :text="rt.preview_url"
              tip="复制预览地址"
            />
          </div>
        </div>
        <div class="grid-2">
          <div class="panel">
            <div class="panel-hd">
              <h3>后端 · :{{ p.backend_port || '—' }}<CopyIconButton v-if="backendAddr" :text="backendAddr" tip="复制后端地址" /></h3>
              <span class="pill" :class="runtimeStatusPill(rt.backend_status)">{{ runtimeStatusLabel(rt.backend_status) }}</span>
            </div>
            <div class="panel-bd">
              <div class="row" style="justify-content:flex-end">
                <n-button
                  size="small"
                  :disabled="rtBusyBe || rtAllBusy || runtimeTransient(rt.backend_status)"
                  :loading="rtBusyBe || runtimeTransient(rt.backend_status)"
                  @click="rtAction('backend', runtimeCanStop(rt.backend_status) ? 'stop' : 'start')"
                >{{ runtimeCanStop(rt.backend_status) ? '停止' : '启动' }}</n-button>
              </div>
              <pre class="log-box">{{ runtimeLogView(rt.backend_status, rt.backend_log_tail) }}</pre>
            </div>
          </div>
          <div class="panel">
            <div class="panel-hd">
              <h3>前端 · :{{ p.frontend_port || '—' }}<CopyIconButton v-if="frontendAddr" :text="frontendAddr" tip="复制前端地址" /></h3>
              <span class="pill" :class="runtimeStatusPill(rt.frontend_status)">{{ runtimeStatusLabel(rt.frontend_status) }}</span>
            </div>
            <div class="panel-bd">
              <div class="row" style="justify-content:flex-end">
                <n-button
                  size="small"
                  :disabled="rtBusyFe || rtAllBusy || runtimeTransient(rt.frontend_status)"
                  :loading="rtBusyFe || runtimeTransient(rt.frontend_status)"
                  @click="rtAction('frontend', runtimeCanStop(rt.frontend_status) ? 'stop' : 'start')"
                >{{ runtimeCanStop(rt.frontend_status) ? '停止' : '启动' }}</n-button>
              </div>
              <pre class="log-box">{{ runtimeLogView(rt.frontend_status, rt.frontend_log_tail) }}</pre>
            </div>
          </div>
        </div>
      </n-tab-pane>

      <!-- Logs -->
      <n-tab-pane name="logs" tab="日志">
        <div class="row mb-12" style="justify-content:space-between;gap:12px;flex-wrap:wrap">
          <div class="row" style="gap:10px;flex-wrap:wrap">
            <n-button-group size="small">
              <n-button v-for="s in logSides" :key="s.id" :type="logSide===s.id?'primary':'default'" @click="loadLog(s.id)">{{ s.label }}</n-button>
            </n-button-group>
            <n-input v-model:value="logFilter" clearable placeholder="过滤关键字…" style="width:180px" />
          </div>
          <n-button size="small" :loading="logLoading" @click="loadLog(logSide)">刷新</n-button>
        </div>
        <pre class="log-viewer">{{ filteredLog }}</pre>
      </n-tab-pane>

      <!-- Artifacts -->
      <n-tab-pane name="artifacts" tab="产物 / 对照">
        <div class="panel artifacts-files">
          <div class="panel-hd">
            <h3>产物</h3>
            <span class="small muted">交付文件与工作区路径</span>
          </div>
          <div class="panel-bd artifacts-file-grid">
            <div class="file-row" style="margin:0">
              <span><strong>thesis-app.zip</strong><br /><span class="small muted">{{ zipLockHint }}</span></span>
              <n-button size="small" :disabled="!canDownload" :title="downloadBlockedReason" @click="downloadZip">
                {{ canDownload ? '下载' : '锁定' }}
              </n-button>
            </div>
            <div class="file-row" style="margin:0">
              <span><strong>workspace/</strong><br /><span class="small muted mono">{{ p.workspace_path || '尚未生成' }}</span></span>
              <CopyIconButton v-if="p.workspace_path" :text="p.workspace_path" tip="复制路径" />
            </div>
            <div class="file-row" style="margin:0">
              <span><strong>spec.json</strong><br /><span class="small muted">匹配与生成配置</span></span>
              <div class="row" style="margin:0;gap:6px">
                <CopyIconButton :text="specText" tip="复制 JSON" />
                <n-button text size="small" @click="showSpec = true">查看</n-button>
              </div>
            </div>
          </div>
        </div>

        <div class="panel mt-16">
          <div class="panel-hd">
            <h3>对照视图</h3>
            <span class="small muted">库表 · 学生端 API · 门禁（不写入 ZIP）</span>
          </div>
          <div class="panel-bd" style="padding-top:4px">
            <n-tabs v-model:value="artifactView" type="line" size="small" @update:value="onArtifactView">
              <n-tab-pane name="db" tab="数据库">
                <div class="artifact-pane stack">
                  <div class="row" style="justify-content:space-between;align-items:center;gap:12px">
                    <div class="small">
                      <span class="muted">库名</span> · <span class="mono">{{ p.db_name || '—' }}</span>
                      <CopyIconButton v-if="p.db_name" :text="p.db_name" tip="复制库名" />
                      <span class="pill" :class="schema ? 'pill-green' : 'pill-neutral'" style="margin-left:8px">
                        {{ schema ? '已解析' : (p.workspace_path ? '无 SQL' : '未生成') }}
                      </span>
                    </div>
                    <div class="row" style="margin:0;gap:8px">
                      <label v-if="schema?.tables?.length" class="type-mode-switch small">
                        <n-switch v-model:value="typeParenMode" size="small" />
                        <span class="muted">{{ typeParenMode ? '类型 varchar(60)' : '类型分列 varchar | 60' }}</span>
                      </label>
                      <n-button size="small" :disabled="!schema?.tables?.length" @click="openEr">E-R 图</n-button>
                      <n-button size="small" secondary :disabled="!schema?.tables?.length" @click="downloadEr">下载 SVG</n-button>
                    </div>
                  </div>
                  <div class="small muted">SQL · sql/schema.sql · 约束 6~13 张表</div>
                  <template v-if="schema?.tables?.length">
                    <div class="small">当前 <strong>{{ schema.tables.length }}</strong> 张
                      <span :class="(schema.tables.length >= 6 && schema.tables.length <= 13) ? 'muted' : 'text-danger'">
                        （{{ schema.tables.length >= 6 && schema.tables.length <= 13 ? '符合' : '不符合' }} 6~13）
                      </span>
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
                          <span v-if="t.label && t.label !== t.name" class="table-zh">{{ t.label }}</span>
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
                            <span class="col-zh">{{ c.label || '—' }}</span>
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
                        —〈{{ r.label || r.name }}〉—
                        <span class="muted">{{ r.card_right }}</span>
                        <span class="mono">{{ r.right }}</span>
                        <span class="small muted">via {{ r.via }}</span>
                      </div>
                    </div>
                  </template>
                  <p v-else class="small muted">生成工作区后可查看表结构与 E-R 图。</p>
                </div>
              </n-tab-pane>

              <n-tab-pane name="api" tab="学生端 API">
                <div class="artifact-pane stack">
                  <div class="row" style="justify-content:space-between;align-items:center;gap:12px">
                    <div class="small">
                      <template v-if="apis">
                        <strong>{{ apis.count }}</strong> 条 ·
                        <span class="muted">{{ apis.controller_count }} 个 Controller</span>
                        <span v-if="apis.flow_marked" class="pill pill-green" style="margin-left:8px">
                          主流程 {{ apis.flow_marked }}
                        </span>
                      </template>
                      <span v-else class="pill pill-neutral">{{ p.workspace_path ? '无 Controller' : '未生成' }}</span>
                    </div>
                    <div class="row" style="margin:0;gap:8px">
                      <n-input
                        v-model:value="apiQuery"
                        size="small"
                        clearable
                        placeholder="筛选 path / 方法 / handler"
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
                    静态扫描工作区 Controller · 对照门禁 flow_api · 不写入学生 ZIP。
                    复制为「方法 + 路径」；联调基址用运行页后端地址（Session Cookie）。
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
                            <span>Handler</span>
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
                  <p v-else class="small muted">生成工作区后可对照学生端 REST 映射。</p>
                </div>
              </n-tab-pane>

              <n-tab-pane name="gates" tab="门禁 / 清单">
                <div class="artifact-pane stack">
                  <div class="row" style="justify-content:space-between;align-items:center">
                    <div class="small">
                      质量门禁 · 交付 DoD
                      <span class="pill" :class="canDownload ? 'pill-green' : 'pill-red'" style="margin-left:8px">
                        {{ canDownload ? '可交付' : '禁止交付' }}
                      </span>
                    </div>
                  </div>
                  <p class="small muted" style="margin:0">P2 主流程或功能清单未过，禁止下载 ZIP。</p>
                  <n-data-table :columns="gateCols" :data="gateRows" :bordered="false" size="small" />
                  <div class="parse-sec-hd mt-12">开题对照清单</div>
                  <n-data-table :columns="checkCols" :data="checkRows" :bordered="false" size="small" />
                </div>
              </n-tab-pane>
            </n-tabs>
          </div>
        </div>
      </n-tab-pane>
    </n-tabs>

    <n-modal
      v-model:show="showDelete"
      preset="dialog"
      title="删除项目"
      positive-text="确认删除"
      negative-text="取消"
      type="error"
      :loading="deleting"
      @positive-click="confirmDelete"
      @negative-click="showDelete = false"
    >
      <p style="margin:0 0 12px">将清理工作区与 ZIP，此操作不可恢复。</p>
      <p v-if="p.db_name" class="small muted" style="margin:0 0 12px">
        学生库 <span class="mono">{{ p.db_name }}</span>
        {{ keepDb ? '将被保留' : '将一并删除' }}
      </p>
      <n-checkbox v-if="p.db_name" v-model:checked="keepDb">保留数据库（不执行 DROP）</n-checkbox>
    </n-modal>
    <n-modal v-model:show="showSpec" preset="card" title="spec.json" style="width:640px">
      <div class="row" style="justify-content:flex-end;margin:0 0 8px">
        <CopyIconButton :text="specText" tip="复制 JSON" />
      </div>
      <pre class="spec-preview" style="max-height:60vh">{{ specText }}</pre>
    </n-modal>
    <n-modal v-model:show="showEr" preset="card" title="E-R 图（线框）" style="width:min(1280px,96vw)">
      <div class="er-toolbar row mb-12">
        <span class="small muted">拖拽平移 · 滚轮缩放 · 菱形联系 · 方框实体 · 椭圆属性</span>
        <div class="er-zoom-btns row">
          <n-button size="small" @click="erZoomOut">缩小</n-button>
          <span class="er-zoom-label">{{ Math.round(erScale * 100) }}%</span>
          <n-button size="small" @click="erZoomIn">放大</n-button>
          <n-button size="small" @click="erZoomReset">重置</n-button>
          <n-button size="small" type="primary" @click="downloadEr">下载 SVG</n-button>
        </div>
      </div>
      <div
        ref="erFrameRef"
        class="er-frame"
        @wheel.prevent="onErWheel"
        @pointerdown="onErPointerDown"
        @pointermove="onErPointerMove"
        @pointerup="onErPointerUp"
        @pointercancel="onErPointerUp"
        @pointerleave="onErPointerUp"
      >
        <div class="er-canvas" :style="erCanvasStyle" v-html="erSvgHtml" />
      </div>
    </n-modal>
  </div>
  <ErrorPage
    v-else-if="loadError"
    :code="loadErrorCode"
    :title="loadErrorCode === 404 ? '项目不存在' : '加载失败'"
    :description="loadErrorCode === 404
      ? '该项目 ID 在本机工作区中找不到，可能已被删除或链接有误。'
      : '拉取项目详情时出错，可重试或返回项目列表。'"
    :detail="loadError"
    retryable
    @retry="reload"
  />
  <PageSkeleton v-else variant="detail" />
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { api, message, confirm } from '../api'
import ErrorPage from './ErrorPage.vue'
import PageSkeleton from '../components/PageSkeleton.vue'
import CopyIconButton from '../components/CopyIconButton.vue'
import {
  CHECKLIST_RESULT,
  LOG_SIDES,
  defaultTabForStatus,
  detailCrumb,
  getCatalog,
  projectStatusLabel,
  projectStatusPill,
  statusPillNode,
} from '../opsShared'

const route = useRoute()
const router = useRouter()
/** 离开详情页 / 切换项目时递增，作废进行中的启动轮询，避免用空 id 请求 */
let viewEpoch = 0
const p = ref(null)
const loadError = ref('')
const loadErrorCode = ref(500)
const tab = ref('match')
const catalog = ref({ archetypes: [], domains: [], themes_by_domain: {} })
const form = reactive({ archetype: '', domain: '', theme: '', llm: 'on', passwordHash: 'none' })
const ack = ref(false)
const unlocked = ref(false)
const currentJob = ref(null)
const rt = reactive({
  backend_status: 'stopped',
  frontend_status: 'stopped',
  preview_url: null,
  backend_url: null,
  public_host: '127.0.0.1',
  backend_log_tail: '',
  frontend_log_tail: '',
})
const rtBusyBe = ref(false)
const rtBusyFe = ref(false)
const rtPendingAll = ref('')
const rtAnyBusy = computed(() => rtBusyBe.value || rtBusyFe.value)
const rtAllBusy = computed(() => rtBusyBe.value && rtBusyFe.value)
/** IDE 式：已在跑就不能再启动；全停就不能关/重启 */
const rtBeLive = computed(() => runtimeCanStop(rt.backend_status))
const rtFeLive = computed(() => runtimeCanStop(rt.frontend_status))
const rtAnyLive = computed(() => rtBeLive.value || rtFeLive.value)
const rtBothLive = computed(() => rtBeLive.value && rtFeLive.value)
const rtCanStartAll = computed(
  () => Boolean(p.value?.workspace_path) && !rtAnyBusy.value && !rtBothLive.value,
)
const rtCanStopAll = computed(
  () => Boolean(p.value?.workspace_path) && !rtAnyBusy.value && rtAnyLive.value,
)
const rtCanRestartAll = computed(() => rtCanStopAll.value)
const backendAddr = computed(() => {
  if (rt.backend_url) return rt.backend_url
  const host = rt.public_host || '127.0.0.1'
  const port = p.value?.backend_port
  return port ? `http://${host}:${port}` : ''
})
const frontendAddr = computed(() => {
  if (rt.preview_url) return rt.preview_url
  const host = rt.public_host || '127.0.0.1'
  const port = p.value?.frontend_port
  return port ? `http://${host}:${port}` : ''
})
const logSide = ref('job')
const logText = ref('')
const logFilter = ref('')
const logLoading = ref(false)
const logSides = LOG_SIDES
const showSpec = ref(false)
const showEr = ref(false)
const showDelete = ref(false)
const keepDb = ref(false)
const deleting = ref(false)
const schema = ref(null)
const apis = ref(null)
const artifactView = ref('db')
const apiQuery = ref('')
const apiSurface = ref('all')
const collapsedApis = ref({})
const erSvgHtml = ref('')
const erFrameRef = ref(null)
const erScale = ref(1)
const erPanX = ref(0)
const erPanY = ref(0)
const erDragging = ref(false)
let erLastX = 0
let erLastY = 0
let pollTimer = null

const erCanvasStyle = computed(() => ({
  transform: `translate(${erPanX.value}px, ${erPanY.value}px) scale(${erScale.value})`,
  transformOrigin: '0 0',
}))

const ER_SCALE_MIN = 0.25
const ER_SCALE_MAX = 4
const ER_SCALE_STEP = 0.15

function erClampScale(s) {
  return Math.min(ER_SCALE_MAX, Math.max(ER_SCALE_MIN, s))
}

function erZoomIn() {
  erScale.value = erClampScale(erScale.value + ER_SCALE_STEP)
}

function erZoomOut() {
  erScale.value = erClampScale(erScale.value - ER_SCALE_STEP)
}

function erZoomReset() {
  erScale.value = 1
  erPanX.value = 0
  erPanY.value = 0
}

function onErWheel(e) {
  const frame = erFrameRef.value
  if (!frame) return
  const rect = frame.getBoundingClientRect()
  const mx = e.clientX - rect.left
  const my = e.clientY - rect.top
  const prev = erScale.value
  const next = erClampScale(prev * (e.deltaY < 0 ? 1.1 : 1 / 1.1))
  if (next === prev) return
  // 以光标为缩放中心
  const wx = (mx - erPanX.value) / prev
  const wy = (my - erPanY.value) / prev
  erScale.value = next
  erPanX.value = mx - wx * next
  erPanY.value = my - wy * next
}

function onErPointerDown(e) {
  if (e.button !== 0) return
  erDragging.value = true
  erLastX = e.clientX
  erLastY = e.clientY
  e.currentTarget.setPointerCapture?.(e.pointerId)
}

function onErPointerMove(e) {
  if (!erDragging.value) return
  erPanX.value += e.clientX - erLastX
  erPanY.value += e.clientY - erLastY
  erLastX = e.clientX
  erLastY = e.clientY
}

function onErPointerUp(e) {
  erDragging.value = false
  try {
    e.currentTarget?.releasePointerCapture?.(e.pointerId)
  } catch {
    /* ignore */
  }
}

const planSteps = [
  { t: '解析开题 → 合并 Spec', m: '匹配阶段' },
  { t: '复制骨架 · 写入领域 SQL', m: '确定性 bake' },
  { t: '业务岛 emit · LLM 填缺口', m: '白名单文件' },
  { t: '构建验证', m: 'P0' },
  { t: '门禁：登录 + 主流程 E2E', m: 'P1 / P2' },
  { t: '开题对照 · 打包 ZIP', m: '仅门禁全过' },
]

function stepStatusLabel(st) {
  return ({ done: '已完成', run: '进行中', fail: '失败', pending: '等待中' })[st] || st || '等待中'
}

const archOptions = computed(() => catalog.value.archetypes.map((x) => ({ label: x.label, value: x.id })))
const domOptions = computed(() => catalog.value.domains.map((x) => ({ label: x.label, value: x.id })))
const themeOptions = computed(() => {
  const list = catalog.value.themes_by_domain?.[form.domain] || []
  return list.map((x) => ({ label: x.label, value: x.id }))
})
const passwordHashOptions = [
  { label: '明文', value: 'none' },
  { label: 'BCrypt', value: 'bcrypt' },
  { label: 'MD5', value: 'md5' },
  { label: 'SHA-256', value: 'sha256' },
]
const llmOptions = [
  { label: '开启 · 白名单插槽填充', value: 'on' },
  { label: '关闭 · 仅确定性 bake', value: 'off' },
]

const deviant = computed(() => {
  if (!p.value) return false
  return form.archetype !== p.value.recommended_arch || form.domain !== p.value.recommended_domain
})
const displayConf = computed(() => (deviant.value ? 0.41 : (p.value?.confidence || 0)))
const matchPillClass = computed(() => {
  if (deviant.value) return 'pill-red'
  if (unlocked.value) return 'pill-amber'
  return 'pill-green'
})
const matchPillText = computed(() => {
  if (deviant.value) return '已偏离推荐'
  if (unlocked.value) return '已解锁'
  return '已锁定推荐'
})
const matchWarnings = computed(() => {
  const spec = p.value?.spec || {}
  if (Array.isArray(spec.match_warnings) && spec.match_warnings.length) return spec.match_warnings
  return (spec.hits || []).filter((h) => typeof h === 'string' && h.startsWith('提示：'))
})
const keywordHits = computed(() =>
  (p.value?.spec?.hits || []).filter((h) => typeof h === 'string' && !h.startsWith('提示：')),
)
function warningText(w) {
  return String(w || '').replace(/^提示：/, '')
}
const confirmHint = computed(() => {
  if (deviant.value) return '确认按当前骨架 / 领域生成。'
  return '已核对骨架、领域与砍项，确认后开始生成。'
})
const canDownload = computed(() => {
  if (!p.value) return false
  if (p.value.status === 'generating') return false
  return !!(p.value.zip_ready && p.value?.gates?.zip_allowed && p.value?.gates?.overall)
})
const downloadZipLabel = computed(() => (p.value?.status === 'generating' ? '生成中…' : '下载 ZIP'))
const downloadBlockedReason = computed(() => {
  if (p.value?.status === 'generating') return '生成中 · 打包完成前不可下载'
  if (!canDownload.value) return '门禁未过 · 禁止下载 ZIP'
  return ''
})
const zipLockHint = computed(() => {
  if (p.value?.status === 'generating') return '生成中 · 打包完成后解锁'
  return canDownload.value ? '门禁已过' : '门禁未过 · 锁定'
})

const deleteBlocked = computed(() => {
  if (!p.value) return true
  if (p.value.status === 'running' || p.value.status === 'generating') return true
  if (p.value.backend_running || p.value.frontend_running) return true
  const be = rt.backend_status
  const fe = rt.frontend_status
  if (['starting', 'healthy', 'stopping'].includes(be) || ['starting', 'healthy', 'stopping'].includes(fe)) {
    return true
  }
  return false
})
const deleteBlockedReason = computed(() =>
  deleteBlocked.value ? '项目运行中或正在生成，请先停止后再删除' : '',
)

function runtimeStatusLabel(st) {
  return ({
    stopped: '已停止',
    starting: '启动中',
    stopping: '停止中',
    healthy: '健康',
    error: '异常',
  })[st] || st || '已停止'
}
function runtimeStatusPill(st) {
  return ({
    stopped: 'pill-neutral',
    starting: 'pill-amber',
    stopping: 'pill-amber',
    healthy: 'pill-green',
    error: 'pill-red',
  })[st] || 'pill-neutral'
}
function runtimeCanStop(st) {
  return st === 'healthy' || st === 'starting' || st === 'stopping'
}
function runtimeTransient(st) {
  return st === 'starting' || st === 'stopping'
}
/** 状态只在 pill；这里只展示真实日志，占位文案一律收成 — */
function runtimeLogView(st, tail) {
  if (st === 'stopped' || st === 'stopping') return '—'
  if (!tail || /^(后端|前端)?(启动|停止)中/.test(String(tail).trim())) return '—'
  return _tailLines(tail, st === 'error' ? 12 : 8)
}
function _tailLines(tail, keep) {
  const lines = String(tail).split(/\r?\n/).filter((l) => l.trim())
  return lines.slice(-keep).join('\n') || '—'
}

const statusLabel = computed(() =>
  projectStatusLabel(p.value?.status, { zipReady: canDownload.value }),
)
const statusPill = computed(() =>
  projectStatusPill(p.value?.status, { zipReady: canDownload.value }),
)

const genState = computed(() => {
  if (!p.value) return 'idle'
  if (p.value.status === 'generating') return 'running'
  if (p.value.status === 'running') return 'live'
  if (p.value.status === 'generated') return 'success'
  if (p.value.status === 'failed') return 'failed'
  return 'idle'
})

const specText = computed(() => JSON.stringify(p.value?.spec || {}, null, 2))
const proposal = computed(() => p.value?.spec?.proposal || {})
/** Spec 角色文案：schema.roles / staff_posts[].label，不写死中文 */
const roleSpecText = computed(() => {
  const roles = p.value?.spec?.roles || []
  if (!roles.length) return '—'
  const byId = p.value?.spec?.schema?.roles || {}
  const posts = Array.isArray(byId.staff_posts) ? byId.staff_posts : []
  const postLabel = Object.fromEntries(
    posts.filter((x) => x?.id).map((x) => [x.id, x.label || x.id]),
  )
  return roles
    .map((id) => {
      const label = postLabel[id] || byId[id]?.label
      const kind = posts.find((x) => x?.id === id)?.kind
      const kindZh = kind === 'worker' ? '员工' : kind === 'clerk' ? '子管理' : ''
      if (label && kindZh) return `${id}（${label}·${kindZh}）`
      return label ? `${id}（${label}）` : id
    })
    .join('、')
})
const filteredLog = computed(() => {
  const q = logFilter.value.trim().toLowerCase()
  if (!q) return logText.value || '（无日志）'
  return logText.value.split('\n').filter((l) => l.toLowerCase().includes(q)).join('\n') || '（无匹配）'
})

const gateCols = [
  { title: '级别', key: 'level', width: 80, render: (r) => statusPillNode(r.level, 'pill-neutral') },
  { title: '检查项', key: 'label' },
  {
    title: '结果',
    key: 'ok',
    width: 100,
    render: (r) => statusPillNode(r.ok ? '通过' : '未通过', r.ok ? 'pill-green' : 'pill-red'),
  },
  { title: '说明', key: 'desc' },
]
const gateRows = computed(() => {
  const g = p.value?.gates || {}
  // 含 p3c/p3d/accept：否则 overall 被这些项卡住时 UI 看不见原因
  const keys = ['p0a', 'p0b', 'p1', 'p2', 'p3a', 'p3b', 'p3t', 'p3c', 'p3d', 'accept']
  const levels = {
    p0a: 'P0', p0b: 'P0', p1: 'P1', p2: 'P2',
    p3a: 'P3', p3b: 'P3', p3t: 'P3', p3c: 'P3', p3d: 'P3', accept: 'P3',
  }
  return keys
    .filter((k) => g[k] != null)
    .map((k) => ({
      key: k,
      level: levels[k] || 'P3',
      label: g[k]?.label || k,
      ok: !!g[k]?.ok,
      desc: g[k]?.desc || '',
    }))
})
const checkCols = [
  { title: '开题功能', key: 'name' },
  {
    title: '实现状态',
    key: 'result',
    render: (r) => {
      const m = CHECKLIST_RESULT[r.result] || CHECKLIST_RESULT.pending
      return statusPillNode(m.label, m.pill)
    },
  },
  { title: '说明', key: 'status' },
]
const checkRows = computed(() => (p.value?.checklist || []).map((x) => ({
  name: x.name,
  result: x.result || (x.status === 'out_of_mvp' ? 'out_of_mvp' : 'pending'),
  status: x.status,
})))

/** 开：varchar(60)；关：类型 / 长度 分列 */
const TYPE_PAREN_KEY = 'gf-ops-schema-type-paren'
const typeParenMode = ref(
  (() => {
    try {
      const v = localStorage.getItem(TYPE_PAREN_KEY)
      if (v === '0' || v === 'false') return false
    } catch { /* ignore */ }
    return true
  })(),
)
watch(typeParenMode, (v) => {
  try {
    localStorage.setItem(TYPE_PAREN_KEY, v ? '1' : '0')
  } catch { /* ignore */ }
})

/** 解析 MySQL 类型 → 标准小写 + 可选长度参数 */
function parseMysqlType(raw) {
  const s = String(raw || '').trim()
  const m = s.match(/^([a-zA-Z][a-zA-Z0-9_]*)\s*(?:\(([^)]*)\))?/)
  if (!m) {
    const base = s.toLowerCase()
    return { base, len: '', full: base }
  }
  const base = m[1].toLowerCase()
  const len = (m[2] || '').replace(/\s+/g, '').trim()
  return { base, len, full: len ? `${base}(${len})` : base }
}

/**
 * 单表复制：制表符分隔，可贴进 Word「文本转换成表格」。
 * 随 typeParenMode：合并类型 或 类型/长度分列。
 */
function tableCopyText(t) {
  if (!t) return ''
  const title = t.label && t.label !== t.name
    ? `表 ${t.label}（${t.name}）`
    : `表 ${t.name}`
  const paren = typeParenMode.value
  const rows = paren
    ? [['字段名', '中文名', '数据类型']]
    : [['字段名', '中文名', '类型', '长度']]
  for (const c of t.columns || []) {
    const { base, len, full } = parseMysqlType(c.type)
    if (paren) {
      rows.push([c.name || '', c.label || c.name || '', full])
    } else {
      rows.push([c.name || '', c.label || c.name || '', base, len])
    }
  }
  const body = rows.map((cols) => cols.join('\t')).join('\n')
  return `${title}\n\n${body}`
}

/** 表卡片折叠（点表头空白处切换；复制按钮自带 stop） */
const collapsedTables = ref({})
function isTableCollapsed(name) {
  return !!collapsedTables.value[name]
}
function toggleTable(name) {
  collapsedTables.value = {
    ...collapsedTables.value,
    [name]: !collapsedTables.value[name],
  }
}

function formatSize(n) {
  if (!n) return '—'
  if (n < 1024) return n + ' B'
  if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB'
  return (n / 1024 / 1024).toFixed(1) + ' MB'
}

function viewActive(projectId, epoch) {
  return epoch === viewEpoch && route.params.id === projectId
}

async function load({ syncTab = false, lite = false, id: idOpt } = {}) {
  const id = idOpt || route.params.id
  loadError.value = ''
  if (!id || id === 'undefined' || id === 'null') {
    p.value = null
    detailCrumb.value = ''
    loadErrorCode.value = 404
    loadError.value = '项目 ID 无效'
    return
  }
  try {
    if (!lite && !catalog.value.archetypes.length) {
      catalog.value = await getCatalog()
    }
    // 轮询用短超时静默接口：后端 reload 时不弹错、不卡 60s
    p.value = lite ? await api.getProjectPoll(id) : await api.getProject(id)
    detailCrumb.value = p.value.title || ''
    pollSyncHint.value = ''
    pollFailStreak.value = 0
    if (!lite) {
      form.archetype = p.value.archetype
      form.domain = p.value.domain
      form.theme = p.value.theme
      form.llm = p.value.llm_enabled ? 'on' : 'off'
      form.passwordHash = p.value.password_hash || 'none'
      unlocked.value = !p.value.match_locked
      ack.value = p.value.match_confirmed
    }
    // 仅进入/切项目时同步主 tab；轮询禁止强切，否则无法停在日志页
    if (syncTab) tab.value = defaultTabForStatus(p.value.status)
    if (!lite && p.value.workspace_path && tab.value === 'runtime') await refreshRuntime(id)
    await refreshJob({ silent: lite })
    // schema / apis 只在产物 Tab 拉，避免生成轮询疯狂刷
    if (!lite && tab.value === 'artifacts') await loadArtifactView()
  } catch (e) {
    if (lite) {
      pollFailStreak.value += 1
      if (pollFailStreak.value >= 2) {
        pollSyncHint.value = '状态同步暂时中断（后端可能在重载），后台任务仍在跑，自动重试中…'
      }
      return
    }
    p.value = null
    detailCrumb.value = ''
    const status = e?.response?.status
    loadErrorCode.value = status === 404 ? 404 : 500
    const detail = e?.response?.data?.detail
    loadError.value = (typeof detail === 'string' ? detail : '') || e?.message || '加载失败'
  }
}

async function reload() {
  stopPoll()
  await load({ syncTab: true })
  if (p.value?.status === 'generating') startPoll()
}

async function loadSchema() {
  if (!p.value?.workspace_path) {
    schema.value = null
    return
  }
  try {
    schema.value = await api.getSchema(p.value.id)
  } catch {
    schema.value = null
  }
}

async function loadApis() {
  if (!p.value?.workspace_path) {
    apis.value = null
    return
  }
  try {
    apis.value = await api.getApis(p.value.id)
  } catch {
    apis.value = null
  }
}

async function loadArtifactView() {
  if (artifactView.value === 'api') await loadApis()
  else if (artifactView.value === 'db') await loadSchema()
  else {
    // 门禁数据已在项目上；顺带预热 schema
    await loadSchema()
  }
}

function onArtifactView(name) {
  if (name === 'api') loadApis()
  else if (name === 'db') loadSchema()
}

function goArtifacts(view = 'db') {
  artifactView.value = view
  tab.value = 'artifacts'
  loadArtifactView()
}

function isApiCollapsed(name) {
  return !!collapsedApis.value[name]
}

function toggleApi(name) {
  collapsedApis.value = {
    ...collapsedApis.value,
    [name]: !collapsedApis.value[name],
  }
}

const filteredApiGroups = computed(() => {
  const inv = apis.value
  if (!inv?.controllers?.length) return []
  const q = (apiQuery.value || '').trim().toLowerCase()
  const surface = apiSurface.value
  const groups = []
  for (const c of inv.controllers) {
    const endpoints = (c.endpoints || []).filter((ep) => {
      if (surface !== 'all' && ep.surface !== surface) return false
      if (!q) return true
      const blob = `${ep.method} ${ep.path} ${ep.handler} ${(ep.flow_keys || []).join(' ')} ${c.controller}`.toLowerCase()
      return blob.includes(q)
    })
    if (endpoints.length) groups.push({ ...c, endpoints })
  }
  return groups
})

function apiGroupCopyText(g) {
  return (g.endpoints || [])
    .map((ep) => `${ep.method} ${ep.path}`)
    .join('\n')
}

const apiCopyText = computed(() => {
  const groups = filteredApiGroups.value
  if (!groups.length) return ''
  return groups.map((g) => apiGroupCopyText(g)).filter(Boolean).join('\n')
})

async function openEr() {
  if (!p.value) return
  const res = await fetch(`${api.erSvgUrl(p.value.id)}?t=${Date.now()}`)
  if (!res.ok) {
    message.error('无法加载 E-R 图')
    return
  }
  const raw = await res.text()
  erSvgHtml.value = raw.replace(/^<\?xml[^>]*>\s*/i, '')
  erZoomReset()
  showEr.value = true
}

function downloadEr() {
  if (!p.value) return
  const a = document.createElement('a')
  a.href = `${api.erSvgUrl(p.value.id)}?t=${Date.now()}`
  a.download = `${p.value.id}-er.svg`
  a.click()
}

async function refreshJob({ silent = false } = {}) {
  try {
    const jobs = silent ? await api.listJobsPoll() : await api.listJobs()
    currentJob.value = jobs.find((j) => j.project_id === route.params.id) || null
  } catch (e) {
    if (!silent) throw e
  }
}

async function refreshRuntime(projectId) {
  const id = projectId || route.params.id
  if (!id || id === 'undefined' || id === 'null') return
  let data
  try {
    data = await api.runtime(id)
  } catch {
    return
  }
  if (route.params.id !== id) return
  rt.preview_url = data.preview_url || null
  rt.backend_url = data.backend_url || null
  rt.public_host = data.public_host || '127.0.0.1'
  if (p.value && p.value.id === id) {
    p.value.backend_port = data.backend_port || 0
    p.value.frontend_port = data.frontend_port || 0
    if (data.project_status) {
      p.value.status = data.project_status
      p.value.backend_running = ['starting', 'healthy'].includes(data.backend_status)
      p.value.frontend_running = ['starting', 'healthy'].includes(data.frontend_status)
    }
  }
  rt.backend_log_tail = data.backend_log_tail || ''
  rt.frontend_log_tail = data.frontend_log_tail || ''
  const be = data.backend_status || 'stopped'
  const fe = data.frontend_status || 'stopped'
  // 仅忙碌的那一侧保留中间态，另一侧照常刷新
  if (rtBusyBe.value) {
    if (rt.backend_status === 'stopping') {
      rt.backend_status = be === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.backend_status === 'starting') {
      rt.backend_status = be === 'stopped' ? 'starting' : be
    } else {
      rt.backend_status = be
    }
  } else {
    rt.backend_status = be
  }
  if (rtBusyFe.value) {
    if (rt.frontend_status === 'stopping') {
      rt.frontend_status = fe === 'stopped' ? 'stopped' : 'stopping'
    } else if (rt.frontend_status === 'starting') {
      rt.frontend_status = fe === 'stopped' ? 'starting' : fe
    } else {
      rt.frontend_status = fe
    }
  } else {
    rt.frontend_status = fe
  }
}

async function toggleUnlock() {
  if (!unlocked.value) {
    const ok = await confirm('解锁后可改骨架/领域。确认解锁？', {
      title: '解锁匹配',
    })
    if (!ok) return
    await api.patchMatch(p.value.id, { unlock: true })
    unlocked.value = true
    message.success('已解锁')
  } else {
    if (deviant.value) {
      message.warning('已偏离推荐，请先恢复推荐再锁定')
      return
    }
    await api.patchMatch(p.value.id, { unlock: false })
    unlocked.value = false
    message.success('已重新锁定')
  }
  await load()
}

async function resetMatch() {
  p.value = await api.patchMatch(p.value.id, { reset: true })
  form.archetype = p.value.archetype
  form.domain = p.value.domain
  form.theme = p.value.theme
  form.passwordHash = p.value.password_hash || 'none'
  unlocked.value = false
  ack.value = false
  message.success('已恢复推荐')
}

async function onArchDomChange() {
  try {
    p.value = await api.patchMatch(p.value.id, {
      archetype: form.archetype,
      domain: form.domain,
    })
    form.theme = p.value.theme
    ack.value = false
  } catch {
    form.archetype = p.value.archetype
    form.domain = p.value.domain
    form.theme = p.value.theme
  }
}

async function saveSoft() {
  p.value = await api.patchMatch(p.value.id, {
    theme: form.theme,
    llm_enabled: form.llm === 'on',
    password_hash: form.passwordHash,
  })
  message.success('已保存')
}

async function confirmMatch() {
  if (deviant.value) {
    const ok = await confirm('当前已偏离系统推荐。确认仍要用这套骨架/领域生成？', {
      title: '偏离推荐确认',
      type: 'warning',
    })
    if (!ok) return
  }
  p.value = await api.patchMatch(p.value.id, { confirm: true, ack: true })
  unlocked.value = false
  message.success(deviant.value ? '已按覆盖确认' : '已确认匹配')
  tab.value = 'generate'
}

async function startGenerate() {
  const res = await api.generate(p.value.id)
  message.success(res.message)
  await load()
  tab.value = 'generate'
  startPoll()
}

async function cancelCurrent() {
  if (!currentJob.value) return
  const ok = await confirm('确认取消该生成任务？进行中的步骤将中止。', {
    title: '取消任务',
    type: 'warning',
    positiveText: '确认取消',
  })
  if (!ok) return
  await api.cancelJob(currentJob.value.id)
  message.success('已取消')
  await load()
}

async function retryCurrent() {
  if (!currentJob.value) {
    await startGenerate()
    return
  }
  const res = await api.retryJob(currentJob.value.id)
  message.success(res?.message || '已从失败步骤续跑')
  await load()
  startPoll()
}

function downloadZip() {
  if (!canDownload.value) {
    message.error(downloadBlockedReason.value || '门禁未过 · 禁止下载 ZIP')
    if (p.value?.status !== 'generating') tab.value = 'gates'
    return
  }
  window.open(api.downloadUrl(p.value.id), '_blank')
}

function onDelete() {
  if (deleteBlocked.value) {
    message.warning(deleteBlockedReason.value || '请先停止运行后再删除')
    return
  }
  keepDb.value = false
  showDelete.value = true
}

async function confirmDelete() {
  if (!p.value || deleting.value) return false
  deleting.value = true
  try {
    const res = await api.deleteProject(p.value.id, { keepDb: keepDb.value })
    message.success(res?.message || '已删除')
    showDelete.value = false
    router.push('/')
    return true
  } catch (e) {
    message.error(e?.response?.data?.detail || e?.message || '删除失败')
    return false
  } finally {
    deleting.value = false
  }
}

async function rtAction(side, action) {
  const projectId = p.value?.id
  if (!projectId) return
  const epoch = viewEpoch
  const touchBe = side === 'all' || side === 'backend'
  const touchFe = side === 'all' || side === 'frontend'
  if ((touchBe && rtBusyBe.value) || (touchFe && rtBusyFe.value)) return
  if (touchBe) rtBusyBe.value = true
  if (touchFe) rtBusyFe.value = true
  if (side === 'all') rtPendingAll.value = action

  if (action === 'start' || action === 'restart') {
    if (touchBe) rt.backend_status = 'starting'
    if (touchFe) rt.frontend_status = 'starting'
  } else if (action === 'stop') {
    if (touchBe) rt.backend_status = 'stopping'
    if (touchFe) rt.frontend_status = 'stopping'
  }
  try {
    await api.runtimeAction(projectId, side, action)
    if (!viewActive(projectId, epoch)) return
    await load({ id: projectId })
    if (!viewActive(projectId, epoch)) return
    const deadline = Date.now() + (action === 'stop' ? 8000 : 20000)
    while (Date.now() < deadline && viewActive(projectId, epoch) && tab.value === 'runtime') {
      await refreshRuntime(projectId)
      if (_runtimeSettled(side, action)) break
      await new Promise((r) => setTimeout(r, 700))
    }
  } finally {
    if (touchBe) rtBusyBe.value = false
    if (touchFe) rtBusyFe.value = false
    if (side === 'all') rtPendingAll.value = ''
    if (viewActive(projectId, epoch) && tab.value === 'runtime') {
      await refreshRuntime(projectId)
    }
  }
}

function _runtimeSettled(side, action) {
  const be = rt.backend_status
  const fe = rt.frontend_status
  const beDone = be !== 'starting' && be !== 'stopping'
  const feDone = fe !== 'starting' && fe !== 'stopping'
  if (side === 'backend') return beDone
  if (side === 'frontend') return feDone
  if (action === 'stop') return be === 'stopped' && fe === 'stopped'
  return beDone && feDone
}

function openPreview() {
  if (rt.frontend_status !== 'healthy') {
    message.warning('前端未就绪，请先启动并等待健康')
    return
  }
  const url = rt.preview_url || frontendAddr.value
  if (url) {
    window.open(url, '_blank')
    return
  }
  message.warning('前端未就绪，请先启动并等待健康')
}

let logReqSeq = 0
async function loadLog(side, { silent = false } = {}) {
  logSide.value = side
  const seq = ++logReqSeq
  if (!silent) logLoading.value = true
  try {
    const res = silent
      ? await api.logsPoll(p.value.id, side)
      : await api.logs(p.value.id, side)
    if (seq !== logReqSeq || logSide.value !== side) return
    logText.value = res.content || ''
  } catch {
    /* 轮询静默；手动打开日志页时仍走默认 toast */
  } finally {
    if (!silent && seq === logReqSeq) logLoading.value = false
  }
}

let pollInFlight = false
const pollSyncHint = ref('')
const pollFailStreak = ref(0)

function startPoll() {
  stopPoll()
  pollSyncHint.value = ''
  pollFailStreak.value = 0
  pollTimer = setInterval(async () => {
    if (pollInFlight) return
    pollInFlight = true
    try {
      // 轻量轮询：只刷项目状态/Job/日志，不拉 catalog/schema
      await load({ syncTab: false, lite: true })
      if (tab.value === 'logs') await loadLog(logSide.value, { silent: true })
      if (!p.value || p.value.status !== 'generating') {
        stopPoll()
        pollSyncHint.value = ''
        // 结束后补一次完整刷新；人在日志/产物页则不强切 Tab
        if (p.value) {
          const keepTab = tab.value === 'logs' || tab.value === 'artifacts'
          await load({ syncTab: !keepTab, lite: false })
        }
      }
    } finally {
      pollInFlight = false
    }
  }, 1500)
}

function stopPoll() {
  if (pollTimer) clearInterval(pollTimer)
  pollTimer = null
  pollInFlight = false
}

watch(tab, (v) => {
  if (v === 'logs') loadLog(logSide.value)
  if (v === 'runtime') refreshRuntime()
  if (v === 'artifacts') loadArtifactView()
})

watch(
  () => route.params.id,
  async (id, prev) => {
    if (!id || id === prev) return
    viewEpoch += 1
    stopPoll()
    p.value = null
    loadError.value = ''
    await reload()
  },
)

onMounted(reload)
onUnmounted(() => {
  viewEpoch += 1
  stopPoll()
  detailCrumb.value = ''
})
</script>

<style scoped>
.er-toolbar {
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.er-zoom-btns {
  align-items: center;
  gap: 8px;
}
.er-zoom-label {
  min-width: 48px;
  text-align: center;
  font-variant-numeric: tabular-nums;
  font-size: 13px;
  color: var(--muted);
}
.er-frame {
  height: 72vh;
  overflow: hidden;
  border: 1px solid var(--line);
  background: var(--er-bg);
  cursor: grab;
  touch-action: none;
  user-select: none;
}
.er-frame:active {
  cursor: grabbing;
}
.er-canvas {
  display: inline-block;
  will-change: transform;
}
.er-canvas :deep(svg) {
  display: block;
  max-width: none;
  height: auto;
  pointer-events: none;
}
</style>
