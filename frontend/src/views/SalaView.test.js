import {flushPromises, mount} from '@vue/test-utils'
import {createI18n} from 'vue-i18n'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import SalaView from './SalaView.vue'
import esMessages from '../locales/es-ES.json'

vi.mock('../api/index.js', () => ({
    api: {
        getConfig: vi.fn(),
        saveConfigSection: vi.fn(),
        testTvConnection: vi.fn(),
        getTvSources: vi.fn(),
        tvSwitchInput: vi.fn(),
        tvRestoreInput: vi.fn(),
        getAvSources: vi.fn(),
        avPowerOn: vi.fn(),
        avPowerOff: vi.fn(),
        avSwitchInput: vi.fn(),
        discoverDevices: vi.fn(),
    },
}))

vi.mock('../composables/useNetworkScan.js', () => ({
    useNetworkScan: () => ({
        scanning: {value: false},
        devices: {value: []},
        scan: vi.fn(),
    }),
}))

function mountView() {
    const i18n = createI18n({
        legacy: false,
        locale: 'es-ES',
        messages: {'es-ES': esMessages},
        missingWarn: false,
        fallbackWarn: false,
    })

    return mount(SalaView, {
        global: {
            plugins: [i18n],
            stubs: {
                StepNav: true,
                HelpTooltip: {
                    template: '<span><slot /></span>',
                },
                IpInput: true,
                IconActionButton: true,
                FormSelect: true,
            },
        },
    })
}

describe('SalaView section saves', () => {
    beforeEach(async () => {
        const {api} = await import('../api/index.js')
        Object.values(api).forEach((mock) => mock.mockReset())
    })

    it('persists disabled TV through the TV section endpoint', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: '', ip: '192.168.1.20'},
            av: {enabled: false, model: '', ip: '192.168.1.30'},
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'SCRIPTS'],
        })
        api.saveConfigSection.mockResolvedValueOnce({
            tv: {enabled: false, model: '', ip: '192.168.1.20'},
        })

        const wrapper = mountView()
        await flushPromises()

        await buttonByText(wrapper, 'Guardar TV').trigger('click')
        await flushPromises()

        expect(api.saveConfigSection).toHaveBeenCalledWith(
            'tv',
            expect.objectContaining({enabled: false}),
        )
        expect(api.saveConfig).toBeUndefined()
    })

    it('persists disabled AV through the AV section endpoint', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: '', ip: '192.168.1.20'},
            av: {enabled: false, model: '', ip: '192.168.1.30'},
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'SCRIPTS'],
        })
        api.saveConfigSection.mockResolvedValueOnce({
            av: {enabled: false, model: '', ip: '192.168.1.30'},
        })

        const wrapper = mountView()
        await flushPromises()

        await buttonByText(wrapper, 'Guardar receptor AV').trigger('click')
        await flushPromises()

        expect(api.saveConfigSection).toHaveBeenCalledWith(
            'av',
            expect.objectContaining({enabled: false}),
        )
        expect(api.saveConfig).toBeUndefined()
    })
})

function buttonByText(wrapper, text) {
    const button = wrapper.findAll('button').find((candidate) => candidate.text() === text)
    if (!button) throw new Error(`Button not found: ${text}`)
    return button
}
