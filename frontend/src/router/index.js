// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Асинхронная загрузка компонентов (lazy loading)
const CoinsList = () => import('../views/CoinsList.vue')
const CoinDetail = () => import('../views/CoinDetail.vue')
const AdminPanel = () => import('../views/AdminPanel.vue')

// Определение маршрутов
const routes = [
  {
    path: '/',
    name: 'CoinsList',
    component: CoinsList,
    meta: { title: 'Список монет' }
  },
  {
    path: '/coin/:id',
    name: 'CoinDetail',
    component: CoinDetail,
    meta: { title: 'Детали монеты' },
    props: true
  },
  {
    path: '/admin',
    name: 'AdminPanel',
    component: AdminPanel,
    meta: { title: 'Админ-панель' }
  },
  // Редирект с несуществующих путей
  {
    path: '/:catchAll(.*)',
    redirect: '/'
  }
]

// Создание роутера
const router = createRouter({
  history: createWebHistory(),
  routes
})

// Глобальный навигационный хук (опционально — для логирования)
router.beforeEach((to, from, next) => {
  document.title = to.meta.title ? `${to.meta.title} | Crypto Dashboard` : 'Crypto Dashboard'
  console.log(`[Router] Переход: ${from.path} → ${to.path}`)
  next()
})

export default router