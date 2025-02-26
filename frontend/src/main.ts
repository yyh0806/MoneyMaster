import { createApp } from 'vue'
import App from './App.vue'
import router from './router'

// 引入Element Plus
import ElementPlus from 'element-plus'
// 引入基础样式
import 'element-plus/dist/index.css'
// 引入暗色主题
import 'element-plus/theme-chalk/dark/css-vars.css'
// 使用自定义主题
import './styles/index.scss'
// 引入中文语言包
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'
// 引入全局样式
import './style.css'

const app = createApp(App)

app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')
