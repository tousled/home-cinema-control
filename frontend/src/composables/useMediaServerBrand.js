import {computed, toValue} from 'vue'
import {useI18n} from 'vue-i18n'

const BRANDS = {
    emby: {brand: 'emby', label: 'Emby'},
    jellyfin: {brand: 'jellyfin', label: 'Jellyfin'},
    plex: {brand: 'plex', label: 'Plex'},
}

// `providerType` may be a ref, computed, or plain getter function returning
// the raw `media_server.type` string (e.g. () => config.value.media_server?.type).
export function useMediaServerBrand(providerType) {
    const {t} = useI18n()

    const brand = computed(() => {
        const type = String(toValue(providerType) || 'emby').toLowerCase()
        return BRANDS[type] || {brand: '', label: t('x-media-server-generic')}
    })

    return {brand}
}
