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
            <div class="latest-price">
              <span class="label">最新价格:</span>
              <span class="value" :class="priceChangeClass">{{ marketData.last_price || '-' }}</span>
            </div>
            <div class="price-details">
              <div class="detail-item">
                <span class="label">24h高:</span>
                <span class="value">{{ marketData.high_24h || '-' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">24h低:</span>
                <span class="value">{{ marketData.low_24h || '-' }}</span>
              </div>
              <div class="detail-item">
                <span class="label">24h成交量:</span>
                <span class="value">{{ marketData.volume_24h || '-' }}</span>
              </div>
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
                <el-select v-model="selectedPeriod" size="small" @change="handlePeriodChange">
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
      <el-col :span="24">
        <el-card class="strategy-status" :body-style="{ padding: '20px' }">
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
            <el-row :gutter="20">
              <!-- 左侧面板：思考过程 -->
              <el-col :span="6">
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
                        <span :class="['value', 'recommendation-text', recommendationClass]">{{ getRecommendationText }}</span>
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
              </el-col>

              <!-- 右侧面板：状态和交易记录 -->
              <el-col :span="18">
                <!-- 状态信息行 -->
                <el-row :gutter="16" class="status-row">
                  <!-- 盈亏信息卡片 -->
                  <el-col :span="6">
                    <div class="status-info">
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
                  </el-col>

                  <!-- 资金信息卡片 -->
                  <el-col :span="6">
                    <div class="status-info">
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
                  </el-col>

                  <!-- 风险信息卡片 -->
                  <el-col :span="6">
                    <div class="status-info">
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
                  </el-col>

                  <!-- 状态信息 -->
                  <el-col :span="6">
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
                  </el-col>
                </el-row>

                <!-- 交易记录表格 -->
                <el-row class="trade-records-row">
                  <el-col :span="24">
                    <div class="trade-records">
                      <div class="section-header">
                        <div class="title-area">
                          <span class="section-title">交易记录</span>
                          <el-tooltip content="策略的历史交易记录" placement="top">
                            <el-icon class="info-icon"><InfoFilled /></el-icon>
                          </el-tooltip>
                        </div>
                        <div class="actions-area">
                          <el-button
                            type="danger"
                            size="small"
                            @click="handleClearHistory"
                            :loading="isClearing"
                          >
                            清空历史
                          </el-button>
                        </div>
                      </div>
                      <div class="table-container">
                        <el-table 
                          :data="tradeHistory" 
                          style="width: 100%" 
                          height="350"
                          :header-cell-style="{
                            background: '#1a1a1a',
                            color: '#e5e7eb',
                            borderColor: '#262626'
                          }"
                          :cell-style="{
                            borderColor: '#262626'
                          }"
                        >
                          <el-table-column prop="trade_time" label="时间" min-width="180" align="center">
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
                          <el-table-column prop="price" label="价格" width="120" align="right">
                            <template #default="scope">
                              {{ formatPrice(scope.row.price) }}
                            </template>
                          </el-table-column>
                          <el-table-column prop="quantity" label="数量" width="120" align="right">
                            <template #default="scope">
                              {{ formatQuantity(scope.row.quantity) }}
                            </template>
                          </el-table-column>
                          <el-table-column prop="commission" label="手续费" width="100" align="right">
                            <template #default="scope">
                              {{ formatPrice(scope.row.commission) }}
                            </template>
                          </el-table-column>
                          <el-table-column prop="realized_pnl" label="实现盈亏" width="120" align="right">
                            <template #default="scope">
                              <span :class="pnlClass(scope.row.realized_pnl)">
                                {{ scope.row.realized_pnl === 0 ? '-' : formatPnL(scope.row.realized_pnl) }}
                              </span>
                            </template>
                          </el-table-column>
                        </el-table>
                      </div>
                    </div>
                  </el-col>
                </el-row>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, computed, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ArrowRight, InfoFilled } from '@element-plus/icons-vue'
import axios from 'axios'
import dayjs from 'dayjs'
import * as echarts from 'echarts'
import { useWebSocket } from '@vueuse/core'

// 使用相对路径
const API_BASE_URL = ''
const symbol = ref('BTC-USDT')
const marketData = ref({
  last_price: '-',
  best_bid: '-',
  best_ask: '-',
  high_24h: '-',
  low_24h: '-',
  volume_24h: '-'
})
const strategyState = ref({})
const accountBalances = ref({})
const tradeHistory = ref([])
const isStrategyRunning = ref(false)
const selectedPeriod = ref('15m')
const chartContainer = ref(null)
const chart = ref(null)
let ws = null
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
const formatPrice = (price) => {
  if (!price || price === '0' || price === '-') return '-'
  return `$${Number(price).toFixed(2)}`
}

const formatQuantity = (qty) => qty ? Number(qty).toFixed(6) : '-'
const formatVolume = (vol) => {
  if (!vol || vol === '0' || vol === '-') return '-'
  return Number(vol).toFixed(2)
}
const formatPnL = (pnl) => pnl ? `$${Number(pnl).toFixed(2)}` : '-'
const formatBalance = (balance) => balance ? Number(balance).toFixed(6) : '-'
const formatDateTime = (datetime) => dayjs(datetime).format('YYYY-MM-DD HH:mm:ss')

// 样式计算
const priceChangeClass = computed(() => {
  if (!marketData.value.last_price || marketData.value.last_price === '-') return ''
  const lastPrice = parseFloat(marketData.value.last_price)
  const prevPrice = parseFloat(marketData.value._prevPrice || marketData.value.last_price)
  return lastPrice > prevPrice ? 'price-up' : lastPrice < prevPrice ? 'price-down' : ''
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

// 获取市场数据
const fetchMarketData = async () => {
  try {
    log('获取市场数据:', symbol.value)
    const response = await axios.get(`${API_BASE_URL}/api/market/price/${symbol.value}`)
    log('市场数据响应:', response.data)
    
    if (response.data && response.data.data) {
      marketData.value = {
        _prevPrice: marketData.value.last_price,
        last_price: formatPrice(response.data.data.last_price),
        best_bid: formatPrice(response.data.data.best_bid),
        best_ask: formatPrice(response.data.data.best_ask),
        high_24h: formatPrice(response.data.data.high_24h),
        low_24h: formatPrice(response.data.data.low_24h),
        volume_24h: formatVolume(response.data.data.volume_24h),
        timestamp: response.data.data.timestamp || new Date().toISOString()
      }
      log('更新市场数据:', marketData.value)
    } else {
      log('获取市场数据失败:', response.data)
      ElMessage.warning('获取市场数据失败')
    }
  } catch (error) {
    log('获取市场数据异常:', error)
    ElMessage.error('获取市场数据失败')
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

// 更新图表
const updateChart = (klineData) => {
  console.log('开始更新图表，数据长度:', klineData.length)
  
  if (!chart.value) {
    console.log('图表未初始化，正在初始化...')
    initChart()
  }

  if (!chart.value) {
    console.error('图表初始化失败')
    return
  }

  try {
    const option = chart.value.getOption()
    const data = option.series[0].data
    
    // 更新或添加新的K线数据
    const timestamp = klineData[0]
    const index = data.findIndex(item => item[0] === timestamp)
    
    if (index !== -1) {
      data[index] = klineData
    } else {
      data.push(klineData)
      // 保持数据按时间排序
      data.sort((a, b) => a[0] - b[0])
    }
    
    // 更新图表
    chart.value.setOption({
      series: [{
        data: data.map(item => [
          item[0],
          item[1],
          item[2],
          item[3],
          item[4],
          item[5]
        ])
      }]
    })
    console.log('图表更新完成')
  } catch (error) {
    console.error('更新图表失败:', error)
    ElMessage.error('更新图表失败')
  }
}

// 获取K线数据
const fetchKlineData = async () => {
  try {
    log('获取K线数据:', {
      symbol: symbol.value,
      interval: selectedPeriod.value
    })
    
    const response = await axios.get(`${API_BASE_URL}/api/market/full-history-kline/${symbol.value}`, {
      params: {
        interval: selectedPeriod.value
      }
    })
    
    log('K线数据响应:', response.data)
    
    if (response.data?.code === '0' && Array.isArray(response.data?.data)) {
      const data = response.data.data
      if (data.length > 0) {
        // 初始化图表
        if (!chart.value) {
          initChart()
        }
        
        // 设置图表配置
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
          series: [{
            type: 'candlestick',
            data: data.map(item => [
              item[0], // 时间戳
              item[1], // 开盘价
              item[2], // 最高价
              item[3], // 最低价
              item[4]  // 收盘价
            ])
          }],
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'cross'
            },
            formatter: (params) => {
              const item = params[0]
              const date = new Date(item.data[0])
              return [
                `时间: ${date.toLocaleString()}`,
                `开盘价: ${item.data[1]}`,
                `最高价: ${item.data[2]}`,
                `最低价: ${item.data[3]}`,
                `收盘价: ${item.data[4]}`
              ].join('<br/>')
            }
          },
          dataZoom: [
            {
              type: 'inside',
              start: 50,
              end: 100
            },
            {
              show: true,
              type: 'slider',
              bottom: '5%',
              start: 50,
              end: 100
            }
          ]
        }
        
        chart.value.setOption(option)
        log('K线图更新成功')
      } else {
        log('没有有效的K线数据')
        ElMessage.warning('暂无有效的K线数据')
      }
    } else {
      log('获取K线数据失败:', response.data)
      ElMessage.warning('获取K线数据失败')
    }
  } catch (error) {
    log('获取K线数据异常:', error)
    ElMessage.error('获取K线数据失败')
  }
}

// WebSocket处理K线数据更新
const handleKlineUpdate = (klineData) => {
  if (!chart.value) return
  
  const option = chart.value.getOption()
  const data = option.series[0].data
  
  // 更新现有K线或添加新的K线
  const timestamp = klineData[0]
  const index = data.findIndex(item => item[0] === timestamp)
  
  if (index !== -1) {
    // 更新现有K线
    data[index] = klineData
  } else {
    // 添加新的K线
    data.push(klineData)
    // 保持数据按时间排序
    data.sort((a, b) => a[0] - b[0])
  }
  
  // 更新图表
  chart.value.setOption({
    series: [{
      data: data
    }]
  })
}

// 处理WebSocket消息
const handleWebSocketMessage = (message) => {
  try {
    const data = JSON.parse(message)
    if (data.code === '0' && data.data) {
      if (data.data.type === 'kline') {
        handleKlineUpdate(data.data.kline[0])
      }
    }
  } catch (error) {
    log('处理WebSocket消息失败:', error)
  }
}

// 处理周期变更
const handlePeriodChange = () => {
  fetchKlineData()
}

// 处理交易对变更
const handleSymbolChange = async () => {
  // 清空历史数据
  historicalData.value.clear()
  
  // 断开旧的WebSocket连接
  if (ws) {
    ws.close()
  }
  
  // 重新获取市场数据
  await fetchStrategyState()
  
  // 重新获取K线数据
  fetchKlineData()
  
  // 重新获取交易历史
  fetchTradeHistory()
  
  // 重新获取账户余额
  fetchAccountBalance()
}

// 组件挂载时启动自动刷新
onMounted(() => {
  log('组件挂载')
  fetchMarketData()  // 先获取一次市场数据
  connectWebSocket() // 然后建立WebSocket连接
  if (chartContainer.value) {
    initChart()
    fetchKlineData()
  }
})

// 监听窗口大小变化
window.addEventListener('resize', () => {
  if (chart.value) {
    chart.value.resize()
  }
})

onUnmounted(() => {
  console.log('组件卸载')
  window.removeEventListener('resize', () => {
    if (chart.value) {
      chart.value.resize()
    }
  })
  if (chart.value) {
    chart.value.dispose()
    chart.value = null
  }
  if (ws) {
    ws.close()
  }
})

const getRecommendationText = computed(() => {
  const recommendationMap = {
    '买入': '买入',
    '卖出': '卖出',
    '持有': '观望'
  }
  return recommendationMap[analysis.value.recommendation] || '观望'
})

// 初始化图表
const initChart = () => {
  if (!chartContainer.value) {
    console.error('图表容器未找到')
    return
  }

  try {
    chart.value = echarts.init(chartContainer.value, 'dark')
    console.log('图表初始化成功')
  } catch (error) {
    console.error('初始化图表失败:', error)
    ElMessage.error('初始化图表失败')
  }
}

// WebSocket连接
const connectWebSocket = () => {
  try {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws/market/${symbol.value}/${selectedPeriod.value}`
    log('连接WebSocket:', wsUrl)
    
    if (ws) {
      ws.close()
    }
    
    ws = new WebSocket(wsUrl)
    
    ws.onopen = () => {
      log('WebSocket连接已建立')
      // 发送订阅消息
      const subscribeMsg = {
        op: 'subscribe',
        args: [
          { channel: 'ticker', instId: symbol.value },
          { channel: `candle${selectedPeriod.value}`, instId: symbol.value }
        ]
      }
      ws.send(JSON.stringify(subscribeMsg))
    }
    
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        log('收到WebSocket消息:', data)
        
        if (data.code === '0' && data.data) {
          if (data.data.type === 'ticker') {
            // 更新市场数据
            const ticker = data.data.ticker
            marketData.value = {
              _prevPrice: marketData.value.last_price,
              last_price: formatPrice(ticker.last_price),
              best_bid: formatPrice(ticker.best_bid),
              best_ask: formatPrice(ticker.best_ask),
              high_24h: formatPrice(ticker.high_24h),
              low_24h: formatPrice(ticker.low_24h),
              volume_24h: formatVolume(ticker.volume_24h)
            }
          } else if (data.data.type === 'kline') {
            // 更新K线图
            const klineData = data.data.kline
            if (Array.isArray(klineData) && klineData.length > 0) {
              // 确保图表已初始化
              if (!chart.value) {
                initChart()
              }
              
              // 更新图表数据
              const option = chart.value.getOption()
              const chartData = option.series[0].data || []
              
              // 更新或添加新的K线数据
              klineData.forEach(kline => {
                const timestamp = kline[0]
                const index = chartData.findIndex(item => item[0] === timestamp)
                
                if (index !== -1) {
                  chartData[index] = kline
                } else {
                  chartData.push(kline)
                }
              })
              
              // 保持数据按时间排序
              chartData.sort((a, b) => a[0] - b[0])
              
              // 更新图表
              chart.value.setOption({
                series: [{
                  data: chartData
                }]
              })
            }
          }
        }
      } catch (error) {
        log('处理WebSocket消息失败:', error)
      }
    }
    
    ws.onerror = (error) => {
      log('WebSocket错误:', error)
      ElMessage.error('WebSocket连接错误')
    }
    
    ws.onclose = () => {
      log('WebSocket连接已关闭')
      // 尝试重新连接
      setTimeout(() => {
        if (!ws || ws.readyState === WebSocket.CLOSED) {
          connectWebSocket()
        }
      }, 5000)
    }
  } catch (error) {
    log('创建WebSocket连接失败:', error)
    ElMessage.error('创建WebSocket连接失败')
  }
}
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
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 16px;
  font-weight: 600;
  color: #e5e7eb;
  margin-bottom: 15px;
  padding-bottom: 12px;
  border-bottom: 1px solid #262626;

  .info-icon {
    font-size: 16px;
    color: #60a5fa;
    cursor: pointer;
  }
}

.thinking-process {
  height: 100%;
  margin: 0;
  background: #18181b;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #262626;
  display: flex;
  flex-direction: column;

  .analysis-section {
    flex: 1;
    overflow-y: auto;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-track {
      background: #18181b;
      border-radius: 3px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: #4a4a4a;
      border-radius: 3px;
    }
    
    &::-webkit-scrollbar-thumb:hover {
      background: #5a5a5a;
    }
  }

  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.analysis-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
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
  padding: 10px;
  height: 100%;

  .el-row {
    height: 100%;
  }

  .el-col {
    height: 100%;
  }
}

.status-row {
  margin-bottom: 20px;
  height: 220px;  /* 固定状态信息行的高度 */
}

.trade-records-row {
  margin-top: 0;
  height: calc(100% - 240px);  /* 减去状态行高度和间距 */
}

.thinking-process {
  height: 100%;
  margin: 0;
  background: #18181b;
  border-radius: 8px;
  padding: 20px;
  border: 1px solid #262626;
  display: flex;
  flex-direction: column;

  .analysis-section {
    flex: 1;
    overflow-y: auto;
    
    &::-webkit-scrollbar {
      width: 6px;
    }
    
    &::-webkit-scrollbar-track {
      background: #18181b;
      border-radius: 3px;
    }
    
    &::-webkit-scrollbar-thumb {
      background: #4a4a4a;
      border-radius: 3px;
    }
    
    &::-webkit-scrollbar-thumb:hover {
      background: #5a5a5a;
    }
  }

  .empty-state {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
  }
}

.status-info {
  background: #18181b;
  border-radius: 8px;
  padding: 15px;
  border: 1px solid #262626;
  height: 100%;
  display: flex;
  flex-direction: column;

  .info-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
  }
}

.trade-records {
  background: #18181b;
  border-radius: 8px;
  padding: 15px;  /* 减小整体内边距 */
  border: 1px solid #262626;
  height: 100%;
  display: flex;
  flex-direction: column;

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid #262626;

    .title-area {
      display: flex;
      align-items: center;
      gap: 8px;

      .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #e5e7eb;
        margin: 0;
        padding: 0;
        border: none;
      }

      .info-icon {
        font-size: 16px;
        color: #60a5fa;
        cursor: pointer;
      }
    }
  }

  .table-container {
    flex: 1;
    background: #1f1f23;
    border-radius: 8px;
    padding: 12px;  /* 减小表格容器的内边距 */
    border: 1px solid #262626;
    overflow: hidden;

    :deep(.el-table) {
      height: 100%;
      background-color: transparent;
      border: none;
      
      &::before {
        display: none;
      }
      
      th {
        background-color: #1a1a1a;
        border-bottom: 1px solid #262626;
        padding: 8px;  /* 减小表头单元格的内边距 */
        font-weight: 500;
        font-size: 13px;  /* 稍微减小表头文字大小 */
      }
      
      td {
        background-color: transparent;
        border-bottom: 1px solid #262626;
        padding: 6px 8px;  /* 减小表格单元格的内边距 */
        font-size: 13px;  /* 稍微减小单元格文字大小 */
      }
      
      tr {
        background-color: transparent;
        
        &:hover > td {
          background-color: #262626;
        }
      }
    }
  }
}

.section-subtitle {
  font-size: 15px;
  font-weight: 500;
  color: #e5e7eb;
  margin: 15px 0 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid #2d2d33;
}

.actions-area {
  display: flex;
  gap: 10px;
}
</style> 