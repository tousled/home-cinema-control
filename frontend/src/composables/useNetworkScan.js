import {ref} from 'vue'
import {api} from '../api/index.js'

export function useNetworkScan() {
    const scanning = ref(false)
    const devices = ref([])

    async function scan() {
        scanning.value = true
        try {
            devices.value = await api.discoverDevices()
        } catch {
            devices.value = []
        } finally {
            scanning.value = false
        }
    }

    return {scanning, devices, scan}
}
