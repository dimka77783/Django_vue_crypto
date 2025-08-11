<!-- frontend/src/views/CoinsList.vue -->
<template>
  <div class="container">
    <h1>Список монет</h1>
    <ul class="coins-list">
      <li v-for="coin in coins" :key="coin.id">
        <router-link :to="{ name: 'CoinDetail', params: { id: coin.id } }">
          {{ coin.project_name }} ({{ coin.project_symbol }}) — {{ formatDate(coin.launch_date) }}
        </router-link>
      </li>
    </ul>
    <p v-if="loading">Загрузка...</p>
    <p v-else-if="coins.length === 0">Нет данных</p>
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
    this.fetchCoins()
  },
  methods: {
    async fetchCoins() {
      try {
        const response = await api.get('/coins/')
        this.coins = response.data.results || response.data
      } catch (error) {
        console.error('Ошибка:', error)
      } finally {
        this.loading = false
      }
    },
    formatDate(dateStr) {
      if (!dateStr) return 'TBA'
      const date = new Date(dateStr)
      return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      })
    }
  }
}
</script>

<style scoped>
.container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}
.coins-list li {
  margin: 10px 0;
}
.coins-list a {
  text-decoration: none;
  color: #007bff;
  font-size: 1.1em;
}
.coins-list a:hover {
  text-decoration: underline;
}
</style>