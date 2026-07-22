<template>
  <div class="help-page">
    <h1 class="page-title">帮助文档</h1>
    <p class="page-desc">本说明面向运营人员，介绍毕设港工作台的标准使用流程、交付条件与常用术语。</p>

    <section v-for="sec in sections" :key="sec.title" class="help-section">
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
const sections = [
  {
    title: '总览',
    cards: [
      {
        title: '产品定位',
        tag: '总览',
        lead: '毕设港工作台用于依据开题、任务书等材料完成选题匹配、工程生成、质量检查与本地预览，并在检查通过后提供可交付压缩包。',
        bullets: [
          '以固定基线骨架与能力运行时为主体；大语言模型仅填充业务配置，不承担业务代码编写。',
          '交付质量以质量检查结果为准，不以生成耗时或文案完整度替代判定。',
        ],
      },
      {
        title: '注意事项',
        tag: '规范',
        bullets: [
          '请勿将未通过质量检查的工程作为最终交付物提供给学生或指导教师。',
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
            body: '在「项目」页上传材料（开题 / 任务书 / 功能清单等，PDF / Word / TXT，可一次多选，最多 8 份）。系统解析后自动创建项目记录，进入项目详情。',
          },
          {
            title: '匹配确认',
            body: '在「匹配确认」页核验推荐骨架与领域。确认无误后锁定匹配；如需调整，须先解锁再修改并重新确认。配色、布局等视觉选项在「一键生成」页调整。',
          },
          {
            title: '一键生成',
            body: '匹配确认后，在「一键生成」页调整视觉与生成选项（即时保存），再启动生成。生成完成后可同页改选项并「按当前选项重新生成」。进度可在「任务队列」与项目详情中查看。',
          },
          {
            title: '预览与验收',
            body: '于「运行」页启动前后端预览做快速验收；于「产物 / 对照」核对质量检查、数据库（表结构 / E-R）、论文材料（模块图 / 测试用例）与学生端 API。',
          },
          {
            title: '交付',
            body: '质量检查全部通过后方可下载交付包。未通过或工程与验收规则不一致时下载保持锁定，须重新生成或排查未通过项。',
          },
        ],
      },
      {
        title: '质量检查与交付',
        tag: '交付',
        wide: true,
        lead: '质量检查是交付条件的组成部分。主流程或功能清单等关键项未通过时，系统暂不可下载交付包，以防不合格工程外发。',
        bullets: [
          '检查明细见项目详情「产物 / 对照」中的「质量检查」。',
          '骨架或运行时升级后，既有工程目录可能与当前规则不一致，须重新生成。',
          '质量检查通过仅表示结构与声明能力达标，不替代运营人员对业务路径的人工预览确认。',
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
          '大模型只润色文案，不增删用例、不改编号与模块归属。',
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
        ],
      },
    ],
  },
  {
    title: '运维',
    cards: [
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
          { name: '骨架', def: '学生工程的技术基线模板。匹配时选定骨架，决定可生成工程的基础形态。' },
          { name: '领域', def: '题目所属业务域。决定文案、菜单与能力组合，与骨架配合使用。' },
          { name: '匹配确认', def: '核验并锁定推荐骨架与领域。确认前不可正式生成；改动后须重新确认。视觉选项在「一键生成」页调整。' },
          { name: '生成配置', def: '描述业务配置的结构化数据（内部亦称 Spec）。大模型主要填充此类配置，而非手写业务代码。' },
          { name: '视觉与生成选项', def: '配色、质感、布局、字体、智能填充与密码策略；在「一键生成」页即时保存，写入工程须重新生成。' },
          { name: '基线生成', def: '基于骨架与生成配置将工程落地的主路径（内部亦称 bake）。' },
          { name: '能力运行时', def: '基线内已实现的通用业务能力；领域通过能力组合复用同一套运行时。' },
          { name: '工程目录', def: '单个项目生成后的本机工程目录，供预览、质量检查与打包下载使用。' },
          { name: 'E-R 图', def: '按交付库表与联系绘制的陈氏线框图；总图不含属性。位于「产物 → 数据库」。' },
          { name: '论文材料', def: '功能模块图与软件测试用例；位于「产物 → 论文材料」，按交付菜单推导。' },
          { name: '软件测试用例', def: '由菜单与角色推导的用例表；字段模板 5～9 可选。可选大模型只润色文案。' },
          { name: '质量检查', def: '交付前的自动验收项集合。关键项未通过时暂不可下载交付包。' },
          { name: '交付包锁定', def: '因质量检查未过或工程与验收规则不一致，系统禁用压缩包下载的状态。' },
          { name: '预览', def: '在端口池内临时启动前后端做快速验收；不作为生产部署。' },
          { name: '端口池', def: '预留给预览的端口区间，用于限制同时运行的预览实例数量。' },
          { name: '任务队列', def: '异步生成等任务的状态列表，用于查看排队、执行、失败与重试。' },
        ],
      },
    ],
  },
]
</script>
