import {defineStore} from 'pinia'
import {ref} from 'vue'
import {api} from '../api/index.js'

export const useVersionStore = defineStore('version', () => {
    const newVersionAvailable = ref(false)
    const rollbackInfo = ref(null)

    function setVersionInfo(info) {
        newVersionAvailable.value = info?.new_version === true
    }

    function clearNewVersion() {
        newVersionAvailable.value = false
    }

    async function loadRollbackInfo() {
        try {
            rollbackInfo.value = await api.rollbackVersion()
        } catch {
            rollbackInfo.value = {available: false}
        }
    }

    return {newVersionAvailable, rollbackInfo, setVersionInfo, clearNewVersion, loadRollbackInfo}
})
