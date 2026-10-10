import {flushPromises, mount} from '@vue/test-utils'
import {createI18n} from 'vue-i18n'
import {beforeEach, describe, expect, it, vi} from 'vitest'
import HomeAssistantView from './HomeAssistantView.vue'
import esMessages from '../locales/es-ES.json'

vi.mock('../api/index.js', () => ({
    api: {
        getConfig: vi.fn(),
        saveConfigSection: vi.fn(),
        getHomeAssistantDeliveryStatus: vi.fn(),
    },
}))

function mountView() {
    const i18n = createI18n({
        legacy: false,
        locale: 'es-ES',
        messages: {'es-ES': esMessages},
        missingWarn: false,
        fallbackWarn: false,
    })

    return mount(HomeAssistantView, {
        global: {
            plugins: [i18n],
            stubs: {
                HelpTooltip: true,
                RouterLink: {template: '<a><slot /></a>'},
            },
        },
    })
}

describe('HomeAssistantView connection state', () => {
    beforeEach(async () => {
        const {api} = await import('../api/index.js')
        Object.values(api).forEach((mock) => mock.mockReset())
    })

    it('shows complete configuration without claiming the connection was tested', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: true,
                base_url: 'http://homeassistant.local:8123',
                webhook_id_configured: true,
                timeout_seconds: 3,
            },
        })
        api.getHomeAssistantDeliveryStatus.mockResolvedValueOnce({status: 'pending'})

        const wrapper = mountView()
        await flushPromises()

        const state = wrapper.find('.player-state')
        expect(state.text()).toBe('CONFIGURADO')
        expect(state.classes()).toContain('player-state--configured')
        expect(state.classes()).not.toContain('player-state--tested')
        expect(wrapper.text()).toContain(
            'La configuración está lista. HCC confirmará la entrega con el próximo evento.',
        )
        expect(wrapper.text()).toContain('Pendiente del primer evento')
    })

    it('shows incomplete when Home Assistant is enabled without all credentials', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: true,
                base_url: '',
                webhook_id_configured: false,
                timeout_seconds: 3,
            },
        })

        const wrapper = mountView()
        await flushPromises()

        const state = wrapper.find('.player-state')
        expect(state.text()).toBe('INCOMPLETO')
        expect(state.classes()).toContain('player-state--incomplete')
    })

    it('shows disabled when the integration is turned off', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: false,
                base_url: '',
                webhook_id_configured: false,
                timeout_seconds: 3,
            },
        })

        const wrapper = mountView()
        await flushPromises()

        expect(wrapper.find('.player-state').text()).toBe('DESACTIVADO')
        expect(wrapper.find('.home-assistant-delivery-status').exists()).toBe(false)
        expect(wrapper.text()).toContain('La integración está desactivada. Actívala para editar la conexión o enviar eventos.')
        expect(wrapper.find('#ha-base-url').element.disabled).toBe(true)
        expect(wrapper.find('#ha-webhook-id').element.disabled).toBe(true)
        expect(wrapper.find('#ha-timeout').element.disabled).toBe(true)
    })

    it('keeps the webhook hidden and shows the restart guidance', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: true,
                base_url: 'http://homeassistant.local:8123',
                webhook_id_configured: true,
                timeout_seconds: 3,
            },
        })
        api.getHomeAssistantDeliveryStatus.mockResolvedValueOnce({
            status: 'delivered',
            last_event: 'started',
            last_attempt_at: '2026-10-10T20:15:00Z',
        })

        const wrapper = mountView()
        await flushPromises()

        expect(wrapper.find('#ha-webhook-id').exists()).toBe(false)
        expect(wrapper.text()).toContain('Reiniciar HCC')
        expect(wrapper.text()).toContain('Última entrega correcta')
        expect(wrapper.text()).toContain('Evento reproducción iniciada')
    })

    it('saves the Home Assistant section through the section endpoint', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: true,
                base_url: 'http://homeassistant.local:8123',
                webhook_id_configured: true,
                timeout_seconds: 3,
            },
        })
        api.getHomeAssistantDeliveryStatus.mockResolvedValueOnce({status: 'pending'})
        api.saveConfigSection.mockResolvedValueOnce({
            home_assistant: {
                enabled: true,
                base_url: 'http://homeassistant.local:8123',
                webhook_id_configured: true,
                timeout_seconds: 3,
            },
        })

        const wrapper = mountView()
        await flushPromises()

        await wrapper.findAll('button').find((button) => button.text() === 'Guardar').trigger('click')
        await flushPromises()

        expect(api.saveConfigSection).toHaveBeenCalledWith(
            'home_assistant',
            expect.objectContaining({
                enabled: true,
                base_url: 'http://homeassistant.local:8123',
            }),
        )
    })

    it('shows a retryable error instead of rendering an empty form', async () => {
        const {api} = await import('../api/index.js')
        api.getConfig.mockRejectedValueOnce(new Error('backend unavailable'))

        const wrapper = mountView()
        await flushPromises()

        expect(wrapper.find('[role="alert"]').text()).toContain('No se ha podido cargar Home Assistant')
        expect(wrapper.find('#ha-base-url').exists()).toBe(false)

        api.getConfig.mockResolvedValueOnce({
            home_assistant: {
                enabled: false,
                base_url: '',
                webhook_id_configured: false,
                timeout_seconds: 3,
            },
        })
        await wrapper.find('[role="alert"] button').trigger('click')
        await flushPromises()

        expect(wrapper.find('[role="alert"]').exists()).toBe(false)
        expect(wrapper.find('#ha-base-url').exists()).toBe(true)
    })
})
