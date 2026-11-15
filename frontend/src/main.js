import { createApp } from 'vue'
import App from './App.vue'
import router from './router.js'
import { loadSample } from './data/store.js'
import './styles/prototype.css'
import './styles/app.css'

loadSample('1')
createApp(App).use(router).mount('#app')
