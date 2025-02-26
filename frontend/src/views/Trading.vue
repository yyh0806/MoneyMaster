<template>
  <div class="trading-view">
    <AccountDrawer />
    
    <el-row :gutter="20">
      <!-- 市场数据卡片 -->
      <el-col :span="4">
        <MarketData />
      </el-col>

      <!-- 市场走势图卡片 -->
      <el-col :span="20">
        <MarketChart />
      </el-col>
    </el-row>

    <!-- AI交易员卡片 -->
    <el-row :gutter="20" style="margin-top: 20px;">
      <el-col :span="24">
        <AITrader />
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import AccountDrawer from '../components/account/AccountDrawer.vue';
import MarketData from '../components/market/MarketData.vue';
import MarketChart from '../components/market/MarketChart.vue';
import AITrader from '../components/trading/AITrader.vue';
</script>

<style scoped>
.trading-view {
  padding: 20px;
}
</style> 