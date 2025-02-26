<template>
  <div class="account-drawer-container">
    <div class="drawer-trigger" @click="openDrawer">
      <el-icon class="trigger-icon"><ArrowRight /></el-icon>
      <span class="trigger-text">账户</span>
    </div>

    <el-drawer
      v-model="drawerVisible"
      title="账户信息"
      direction="ltr"
      size="260px"
      :with-header="true"
      :modal="true"
      :append-to-body="true"
      :show-close="true"
      :close-on-click-modal="true"
      :close-on-press-escape="true"
      class="account-drawer"
    >
      <div class="drawer-content">
        <el-card class="account-info" shadow="never">
          <template #header>
            <div class="card-header">
              <span>持仓信息</span>
              <el-button type="primary" link @click="fetchAccountBalances">
                <el-icon><Refresh /></el-icon>
              </el-button>
            </div>
          </template>
          <div class="balance-info">
            <template v-if="Object.keys(balances).length > 0">
              <div v-for="(balance, currency) in balances" :key="currency" class="balance-item">
                <div class="currency-info">
                  <span class="currency-icon">{{ getCurrencyIcon(currency) }}</span>
                  <span class="currency-name">{{ currency }}</span>
                  <span class="total-balance">{{ formatBalance(balance.total) }}</span>
                </div>
                <div class="balance-details">
                  <div class="balance-row">
                    <span class="label">可用</span>
                    <span class="value">{{ formatBalance(balance.available) }}</span>
                  </div>
                  <div class="balance-row" v-if="balance.frozen !== '0'">
                    <span class="label">冻结</span>
                    <span class="value">{{ formatBalance(balance.frozen) }}</span>
                  </div>
                </div>
              </div>
            </template>
            <div v-else class="empty-state">
              暂无持仓数据
            </div>
          </div>
        </el-card>
      </div>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { ElMessage, ElDrawer, ElCard, ElButton, ElIcon } from 'element-plus';
import { ArrowRight, Refresh } from '@element-plus/icons-vue';
import { formatBalance } from '@/utils/formatters';

// 确保组件被正确注册
defineOptions({
  name: 'AccountDrawer',
});

interface Balance {
  total: string;
  available: string;
  frozen: string;
}

interface Balances {
  [currency: string]: Balance;
}

const drawerVisible = ref(false);
const balances = ref<Balances>({});

const openDrawer = () => {
  console.log('Opening drawer...'); // 添加调试日志
  drawerVisible.value = true;
  fetchAccountBalances();
};

const getCurrencyIcon = (currency: string): string => {
  const icons: { [key: string]: string } = {
    'BTC': '₿',
    'ETH': 'Ξ',
    'USDT': '₮',
    'BNB': 'BNB',
    'XRP': 'XRP',
    'ADA': 'ADA'
  };
  return icons[currency] || currency;
};

// 获取账户余额的方法
const fetchAccountBalances = async () => {
  try {
    console.log('Fetching account balances...'); // 添加调试日志
    const response = await fetch('/api/v5/account/balance');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const result = await response.json();
    console.log('Account balances result:', result); // 添加调试日志
    if (result.code === "0" && result.data && result.data.balances) {
      balances.value = result.data.balances;
    } else {
      console.error('获取账户余额失败:', result.msg);
      ElMessage.error('获取账户余额失败');
    }
  } catch (error) {
    console.error('获取账户余额失败:', error);
    ElMessage.error('获取账户余额失败');
  }
};

// 组件挂载时获取余额
onMounted(() => {
  console.log('Component mounted'); // 添加调试日志
  fetchAccountBalances();
});

// 设置定时更新
let timer: number | null = null;
onMounted(() => {
  timer = window.setInterval(fetchAccountBalances, 5000);
});

// 组件卸载时清理定时器
onUnmounted(() => {
  if (timer !== null) {
    clearInterval(timer);
    timer = null;
  }
});
</script>

<style scoped>
.account-drawer-container {
  position: relative;
}

.drawer-trigger {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: var(--el-color-primary);
  color: white;
  padding: 8px 10px;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 2000;
  display: flex;
  align-items: center;
  transition: all 0.3s ease;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  user-select: none;
}

.drawer-trigger:hover {
  background: var(--el-color-primary-light-3);
  transform: translateY(-50%) translateX(2px);
}

.trigger-icon {
  margin-right: 4px;
  transition: transform 0.3s ease;
}

.drawer-trigger:hover .trigger-icon {
  transform: translateX(2px);
}

.trigger-text {
  font-size: 14px;
  white-space: nowrap;
}

.account-drawer {
  :deep(.el-drawer__header) {
    margin-bottom: 0;
    padding: 16px 20px;
    border-bottom: 1px solid var(--el-border-color-light);
  }
  
  :deep(.el-drawer__body) {
    padding: 0;
  }
}

.drawer-content {
  height: 100%;
  padding: 8px;
  box-sizing: border-box;
}

.account-info {
  height: 100%;
  
  :deep(.el-card__header) {
    padding: 6px 10px;
  }
  
  :deep(.el-card__body) {
    padding: 8px;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
}

.balance-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.balance-item {
  padding: 6px 8px;
  background: var(--el-fill-color-light);
  border-radius: 4px;
}

.currency-info {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.currency-icon {
  font-size: 14px;
  font-weight: bold;
}

.currency-name {
  font-size: 13px;
  font-weight: 500;
  flex: 1;
}

.total-balance {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-color-primary);
}

.balance-details {
  display: flex;
  flex-direction: column;
  gap: 1px;
  margin-left: 20px;
}

.balance-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 12px;
}

.label {
  color: var(--el-text-color-secondary);
}

.value {
  font-weight: 500;
  color: var(--el-text-color-regular);
}

.empty-state {
  text-align: center;
  color: var(--el-text-color-secondary);
  padding: 12px 0;
  font-size: 12px;
}
</style>