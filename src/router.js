import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/farm' },
  { path: '/farm', component: () => import('./views/FarmMap.vue') },
  { path: '/farm/alert', component: () => import('./views/FarmMap.vue'), meta: { alert: true } },
  { path: '/field/1/crops', component: () => import('./views/Crops.vue') },
  { path: '/field/1/soil', component: () => import('./views/Soil.vue') },
  { path: '/field/1/priorities', component: () => import('./views/Priorities.vue') },
  { path: '/field/1/results', component: () => import('./views/Results.vue') },
  { path: '/field/1/results/:option', component: () => import('./views/Results.vue') },
  { path: '/field/1/costs', component: () => import('./views/CostsMoney.vue') },
  { path: '/field/1/costs/big-picture', component: () => import('./views/CostsBigPicture.vue') },
  { path: '/how', component: () => import('./views/HowWeCalculated.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/farm' }
]

export default createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})
