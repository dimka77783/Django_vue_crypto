<template>
  <div class="container">
    <h1>Список монет</h1>
    <ul>
      <li v-for="coin in coins" :key="coin.id">
        {{ coin.project_name }} ({{ coin.project_symbol }}) — {{ coin.launch_date }}
      </li>
    </ul>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  data() {
    return {
      coins: [],
    };
  },
  created() {
    this.fetchCoins();
  },
  methods: {
    async fetchCoins() {
      try {
        const response = await api.get('/coins/');
        this.coins = response.data;
      } catch (error) {
        console.error('Ошибка получения данных:', error);
      }
    },
  },
};
</script>