import { createRouter, createWebHistory } from 'vue-router'
import OpsHome from './views/OpsHome.vue'
import Projects from './views/Projects.vue'
import ProjectDetail from './views/ProjectDetail.vue'
import Jobs from './views/Jobs.vue'
import FailAnalysis from './views/FailAnalysis.vue'
import Help from './views/Help.vue'
import Llm from './views/Llm.vue'
import Unsplash from './views/Unsplash.vue'
import System from './views/System.vue'
import ZhLexicon from './views/ZhLexicon.vue'
import StatusCopy from './views/StatusCopy.vue'
import DictValues from './views/DictValues.vue'
import DemoScripts from './views/DemoScripts.vue'
import AddonSuggest from './views/AddonSuggest.vue'
import CapCards from './views/CapCards.vue'
import ErrorCopy from './views/ErrorCopy.vue'
import WidgetHints from './views/WidgetHints.vue'
import MenuMatrix from './views/MenuMatrix.vue'
import RuleParams from './views/RuleParams.vue'
import ErEdgeCopy from './views/ErEdgeCopy.vue'
import DemoAccounts from './views/DemoAccounts.vue'
import DiagramTitles from './views/DiagramTitles.vue'
import DiagramVerbs from './views/DiagramVerbs.vue'
import UsecaseFlows from './views/UsecaseFlows.vue'
import ErrorPage from './views/ErrorPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'ops-home', component: OpsHome, meta: { crumb: '开工台' } },
    { path: '/projects', name: 'projects', component: Projects, meta: { crumb: '项目' } },
    { path: '/projects/:id', name: 'project', component: ProjectDetail, meta: { crumb: '详情' } },
    { path: '/jobs', name: 'jobs', component: Jobs, meta: { crumb: '任务队列' } },
    {
      path: '/fail-analysis',
      name: 'fail-analysis',
      component: FailAnalysis,
      meta: { crumb: '失败分析' },
    },
    { path: '/help', name: 'help', component: Help, meta: { crumb: '帮助文档' } },
    { path: '/llm', name: 'llm', component: Llm, meta: { crumb: '大模型' } },
    { path: '/deepseek', redirect: '/llm' },
    { path: '/gemini', redirect: '/llm' },
    { path: '/unsplash', name: 'unsplash', component: Unsplash, meta: { crumb: 'Unsplash' } },
    { path: '/system', name: 'system', component: System, meta: { crumb: '运行环境' } },
    { path: '/zh-lexicon', name: 'zh-lexicon', component: ZhLexicon, meta: { crumb: '词表维护' } },
    { path: '/status-copy', name: 'status-copy', component: StatusCopy, meta: { crumb: '状态话术' } },
    { path: '/dict-values', name: 'dict-values', component: DictValues, meta: { crumb: '字典台' } },
    { path: '/demo-scripts', name: 'demo-scripts', component: DemoScripts, meta: { crumb: '演示剧本' } },
    { path: '/addon-suggest', name: 'addon-suggest', component: AddonSuggest, meta: { crumb: '开关建议' } },
    { path: '/cap-cards', name: 'cap-cards', component: CapCards, meta: { crumb: '能力说明' } },
    { path: '/error-copy', name: 'error-copy', component: ErrorCopy, meta: { crumb: '错误码中文' } },
    { path: '/widget-hints', name: 'widget-hints', component: WidgetHints, meta: { crumb: '控件语义' } },
    { path: '/menu-matrix', name: 'menu-matrix', component: MenuMatrix, meta: { crumb: '菜单矩阵' } },
    { path: '/rule-params', name: 'rule-params', component: RuleParams, meta: { crumb: '规则参数' } },
    { path: '/er-edge-copy', name: 'er-edge-copy', component: ErEdgeCopy, meta: { crumb: '表关系叙事' } },
    { path: '/demo-accounts', name: 'demo-accounts', component: DemoAccounts, meta: { crumb: '测试账号' } },
    { path: '/diagram-titles', name: 'diagram-titles', component: DiagramTitles, meta: { crumb: '论文图题' } },
    { path: '/diagram-verbs', name: 'diagram-verbs', component: DiagramVerbs, meta: { crumb: '实体动作词' } },
    { path: '/usecase-flows', name: 'usecase-flows', component: UsecaseFlows, meta: { crumb: '用例流程' } },
    {
      path: '/thesis-absorb',
      name: 'thesis-absorb',
      component: () => import('./views/ThesisAbsorb.vue'),
      meta: { crumb: '终稿吸收' },
    },
    {
      path: '/thesis-absorb/:id',
      name: 'thesis-absorb-detail',
      component: () => import('./views/ThesisAbsorb.vue'),
      meta: { crumb: '终稿吸收' },
    },
    {
      path: '/error/500',
      name: 'error-500',
      component: ErrorPage,
      meta: {
        crumb: '服务异常',
        code: 500,
        title: '服务异常',
        description: '请求处理失败，或上游服务暂时不可用。可稍后重试，或从侧栏回到工作台。',
      },
      props: { code: 500 },
    },
    {
      path: '/:pathMatch(.*)*',
      name: 'not-found',
      component: ErrorPage,
      meta: {
        crumb: '未找到',
        code: 404,
        title: '页面不存在',
        description: '当前地址未匹配到路由，链接可能已失效或项目 ID 有误。',
      },
      props: { code: 404 },
    },
  ],
})

export default router
