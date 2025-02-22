import { createApp } from 'vue'
import './style.css'
import App from './App.vue'
import router from './router'

// 引入naive-ui样式
import 'vfonts/Lato.css'
import 'vfonts/FiraCode.css'

// 引入Element Plus
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import zhCn from 'element-plus/dist/locale/zh-cn.mjs'

const app = createApp(App)

app.use(router)
app.use(ElementPlus, {
  locale: zhCn,
})

app.mount('#app')
