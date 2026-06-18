import {reactive} from 'vue'

const toasts = reactive([])
let nextId = 0

export function useToast() {
    function show(type, message, duration = 4000) {
        const id = ++nextId
        toasts.push({id, type, message})
        if (duration > 0) {
            setTimeout(() => dismiss(id), duration)
        }
    }

    function dismiss(id) {
        const i = toasts.findIndex(t => t.id === id)
        if (i !== -1) toasts.splice(i, 1)
    }

    return {
        toasts,
        success: (msg, duration) => show('success', msg, duration),
        error: (msg, duration) => show('error', msg, duration),
        dismiss,
    }
}
