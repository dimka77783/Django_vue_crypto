// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Компоненты
const CoinsList = () => import('../views/CoinsList.vue')
const CoinDetail = () => import('../views/CoinDetail.vue')
const AdminPanel = () => import('../views/AdminPanel.vue') // ✅ Добавлено

const routes = [
  { path: '/', component: CoinsList, name: 'CoinsList' },
  { path: '/coin/:id', component: CoinDetail, name: 'CoinDetail' },
  { path: '/admin', component: AdminPanel, name: 'AdminPanel' } // ✅ Добавлено
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router