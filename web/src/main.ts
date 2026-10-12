import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { initOpenDesignAnalytics } from '@opendesign-plus/plugins/analytics'
import router from './router'
import App from './App.vue'
import { api } from '@/api/client'
import '@opensig/opendesign/es/index.css'
import '@opensig/opendesign-token/themes/e.light.token.css'
import '@opensig/opendesign-token/themes/e.dark.token.css'
import './styles/main.css'

const app = createApp(App)

// Register the OpenEuler-style analytics plugin (same component used by
// openEuler-portal). It enables the `v-analytics` directive and the wired
// `oaReport` helper; every reported event is delivered to *this* function,
// which forwards it (SDK-batched `{ header, body }`) to the shared openEuler
// dsapi collector (https://dsapi.test.osinfra.cn/query/track/openeuler) via a
// same-origin /api-dsapi prefix, mirroring openEuler-portal's reporting.
app.use(initOpenDesignAnalytics, {
  appKey: 'wittyhub',
  // wittyhub has no cookie-consent gate; analytics is enabled by default.
  isCookieAgreed: () => true,
  request: (data: unknown) => {
    api.track(data as Record<string, unknown>)
  },
})

app.use(createPinia())
app.use(router)
app.mount('#app')
