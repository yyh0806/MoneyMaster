<template>
  <el-card class="market-data">
    <template #header>
      <div class="card-header">
        <span>市场数据</span>
        <el-select v-model="symbol" size="small" @change="handleSymbolChange" style="margin-left: 10px; width: 120px;">
          <el-option v-for="option in symbols" :key="option" :label="option" :value="option" />
        </el-select>
      </div>
    </template>
    <div class="price-info">
      <div class="latest-price">
        <span class="label">最新价格:</span>
        <span class="value" :class="priceChangeClass">{{ formatPrice(marketData.last_price) }}</span>
      </div>
      <div class="price-details">
        <div class="detail-item">
          <span class="label">24h高:</span>
          <span class="value">{{ formatPrice(marketData.high_24h) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">24h低:</span>
          <span class="value">{{ formatPrice(marketData.low_24h) }}</span>
        </div>
        <div class="detail-item">
          <span class="label">24h成交量:</span>
          <span class="value">{{ formatQuantity(marketData.volume_24h) }}</span>
        </div>
      </div>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import type { MarketData } from '@/types/trading';
import { formatPrice, formatQuantity } from '@/utils/formatters';

const symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT', 'ADA-USDT'];
const symbol = ref('BTC-USDT');
const marketData = ref<MarketData>({});
let prevPrice = ref<number | undefined>(undefined);

const priceChangeClass = computed(() => {
  if (!prevPrice.value || !marketData.value.last_price) return '';
  return marketData.value.last_price > prevPrice.value ? 'price-up' : 'price-down';
});

const handleSymbolChange = (newSymbol: string) => {
  symbol.value = newSymbol;
  fetchMarketData();
};

const fetchMarketData = async () => {
  try {
    const response = await fetch(`/api/market/data/${symbol.value}`);
    const data = await response.json();
    prevPrice.value = marketData.value.last_price;
    marketData.value = data;
  } catch (error) {
    console.error('获取市场数据失败:', error);
  }
};

// 初始加载和定时更新
fetchMarketData();
setInterval(fetchMarketData, 5000);
</script>

<style scoped>
.market-data {
  height: 100%;
}

.card-header {
  display: flex;
  align-items: center;
}

.price-info {
  padding: 16px 0;
}

.latest-price {
  font-size: 1.2em;
  margin-bottom: 16px;
}

.price-details {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.detail-item {
  display: flex;
  justify-content: space-between;
}

.label {
  color: var(--el-text-color-secondary);
}

.value {
  font-weight: bold;
}

.price-up {
  color: #67c23a;
}

.price-down {
  color: #f56c6c;
}
</style> 