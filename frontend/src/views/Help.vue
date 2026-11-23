<template>
  <div class="help-page surface-page">
    <h1 class="page-title">帮助文档</h1>
    <p class="page-desc">
      本说明面向运营人员：标准流程、交付条件与术语。卡壳时先看
      <a href="#help-card-四痛点">运营诊断 · 四痛点</a>。
    </p>

    <div class="help-toolbar">
      <n-input
        v-model:value="query"
        clearable
        placeholder="过滤卡片或术语…（如：状态话术、字典台、演示剧本、第一次出单）"
        style="max-width:360px"
      />
      <nav v-if="!qNorm" class="help-toc" aria-label="章节目录">
        <a
          v-for="sec in sections"
          :key="sec.title"
          class="help-toc-link"
          :href="'#' + sectionId(sec.title)"
        >{{ sec.title }}</a>
      </nav>
      <span v-else class="small muted">{{ filterHint }}</span>
    </div>

    <n-empty
      v-if="!visibleSections.length"
      description="没有匹配的说明，试试换个词"
      style="margin-top:32px"
    />

    <section
      v-for="sec in visibleSections"
      :id="sectionId(sec.title)"
      :key="sec.title"
      class="help-section"
    >
      <h2 class="help-section-title">{{ sec.title }}</h2>
      <div class="help-cards" :class="sec.grid || ''">
        <article
          v-for="card in sec.cards"
          :id="cardAnchor(card)"
          :key="card.title"
          class="help-card panel"
          :class="{ wide: card.wide }"
        >
          <div class="panel-hd">
            <h3>{{ card.title }}</h3>
            <span v-if="card.tag" class="pill pill-teal">{{ card.tag }}</span>
          </div>
          <div class="panel-bd help-body">
            <p v-if="card.lead">{{ card.lead }}</p>
            <ol v-if="card.steps?.length" class="help-steps">
              <li v-for="(step, i) in card.steps" :key="i">
                <strong>{{ step.title }}</strong>
                <p>{{ step.body }}</p>
                <p v-if="step.page" class="help-step-page muted">页面：{{ step.page }}</p>
              </li>
            </ol>
            <div v-if="card.table?.rows?.length" class="help-table-wrap">
              <table class="help-table">
                <thead>
                  <tr>
                    <th v-for="h in card.table.headers" :key="h">{{ h }}</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="(row, ri) in card.table.rows" :key="ri">
                    <td v-for="(cell, ci) in row" :key="ci">{{ cell }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <div v-if="card.liveTable === 'failCatalog'" class="help-table-wrap">
              <ContentLoading v-if="catalogLoading" :rows="3" compact show-label label="正在加载对照表" />
              <p v-else-if="catalogError" class="muted">{{ catalogError }}</p>
              <p v-else-if="!failCatalogRows.length" class="muted">没有匹配的失败类型</p>
              <table v-else class="help-table">
                <thead>
                  <tr>
                    <th>类型</th>
                    <th>含义</th>
                    <th>相关位置</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="row in failCatalogRows" :key="row.code">
                    <td><code>{{ row.code }}</code></td>
                    <td>{{ row.label }}</td>
                    <td class="help-mono">{{ row.fix_locus }}</td>
                    <td>
                      <a
                        class="help-jump"
                        :href="`/fail-analysis?code=${encodeURIComponent(row.code)}`"
                      >查分布</a>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
            <ul v-if="card.bullets?.length">
              <li v-for="(b, i) in card.bullets" :key="i">{{ b }}</li>
            </ul>
            <p v-if="card.links?.length" class="help-links">
              <a
                v-for="l in card.links"
                :key="l.href || l.hash || l.label"
                :href="l.href || l.hash"
                :target="l.href && !l.hash ? '_blank' : undefined"
                :rel="l.href && !l.hash ? 'noopener' : undefined"
              >{{ l.label }}</a>
            </p>
            <dl v-if="card.terms?.length" class="help-glossary">
              <div v-for="t in card.terms" :key="t.name" class="help-glossary-row">
                <dt>{{ t.name }}</dt>
                <dd>{{ t.def }}</dd>
              </div>
            </dl>
          </div>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NEmpty, NInput } from 'naive-ui'
import { api } from '../api'
import ContentLoading from '../components/ContentLoading.vue'

const route = useRoute()
const query = ref('')
const qNorm = computed(() => String(query.value || '').trim().toLowerCase())
const failCatalog = ref([])
const catalogLoading = ref(false)
const catalogError = ref('')

function sectionId(title) {
  return `help-sec-${String(title || '').replace(/\s+/g, '-')}`
}

function cardAnchor(card) {
  const slug = card.anchor || card.title || ''
  return `help-card-${String(slug).replace(/\s+/g, '-')}`
}

function scrollToHash(raw) {
  const id = String(raw || '').replace(/^#/, '')
  if (!id) return
  nextTick(() => {
    const el = document.getElementById(id)
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
  })
}

async function loadFailCatalog() {
  catalogLoading.value = true
  catalogError.value = ''
  try {
    failCatalog.value = await api.failAnalysisCatalog()
  } catch (e) {
    catalogError.value = e?.message || '对照表暂时加载失败'
    failCatalog.value = []
  } finally {
    catalogLoading.value = false
  }
}

onMounted(async () => {
  await loadFailCatalog()
  scrollToHash(route.hash || window.location.hash)
})
watch(
  () => route.hash,
  (h) => scrollToHash(h),
)

const failCatalogRows = computed(() => {
  const q = qNorm.value
  const rows = failCatalog.value || []
  if (!q) return rows
  return rows.filter((r) =>
    `${r.code}\n${r.label}\n${r.fix_locus}`.toLowerCase().includes(q),
  )
})

function cardBlob(card, { withTerms = true } = {}) {
  const parts = [card.title, card.tag, card.lead, card.anchor]
  for (const s of card.steps || []) parts.push(s.title, s.body, s.page)
  for (const b of card.bullets || []) parts.push(b)
  for (const l of card.links || []) parts.push(l.label)
  for (const h of card.table?.headers || []) parts.push(h)
  for (const row of card.table?.rows || []) {
    for (const cell of row) parts.push(cell)
  }
  if (withTerms) {
    for (const t of card.terms || []) parts.push(t.name, t.def)
  }
  return parts.filter(Boolean).join('\n').toLowerCase()
}

function filterCard(card, q) {
  if (!q) return card
  const terms = card.terms || []
  if (terms.length) {
    const termHits = terms.filter((t) => `${t.name}\n${t.def}`.toLowerCase().includes(q))
    const metaHit = cardBlob(card, { withTerms: false }).includes(q)
    if (metaHit) return card
    if (termHits.length) return { ...card, terms: termHits }
    return null
  }
  if (card.liveTable === 'failCatalog') {
    if (cardBlob(card).includes(q)) return card
    if (failCatalogRows.value.length) return card
    return null
  }
  return cardBlob(card).includes(q) ? card : null
}

const visibleSections = computed(() => {
  const q = qNorm.value
  return sections
    .map((sec) => {
      if (q && String(sec.title || '').toLowerCase().includes(q)) return sec
      const cards = (sec.cards || []).map((c) => filterCard(c, q)).filter(Boolean)
      if (!cards.length) return null
      return { ...sec, cards }
    })
    .filter(Boolean)
})

const filterHint = computed(() => {
  const n = visibleSections.value.reduce((acc, s) => acc + s.cards.length, 0)
  return n ? `匹配 ${n} 张卡片` : '无匹配'
})

const sections = [
  {
    title: '总览',
    cards: [
      {
        title: '侧栏分工',
        tag: '总览',
        anchor: '侧栏分工',
        wide: true,
        lead: '各栏职责单一，避免同一信息在多页重复呈现。',
        table: {
          headers: ['栏目', '职责', '不包含'],
          rows: [
            ['开工台', '当日待办总览：待匹配、生成中、复审、近七日失败与环境额度', '不上传材料、不重试单条任务'],
            ['项目', '上传分堆建项；筛选履约状态（待审/待发/已发）与待匹配/复审中', '不提供失败类型分布'],
            ['终稿吸收', '只有终稿时抽出要点、对照能力补齐；与「项目」并列', '不建项、不出包、不替代开题匹配'],
            ['任务队列', '单条任务进度、取消、重试与历史清理', '不按失败码排列排修优先级'],
            ['失败分析', '按类型/步骤/域汇总失败，提供相关位置与处理建议', '不替代项目详情中的日志与未通过清单'],
            ['帮助文档', '流程说明、对照表与术语', '不展示实时任务数据'],
            ['词表 / 状态话术 / 字典台 / … / 测试账号', '出包前可维护的中文与演示资产', '不替代匹配确认'],
            ['大模型 / Unsplash / 运行环境', '业务配置填充用量、图床与本机工具链/端口', '不进入业务项目列表'],
          ],
        },
        links: [
          { href: '/', label: '打开开工台' },
          { hash: '#help-card-本机怎么启动', label: '本机怎么启动' },
          { hash: '#help-card-第一次怎么出单', label: '第一次怎么出单' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-五步主路径', label: '五步主路径' },
        ],
      },
      {
        title: '本机怎么启动',
        tag: '上手',
        anchor: '本机怎么启动',
        lead: '最多两人用的本机工具：拉仓后按下面起服务即可，不必记一堆命令。',
        steps: [
          {
            title: '1 · 环境',
            page: '本机',
            body: '需要 Python 3.11+、Node 18+、JDK 17、Maven、MySQL 8。仓库根 README「第一次用 · 拉仓开工」有最短路径。',
          },
          {
            title: '2 · 启动',
            page: 'scripts\\launcher.bat',
            body: '双击或运行 launcher 打开本地控制台；按 1 启动全部服务。缺依赖时按 N 做环境自检。运营台地址一般是 http://127.0.0.1:5300 。',
          },
          {
            title: '3 · 进台',
            page: '开工台',
            body: '浏览器打开运营台；服务异常时先回到本地控制台按 N 做环境自检，再点「第一次怎么出单」。',
          },
        ],
        links: [
          { hash: '#help-card-第一次怎么出单', label: '第一次怎么出单' },
        ],
      },
      {
        title: '第一次怎么出单',
        tag: '上手',
        anchor: '第一次怎么出单',
        lead: '服务已起来后，用测试开题走通上传 → 匹配 → 生成 → 下载。',
        steps: [
          {
            title: '1 · 建项',
            page: '项目',
            body: '点「生成测试开题」下载 txt，再拖到上传区，确认分堆后创建项目。',
          },
          {
            title: '2 · 匹配',
            page: '匹配确认',
            body: '看推荐业务类型是否对得上开题；对得上就确认。需要时勾「我已看过」。',
          },
          {
            title: '3 · 生成与下载',
            page: '一键生成 → 质检交付',
            body: '一键生成；通过后跟顶栏下载 ZIP。卡住时：能清洗/重试/重打包就先做；反复同错再改生成逻辑。',
          },
        ],
        links: [
          { href: '/projects', label: '打开项目' },
          { hash: '#help-card-五步主路径', label: '五步主路径' },
        ],
      },
      {
        title: '产品定位',
        tag: '总览',
        lead: '毕设港工作台用于依据开题、任务书等材料完成选题匹配、工程生成、质量检查与本地预览；机器质检通过后可下载压缩包。人工审核后可直接标记已发出，或先标已审待发再发出。',
        bullets: [
          '以固定工程基线与能力运行时为主体；大语言模型仅填充业务配置，不承担业务代码编写。',
          '机器质检通过只代表可下载，不代表文案与业务逻辑已过人工审核。',
          '建议每日先查看侧栏「开工台」，再进入项目或任务队列处理。',
        ],
      },
      {
        title: '注意事项',
        tag: '规范',
        bullets: [
          '请勿将未通过质量检查的工程作为最终交付物提供给学生或指导教师；发出前请完成人工审核并标记「已发出」（或先「已审待发」暂存）。',
          '匹配确认前请认真阅读解析摘要；擅自更换领域可能导致能力组合与题目不符。',
          '预览仅供验收使用，不构成生产环境部署方案。',
          '界面与操作约定如有调整，以当前版本页面提示为准。',
        ],
      },
    ],
  },
  {
    title: '运营诊断',
    cards: [
      {
        title: '四痛点 → 先看哪',
        tag: '索引',
        anchor: '四痛点',
        wide: true,
        lead: '遇到阻塞时可按痛点跳转对应说明；本页仅作导航索引，不替代门禁与验收结果。',
        bullets: [
          '使用流程 → 侧栏「开工台」查看当日待办；详细步骤见「五步主路径」；项目内顺序为：匹配确认 → 一键生成 → 运行 → 产物/对照 → 交付复审。',
          '高频故障 → 「最常爆炸处置」卡；项目内优先查看匹配双显 / 质量检查未通过清单 / 任务日志 / 交付复审重打包；同类出包失败集中时使用侧栏「失败分析」。',
          '结果异常但原因不明 → 产物「交付复审」中的审计检查表（12 主项 + 理解偏差），并对照未通过清单 / 验收 / 质量摘要。',
          '开题措辞笼统 / 弱匹配偏多 → 「开题笼统时仍要写对」：已确认的开题为合同依据，出包不符应先核查工厂匹配与理解，不得归咎于材料。',
        ],
        links: [
          { href: '/', label: '开工台' },
          { hash: '#help-card-侧栏分工', label: '侧栏分工' },
          { hash: '#help-card-五步主路径', label: '五步主路径' },
          { hash: '#help-card-最常爆炸处置', label: '最常爆炸' },
          { hash: '#help-card-失败类型对照表', label: '失败类型对照表' },
          { hash: '#help-card-开题笼统时仍要写对', label: '开题笼统仍要写对' },
          { hash: '#help-card-交付复审', label: '交付复审说明' },
        ],
      },
      {
        title: '五步主路径',
        tag: '怎么用',
        anchor: '五步主路径',
        wide: true,
        lead: '从建项到可下载交付包：每步只完成一件事。细节见「流程与交付」各卡。',
        steps: [
          {
            title: '0 · 查看开工台',
            page: '开工台',
            body: '查看待匹配、生成中、复审与近七日失败类型，据此安排当日处理顺序。',
          },
          {
            title: '1 · 上传建项',
            page: '项目',
            body: '上传开题/任务书等材料，确认分堆后再创建项目。不同课题请勿强行合并为一堆。',
          },
          {
            title: '2 · 匹配确认',
            page: '项目详情 → 匹配确认',
            body: '核对领域、身份、主路径、持久层、Security、AI；存在双显时先确认拟选与出包是否一致。开题依据较弱时须勾选「主路径已核对」——核验的是工厂理解是否正确，而非为偏差预留借口。',
          },
          {
            title: '3 · 一键生成',
            page: '项目详情 → 一键生成',
            body: '调视觉选项（配色、门户首页，以及本域才出现的列表构图）后启动；弹窗做开题措辞核对（不扫工程）。生成后看质量检查实装。',
          },
          {
            title: '4 · 运行预览',
            page: '项目详情 → 运行',
            body: '启前后端点主路径：提交→审→完结是否真能走。',
          },
          {
            title: '5 · 产物与复审',
            page: '项目详情 → 产物/对照',
            body: '对库表/论文图/质量检查；工程改过则交付复审验收后重打包，再下 ZIP。',
          },
        ],
        links: [
          { hash: '#help-card-标准作业流程', label: '标准作业流程（细）' },
          { hash: '#help-card-上传与分堆', label: '上传与分堆' },
          { hash: '#help-card-生成前-开题措辞核对', label: '开题措辞核对' },
        ],
      },
      {
        title: '最常爆炸处置',
        tag: '防炸',
        anchor: '最常爆炸处置',
        wide: true,
        lead: '故障时的优先查看位置与处置要点。已确认的开题为合同依据；禁止改开题迁就工厂，也禁止将问题归咎于「材料薄」。',
        table: {
          headers: ['症状', '先看', '处置'],
          rows: [
            ['域摇摆 / 易混', '匹配确认双显', '按题名+正文核主路径与域；理解不清就解锁核清，不改开题'],
            ['门禁红 / 不能下包', '产物 → 质量检查未通过清单', '空壳优先；修 bake/皮/开关对齐后再验'],
            ['生成中编译挂', '日志 + Fix Agent', '允许 schema 重放；勿手改学生业务当常态'],
            ['开了 AI/Security 包里没有', '匹配确认双显', '开关与 bake 对齐，或标不支持；关则勿写已集成'],
            ['预览 OK 但 ZIP 旧', '交付复审', '验收通过后重打包'],
            ['「演示」字样 / 场景穿帮', '质量检查语义门禁', '洗学生可见面；身份跟 scene_scan'],
            ['措辞弱匹配多 / 出包像模具', '措辞核对 + 匹配确认', '见「开题笼统时仍要写对」——先查工厂是否写对老师确认的主路径'],
            ['多题同一种出包失败', '侧栏 → 失败分析', '查看类型分布与「相关位置」；优先修复集中出现的类型，勿逐单修改学生包'],
          ],
        },
        links: [
          { hash: '#help-card-开题笼统时仍要写对', label: '开题笼统仍要写对' },
          { hash: '#help-card-交付复审', label: '交付复审' },
          { hash: '#help-card-质量检查与交付', label: '质量检查' },
          { hash: '#help-card-失败分析', label: '失败分析' },
          { hash: '#help-card-失败类型对照表', label: '失败类型对照表' },
        ],
      },
      {
        title: '开题笼统时仍要写对',
        tag: '理解',
        anchor: '开题笼统时仍要写对',
        wide: true,
        lead: '开题措辞笼统、万能句多，不等于可以甩锅。「老师 / 客户已确认的开题」是合同：工厂写不出来，默认是匹配理解或 bake 不到位，不是材料的错。',
        bullets: [
          '禁止改开题迁就工厂；也禁止用「材料薄 / 套话」给错包开脱。',
          '弱匹配 / 依据弱 = 提醒运营更仔细核：题名、正文、谁对谁做什么、完结态——把主路径确认对，再生成。',
          '出包像模具、主路径不对、皮穿帮：对照开题修域 / 主路径入口 / 域皮 / 种子；登记偏差写清「工厂理解偏差」，不要写「材料不行」。',
          '仅当开题明确只要更窄主路径、且未宣称高级能力时，才可记「材料未要求」——不是「材料差所以交差」。',
          '硬边界（人脸/真支付/物联网等）该拒就拒并诚实双显；能 bake 的主路径必须写到可答辩。',
        ],
        links: [
          { hash: '#help-card-生成前-开题措辞核对', label: '开题措辞核对' },
          { hash: '#help-card-领域易混（先问清再确认）', label: '领域易混' },
        ],
      },
    ],
  },
  {
    title: '流程与交付',
    cards: [
      {
        title: '标准作业流程',
        tag: '流程',
        anchor: '标准作业流程',
        wide: true,
        lead: '与「运营诊断 → 五步主路径」同一条链；此处展开细则。',
        steps: [
          {
            title: '创建项目',
            page: '项目',
            body: '在「项目」页上传开题 / 任务书 / 功能清单等材料，确认分堆后再创建。格式、数量上限、同课题合并与多课题拆开等说明见下方「上传与分堆」。',
          },
          {
            title: '匹配确认',
            page: '匹配确认',
            body: '在「匹配确认」页核验推荐骨架、领域、身份场景、主路径入口（如有分叉：晨午检自报/绑岗/调宿等）、持久层，以及按需开关（Spring Security、AI 助手）。开题未写清「谁怎么用」时须勾选「主路径已核对」或解锁手改后再确认。开题推荐与当前出包不一致时双显（持久层 / Security / AI / 身份入口）。配色、布局、门户首页、本域列表构图等视觉选项在「一键生成」页调整；技术栈与 AI 开关不要放进视觉区。',
          },
          {
            title: '一键生成',
            page: '一键生成',
            body: '匹配确认后，在「一键生成」页调整视觉与生成选项（配色、质感、布局、字体、门户首页、本域列表构图、智能填充、密码策略；即时保存），再启动生成。列表构图只在该业务组出现，改的是页内排列，不改菜单和主路径。启动前会弹出「开题措辞核对」，对照开题功能行与工厂清单项名（不扫工程）。生成完成后在「质量检查」看「清单实装验收」，确认 ZIP 内真有对应实现。生成完成后可同页改选项并「按当前选项重新生成」。进度可在「任务队列」与项目详情中查看；业务配置填充会拆成多个 Unit 并发执行，详情见「大模型与填岛拆解」。',
          },
          {
            title: '答辩 PPT（后置）',
            page: '一键生成',
            body: '程序 bake 门禁通过后，在「一键生成」下半截填写封面信息（学校/学院/班级/姓名/学号/导师/校徽全部必填）并生成终期答辩 PPT。产物可检查与导出 PPTX（不进 ZIP）；对照子页做预览纠错。业务脏时须「按工程更新业务页」后再导出。',
          },
          {
            title: '预览与验收',
            page: '运行 · 产物/对照',
            body: '于「运行」页启动前后端预览做快速验收；于「产物」核对数据库（表结构 / E-R）、论文材料（各图可下 Draw.io / Mermaid；可点论文图对账）、学生端 API 与质量检查。工程有改动时，在「质检交付」验收并重打包，确保 ZIP 与工程目录一致。',
          },
          {
            title: '交付',
            page: '列表履约 / 详情',
            body: '机器质检通过后可下载 ZIP。列表「履约」列或详情页头可操作：审过可一步「标记已发出」；暂存用「已审待发」，发出时用「下载并发出」。重新生成会清掉人工标记与复审轮次。',
          },
        ],
        links: [
          { hash: '#help-card-五步主路径', label: '五步主路径（短）' },
          { hash: '#help-card-列表构图', label: '列表构图' },
        ],
      },
      {
        title: '列表构图',
        tag: '视觉',
        anchor: '列表构图',
        wide: true,
        lead: '「一键生成」视觉区里，门户首页之外还有按业务组出现的列表构图。只改列表页怎么排、信息密不密，不删菜单、不改主路径能力。当前领域不属于该组时，这项不出现。',
        table: {
          headers: ['页面上的名字', '什么题才有', '可选档'],
          rows: [
            ['内容列表构图', '影视 / 音乐 / 论坛 / 博客 / 文库', '刊头阅读流、封面墙、条目清单、双栏阅读台'],
            ['商品列表构图', '商城 / 餐饮 / 影院', '货架密铺；档口菜单板只给餐饮；排片选座行只给影院'],
            ['预约列表构图', '医院 / 场地 / 美容 / 仪器 / 酒店 / 租车 / 停车', '时段条；房态格只给酒店；车型档期卡只给租车、停车'],
            ['借用列表构图', '图书 / 器材 / 物资 / 采购 / 床位 / 驿站', '书架脊列只给图书；库存台账行；床位色块墙只给宿舍床位；驿站货架格只给快递'],
            ['报名列表构图', '活动 / 选课 / 失物 / 旅游', '活动海报墙、课表网、启事板、线路行程卡，各绑本域'],
            ['互动列表构图', '婚恋 / 双选 / 拼车 / 时间银行', '资料卡片墙、双选志愿卡、行程同行行。考试、问卷、投票不走这项'],
            ['跟进列表构图', '客户 / 打卡 / 考勤 / 资助 / 招聘 / 成绩 / 实习 / 房源', '阶段看板只给客户跟进；挂牌价签只给房源；其余用档案行'],
            ['报修列表构图', '宿舍 / 物业 / IT', '我的工单进度流、分类故障看板'],
            ['审批列表构图', '用章、报销、访客等审批类题目', '事项类型清单、待审收件箱'],
          ],
        },
        bullets: [
          '下拉里看不到的档，就是这个领域不能用，不要指望换皮冒充别的业务。',
          '名字旁边的小圆点可看当前档的线框示意。改完即时保存；要进学生包须「按当前选项重新生成」。',
          '和行业配色、界面质感、门户布局、字体、门户首页各管各的。持久层、Spring Security、AI 助手仍在「匹配确认」，不进视觉区。',
        ],
      },
      {
        title: '上传与分堆',
        tag: '上传',
        anchor: '上传与分堆',
        wide: true,
        lead: '上传后先分堆、再确认创建。上限与「直接选文件」相同：只计展开后的 PDF / Word / TXT 份数。',
        bullets: [
          '格式：PDF / Word（.doc / .docx）/ TXT；可多选、拖文件夹，或选择 / 拖入 zip。文件夹与 zip 内非材料文件会跳过。',
          '数量：展开后合计最多 8 份。例：8 个 zip 各含 1 份开题 → 8 份，可通过；1 个 zip 内 9 份 → 拒绝；合计超过 8 → 拒绝，不会截取前 8 份。',
          '同课题：开题 + 任务书 + 功能清单等会并成一个项目。',
          '不同课题：一次拖入多份不同开题，会拆成多个项目；确认弹窗可「全部拆开」或「合并为一个」后微调。',
          '同领域不同实现（如都是图书皮，一套借阅、一套二手交易）会尽量拆开，避免烤成一个项目。',
          '无关材料（简历、空文件、纯闲文等）会剔除，不参与匹配。',
          '确认前不会建项。弹窗内可「追加材料」并入当前方案后重新分堆（与已有合计仍 ≤8）；弹窗外再传下一批则进入队列，不顶掉当前内容；可点「查看分堆」切换，或确认 / 取消后自动翻下一份。',
          '需要超过 8 份材料时，请分多次上传（每次 ≤8）；项目总数不受 8 限制。',
        ],
      },
      {
        title: '质量检查与交付',
        tag: '交付',
        anchor: '质量检查与交付',
        wide: true,
        lead: '机器质检通过只代表可下载。关键项未通过时不可下载。人工审核后可在列表或详情直接标「已发出」；需要暂存待发再用「已审待发」。工程变更后须先验收再重打包。',
        bullets: [
          '检查明细见项目详情「产物 / 对照 → 质量检查」。含语义门禁（学生可见面「演示」字样、场景身份穿帮）与交付质量摘要。',
          '项目列表顶部「待审 / 已审待发 / 已发出」可点开 backlog；履约列无需进详情即可下载与标记。',
          '工程基线或运行时升级后，既有工程目录可能与当前规则不一致，须重新生成。',
          '质量检查通过仅表示结构与声明能力达标，不替代运营人员对业务路径的人工预览确认。',
        ],
      },
      {
        title: '交付复审',
        tag: '复审',
        anchor: '交付复审',
        wide: true,
        lead: '「质检交付 → 交付复审」用于对照开题收窄偏差：已通过项纳入已通过清单；验收通过后方可重打包更新交付包。不进学生 ZIP。感觉不对时用同页审计检查表（12 主项 + 理解偏差）对着勾，并对照未通过清单 / 质量摘要。',
        bullets: [
          '首包直发：首次打包未进入复审时，质检通过即可下载；工程改动后 ZIP 可能过期，须验收并重打包。',
          '进入复审：主动开启后，每轮「验收」冻结已通过的门禁与 checklist 项到已通过清单；未通过项留在未通过清单待收敛。复审进行中会拦截重新生成。',
          '验收：检查单调性（已通过清单不得回退）并刷新质量摘要；有回退或 open 偏差登记时不可重打包。',
          '重打包：验收通过后重新打包 ZIP，使交付包与当前工程目录一致。重打包不能代替修工厂；门禁须改 bake/基线时，请先「结束复审」再重新生成。',
          '偏差登记：记录工厂与开题不一致之处（仅运营可见）；写「工厂理解偏差」，禁止甩锅「材料薄」。待结案项须处理后再重打包。',
          '死锁出口：ZIP 过期要重打包、但门禁不过又拦重打包、同时复审又拦重跑时——点「结束复审并去重新生成」，不要空等重打包。',
          '审计检查表：运营自检 12 主项 +「理解偏差」（完成度写库、每业务组代表+邻域/触点回归、八张材料图、视觉轴、可见面工厂腔等）；机器全绿仍可能写错老师已确认的主路径——对着开题核，修工厂。',
          '导出交接包：供线下交接或留档，不含于学生交付物。',
          '按钮悬停有一句操作说明；重打包不可用时悬停可见原因。',
        ],
        links: [
          { hash: '#help-card-四痛点', label: '四痛点索引' },
        ],
      },
      {
        title: '生成前 · 开题措辞核对',
        tag: '生成前',
        anchor: '生成前-开题措辞核对',
        wide: true,
        lead: '启动生成前弹出：开题功能行 ↔ Spec 清单项名的静态措辞对照（不调大模型、不扫 workspace）。',
        bullets: [
          '与「质量检查 → 清单实装验收」不是同一功能；措辞绿了不代表包内已实装。',
          '顶部覆盖比例（如 8/8 已覆盖）一眼判断能否放心生成；不阻断生成。',
          '已对照 / 措辞弱匹配 / 措辞待核 / 工厂实现模块：见弹窗分区说明。',
          '弱匹配 / 待核偏多：对照开题核域与主路径是否理解对；老师已确认的内容写不出来，责任在工厂。',
        ],
      },
      {
        title: 'AI 助手（按需开关）',
        tag: 'AI',
        anchor: 'AI助手',
        wide: true,
        lead: '学生包智能客服/导购挂件：匹配确认与 Spring Security 同级开关；默认关，开题点名则推荐开。不是新领域，不塞进骨架/持久层/一键生成视觉区。详细对照见仓库 docs/ai-opening-delivery-map.md。',
        bullets: [
          '接 A 拒 B：主路径仍是商城/借阅/报修等业务、特色节写智能客服/导购/助手/大模型问答 → 接并开开关；题眼是 RAG 平台/向量库工程/自训 CNN/多 Agent 平台 → 标不支持，禁止用聊天壳冒充整题已齐。',
          '一个跨域岛：农产导购、图书问答、宿舍助手 = 同一 ai_assistant；只换 FAQ 种子与页面标题。FAQ 分类名与货架/假别/工单类型同字（农产→水果/蔬菜/粮油；药店/美妆/汽配等零售软皮走 retail_*，与货架分类同字）。',
          '出包能力（开则）：门户右下角悬浮对话；Spring AI + DeepSeek（学生自配 DEEPSEEK_API_KEY，工厂 Key 禁止进 ZIP）；无 Key 回落知识表/业务摘要；管理端 AI 知识库 + 统计（不是用户同款聊天窗）。',
          '只读接业务：按意图调用本包已开 Store（商品/订单/办理票/预约/公告/推荐/收藏/积分券/考试问卷投票等）；不下单、不改状态、不另写一套 SQL。',
          '语音播报用浏览器 Web Speech；图片入口按品类/文件名匹配知识——论文写清实现路径，禁止写成自研语音模型或 CNN 以图搜图。',
          '拟选≠出包须双显（与 Security 同交互）。关开关则无 cap、无 SQL 种子、无菜单入口。验收：重新 bake 后看悬浮窗、知识库种子、pom 含 spring-ai-deepseek、README 含 Key 说明。',
          '易混：工厂「大模型」页只服务运营填岛/论文图文，与学生包运行时 AI 不是同一条链路；「知识库」问答走 AI 助手，「资料下载」走文库 doclib，两词都有则双挂分写；规则「猜你喜欢」≠ 协同过滤。',
        ],
      },
      {
        title: '质量检查 · 清单实装验收',
        tag: '包后',
        anchor: '清单实装验收',
        wide: true,
        lead: '生成完成后，在项目详情「产物 → 质量检查」扫描 workspace/ZIP，核对清单各项是否真有路由与实现。',
        bullets: [
          '表格「清单项 + 实现状态」即实装验收；P3a 门禁「清单实装 · 核心项」与此同源。',
          '与生成前「开题措辞核对」互补：先措辞对齐再生成，再实装验收再下载/演示。',
          '未通过时先查领域/生成是否完整，勿与措辞核对弹窗混为一谈。',
        ],
      },
    ],
  },
  {
    title: '产物对照',
    grid: 'cols-3',
    cards: [
      {
        title: '数据库',
        tag: '产物',
        lead: '「产物 / 对照 → 数据库」查看表结构与 E-R 图，供「数据库设计」章节使用。',
        bullets: [
          '字段类型按标准 MySQL 写法（如 varchar(60)）；可切换合并类型 / 类型·长度分列。',
          '单表复制为制表符文本，可贴 Word「文本转换成表格」。',
          '物理全量可含辅助表；「6～15」看论文概念实体数，不拿物理张数打红。出包硬顶另计费（平台壳可豁免）。',
          'E-R 总图默认「论文概念」精简（藏登录/会话等壳表，角色收回用户；实体 + 联系 + 基数；中间表画成 N:M），可切「全量」对账；实体属性图只含自身字段（无外键）。物理表在「表结构」全量列出（业务/辅助分显）；可一键复制/下载「逻辑设计 + 物理设计」正文（同源 schema.sql，含辅助表、禁止编造）。可复制 PNG / 下载矢量；「导出全部 Draw.io」一文件多页（每实体一页）；几何翻车可下同源 Draw.io 手调。',
        ],
      },
      {
        title: '论文材料',
        tag: '产物',
        lead: '「产物 → 论文材料」：功能模块图、系统逻辑架构图、系统类图、系统序列图、系统活动图、用例图、用例描述表与软件测试用例。结构从交付包（菜单 / SQL / Java）推导，与 ZIP 同源。模块图按身份以交付菜单为叶子真源；类图按 schema.sql + bake 包 Java（三栏 UML）；序列/活动固定 3 张可勾选，四槽位 / 三泳道，文案取自 bake；用例图按角色走查菜单；描述表默认 4 个主路径；测例按交付菜单推导。',
        bullets: [
          '三档导出同源：PNG/SVG 快照 · Mermaid（结构参考，可贴 https://app.diagrams.net/）· Draw.io（可拖框手调；厂内叠图/交叉时的主兜底）。用例图另可下 StarUML .mdj。',
          '规则红：老师规矩确定性闸未过则禁可交导出。「论文图对账」分两栏：须改＝规则铁证；待核＝LLM 嫌疑（不当老师，需打开材料卡核对）。',
          '模块图可按身份 / 按业务切换；类图可拖拽；几何未齐时用 Draw.io 收尾，不代替以后修厂内排版。',
          '用例描述表 / 测例：复制表格可贴 Word；测例 5～9 字段可选（默认 6）。大模型只润色测例文案，不增删用例。',
        ],
      },
      {
        title: '学生端 API',
        tag: '产物',
        lead: '「产物 → 学生端 API」按工作区 Controller 源码列出实有 Mapping（对准实包，不按风格藏接口；不是 Swagger 运行时文档），便于对照主流程验收。',
        bullets: [
          '可按门户 / 管理端等面筛选，可搜索路径或处理函数。',
          '命中主流程契约的接口会标注契约键（路径精确匹配，不整树误标）。',
          '复制为「方法 + 路径」；联调基址取「运行」页。仅供运营端，不含于交付包。',
          '「运行」页只负责启停预览；「全量冒烟」按本域 flow_api 模拟页面主路径（含借+约双链、收藏等），只打已 healthy 的学生 API。未启动会提示前往运行页，不会自动启动。',
          '冒烟结果分工厂错 / 学生错 / 跳过：学生端 message 原样展示，不改写。',
        ],
      },
    ],
  },
  {
    title: '领域匹配',
    cards: [
      {
        title: '领域易混（先问清再确认）',
        tag: '防坑',
        anchor: '领域易混（先问清再确认）',
        wide: true,
        lead: '匹配确认前先分清客户原话落在哪条主路径；下列成对易混须双侧成立，禁止只显一侧。完整清单见仓库 docs/domain-skin-gap-analysis.md §2。',
        bullets: [
          '实习管理系统：交周报（实习周报 INTERN）还是投简历找岗（招聘投递 RECRUIT）？INTERN 默认「我的周报」选已建档岗；开题写岗位与学生绑定/一人一岗则资料绑岗（单位+岗位对齐本岗）。岗位说明≠「我的=多单位」、≠招聘目录。',
          '活动报名 vs 选课：社团/志愿占名额（活动）≠ 公选课学分（选课）。',
          '考勤：请假销假单据（考勤请假）≠ 健康打卡/晨午检（事件上报）；人脸/GPS 硬件考勤不在本期。',
          '宠物：门诊挂号（医院）≠ 流浪动物领养（失物/认领壳）。',
          '快递驿站取件 ≠ 跑腿代买商城；宾馆客房预约+附加消费（具名 HOTEL）≠ 会议室预约+小卖部下单（交叉 X-SHOP-RESERVE → GENERIC）；借阅+二手+预约三合一 / 智慧校园 → 拒绝。',
          '真交叉须开题写清两套玩法：X-BORROW-SHOP（借阅+二手 / 点餐+报修）、X-BORROW-RESERVE（图书+座位；仪器借+机时走 INSTRUMENT）、X-SHOP-RESERVE（下单+预约）；样见 data/samples/交叉预设开题。',
          '实验室：安全准入 ≠ 耗材/试剂申领（物资领用）≠ 纯器材借用 ≠ 大型仪器借+机时（仪器机时 INSTRUMENT）。',
          '物业：报修工单可含「投诉建议」类型；独立投诉专版深皮仍见清单 S-21。家政上门时段预约（美容美发/预约 SALON）≠ 小区物业报修工单（物业 PROPERTY）；消防/设备巡检打卡（事件 EVENT）≠ IT/校园网报修工单（IT）。',
          '食安风险排查/追溯台账（事件 EVENT）≠ 食堂/档口点餐下单（点餐 FOOD）；题名含食品安全/风险排查时勿因正文食堂档口误落点餐。',
          '资助申请 ≠ 报销/用章；相亲牵线 ≠ 导师双选；宿舍报修 ≠ 床位分配；成绩更正 ≠ 网上评教。',
          '旅行社线路跟团报名（旅游 TOUR）≠ 客房预约（酒店 HOTEL）≠ 社团活动报名（活动 ACTIVITY）≠ 拼车结伴（拼车 CARPOOL）。',
          '景区/演出领票占名额（活动 ACTIVITY）≠ 影院选座购票座位图（影院 CINEMA）。',
          '校园跑腿代买订单（商城 SHOP）≠ 快递驿站取件核销（快递 PARCEL）。',
          '充电桩/共享车位时段预约（车位 PARKING）≠ 临时车辆通行证备案发码（通行证 CARPASS）。',
          '点播课/课程视频库播放（媒资 MEDIA）≠ 公选课选课占名额（选课 COURSE）；表白墙发帖（论坛 FORUM）≠ 院刊资讯浏览（博客 BLOG）。',
          '考试题库/组卷/自动判分（在线考试 EXAM）≠ 简易问卷填写回收（问卷 SURVEY）≠ 网上评教多维打分（评教 EVAL）；党建/驾校/安全答题同 EXAM 换皮；实验室开题写「准入考试/先考试」→ 先考后申挂 exam。',
          '十佳/评选在线投票计票（投票 VOTE）≠ 社团活动报名占名额（活动 ACTIVITY）；开题同时写报名+投票 → 活动域并挂 vote（复合）。',
          '制度/课件文库下载台账（文库 DOCLIB）≠ 图书借阅归还（图书 LIBRARY）≠ 院刊资讯收藏（博客 BLOG）；「知识库」若指问答/FAQ → AI 助手，若指附件下载 → 文库，两词都有则双挂。',
          '拼车/结伴行程同行意向（拼车 CARPOOL）≠ 婚恋牵线（交友 DATING）≠ 学习搭子互选（组队 MUTUAL）≠ 活动报名（活动 ACTIVITY）；无地图导航。',
          '时间银行志愿时长账户存取核销（时间银行 TIMEBANK）≠ 劳动项目时长认定（劳动 LABOR）≠ 社团活动报名（活动 ACTIVITY）。',
          '影院选座购票座位图下单（影院 CINEMA）≠ 影视点播收藏（影视 MEDIA）≠ 图书馆座位时段预约（场地 MEETING）≠ 演出报名领票（活动 ACTIVITY）。',
          '三级审批/初审复审终审（会签 multi_approve，开题写到才挂）≠ 两级初审终审 ≠ 任意可配置工作流引擎；开题写「本期不」多级会签则不开。',
          '仓储入库出库+库存流水（物资 ASSET + stock_io）≠ 采购申购审批（采购 PROCURE）≠ 多仓/WMS/ERP 财务一体化 ≠ RFID 全链路盘点。',
          '实习鉴定本地签章图+勾选同意（实习 INTERN + e_sign）≠ 法大大/上上签/CA 第三方电子签平台。',
          'OA：用章 / 用车 / 开具证明须裁成单一申请主路径；三联一题拒绝冒充。',
          '售前可先问清：见清单 §13.1「客户原话 → 先问清的一句」。',
        ],
      },
      {
        title: '硬边界（不接）',
        tag: '边界',
        lead: '下列不纳入换皮全覆盖，继续拒绝或标超出演示范围：',
        bullets: [
          '人脸 / 指纹 / 闸机硬件；GPS 轨迹考勤 / 社区矫正定位。',
          '真微信支付 / 支付宝对接；小程序 / iOS / Android 原生。',
          '物联网传感器 / 真门禁开锁；疾控/医保/银行直连。',
          '智慧校园 N 合一 / 三主路径以上；用章+用车+证明 OA 三联；硕博真实全流程业务系统。',
          'AI 主产品：RAG/向量库工程、自训 CNN、真以图搜图、协同过滤/矩阵分解当主交付、多 Agent 自动下单派单平台——禁止用 FAQ 聊天壳冒充整题已齐（业务系统旁挂问答仍可走开助手开关）。',
        ],
      },
      {
        title: '换皮全覆盖清单索引',
        tag: '索引',
        wide: true,
        lead: '运营对照仓库 docs/domain-skin-gap-analysis.md；样例均在 data/samples/，可直接上传匹配。AI 开题对照另见 docs/ai-opening-delivery-map.md。',
        bullets: [
          '§2 易混对 M-01～M-15：本页「领域易混」卡 + test_confusion_pairs。',
          '§3 深皮 S-*：data/samples/深皮开题/（S-01…S-81，共 60 份；索引见目录 00-说明.txt）。',
          '§4 预设 P-*：申请预设开题/、学工预设开题/、长尾预设开题/（P-01～P-29；P-30 三联拒绝）。',
          '§5 能力 C-*：考试/问卷/投票/文库/拼车/时间银行/影院/会签/进销存/签章等 *预设开题/；C-05～C-10 挂载见对应 P 样例。',
          '§6 交叉 X-*：交叉预设开题/（X-01 点餐+报修、X-02 图书+座位、X-03 下单+预约）与图书借阅与二手交叉开题。',
          '进度总览见清单 §9；能力矩阵见 docs/capabilities.md；领域组见 docs/domains.md。',
        ],
      },
    ],
  },
  {
    title: '资产台',
    cards: [
      {
        title: '资产台总览',
        tag: '配置',
        anchor: '资产台总览',
        wide: true,
        lead: '侧栏资产台维护出包时注入学生包的结构化资产。运行真源在工厂库表；「导入初始…」仅追加缺失项，不覆盖已有记录。改动对之后新生成的包生效，不会回写已下载的 ZIP。',
        table: {
          headers: ['栏目', '解决什么', '出包落点'],
          rows: [
            ['词表维护', '库表/列的中文名', 'schema.sql 注释'],
            ['状态话术', '状态码的列表名、主操作与空态文案', '状态展示与按钮文案'],
            ['字典台', '业务枚举与下拉选项', '筛选与表单选项'],
            ['演示剧本', '答辩演示步骤与所需业务数据', '演示步骤清单'],
            ['开关建议', '开题扫词 → 匹配页建议卡', '鉴权 / AI 助手等推荐值'],
            ['能力说明', '能力岛 README 段与菜单入口', '开则注入 / 关则禁宣称'],
            ['错误码中文', '业务错误码默认中文', 'error-messages.json / 空消息回落'],
            ['控件语义', '字段标签启发式 → 控件', 'fieldWidgetRules.js / 档案控件'],
            ['菜单矩阵', '岗位 × 菜单入口', 'schema.menus 补齐缺项'],
            ['规则参数', '超时 / 提前量 / 倍率等默认值', 'schema.ruleParams 与已知键补缺'],
            ['表关系叙事', '表边一句人话', 'schema.erEdgeCopy（论文库设旁注）'],
            ['测试账号', '三端演示账号与登录提示', 'schema.demoAccounts'],
          ],
        },
        bullets: [
          '日常出单不必先改资产台；当某域状态名不对、下拉缺项、或答辩列表空空时再到对应台补齐。',
          '「检查待补」按选定域扫描缺口；有待补时在「待补」页登记，标识字段锁定，只补展示内容。',
          '与匹配确认、一键生成分工：资产台管「写什么中文 / 准备什么演示数据 / 扫哪些开关词 / 能力怎么写进说明书 / 菜单是否漏挂 / 规则默认值 / 表边人话 / 演示账号」，匹配管「做什么业务」。',
          '只有终稿、没有开题时去工作台「终稿吸收」，不在本栏。',
        ],
        links: [
          { hash: '#help-card-词表维护', label: '词表维护' },
          { hash: '#help-card-状态话术', label: '状态话术' },
          { hash: '#help-card-字典台', label: '字典台' },
          { hash: '#help-card-演示剧本', label: '演示剧本' },
          { hash: '#help-card-开关建议', label: '开关建议' },
          { hash: '#help-card-能力说明', label: '能力说明' },
          { hash: '#help-card-错误码中文', label: '错误码中文' },
          { hash: '#help-card-控件语义', label: '控件语义' },
          { hash: '#help-card-菜单矩阵', label: '菜单矩阵' },
          { hash: '#help-card-规则参数', label: '规则参数' },
          { hash: '#help-card-表关系叙事', label: '表关系叙事' },
          { hash: '#help-card-测试账号', label: '测试账号' },
          { hash: '#help-card-终稿吸收', label: '终稿吸收（工作台）' },
          { href: '/zh-lexicon', label: '打开词表维护' },
        ],
      },
      {
        title: '词表维护',
        tag: '配置',
        anchor: '词表维护',
        wide: true,
        lead: '给库表 / 列起中文名，出包写入 schema.sql 的 COMMENT。列名本身保持英文。跨域默认可被具名域覆盖；改完后对新生成的包生效。',
        steps: [
          {
            title: '1 · 打开台面',
            page: '侧栏 → 词表维护',
            body: '先「导入初始词表」补齐出厂种子；用域 / 关键字筛选查看现有词条。',
          },
          {
            title: '2 · 检查缺口',
            page: '待补',
            body: '选定业务域后点「检查待补」。交付库里有列、词表无中文名时会出现在待补列表。可「生成建议草稿」一键填建议中文，再人工确认。',
          },
          {
            title: '3 · 登记或修订',
            page: '登记词条 / 改词条',
            body: '填写表名、列名与中文注释。域可选「跨域壳默认」；具名域优先生效。标识字段（表/列/域）登记后锁定，只改展示中文。',
          },
        ],
        bullets: [
          '只管库表 COMMENT 中文，不管页面按钮话术（见状态话术）或下拉枚举（见字典台）。',
          '「导入初始词表」只追加缺失项，不覆盖已有记录（含手工改过的）。',
          '修订后须重新生成 / 重打包才会进入学生 ZIP；已发出包不会自动回写。',
        ],
        links: [
          { href: '/zh-lexicon', label: '打开词表维护' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-状态话术', label: '状态话术' },
          { hash: '#help-card-字典台', label: '字典台' },
        ],
      },
      {
        title: '状态话术',
        tag: '配置',
        anchor: '状态话术',
        wide: true,
        lead: '把业务状态码转成学生可见的中文：列表徽章、主操作按钮、该态下列表为空时的提示。一条记录由域、状态机、状态码唯一确定。',
        steps: [
          {
            title: '1 · 打开台面',
            page: '侧栏 → 状态话术',
            body: '先「导入初始话术」补齐出厂种子；再用域 / 状态机筛选查看现有条目。',
          },
          {
            title: '2 · 检查缺口',
            page: '待补',
            body: '选定具体业务域后点「检查待补」。实体状态在台中无对应话术时会出现在待补列表。',
          },
          {
            title: '3 · 登记或修订',
            page: '登记话术 / 改话术',
            body: '填写列表名、主操作、空态文案与适用角色。域可选「跨域壳默认」供多数域共用；具名域优先生效。',
          },
        ],
        bullets: [
          '状态机对应业务对象（如订单、单据）；状态码对应节点（如 pending）。',
          '不在此配置「谁能点下一步」——流转权限属于能力与角色，不在本台。',
          '修订后重新生成项目才会进入新包；已发出 ZIP 需重打包或重新生成。',
        ],
        links: [
          { href: '/status-copy', label: '打开状态话术' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '字典台',
        tag: '配置',
        anchor: '字典台',
        wide: true,
        lead: '维护业务枚举：售后类型、报修优先级、商品分类等。同一字典键下的多条值码构成学生包中的下拉与筛选项。',
        steps: [
          {
            title: '1 · 打开台面',
            page: '侧栏 → 字典台',
            body: '「导入初始字典」追加出厂枚举；按域或字典键筛选查看。',
          },
          {
            title: '2 · 检查缺口',
            page: '待补',
            body: '选定域后检查期望枚举是否齐全；缺值码时进入登记。',
          },
          {
            title: '3 · 登记枚举',
            page: '登记枚举',
            body: '填写域、字典键、值码与展示名；可选皮、排序与启用。皮仅在软皮差异（如商城细分品类）时使用，默认可留空。',
          },
        ],
        bullets: [
          '下拉选项以本台为真源；禁止在学生包页面手写一套平行选项。',
          '可筛选搜索允许，创建库外新值不允许——与控件规范一致。',
          '关闭「启用」后该项不再注入新包，历史记录仍保留。',
        ],
        links: [
          { href: '/dict-values', label: '打开字典台' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '演示剧本',
        tag: '配置',
        anchor: '演示剧本',
        wide: true,
        lead: '为各域配置答辩演示步骤：操作角色、步骤标题，以及该步所需业务数据（业务对象、最少条数、可选状态范围）。用于保证演示时工作台有可操作数据，而不是空列表。',
        steps: [
          {
            title: '1 · 打开台面',
            page: '侧栏 → 演示剧本',
            body: '「导入初始剧本」为各域追加默认步骤；按域或剧本筛选。',
          },
          {
            title: '2 · 检查缺口',
            page: '待补',
            body: '选定域后检查是否已有默认剧本；缺失则登记至少一步。',
          },
          {
            title: '3 · 配置步骤',
            page: '登记步骤',
            body: '填写步号、操作角色、步骤标题；选择业务对象与最少条数。状态范围用于收窄可用记录，默认可留空。',
          },
        ],
        bullets: [
          '所需数据表示「演示该步时库中至少应具备的业务记录」，例如订单 ≥ 1。',
          '剧本标识默认 default；同域可按皮区分软皮差异，多数域皮留空即可。',
          '本台不替代浏览器逐页点验；它保证数据底线，验收动线仍按项目预览与交付复审执行。',
        ],
        links: [
          { href: '/demo-scripts', label: '打开演示剧本' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-交付复审', label: '交付复审' },
        ],
      },
      {
        title: '开关建议',
        tag: '配置',
        anchor: '开关建议',
        wide: true,
        lead: '维护「开题出现某词 → 建议开启某开关」的扫词规则。命中后在匹配确认展示证据与建议；推荐值可预填，须运营确认后才锁定，不自动改开题。',
        steps: [
          {
            title: '1 · 维护扫词',
            page: '侧栏 → 开关建议',
            body: '「导入初始扫词」追加出厂规则；按开关筛选，登记提示词、证据句与是否建议开启。',
          },
          {
            title: '2 · 匹配页消费',
            page: '项目 → 匹配确认',
            body: '开题命中提示词时出现「开关建议」卡，列出证据。下方解锁后确认鉴权 / AI 助手等开关。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子中应有扫词的开关若台内无规则，会出现在待补列表。',
          },
        ],
        bullets: [
          '「建议开启」且「可交付」时，匹配推荐会预填对应开关；不可交付的命中仅记录，不推荐开启。',
          '低置信或未点名时仍须人工核域；本台禁止代替确认勾选。',
          '与 AI 助手能力岛、Spring Security 开关同轴；工厂运营 Key 禁止进入学生 ZIP。',
        ],
        links: [
          { href: '/addon-suggest', label: '打开开关建议' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-AI助手', label: 'AI 助手说明' },
        ],
      },
      {
        title: '能力说明',
        tag: '配置',
        anchor: '能力说明',
        wide: true,
        lead: '为按需能力岛维护学生 README 说明段、菜单入口与「宣称针」。能力开启则注入对应 FAQ；关闭则 README 不得残留宣称针，避免假集成。',
        steps: [
          {
            title: '1 · 维护说明卡',
            page: '侧栏 → 能力说明',
            body: '「导入初始说明」追加出厂卡（Spring Security / AI 助手）；编辑 README 说明段、菜单入口与宣称针。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成 → README',
            body: '开启时写入对应 README 槽；关闭时槽为空，并可用宣称针做诚实校验。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子能力若缺卡或正文为空，会出现在待补列表。',
          },
        ],
        bullets: [
          '与开关建议分工：建议卡管「开题是否点名」；说明卡管「开了以后说明书写什么」。',
          '菜单入口字段供对账（如 ai_assistant / ai_knowledge），挂菜单仍走既有 bake 能力链。',
          '工厂运营 Key 禁止进入学生 ZIP；说明书只写学生自配环境变量。',
        ],
        links: [
          { href: '/cap-cards', label: '打开能力说明' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-开关建议', label: '开关建议' },
        ],
      },
      {
        title: '错误码中文',
        tag: '配置',
        anchor: '错误码中文',
        wide: true,
        lead: '维护业务错误码的默认中文。出包写入学生包 error-messages.json；接口返回空消息时回落本台文案，避免英文码露脸。',
        steps: [
          {
            title: '1 · 维护错误码',
            page: '侧栏 → 错误码中文',
            body: '「导入初始错误码」追加出厂九码；可改默认中文。与骨架 ErrorCode 枚举对齐。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '写入 backend 资源 error-messages.json，并注入 schema.errorCopy。业务抛错若自带中文句则优先用业务句。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '期望错误码缺行或中文为空时进入待补。',
          },
        ],
        bullets: [
          '不管工厂腔词表（FACTORY_UI_FORBIDDEN）；只管学生可见业务错误默认句。',
          '骨架内置回落与种子同文，缺 JSON 时仍有中文底线。',
        ],
        links: [
          { href: '/error-copy', label: '打开错误码中文' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '控件语义',
        tag: '配置',
        anchor: '控件语义',
        wide: true,
        lead: '维护档案字段「标签/键启发式 → 控件」规则。类型直映（date→日期选择器等）由代码保证；本台扩展可维护的标签规则，出包投影为 fieldWidgetRules.js。',
        steps: [
          {
            title: '1 · 维护规则',
            page: '侧栏 → 控件语义',
            body: '「导入初始规则」追加出厂启发式；登记匹配范围、模式、适用类型与目标控件。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '工厂台仍用规则形；bake 投影写入 fieldWidgetRules.js（labelHasAny / labelIsAny），由 archiveFieldWidget 读取。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子规则缺行或模式/控件非法时进入待补。',
          },
        ],
        bullets: [
          '口径真源仍是 docs/form-controls.md；本台是维护面，禁止绕开映射手写日期/数字框。',
          '与 form-controls 门禁同轴：基线与出包均扫手填日期等一眼病。',
        ],
        links: [
          { href: '/widget-hints', label: '打开控件语义' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '菜单矩阵',
        tag: '配置',
        anchor: '菜单矩阵',
        wide: true,
        lead: '维护「域 × 岗位 × 菜单」入口。常驻入口始终可补；绑定能力的入口仅在该能力开启时由 bake 补齐到 schema.menus。不替代学生包内 X-ORG 岗位菜单勾选。',
        steps: [
          {
            title: '1 · 维护入口',
            page: '侧栏 → 菜单矩阵',
            body: '「导入初始矩阵」追加出厂行（工作台 / AI 助手等）；按域或岗位筛选，登记菜单 ID、展示名与绑定能力。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '收束阶段按矩阵补齐缺菜单项；已有项不覆盖、不删除。能力关闭时不挂能力菜单。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子缺行，或能力说明卡登记的 menu_ids 未进矩阵时，会出现在待补列表。',
          },
        ],
        bullets: [
          '与能力说明分工：说明卡管 README/宣称针；矩阵管「开了能力后各端侧栏有没有入口」。',
          '禁止另起第二套 RBAC；学生包运行时岗位勾选仍走 X-ORG。',
        ],
        links: [
          { href: '/menu-matrix', label: '打开菜单矩阵' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-能力说明', label: '能力说明' },
        ],
      },
      {
        title: '规则参数',
        tag: '配置',
        anchor: '规则参数',
        wide: true,
        lead: '维护超时关单分钟、预约最少提前小时、积分倍率等业务默认数值。出包写入 schema.ruleParams；若配置了落点键且 schema 尚无该键，则补上默认值，不覆盖开题扫词或加厚已写入的值。',
        steps: [
          {
            title: '1 · 维护参数',
            page: '侧栏 → 规则参数',
            body: '「导入初始参数」追加出厂默认；按域筛选，登记规则 ID、名称、数值、单位与可选落点键。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '注入 schema.ruleParams；具名域覆盖跨域壳默认。落点键仅在缺省时写入。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子参数缺行时进入待补列表。',
          },
        ],
        bullets: [
          '宣称「支持超时」等仍由能力/门禁路径负责；本台只提供可维护默认值，避免各域硬编码分叉。',
          '数值用数字控件；单位与落点键从有限选项中选。',
        ],
        links: [
          { href: '/rule-params', label: '打开规则参数' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '表关系叙事',
        tag: '配置',
        anchor: '表关系叙事',
        wide: true,
        lead: '为两张表之间维护一句中文旁注（如「一笔订单包含多条明细」）。出包写入 schema.erEdgeCopy，供论文「数据库设计」引用；不替代 E-R 结构对账，也不管论文图几何。',
        steps: [
          {
            title: '1 · 维护叙事',
            page: '侧栏 → 表关系叙事',
            body: '「导入初始叙事」追加出厂表对；登记表 A、表 B 与一句人话。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '注入 schema.erEdgeCopy（键为 table_a|table_b）与 erEdgeCopyList。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '种子表对缺行时进入待补列表。',
          },
        ],
        bullets: [
          '与词表 COMMENT、E-R 中文标签分工：本台只管「边上一句人话」。',
          '几何排版仍归 parked 论文图债；本台禁止当作排版工具。',
        ],
        links: [
          { href: '/er-edge-copy', label: '打开表关系叙事' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '测试账号',
        tag: '配置',
        anchor: '测试账号',
        wide: true,
        lead: '维护管理端 / 受理端 / 用户端演示账号（用户名、密码、昵称、登录提示）。出包写入 schema.demoAccounts；具名域可覆盖跨域壳默认。与演示剧本的操作角色列对齐。',
        steps: [
          {
            title: '1 · 维护账号',
            page: '侧栏 → 测试账号',
            body: '「导入初始账号」追加出厂三端；可按域登记覆盖账号与登录提示。',
          },
          {
            title: '2 · 出包消费',
            page: '一键生成',
            body: '注入 schema.demoAccounts，供 README / 登录提示引用。',
          },
          {
            title: '3 · 检查缺口',
            page: '待补',
            body: '跨域三端缺任一侧时会出现在待补列表。',
          },
        ],
        bullets: [
          '演示密码是学生包可见明文，勿填真实运营密钥。',
          '登录提示按该端角色口吻写（谁登录说谁的事）。',
        ],
        links: [
          { href: '/demo-accounts', label: '打开测试账号' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-演示剧本', label: '演示剧本' },
        ],
      },
      {
        title: '终稿吸收',
        tag: '工作台',
        anchor: '终稿吸收',
        wide: true,
        lead: '手里只有终稿、没有开题时：抽出需求与实现要点，对照现有能力标缺口，再复制给助手补齐。不建项、不出包；入口在工作台，紧挨「项目」。',
        steps: [
          {
            title: '1 · 上传终稿',
            page: '工作台 → 终稿吸收',
            body: '上传 PDF / Word / TXT。按章节标题抽取；同一文件反复上传/重抽结果应一致。',
          },
          {
            title: '2 · 标覆盖',
            page: '详情',
            body: '对照现有能力标已齐 / 差说法 / 差能力（默认待判断）。已齐也可留作样本；有缺口再补。',
          },
          {
            title: '3 · 复制给助手并试一下',
            page: '详情',
            body: '复制给助手。可反推成开题草稿；需要时下载后到「项目」页自行上传试匹配（只验收，不当正式订单）。',
          },
        ],
        bullets: [
          '三个「论文」词：终稿吸收（本页）≠ 产物「论文材料」（bake 出图）≠ 格式参考旁路。',
          '绪论对比句（现有系统有…/本文不做…）不得当己方功能写入。',
          '可反复重抽、改要点、改覆盖、再复制；一刻不当永久。',
          '禁止入口文案写成「上传论文出包 / 智能匹配论文」。',
        ],
        links: [
          { href: '/thesis-absorb', label: '打开终稿吸收' },
          { href: '/projects', label: '打开项目' },
          { hash: '#help-card-论文材料', label: '产物·论文材料' },
          { hash: '#help-card-上传与分堆', label: '上传开题（出包）' },
        ],
      },
    ],
  },
  {
    title: '运维',
    cards: [
      {
        title: '大模型与填岛拆解',
        tag: '大模型',
        wide: true,
        lead: '大模型仅填充业务配置（Island 文案、E-R 中文、模块图、测试用例等），不写业务源码。开启「业务配置填充」后，工厂会先拆解计划再按 Unit 并发调用。与学生包「AI 助手」运行时不是同一条链路：工厂 Key 禁止打进 ZIP。',
        bullets: [
          '拆解粒度：Island 文案 / 公告种子 / 实体与岗位称呼、E-R 中文、功能模块图、测试用例等各自为独立 Unit；每 Unit 生成后做校验，失败最多重试 1 次。',
          '并发设置：「大模型」页「填岛并发 Unit 数」（1～8，默认 3）；环境变量 GF_FILL_UNIT_CONCURRENCY 为冷启动默认值，页面保存后写入配置库，一键生成 step「业务配置填充」按此并发。',
          '计划预览：项目详情「产物 / 对照」可点「填岛拆解计划」查看各 Unit（只看不执行、不调 LLM）；实际填岛在一键生成 step「业务配置填充」；生成后工作区内 islands/unit_flow/plan.json 为同源产物。',
          '任务日志：生成中可看到 unit · start/done/failed 行；一键生成页会实时显示各 Unit 状态（SSE），断线后自动重连。',
          '过大并发可能触发厂商限流；与 token 预算、修复轮次上限同在「大模型」页配置。',
        ],
      },
      {
        title: '工作台后端 API',
        tag: '运维',
        lead: '毕设港自身（Python / FastAPI）运维接口，与学生端交付包无关；供本机调试、脚本或 Postman。',
        bullets: [
          '涵盖项目、任务、大模型、Unsplash、运行环境、catalog 等。',
          '勿与「产物 → 学生端 API」混淆。',
          '服务探活：GET /api/health。',
        ],
        links: [
          { href: '/docs', label: 'Swagger · /docs' },
          { href: '/redoc', label: 'ReDoc · /redoc' },
        ],
      },
      {
        title: '任务队列与运行环境',
        tag: '运维',
        lead: '「任务队列」看生成排队与失败；「运行环境」看本机 JDK / Maven / Node / MySQL 与预览端口池。',
        bullets: [
          '错误信息会回写到对应项目详情；可清理已失效任务记录。',
          '同类失败反复出现时，到侧栏「失败分析」看周分布与相关位置，不必只在队列里逐条翻。',
          '端口池限制同时预览数量，不限制选题库存。',
          '服务器部署须配置 GF_PUBLIC_HOST，保证预览链接可访问。',
          '「释放异常占用」只清理未托管却占端口的进程；正在预览的项目须到项目详情停止。',
        ],
        links: [
          { hash: '#help-card-失败分析', label: '失败分析' },
        ],
      },
      {
        title: '失败分析',
        tag: '运维',
        anchor: '失败分析',
        wide: true,
        lead: '侧栏「失败分析」汇总指定时间范围内的出包失败：按类型、步骤与领域统计分布，并标出建议优先处理的相关位置。用于排定排修优先级，不是学生包操作说明。',
        bullets: [
          '类型：系统按报错归类的失败类别（含中文名称）。查阅码表请用下方「失败类型对照表」，无需翻阅分类源码。',
          '相关位置：该类型的权威落点（工厂文件/模块）。排修应以此处为准。',
          '识别类型：对单条样本再次推断归属，仅提示、不写回任务。',
          '处理建议：支持多任务并行生成；浮层仅显示当前打开的任务。关闭仅收起浮层，后台仍会生成并缓存，再次打开即可查看。「清除缓存」或离开本页将清除前端缓存；服务端草稿约 2 小时过期，最多保留 32 条，进程重启后清空。',
          '关闭仅收起浮层；未核对的建议不得直接作为修复依据，更不得仅修改当前学生包应付验收。',
        ],
        links: [
          { href: '/fail-analysis', label: '打开失败分析' },
          { hash: '#help-card-失败类型对照表', label: '失败类型对照表' },
          { hash: '#help-card-任务队列与运行环境', label: '任务队列' },
          { hash: '#help-card-最常爆炸处置', label: '最常爆炸' },
        ],
      },
      {
        title: '失败类型对照表',
        tag: '索引',
        anchor: '失败类型对照表',
        wide: true,
        liveTable: 'failCatalog',
        lead: '出包失败类型索引：类型码 → 含义 → 相关位置。与失败分析页、码表同源；顶栏搜索可按码或中文过滤。点击「查分布」将打开失败分析并筛选该类型。',
        bullets: [
          '任务上出现类型码时，请先在本表查阅含义与建议修复位置。',
          '典型报错原文与归类细则以仓库 docs/bake-fail-analysis.md 为准；本表仅作快速索引。',
        ],
        links: [
          { href: '/fail-analysis', label: '打开失败分析' },
          { hash: '#help-card-失败分析', label: '失败分析说明' },
        ],
      },
    ],
  },
  {
    title: '术语',
    cards: [
      {
        title: '术语说明',
        tag: '词典',
        wide: true,
        terms: [
          { name: '分堆确认', def: '上传后按是否同一毕设分簇，确认后再建项；细则见「上传与分堆」。' },
          { name: '材料份数', def: '上传上限按展开后的 PDF / Word / TXT 计（单次最多 8）；细则见「上传与分堆」。' },
          { name: '骨架', def: '匹配页选定的能力路径（如 ARCH-FLOW / ARCH-TRADE）。决定主流程形态，不是 Spring Boot + Vue 或 SSR 等技术主线。' },
          { name: '领域', def: '题目所属业务域（DOM-*）。决定文案、菜单与能力组合，与骨架配合使用。合成壳不是行业域，仅作无贴切领域或需多主路径拼装时的回落。' },
          { name: '持久层', def: '匹配确认中的数据访问实现：JdbcTemplate、MyBatis（绑 PageHelper）或 Spring Data JPA。只换实现与说明书措辞，不换业务能力；与骨架、领域同级，独立于视觉选项。开题推荐与出包不一致时双显。' },
          { name: 'Spring Security', def: '按需鉴权开关（addons.spring_security）。开=过滤器链 + starter-security；关=仅 Session + AdminAuth。匹配确认与 AI 助手同级，不进一键生成视觉区；开题点名则推荐开。' },
          { name: '工程基线', def: '学生 ZIP 的物理工程模板（内部 skeletons/baseline）。与匹配页「骨架」不是同一概念。' },
          { name: '匹配确认', def: '核验并锁定推荐骨架、领域、身份场景、主路径入口（分叉域）、持久层与鉴权、AI 助手等。开题依据弱时须勾「主路径已核对」；确认前不可正式生成；改动后须重新确认。视觉选项在「一键生成」页调整。' },
          { name: '身份场景', def: '校园 / 企业 / 社区等身份档，决定资料字段与壳文案。匹配确认可解锁手改；扫题只推荐。' },
          { name: '主路径入口', def: '同域「谁怎么用」分叉（如本人打卡 vs 对象台账、绑岗 vs 选岗、调宿 vs 选房）。仅部分域有选项；手改后 bake 跟出包选择，不改开题原文。' },
          { name: 'AI 助手', def: '学生包按需开关（addons.ai_assistant）：业务系统旁挂智能问答。开则挂 cap/SQL/悬浮窗/知识库；Spring AI 对接 DeepSeek；只读查本包已开业务 Store。不是新 DOM-*，不进一键生成视觉区。' },
          { name: 'Spring AI', def: '学生包内大模型调用框架（spring-ai-deepseek → DeepSeekChatModel）。Key 用环境变量 DEEPSEEK_API_KEY；与工厂运营「大模型」页填岛 Key 分离。' },
          { name: '只读业务摘录', def: '助手按意图调用 Archive/Order/Ticket/Slot 等现有 Store 拼摘要再回答；能力未开则跳过。不下单、不改状态。' },
          { name: '生成配置', def: '描述业务配置的结构化数据（内部亦称 Spec）。大模型主要填充此类配置，而非手写业务代码。' },
          { name: '填岛拆解', def: '业务配置填充的执行方式：先根据工程与开题生成 DeliveryPlan，再按 Unit 并发调用大模型并合并回 Spec；不改业务源码。' },
          { name: 'Unit', def: '填岛拆解中的最小任务单元（如 E-R 中文、模块图、某类 Island 文案）。各 Unit 独立生成、校验与重试。' },
          { name: '填岛并发', def: '同时执行的 Unit 数量上限，默认 3。在「大模型」页配置，对应环境变量 GF_FILL_UNIT_CONCURRENCY。' },
          { name: '视觉与生成选项', def: '配色、质感、布局、字体、门户首页、本域列表构图、智能填充与密码策略；在「一键生成」页即时保存，写入工程须重新生成。技术栈与 AI/Security 不在此区。' },
          { name: '门户首页', def: '一键生成视觉选项：功能卡片首页 / 资讯侧栏首页 / 商城货架首页（商城、餐饮）。与匹配轴、列表构图无关。' },
          { name: '列表构图', def: '一键生成里按业务组出现的列表页排法（内容 / 商品 / 预约 / 借用 / 报名 / 互动 / 跟进 / 报修 / 审批）。只改页内排列，不改菜单和能力；本域没有的组不显示，跨业务隐喻的档也不会出现在下拉里。' },
          { name: '答辩 PPT', def: 'bake 通过后在「一键生成」下半截开跑的终期答辩材料；可检查/导出 PPTX，不进学生 ZIP。业务脏须按工程更新后再导出。' },
          { name: '基线生成', def: '基于工程基线、骨架、领域与生成配置将工程落地的主路径（内部亦称 bake）。' },
          { name: '能力运行时', def: '工程基线内已实现的通用业务能力；领域通过能力组合复用同一套运行时。' },
          { name: '工程目录', def: '单个项目生成后的本机工程目录，供预览、质量检查与打包下载使用。' },
          { name: 'E-R 图', def: '按交付库表与联系绘制的陈氏线框图；总图不含属性。位于「产物 → 数据库」。' },
          { name: '论文材料', def: '功能模块图、架构图、类图、序列图、活动图、用例图、用例描述表与测例；位于「产物 → 论文材料」。结构跟 ZIP 同源；可导出 PNG/SVG、Mermaid、Draw.io；规则红禁可交导出；「论文图对账」补假宣称扫描。' },
          { name: '终稿吸收', def: '只有终稿、无开题时：抽出要点 → 标覆盖 → 复制给助手补齐；工作台里紧挨「项目」。不建项、不出包；≠ 产物论文材料。' },
          { name: '同材同果', def: '同一终稿内容反复上传/重抽，结构化结果必须一致；属工厂确定性纪律在吸收上的落地。' },
          { name: '系统类图', def: '领域实体 UML：属性/方法取自 bake 包 Java（+/-/#）；外键推关联·聚合·组合，类型引用推依赖，extends/implements 推继承·实现。默认「论文示例」，可切「代码全量」；几何翻车可下同源 Draw.io。' },
          { name: 'Draw.io / Mermaid 导出', def: '与打开的论文图同一 model：Mermaid 作结构参考（可贴 diagrams.net）；Draw.io 可拖框改线，作厂内几何未齐时的手调兜底。' },
          { name: '用例描述表', def: '默认阐述 4 个主路径；含用例名称/执行者/简要说明/基本事件流；步骤对照实包菜单，开题只影响选用。' },
          { name: '软件测试用例', def: '由菜单与角色推导的用例表；字段模板 5～9 可选。可选大模型只润色文案。' },
          { name: '质量检查', def: '交付前的自动验收项集合。关键项未通过时暂不可下载交付包。含语义门禁（可见面与场景）与交付质量摘要。' },
          { name: '开题措辞核对', def: '生成前弹窗：开题功能行与 Spec 清单项名静态比对，不扫工程。' },
          { name: '清单实装验收', def: '生成后质量检查：扫描 workspace，核对清单项是否在 ZIP 中有对应实现（P3a 门禁同源）。' },
          { name: '交付复审', def: '质检交付页运营流程：验收冻结已通过清单、登记偏差、重打包同步 ZIP。不进学生交付包。' },
          { name: '验收（原称验圈）', def: '交付复审中一轮验收：检查门禁单调性、刷新质量摘要，将通过项纳入已通过清单。' },
          { name: '重打包（原称合卷）', def: '验收通过后重新打包 ZIP，使交付包与当前工程目录一致。' },
          { name: '已通过清单（原称安全区）', def: '交付复审中已冻结并通过的门禁与 checklist 项；验收时不得回退。' },
          { name: '未通过清单（原称毒区）', def: '交付复审中尚未收敛、待处理的门禁或 checklist 项。' },
          { name: '审计检查表（原称老板小卡）', def: '交付复审旁运营自检：12 主项（空壳写库完成度/每业务组代表+邻域触点回归/状态机/字段皮/主流程串味/匹配互抢/可见面演示与工厂腔/改开题/reject/材料图/视觉轴/场景身份）+ 理解偏差；勾选仅本机保存，对照未通过清单与质量摘要。' },
          { name: '理解偏差', def: '老师已确认的开题是合同；工厂域/主路径/皮写不对时默认是匹配或 bake 理解问题，禁止甩锅开题套话。' },
          { name: '交付包锁定', def: '因质量检查未过或工程与验收规则不一致，系统禁用压缩包下载的状态。' },
          { name: '预览', def: '在端口池内临时启动前后端做快速验收；不作为生产部署。' },
          { name: '端口池', def: '预留给预览的端口区间，用于限制同时运行的预览实例数量。' },
          { name: '任务队列', def: '异步生成任务列表，用于查看排队、生成中、失败与重试。' },
          { name: '失败分析', def: '侧栏运维页：按失败类型/步骤/领域汇总出包失败，标出权威相关位置，便于优先处理集中出现的类型。' },
          { name: '失败类型', def: '失败分析中的归类码（如 BAKE_PACK_LEAN）及其中文名；由报错与步骤自动归类。速查见帮助「失败类型对照表」。' },
          { name: '相关位置', def: '某失败类型在工厂中的权威落点（文件/模块）。排修以它为准；大模型「处理建议」不得覆盖它。' },
          { name: '处理建议', def: '失败分析中生成的未核对草稿；可关闭、可重新生成，默认同任务复用；确认前请勿直接照做。' },
          { name: '开工台', def: '侧栏首页：汇总待匹配、生成中、复审与近七日失败，便于安排当日处理顺序；不承担建项或单条重试。' },
          { name: '资产台', def: '词表 / 状态话术 / 字典台 / 演示剧本等配置页合称。维护出包注入的中文与演示数据；导入仅追加缺失项。' },
          { name: '词表维护', def: '表/列英文名 → 中文 COMMENT。跨域默认可被具名域覆盖；出包写入 schema.sql 注释。可检查待补、生成建议草稿。' },
          { name: '状态话术', def: '状态码 → 列表名 / 主操作 / 空态文案。跨域默认可被具名域覆盖；出包写入状态展示。' },
          { name: '字典台', def: '业务枚举真源：字典键 × 值码 → 展示名。出包后下拉与筛选项读取本台。' },
          { name: '演示剧本', def: '各域答辩演示步骤清单；含操作角色、步骤标题与所需业务数据（对象、最少条数、可选状态范围）。' },
          { name: '所需数据', def: '演示剧本中该步的数据底线：指定业务对象至少若干条，并可限定状态范围，避免演示时列表为空。' },
          { name: '跨域壳默认', def: '资产台中域取「*」的条目，作为多数域共用底稿；具名 DOM-* 条目优先生效。' },
          { name: '开关建议', def: '开题扫词规则台：提示词命中后在匹配确认展示证据与建议开启项；须人工确认，不自动改开题。' },
          { name: '能力说明', def: '能力岛 README 说明卡：开则注入 FAQ/鉴权文案，关则禁止宣称针残留；可登记菜单入口供对账。' },
          { name: '宣称针', def: '能力说明卡中的关键词列表；对应能力关闭时，学生 README 不得出现这些词，用于防假集成。' },
          { name: '错误码中文', def: '业务 ErrorCode → 默认中文句。bake 写入 error-messages.json；空消息时学生包 ErrorMessages 回落本台。' },
          { name: '控件语义', def: '字段标签/键启发式 → 控件类型。工厂台规则形；bake 投影 fieldWidgetRules.js；与 archiveFieldWidget / form-controls 同轴。' },
          { name: '菜单矩阵', def: '域 × 岗位 × 菜单入口。常驻或绑能力；bake 补齐 schema.menus 缺项，不删已有、不另起 RBAC。' },
          { name: '规则参数', def: '域 × 规则 ID → 数值/单位。bake 写入 schema.ruleParams；落点键仅补缺不覆盖扫词结果。' },
          { name: '表关系叙事', def: '表 A–表 B → 一句中文。bake 写入 schema.erEdgeCopy；服务论文库设旁注，不替代结构对账。' },
          { name: '测试账号', def: '域 × 岗位 → 演示用户名/密码/登录提示。bake 写入 schema.demoAccounts；与演示剧本角色对齐。' },
        ],
      },
    ],
  },
]
</script>
