import {describe, expect, it, vi} from 'vitest'

vi.mock('../api/index.js', () => ({
    api: {
        saveConfigSection: vi.fn(),
    },
}))

describe('useConfigSectionSave', () => {
    it('saves through the section endpoint instead of a full config save', async () => {
        const {api} = await import('../api/index.js')
        const {useConfigSectionSave} = await import('./useConfigSectionSave.js')
        api.saveConfigSection.mockResolvedValueOnce({tv: {enabled: false}})

        const {saveSection} = useConfigSectionSave()
        const result = await saveSection('tv', {enabled: false})

        expect(api.saveConfigSection).toHaveBeenCalledWith('tv', {enabled: false})
        expect(result).toEqual({tv: {enabled: false}})
    })

    it('serializes writes for the same section', async () => {
        vi.resetModules()
        vi.doMock('../api/index.js', () => ({
            api: {
                saveConfigSection: vi.fn(),
            },
        }))
        const {api} = await import('../api/index.js')
        const {useConfigSectionSave} = await import('./useConfigSectionSave.js')
        const order = []
        let releaseFirst

        api.saveConfigSection.mockImplementation((section, body) => {
            order.push(body.value)
            if (body.value === 1) {
                return new Promise((resolve) => {
                    releaseFirst = () => resolve({ok: 1})
                })
            }
            return Promise.resolve({ok: 2})
        })

        const {saveSection} = useConfigSectionSave()
        const first = saveSection('playback-libraries', {value: 1})
        const second = saveSection('playback-libraries', {value: 2})

        await Promise.resolve()
        expect(order).toEqual([1])

        releaseFirst()
        await Promise.all([first, second])

        expect(order).toEqual([1, 2])
    })
})
