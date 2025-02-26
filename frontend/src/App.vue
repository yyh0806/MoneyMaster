<template>
  <el-config-provider :theme-overrides="themeOverrides">
    <router-view></router-view>
  </el-config-provider>
</template>

<script setup lang="ts">
import { ElConfigProvider } from 'element-plus';
import { ref } from 'vue';

// 主题配置
const themeOverrides = ref({
  dark: true,
  common: {
    'primary-color': '#409EFF',
  },
  card: {
    'bg-color': '#1d1d1d'
  },
  button: {
    'bg-color': '#2b2b2b',
    'text-color': '#E5EAF3',
    'border-color': '#363637',
    'hover-bg-color': '#363637',
    'active-bg-color': '#404040'
  }
});

// 设置暗色主题
document.documentElement.setAttribute('class', 'dark');
document.body.setAttribute('class', 'dark');
</script>

<style>
html, body {
  margin: 0;
  padding: 0;
  height: 100%;
  width: 100%;
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
}

#app {
  width: 100%;
  height: 100vh;
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
}
</style>
