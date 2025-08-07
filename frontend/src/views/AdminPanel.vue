<!-- frontend/src/views/AdminPanel.vue -->
<template>
  <div class="admin-panel">
    <h1>🛠️ Админ-панель</h1>
    <button @click="triggerParse" :disabled="loading">
      {{ loading ? 'Парсинг...' : '🚀 Запустить полный парсинг' }}
    </button>
    <p v-if="status">{{ status }}</p>
  </div>
</template>

<script>
import api from '@/services/api'; // ✅ Правильный путь

export default {
  data() {
    return {
      loading: false,
      status: ''
    }
  },
  methods: {
    async triggerParse() {
      this.loading = true;
      this.status = 'Запуск...';
      try {
        await api.post('/trigger-parsing/');
        this.status = '✅ Парсинг запущен. Данные обновятся через 5-10 мин.';
      } catch (err) {
        this.status = '❌ Ошибка: ' + (err.response?.data?.message || err.message);
      } finally {
        this.loading = false;
      }
    }
  }
}
</script>

<style scoped>
.admin-panel {
  padding: 2rem;
  max-width: 600px;
  margin: 0 auto;
}
button {
  padding: 0.8rem 1.5rem;
  font-size: 1rem;
}
.status {
  margin-top: 1rem;
  color: #d63384;
}
</style>