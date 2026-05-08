import { createApp } from 'vue'
import App from './App.vue'
import Antd from 'ant-design-vue'
import 'ant-design-vue/dist/reset.css'
import './composables/useModelStatus'

const app = createApp(App)

app.use(Antd)

app.mount('#app')

const splash = document.getElementById('splash')
if (splash) {
  splash.classList.add('fade-out')
  setTimeout(() => splash.remove(), 400)
}
