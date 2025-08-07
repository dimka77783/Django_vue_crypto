<template>
  <div class="coin-detail">
    <button @click="$router.back()" class="back-button">← Назад</button>

    <div v-if="coin" class="coin-content">
      <h1>{{ coin.project_name }} ({{ coin.project_symbol }})</h1>

      <div class="info-grid">
        <div class="info-item">
          <strong>Дата запуска:</strong>
          <span>{{ formatDate(coin.launch_date) }}</span>
        </div>

        <div class="info-item">
          <strong>Тип:</strong>
          <span>{{ coin.project_type || '—' }}</span>
        </div>

        <div class="info-item">
          <strong>Мони-скор:</strong>
          <span>{{ coin.moni_score || '—' }}</span>
        </div>

        <div class="info-item">
          <strong>Начальная капитализация:</strong>
          <span>{{ coin.initial_cap || '—' }}</span>
        </div>

        <div class="info-item">
          <strong>IDO/ICO сумма:</strong>
          <span>{{ coin.ido_raise || '—' }}</span>
        </div>
      </div>

      <!-- Токеномика -->
      <div v-if="tokenomics" class="tokenomics-section">
        <h2>📊 Токеномика</h2>
        <table class="tokenomics-table">
          <tr>
            <td><strong>Общий объём:</strong></td>
            <td>{{ tokenomics.total_supply || '—' }}</td>
          </tr>
          <tr>
            <td><strong>В обращении:</strong></td>
            <td>{{ tokenomics.circulating_supply || '—' }}</td>
          </tr>
          <tr>
            <td><strong>Макс. объём:</strong></td>
            <td>{{ tokenomics.max_supply || '—' }}</td>
          </tr>
          <tr>
            <td><strong>Цена при запуске:</strong></td>
            <td>{{ tokenomics.initial_price || '—' }}</td>
          </tr>
          <tr>
            <td><strong>Рыночная капитализация:</strong></td>
            <td>{{ tokenomics.market_cap || '—' }}</td>
          </tr>
          <tr>
            <td><strong>Качество данных:</strong></td>
            <td :class="tokenomics.data_quality.toLowerCase()">
              {{ tokenomics.data_quality }}
            </td>
          </tr>
        </table>

        <!-- Распределение -->
        <div v-if="tokenomics.distribution_data" class="distribution">
          <h3>🎯 Распределение токенов</h3>
          <ul>
            <li v-for="(value, key) in tokenomics.distribution_data" :key="key">
              {{ key }}: <strong>{{ value }}</strong>
            </li>
          </ul>
        </div>
      </div>

      <!-- Инвесторы -->
      <div v-if="coin.investors && coin.investors.length > 0" class="investors-section">
        <h2>👥 Инвесторы ({{ coin.investors.length }})</h2>
        <ul class="investors-list">
          <li v-for="inv in coin.investors" :key="inv.investor_href || inv.investor_name">
            <strong>{{ inv.investor_name }}</strong>
            <span v-if="inv.investor_role">({{ inv.investor_role }})</span>
            <span v-if="inv.investor_tier">, Tier {{ inv.investor_tier }}</span>
            <span v-if="inv.investor_type">, {{ inv.investor_type }}</span>
            <span v-if="inv.investor_href">
              <a :href="inv.investor_href" target="_blank" class="link">🔗 профиль</a>
            </span>
          </li>
        </ul>
      </div>

      <!-- Launchpad-платформы -->
      <div v-if="coin.launchpad && coin.launchpad.length > 0" class="launchpad-section">
        <h2>🚀 Launchpad-платформы</h2>
        <ul class="launchpad-list">
          <li v-for="lp in coin.launchpad" :key="lp">
            {{ lp }}
          </li>
        </ul>
      </div>

      <p v-else-if="loading">Загрузка данных...</p>
      <p v-else class="no-data">Нет дополнительных данных</p>
    </div>

    <div v-else class="not-found">
      <h2>Монета не найдена</h2>
      <p>Проверьте URL или вернитесь к списку.</p>
    </div>
  </div>
</template>

<script>
import api from '@/services/api';

export default {
  name: 'CoinDetail',
  data() {
    return {
      coin: null,
      tokenomics: null,
      loading: true
    };
  },
  async created() {
    await this.loadCoin();
    await this.loadTokenomics();
  },
  methods: {
    async loadCoin() {
      try {
        const response = await api.get(`/coins/${this.$route.params.id}/`);
        this.coin = response.data;
      } catch (error) {
        console.error('Ошибка загрузки монеты:', error);
      } finally {
        this.loading = false;
      }
    },
    async loadTokenomics() {
      if (!this.coin?.project_name) return;
      try {
        const response = await api.get(`/tokenomics-detailed/`);
        const data = Array.isArray(response.data) ? response.data : [];
        this.tokenomics = data.find(t => t.project_name === this.coin.project_name) || null;
      } catch (error) {
        console.error('Ошибка загрузки токеномики:', error);
      }
    },
    formatDate(dateStr) {
      if (!dateStr) return 'TBA';
      const date = new Date(dateStr);
      return date.toLocaleDateString('ru-RU', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
      });
    }
  },
  watch: {
    '$route': 'loadCoin'
  }
};
</script>

<style scoped>
.coin-detail {
  max-width: 1000px;
  margin: 0 auto;
  padding: 20px;
}

.back-button {
  display: inline-block;
  margin-bottom: 20px;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
}

.back-button:hover {
  background: #0056b3;
}

.coin-content h1 {
  margin-bottom: 20px;
  color: #333;
}

.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 30px;
}

.info-item {
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
  font-size: 14px;
}

.info-item strong {
  color: #495057;
  margin-bottom: 4px;
}

.tokenomics-table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
}

.tokenomics-table td {
  padding: 10px;
  border-bottom: 1px solid #dee2e6;
}

.tokenomics-table td:first-child {
  width: 30%;
  font-weight: bold;
}

.distribution ul {
  list-style: none;
  padding: 0;
}

.distribution li {
  margin: 8px 0;
  padding: 6px 10px;
  background: #f8f9fa;
  border-radius: 6px;
}

.investors-list, .launchpad-list {
  list-style: none;
  padding: 0;
}

.investors-list li, .launchpad-list li {
  margin: 8px 0;
  padding: 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 14px;
}

.link {
  color: #007bff;
  text-decoration: none;
  margin-left: 8px;
}

.link:hover {
  text-decoration: underline;
}

.not-found {
  text-align: center;
  color: #6c757d;
  margin-top: 50px;
}

.no-data {
  color: #6c757d;
  font-style: italic;
}

.complete { color: #28a745; }
.partial { color: #ffc107; }
.minimal { color: #dc3545; }
</style>