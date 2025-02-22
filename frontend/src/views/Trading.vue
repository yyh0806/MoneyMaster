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
                  :type="isStrategyRunning ? 'danger' : 'success'"
                  size="small"
                  @click="toggleStrategy"
                >
                  {{ isStrategyRunning ? '停止策略' : '启动策略' }}
                </el-button>
              </div>
            </div>
          </template>
          <div class="strategy-info">
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
              <span class="value" :class="pnlClass(strategyState.unrealized_pnl)">
                {{ formatPnL(strategyState.unrealized_pnl) }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">总盈亏:</span>
              <span class="value" :class="pnlClass(strategyState.total_pnl)">
                {{ formatPnL(strategyState.total_pnl) }}
              </span>
            </div>
            <div class="info-item">
              <span class="label">总手续费:</span>
              <span class="value">{{ formatPrice(strategyState.total_commission) }}</span>
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

    <!-- 交易记录表格 -->
    <el-card class="trade-history">
      <template #header>
        <div class="card-header">
          <span>交易记录</span>
        </div>
      </template>
      <el-table :data="tradeHistory" style="width: 100%" height="400">
        <el-table-column prop="trade_time" label="时间" width="180">
          <template #default="scope">
            {{ formatDateTime(scope.row.trade_time) }}
          </template>
        </el-table-column>
        <el-table-column prop="side" label="方向" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.side === 'BUY' ? 'success' : 'danger'">
              {{ scope.row.side === 'BUY' ? '买入' : '卖出' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="price" label="价格" width="150">
          <template #default="scope">
            {{ formatPrice(scope.row.price) }}
          </template>
        </el-table-column>
        <el-table-column prop="quantity" label="数量" width="150">
          <template #default="scope">
            {{ formatQuantity(scope.row.quantity) }}
          </template>
        </el-table-column>
        <el-table-column prop="realized_pnl" label="实现盈亏" width="150">
          <template #default="scope">
            <span :class="pnlClass(scope.row.realized_pnl)">
              {{ formatPnL(scope.row.realized_pnl) }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="commission" label="手续费" width="150">
          <template #default="scope">
            {{ formatPrice(scope.row.commission) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import axios from 'axios'
import dayjs from 'dayjs'

// 使用相对路径
const API_BASE_URL = ''
const symbol = ref('BTC-USDT')
const marketData = ref({})
const strategyState = ref({})
const accountBalances = ref({})
const tradeHistory = ref([])
const isStrategyRunning = ref(false)
let ws = null

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
  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data)
    marketData.value = data.market?.data?.[0] || {}
    if (data.strategy) {
        strategyState.value = data.strategy
        isStrategyRunning.value = data.strategy.is_running
    }
  }

  ws.onclose = () => {
    setTimeout(connectWebSocket, 1000)
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

// 切换策略状态
const toggleStrategy = async () => {
  try {
    const url = `${API_BASE_URL}/api/strategy/${isStrategyRunning.value ? 'stop' : 'start'}`
    await axios.post(url)
    isStrategyRunning.value = !isStrategyRunning.value
    ElMessage.success(`策略${isStrategyRunning.value ? '启动' : '停止'}成功`)
  } catch (error) {
    ElMessage.error(`策略${isStrategyRunning.value ? '启动' : '停止'}失败`)
  }
}

// 定时刷新数据
let refreshInterval

onMounted(() => {
  connectWebSocket()
  fetchTradeHistory()
  fetchAccountBalance()
  
  // 每分钟刷新一次数据
  refreshInterval = setInterval(() => {
    fetchTradeHistory()
    fetchAccountBalance()
  }, 60000)
})

onUnmounted(() => {
  if (ws) {
    ws.close()
  }
  if (refreshInterval) {
    clearInterval(refreshInterval)
  }
})
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
</style> 