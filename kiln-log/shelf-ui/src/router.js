import { createRouter, createWebHistory } from 'vue-router'
import FiringList from './views/FiringList.vue'
import FiringDetail from './views/FiringDetail.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: FiringList },
    { path: '/firings/:id', name: 'firing', component: FiringDetail, props: true },
  ],
})
