<template>
  <el-card class="market-chart">
    <template #header>
      <div class="card-header">
        <div class="left-controls">
          <span>市场走势图</span>
          <el-select v-model="symbol" size="small" @change="handleSymbolChange" style="margin-left: 10px; width: 120px;">
            <el-option v-for="option in symbols" :key="option" :label="option" :value="option" />
          </el-select>
        </div>
        <div class="chart-controls">
          <el-select v-model="selectedPeriod" size="small" @change="handlePeriodChange">
            <el-option v-for="period in periods" :key="period.value" :label="period.label" :value="period.value" />
          </el-select>
        </div>
      </div>
    </template>
    <div ref="chartContainer" style="height: 400px;"></div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import type { Period } from '../../types/trading';
import * as echarts from 'echarts';

const chartContainer = ref<HTMLElement>();
let chart: echarts.ECharts | null = null;

const symbols = ['BTC-USDT', 'ETH-USDT', 'BNB-USDT', 'XRP-USDT', 'ADA-USDT'];
const symbol = ref('BTC-USDT');

const periods = [
  { label: '1分钟', value: '1m' },
  { label: '5分钟', value: '5m' },
  { label: '15分钟', value: '15m' },
  { label: '1小时', value: '1H' },
  { label: '4小时', value: '4H' },
  { label: '1天', value: '1D' }
];
const selectedPeriod = ref<Period>('1m');

const handleSymbolChange = (newSymbol: string) => {
  symbol.value = newSymbol;
  fetchKlineData();
};

const handlePeriodChange = (period: Period) => {
  selectedPeriod.value = period;
  fetchKlineData();
};

const initChart = () => {
  if (!chartContainer.value) return;
  
  chart = echarts.init(chartContainer.value);
  const option = {
    grid: {
      left: '10%',
      right: '10%',
      bottom: '15%'
    },
    xAxis: {
      type: 'category',
      data: []
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      }
    },
    series: [{
      type: 'candlestick',
      data: []
    }]
  };
  
  chart.setOption(option);
};

const updateChart = (data: any[]) => {
  if (!chart || !Array.isArray(data)) return;
  
  const times = data.map(item => {
    if (Array.isArray(item) && item.length > 0) {
      return new Date(Number(item[0])).toLocaleTimeString();
    }
    return '';
  }).filter(time => time !== '');
  
  const values = data.map(item => {
    if (Array.isArray(item) && item.length >= 5) {
      return [
        Number(item[1] || 0), // open
        Number(item[4] || 0), // close
        Number(item[3] || 0), // low
        Number(item[2] || 0)  // high
      ];
    }
    return [0, 0, 0, 0];
  }).filter(value => value.some(v => v !== 0));
  
  if (times.length === 0 || values.length === 0) {
    console.warn('No valid K-line data available');
    return;
  }

  chart.setOption({
    xAxis: {
      data: times
    },
    series: [{
      data: values
    }]
  });
};

const fetchKlineData = async () => {
  try {
    const response = await fetch(`/api/market/kline/${symbol.value}/${selectedPeriod.value}`);
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    if (result.code === "0" && Array.isArray(result.data)) {
      updateChart(result.data);
    } else {
      console.error('获取K线数据失败:', result.msg);
    }
  } catch (error) {
    console.error('获取K线数据失败:', error);
  }
};

onMounted(() => {
  initChart();
  fetchKlineData();
  window.addEventListener('resize', () => chart?.resize());
});

onUnmounted(() => {
  chart?.dispose();
  window.removeEventListener('resize', () => chart?.resize());
});
</script>

<style scoped>
.market-chart {
  height: 100%;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-controls {
  display: flex;
  align-items: center;
}

.chart-controls {
  display: flex;
  gap: 8px;
}
</style> 