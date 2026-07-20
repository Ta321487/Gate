<template>
  <div class="help-page">
    <h1 class="page-title">帮助文档</h1>
    <p class="page-desc">本说明面向运营人员，介绍毕设港工作台的标准使用流程、交付条件与常用术语。</p>

    <div class="help-cards">
      <article
        v-for="card in cards"
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
  </div>
</template>

<script setup>
const cards = [
  {
    title: '产品定位',
    tag: '总览',
    lead: '毕设港工作台用于依据开题报告完成选题匹配、工程生成、质量门禁校验与本地预览，并在门禁通过后提供可交付压缩包。',
    bullets: [
      '以固定基线骨架与能力运行时为主体；大语言模型仅填充业务配置（Schema），不承担业务代码编写。',
      '交付质量以门禁结果为准，不以生成耗时或文案完整度替代判定。',
    ],
  },
  {
    title: '注意事项',
    tag: '规范',
    bullets: [
      '请勿将未过门禁的工程作为最终交付物提供给学生或指导教师。',
      '匹配确认前请认真阅读解析摘要；擅自更换领域可能导致能力组合与题目不符。',
      '预览仅供验收使用，不构成生产环境部署方案。',
      '界面与操作约定如有调整，以当前版本页面提示为准。',
    ],
  },
  {
    title: '标准作业流程',
    tag: '流程',
    wide: true,
    steps: [
      {
        title: '创建项目',
        body: '在「项目」页上传开题报告（PDF / Word / TXT）。系统解析题目后自动创建项目记录，进入项目详情。',
      },
      {
        title: '匹配确认',
        body: '在「匹配确认」页核验推荐骨架与领域。确认无误后锁定匹配；如需调整，须先解锁再修改并重新确认。',
      },
      {
        title: '一键生成',
        body: '匹配确认后方可启动生成。生成过程以 bake 为主，进度可在「任务队列」与项目详情中查看。',
      },
      {
        title: '预览与验收',
        body: '于「运行」页启动前后端预览做冒烟检查；于「产物 / 对照」页核对门禁、表结构、学生端 API 与 E-R 图。',
      },
      {
        title: '交付',
        body: '规定门禁全部通过后方可下载 ZIP。未通过或工作区与门禁不一致时下载保持锁定，须重新生成或排查未过项。',
      },
    ],
  },
  {
    title: '质量门禁与交付',
    tag: 'DoD',
    lead: '质量门禁为交付定义（DoD）的组成部分。主流程或功能清单等关键项未通过时，系统禁止下载 ZIP，以防不合格工程外发。',
    bullets: [
      '门禁明细见项目详情「产物 / 对照」中的「门禁 / 清单」。',
      '骨架或运行时升级后，既有工作区可能与当前规则不一致，须重新生成。',
      '门禁通过仅表示结构与声明能力达标，不替代运营人员对业务路径的人工预览确认。',
    ],
  },
  {
    title: '数据库结构',
    tag: '产物',
    lead: '生成完成后，可在「产物 / 对照」查看数据表、字段中文名及类型，并导出 E-R 图。',
    bullets: [
      '字段类型按标准 MySQL 写法展示（如 varchar(60)、decimal(10,2)）。',
      '可通过开关切换「合并类型」与「类型 / 长度分列」；复制内容与当前开关一致。',
      '单表复制为制表符分隔文本，可贴入 Word 后使用「文本转换成表格」。',
      '表头为字段名、中文名、数据类型（分列时另含长度）；中文名已表达业务含义，不设说明列。',
    ],
  },
  {
    title: '学生端 API',
    tag: '产物',
    lead: '「产物 / 对照 → 学生端 API」静态扫描工作区 Controller，列出方法、路径与 Handler，便于对照门禁主流程。',
    bullets: [
      '按门户 / 管理端 / 基线等面筛选；可搜索 path 或 handler。',
      '命中 Spec.gate.flow_api 的接口会标契约键（如 apply / place）。',
      '复制为「方法 + 路径」地址列表；联调基址取运行页后端地址。该视图仅工厂侧，不写入学生 ZIP。',
    ],
  },
  {
    title: '工厂后端 API',
    tag: '运维',
    lead: '毕设港自身（Python / FastAPI）的运维接口，与学生端 ZIP 无关；用于本机调试工厂、对接脚本或 Postman。',
    bullets: [
      '涵盖项目、任务、DeepSeek、运行环境、catalog 等；日常用本站页面，文档供查参与手工调试。',
      '勿与「产物 → 学生端 API」混淆：那是学生工程 Controller，这是工厂 Python 服务。',
      '健康检查：GET /api/health。',
    ],
    links: [
      { href: '/docs', label: 'Swagger · /docs' },
      { href: '/redoc', label: 'ReDoc · /redoc' },
    ],
  },
  {
    title: '任务队列',
    tag: '运维',
    lead: '「任务队列」汇总本机生成与相关异步任务状态，用于排查排队、失败与重试；错误信息亦回写至对应项目详情。',
    bullets: [
      '对已失效或孤立的任务记录，可按页面提供的清理能力处理，避免长期堆积干扰判断。',
    ],
  },
  {
    title: '运行环境',
    tag: '运维',
    lead: '「运行环境」页展示本机 JDK、Maven、Node、学生库 MySQL 以及预览端口池占用。端口池限制同时预览数量，不限制选题库存。',
    bullets: [
      '服务器部署时须配置 GF_PUBLIC_HOST（公网 IP 或域名），以保证预览链接可被正确访问。',
      '「释放僵尸占用」只清理工厂未托管但仍占端口的进程；正在预览的项目须到项目详情停止。',
    ],
  },
  {
    title: '术语说明',
    tag: '词典',
    wide: true,
    terms: [
      { name: '骨架', def: '学生工程的技术基线模板。匹配时选定骨架，决定可生成工程的基础形态。' },
      { name: '领域', def: '题目所属业务域。决定文案、菜单与能力组合，与骨架配合使用。' },
      { name: '匹配确认', def: '核验并锁定推荐骨架与领域。确认前不可正式生成；改动后须重新确认。' },
      { name: 'Spec / Schema', def: '描述业务配置的结构化数据。大模型主要填充此类配置，而非手写业务代码。' },
      { name: 'bake', def: '基于骨架与 Spec 将工程落地的主生成路径，区别于仅调用大模型写代码。' },
      { name: '能力运行时', def: '基线内已实现的通用业务能力；领域通过能力组合复用同一套运行时。' },
      { name: '工作区', def: '单个项目生成后的本机工程目录，供预览、门禁与打包下载使用。' },
      { name: '质量门禁 / DoD', def: '交付前的自动验收项集合。关键项未通过时禁止下载 ZIP。' },
      { name: 'ZIP 锁定', def: '因门禁未过或工作区与门禁不一致，系统禁用压缩包下载的状态。' },
      { name: '预览', def: '在端口池内临时启动前后端做冒烟验收；不作为生产部署。' },
      { name: '端口池', def: '预留给预览的端口区间，用于限制同时运行的预览实例数量。' },
      { name: '任务队列', def: '异步生成等任务的状态列表，用于查看排队、执行、失败与重试。' },
    ],
  },
]
</script>
