import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// 引入Element Plus
import ElementPlus from 'element-plus'
// 使用自定义主题
import './styles/index.scss'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const app = createApp(App)

app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')
