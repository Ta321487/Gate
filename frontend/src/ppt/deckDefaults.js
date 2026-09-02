import { EMPTY_COVER } from './types.js'

export const PPT_THEME_OPTIONS = [
  { value: 'scholar', label: 'scholar · 学术默认（按种子）', accent: '#0b6e75', soft: '#d7eef0', ink: '#1a2b34' },
  { value: 'ink', label: 'ink · 墨蓝', accent: '#1e3a5f', soft: '#dbe4f0', ink: '#142033' },
  { value: 'grove', label: 'grove · 青松', accent: '#2f6b4f', soft: '#dceee4', ink: '#1a2e24' },
]

export const PPT_LAYOUT_OPTIONS = [
  { value: 'band', label: 'band · 色带（按种子）', hint: '左侧色带' },
  { value: 'center', label: 'center · 居中', hint: '标题居中' },
  { value: 'footer', label: 'footer · 底栏', hint: '底部色条' },
]

export function pptThemeMeta(value) {
  return PPT_THEME_OPTIONS.find((o) => o.value === value) || PPT_THEME_OPTIONS[0]
}

export function pptLayoutMeta(value) {
  return PPT_LAYOUT_OPTIONS.find((o) => o.value === value) || PPT_LAYOUT_OPTIONS[0]
}


export const PPT_MASTER_OPTIONS = [
  { value: 'none', label: '无 · 学术默认' },
  { value: 'college_demo', label: '某学院统一母版（示意）' },
]

export const PPT_PIPELINE_STEPS = [
  { key: 'collect', title: '收集证据（开题 + 菜单/栈 + 模块图/E-R/用例）' },
  { key: 'fill', title: '填页 Unit（LLM 只整形，校验锁源）' },
  { key: 'screenshots', title: '采集界面截图（主路径半自动）' },
  { key: 'check', title: '瞎写/结构检查' },
  { key: 'write', title: '写 deck.json（嵌入图引用）' },
]

export const PPT_UNIT_DEFS = [
  { key: 'ppt.cover', title: '封面' },
  { key: 'ppt.toc', title: '目录' },
  { key: 'ppt.background', title: '背景与需求' },
  { key: 'ppt.tech', title: '技术选型' },
  { key: 'ppt.arch', title: '系统架构' },
  { key: 'ppt.modules', title: '功能模块' },
  { key: 'ppt.er', title: 'E-R 图' },
  { key: 'ppt.demo', title: '实现与演示' },
  { key: 'ppt.test', title: '测试' },
  { key: 'ppt.summary', title: '总结与致谢' },
]

const DEMO_BADGE =
  'data:image/svg+xml,' +
  encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="96" height="96"><circle cx="48" cy="48" r="40" fill="none" stroke="#0b6e75" stroke-width="6"/><text x="48" y="54" text-anchor="middle" font-size="18" fill="#0b6e75" font-family="sans-serif">校</text></svg>',
  )

/** 系统类终期默认大纲样例 deck（mock / 预览骨架） */
export function buildSampleDeck({ title = '毕业设计答辩', cover = null, theme = 'scholar', layout_family = 'band', master = 'none' } = {}) {
  const c = { ...EMPTY_COVER(), ...(cover || {}) }
  if (!c.badge_data_url) c.badge_data_url = DEMO_BADGE
  return {
    version: '1',
    title,
    theme,
    layout_family,
    master,
    cover: c,
    biz_dirty: false,
    pages: [
      {
        id: 'cover',
        title: '封面',
        role: 'cover',
        cover: { ...c },
      },
      {
        id: 'toc',
        title: '目录',
        role: 'toc',
        toc_items: [
          '背景与需求',
          '方案与技术选型',
          '系统设计',
          '实现与演示',
          '测试',
          '总结与致谢',
        ],
      },
      {
        id: 'background',
        title: '背景与需求',
        role: 'bullets',
        bullets: [
          {
            id: 'bg-1',
            text: '围绕开题材料中的业务背景与痛点展开（来源：开题）',
            locked: false,
            source_refs: ['proposal'],
          },
          {
            id: 'bg-2',
            text: '明确目标用户与核心业务流程（来源：开题∪实包菜单）',
            locked: true,
            source_refs: ['proposal', 'menu'],
          },
          {
            id: 'bg-3',
            text: '梳理非功能约束：可演示、可交付、可答辩讲解',
            locked: false,
            source_refs: ['proposal'],
          },
        ],
      },
      {
        id: 'tech',
        title: '技术选型',
        role: 'table',
        table: {
          headers: ['层次', '技术', '说明'],
          rows: [
            ['后端', 'Spring Boot', '与实包一致'],
            ['前端', 'Vue 3 + Element Plus', '与实包一致'],
            ['持久层', 'JdbcTemplate / MyBatis / JPA', '跟项目 persistence'],
            ['数据库', 'MySQL', '演示库种子同源'],
          ],
        },
        bullets: [
          {
            id: 'tech-1',
            text: '技术名仅取自开题可交付项与实包扫描，禁止编造中间件',
            locked: false,
            source_refs: ['stack'],
          },
        ],
      },
      {
        id: 'arch',
        title: '系统架构',
        role: 'bullets',
        bullets: [
          { id: 'arch-1', text: '前后端分离：运营预览双端口 / 学生交付同构', source_refs: ['arch'] },
          { id: 'arch-2', text: '角色与菜单按域能力挂载，主路径可走通', source_refs: ['menu'] },
          { id: 'arch-3', text: '数据层与门禁扫描对齐，保证可下载口径', source_refs: ['gates'] },
        ],
      },
      {
        id: 'modules',
        title: '功能模块',
        role: 'modules',
        figure: { kind: 'modules', label: '模块图（嵌自产物 SVG）', available: true },
        bullets: [
          { id: 'mod-1', text: '模块划分与实包菜单/能力树一致', source_refs: ['modules'] },
        ],
      },
      {
        id: 'er',
        title: 'E-R 图',
        role: 'er',
        figure: { kind: 'er', label: 'E-R 图（嵌自产物 SVG）', available: true },
        bullets: [
          { id: 'er-1', text: '实体中文名与表结构来自实包 schema', source_refs: ['schema'] },
        ],
      },
      {
        id: 'demo',
        title: '实现与演示',
        role: 'demo',
        figure: {
          kind: 'screenshot',
          label: '主流程界面截图',
          available: false,
          missing: true,
          hint: '缺主流程截图 · 检查将报 error',
        },
        bullets: [
          {
            id: 'demo-1',
            text: '演示账号与 README 一致；截图跟 bake 种子同源',
            source_refs: ['runtime', 'seed'],
          },
          {
            id: 'demo-2',
            text: '登录 → 主列表 → 关键业务动作（域主路径）',
            locked: false,
            source_refs: ['flows'],
          },
        ],
      },
      {
        id: 'test',
        title: '测试',
        role: 'table',
        table: {
          headers: ['用例', '步骤摘要', '预期'],
          rows: [
            ['登录', '演示账号登录', '进入工作台'],
            ['主流程', '按用例表走通', '状态正确落库'],
            ['权限', '角色切换', '菜单与操作隔离'],
          ],
        },
        bullets: [
          { id: 'test-1', text: '用例要点来自产物用例表', source_refs: ['testcases'] },
        ],
      },
      {
        id: 'summary',
        title: '总结与致谢',
        role: 'summary',
        bullets: [
          { id: 'sum-1', text: '完成系统设计、实现与可演示交付' },
          { id: 'sum-2', text: '感谢导师与同学的指导与帮助' },
        ],
      },
    ],
  }
}

export function seedThemeForProject(projectId) {
  const id = String(projectId || '0')
  let h = 0
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) >>> 0
  const themes = PPT_THEME_OPTIONS.map((o) => o.value)
  const layouts = PPT_LAYOUT_OPTIONS.map((o) => o.value)
  return {
    theme: themes[h % themes.length],
    layout_family: layouts[(h >> 3) % layouts.length],
    master: 'none',
  }
}

export { DEMO_BADGE }
