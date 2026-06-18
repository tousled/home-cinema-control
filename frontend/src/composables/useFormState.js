import {ref} from 'vue'

export function useFormState() {
    const loading = ref(false)
    const success = ref('')
    const error = ref('')

    function reset() {
        success.value = ''
        error.value = ''
    }

    async function run(label, fn) {
        reset()
        loading.value = true
        try {
            const result = await fn()
            success.value = label
            return result
        } catch (e) {
            error.value = e.message
            throw e
        } finally {
            loading.value = false
        }
    }

    return {loading, success, error, reset, run}
}
