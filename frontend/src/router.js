import { createRouter, createWebHistory } from 'vue-router'
import { farm, fieldById } from './data/fields.js'

const routes = [
  { path: '/', redirect: '/farm' },
  { path: '/farm', component: () => import('./views/FarmMap.vue') },
  { path: '/farm/alert', component: () => import('./views/FarmMap.vue'), meta: { alert: true } },
  { path: '/field/:id/crops', component: () => import('./views/Crops.vue') },
  { path: '/field/:id/soil', component: () => import('./views/Soil.vue') },
  { path: '/field/:id/priorities', component: () => import('./views/Priorities.vue') },
  { path: '/field/:id/results', component: () => import('./views/Results.vue') },
  { path: '/field/:id/results/:option', component: () => import('./views/Results.vue') },
  { path: '/field/:id/costs', component: () => import('./views/CostsMoney.vue') },
  { path: '/field/:id/costs/big-picture', component: () => import('./views/CostsBigPicture.vue') },
  { path: '/planting', component: () => import('./views/Planting.vue') },
  { path: '/how', component: () => import('./views/HowWeCalculated.vue') },
  { path: '/:pathMatch(.*)*', redirect: '/farm' }
]

const router = createRouter({
  history: createWebHistory(),
  routes,
  scrollBehavior: () => ({ top: 0 })
})

// /field/:id/...: the id picks the selected field; an unknown id goes back to the map.
router.beforeEach((to) => {
  if (!to.path.startsWith('/field/')) return true
  const id = String(to.params.id)
  if (!fieldById(id)) return '/farm'
  farm.selectedId = id
  return true
})

export default router
