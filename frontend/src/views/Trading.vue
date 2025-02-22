<template>
  <div class="trading-view">
    <el-row :gutter="20">
      <!-- 市场数据卡片 -->
      <el-col :span="8">
        <el-card class="market-data">
          <template #header>
            <div class="card-header">
              <span>市场数据 ({{ symbol }})</span>
            </div>
          </template>
          <div class="price-info">
            <div class="price-item">
              <span class="label">最新价格:</span>
              <span class="value" :class="priceChangeClass">{{ formatPrice(marketData.last) }}</span>
            </div>
            <div class="price-item">
              <span class="label">24h高:</span>
              <span class="value">{{ formatPrice(marketData.high24h) }}</span>
            </div>
            <div class="price-item">
              <span class="label">24h低:</span>
              <span class="value">{{ formatPrice(marketData.low24h) }}</span>
            </div>
            <div class="price-item">
              <span class="label">24h成交量:</span>
              <span class="value">{{ formatVolume(marketData.vol24h) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 策略状态卡片 -->
      <el-col :span="8">
        <el-card class="strategy-status">
          <template #header>
            <div class="card-header">
              <span>策略状态</span>
              <div class="strategy-controls">
                <el-button
                  :type="getStrategyButtonType"
                  size="small"
                  @click="handleStrategyAction"
                  :loading="isLoading"
                >
                  {{ getStrategyButtonText }}
                </el-button>
                <el-button
                  v-if="canPause"
                  type="warning"
                  size="small"
                  @click="handlePause"
                  :loading="isLoading"
                >
                  暂停
                </el-button>
              </div>
            </div>
          </template>
          <div class="strategy-info">
            <div class="info-item">
              <span class="label">状态:</span>
              <el-tag :type="getStatusTagType">
                {{ getStatusText }}
              </el-tag>
            </div>
            <div class="info-item" v-if="strategyState.last_error">
              <span class="label">错误信息:</span>
              <span class="value text-danger">{{ strategyState.last_error }}</span>
            </div>
            <div class="info-item">
              <span class="label">最后运行时间:</span>
              <span class="value">{{ formatLastRunTime }}</span>
            </div>
            <div class="info-item">
              <span class="label">当前持仓:</span>
              <span class="value">{{ formatQuantity(strategyState.position) }}</span>
            </div>
            <div class="info-item">
              <span class="label">持仓均价:</span>
              <span class="value">{{ formatPrice(strategyState.avg_entry_price) }}</span>
            </div>
            <div class="info-item">
              <span class="label">未实现盈亏:</span>
              <el-tooltip
                content="未实现盈亏 = (当前市价 - 持仓均价) × 持仓数量。这是当前持仓的预计盈亏，尚未通过交易实现。"
                placement="top"
              >
                <span class="value" :class="pnlClass(strategyState.unrealized_pnl)">
                  {{ formatPnL(strategyState.unrealized_pnl) }}
                </span>
              </el-tooltip>
            </div>
            <div class="info-item">
              <span class="label">总盈亏:</span>
              <el-tooltip
                content="总盈亏 = 已实现盈亏 + 未实现盈亏。绿色表示盈利，红色表示亏损。"
                placement="top"
              >
                <span class="value" :class="pnlClass(strategyState.total_pnl)">
                  {{ formatPnL(strategyState.total_pnl) }}
                </span>
              </el-tooltip>
            </div>
            <div class="info-item">
              <span class="label">总手续费:</span>
              <el-tooltip
                content="所有交易产生的手续费总和"
                placement="top"
              >
                <span class="value">{{ formatPrice(strategyState.total_commission) }}</span>
              </el-tooltip>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 账户信息卡片 -->
      <el-col :span="8">
        <el-card class="account-info">
          <template #header>
            <div class="card-header">
              <span>账户信息</span>
            </div>
          </template>
          <div class="balance-info">
            <div v-for="(balance, currency) in accountBalances" :key="currency" class="balance-item">
              <span class="label">{{ currency }}:</span>
              <span class="value">{{ formatBalance(balance) }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 市场走势图卡片 -->
    <el-card class="market-chart">
      <template #header>
        <div class="card-header">
          <span>市场走势图</span>
          <div class="chart-controls">
            <el-select v-model="selectedPeriod" size="small" @change="fetchKlineData">
              <el-option label="1分钟" value="1m" />
              <el-option label="5分钟" value="5m" />
              <el-option label="15分钟" value="15m" />
              <el-option label="1小时" value="1H" />
              <el-option label="4小时" value="4H" />
              <el-option label="1天" value="1D" />
            </el-select>
          </div>
        </div>
      </template>
      <div ref="chartContainer" style="height: 400px;"></div>
    </el-card>

    <!-- 交易记录表格 -->
    <el-card class="trade-history">
      <template #header>
        <div class="card-header">
          <span>交易记录</span>
          <el-button
            type="danger"
            size="small"
            @click="handleClearHistory"
            :loading="isClearing"
          >
            清空历史
          </el-button>
        </div>
      </template>
      <div class="table-container">
        <el-table :data="tradeHistory" style="width: 100%" height="400">
          <el-table-column prop="trade_time" label="时间" min-width="200" align="center">
            <template #default="scope">
              {{ formatDateTime(scope.row.trade_time) }}
            </template>
          </el-table-column>
          <el-table-column prop="side" label="方向" width="100" align="center">
            <template #default="scope">
              <el-tag :type="scope.row.side === 'BUY' ? 'success' : 'danger'">
                {{ scope.row.side === 'BUY' ? '买入' : '卖出' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="price" label="价格" width="140" align="right">
            <template #default="scope">
              {{ formatPrice(scope.row.price) }}
            </template>
          </el-table-column>
          <el-table-column prop="quantity" label="数量" width="140" align="right">
            <template #default="scope">
              {{ formatQuantity(scope.row.quantity) }}
            </template>
          </el-table-column>
          <el-table-column prop="commission" label="手续费" width="120" align="right">
            <template #default="scope">
              {{ formatPrice(scope.row.commission) }}
            </template>
          </el-table-column>
          <el-table-column prop="realized_pnl" label="实现盈亏" width="140" align="right">
            <template #default="scope">
              <span :class="pnlClass(scope.row.realized_pnl)">
                {{ scope.row.realized_pnl === 0 ? '-' : formatPnL(scope.row.realized_pnl) }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import axios from 'axios'
import dayjs from 'dayjs'
import * as echarts from 'echarts'

// 使用相对路径
const API_BASE_URL = ''
const symbol = ref('BTC-USDT')
const marketData = ref({})
const strategyState = ref({})
const accountBalances = ref({})
const tradeHistory = ref([])
const isStrategyRunning = ref(false)
const selectedPeriod = ref('15m')
const chartContainer = ref(null)
let ws = null
let chart = null
const isLoading = ref(false)
const isClearing = ref(false)

// 格式化函数
const formatPrice = (price) => price ? `$${Number(price).toFixed(2)}` : '-'
const formatQuantity = (qty) => qty ? Number(qty).toFixed(6) : '-'
const formatVolume = (vol) => vol ? Number(vol).toFixed(2) : '-'
const formatPnL = (pnl) => pnl ? `$${Number(pnl).toFixed(2)}` : '-'
const formatBalance = (balance) => balance ? Number(balance).toFixed(6) : '-'
const formatDateTime = (datetime) => dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')

// 样式计算
const priceChangeClass = computed(() => {
  if (!marketData.value.last || !marketData.value.open24h) return ''
  return Number(marketData.value.last) >= Number(marketData.value.open24h) ? 'text-success' : 'text-danger'
})

const pnlClass = (pnl) => {
  if (!pnl) return ''
  return Number(pnl) >= 0 ? 'text-success' : 'text-danger'
}

// WebSocket连接
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/market/${symbol.value}`
  
  // 如果已经有连接，先关闭
  if (ws) {
    console.log('关闭现有WebSocket连接')
    ws.close()
    ws = null
  }
  
  console.log('建立新的WebSocket连接:', wsUrl)
  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    try {
      const data = JSON.parse(event.data)
      if (data.market?.data?.[0]) {
        marketData.value = data.market.data[0]
      }
      if (data.strategy) {
        console.log('收到策略状态更新:', data.strategy)
        strategyState.value = data.strategy
      }
    } catch (error) {
      console.error('处理WebSocket消息失败:', error)
    }
  }

  ws.onopen = () => {
    console.log('WebSocket连接已建立')
    // 连接成功后立即获取最新状态
    fetchStrategyState()
  }

  ws.onclose = (event) => {
    console.log('WebSocket连接已关闭，code:', event.code, '原因:', event.reason)
    ws = null
    // 如果不是主动关闭的连接，则尝试重连
    if (event.code !== 1000) {
      console.log('1秒后尝试重新连接...')
      setTimeout(connectWebSocket, 1000)
    }
  }

  ws.onerror = (error) => {
    console.error('WebSocket错误:', error)
  }
}

// 获取交易历史
const fetchTradeHistory = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/trades?symbol=${symbol.value}`)
    tradeHistory.value = response.data
  } catch (error) {
    ElMessage.error('获取交易历史失败')
  }
}

// 获取账户余额
const fetchAccountBalance = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/account/balance`)
    accountBalances.value = response.data
  } catch (error) {
    ElMessage.error('获取账户余额失败')
  }
}

// 策略状态相关
const getStrategyButtonType = computed(() => {
  switch (strategyState.value?.status) {
    case 'running':
      return 'danger'
    case 'error':
      return 'warning'
    default:
      return 'success'
  }
})

const getStrategyButtonText = computed(() => {
  switch (strategyState.value?.status) {
    case 'running':
      return '停止策略'
    case 'paused':
      return '继续运行'
    case 'error':
      return '重新启动'
    default:
      return '启动策略'
  }
})

const getStatusTagType = computed(() => {
  switch (strategyState.value?.status) {
    case 'running':
      return 'success'
    case 'stopped':
      return 'info'
    case 'paused':
      return 'warning'
    case 'error':
      return 'danger'
    default:
      return 'info'
  }
})

const getStatusText = computed(() => {
  switch (strategyState.value?.status) {
    case 'running':
      return '运行中'
    case 'stopped':
      return '已停止'
    case 'paused':
      return '已暂停'
    case 'error':
      return '错误'
    default:
      return '未知'
  }
})

const canPause = computed(() => {
  return strategyState.value?.status === 'running'
})

const formatLastRunTime = computed(() => {
  return strategyState.value?.last_run_time
    ? dayjs(strategyState.value.last_run_time).format('YYYY-MM-DD HH:mm:ss')
    : '-'
})

// 处理策略操作
const handleStrategyAction = async () => {
  try {
    isLoading.value = true
    const action = strategyState.value?.status === 'running' ? 'stop' : 'start'
    console.log(`执行策略${action}操作`)
    const response = await axios.post(`${API_BASE_URL}/api/strategy/${action}`)
    console.log('策略操作响应:', response.data)
    ElMessage.success(`策略${action === 'start' ? '启动' : '停止'}成功`)
    
    // 立即获取最新状态
    await fetchStrategyState()
    // 重新建立WebSocket连接以确保获取最新数据
    connectWebSocket()
  } catch (error) {
    console.error('策略操作失败:', error)
    ElMessage.error(error.response?.data?.detail || `策略操作失败`)
  } finally {
    isLoading.value = false
  }
}

const handlePause = async () => {
  try {
    isLoading.value = true
    console.log('执行策略暂停操作')
    const response = await axios.post(`${API_BASE_URL}/api/strategy/pause`)
    console.log('策略暂停响应:', response.data)
    ElMessage.success('策略已暂停')
    
    // 立即获取最新状态
    await fetchStrategyState()
  } catch (error) {
    console.error('策略暂停失败:', error)
    ElMessage.error(error.response?.data?.detail || '策略暂停失败')
  } finally {
    isLoading.value = false
  }
}

// 获取策略状态
const fetchStrategyState = async () => {
  try {
    const response = await axios.get(`${API_BASE_URL}/api/strategy/state?symbol=${symbol.value}`)
    if (response.data && response.data.length > 0) {
      console.log('获取到策略状态:', response.data[0])
      strategyState.value = response.data[0]
    }
  } catch (error) {
    console.error('获取策略状态失败:', error)
    ElMessage.error('获取策略状态失败')
  }
}

// 格式化K线数据
const formatKlineData = (data) => {
  return data.map(item => {
    // OKX的K线数据格式：[timestamp, open, high, low, close, volume, ...]
    console.log('原始数据项:', item)
    const [timestamp, open, high, low, close, volume] = item
    console.log('解析后的原始数据:', {
      timestamp: dayjs(parseInt(timestamp)).format('YYYY-MM-DD HH:mm:ss'),
      open: Number(open),
      high: Number(high),
      low: Number(low),
      close: Number(close),
      volume: Number(volume)
    })
    
    // 确保所有价格数据都是数值类型
    const formattedData = {
      time: dayjs(parseInt(timestamp)).format('YYYY-MM-DD HH:mm'),
      open: Number(open),
      high: Number(high),
      low: Number(low),
      close: Number(close),
      volume: Number(volume)
    }
    
    // 验证价格的合理性
    if (formattedData.high < formattedData.close || formattedData.high < formattedData.open) {
      console.error('数据异常: 最高价低于开盘价或收盘价', formattedData)
    }
    if (formattedData.low > formattedData.close || formattedData.low > formattedData.open) {
      console.error('数据异常: 最低价高于开盘价或收盘价', formattedData)
    }
    
    return formattedData
  })
}

// 初始化图表
const initChart = () => {
  if (chart) {
    chart.dispose()
  }
  chart = echarts.init(chartContainer.value)
}

// 更新图表
const updateChart = (klineData) => {
  if (!chart) {
    initChart()
  }

  // 记录传递给ECharts的数据
  const candlestickData = klineData.map(item => {
    const data = [
      item.open,    // 开盘价
      item.close,   // 收盘价
      item.low,     // 最低价
      item.high     // 最高价
    ]
    console.log('K线数据转换:', {
      from: item,
      to: data
    })
    return data
  })

  const option = {
    animation: false,
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      formatter: (params) => {
        const candleData = params.find(p => p.seriesName === '价格')
        const volumeData = params.find(p => p.seriesName === '成交量')
        
        if (volumeData && volumeData.componentIndex === 1) {
          return `
            时间: ${params[0].axisValue}<br/>
            成交量: ${Number(volumeData.value).toFixed(4)}
          `
        } else if (candleData) {
          console.log('Tooltip原始数据:', candleData.data)
          // OKX的K线数据格式：[timestamp, open, high, low, close, volume]
          const [timestamp, open, high, low, close] = candleData.data
          console.log('Tooltip解析后的数据:', {
            time: params[0].axisValue,
            open,
            high,
            low,
            close
          })
          return `
            时间: ${params[0].axisValue}<br/>
            开盘: $${Number(open).toFixed(2)}<br/>
            收盘: $${Number(close).toFixed(2)}<br/>
            最高: $${Number(high).toFixed(2)}<br/>
            最低: $${Number(low).toFixed(2)}
          `
        }
        return ''
      }
    },
    legend: {
      data: ['价格', '成交量'],
      top: 0
    },
    grid: [{
      left: '10%',
      right: '10%',
      height: '60%'
    }, {
      left: '10%',
      right: '10%',
      top: '75%',
      height: '15%'
    }],
    xAxis: [{
      type: 'category',
      data: klineData.map(item => item.time),
      scale: true,
      boundaryGap: false,
      axisLine: { onZero: false },
      splitLine: { show: false },
      min: 'dataMin',
      max: 'dataMax',
      axisLabel: {
        formatter: (value) => dayjs(value).format('HH:mm')
      }
    }, {
      type: 'category',
      gridIndex: 1,
      data: klineData.map(item => item.time),
      scale: true,
      boundaryGap: false,
      axisLine: { onZero: false },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    }],
    yAxis: [{
      scale: true,
      splitArea: { show: true },
      axisLabel: {
        formatter: (value) => `$${value}`
      }
    }, {
      scale: true,
      gridIndex: 1,
      splitNumber: 2,
      axisLabel: { show: false },
      axisLine: { show: false },
      axisTick: { show: false },
      splitLine: { show: false }
    }],
    dataZoom: [{
      type: 'inside',
      xAxisIndex: [0, 1],
      start: 0,
      end: 100
    }, {
      show: true,
      xAxisIndex: [0, 1],
      type: 'slider',
      bottom: '5%',
      start: 0,
      end: 100
    }],
    series: [{
      name: '价格',
      type: 'candlestick',
      data: candlestickData,
      itemStyle: {
        color: '#67C23A',
        color0: '#F56C6C',
        borderColor: '#67C23A',
        borderColor0: '#F56C6C'
      }
    }, {
      name: '成交量',
      type: 'bar',
      xAxisIndex: 1,
      yAxisIndex: 1,
      data: klineData.map(item => ({
        value: item.volume,
        itemStyle: {
          color: item.close > item.open ? '#67C23A' : '#F56C6C'
        }
      }))
    }]
  }

  chart.setOption(option, true)
}

// 获取K线数据
const fetchKlineData = async () => {
  try {
    const response = await axios.get(
      `${API_BASE_URL}/api/market/kline/${symbol.value}?interval=${selectedPeriod.value}`
    )
    if (response.data?.code === '0' && response.data?.data) {
      const klineData = formatKlineData(response.data.data)
      updateChart(klineData)
    } else {
      ElMessage.error(response.data?.msg || '获取K线数据失败')
    }
  } catch (error) {
    ElMessage.error('获取K线数据失败')
  }
}

// 监听窗口大小变化
const handleResize = () => {
  if (chart) {
    chart.resize()
  }
}

const handleClearHistory = async () => {
  try {
    // 显示确认对话框
    await ElMessageBox.confirm('确定要清空所有历史记录吗？此操作不可恢复！', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    isClearing.value = true
    const response = await axios.post(`${API_BASE_URL}/api/clear_history`)
    if (response.data.status === 'success') {
      ElMessage.success('历史记录已清空')
      // 刷新数据
      await fetchStrategyState()
      await fetchTradeHistory()
      await fetchAccountBalance()
    }
  } catch (error) {
    if (error !== 'cancel') {
      console.error('清空历史记录失败:', error)
      ElMessage.error(error.response?.data?.detail || '清空历史记录失败')
    }
  } finally {
    isClearing.value = false
  }
}

onMounted(async () => {
  await fetchStrategyState()  // 首次加载时获取策略状态
  connectWebSocket()
  fetchTradeHistory()
  fetchAccountBalance()
  fetchKlineData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  if (ws) {
    console.log('组件卸载，关闭WebSocket连接')
    ws.close(1000, 'Component unmounted')
    ws = null
  }
  window.removeEventListener('resize', handleResize)
  if (chart) {
    chart.dispose()
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})

// 添加到定时刷新
let refreshInterval = setInterval(() => {
  fetchTradeHistory()
  fetchAccountBalance()
  fetchKlineData()
}, 60000)
</script>

<style scoped>
.trading-view {
  padding: 20px;
}

.el-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price-info,
.strategy-info,
.balance-info {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.price-item,
.info-item,
.balance-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: #606266;
}

.value {
  font-weight: bold;
}

.text-success {
  color: #67C23A;
}

.text-danger {
  color: #F56C6C;
}

.trade-history {
  margin-top: 20px;
}

.strategy-controls {
  display: flex;
  gap: 10px;
}

.market-chart {
  margin-bottom: 20px;
}

.chart-controls {
  display: flex;
  gap: 10px;
}

.table-container {
  margin: 0 auto;
  max-width: 900px;
}

.trade-history .el-card__body {
  padding: 10px 20px;
}
</style> 