import {ref} from 'vue'
import {api} from '../api/index.js'

const _readiness = ref(null)
let _fetching = false
let _fetched = false
let _listenerRegistered = false
let _refreshQueued = false

export async function refreshSetupReadiness() {
    if (_fetching) {
        _refreshQueued = true
        return _readiness.value
    }
    _fetching = true
    try {
        const data = await api.getConfigReadiness()
        _readiness.value = data
        _fetched = true
        return data
    } catch {
        _readiness.value = null
        return null
    } finally {
        _fetching = false
        if (_refreshQueued) {
            _refreshQueued = false
            refreshSetupReadiness()
        }
    }
}

function ensureReadinessListener() {
    if (_listenerRegistered || typeof window === 'undefined') return
    window.addEventListener('hcc:config-saved', () => {
        refreshSetupReadiness()
    })
    _listenerRegistered = true
}

export function useSetupReadiness() {
    ensureReadinessListener()

    if (!_fetched && !_fetching) {
        refreshSetupReadiness()
    }

    return {readiness: _readiness, refreshReadiness: refreshSetupReadiness}
}
