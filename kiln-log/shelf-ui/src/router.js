import { createRouter, createWebHistory } from 'vue-router'
import FiringList from './views/FiringList.vue'
import FiringDetail from './views/FiringDetail.vue'
import KilnList from './views/KilnList.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: FiringList },
    { path: '/kilns', name: 'kilns', component: KilnList },
    { path: '/firings/:id', name: 'firing', component: FiringDetail, props: true },
  ],
})
