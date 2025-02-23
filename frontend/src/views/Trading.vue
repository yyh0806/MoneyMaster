<template>
  <div class="trading-view">
    <!-- 添加抽屉按钮 -->
    <div
      class="drawer-trigger"
      @click="drawerVisible = true"
    >
      <el-icon class="trigger-icon"><ArrowRight /></el-icon>
      <span class="trigger-text">账户信息</span>
    </div>

    <!-- 抽屉组件 -->
    <el-drawer
      v-model="drawerVisible"
      title="账户信息"
      direction="ltr"
      size="300px"
      :with-header="true"
      class="account-drawer"
    >
      <div class="drawer-content">
        <el-card class="account-info">
          <div class="balance-info">
            <div v-for="(balance, currency) in accountBalances" :key="currency" class="balance-item">
              <span class="label">{{ currency }}:</span>
              <span class="value">{{ formatBalance(balance) }}</span>
            </div>
          </div>
        </el-card>
      </div>
    </el-drawer>

    <el-row :gutter="20">
      <!-- 市场数据卡片 -->
      <el-col :span="3">
        <el-card class="market-data">
          <template #header>
            <div class="card-header">
              <span>市场数据</span>
              <el-select v-model="symbol" size="small" @change="handleSymbolChange" style="margin-left: 10px; width: 120px;">
                <el-option label="BTC-USDT" value="BTC-USDT" />
                <el-option label="ETH-USDT" value="ETH-USDT" />
                <el-option label="BNB-USDT" value="BNB-USDT" />
                <el-option label="XRP-USDT" value="XRP-USDT" />
                <el-option label="ADA-USDT" value="ADA-USDT" />
              </el-select>
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

      <!-- 市场走势图卡片 -->
      <el-col :span="21">
        <el-card class="market-chart">
          <template #header>
            <div class="card-header">
              <div class="left-controls">
                <span>市场走势图</span>
                <el-select v-model="symbol" size="small" @change="handleSymbolChange" style="margin-left: 10px; width: 120px;">
                  <el-option label="BTC-USDT" value="BTC-USDT" />
                  <el-option label="ETH-USDT" value="ETH-USDT" />
                  <el-option label="BNB-USDT" value="BNB-USDT" />
                  <el-option label="XRP-USDT" value="XRP-USDT" />
                  <el-option label="ADA-USDT" value="ADA-USDT" />
                </el-select>
              </div>
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
      </el-col>
    </el-row>

    <!-- 策略状态卡片行 -->
    <el-row :gutter="20">
      <!-- 杨二狗策略 -->
      <el-col :span="6">
        <el-card class="strategy-status">
          <template #header>
            <div class="card-header">
              <div class="strategy-title">
                <span>AI员工 杨二狗</span>
                <el-tooltip
                  content="您好，我是AI交易员小深。我擅长通过深度分析市场数据和历史交易信息，为您提供专业的交易建议。作为一名尽职的AI交易员，我会时刻关注市场动态，确保每个交易决策都经过深思熟虑。"
                  placement="top"
                >
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
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
            <!-- 思考过程 -->
            <div class="thinking-process">
              <div class="section-title">
                思考过程
                <el-tooltip
                  content="AI模型分析市场数据并做出交易决策的详细过程"
                  placement="top"
                >
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="analysis-section" v-if="hasAnalysisData">
                <!-- 推理过程 -->
                <div class="reasoning" v-if="analysis.reasoning">
                  <div class="section-subtitle">推理过程</div>
                  <div class="content-block">{{ analysis.reasoning }}</div>
                </div>
                
                <!-- 分析内容 -->
                <div class="analysis-content" v-if="analysis.analysis">
                  <div class="section-subtitle">分析内容</div>
                  <div class="content-block">{{ analysis.analysis }}</div>
                </div>
                
                <div class="recommendation">
                  <div class="rec-header">
                    <span class="label">交易建议:</span>
                    <span :class="['value', recommendationClass]">{{ getRecommendationText }}</span>
                  </div>
                  <div class="confidence">
                    <span class="label">信心度:</span>
                    <div class="confidence-bar">
                      <div :style="{ width: `${analysis.confidence * 100}%` }" class="confidence-fill"></div>
                    </div>
                    <span class="confidence-value">{{ ((analysis.confidence || 0) * 100).toFixed(1) }}%</span>
                  </div>
                </div>
              </div>
              <div v-else class="empty-state">
                <p>等待AI分析结果...</p>
              </div>
            </div>

            <!-- 盈亏信息卡片 -->
            <div class="info-card">
              <div class="section-title">
                盈亏信息
                <el-tooltip content="策略运行产生的盈亏统计信息" placement="top">
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="info-content">
                <div class="info-item">
                  <span class="label">当前持仓:</span>
                  <span class="value">{{ formatQuantity(strategyState.position_info?.盈亏信息?.当前持仓) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">持仓均价:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.盈亏信息?.持仓均价) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">持仓市值:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.盈亏信息?.持仓市值) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">未实现盈亏:</span>
                  <span class="value" :class="pnlClass(strategyState.position_info?.盈亏信息?.未实现盈亏)">
                    {{ formatPnL(strategyState.position_info?.盈亏信息?.未实现盈亏) }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="label">总盈亏:</span>
                  <span class="value" :class="pnlClass(strategyState.position_info?.盈亏信息?.总盈亏)">
                    {{ formatPnL(strategyState.position_info?.盈亏信息?.总盈亏) }}
                  </span>
                </div>
                <div class="info-item">
                  <span class="label">总手续费:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.盈亏信息?.总手续费) }}</span>
                </div>
              </div>
            </div>

            <!-- 资金信息卡片 -->
            <div class="info-card">
              <div class="section-title">
                资金信息
                <el-tooltip content="策略可用资金和使用情况" placement="top">
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="info-content">
                <div class="info-item">
                  <span class="label">总资金:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.资金信息?.总资金) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">已用资金:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.资金信息?.已用资金) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">剩余可用:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.资金信息?.剩余可用) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">单笔最大交易:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.资金信息?.单笔最大交易) }}</span>
                </div>
              </div>
            </div>

            <!-- 风险信息卡片 -->
            <div class="info-card">
              <div class="section-title">
                风险信息
                <el-tooltip content="策略风险控制参数" placement="top">
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
              <div class="info-content">
                <div class="info-item">
                  <span class="label">杠杆倍数:</span>
                  <span class="value">{{ strategyState.position_info?.风险信息?.杠杆倍数 }}x</span>
                </div>
                <div class="info-item">
                  <span class="label">最大持仓市值:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.风险信息?.最大持仓市值) }}</span>
                </div>
                <div class="info-item">
                  <span class="label">最大杠杆倍数:</span>
                  <span class="value">{{ strategyState.position_info?.风险信息?.最大杠杆倍数 }}x</span>
                </div>
                <div class="info-item">
                  <span class="label">最小保证金率:</span>
                  <span class="value">{{ (strategyState.position_info?.风险信息?.最小保证金率 * 100).toFixed(2) }}%</span>
                </div>
                <div class="info-item">
                  <span class="label">最大日亏损:</span>
                  <span class="value">{{ formatPrice(strategyState.position_info?.风险信息?.最大日亏损) }}</span>
                </div>
              </div>
            </div>

            <!-- 状态信息 -->
            <div class="status-info">
              <div class="section-title">
                状态信息
                <el-tooltip
                  content="策略运行状态和系统信息"
                  placement="top"
                >
                  <el-icon class="info-icon"><InfoFilled /></el-icon>
                </el-tooltip>
              </div>
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
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 策略2（占位） -->
      <el-col :span="6">
        <el-card class="strategy-status">
          <template #header>
            <div class="card-header">
              <span>策略2</span>
              <div class="strategy-controls">
                <el-button type="success" size="small" disabled>启动策略</el-button>
              </div>
            </div>
          </template>
          <div class="strategy-info">
            <div class="section-title">开发中</div>
            <p class="placeholder-text">该策略正在开发中...</p>
          </div>
        </el-card>
      </el-col>

      <!-- 策略3（占位） -->
      <el-col :span="6">
        <el-card class="strategy-status">
          <template #header>
            <div class="card-header">
              <span>策略3</span>
              <div class="strategy-controls">
                <el-button type="success" size="small" disabled>启动策略</el-button>
              </div>
            </div>
          </template>
          <div class="strategy-info">
            <div class="section-title">开发中</div>
            <p class="placeholder-text">该策略正在开发中...</p>
          </div>
        </el-card>
      </el-col>

      <!-- 策略4（占位） -->
      <el-col :span="6">
        <el-card class="strategy-status">
          <template #header>
            <div class="card-header">
              <span>策略4</span>
              <div class="strategy-controls">
                <el-button type="success" size="small" disabled>启动策略</el-button>
              </div>
            </div>
          </template>
          <div class="strategy-info">
            <div class="section-title">开发中</div>
            <p class="placeholder-text">该策略正在开发中...</p>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易记录表格 -->
    <el-row>
      <el-col :span="24">
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
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, InfoFilled } from '@element-plus/icons-vue'
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
const drawerVisible = ref(false)

// 策略类型
const strategyType = ref('deepseek')  // 默认使用deepseek策略

// AI思考过程相关数据
const analysis = ref({
  analysis: '',
  recommendation: '持有',
  confidence: 0,
  reasoning: '',
  timestamp: 0
})

// 移除不必要的计算属性
const formattedAnalysis = computed(() => {
  return analysis.value.analysis
})

// 添加空值检查的计算属性
const hasAnalysisData = computed(() => {
  return Boolean(analysis.value.reasoning || analysis.value.analysis)
})

const recommendationClass = computed(() => {
  const rec = analysis.value.recommendation
  return {
    'buy': rec === '买入',
    'sell': rec === '卖出',
    'hold': rec === '持有'
  }
})

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

const log = (message: string, ...args: any[]) => {
  const timestamp = dayjs().format('YYYY-MM-DD HH:mm:ss.SSS')
  console.log(`[${timestamp}] ${message}`, ...args)
}

// 添加性能追踪日志
const logPerformance = (stage: string, startTime: number) => {
  const endTime = performance.now()
  const duration = endTime - startTime
  log(`性能追踪 - ${stage}: ${duration.toFixed(2)}ms`)
}

// WebSocket连接
const connectWebSocket = () => {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/ws/strategy/${symbol.value}`
  
  // 如果已经有连接，先关闭
  if (ws) {
    log('关闭现有WebSocket连接')
    ws.close()
    ws = null
  }
  
  log('建立新的WebSocket连接:', wsUrl)
  ws = new WebSocket(wsUrl)
  
  ws.onmessage = (event) => {
    const receiveTime = performance.now()
    log('收到WebSocket消息，开始处理')
    
    try {
      const parseStart = performance.now()
      const data = JSON.parse(event.data)
      logPerformance('JSON解析', parseStart)
      
      // 处理市场数据
      if (data.market?.data?.[0]) {
        const marketStart = performance.now()
        marketData.value = data.market.data[0]
        logPerformance('市场数据更新', marketStart)
      }
      
      // 处理策略状态
      if (data.strategy) {
        const strategyStart = performance.now()
        log('收到策略状态更新:', data.strategy)
        const oldStatus = strategyState.value?.status
        
        // 更新状态前先检查是否真的有变化
        const hasStatusChanged = oldStatus !== data.strategy.status
        const hasPositionChanged = strategyState.value?.position !== data.strategy.position
        const hasPnLChanged = strategyState.value?.total_pnl !== data.strategy.total_pnl
        
        // 更新状态
        strategyState.value = data.strategy
        
        // 如果状态发生实质性变化，显示通知
        if (hasStatusChanged || hasPositionChanged || hasPnLChanged) {
          const statusMap = {
            running: '运行中',
            stopped: '已停止',
            paused: '已暂停',
            error: '发生错误'
          }
          
          if (hasStatusChanged) {
            ElMessage.info(`策略状态变更为: ${statusMap[data.strategy.status] || data.strategy.status}`)
          }
        }
        logPerformance('策略状态更新', strategyStart)
      }
      
      // 处理AI分析结果
      if (data.analysis) {
        const analysisStart = performance.now()
        log('收到AI分析更新:', data.analysis)
        
        // 确保数据存在并且有效
        if (typeof data.analysis === 'object') {
          analysis.value = {
            analysis: data.analysis.analysis || '',
            recommendation: data.analysis.recommendation || '持有',
            confidence: data.analysis.confidence || 0,
            reasoning: data.analysis.reasoning || '',
            timestamp: data.analysis.timestamp || Date.now()
          }
          
          // 调试日志
          log('更新后的分析数据:', analysis.value)
        } else {
          log('无效的分析数据格式:', data.analysis)
        }
        
        logPerformance('AI分析更新', analysisStart)
      }
      
      logPerformance('总处理时间', receiveTime)
    } catch (error) {
      log('处理WebSocket消息失败:', error)
    }
  }

  ws.onopen = () => {
    log('WebSocket连接已建立')
    // 连接成功后立即获取最新状态
    fetchStrategyState()
  }

  ws.onclose = (event) => {
    log('WebSocket连接已关闭，code:', event.code, '原因:', event.reason)
    ws = null
    // 如果不是主动关闭的连接，则尝试重连
    if (event.code !== 1000) {
      log('3秒后尝试重新连接...')
      setTimeout(connectWebSocket, 3000)
    }
  }

  ws.onerror = (error) => {
    log('WebSocket错误:', error)
    ElMessage.error('WebSocket连接错误，正在尝试重新连接...')
    // 发生错误时重新获取状态
    fetchStrategyState()
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
  const statusMap = {
    'running': 'danger',
    'error': 'warning',
    'paused': 'warning',
    'stopped': 'success'
  }
  return statusMap[strategyState.value?.status] || 'success'
})

const getStrategyButtonText = computed(() => {
  const statusMap = {
    'running': '停止策略',
    'paused': '继续运行',
    'error': '重新启动',
    'stopped': '启动策略'
  }
  return statusMap[strategyState.value?.status] || '启动策略'
})

const getStatusTagType = computed(() => {
  const statusMap = {
    'running': 'success',
    'stopped': 'info',
    'paused': 'warning',
    'error': 'danger'
  }
  return statusMap[strategyState.value?.status] || 'info'
})

const getStatusText = computed(() => {
  const statusMap = {
    'running': '运行中',
    'stopped': '已停止',
    'paused': '已暂停',
    'error': '错误'
  }
  return statusMap[strategyState.value?.status] || '未知'
})

const canPause = computed(() => strategyState.value?.status === 'running')

const formatLastRunTime = computed(() => {
  return strategyState.value?.last_run_time
    ? dayjs(strategyState.value.last_run_time).format('YYYY-MM-DD HH:mm:ss')
    : '-'
})

// 处理策略操作
const handleStrategyAction = async () => {
  try {
    isLoading.value = true
    const currentStatus = strategyState.value?.status || 'stopped'
    log('当前策略状态:', currentStatus)
    
    // 根据当前状态决定操作
    const action = currentStatus === 'running' ? 'stop' : 'start'
    
    log(`执行策略${action}操作`)
    await axios.post(`${API_BASE_URL}/api/strategy/${action}`, {
      strategy_type: strategyType.value,
      symbol: symbol.value
    })
    
    // 获取最新状态
    await fetchStrategyState()
    
  } catch (error) {
    log('策略操作失败:', error)
    const errorMessage = error.response?.data?.detail || `策略操作失败`
    ElMessage.error(errorMessage)
    
    // 如果发生错误，重新获取状态以确保显示正确的状态
    await fetchStrategyState()
  } finally {
    isLoading.value = false
  }
}

const handlePause = async () => {
  try {
    isLoading.value = true
    log('执行策略暂停操作')
    await axios.post(`${API_BASE_URL}/api/strategy/pause`, {
      strategy_type: strategyType.value,
      symbol: symbol.value
    })
    
    // 获取最新状态
    await fetchStrategyState()
    
  } catch (error) {
    log('策略暂停失败:', error)
    ElMessage.error(error.response?.data?.detail || '策略暂停失败')
    await fetchStrategyState()
  } finally {
    isLoading.value = false
  }
}

// 获取策略状态
const fetchStrategyState = async () => {
  try {
    log('获取策略状态, 参数:', {
      symbol: symbol.value,
      strategy_type: strategyType.value
    })
    
    const response = await axios.get(
      `${API_BASE_URL}/api/strategy/state?symbol=${symbol.value}&strategy_type=${strategyType.value}`
    )
    
    log('获取策略状态响应:', response.data)
    
    if (response.data && response.data.length > 0) {
      const newState = response.data[0]
      
      // 验证状态的有效性
      if (!['running', 'stopped', 'paused', 'error'].includes(newState.status)) {
        log('无效的策略状态:', newState.status)
        ElMessage.error('收到无效的策略状态')
        return
      }
      
      // 检查状态变化
      const oldStatus = strategyState.value?.status
      if (oldStatus && oldStatus !== newState.status) {
        log('策略状态发生变化:', {
          from: oldStatus,
          to: newState.status
        })
      }
      
      strategyState.value = newState
      log('更新策略状态:', strategyState.value)
    } else {
      log('没有找到策略状态，使用默认值')
      strategyState.value = {
        status: 'stopped',
        position: 0,
        avg_entry_price: 0,
        unrealized_pnl: 0,
        total_pnl: 0,
        total_commission: 0
      }
    }
  } catch (error) {
    log('获取策略状态失败:', error)
    ElMessage.error('获取策略状态失败')
    
    // 如果获取状态失败，不要清空现有状态
    if (!strategyState.value) {
      strategyState.value = {
        status: 'error',
        position: 0,
        avg_entry_price: 0,
        unrealized_pnl: 0,
        total_pnl: 0,
        total_commission: 0,
        last_error: '无法获取策略状态'
      }
    }
  }
}

// 格式化K线数据
const formatKlineData = (data) => {
  return data.map(item => {
    // OKX的K线数据格式：[timestamp, open, high, low, close, volume, ...]
    log('原始数据项:', item)
    const [timestamp, open, high, low, close, volume] = item
    log('解析后的原始数据:', {
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
      log('数据异常: 最高价低于开盘价或收盘价', formattedData)
    }
    if (formattedData.low > formattedData.close || formattedData.low > formattedData.open) {
      log('数据异常: 最低价高于开盘价或收盘价', formattedData)
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
    log('K线数据转换:', {
      from: item,
      to: data
    })
    return data
  })

  const option = {
    animation: false,
    backgroundColor: '#000000',
    textStyle: {
      color: '#ffffff'
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'cross'
      },
      backgroundColor: '#141414',
      borderColor: '#262626',
      textStyle: {
        color: '#ffffff'
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
          log('Tooltip原始数据:', candleData.data)
          // OKX的K线数据格式：[timestamp, open, high, low, close, volume]
          const [timestamp, open, high, low, close] = candleData.data
          log('Tooltip解析后的数据:', {
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
      axisLine: { 
        onZero: false,
        lineStyle: {
          color: '#404040'
        }
      },
      splitLine: { 
        show: true,
        lineStyle: {
          color: '#1a1a1a'
        }
      },
      axisLabel: {
        formatter: (value) => dayjs(value).format('HH:mm'),
        color: '#808080'
      }
    }, {
      type: 'category',
      gridIndex: 1,
      data: klineData.map(item => item.time),
      scale: true,
      boundaryGap: false,
      axisLine: { 
        onZero: false,
        lineStyle: {
          color: '#404040'
        }
      },
      axisTick: { show: false },
      splitLine: { show: false },
      axisLabel: { show: false },
      min: 'dataMin',
      max: 'dataMax'
    }],
    yAxis: [{
      scale: true,
      splitArea: { 
        show: true,
        areaStyle: {
          color: ['#000000', '#0a0a0a']
        }
      },
      splitLine: {
        lineStyle: {
          color: '#1a1a1a'
        }
      },
      axisLine: {
        lineStyle: {
          color: '#404040'
        }
      },
      axisLabel: {
        formatter: (value) => `$${value}`,
        color: '#808080'
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
      end: 100,
      backgroundColor: '#141414',
      borderColor: '#262626',
      fillerColor: 'rgba(38, 38, 38, 0.2)',
      handleStyle: {
        color: '#606060',
        borderColor: '#808080'
      },
      moveHandleStyle: {
        color: '#606060',
        borderColor: '#808080'
      },
      selectedDataBackground: {
        lineStyle: {
          color: '#606060'
        },
        areaStyle: {
          color: '#262626'
        }
      },
      emphasis: {
        handleStyle: {
          borderColor: '#909090'
        },
        moveHandleStyle: {
          borderColor: '#909090'
        }
      },
      dataBackground: {
        lineStyle: {
          color: '#404040'
        },
        areaStyle: {
          color: '#262626'
        }
      },
      textStyle: {
        color: '#808080'
      }
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
      log('清空历史记录失败:', error)
      ElMessage.error(error.response?.data?.detail || '清空历史记录失败')
    }
  } finally {
    isClearing.value = false
  }
}

// 处理交易对变更
const handleSymbolChange = async () => {
  // 断开旧的WebSocket连接
  if (ws) {
    ws.close()
  }
  
  // 重新获取市场数据
  await fetchStrategyState()
  
  // 重新连接WebSocket
  connectWebSocket()
  
  // 重新获取K线数据
  fetchKlineData()
  
  // 重新获取交易历史
  fetchTradeHistory()
  
  // 重新获取账户余额
  fetchAccountBalance()
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
    log('组件卸载，关闭WebSocket连接')
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

const getRecommendationText = computed(() => {
  const recommendationMap = {
    '买入': '买入',
    '卖出': '卖出',
    '持有': '观望'
  }
  return recommendationMap[analysis.value.recommendation] || '观望'
})
</script>

<style scoped>
.trading-view {
  padding: 20px;
}

.drawer-trigger {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  z-index: 100;
  background-color: #141414;
  border: 1px solid #262626;
  border-left: none;
  border-radius: 0 8px 8px 0;
  padding: 12px 8px;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.15);
  transition: all 0.3s ease;

  &:hover {
    background-color: #262626;
    .trigger-icon {
      transform: translateX(3px);
    }
  }

  .trigger-icon {
    font-size: 20px;
    color: #60a5fa;
    transition: transform 0.3s ease;
  }

  .trigger-text {
    writing-mode: vertical-lr;
    letter-spacing: 2px;
    color: #e5e7eb;
    font-size: 14px;
  }
}

.drawer-content {
  height: 100%;
  padding: 0;
  
  .account-info {
    height: 100%;
    border: none;
    background-color: transparent;
    
    .balance-info {
      display: flex;
      flex-direction: column;
      gap: 15px;
    }
  }
}

.el-row {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.left-controls {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chart-controls {
  display: flex;
  gap: 10px;
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

.table-container {
  margin: 0 auto;
  max-width: 900px;
}

.trade-history .el-card__body {
  padding: 10px 20px;
}

.account-drawer {
  /* Add your styles here */
}

.price-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.price-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 14px;
}

.label {
  color: #606266;
  margin-right: 8px;
}

.value {
  font-weight: bold;
  font-size: 14px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: #909399;
  margin: 15px 0 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid #262626;
}

.thinking-process {
  margin-top: 20px;
  background: #18181b;
  border-radius: 8px;
  padding: 20px;
  min-height: 300px;
}

.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.reasoning,
.analysis-content {
  margin-bottom: 20px;
}

.reasoning p,
.analysis-content p {
  margin: 0;
  padding: 12px;
  background: #262626;
  border-radius: 6px;
  color: #E5E7EB;
  font-size: 14px;
  line-height: 1.6;
}

.recommendation {
  margin: 15px 0;
  padding: 10px;
  background: #18181b;
  border-radius: 6px;
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.buy {
  color: #67C23A;
}

.sell {
  color: #F56C6C;
}

.hold {
  color: #60a5fa;
}

.confidence {
  display: flex;
  align-items: center;
  gap: 10px;
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: #262626;
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: #60a5fa;
  transition: width 0.3s ease;
}

.confidence-value {
  min-width: 60px;
  text-align: right;
  font-size: 12px;
  color: #909399;
}

.strategy-info {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.thinking-process,
.pnl-info,
.status-info {
  background: #18181b;
  border-radius: 8px;
  padding: 15px;
}

.section-subtitle {
  font-size: 14px;
  font-weight: 500;
  color: #e5e7eb;
  margin: 15px 0 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2d2d33;
}

.content-block {
  padding: 15px;
  background: #1f1f23;
  border-radius: 6px;
  color: #e5e7eb;
  font-size: 14px;
  line-height: 1.8;
  margin-top: 8px;
  white-space: pre-wrap;
  min-height: 80px;
  max-height: 200px;
  overflow-y: auto;
  border: 1px solid #2d2d33;
}

.content-block::-webkit-scrollbar {
  width: 6px;
}

.content-block::-webkit-scrollbar-track {
  background: #18181b;
  border-radius: 3px;
}

.content-block::-webkit-scrollbar-thumb {
  background: #4a4a4a;
  border-radius: 3px;
}

.content-block::-webkit-scrollbar-thumb:hover {
  background: #5a5a5a;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: #909399;
  font-size: 14px;
}
</style> 