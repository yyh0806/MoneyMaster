<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'
import {
  NConfigProvider,
  NLayout,
  NLayoutHeader,
  NLayoutContent,
  NSpace,
  NH2,
  NSelect,
  NGrid,
  NGridItem,
  NCard,
  NStatistic
} from 'naive-ui'

// 状态定义
const selectedSymbol = ref('BTC-USDT')
const symbols = [
  { label: 'BTC/USDT', value: 'BTC-USDT' },
  { label: 'ETH/USDT', value: 'ETH-USDT' }
]
const marketPrice = ref<any>(null)
const accountBalance = ref<any>(null)
const chartRef = ref<HTMLElement>()
let chart: echarts.ECharts | null = null

// API调用函数
async function fetchMarketPrice() {
  try {
    const response = await fetch(`http://localhost:8000/api/market/price/${selectedSymbol.value}`)
    marketPrice.value = await response.json()
  } catch (error) {
    console.error('获取市场价格失败:', error)
  }
}

async function fetchAccountBalance() {
  try {
    const response = await fetch('http://localhost:8000/api/account/balance')
    accountBalance.value = await response.json()
  } catch (error) {
    console.error('获取账户余额失败:', error)
  }
}

async function fetchKlineData() {
  try {
    const response = await fetch(`http://localhost:8000/api/market/kline/${selectedSymbol.value}?interval=1m`)
    const data = await response.json()
    updateChart(data)
  } catch (error) {
    console.error('获取K线数据失败:', error)
  }
}

// 图表更新函数
function initChart() {
  if (chartRef.value) {
    chart = echarts.init(chartRef.value)
  }
}

function updateChart(data: any) {
  if (!chart) return
  
  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'time',
      boundaryGap: false
    },
    yAxis: {
      type: 'value',
      scale: true
    },
    series: [{
      name: selectedSymbol.value,
      type: 'line',
      data: data.data?.map((item: any[]) => [
        new Date(Number(item[0])),
        Number(item[4])  // 收盘价
      ]) || [],
      animation: false
    }]
  }
  
  chart.setOption(option)
}

// 生命周期钩子
onMounted(() => {
  initChart()
  fetchMarketPrice()
  fetchAccountBalance()
  fetchKlineData()
  
  // 设置定时刷新
  setInterval(() => {
    fetchMarketPrice()
    fetchKlineData()
  }, 5000)  // 每5秒更新一次
})

// 监听交易对变化
watch(selectedSymbol, () => {
  fetchMarketPrice()
  fetchKlineData()
})
</script>

<template>
  <n-config-provider>
    <n-layout>
      <n-layout-header bordered>
        <n-space justify="space-between" align="center" class="header">
          <n-h2>MoneyMaster</n-h2>
          <n-space>
            <n-select
              v-model:value="selectedSymbol"
              :options="symbols"
              placeholder="选择交易对"
            />
          </n-space>
        </n-space>
      </n-layout-header>
      
      <n-layout-content content-style="padding: 24px;">
        <n-grid :cols="2" :x-gap="24" :y-gap="24">
          <!-- 市场价格卡片 -->
          <n-grid-item>
            <n-card title="市场价格">
              <n-statistic label="当前价格">
                {{ marketPrice?.data?.[0]?.last || '-' }} USDT
              </n-statistic>
              <n-statistic label="24h高">
                {{ marketPrice?.data?.[0]?.high24h || '-' }} USDT
              </n-statistic>
              <n-statistic label="24h低">
                {{ marketPrice?.data?.[0]?.low24h || '-' }} USDT
              </n-statistic>
            </n-card>
          </n-grid-item>
          
          <!-- 账户余额卡片 -->
          <n-grid-item>
            <n-card title="账户余额">
              <n-statistic label="总资产">
                {{ accountBalance?.data?.[0]?.totalEq || '-' }} USD
              </n-statistic>
            </n-card>
          </n-grid-item>
          
          <!-- K线图卡片 -->
          <n-grid-item span="2">
            <n-card title="价格走势">
              <div ref="chartRef" style="width: 100%; height: 400px;"></div>
            </n-card>
          </n-grid-item>
        </n-grid>
      </n-layout-content>
    </n-layout>
  </n-config-provider>
</template>

<style scoped>
.logo {
  height: 6em;
  padding: 1.5em;
  will-change: filter;
  transition: filter 300ms;
}
.logo:hover {
  filter: drop-shadow(0 0 2em #646cffaa);
}
.logo.vue:hover {
  filter: drop-shadow(0 0 2em #42b883aa);
}
.header {
  padding: 16px 24px;
}
</style>
