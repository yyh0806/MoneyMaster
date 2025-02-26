<template>
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
                  <span :class="['value', 'recommendation-text', recommendationClass]">
                    {{ getRecommendationText }}
                  </span>
                </div>
                <div class="confidence">
                  <span class="label">信心度:</span>
                  <div class="confidence-bar">
                    <div :style="{ width: `${(analysis.confidence || 0) * 100}%` }" class="confidence-fill"></div>
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
          <el-row :gutter="16" class="status-row">
            <el-col :span="12">
              <TradeStatus :position-info="strategyState.position_info" />
            </el-col>
          </el-row>
        </el-col>
      </el-row>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue';
import { InfoFilled } from '@element-plus/icons-vue';
import type { Analysis, StrategyState } from '@/types/trading';
import TradeStatus from './TradeStatus.vue';

const isLoading = ref(false);
const strategyState = ref<StrategyState>({
  status: 'stopped',
  position_info: {}
});

const analysis = ref<Analysis>({});

const hasAnalysisData = computed(() => {
  return !!(analysis.value.reasoning || analysis.value.analysis);
});

const getStrategyButtonType = computed(() => {
  switch (strategyState.value.status) {
    case 'running':
      return 'success';
    case 'paused':
      return 'warning';
    default:
      return 'primary';
  }
});

const getStrategyButtonText = computed(() => {
  switch (strategyState.value.status) {
    case 'running':
      return '停止';
    case 'paused':
      return '继续';
    default:
      return '启动';
  }
});

const canPause = computed(() => {
  return strategyState.value.status === 'running';
});

const recommendationClass = computed(() => {
  switch (analysis.value.recommendation) {
    case 'buy':
      return 'recommendation-buy';
    case 'sell':
      return 'recommendation-sell';
    default:
      return 'recommendation-hold';
  }
});

const getRecommendationText = computed(() => {
  switch (analysis.value.recommendation) {
    case 'buy':
      return '买入';
    case 'sell':
      return '卖出';
    default:
      return '观望';
  }
});

const handleStrategyAction = async () => {
  isLoading.value = true;
  try {
    const action = strategyState.value.status === 'running' ? 'stop' : 'start';
    const response = await fetch(`/api/strategy/${action}`, { method: 'POST' });
    const data = await response.json();
    strategyState.value.status = data.status;
  } catch (error) {
    console.error('策略操作失败:', error);
  } finally {
    isLoading.value = false;
  }
};

const handlePause = async () => {
  isLoading.value = true;
  try {
    const response = await fetch('/api/strategy/pause', { method: 'POST' });
    const data = await response.json();
    strategyState.value.status = data.status;
  } catch (error) {
    console.error('暂停策略失败:', error);
  } finally {
    isLoading.value = false;
  }
};

// 定时获取策略状态和分析结果
const fetchStrategyState = async () => {
  try {
    const [stateResponse, analysisResponse] = await Promise.all([
      fetch('/api/strategy/state'),
      fetch('/api/strategy/analysis')
    ]);
    const [stateData, analysisData] = await Promise.all([
      stateResponse.json(),
      analysisResponse.json()
    ]);
    strategyState.value = stateData;
    analysis.value = analysisData;
  } catch (error) {
    console.error('获取策略状态失败:', error);
  }
};

// 初始化和定时更新
fetchStrategyState();
setInterval(fetchStrategyState, 5000);
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.strategy-title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  color: var(--el-color-info);
  cursor: help;
}

.section-title {
  font-weight: bold;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-subtitle {
  font-weight: 500;
  color: var(--el-text-color-secondary);
  margin-bottom: 8px;
}

.content-block {
  background: var(--el-fill-color-light);
  padding: 12px;
  border-radius: 4px;
  margin-bottom: 16px;
  line-height: 1.5;
}

.recommendation {
  margin-top: 16px;
}

.rec-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}

.recommendation-text {
  font-weight: bold;
}

.recommendation-buy {
  color: #67c23a;
}

.recommendation-sell {
  color: #f56c6c;
}

.recommendation-hold {
  color: #e6a23c;
}

.confidence {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-bar {
  flex: 1;
  height: 6px;
  background: var(--el-fill-color-light);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: var(--el-color-primary);
  transition: width 0.3s ease;
}

.confidence-value {
  min-width: 48px;
  text-align: right;
}

.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  color: var(--el-text-color-secondary);
}

.status-row {
  margin-bottom: 20px;
}
</style> 