// frontend/src/router/index.js
import { createRouter, createWebHistory } from 'vue-router'

// Заглушки для маршрутов
const CoinsList = { template: '<div><h1>Список монет</h1><p>Данные загружаются...</p></div>' }
const AdminPanel = { template: '<div><h1>Админ-панель</h1><p>Кнопка запуска парсинга</p></div>' }

const routes = [
  { path: '/', component: CoinsList },
  { path: '/admin', component: AdminPanel }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router