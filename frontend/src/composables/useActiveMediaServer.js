import {computed, toValue} from 'vue'

const EMPTY_PROVIDER = {
    server_url: '',
    display_name: '',
    access_token_configured: false,
    playback: {hcc_controlled_device: '', use_all_libraries: false, path_mappings: [], libraries: []},
}

export function mediaServerProvider(config, providerType) {
    const providers = config?.media_servers?.providers || {}
    const type = providerType || config?.media_servers?.active || 'emby'
    return {...EMPTY_PROVIDER, ...(providers[type] || {})}
}

// `config` may be a ref, computed, or plain getter function returning the
// full loaded config object (e.g. () => config.value). Resolves
// media_servers.providers[media_servers.active] — the per-provider shape
// that replaced the old flat media_server field. See
// .agents/specs/2026-06-23-media-server-multi-provider-config-design.md.
export function useActiveMediaServer(config) {
    const type = computed(() => toValue(config)?.media_servers?.active || 'emby')

    const provider = computed(() => {
        return mediaServerProvider(toValue(config), type.value)
    })

    return {type, provider}
}
