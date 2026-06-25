import {describe, expect, it} from 'vitest'
import {mediaServerProvider, useActiveMediaServer} from './useActiveMediaServer.js'

describe('useActiveMediaServer', () => {
    it('resolves playback for the active provider, not the inactive one', () => {
        const config = {
            media_servers: {
                active: 'jellyfin',
                providers: {
                    emby: {
                        server_url: 'http://emby',
                        playback: {
                            hcc_controlled_device: 'emby-device',
                            libraries: [],
                            path_mappings: [],
                            use_all_libraries: false
                        },
                    },
                    jellyfin: {
                        server_url: 'http://jf',
                        playback: {
                            hcc_controlled_device: 'jf-device',
                            libraries: [],
                            path_mappings: [],
                            use_all_libraries: true
                        },
                    },
                },
            },
        }

        const {type, provider} = useActiveMediaServer(() => config)

        expect(type.value).toBe('jellyfin')
        expect(provider.value.server_url).toBe('http://jf')
        expect(provider.value.playback.hcc_controlled_device).toBe('jf-device')
        expect(provider.value.playback.use_all_libraries).toBe(true)
    })

    it('defaults playback fields when the active provider has no entry yet', () => {
        const config = {media_servers: {active: 'emby', providers: {}}}

        const {provider} = useActiveMediaServer(() => config)

        expect(provider.value.playback).toEqual({
            hcc_controlled_device: '',
            use_all_libraries: false,
            path_mappings: [],
            libraries: [],
        })
    })

    it('can resolve a selected provider without making it active', () => {
        const config = {
            media_servers: {
                active: 'emby',
                providers: {
                    emby: {server_url: 'http://emby'},
                    jellyfin: {server_url: 'http://jf', display_name: 'Pedro'},
                },
            },
        }

        const provider = mediaServerProvider(config, 'jellyfin')

        expect(provider.server_url).toBe('http://jf')
        expect(provider.display_name).toBe('Pedro')
        expect(provider.playback.hcc_controlled_device).toBe('')
    })
})
