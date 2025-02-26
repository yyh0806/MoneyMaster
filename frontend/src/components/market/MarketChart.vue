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
    animation: false,
    legend: {
      bottom: 10,
      left: 'center',
      data: ['K线', '成交量']
    },
    axisPointer: {
      link: {xAxisIndex: 'all'},
      label: {
        backgroundColor: '#777'
      }
    },
    grid: [{
      left: '10%',
      right: '8%',
      height: '60%',
      top: '5%'
    }, {
      left: '10%',
      right: '8%',
      top: '70%',
      height: '20%'
    }],
    xAxis: [{
      type: 'category',
      data: [],
      scale: true,
      boundaryGap: true,
      axisLine: {onZero: false},
      splitLine: {show: false},
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        show: false
      }
    }, {
      type: 'category',
      gridIndex: 1,
      data: [],
      scale: true,
      boundaryGap: true,
      axisLine: {onZero: false},
      axisTick: {show: false},
      splitLine: {show: false},
      min: 'dataMin',
      max: 'dataMax'
    }],
    yAxis: [{
      scale: true,
      splitArea: {
        show: true
      }
    }, {
      scale: true,
      gridIndex: 1,
      splitNumber: 2,
      axisLabel: {
        show: true,
        formatter: function (value: number) {
          return Math.round(value);
        }
      },
      axisLine: {show: false},
      axisTick: {show: false},
      splitLine: {show: false}
    }],
    dataZoom: [
      {
        type: 'inside',
        xAxisIndex: [0, 1],
        start: 0,
        end: 100
      },
      {
        show: true,
        xAxisIndex: [0, 1],
        type: 'slider',
        bottom: '0%',
        start: 0,
        end: 100
      }
    ],
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: 'rgba(255, 255, 255, 0.8)',
      position: function (pos: number[], params: any, el: any, elRect: any, size: any) {
        const obj = {top: 10};
        obj[['left', 'right'][+(pos[0] < size.viewSize[0] / 2)]] = 30;
        return obj;
      }
    },
    series: [{
      name: 'K线',
      type: 'candlestick',
      data: [],
      itemStyle: {
        color: '#cc0000',
        color0: '#00b33c',
        borderColor: '#cc0000',
        borderColor0: '#00b33c'
      }
    }, {
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: [],
      itemStyle: {
        color: '#7fbe9e'
      }
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

  const volumes = data.map(item => {
    if (Array.isArray(item) && item.length >= 6) {
      const volume = Number(item[5] || 0);
      const open = Number(item[1] || 0);
      const close = Number(item[4] || 0);
      return {
        value: volume,
        itemStyle: {
          color: close >= open ? '#00b33c' : '#cc0000'
        }
      };
    }
    return { value: 0, itemStyle: { color: '#00b33c' } };
  }).filter(item => item.value !== 0);
  
  if (times.length === 0 || values.length === 0) {
    console.warn('No valid K-line data available');
    return;
  }

  chart.setOption({
    xAxis: [{
      data: times
    }, {
      data: times
    }],
    series: [{
      data: values
    }, {
      data: volumes
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