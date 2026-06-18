import {createApp} from 'vue'
import {createPinia} from 'pinia'
import {createI18n} from 'vue-i18n'
import {router} from './router/index.js'
import App from './App.vue'
import './style.css'
import esMessages from './locales/es-ES.json'
import enMessages from './locales/en-US.json'

const locales = {'es-ES': esMessages, 'en-US': enMessages}

async function bootstrap() {
    let locale = 'es-ES'
    try {
        const res = await fetch('/api/config')
        if (res.ok) {
            const config = await res.json()
            const lang = config?.app?.language
            if (lang && locales[lang]) locale = lang
        }
    } catch { /* fallback to es-ES */
    }

    const i18n = createI18n({
        legacy: false,
        locale,
        messages: locales,
        fallbackLocale: 'es-ES',
        missingWarn: false,
        fallbackWarn: false,
    })

    createApp(App).use(createPinia()).use(router).use(i18n).mount('#app')
}

bootstrap()
