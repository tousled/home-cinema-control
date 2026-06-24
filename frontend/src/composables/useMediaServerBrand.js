import {computed, toValue} from 'vue'
import {useI18n} from 'vue-i18n'

const BRANDS = {
    emby: {brand: 'emby', label: 'Emby'},
    jellyfin: {brand: 'jellyfin', label: 'Jellyfin'},
    plex: {brand: 'plex', label: 'Plex'},
}

// `providerType` may be a ref, computed, or plain getter function returning
// the raw provider type string — typically useActiveMediaServer's `type`,
// or media_servers.active directly (e.g. () => config.value.media_servers?.active).
export function useMediaServerBrand(providerType) {
    const {t} = useI18n()

    const brand = computed(() => {
        const type = String(toValue(providerType) || 'emby').toLowerCase()
        return BRANDS[type] || {brand: '', label: t('x-media-server-generic')}
    })

    return {brand}
}

// Non-reactive label lookup for one-off uses outside a component's reactive
// graph (e.g. building a confirmation message for a provider that isn't the
// current selection). Falls back to the bare type string, not the i18n
// generic label — callers inside a component's reactive graph should prefer
// useMediaServerBrand instead.
export function mediaServerBrandLabel(type) {
    const known = BRANDS[String(type || '').toLowerCase()]
    return known ? known.label : String(type || '')
}
