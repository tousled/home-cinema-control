import {computed, toValue} from 'vue'

const EMPTY_PROVIDER = {server_url: '', display_name: '', access_token_configured: false}

// `config` may be a ref, computed, or plain getter function returning the
// full loaded config object (e.g. () => config.value). Resolves
// media_servers.providers[media_servers.active] — the per-provider shape
// that replaced the old flat media_server field. See
// .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
export function useActiveMediaServer(config) {
    const type = computed(() => toValue(config)?.media_servers?.active || 'emby')

    const provider = computed(() => {
        const providers = toValue(config)?.media_servers?.providers || {}
        return {...EMPTY_PROVIDER, ...(providers[type.value] || {})}
    })

    return {type, provider}
}
