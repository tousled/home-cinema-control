import {beforeEach, describe, expect, it, vi} from 'vitest'
import {patchSetupReadiness, refreshSetupReadiness, useSetupReadiness} from './useSetupReadiness.js'

vi.mock('../api/index.js', () => ({
    api: {
        getConfigReadiness: vi.fn(),
    },
}))

describe('useSetupReadiness', () => {
    beforeEach(async () => {
        const {api} = await import('../api/index.js')
        api.getConfigReadiness.mockReset()
        api.getConfigReadiness.mockResolvedValue({
            media_server: {status: 'verified', detail: 'Jellyfin'},
        })
    })

    it('lets a live page downgrade a stale successful readiness result', async () => {
        const {readiness} = useSetupReadiness()
        await refreshSetupReadiness()

        patchSetupReadiness('media_server', {
            status: 'incomplete',
            detail: 'Jellyfin is not responding right now',
        })

        expect(readiness.value.media_server).toEqual({
            status: 'incomplete',
            detail: 'Jellyfin is not responding right now',
        })
    })
})
