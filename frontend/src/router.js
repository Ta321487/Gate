import { createRouter, createWebHistory } from 'vue-router'
import Projects from './views/Projects.vue'
import ProjectDetail from './views/ProjectDetail.vue'
import Jobs from './views/Jobs.vue'
import DeepSeek from './views/DeepSeek.vue'
import System from './views/System.vue'
import ErrorPage from './views/ErrorPage.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'projects', component: Projects, meta: { crumb: '项目' } },
    { path: '/projects/:id', name: 'project', component: ProjectDetail, meta: { crumb: '详情' } },
    { path: '/jobs', name: 'jobs', component: Jobs, meta: { crumb: '任务队列' } },
    { path: '/deepseek', name: 'deepseek', component: DeepSeek, meta: { crumb: 'DeepSeek' } },
    { path: '/system', name: 'system', component: System, meta: { crumb: '运行环境' } },
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
      props: { code: 500, retryable: true },
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
