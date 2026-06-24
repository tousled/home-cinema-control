import {nextTick} from 'vue'
import {describe, expect, it, vi} from 'vitest'
import {useMediaPathWorkflow} from './useMediaPathWorkflow.js'

function workflow(overrides = {}) {
    return useMediaPathWorkflow({
        api: {
            previewPath: vi.fn(),
            getPathMappingSuggestions: vi.fn(),
            testPath: vi.fn(),
            navigatePath: vi.fn(),
        },
        defaultProtocol: () => 'nfs',
        isLibraryIntercepted: () => true,
        persistRouteMappings: vi.fn(),
        persistNetworkAccess: vi.fn(),
        clearSmbCredentials: vi.fn(),
        ...overrides,
    })
}

describe('useMediaPathWorkflow', () => {
    it('keeps verified route state separate from intercepted-library state', async () => {
        const subject = workflow({
            isLibraryIntercepted: () => false,
        })

        subject.initialize(
            {
                media_servers: {
                    active: 'emby',
                    providers: {
                        emby: {
                            playback: {
                                path_mappings: [
                                    {
                                        name: 'Movies',
                                        source_path: '/volume1/Video/Movies',
                                        player_path: '/NAS/Movies',
                                        protocol: 'nfs',
                                        verified: true,
                                    },
                                ],
                            },
                        },
                    },
                },
            },
            [
                {
                    library_name: 'Movies',
                    source_path: '/volume1/Video/Movies',
                },
            ],
        )
        await nextTick()

        expect(subject.detectedRows.value[0].status).toBe('not_intercepted')
        expect(subject.detectedRows.value[0].mapping.verified).toBe(true)
    })

    it('invalidates CIFS mappings without invalidating verified NFS mappings', async () => {
        const persistNetworkAccess = vi.fn(async ({pathMappings}) => ({
            media_servers: {
                active: 'emby',
                providers: {emby: {playback: {path_mappings: pathMappings}}},
            },
        }))
        const subject = workflow({persistNetworkAccess})

        subject.initialize(
            {
                media_servers: {
                    active: 'emby',
                    providers: {
                        emby: {
                            playback: {
                                path_mappings: [
                                    {
                                        name: 'Movies',
                                        source_path: '/volume1/Video/Movies',
                                        player_path: '/NAS-NFS/Movies',
                                        protocol: 'nfs',
                                        verified: true,
                                    },
                                    {
                                        name: 'Trailers',
                                        source_path: '/volume1/Video/Trailers',
                                        player_path: '/NAS-SMB/Trailers',
                                        protocol: 'cifs',
                                        verified: true,
                                    },
                                ],
                            },
                        },
                    },
                },
            },
            [],
        )

        await subject.saveNetworkAccess({
            smbAccessChanged: true,
            preMountSmb: true,
            username: 'nas',
            password: 'secret',
        })

        expect(subject.manualRows.value[0].mapping.verified).toBe(true)
        expect(subject.manualRows.value[1].mapping.verified).toBe(false)
    })
})
