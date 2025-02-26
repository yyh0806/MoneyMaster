<template>
  <div class="trade-status">
    <!-- 盈亏信息卡片 -->
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
          <span class="value">{{ formatQuantity(positionInfo?.盈亏信息?.当前持仓) }}</span>
        </div>
        <div class="info-item">
          <span class="label">持仓均价:</span>
          <span class="value">{{ formatPrice(positionInfo?.盈亏信息?.持仓均价) }}</span>
        </div>
        <div class="info-item">
          <span class="label">持仓市值:</span>
          <span class="value">{{ formatPrice(positionInfo?.盈亏信息?.持仓市值) }}</span>
        </div>
        <div class="info-item">
          <span class="label">未实现盈亏:</span>
          <span class="value" :class="pnlClass(positionInfo?.盈亏信息?.未实现盈亏)">
            {{ formatPnL(positionInfo?.盈亏信息?.未实现盈亏) }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">总盈亏:</span>
          <span class="value" :class="pnlClass(positionInfo?.盈亏信息?.总盈亏)">
            {{ formatPnL(positionInfo?.盈亏信息?.总盈亏) }}
          </span>
        </div>
        <div class="info-item">
          <span class="label">总手续费:</span>
          <span class="value">{{ formatPrice(positionInfo?.盈亏信息?.总手续费) }}</span>
        </div>
      </div>
    </div>

    <!-- 资金信息卡片 -->
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
          <span class="value">{{ formatPrice(positionInfo?.资金信息?.总资金) }}</span>
        </div>
        <div class="info-item">
          <span class="label">已用资金:</span>
          <span class="value">{{ formatPrice(positionInfo?.资金信息?.已用资金) }}</span>
        </div>
        <div class="info-item">
          <span class="label">可用资金:</span>
          <span class="value">{{ formatPrice(positionInfo?.资金信息?.可用资金) }}</span>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { InfoFilled } from '@element-plus/icons-vue';
import type { PositionInfo } from '@/types/trading';
import { formatPrice, formatQuantity, formatPnL } from '@/utils/formatters';

const props = defineProps<{
  positionInfo?: PositionInfo;
}>();

const pnlClass = (value: number | undefined) => {
  if (!value) return '';
  return value > 0 ? 'profit' : value < 0 ? 'loss' : '';
};
</script>

<style scoped>
.trade-status {
  display: flex;
  gap: 20px;
}

.status-info {
  flex: 1;
  background: var(--el-bg-color);
  border-radius: 4px;
  padding: 16px;
}

.section-title {
  font-weight: bold;
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.info-icon {
  color: var(--el-color-info);
  cursor: help;
}

.info-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: var(--el-text-color-secondary);
}

.value {
  font-weight: 500;
}

.profit {
  color: #67c23a;
}

.loss {
  color: #f56c6c;
}
</style> 