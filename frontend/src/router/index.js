// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Компоненты
const CoinsList = () => import('../views/CoinsList.vue')
const CoinDetail = () => import('../views/CoinDetail.vue')

// Роуты
const routes = [
  { path: '/', component: CoinsList, name: 'CoinsList' },
  { path: '/coin/:id', component: CoinDetail, name: 'CoinDetail' }
]

// Создание роутера
const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router