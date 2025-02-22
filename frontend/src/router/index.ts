import { createRouter, createWebHistory } from 'vue-router'
import Trading from '../views/Trading.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'home',
      component: Trading
    },
    {
      path: '/trading',
      name: 'trading',
      component: Trading
    }
  ]
})

export default router 