<template>
  <div class="admin-panel">
    <h2>🛠️ Админ-панель</h2>
    <button @click="startParsing" :disabled="loading">
      {{ loading ? 'Парсинг...' : '🚀 Запустить полный парсинг' }}
    </button>
    <p v-if="status" class="status">{{ status }}</p>
  </div>
</template>

<script>
import api from '../services/api'

export default {
  data() {
    return {
      loading: false,
      status: ''
    }
  },
  methods: {
    async startParsing() {
      this.loading = true
      this.status = 'Запуск...'
      try {
        await api.post('/api/trigger-parsing/')
        this.status = '✅ Парсинг запущен в фоне. Данные обновятся через 10-15 мин.'
      } catch (err) {
        this.status = '❌ Ошибка: ' + (err.response?.data?.message || err.message)
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style>
.admin-panel { padding: 2rem; }
button { padding: 0.8rem 1.5rem; font-size: 1rem; }
.status { margin-top: 1rem; color: #d63384; }
</style>