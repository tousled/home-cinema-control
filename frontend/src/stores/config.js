import {defineStore} from 'pinia'
import {ref} from 'vue'
import {api} from '../api/index.js'

export const useConfigStore = defineStore('config', () => {
    const config = ref(null)
    const loading = ref(false)
    const error = ref(null)

    async function load() {
        loading.value = true
        error.value = null
        try {
            config.value = await api.getConfig()
        } catch (e) {
            error.value = e.message
        } finally {
            loading.value = false
        }
    }

    return {config, loading, error, load}
})
