<template>
  <div class="container">
    <h1>Список монет</h1>
    <p v-if="loading">Загрузка...</p>
    <p v-else-if="coins.length === 0">Нет данных</p>
    <ul v-else>
      <li v-for="coin in coins" :key="coin.id">
        {{ coin.project_name }} ({{ coin.project_symbol }}) — {{ coin.launch_date }}
      </li>
    </ul>
    <p>Количество: {{ coins.length }}</p>
  </div>
</template>

<script>
import api from '@/services/api'

export default {
  data() {
    return {
      coins: [],
      loading: true
    }
  },
  created() {
    console.log('✅ created: вызов fetchCoins')
    this.fetchCoins()
  },
  methods: {
    async fetchCoins() {
      try {
        console.log('➡️ Запрос к /api/coins/')
        const response = await api.get('coins/')
        console.log('✅ Данные получены:', response.data)
        this.coins = response.data.results || response.data
      } catch (error) {
        console.error('❌ Ошибка получения монет:', error)
        console.error('URL:', api.defaults.baseURL + 'coins/')
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
</style>