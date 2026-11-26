<template>
  <div class="help-page surface-page">
    <h1 class="page-title">帮助文档</h1>
    <p class="page-desc">
      第一次上手：先看
      <a href="#help-card-这套系统干什么">这套系统干什么</a>
      和
      <a href="#help-card-先搞清这几个词">先搞清这几个词</a>，
      再跟
      <a href="#help-card-第一次怎么出单">第一次怎么出单</a>。
      台里按钮、侧栏名看不懂时查
      <a href="#help-card-术语说明">术语</a>；
      卡壳看
      <a href="#help-card-四痛点">四痛点</a>。
    </p>

    <div class="help-toolbar">
      <n-input
        v-model:value="query"
        clearable
        placeholder="过滤卡片或术语…（如：领域、皮、第一次出单、状态话术）"
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
        title: '这套系统干什么',
        tag: '入门',
        anchor: '这套系统干什么',
        wide: true,
        lead: '毕设港是本机运营台：根据开题等材料，匹配业务类型，生成可答辩演示的学生工程压缩包。不是通用 IDE，也不替学生改开题。',
        bullets: [
          '主链路只有一条：材料 → 匹配领域（及能力）→ 生成工程 → 质量检查通过后下载。',
          '成功标准：实包、README、论文「系统实现」说的是同一套东西；宣称有的功能，包里要真有表、接口和页面。',
          '常规题应能无人值守出包。出包不对，默认修工厂（匹配 / 生成 / 域皮），不要手改当面学生 ZIP 交差。',
          '已确认的开题是合同。工厂写不出主路径，责任在匹配或生成，不在「材料薄」。',
        ],
        links: [
          { hash: '#help-card-先搞清这几个词', label: '先搞清这几个词' },
          { hash: '#help-card-本机怎么启动', label: '本机怎么启动' },
          { hash: '#help-card-第一次怎么出单', label: '第一次怎么出单' },
        ],
      },
      {
        title: '先搞清这几个词',
        tag: '入门',
        anchor: '先搞清这几个词',
        wide: true,
        lead: '后面页面会反复用到。先分清这几组，再去点匹配确认。',
        table: {
          headers: ['词', '指什么', '别和它搞混'],
          rows: [
            ['领域（DOM-*）', '这题是哪类业务：借阅、报修、商城、预约…决定默认能力、菜单和主路径', '不是校园/企业场景，也不是 Vue/MyBatis'],
            ['皮', '仍挂同一领域，只换文案、种子、分类说法（如商城卖农资 vs 鲜花）', '主流程盖不住时再开新域，不要硬换皮冒充'],
            ['能力 / 能力岛', '可挂到领域上的功能积木：额度、预约、选座、AI 助手等', '不是新开一个「AI 领域」'],
            ['骨架（ARCH-*）', '匹配页选的主流程形态：单据流 / 交易 / 预约…', '不是工程模板目录'],
            ['工程基线', '学生 ZIP 的物理模板（skeletons/baseline）', '与匹配页「骨架」不是一回事'],
            ['身份场景', '校园 / 企业 / 社区：资料字段与壳文案跟谁说话', '不能代替领域匹配'],
            ['异域残留', '本题包里夹带了别的业务脸：主题色、详情 CTA、行业肤 CSS', '门禁瘦身会拦；不是「再匹配一个域」'],
            ['门禁', '出包前自动检查。红灯不可下载交付包', '机器全绿仍可能写错老师确认的主路径，要对着开题看'],
          ],
        },
        bullets: [
          '能挂靠已有领域且主流程盖得住 → 做皮；需要另一套能力组合或状态机 → 才开新领域。',
          '上表只够建立心智。侧栏名、交付页按钮、门禁话术等本台用词，一律在文末「术语」按组查；顶栏过滤框可直接搜词条。',
          '易混题型见「领域易混」。',
        ],
        links: [
          { hash: '#help-card-术语说明', label: '术语（全文）' },
          { hash: '#help-card-领域易混（先问清再确认）', label: '领域易混' },
        ],
      },
      {
        title: '本机怎么启动',
        tag: '上手',
        anchor: '本机怎么启动',
        lead: '本机工具，拉仓后按下面起服务即可。',
        steps: [
          {
            title: '1 · 环境',
            body: '需要 Python 3.11+、Node 18+、JDK 17、Maven、MySQL 8。最短路径见仓库根 README「第一次用 · 拉仓开工」。',
          },
          {
            title: '2 · 启动',
            body: '仓库根运行 scripts/launcher.ps1（或文档里的等价命令），按提示起后端与运营台前端。',
          },
          {
            title: '3 · 进台',
            body: '浏览器打开运营台。服务异常时回本地控制台按 N 做环境自检，再跟「第一次怎么出单」。',
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
        lead: '服务起来后，用测试开题走通：上传 → 匹配 → 生成 → 下载。',
        steps: [
          {
            title: '1 · 建项',
            page: '项目',
            body: '点「生成测试开题」下载 txt，拖到上传区，确认分堆后创建项目。',
          },
          {
            title: '2 · 匹配',
            page: '匹配确认',
            body: '看推荐业务类型是否对得上开题；对得上就确认。需要时勾「我已看过」。',
          },
          {
            title: '3 · 生成与下载',
            page: '一键生成 / 产物',
            body: '启动生成；质量检查通过后下载压缩包。第一次不必先改资产台。',
          },
        ],
        links: [
          { hash: '#help-card-五步主路径', label: '五步主路径' },
          { href: '/projects', label: '打开项目' },
        ],
      },
      {
        title: '侧栏分工',
        tag: '总览',
        anchor: '侧栏分工',
        wide: true,
        lead: '各栏只干一件事，同一信息不要在多页重复找。',
        table: {
          headers: ['栏目', '职责', '不包含'],
          rows: [
            ['开工台', '当日待办：待匹配、生成中、复审、近七日失败', '不上传、不重试单条任务'],
            ['项目', '上传建项；筛待审/待发/已发', '不提供失败类型分布'],
            ['终稿吸收', '只有终稿时抽要点、标缺口；与「项目」并列', '不建项、不出包'],
            ['任务队列', '单条进度、取消、重试', '不按失败码排优先级'],
            ['失败分析', '按类型/步骤/域汇总失败', '不替代项目详情日志'],
            ['帮助文档', '流程与术语', '不展示实时任务'],
            ['词表 / 状态话术 / … / 测试账号', '出包前可维护的中文与演示资产', '不替代匹配确认'],
            ['大模型 / Unsplash / 运行环境', '填岛额度、图床、本机工具链', '不进业务项目列表'],
          ],
        },
        links: [
          { href: '/', label: '打开开工台' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
          { hash: '#help-card-五步主路径', label: '五步主路径' },
        ],
      },
      {
        title: '注意事项',
        tag: '边界',
        lead: '几条硬规矩，后面各卡不再重复展开。',
        bullets: [
          '禁止改开题迁就工厂模板。',
          '匹配确认前请读解析摘要；乱换领域会导致能力与题目不符。',
          '开关开了，包里就要有对应表、菜单和实现；缺了先修生成，不要在界面写「本期不做」。',
          '工厂运营大模型 Key 禁止进入学生 ZIP。',
        ],
      },
    ],
  },
  {
    title: '运营诊断',
    cards: [
      {
        title: '四痛点 → 先看哪',
        tag: '诊断',
        anchor: '四痛点',
        wide: true,
        lead: '不知道从哪下手时，对号入座：',
        bullets: [
          '不知道点哪 → 「侧栏分工」+「五步主路径」。',
          '生成失败 / 下不了包 → 「最常爆炸处置」+「失败类型对照表」。',
          '包能下但答辩像模具 / 主路径不对 → 「开题笼统时仍要写对」：先查工厂是否写对已确认的开题。',
          '机器绿了仍不放心 → 「交付复审」旁的审计检查表对着开题勾。',
        ],
        links: [
          { hash: '#help-card-侧栏分工', label: '侧栏分工' },
          { hash: '#help-card-五步主路径', label: '五步主路径' },
          { hash: '#help-card-最常爆炸处置', label: '最常爆炸' },
          { hash: '#help-card-失败类型对照表', label: '失败类型对照表' },
          { hash: '#help-card-开题笼统时仍要写对', label: '开题笼统仍要写对' },
          { hash: '#help-card-交付复审', label: '交付复审' },
        ],
      },
      {
        title: '五步主路径',
        tag: '流程',
        anchor: '五步主路径',
        wide: true,
        lead: '日常出单的最短路径。细节卡挂在对应步骤下。',
        steps: [
          {
            title: '0 · 开工台',
            page: '开工台',
            body: '看当日待匹配、生成中、复审与失败，决定先处理哪几单。',
          },
          {
            title: '1 · 上传建项',
            page: '项目',
            body: '上传开题/任务书等，确认分堆后创建。不同课题不要强行并成一堆。',
          },
          {
            title: '2 · 匹配确认',
            page: '匹配确认',
            body: '核对领域、身份场景、主路径入口、持久层、Security、AI。有双显时先确认拟选与出包是否一致。开题写不清「谁怎么用」时勾「主路径已核对」。',
          },
          {
            title: '3 · 一键生成',
            page: '一键生成',
            body: '调视觉选项后启动；弹窗做开题措辞核对（不扫工程）。完成后看质量检查。',
          },
          {
            title: '4 · 运行预览',
            page: '运行',
            body: '启停本机预览，按主路径点一遍。',
          },
          {
            title: '5 · 产物与复审',
            page: '产物 / 质检交付',
            body: '过质量检查、需要时交付复审，再下载或标记发出。',
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
        tag: '排障',
        anchor: '最常爆炸处置',
        wide: true,
        lead: '故障时先看哪里、怎么处置。已确认开题是合同，禁止甩锅「材料薄」。',
        table: {
          headers: ['现象', '先看', '处置要点'],
          rows: [
            ['域摇摆 / 易混', '匹配确认双显', '按题名+正文核主路径；理解不清就解锁核清，不改开题'],
            ['门禁红 / 不能下包', '产物 → 质量检查未通过清单', '空壳优先；修生成与域皮后再验'],
            ['异域行业肤 / 详情串台', '瘦身门禁（p3lean）', '包里夹带别家脸；修剪枝与主题，勿手擦 ZIP 糊弄'],
            ['「演示」字样 / 场景穿帮', '质量检查语义门禁', '洗学生可见面；身份跟场景扫描'],
            ['措辞弱匹配多 / 出包像模具', '措辞核对 + 匹配确认', '见「开题笼统时仍要写对」'],
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
        tag: '纪律',
        anchor: '开题笼统时仍要写对',
        wide: true,
        lead: '开题套话多，不等于可以交差。「老师 / 客户已确认的开题」是合同：写不出来，默认是匹配或生成不到位。',
        bullets: [
          '禁止改开题迁就工厂；也禁止用「材料薄」给错包开脱。',
          '出包像模具、主路径不对、皮穿帮：对照开题修领域 / 主路径入口 / 域皮 / 种子；偏差登记写「工厂理解偏差」。',
          '仅当开题明确只要更窄主路径、且未宣称高级能力时，才可记「材料未要求」。',
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
        lead: '五步的展开版。与「五步主路径」同一条链，这里补匹配页和生成页容易漏的点。',
        steps: [
          {
            title: '创建项目',
            page: '项目',
            body: '上传开题 / 任务书 / 功能清单，确认分堆后创建。份数与合并规则见「上传与分堆」。',
          },
          {
            title: '匹配确认',
            page: '匹配确认',
            body: '锁定领域、身份场景、主路径入口（有分叉时）、持久层、Security、AI。视觉选项不在本页，在一键生成。拟选与出包不一致时双显。',
          },
          {
            title: '一键生成',
            page: '一键生成',
            body: '配色、布局、门户首页、本域列表构图等即时保存后启动。启动前弹「开题措辞核对」。完成后看「清单实装验收」。可按当前选项重新生成。',
          },
          {
            title: '答辩 PPT（后置）',
            page: '一键生成下半',
            body: '工程通过后可再跑答辩材料；不进学生 ZIP。业务脏了要先按工程更新再导出。',
          },
          {
            title: '预览与验收',
            page: '运行 / 产物',
            body: '预览点主路径；产物区看库表、论文材料、学生端 API。',
          },
          {
            title: '交付',
            page: '质检交付',
            body: '质量检查通过后下载。需要收窄偏差时走交付复审（验收 → 重打包）。',
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
        lead: '一键生成视觉区里，按业务组出现的列表页排法。只改页内怎么排，不删菜单、不改主路径。当前领域不属于该组时，这项不出现。',
        table: {
          headers: ['选项组', '典型领域', '改什么'],
          rows: [
            ['内容 / 商品 / 预约等', '对应业务组', '列表信息密度与卡片排法'],
            ['报名列表构图', '活动 / 选课 / 失物 / 旅游', '海报墙、课表网、启事板、行程卡等'],
          ],
        },
        bullets: [
          '下拉里看不到的档，就是本领域不能用，不要指望用构图冒充别的业务。',
        ],
      },
      {
        title: '上传与分堆',
        tag: '建项',
        anchor: '上传与分堆',
        wide: true,
        lead: '上传后按是否同一毕设分簇，确认后再建项。',
        bullets: [
          '格式：PDF / Word / TXT；也可 zip（展开后按份计）。',
          '数量：展开后合计最多 8 份。超过则拒绝，不会截取前 8。',
          '同课题：开题 + 任务书 + 功能清单并成一个项目。',
          '不同课题：一次多份开题会拆成多个项目；弹窗可全部拆开或合并后再微调。',
          '同领域不同实现（例如都是图书相关，一套借阅、一套二手）会尽量拆开，避免烤成一个项目。',
        ],
      },
      {
        title: '质量检查与交付',
        tag: '交付',
        anchor: '质量检查与交付',
        wide: true,
        lead: '关键项未通过时不能下载交付包。明细在项目详情「产物 / 对照 → 质量检查」。',
        bullets: [
          '含语义门禁（学生可见面「演示」字样、场景身份穿帮）与交付质量摘要。',
          '清单实装验收与 P3a 同源：清单上写了的，ZIP 里要有实现。',
          '人工审核后可标已发出，或先标已审待发再发出。',
        ],
      },
      {
        title: '交付复审',
        tag: '交付',
        anchor: '交付复审',
        wide: true,
        lead: '「质检交付 → 交付复审」对照开题收窄偏差：验收通过项进已通过清单；通过后方可重打包。不进学生 ZIP。',
        bullets: [
          '偏差登记写「工厂理解偏差」，禁止甩锅「材料薄」。待结案项处理后再重打包。',
          '审计检查表：12 主项 + 理解偏差；机器全绿仍可能写错主路径——对着开题核，修工厂。',
        ],
        links: [
          { hash: '#help-card-四痛点', label: '四痛点索引' },
        ],
      },
      {
        title: '生成前 · 开题措辞核对',
        tag: '包前',
        anchor: '生成前-开题措辞核对',
        wide: true,
        lead: '启动生成前弹出：开题功能行 ↔ 清单项名的静态对照（不调大模型、不扫工程）。',
        bullets: [
          '弱匹配偏多时，先核领域与主路径是否理解对。',
          '与生成后的「清单实装验收」互补：先措辞对齐，再验包内是否真有。',
        ],
      },
      {
        title: 'AI 助手（按需开关）',
        tag: 'AI',
        anchor: 'AI助手',
        wide: true,
        lead: '学生包旁挂的智能客服/导购：匹配确认里与 Spring Security 同级开关；默认关，开题点名则推荐开。不是新领域，不进一键生成视觉区。',
        bullets: [
          '接：主路径仍是业务系统，开题写客服/导购/助手问答。拒：整题是 RAG/向量库/自训 CNN/多 Agent 平台——禁止用聊天壳冒充。',
          '各行业共用一个助手能力，只换 FAQ 与标题；工厂运营 Key 禁止进 ZIP，学生自配 DEEPSEEK_API_KEY。',
          '开则：悬浮对话、知识库、README 说明；关则不得残留「已集成」类宣称。',
          '工厂「大模型」页只服务运营填岛，与学生包运行时 AI 不是一条链路。',
        ],
      },
      {
        title: '质量检查 · 清单实装验收',
        tag: '包后',
        anchor: '清单实装验收',
        wide: true,
        lead: '生成后在「产物 → 质量检查」扫描工程，核对清单项是否真有路由与实现。',
        bullets: [
          '与生成前措辞核对互补；勿把两个弹窗/表格混为一谈。',
          '未通过时先查领域与生成是否完整。',
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
        lead: '「产物 → 数据库」：表结构与 E-R，供论文数据库设计章节用。',
        bullets: [
          '可复制制表符文本贴 Word；E-R 默认可切「论文概念 / 全量」。',
          '论文看概念实体数，不拿物理表张数打红。',
          '可导出 PNG / Draw.io；几何翻车时用 Draw.io 手调。',
        ],
      },
      {
        title: '论文材料',
        tag: '产物',
        lead: '「产物 → 论文材料」：模块图、架构图、类图、序列/活动图、用例图、用例描述表、测例。结构从交付包推导，与 ZIP 同源。',
        bullets: [
          '导出：PNG/SVG、Mermaid、Draw.io（可拖框）。规则红则禁可交导出。',
          '「论文图对账」：须改＝规则铁证；待核＝需打开材料卡核对。',
          '≠ 工作台「终稿吸收」（那是无开题时抽终稿进厂库）。',
        ],
      },
      {
        title: '学生端 API',
        tag: '产物',
        lead: '按工作区 Controller 列出实有 Mapping（源码清单，不是 Swagger）。',
        bullets: [
          '可按端筛选、搜索路径；命中主流程契约的会标注。',
          '「运行」启停预览；「全量冒烟」只打已 healthy 的学生 API，不会自动启动。',
        ],
      },
    ],
  },
  {
    title: '领域匹配',
    cards: [
      {
        title: '域还是皮',
        tag: '入门',
        anchor: '域还是皮',
        wide: true,
        lead: '新题先问两句，再决定改登记表还是开新域。',
        bullets: [
          '现有某个 DOM-* 的主流程（借还 / 报修 / 下单 / 约时段 / 跟进…）盖得住 → 做皮：换文案、种子、kind/niche。',
          '需要另一套默认能力、表位或状态机 → 薄开新域；禁止为单题另起平行逻辑。',
          '商城换分类、预约换眉标、考试换题库说法 → 仍是皮。',
          '施工清单见仓库 docs/domain-skin-onboarding.md；进度册见 domain-skin-gap-analysis.md。',
        ],
        links: [
          { hash: '#help-card-换皮全覆盖清单索引', label: '换皮清单索引' },
          { hash: '#help-card-先搞清这几个词', label: '先搞清这几个词' },
        ],
      },
      {
        title: '领域易混（先问清再确认）',
        tag: '防坑',
        anchor: '领域易混（先问清再确认）',
        wide: true,
        lead: '匹配前先分清客户原话落在哪条主路径。成对易混须双侧成立。完整清单见 docs/domain-skin-gap-analysis.md §2。',
        bullets: [
          '实习：交周报（INTERN）≠ 投简历找岗（RECRUIT）。',
          '活动报名占名额 ≠ 公选课选课；请假销假 ≠ 晨午检事件上报。',
          '宠物门诊挂号（医院）≠ 流浪动物领养（失物认领壳）。',
          '快递驿站取件 ≠ 跑腿代买商城；宾馆客房+消费（HOTEL）≠ 会议室+小卖部交叉壳。',
          '真交叉须开题写清两套玩法（借阅+二手 / 图书+座位 / 下单+预约）；三合一拒绝。',
          '实验室准入 ≠ 耗材申领 ≠ 器材借用 ≠ 仪器借+机时。',
          '家政上门预约 ≠ 物业报修；巡检打卡 ≠ IT 报修；食安台账 ≠ 食堂点餐。',
          '演出领票占名额 ≠ 影院选座；文库下载 ≠ 图书借阅 ≠ 博客资讯。',
          '考试题库 ≠ 问卷 ≠ 评教；投票计票 ≠ 活动报名（可复合挂 vote）。',
          '会签多级审批须开题写到才挂；本地签章 ≠ CA 电子签平台。',
          '售前可先问清：见清单 §13.1「客户原话 → 先问清的一句」。',
        ],
      },
      {
        title: '硬边界（不接）',
        tag: '边界',
        lead: '下列继续拒绝或标超出演示范围：',
        bullets: [
          '人脸 / 指纹 / 闸机；GPS 轨迹考勤。',
          '真微信/支付宝；小程序与原生 App。',
          '物联网开锁；疾控/医保/银行直连。',
          '智慧校园 N 合一、OA 三联一题、硕博真实全流程。',
          'AI 主产品（RAG 工程、自训 CNN、多 Agent 派单）——业务旁挂问答仍可走开助手开关。',
        ],
      },
      {
        title: '换皮全覆盖清单索引',
        tag: '索引',
        anchor: '换皮全覆盖清单索引',
        wide: true,
        lead: '对照仓库 docs/domain-skin-gap-analysis.md；样例在 data/samples/，可直接上传匹配。',
        bullets: [
          '易混对 §2：本页「领域易混」+ test_confusion_pairs。',
          '深皮 / 预设 / 能力 / 交叉样例：见清单 §3～§6 与 data/samples 对应目录。',
          '能力矩阵 docs/capabilities.md；领域组 docs/domains.md。',
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
        lead: '侧栏各台维护出包时注入学生包的中文与演示数据。日常出单不必先改；某域状态名不对、下拉缺项、答辩列表空空时再来。',
        table: {
          headers: ['栏目', '解决什么', '出包落点'],
          rows: [
            ['词表维护', '表/列中文名', 'schema.sql 注释'],
            ['状态话术', '状态列表名、主操作、空态', '状态展示与按钮'],
            ['字典台', '业务枚举与下拉', '筛选与表单选项'],
            ['演示剧本', '答辩步骤与所需数据', '演示步骤清单'],
            ['开关建议', '开题扫词 → 匹配建议', '鉴权 / AI 等推荐'],
            ['能力说明', '能力岛 README 与宣称针', '开则注入 / 关则禁宣称'],
            ['错误码中文', '业务错误默认句', 'error-messages.json'],
            ['控件语义', '字段标签 → 控件类型', 'fieldWidgetRules.js'],
            ['菜单矩阵', '岗位 × 菜单入口', 'schema.menus 补缺'],
            ['规则参数', '超时/提前量/倍率等', 'schema.ruleParams'],
            ['表关系叙事', '表边一句人话', 'schema.erEdgeCopy'],
            ['测试账号', '三端演示账号', 'schema.demoAccounts'],
            ['论文图题', '图种×域标题模板', 'schema.diagramTitleTemplates'],
            ['用例流程', '用例描述表事件流模板', 'factory_usecase_flow'],
          ],
        },
        bullets: [
          '共用操作：导入初始…只追加缺失项；选域 → 检查待补 → 登记（标识字段锁定，只改展示内容）。',
          '改动对之后新生成的包生效，不回写已下载 ZIP。',
          '「跨域壳默认」是多数域共用底稿；具名域条目优先生效。',
          '只有终稿、没有开题 → 工作台「终稿吸收」，不在本栏。',
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
          { hash: '#help-card-终稿吸收', label: '终稿吸收' },
          { href: '/zh-lexicon', label: '打开词表维护' },
        ],
      },
      {
        title: '词表维护',
        tag: '配置',
        anchor: '词表维护',
        lead: '表/列英文名 → 中文 COMMENT。列名保持英文。',
        bullets: [
          '不管按钮话术（状态话术）或下拉枚举（字典台）。',
          '待补可生成建议草稿，再人工确认。',
        ],
        links: [
          { href: '/zh-lexicon', label: '打开词表维护' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '状态话术',
        tag: '配置',
        anchor: '状态话术',
        lead: '状态码 → 列表名、主操作按钮、该态空列表提示。由域 + 状态机 + 状态码唯一确定。',
        bullets: [
          '不配置「谁能点下一步」——流转权限在能力与角色。',
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
        lead: '业务枚举真源：字典键 × 值码 → 展示名。学生包下拉与筛选项读本台。',
        bullets: [
          '禁止在学生页面手写平行选项表；可筛选搜索，不可创建库外值。',
          '「皮」字段仅软皮差异时使用，多数留空。',
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
        lead: '各域答辩步骤：角色、标题、该步所需业务数据条数（可选状态范围），避免演示时空列表。',
        bullets: [
          '保证数据底线，不替代浏览器逐页点验。',
        ],
        links: [
          { href: '/demo-scripts', label: '打开演示剧本' },
          { hash: '#help-card-资产台总览', label: '资产台总览' },
        ],
      },
      {
        title: '开关建议',
        tag: '配置',
        anchor: '开关建议',
        lead: '开题出现某词 → 匹配页建议开某开关。须人工确认，不自动改开题。',
        bullets: [
          '与能力说明分工：本台管「开题是否点名」；说明卡管「开了以后说明书怎么写」。',
        ],
        links: [
          { href: '/addon-suggest', label: '打开开关建议' },
          { hash: '#help-card-AI助手', label: 'AI 助手说明' },
        ],
      },
      {
        title: '能力说明',
        tag: '配置',
        anchor: '能力说明',
        lead: '能力岛 README 段、菜单入口与「宣称针」。关能力时 README 不得残留宣称针。',
        bullets: [
          '说明书只写学生自配环境变量；工厂 Key 禁止进 ZIP。',
        ],
        links: [
          { href: '/cap-cards', label: '打开能力说明' },
          { hash: '#help-card-开关建议', label: '开关建议' },
        ],
      },
      {
        title: '错误码中文',
        tag: '配置',
        anchor: '错误码中文',
        lead: '业务 ErrorCode → 默认中文。出包写入 error-messages.json；空消息时回落本台。',
        bullets: [
          '只管学生可见业务错句，不管工厂腔词表。',
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
        lead: '字段标签/键启发式 → 控件类型；出包投影为 fieldWidgetRules.js。',
        bullets: [
          '日期/数字/枚举禁止用手填输入框硬顶；口径见 form-controls。',
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
        lead: '域 × 岗位 × 菜单。常驻可补；绑能力的入口仅在能力开启时补进 schema.menus。',
        bullets: [
          '不另起 RBAC；学生包岗位勾选仍走原有机制。',
        ],
        links: [
          { href: '/menu-matrix', label: '打开菜单矩阵' },
          { hash: '#help-card-能力说明', label: '能力说明' },
        ],
      },
      {
        title: '规则参数',
        tag: '配置',
        anchor: '规则参数',
        lead: '超时分钟、预约提前小时、积分倍率等默认值 → schema.ruleParams；落点键仅补缺，不覆盖开题扫词已写入的值。',
        bullets: [
          '「是否支持超时」仍由能力与门禁负责；本台只给可维护默认值。',
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
        lead: '两表之间一句中文旁注（如「一笔订单包含多条明细」）→ schema.erEdgeCopy，供论文库设引用。',
        bullets: [
          '不替代 E-R 结构对账，也不管图几何。',
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
        lead: '管理端 / 受理端 / 用户端演示账号与登录提示 → schema.demoAccounts。',
        bullets: [
          '演示密码是学生包可见明文，勿填真实密钥；提示按该端角色口吻写。',
        ],
        links: [
          { href: '/demo-accounts', label: '打开测试账号' },
          { hash: '#help-card-演示剧本', label: '演示剧本' },
        ],
      },
      {
        title: '终稿吸收',
        tag: '工作台',
        anchor: '终稿吸收',
        wide: true,
        lead: '只有终稿、没有开题时：抽需求与实现要点，对照能力标缺口，再复制给助手。不建项、不出包。入口在工作台，紧挨「项目」。',
        steps: [
          {
            title: '1 · 上传终稿',
            page: '工作台 → 终稿吸收',
            body: '上传 PDF / Word / TXT。同一文件反复上传/重抽，结构化结果应一致（同材同果）。',
          },
          {
            title: '2 · 标覆盖',
            page: '详情',
            body: '标已齐 / 差说法 / 差能力。已齐也可留作样本。',
          },
          {
            title: '3 · 复制给助手',
            page: '详情',
            body: '复制要点；可反推开题草稿，再到「项目」上传试匹配（只验收，不当正式单）。',
          },
        ],
        links: [
          { href: '/thesis-absorb', label: '打开终稿吸收' },
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
        tag: '运维',
        lead: '运营台「大模型」页配置填岛用量与并发。大模型主要填业务配置（Spec），不手写业务源码。',
        bullets: [
          '先拆 DeliveryPlan，再按 Unit 并发调用并合并；失败项保留，不得假成功。',
          '与学生包 AI 助手不是同一条 Key / 链路。',
        ],
      },
      {
        title: '工作台后端 API',
        tag: '运维',
        lead: '运营台自身接口清单，供本机联调。不是学生包 API。',
        bullets: [
          '学生端接口见产物「学生端 API」。',
        ],
      },
      {
        title: '任务队列与运行环境',
        tag: '运维',
        anchor: '任务队列与运行环境',
        lead: '任务队列看单条生成进度与重试；运行环境看本机工具链、端口与预览池。',
        bullets: [
          '开工台汇总待办；单条取消/重试进任务队列。',
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
        lead: '按失败类型、步骤、领域汇总出包失败，标出权威相关位置，便于排修优先级。',
        bullets: [
          '「相关位置」以工厂落点为准；大模型「处理建议」是未核对草稿，确认前勿直接照做。',
        ],
        links: [
          { href: '/fail-analysis', label: '打开失败分析' },
          { hash: '#help-card-失败类型对照表', label: '失败类型对照表' },
          { hash: '#help-card-最常爆炸处置', label: '最常爆炸' },
        ],
      },
      {
        title: '失败类型对照表',
        tag: '运维',
        anchor: '失败类型对照表',
        wide: true,
        lead: '类型码与中文名、相关位置。可跳到失败分析查分布。',
        liveTable: 'failCatalog',
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
        anchor: '术语说明',
        wide: true,
        lead: '本台侧栏、项目页、交付页会出现的词都收在下面几组。上面过滤框可搜词条名。旧绰号对照见仓库 docs/glossary.md（如毒区→未通过清单）。',
        bullets: [
          '匹配与身份：领域、皮、骨架、场景…',
          '生成与选项：一键生成、业务配置填充、视觉选项…',
          '检查与交付：门禁、验收、重打包、审计检查表…',
          '侧栏与资产台：开工台、词表、状态话术、宣称针…',
        ],
        links: [
          { hash: '#help-card-术语-匹配与身份', label: '匹配与身份' },
          { hash: '#help-card-术语-生成与选项', label: '生成与选项' },
          { hash: '#help-card-术语-检查与交付', label: '检查与交付' },
          { hash: '#help-card-术语-侧栏与资产台', label: '侧栏与资产台' },
          { hash: '#help-card-先搞清这几个词', label: '先搞清这几个词' },
        ],
      },
      {
        title: '匹配与身份',
        tag: '词典',
        anchor: '术语-匹配与身份',
        wide: true,
        terms: [
          { name: '领域', def: '题目所属业务类型，界面与内部常写作 DOM-*（如 DOM-LIBRARY）。决定默认能力、菜单、表和主路径。' },
          { name: '皮', def: '仍挂同一领域，只换文案、演示种子、分类或眉标说法（农资商城 vs 鲜花商城）。主流程盖不住时不要硬换皮。' },
          { name: '深皮', def: '同域上更深的文案/字段/种子覆盖（如跟进类行业说法），仍不新开 DOM-*。' },
          { name: '邻域', def: '容易抢匹配的相近题（驿站 vs 跑腿）。确认前先看「领域易混」。' },
          { name: '异域残留', def: '本题包里夹带别家业务脸：主题色、详情 CTA、行业肤 CSS。瘦身门禁会报。' },
          { name: '能力 / 能力岛', def: '挂到领域上的功能积木（额度、预约、选座、AI 助手等）。开了就要有表、菜单和实现。' },
          { name: '骨架', def: '匹配页选的主流程形态（单据流 / 交易 / 预约等，内部 ARCH-*）。不是技术栈，也不是工程目录。' },
          { name: '工程基线', def: '学生 ZIP 的物理模板（skeletons/baseline）。与匹配页「骨架」不是同一个东西。' },
          { name: '薄壳', def: '同组共用运行时，差别主要在文案、种子、菜单；不另起厚代码包。薄壳不等于功能稀薄。' },
          { name: '身份场景', def: '校园 / 企业 / 社区。管资料字段和壳文案跟谁说话，不能代替领域匹配。' },
          { name: '主路径入口', def: '同域「谁怎么用」分叉（绑岗 vs 选岗、调宿 vs 选房等）。手改后生成跟选择，不改开题原文。' },
          { name: '通用壳 / DOM-GENERIC', def: '对不上具名领域，或单域盖不住多主路径时的回落壳；真交叉也常落这里并保留行为并集。' },
          { name: '真交叉', def: '开题写清两套玩法（如借阅+二手）。白名单内可出包；三合一拒绝。' },
          { name: '双显 / 拟选≠出包', def: '开题推荐与当前出包选择不一致时两边都显示（持久层、Security、AI、身份入口等），须人确认，禁止静默改。' },
          { name: '种子', def: '生成时写入演示库的示例数据与公告等，让预览能点通主路径。' },
          { name: '匹配确认', def: '项目页一步：锁定领域、场景、主路径、持久层、鉴权、AI。确认前不能正式生成。' },
          { name: '分堆确认', def: '上传后按是否同一毕设分簇，确认后再建项。' },
        ],
      },
      {
        title: '生成与选项',
        tag: '词典',
        anchor: '术语-生成与选项',
        wide: true,
        terms: [
          { name: '一键生成', def: '确认匹配后，按当前选项把工程落地的页面。视觉选项在这里调，不在匹配页。' },
          { name: '基线生成 / bake', def: '按领域与配置把工程基线写成学生包的过程；帮助与日志里有时仍写 bake。' },
          { name: '生成配置 / Spec', def: '描述业务配置的结构化数据。大模型主要填这类配置，而不是手写业务代码。' },
          { name: '业务配置填充（填岛）', def: '按单元调用大模型填充 Spec 并合并回工程。按钮主文案用「业务配置填充」；帮助里可夹注填岛。' },
          { name: 'Unit', def: '业务配置填充的最小任务单元（如某类文案、某张图说明）。各 Unit 独立生成、校验与重试。' },
          { name: '填岛并发', def: '同时执行的 Unit 数量上限，默认 3；在「大模型」页配置。' },
          { name: '持久层', def: '数据访问实现：JdbcTemplate / MyBatis / JPA。只换实现与说明书，不换业务能力。' },
          { name: 'Spring Security', def: '按需鉴权开关。与 AI 助手同级，放在匹配确认，不进一键生成视觉区。' },
          { name: 'AI 助手', def: '学生包旁挂问答开关。不是新领域；工厂运营 Key 禁止进入学生 ZIP。' },
          { name: '视觉与生成选项', def: '配色、质感、布局、字体、门户首页、本域列表构图、密码策略等；保存后须重新生成才进包。' },
          { name: '门户首页', def: '一键生成里的首页版式（功能卡片 / 资讯侧栏 / 商城货架等）。与匹配轴无关。' },
          { name: '列表构图', def: '按业务组出现的列表页排法。只改页内排列，不改菜单和能力；本域没有的组不显示。' },
          { name: '开题措辞核对', def: '启动生成前弹窗：开题功能行与清单项名静态比对，不调大模型、不扫工程。' },
          { name: '大模型（运营页）', def: '侧栏「大模型」：运营填岛用量与连接。与学生包运行时 AI 助手不是同一条 Key。' },
        ],
      },
      {
        title: '检查与交付',
        tag: '词典',
        anchor: '术语-检查与交付',
        wide: true,
        terms: [
          { name: '质量检查', def: '交付前自动验收集合。关键项未通过时不能下载交付包。' },
          { name: '门禁', def: '质量检查里的硬规则（布局、控件、瘦身、清单实装等）。红灯不可下包。' },
          { name: '清单实装验收', def: '生成后扫描工程：清单上写了的项，ZIP 里要有对应实现。' },
          { name: '交付复审', def: '质检交付页流程：验收、登记偏差、重打包。结果不进学生 ZIP。' },
          { name: '验收（原称验圈）', def: '交付复审中一轮核对：刷新摘要，把通过项纳入已通过清单。' },
          { name: '重打包（原称合卷）', def: '验收通过后重新打 ZIP，使交付包与当前工程目录一致。' },
          { name: '已通过清单（原称安全区）', def: '交付复审里已冻结且通过的门禁与检查项；验收时不得回退。' },
          { name: '未通过清单（原称毒区）', def: '尚未收敛、待处理的门禁或检查项。' },
          { name: '审计检查表（原称老板小卡）', def: '交付复审旁运营自检：12 主项 + 理解偏差；勾选仅本机保存。' },
          { name: '理解偏差', def: '已确认开题写不对时，默认是匹配或生成理解问题，禁止甩锅开题套话。' },
          { name: '交付包锁定', def: '因质量检查未过或工程与验收规则不一致，系统禁用压缩包下载。' },
          { name: '预览', def: '在端口池内临时启动前后端做快速验收；不是生产部署。' },
          { name: '端口池', def: '预留给预览的端口区间，限制同时运行的预览数量。' },
          { name: '论文材料', def: '产物区的模块图、架构图、类图、序列/活动图、用例与测例等，与 ZIP 同源。≠ 终稿吸收。' },
          { name: '论文图对账', def: '检查论文图是否假宣称或与实包不符；须改＝规则铁证，待核＝需打开材料卡核对。' },
          { name: 'E-R 图', def: '按交付库表绘制的关系图；在「产物 → 数据库」。' },
          { name: '终稿吸收', def: '没有开题、只有终稿时：抽要点、标缺口、复制给助手。不建项、不出包。' },
          { name: '同材同果', def: '同一终稿反复上传/重抽，结构化结果必须一致。' },
          { name: '答辩 PPT', def: '工程通过后可另跑的答辩材料导出；不进学生 ZIP。' },
        ],
      },
      {
        title: '侧栏与资产台',
        tag: '词典',
        anchor: '术语-侧栏与资产台',
        wide: true,
        terms: [
          { name: '开工台', def: '侧栏首页：待匹配、生成中、复审与近七日失败总览。不上传、不重试单条。' },
          { name: '项目', def: '上传建项、匹配、生成、预览、产物与履约状态（待审/待发/已发）。' },
          { name: '任务队列', def: '单条生成任务的进度、取消与重试。' },
          { name: '失败分析', def: '按失败类型、步骤、领域汇总出包失败，标出权威相关位置。' },
          { name: '失败类型', def: '失败归类码及其含义（如瘦身失败）。速查见「失败类型对照表」。' },
          { name: '相关位置', def: '某失败类型在工厂代码中的权威落点。排修以它为准。' },
          { name: '处理建议', def: '失败分析里生成的未核对草稿；确认前不要直接照做。' },
          { name: '运行环境', def: '本机工具链、路径、端口等；卡住时先做环境自检。' },
          { name: '资产台', def: '词表、状态话术、字典台等配置页合称。维护出包注入的中文与演示数据。' },
          { name: '词表维护', def: '表/列英文名 → 中文 COMMENT。出包写入 schema.sql 注释。' },
          { name: '状态话术', def: '状态码 → 列表名、主操作按钮、该态空列表提示。' },
          { name: '字典台', def: '业务枚举：字典键 × 值码 → 展示名。学生包下拉与筛选读本台。' },
          { name: '演示剧本', def: '各域答辩步骤与该步所需业务数据条数，避免演示时空列表。' },
          { name: '开关建议', def: '开题扫词规则：命中后在匹配页给证据与建议；须人确认。' },
          { name: '能力说明', def: '能力岛 README 说明段与菜单入口；关能力时配合宣称针防假集成。' },
          { name: '宣称针', def: '能力关闭时学生 README 不得出现的词。' },
          { name: '错误码中文', def: '业务错误码默认中文句；空消息时学生包回落本台。' },
          { name: '控件语义', def: '字段标签/键 → 控件类型（日期选、数字框等）；禁止手填日期数字枚举。' },
          { name: '菜单矩阵', def: '域 × 岗位 × 菜单入口；能力开启时补齐缺菜单。' },
          { name: '规则参数', def: '超时、预约提前量、积分倍率等默认数值。' },
          { name: '表关系叙事', def: '两表之间一句中文旁注，供论文库设引用。' },
          { name: '测试账号', def: '管理端/受理端/用户端演示账号与登录提示。' },
          { name: '论文图题', def: '各图种按域的标题模板。' },
          { name: '跨域壳默认', def: '资产台里域取「*」的共用底稿；具名领域条目优先生效。' },
          { name: '检查待补', def: '按选定域扫描资产缺口；有缺口再登记，标识字段锁定只改展示内容。' },
          { name: '导入初始…', def: '各资产台「导入」只追加出厂缺失项，不覆盖已有（含手工改过的）记录。' },
        ],
      },
    ],
  },
]
</script>
