import {flushPromises, mount} from '@vue/test-utils'
import {createI18n} from 'vue-i18n'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import SalaView from './SalaView.vue'
import esMessages from '../locales/es-ES.json'

const networkScanMock = vi.hoisted(() => ({
    scanning: {__v_isRef: true, value: false},
    devices: {__v_isRef: true, value: []},
    scan: vi.fn(),
}))

const readinessMock = vi.hoisted(() => ({
    patchSetupReadiness: vi.fn(),
}))

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
    useNetworkScan: () => networkScanMock,
}))

vi.mock('../composables/useSetupReadiness.js', () => ({
    patchSetupReadiness: readinessMock.patchSetupReadiness,
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

describe('SalaView Trinnov AV block', () => {
    beforeEach(async () => {
        const {api} = await import('../api/index.js')
        Object.values(api).forEach((mock) => mock.mockReset())
        networkScanMock.devices.value = []
        networkScanMock.scan.mockReset()
        readinessMock.patchSetupReadiness.mockReset()
    })

    it('shows Trinnov MAC and source/profile copy with power actions locked until MAC exists', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                trinnov_mac: '',
                available_hdmi_inputs: [],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
        })

        const wrapper = mountView()
        await flushPromises()

        expect(wrapper.find('#av-mac').exists()).toBe(true)
        expect(wrapper.text()).toContain('Fuente/perfil del reproductor')
        expect(wrapper.text()).toContain('Las acciones de encendido/apagado de Trinnov requieren dirección MAC')
        expect(wrapper.text()).toContain('Trinnov Altitude usa números de fuente/perfil')

        const powerButtons = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .filter((c) => ['Encender', 'Apagar'].includes(c.props('label')))
        expect(powerButtons).toHaveLength(2)
        expect(powerButtons.every((button) => button.props('disabled') === true)).toBe(true)
    })

    it('auto-fills the Trinnov MAC from the network scan for the configured IP', async () => {
        const {api} = await import('../api/index.js')
        networkScanMock.scan.mockImplementation(async () => {
            networkScanMock.devices.value = [
                {ip: '192.168.1.50', mac: 'aa:bb:cc:dd:ee:ff', vendor: 'Trinnov'},
            ]
        })
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                trinnov_mac: '',
                available_hdmi_inputs: [],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
        })

        const wrapper = mountView()
        await flushPromises()

        const detectMacButton = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .find((c) => c.props('label') === 'Detectar MAC')
        expect(detectMacButton).toBeTruthy()

        await detectMacButton.vm.$emit('click')
        await flushPromises()

        expect(wrapper.find('#av-mac').element.value).toBe('aa:bb:cc:dd:ee:ff')
    })

    it('unlocks manual Trinnov MAC entry when network detection fails', async () => {
        const {api} = await import('../api/index.js')
        networkScanMock.scan.mockImplementation(async () => {
            networkScanMock.devices.value = []
        })
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                trinnov_mac: '',
                available_hdmi_inputs: [],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
            arp_available: true,
        })

        const wrapper = mountView()
        await flushPromises()

        const macInputBefore = wrapper.find('#av-mac')
        expect(macInputBefore.element.disabled).toBe(true)

        const detectMacButton = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .find((c) => c.props('label') === 'Detectar MAC')
        await detectMacButton.vm.$emit('click')
        await flushPromises()

        const macInputAfter = wrapper.find('#av-mac')
        expect(macInputAfter.element.disabled).toBe(false)
    })

    it('clears stale detected inputs when switching from Denon to Trinnov', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'DENON',
                ip: '192.168.1.20',
                player_hdmi_input: 'SIBD\n',
                available_hdmi_inputs: [
                    {id: 3, name: 'BD', param: 'SIBD\n'},
                ],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
            config_readiness: {
                av: {status: 'verified', detail: 'DENON · 192.168.1.20'},
            },
        })

        const wrapper = mountView()
        await flushPromises()

        const modelSelect = wrapper.findComponent({name: 'FormSelect'})
        await modelSelect.vm.$emit('update:modelValue', 'TRINNOV')
        await modelSelect.vm.$emit('change')
        await flushPromises()

        const sourceSelects = wrapper
            .findAllComponents({name: 'FormSelect'})
            .filter((component) => component.attributes('id') === 'av-hdmi-input')
        expect(sourceSelects[0].props('options')).toEqual([])
        expect(sourceSelects[0].props('disabled')).toBe(true)
        expect(wrapper.text()).toContain('Conecta con Trinnov usando Detectar entradas')
        expect(readinessMock.patchSetupReadiness).toHaveBeenLastCalledWith(
            'av',
            {status: 'incomplete', detail: 'Source/profile not detected'},
        )
    })

    it('restores AV navbar readiness when switching back to the saved model', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'DENON',
                ip: '192.168.1.20',
                player_hdmi_input: 'SIBD\n',
                available_hdmi_inputs: [
                    {id: 3, name: 'BD', param: 'SIBD\n'},
                ],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
            config_readiness: {
                av: {status: 'verified', detail: 'DENON · 192.168.1.20'},
            },
        })

        const wrapper = mountView()
        await flushPromises()

        const modelSelect = wrapper.findComponent({name: 'FormSelect'})
        await modelSelect.vm.$emit('update:modelValue', 'TRINNOV')
        await modelSelect.vm.$emit('change')
        await flushPromises()

        await modelSelect.vm.$emit('update:modelValue', 'DENON')
        await modelSelect.vm.$emit('change')
        await flushPromises()

        expect(readinessMock.patchSetupReadiness).toHaveBeenLastCalledWith(
            'av',
            {status: 'verified', detail: 'DENON · 192.168.1.20'},
        )
    })

    it('enables Trinnov source selection after sources are detected', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                trinnov_mac: 'aa:bb:cc:dd:ee:ff',
                available_hdmi_inputs: [
                    {id: 2, name: 'Source/profile 2 - OPPO', param: 'profile 2\n'},
                ],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
        })

        const wrapper = mountView()
        await flushPromises()

        const sourceSelect = wrapper
            .findAllComponents({name: 'FormSelect'})
            .find((component) => component.attributes('id') === 'av-hdmi-input')
        expect(sourceSelect.props('disabled')).toBe(false)

        const switchButton = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .find((component) => component.props('label') === 'Cambiar a OPPO')
        expect(switchButton.props('disabled')).toBe(false)
    })

    it('detects Trinnov sources with the edited AV config', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            tv: {enabled: false, model: ''},
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                available_hdmi_inputs: [],
            },
            tv_dirs: ['LG', 'SCRIPTS'],
            av_dirs: ['DENON', 'TRINNOV', 'SCRIPTS'],
        })
        api.getConfig.mockResolvedValueOnce({
            av: {enabled: true, model: 'TRINNOV', ip: '192.168.1.50'},
        })
        api.getAvSources.mockResolvedValueOnce({
            av: {
                enabled: true,
                model: 'TRINNOV',
                ip: '192.168.1.50',
                available_hdmi_inputs: [
                    {id: 2, name: 'Source/profile 2 - OPPO', param: 'profile 2\n'},
                ],
            },
        })

        const wrapper = mountView()
        await flushPromises()

        const detectInputsButton = wrapper
            .findAllComponents({name: 'IconActionButton'})
            .find((c) => c.props('label') === 'Detectar entradas HDMI')
        expect(detectInputsButton).toBeTruthy()

        await detectInputsButton.vm.$emit('click')
        await flushPromises()

        expect(api.getAvSources).toHaveBeenCalledWith(expect.objectContaining({
            av: expect.objectContaining({model: 'TRINNOV', ip: '192.168.1.50'}),
        }))
    })
})

function buttonByText(wrapper, text) {
    const button = wrapper.findAll('button').find((candidate) => candidate.text() === text)
    if (!button) throw new Error(`Button not found: ${text}`)
    return button
}
