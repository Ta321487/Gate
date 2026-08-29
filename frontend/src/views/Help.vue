<template>
  <div class="help-page">
    <h1 class="page-title">帮助文档</h1>
    <p class="page-desc">本说明面向运营人员，介绍毕设港工作台的标准使用流程、交付条件与常用术语。</p>

    <div class="help-toolbar">
      <n-input
        v-model:value="query"
        clearable
        placeholder="过滤卡片或术语…（如：验圈、填岛、履约）"
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
              </li>
            </ol>
            <ul v-if="card.bullets?.length">
              <li v-for="(b, i) in card.bullets" :key="i">{{ b }}</li>
            </ul>
            <p v-if="card.links?.length" class="help-links">
              <a
                v-for="l in card.links"
                :key="l.href"
                :href="l.href"
                target="_blank"
                rel="noopener"
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
import { computed, ref } from 'vue'
import { NEmpty, NInput } from 'naive-ui'

const query = ref('')
const qNorm = computed(() => String(query.value || '').trim().toLowerCase())

function sectionId(title) {
  return `help-sec-${String(title || '').replace(/\s+/g, '-')}`
}

function cardBlob(card, { withTerms = true } = {}) {
  const parts = [card.title, card.tag, card.lead]
  for (const s of card.steps || []) parts.push(s.title, s.body)
  for (const b of card.bullets || []) parts.push(b)
  for (const l of card.links || []) parts.push(l.label)
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
        title: '产品定位',
        tag: '总览',
        lead: '毕设港工作台用于依据开题、任务书等材料完成选题匹配、工程生成、质量检查与本地预览；机器质检通过后可下载压缩包。人工审核后可直接标记已发出，或先标已审待发再发出。',
        bullets: [
          '以固定工程基线与能力运行时为主体；大语言模型仅填充业务配置，不承担业务代码编写。',
          '机器质检通过只代表可下载，不代表文案与业务逻辑已过人工审核。',
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
    title: '流程与交付',
    cards: [
      {
        title: '标准作业流程',
        tag: '流程',
        wide: true,
        steps: [
          {
            title: '创建项目',
            body: '在「项目」页上传开题 / 任务书 / 功能清单等材料，确认分堆后再创建。格式、数量上限、同课题合并与多课题拆开等说明见下方「上传与分堆」。',
          },
          {
            title: '匹配确认',
            body: '在「匹配确认」页核验推荐骨架、领域、身份场景、主路径入口（如有分叉：晨午检自报/绑岗/调宿等）与持久层。开题未写清「谁怎么用」时须勾选「主路径已核对」或解锁手改后再确认。配色、布局等视觉选项在「一键生成」页调整。',
          },
          {
            title: '一键生成',
            body: '匹配确认后，在「一键生成」页调整视觉与生成选项（即时保存），再启动生成。启动前会弹出「开题措辞核对」，对照开题功能行与工厂清单项名（不扫工程）。生成完成后在「质量检查」看「清单实装验收」，确认 ZIP 内真有对应实现。生成完成后可同页改选项并「按当前选项重新生成」。进度可在「任务队列」与项目详情中查看；业务配置填充会拆成多个 Unit 并发执行，详情见「大模型与填岛拆解」。',
          },
          {
            title: '预览与验收',
            body: '于「运行」页启动前后端预览做快速验收；于「产物 / 对照」核对数据库（表结构 / E-R）、论文材料（模块图 / 测试用例）、学生端 API 与质量检查。工程有改动时，在「交付复审」验圈并合卷，确保 ZIP 与 workspace 一致。',
          },
          {
            title: '交付',
            body: '机器质检通过后可下载 ZIP。列表「履约」列或详情页头可操作：审过可一步「标记已发出」；暂存用「已审待发」，发出时用「下载并发出」。重新生成会清掉人工标记与复审轮次。',
          },
        ],
      },
      {
        title: '上传与分堆',
        tag: '上传',
        wide: true,
        lead: '上传后先分堆、再确认创建。上限与「直接选文件」相同：只计展开后的 PDF / Word / TXT 份数。',
        bullets: [
          '格式：PDF / Word（.doc / .docx）/ TXT；可多选、拖文件夹，或选择 / 拖入 zip。文件夹与 zip 内非材料文件会跳过。',
          '数量：展开后合计最多 8 份。例：8 个 zip 各含 1 份开题 → 8 份，可通过；1 个 zip 内 9 份 → 拒绝；合计超过 8 → 拒绝，不会截取前 8 份。',
          '同课题：开题 + 任务书 + 功能清单等会并成一个项目。',
          '不同课题：一次拖入多份不同开题，会拆成多个项目；确认弹窗可「全部拆开」或「合并为一个」后微调。',
          '同领域不同实现（如都是图书皮，一套借阅、一套二手交易）会尽量拆开，避免烤成一个项目。',
          '无关材料（简历、空文件、纯闲文等）会剔除，不参与匹配。',
          '确认前不会建项。弹窗打开时再上传下一批，后到的分堆进入队列，不顶掉当前内容；可点「查看分堆」切换，或确认 / 取消后自动翻下一份。',
          '需要超过 8 份材料时，请分多次上传（每次 ≤8）；项目总数不受 8 限制。',
        ],
      },
      {
        title: '质量检查与交付',
        tag: '交付',
        wide: true,
        lead: '机器质检通过只代表可下载。关键项未通过时不可下载。人工审核后可在列表或详情直接标「已发出」；需要暂存待发再用「已审待发」。工程变更后须先验圈再合卷。',
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
        wide: true,
        lead: '「产物 / 对照 → 交付复审」用于对照开题收窄偏差：已通过项纳入安全区；验圈通过后方可合卷更新交付包。不进学生 ZIP。',
        bullets: [
          '首包直发：首次打包未进入复审时，质检通过即可下载；工程改动后 ZIP 可能过期，须验圈并合卷。',
          '进入复审：主动开启后，每轮「验圈」冻结已通过的门禁与 checklist 项到安全区；未通过项留在毒区待收敛。',
          '验圈：检查单调性（安全区不得回退）并刷新质量摘要；有回退或 open 偏差登记时不可合卷。',
          '合卷：验圈通过后重新打包 ZIP，使交付包与当前 workspace 一致。',
          '偏差登记：记录与开题或材料不一致之处（仅运营可见）；待结案项须处理或结案后再合卷。',
          '导出交接包：供线下交接或留档，不含于学生交付物。',
          '按钮悬停有一句操作说明；合卷不可用时悬停可见原因。',
        ],
      },
      {
        title: '生成前 · 开题措辞核对',
        tag: '生成前',
        wide: true,
        lead: '启动生成前弹出：开题功能行 ↔ Spec 清单项名的静态措辞对照（不调大模型、不扫 workspace）。',
        bullets: [
          '与「质量检查 → 清单实装验收」不是同一功能；措辞绿了不代表包内已实装。',
          '顶部覆盖比例（如 8/8 已覆盖）一眼判断能否放心生成；不阻断生成。',
          '已对照 / 措辞弱匹配 / 措辞待核 / 工厂实现模块：见弹窗分区说明。',
        ],
      },
      {
        title: '质量检查 · 清单实装验收',
        tag: '包后',
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
          '库表数量 6～15 张（含平台表）。',
          'E-R 总图含实体与联系；分图按实体展开属性。可复制 PNG / 下载矢量，可拖拽微调；首次打开可能略慢。',
        ],
      },
      {
        title: '论文材料',
        tag: '产物',
        lead: '「产物 / 对照 → 论文材料」：功能模块图与软件测试用例。均按交付菜单推导，不发明功能。',
        bullets: [
          '模块图可按业务 / 按端切换；黑白线框；可复制 PNG 或矢量。',
          '测试用例 5～9 字段可选（默认 6）；复制表格可贴 Word（黑白线框）。',
          '大模型只润色文案，不增删用例、不改编号与模块归属；与 Island 文案、E-R、模块图同属填岛拆解流水线。',
        ],
      },
      {
        title: '学生端 API',
        tag: '产物',
        lead: '「产物 / 对照 → 学生端 API」扫描学生工程接口，便于对照主流程验收。',
        bullets: [
          '可按门户 / 管理端等面筛选，可搜索路径或处理函数。',
          '命中主流程契约的接口会标注契约键。',
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
          '资助申请 ≠ 报销/用章；相亲牵线 ≠ 导师双选；宿舍报修 ≠ 床位分配；成绩更正 ≠ 网上评教。',
          '旅行社线路跟团报名（旅游 TOUR）≠ 宾馆客房（酒店 HOTEL）≠ 社团活动报名（活动 ACTIVITY）≠ 拼车结伴（拼车 CARPOOL）。',
          '景区/演出领票占名额（活动 ACTIVITY）≠ 影院选座购票座位图（影院 CINEMA）。',
          '校园跑腿代买订单（商城 SHOP）≠ 快递驿站取件核销（快递 PARCEL）。',
          '充电桩/共享车位时段预约（车位 PARKING）≠ 临时车辆通行证备案发码（通行证 CARPASS）。',
          '点播课/课程视频库播放（媒资 MEDIA）≠ 公选课选课占名额（选课 COURSE）；表白墙发帖（论坛 FORUM）≠ 院刊资讯浏览（博客 BLOG）。',
          '考试题库/组卷/自动判分（在线考试 EXAM）≠ 简易问卷填写回收（问卷 SURVEY）≠ 网上评教多维打分（评教 EVAL）；党建/驾校/安全答题同 EXAM 换皮；实验室开题写「准入考试/先考试」→ 先考后申挂 exam。',
          '十佳/评选在线投票计票（投票 VOTE）≠ 社团活动报名占名额（活动 ACTIVITY）；开题同时写报名+投票 → 活动域并挂 vote（复合）。',
          '制度/课件文库下载台账（文库 DOCLIB）≠ 图书借阅归还（图书 LIBRARY）≠ 院刊资讯收藏（博客 BLOG）。',
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
        ],
      },
      {
        title: '换皮全覆盖清单索引',
        tag: '索引',
        wide: true,
        lead: '运营对照仓库 docs/domain-skin-gap-analysis.md；样例均在 data/samples/，可直接上传匹配。',
        bullets: [
          '§2 易混对 M-01～M-15：本页「领域易混」卡 + test_confusion_pairs。',
          '§3 深皮 S-*：data/samples/深皮开题/（S-01…S-74）。',
          '§4 预设 P-*：申请预设开题/、学工预设开题/、长尾预设开题/（P-01～P-29；P-30 三联拒绝）。',
          '§5 能力 C-*：考试/问卷/投票/文库/拼车/时间银行/影院/会签/进销存/签章等 *预设开题/；C-05～C-10 挂载见对应 P 样例。',
          '§6 交叉 X-*：交叉预设开题/（X-01 点餐+报修、X-02 图书+座位、X-03 下单+预约）与图书借阅与二手交叉开题。',
          '进度总览见清单 §9；能力矩阵见 HANDOFF.md。',
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
        lead: '大模型仅填充业务配置（Island 文案、E-R 中文、模块图、测试用例等），不写业务源码。开启「业务配置填充」后，工厂会先拆解计划再按 Unit 并发调用。',
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
          '端口池限制同时预览数量，不限制选题库存。',
          '服务器部署须配置 GF_PUBLIC_HOST，保证预览链接可访问。',
          '「释放异常占用」只清理未托管却占端口的进程；正在预览的项目须到项目详情停止。',
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
          { name: '持久层', def: '匹配确认中的数据访问实现：JdbcTemplate、MyBatis（绑 PageHelper）或 Spring Data JPA。只换实现与说明书措辞，不换业务能力；与骨架、领域同级，独立于视觉选项。' },
          { name: '工程基线', def: '学生 ZIP 的物理工程模板（内部 skeletons/baseline）。与匹配页「骨架」不是同一概念。' },
          { name: '匹配确认', def: '核验并锁定推荐骨架、领域、身份场景、主路径入口（分叉域）、持久层与鉴权等。开题依据弱时须勾「主路径已核对」；确认前不可正式生成；改动后须重新确认。视觉选项在「一键生成」页调整。' },
          { name: '身份场景', def: '校园 / 企业 / 社区等身份档，决定资料字段与壳文案。匹配确认可解锁手改；扫题只推荐。' },
          { name: '主路径入口', def: '同域「谁怎么用」分叉（如本人打卡 vs 对象台账、绑岗 vs 选岗、调宿 vs 选房）。仅部分域有选项；手改后 bake 跟出包选择，不改开题原文。' },
          { name: '生成配置', def: '描述业务配置的结构化数据（内部亦称 Spec）。大模型主要填充此类配置，而非手写业务代码。' },
          { name: '填岛拆解', def: '业务配置填充的执行方式：先根据工程与开题生成 DeliveryPlan，再按 Unit 并发调用大模型并合并回 Spec；不改业务源码。' },
          { name: 'Unit', def: '填岛拆解中的最小任务单元（如 E-R 中文、模块图、某类 Island 文案）。各 Unit 独立生成、校验与重试。' },
          { name: '填岛并发', def: '同时执行的 Unit 数量上限，默认 3。在「大模型」页配置，对应环境变量 GF_FILL_UNIT_CONCURRENCY。' },
          { name: '视觉与生成选项', def: '配色、质感、布局、字体、智能填充与密码策略；在「一键生成」页即时保存，写入工程须重新生成。' },
          { name: '基线生成', def: '基于工程基线、骨架、领域与生成配置将工程落地的主路径（内部亦称 bake）。' },
          { name: '能力运行时', def: '工程基线内已实现的通用业务能力；领域通过能力组合复用同一套运行时。' },
          { name: '工程目录', def: '单个项目生成后的本机工程目录，供预览、质量检查与打包下载使用。' },
          { name: 'E-R 图', def: '按交付库表与联系绘制的陈氏线框图；总图不含属性。位于「产物 → 数据库」。' },
          { name: '论文材料', def: '功能模块图与软件测试用例；位于「产物 → 论文材料」，按交付菜单推导。' },
          { name: '软件测试用例', def: '由菜单与角色推导的用例表；字段模板 5～9 可选。可选大模型只润色文案。' },
          { name: '质量检查', def: '交付前的自动验收项集合。关键项未通过时暂不可下载交付包。含语义门禁（可见面与场景）与交付质量摘要。' },
          { name: '开题措辞核对', def: '生成前弹窗：开题功能行与 Spec 清单项名静态比对，不扫工程。' },
          { name: '清单实装验收', def: '生成后质量检查：扫描 workspace，核对清单项是否在 ZIP 中有对应实现（P3a 门禁同源）。' },
          { name: '交付复审', def: '产物页运营流程：验圈冻结安全区、登记偏差、合卷同步 ZIP。不进学生交付包。' },
          { name: '验圈', def: '交付复审中一轮验收：检查门禁单调性、刷新质量摘要，将通过项纳入安全区。' },
          { name: '合卷', def: '验圈通过后重新打包 ZIP，使交付包与当前工程目录一致。' },
          { name: '安全区', def: '交付复审中已冻结并通过的门禁与 checklist 项；验圈时不得回退。' },
          { name: '毒区', def: '交付复审中尚未收敛、待处理的门禁或 checklist 项。' },
          { name: '交付包锁定', def: '因质量检查未过或工程与验收规则不一致，系统禁用压缩包下载的状态。' },
          { name: '预览', def: '在端口池内临时启动前后端做快速验收；不作为生产部署。' },
          { name: '端口池', def: '预留给预览的端口区间，用于限制同时运行的预览实例数量。' },
          { name: '任务队列', def: '异步生成任务列表，用于查看排队、生成中、失败与重试。' },
        ],
      },
    ],
  },
]
</script>
