<!-- frontend/src/views/CoinDetail.vue -->
<template>
  <div class="coin-detail">
    <button @click="$router.back()" class="back-button">← Назад</button>

    <div v-if="coin" class="coin-content">
      <h1>{{ coin.project_name }} ({{ coin.project_symbol }})</h1>

      <!-- Основная информация -->
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
          <tr v-for="(value, key) in tokenomics.token_allocation" :key="key">
            <td><strong>{{ key }}:</strong></td>
            <td>{{ value }}</td>
          </tr>
        </table>
      </div>

      <!-- Инвесторы -->
      <div v-if="coin.investors && coin.investors.length > 0" class="investors-section">
        <h2>👥 Инвесторы ({{ coin.investors.length }})</h2>
        <ul class="investors-list">
          <li v-for="inv in coin.investors" :key="inv.investor_name">
            <strong>{{ inv.investor_name }}</strong>
            <span v-if="inv.investor_role">({{ inv.investor_role }})</span>
            <span v-if="inv.investor_tier">, Tier {{ inv.investor_tier }}</span>
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

      <!-- Исторические данные -->
      <div v-if="ohlcData.length > 0" class="ohlc-section">
        <h2>📈 Исторические данные (OHLC)</h2>
        <table class="ohlc-table">
          <tr>
            <th>Дата</th>
            <th>Open</th>
            <th>High</th>
            <th>Low</th>
            <th>Close</th>
            <th>Volume</th>
          </tr>
          <tr v-for="row in ohlcData" :key="row.date">
            <td>{{ formatDate(row.date) }}</td>
            <td>{{ row.open_price }}</td>
            <td>{{ row.high_price }}</td>
            <td>{{ row.low_price }}</td>
            <td>{{ row.close_price }}</td>
            <td>{{ row.volume_usd }}</td>
          </tr>
        </table>
      </div>

      <p v-else-if="loading" class="loading">Загрузка данных...</p>
      <p v-else class="no-data">Нет дополнительных данных</p>
    </div>

    <div v-else class="not-found">
      <h2>Монета не найдена</h2>
      <p>Проверьте URL или вернитесь к списку.</p>
    </div>
  </div>
</template>

<script>
import api from '@/services/api'

export default {
  data() {
    return {
      coin: null,
      tokenomics: null,
      ohlcData: [],
      loading: true
    }
  },
  async created() {
    await this.loadCoin()
    await this.loadTokenomics()
    await this.loadOhlcData()
  },
  methods: {
    async loadCoin() {
      try {
        const response = await api.get(`/coins/${this.$route.params.id}/`)
        this.coin = response.data
      } catch (error) {
        console.error('Ошибка загрузки монеты:', error)
      }
    },
    async loadTokenomics() {
      if (!this.coin?.project_name) return
      try {
        const response = await api.get(`/tokenomics-detailed/`)
        const data = Array.isArray(response.data) ? response.data : []
        this.tokenomics = data.find(t => t.project_name === this.coin.project_name) || null
      } catch (error) {
        console.error('Ошибка загрузки токеномики:', error)
      }
    },
    async loadOhlcData() {
      const symbol = this.coin?.project_symbol?.toLowerCase()
      if (!symbol) return
      try {
        const response = await api.get(`/ohlc/${symbol}/`)
        this.ohlcData = response.data
      } catch (error) {
        console.error('Ошибка загрузки OHLC:', error)
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
  },
  watch: {
    '$route': 'loadCoin'
  }
}
</script>

<style scoped>
.coin-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}
.back-button {
  display: inline-block;
  padding: 8px 16px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  text-decoration: none;
  margin-bottom: 20px;
}
.back-button:hover {
  background: #0056b3;
}
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 30px;
}
.info-item {
  padding: 12px;
  background: #f8f9fa;
  border-radius: 8px;
}
.tokenomics-table, .ohlc-table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
}
.tokenomics-table td, .ohlc-table td {
  padding: 10px;
  border-bottom: 1px solid #dee2e6;
}
.ohlc-table th {
  background: #f8f9fa;
  padding: 10px;
  text-align: left;
}
</style>