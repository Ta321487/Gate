import { createRouter, createWebHistory } from 'vue-router'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Profile from '../views/Profile.vue'
import Notices from '../views/Notices.vue'
import NoticeDetail from '../views/NoticeDetail.vue'
import NoticesAdmin from '../views/admin/NoticesAdmin.vue'
import PortalLayout from '../layouts/PortalLayout.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import Books from '../views/reader/Books.vue'
import BookDetail from '../views/reader/BookDetail.vue'
import MyBorrows from '../views/reader/MyBorrows.vue'
import Dashboard from '../views/admin/Dashboard.vue'
import BooksAdmin from '../views/admin/BooksAdmin.vue'
import CategoriesAdmin from '../views/admin/CategoriesAdmin.vue'
import ReadersAdmin from '../views/admin/ReadersAdmin.vue'
import BorrowsAdmin from '../views/admin/BorrowsAdmin.vue'
import BorrowRecordsAdmin from '../views/admin/BorrowRecordsAdmin.vue'
import OverdueAdmin from '../views/admin/OverdueAdmin.vue'

const specialRoutes = [
  {
    path: '/error',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: '500' },
  },
  {
    path: '/loading',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: 'loading' },
  },
  {
    path: '/:pathMatch(.*)*',
    name: 'not-found',
    component: () => import('../views/special/SpecialPage.vue'),
    props: { kind: '404' },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: Login },
    { path: '/register', component: Register },
    {
      path: '/',
      component: PortalLayout,
      children: [
        { path: '', redirect: '/books' },
        { path: 'books', component: Books },
        { path: 'books/:id', component: BookDetail },
        { path: 'my-borrows', component: MyBorrows },
        { path: 'notices', component: Notices },
        { path: 'notices/:id', component: NoticeDetail },
        { path: 'profile', component: Profile },
      ],
      beforeEnter: (_to, _from, next) => {
        if (localStorage.getItem('role') === 'admin') next('/admin/dashboard')
        else next()
      },
    },
    {
      path: '/admin',
      component: AdminLayout,
      children: [
        { path: '', redirect: '/admin/dashboard' },
        { path: 'dashboard', component: Dashboard },
        { path: 'books', component: BooksAdmin },
        { path: 'categories', component: CategoriesAdmin },
        { path: 'readers', component: ReadersAdmin },
        { path: 'borrows', component: BorrowsAdmin },
        { path: 'borrow-records', component: BorrowRecordsAdmin },
        { path: 'overdue', component: OverdueAdmin },
        { path: 'notices', component: NoticesAdmin },
        { path: 'profile', component: Profile },
      ],
      beforeEnter: (to, _from, next) => {
        if (localStorage.getItem('role') !== 'admin') {
          next('/books')
          return
        }
        const superOnly = ['/admin/books', '/admin/categories', '/admin/readers', '/admin/notices']
        if (superOnly.includes(to.path) && localStorage.getItem('superAdmin') !== 'true') {
          next('/admin/dashboard')
          return
        }
        next()
      },
    },
    ...specialRoutes,
  ],
})

const publicPaths = new Set(['/login', '/register', '/error', '/loading'])

router.beforeEach((to, _from, next) => {
  const token = localStorage.getItem('token')
  if (!publicPaths.has(to.path) && !token) next('/login')
  else next()
})

export default router
