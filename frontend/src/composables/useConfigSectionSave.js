import {ref} from 'vue'
import {api} from '../api/index.js'

const sectionQueues = new Map()

export function useConfigSectionSave() {
    const saving = ref(false)

    async function saveSection(section, body) {
        saving.value = true
        try {
            const previous = sectionQueues.get(section) || Promise.resolve()
            const next = previous.then(
                () => api.saveConfigSection(section, body),
                () => api.saveConfigSection(section, body),
            )
            sectionQueues.set(section, next.catch(() => {
            }))
            return await next
        } finally {
            saving.value = false
        }
    }

    return {saving, saveSection}
}
