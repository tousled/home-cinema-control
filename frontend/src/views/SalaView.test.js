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
        getTvApps: vi.fn(),
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

describe('SalaView Sony TV block', () => {
    beforeEach(async () => {
        const {api} = await import('../api/index.js')
        Object.values(api).forEach((mock) => mock.mockReset())
    })

    it('shows the PSK configured hint but never renders the real secret', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {
                enabled: true,
                model: 'SONY',
                ip: '192.168.1.40',
                sony_psk_configured: true,
                available_hdmi_inputs: [],
            },
            av: {enabled: false, model: ''},
            tv_dirs: ['LG', 'SONY', 'SCRIPTS'],
            av_dirs: ['DENON', 'SCRIPTS'],
        })

        const wrapper = mountView()
        await flushPromises()

        const pskInput = wrapper.find('#tv-psk-sony')
        expect(pskInput.exists()).toBe(true)
        expect(pskInput.element.value).toBe('')
        expect(wrapper.text()).toContain('PSK ya configurada')
    })

    it('detect apps button calls the apps endpoint and merges the response', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {
                enabled: true,
                model: 'SONY',
                ip: '192.168.1.40',
                sony_psk: 'secret-psk',
                available_hdmi_inputs: [],
            },
            av: {enabled: false, model: ''},
            tv_dirs: ['LG', 'SONY', 'SCRIPTS'],
            av_dirs: ['DENON', 'SCRIPTS'],
        })
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: true, model: 'SONY', ip: '192.168.1.40'},
        })
        api.getTvApps.mockResolvedValueOnce({
            tv: {
                enabled: true,
                model: 'SONY',
                ip: '192.168.1.40',
                available_hdmi_inputs: [],
                sony_available_apps: [{title: 'Emby', uri: 'com.sony.dtv.tv.emby.embyatv.MainActivity'}],
            },
        })

        const wrapper = mountView()
        await flushPromises()

        const detectAppsButton = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .find((c) => c.props('label') === 'Detectar apps')
        expect(detectAppsButton).toBeTruthy()

        await detectAppsButton.vm.$emit('click')
        await flushPromises()

        expect(api.getTvApps).toHaveBeenCalled()
    })
})

function buttonByText(wrapper, text) {
    const button = wrapper.findAll('button').find((candidate) => candidate.text() === text)
    if (!button) throw new Error(`Button not found: ${text}`)
    return button
}
