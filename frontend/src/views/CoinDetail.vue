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

        <!-- Распределение -->
        <div v-if="tokenomics.distribution" class="tokenomics-distribution">
          <h3>🎯 Распределение токенов</h3>
          <ul>
            <li v-for="(value, key) in tokenomics.distribution" :key="key">
              <strong>{{ key }}:</strong> {{ value }}
            </li>
          </ul>
        </div>

        <!-- Начальные значения -->
        <div v-if="tokenomics.initial_values" class="tokenomics-initial">
          <h3>📈 Начальные значения</h3>
          <ul>
            <li v-for="(value, key) in tokenomics.initial_values" :key="key">
              <strong>{{ key }}:</strong> {{ value }}
            </li>
          </ul>
        </div>

        <!-- Аллокация токенов -->
        <div v-if="tokenomics.token_allocation" class="tokenomics-allocation">
          <h3>🧩 Аллокация токенов</h3>
          <ul>
            <li v-for="(value, key) in tokenomics.token_allocation" :key="key">
              <strong>{{ key }}:</strong> {{ value }}
            </li>
          </ul>
        </div>

        <!-- Источник -->
        <div class="tokenomics-meta">
          <small>Источник: CryptoRank | Обновлено: {{ formatDate(tokenomics.scraped_at) }}</small>
        </div>
      </div>

      <div v-else-if="loadingTokenomics" class="loading">
        <p>Загрузка токеномики...</p>
      </div>

      <div v-else class="no-data">
        <p>❌ Данные токеномики не найдены</p>
      </div>

      <!-- Инвесторы -->
      <div v-if="coin.investors && coin.investors.length > 0" class="investors-section">
        <h2>👥 Инвесторы ({{ coin.investors.length }})</h2>
        <ul class="investors-list">
          <li v-for="inv in coin.investors" :key="inv.investor_name || inv.investor_href">
            <strong>{{ inv.investor_name }}</strong>
            <span v-if="inv.investor_role"> ({{ inv.investor_role }})</span>
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

      <!-- Исторические данные (OHLC) -->
      <div v-if="ohlcData.length > 0" class="ohlc-section">
        <h2>📈 Исторические данные (OHLC)</h2>
        <table class="ohlc-table">
          <thead>
            <tr>
              <th>Дата</th>
              <th>Open</th>
              <th>High</th>
              <th>Low</th>
              <th>Close</th>
              <th>Volume</th>
              <th>Market Cap</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="row in ohlcData" :key="row.date">
              <td>{{ formatDate(row.date) }}</td>
              <td>{{ row.open_price }}</td>
              <td>{{ row.high_price }}</td>
              <td>{{ row.low_price }}</td>
              <td>{{ row.close_price }}</td>
              <td>{{ row.volume_usd }}</td>
              <td>{{ row.market_cap }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <div v-else-if="loadingOhlc" class="loading">
        <p>Загрузка исторических данных...</p>
      </div>

      <div v-else class="no-data">
        <p>❌ Исторические данные не найдены</p>
      </div>
    </div>

    <div v-else-if="loadingCoin" class="loading">
      <p>Загрузка данных монеты...</p>
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
  name: 'CoinDetail',
  data() {
    return {
      coin: null,
      tokenomics: null,
      ohlcData: [],
      loadingCoin: true,
      loadingTokenomics: true,
      loadingOhlc: true
    }
  },
  async created() {
    await this.loadCoin()
    await this.loadTokenomics()
    await this.loadOhlcData()
  },
  methods: {
    async loadCoin() {
      this.loadingCoin = true
      try {
        const response = await api.get(`/coins/${this.$route.params.id}/`)
        this.coin = response.data
      } catch (error) {
        console.error('Ошибка загрузки монеты:', error)
      } finally {
        this.loadingCoin = false
      }
    },
    async loadTokenomics() {
      this.loadingTokenomics = true
      if (!this.coin?.project_name) {
        this.loadingTokenomics = false
        return
      }
      try {
        const response = await api.get('/tokenomics-detailed/')
        const data = Array.isArray(response.data) ? response.data : []
        this.tokenomics = data.find(t => t.project_name === this.coin.project_name) || null
      } catch (error) {
        console.error('Ошибка загрузки токеномики:', error)
      } finally {
        this.loadingTokenomics = false
      }
    },
    async loadOhlcData() {
      this.loadingOhlc = true
      const symbol = this.coin?.project_symbol?.toLowerCase()
      if (!symbol) {
        this.loadingOhlc = false
        return
      }
      try {
        const response = await api.get(`/ohlc/${symbol}/`)
        this.ohlcData = response.data
      } catch (error) {
        console.error('Ошибка загрузки OHLC:', error)
      } finally {
        this.loadingOhlc = false
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
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
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
  font-size: 1rem;
}

.back-button:hover {
  background: #0056b3;
}

h1 {
  color: #333;
  margin-bottom: 20px;
  font-size: 2rem;
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
  font-size: 14px;
  border: 1px solid #e9ecef;
}

.info-item strong {
  color: #495057;
  margin-bottom: 4px;
  display: block;
}

.tokenomics-section {
  margin: 30px 0;
}

.tokenomics-section h3 {
  margin-top: 15px;
  color: #495057;
}

.tokenomics-section ul {
  list-style: none;
  padding: 0;
}

.tokenomics-section li {
  margin: 8px 0;
  padding: 6px 10px;
  background: #f8f9fa;
  border-radius: 6px;
  font-size: 14px;
  border: 1px solid #e9ecef;
}

.tokenomics-meta {
  margin-top: 20px;
  font-style: italic;
  color: #6c757d;
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
  border: 1px solid #e9ecef;
}

.link {
  color: #007bff;
  text-decoration: none;
  margin-left: 8px;
}

.link:hover {
  text-decoration: underline;
}

.ohlc-section {
  margin: 30px 0;
}

.ohlc-table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-size: 14px;
}

.ohlc-table thead {
  background: #f8f9fa;
  font-weight: bold;
}

.ohlc-table th,
.ohlc-table td {
  padding: 10px;
  border: 1px solid #dee2e6;
  text-align: left;
}

.ohlc-table th {
  background-color: #e9ecef;
}

.loading, .no-data, .not-found {
  text-align: center;
  margin: 40px 0;
  color: #6c757d;
}

.loading p, .no-data p, .not-found p {
  font-size: 1.1em;
}

.not-found h2 {
  color: #dc3545;
}
</style>