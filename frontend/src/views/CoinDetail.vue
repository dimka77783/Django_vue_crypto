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
        <div class="tokenomics-grid">
          <!-- Основные значения -->
          <div v-if="tokenomics.initial_values" class="tokenomics-values">
            <p><strong>Рыночная капитализация:</strong> {{ tokenomics.initial_values['Market cap'] }}</p>
            <p><strong>FDV:</strong> {{ tokenomics.initial_values['FDV'] }}</p>
            <p><strong>Общий объём:</strong> {{ tokenomics.token_allocation?.['Total supply'] }}</p>
            <p><strong>В обращении:</strong> {{ tokenomics.initial_values['Circulating'] }}</p>
          </div>

          <!-- Распределение -->
          <div v-if="tokenomics.distribution" class="distribution">
            <h3>🎯 Распределение токенов</h3>
            <ul>
              <li v-for="(value, key) in tokenomics.distribution" :key="key">
                {{ key }}: <strong>{{ value }}</strong>
              </li>
            </ul>
          </div>
        </div>
      </div>

      <p v-else class="no-data">Исторические данные не найдены</p>

      <!-- Инвесторы -->
      <div v-if="coin.investors && coin.investors.length > 0" class="investors-section">
        <h2>👥 Инвесторы ({{ coin.investors.length }})</h2>
        <ul class="investors-list">
          <li v-for="inv in coin.investors" :key="inv.investor_name">
            <strong>{{ inv.investor_name }}</strong>
            <span v-if="inv.investor_role"> ({{ inv.investor_role }})</span>
            <span v-if="inv.investor_tier">, Tier {{ inv.investor_tier }}</span>
            <span v-if="inv.investor_type">, {{ inv.investor_type }}</span>
            <span v-if="inv.investor_stage">, Stage: {{ inv.investor_stage }}</span>
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
      loading: true
    }
  },
  computed: {
    // Вычисляемое поле: токеномика
    tokenomics() {
      return this.coin?.tokenomics || null
    }
  },
  async created() {
    await this.loadCoin()
  },
  methods: {
    async loadCoin() {
      try {
        const id = this.$route.params.id
        const response = await api.get(`/coins/${id}/`)
        this.coin = response.data

        // Дополнительно: парсим tokenomics, если он пришёл как строка
        if (this.coin.tokenomics && typeof this.coin.tokenomics === 'string') {
          try {
            this.coin.tokenomics = JSON.parse(this.coin.tokenomics)
          } catch (e) {
            console.error('Ошибка парсинга tokenomics:', e)
            this.coin.tokenomics = null
          }
        }
      } catch (error) {
        console.error('Ошибка загрузки монеты:', error)
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
  },
  watch: {
    // Если ID в URL изменился — перезагружаем монету
    '$route.params.id': 'loadCoin'
  }
}
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

.tokenomics-section {
  margin-bottom: 30px;
}

.tokenomics-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
}

.tokenomics-values p {
  margin: 8px 0;
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
  font-size: 14px;
}

.investors-section, .launchpad-section {
  margin-top: 20px;
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
  margin-top: 20px;
}
</style>