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
    <div v-if="loading" class="loading-state">
      <el-skeleton :rows="3" animated />
    </div>
    <div v-else-if="error" class="error-state">
      <el-alert type="error" :title="error" :closable="false" />
    </div>
    <div v-else class="price-info">
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
import { ref, computed, onUnmounted } from 'vue';
import type { MarketData } from '@/types/trading';
import { formatPrice, formatQuantity } from '@/utils/formatters';

const symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT', 'ADA-USDT'];
const symbol = ref('BTC-USDT');
const marketData = ref<MarketData>({});
const loading = ref(true);
const error = ref<string | null>(null);
let prevPrice = ref<number | undefined>(undefined);
let isInitialLoad = ref(true);

const priceChangeClass = computed(() => {
  if (!prevPrice.value || !marketData.value.last_price) return '';
  return marketData.value.last_price > prevPrice.value ? 'price-up' : 'price-down';
});

const handleSymbolChange = (newSymbol: string) => {
  symbol.value = newSymbol;
  fetchMarketData();
};

const fetchMarketData = async () => {
  if (isInitialLoad.value) {
    loading.value = true;
  }
  error.value = null;
  
  try {
    const response = await fetch(`/api/market/price/${symbol.value}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    
    if (result.code === "0" && result.data && result.data.length > 0) {
      prevPrice.value = marketData.value.last_price ? Number(marketData.value.last_price) : undefined;
      const data = result.data[0];
      marketData.value = {
        last_price: Number(data.last_price || data.last || 0),
        high_24h: Number(data.high_24h || 0),
        low_24h: Number(data.low_24h || 0),
        volume_24h: Number(data.volume_24h || 0)
      };
    } else {
      error.value = result.msg || '获取数据失败';
    }
  } catch (err) {
    console.error('获取市场数据失败:', err);
    error.value = '获取市场数据失败';
  } finally {
    if (isInitialLoad.value) {
      loading.value = false;
      isInitialLoad.value = false;
    }
  }
};

// 初始加载和定时更新
fetchMarketData();
const timer = setInterval(fetchMarketData, 5000);

// 组件卸载时清理定时器
onUnmounted(() => {
  clearInterval(timer);
});
</script>

<style scoped>
.market-data {
  height: 100%;
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
}

.card-header {
  display: flex;
  align-items: center;
  background-color: var(--el-bg-color);
}

.price-info {
  padding: 16px 0;
  background-color: var(--el-bg-color);
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
  color: var(--el-text-color-primary);
}

.price-up {
  color: #67c23a;
}

.price-down {
  color: #f56c6c;
}

.loading-state {
  padding: 16px 0;
  background-color: var(--el-bg-color);
}

.error-state {
  padding: 16px 0;
  background-color: var(--el-bg-color);
}
</style> 