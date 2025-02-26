<template>
  <div>
    <div class="drawer-trigger" @click="drawerVisible = true">
      <el-icon class="trigger-icon"><ArrowRight /></el-icon>
      <span class="trigger-text">账户信息</span>
    </div>

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
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { ArrowRight } from '@element-plus/icons-vue';
import { formatBalance } from '@/utils/formatters';

const drawerVisible = ref(false);
const accountBalances = ref<Record<string, number>>({});

// 获取账户余额的方法
const fetchAccountBalances = async () => {
  try {
    const response = await fetch('/api/account/balances');
    const data = await response.json();
    accountBalances.value = data;
  } catch (error) {
    console.error('获取账户余额失败:', error);
  }
};

// 组件挂载时获取余额
fetchAccountBalances();
</script>

<style scoped>
.drawer-trigger {
  position: fixed;
  left: 0;
  top: 50%;
  transform: translateY(-50%);
  background: var(--el-color-primary);
  color: white;
  padding: 10px;
  border-radius: 0 4px 4px 0;
  cursor: pointer;
  z-index: 100;
  display: flex;
  align-items: center;
}

.trigger-icon {
  margin-right: 4px;
}

.account-info {
  margin: 16px;
}

.balance-info {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.balance-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.label {
  color: var(--el-text-color-secondary);
}

.value {
  font-weight: bold;
}
</style> 