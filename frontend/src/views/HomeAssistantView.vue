<template>
  <div class="view-content view-ambient home-assistant-view">
    <div :style="{backgroundImage: `url(${heroBg})`}" class="ambient-bg"></div>
    <div :style="{backgroundImage: `url(${heroBg})`}" class="home-assistant-scene-bg"></div>
    <div class="view-body home-assistant-view-body">
      <section class="home-assistant-showcase">
        <div class="home-assistant-showcase-copy">
          <div class="home-assistant-showcase-eyebrow">
            <span class="s-dot dim"></span>
            <span>{{ $t('x-home-assistant-eyebrow') }}</span>
          </div>
          <h1 class="home-assistant-showcase-title">{{ $t('x-home-assistant-title') }}</h1>
          <p class="home-assistant-showcase-subtitle">{{ $t('x-home-assistant-subtitle') }}</p>
        </div>
      </section>

      <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

      <div v-else-if="loadError" aria-live="assertive" class="home-assistant-load-error" role="alert">
        <h2>{{ $t('x-home-assistant-load-error-title') }}</h2>
        <p>{{ $t('x-home-assistant-load-error-hint') }}</p>
        <button :disabled="loading" class="btn-ghost" @click="loadConfig">
          {{ $t('x-home-assistant-load-error-retry') }}
        </button>
      </div>

      <template v-else>
        <div :class="{'home-assistant-layout--configured': isConfigured}" class="home-assistant-layout">
          <main class="home-assistant-main">
            <section :class="connectionAccentClass" class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title label-with-help">
                <Cable :size="13" :stroke-width="2.3"/>
                {{ $t('x-home-assistant-section-connection') }}
                <HelpTooltip :text="$t('x-home-assistant-tooltip-connection')"/>
              </h2>
              <span :class="['player-state', `player-state--${connectionState.key}`]">
                {{ connectionState.label }}
              </span>
            </div>

            <div class="panel-body">
              <div class="flex items-center gap-2 mb-4">
                <label class="flex items-center gap-2" style="cursor:pointer">
                  <input v-model="homeAssistant.enabled" type="checkbox">
                  <span class="body-text">{{ $t('x-home-assistant-enabled') }}</span>
                </label>
                <HelpTooltip :text="$t('x-home-assistant-tooltip-enabled')"/>
              </div>
              <p v-if="!homeAssistant.enabled" class="section-hint home-assistant-disabled-hint" role="status">
                {{ $t('x-home-assistant-disabled-hint') }}
              </p>

              <fieldset :disabled="!homeAssistant.enabled" class="home-assistant-config-fields">
                <p v-if="isConfigured" class="section-hint home-assistant-connection-hint">
                  {{ $t('x-home-assistant-connection-hint') }}
                </p>

                <div class="form-label label-with-help">
                  <label for="ha-base-url">{{ $t('x-home-assistant-url') }}</label>
                  <HelpTooltip :text="$t('x-home-assistant-tooltip-url')"/>
                </div>
                <input id="ha-base-url" v-model.trim="homeAssistant.base_url"
                       :disabled="!homeAssistant.enabled"
                       :placeholder="$t('x-home-assistant-url-placeholder')"
                       class="form-input mb-1" type="url">
                <div v-if="homeAssistant.base_url" class="webhook-url-preview home-assistant-webhook-preview mb-4">
                  <span class="webhook-url-preview-label">{{ $t('x-home-assistant-webhook-url') }}</span>
                  <code>{{ webhookUrlPreview }}</code>
                </div>

                <template v-if="isWebhookConfigured && !changingWebhook">
                  <div class="webhook-credential-status">
                    <CheckCircle2 :size="18" :stroke-width="2.2"/>
                    <span class="webhook-credential-label">{{ $t('x-home-assistant-webhook-configured') }}</span>
                    <button :disabled="!homeAssistant.enabled" class="btn-ghost" @click="changingWebhook = true">
                      {{ $t('x-home-assistant-change-webhook') }}
                    </button>
                  </div>
                </template>

                <template v-else>
                  <div class="form-label label-with-help">
                    <label for="ha-webhook-id">{{ $t('x-home-assistant-webhook-id') }}</label>
                    <HelpTooltip :text="$t('x-home-assistant-tooltip-webhook-id')"/>
                  </div>
                  <input id="ha-webhook-id" v-model.trim="homeAssistant.webhook_id" :disabled="!homeAssistant.enabled"
                         autocomplete="new-password"
                         class="form-input mb-1" type="password">
                  <div class="flex gap-2">
                    <button v-if="changingWebhook" class="btn-ghost" @click="cancelWebhookChange">
                      {{ $t('x-common-cancel') }}
                    </button>
                  </div>
                </template>
              </fieldset>
            </div>
            </section>

            <section class="panel mb-4">
              <div class="panel-body">
                <details :class="{'home-assistant-advanced-config--disabled': !homeAssistant.enabled}"
                         class="advanced-config home-assistant-advanced-config">
                  <summary
                      :aria-disabled="!homeAssistant.enabled"
                      class="home-assistant-advanced-summary"
                      @click="!homeAssistant.enabled && $event.preventDefault()"
                  >
                    <SlidersHorizontal :size="13" :stroke-width="2.3"/>
                    <span>{{ $t('x-home-assistant-advanced-toggle') }}</span>
                    <HelpTooltip :text="$t('x-home-assistant-tooltip-options')"/>
                  </summary>
                  <div class="advanced-config-body">
                    <div class="form-label label-with-help">
                      <label for="ha-timeout">{{ $t('x-home-assistant-timeout') }}</label>
                      <HelpTooltip :text="$t('x-home-assistant-tooltip-timeout')"/>
                    </div>
                    <input id="ha-timeout" v-model.number="homeAssistant.timeout_seconds"
                           :disabled="!homeAssistant.enabled" class="form-input mb-2"
                           max="30" min="1" step="0.5" type="number">
                    <p class="section-hint">{{ $t('x-home-assistant-timeout-hint') }}</p>
                  </div>
                </details>
              </div>
            </section>

            <div class="flex gap-3 flex-wrap">
              <button :disabled="saving" class="btn-ghost" @click="saveConfig">
                {{ saving ? $t('x-common-saving') : $t('x-common-save') }}
              </button>
            </div>
            <p class="section-hint mt-2">
              {{ $t('x-home-assistant-restart-hint') }}
              <RouterLink class="home-assistant-restart-link" to="/status#restart-service-button">
                {{ $t('x-home-assistant-restart-link') }}
              </RouterLink>
            </p>
          </main>

          <aside v-if="isConfigured" class="home-assistant-aside">
            <section class="panel home-assistant-status-panel">
              <div class="panel-head">
                <h2 class="panel-title label-with-help">
                  <Cable :size="13" :stroke-width="2.3"/>
                  {{ $t('x-home-assistant-delivery-title') }}
                </h2>
              </div>
              <div class="panel-body">
                <div aria-live="polite" class="home-assistant-delivery-status">
                  <div class="home-assistant-delivery-status-head">
                    <span :class="['s-dot', `home-assistant-delivery-dot--${deliveryState.key}`]"></span>
                    <span class="home-assistant-delivery-status-label">{{ deliveryState.label }}</span>
                  </div>
                  <p class="section-hint">{{ deliveryState.hint }}</p>
                  <p v-if="lastDeliverySummary" class="home-assistant-delivery-last">
                    {{ lastDeliverySummary }}
                  </p>
                </div>
              </div>
            </section>
          </aside>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {RouterLink} from 'vue-router'
import {Cable, CheckCircle2, SlidersHorizontal} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-home-assistant.png'
import {useToast} from '../composables/useToast.js'
import {usePoll} from '../composables/usePoll.js'
import HelpTooltip from '../components/HelpTooltip.vue'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {locale, t} = useI18n()
const toast = useToast()
const {saving, saveSection} = useConfigSectionSave()
const loading = ref(true)
const loadError = ref(false)
const changingWebhook = ref(false)
const homeAssistant = ref({enabled: false, base_url: '', webhook_id: '', timeout_seconds: 3})
const deliveryStatus = ref(null)

watch(() => homeAssistant.value.enabled, (enabled) => {
  if (!enabled) changingWebhook.value = false
})

const isWebhookConfigured = computed(() => Boolean(
    homeAssistant.value.webhook_id || homeAssistant.value.webhook_id_configured
))

const isConfigured = computed(() => Boolean(
    homeAssistant.value.enabled
    && homeAssistant.value.base_url
    && (homeAssistant.value.webhook_id || homeAssistant.value.webhook_id_configured)
))

const webhookUrlPreview = computed(() => {
  const baseUrl = String(homeAssistant.value.base_url || '').trim().replace(/\/+$/, '')
  return `${baseUrl || 'http://homeassistant.local:8123'}/api/webhook/********`
})

const connectionState = computed(() => {
  if (!homeAssistant.value.enabled) return {key: 'disabled', label: t('x-home-assistant-state-disabled')}
  if (isConfigured.value) return {key: 'configured', label: t('x-home-assistant-state-configured')}
  return {key: 'incomplete', label: t('x-home-assistant-state-incomplete')}
})

const connectionAccentClass = computed(() => {
  if (connectionState.value.key === 'configured') return 'panel-accent-info'
  return 'panel-accent-warn'
})

const deliveryState = computed(() => {
  const status = deliveryStatus.value?.status
  if (status === 'delivered') {
    return {
      key: 'ok',
      label: t('x-home-assistant-delivery-delivered'),
      hint: t('x-home-assistant-delivery-delivered-hint'),
    }
  }
  if (status === 'failed') {
    return {
      key: 'failed',
      label: t('x-home-assistant-delivery-failed'),
      hint: t('x-home-assistant-delivery-failed-hint'),
    }
  }
  return {
    key: 'pending',
    label: t('x-home-assistant-delivery-pending'),
    hint: t('x-home-assistant-delivery-pending-hint'),
  }
})

const lastDeliverySummary = computed(() => {
  const status = deliveryStatus.value
  if (!status?.last_event || !status.last_attempt_at) return ''
  return t('x-home-assistant-delivery-last', {
    event: formatDeliveryEvent(status.last_event),
    at: formatDeliveryTime(status.last_attempt_at),
    detail: status.detail ? ` · ${status.detail}` : '',
  })
})

async function refreshDeliveryStatus() {
  if (!isConfigured.value) {
    deliveryStatus.value = null
    return
  }
  try {
    deliveryStatus.value = await api.getHomeAssistantDeliveryStatus()
  } catch {
    // Delivery status is diagnostic context; it must not make configuration unusable.
  }
}

async function saveConfig() {
  try {
    const saved = await saveSection('home_assistant', homeAssistant.value)
    homeAssistant.value = {...homeAssistant.value, ...(saved.home_assistant || {})}
    homeAssistant.value.webhook_id = ''
    changingWebhook.value = false
    deliveryStatus.value = null
    toast.success(t('x-common-saved'))
  } catch (error) {
    toast.error(error.message)
  }
}

async function loadConfig() {
  loading.value = true
  loadError.value = false
  try {
    const config = await api.getConfig()
    homeAssistant.value = {
      ...homeAssistant.value,
      ...(config.home_assistant || {}),
      webhook_id: '',
    }
    await refreshDeliveryStatus()
  } catch {
    loadError.value = true
    deliveryStatus.value = null
  } finally {
    loading.value = false
  }
}

onMounted(loadConfig)

function cancelWebhookChange() {
  homeAssistant.value.webhook_id = ''
  changingWebhook.value = false
}

function formatDeliveryEvent(value) {
  const key = `x-home-assistant-event-${value}`
  const translated = t(key)
  return translated === key ? value : translated
}

function formatDeliveryTime(value) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return value
  return new Intl.DateTimeFormat(locale.value, {
    dateStyle: 'short',
    timeStyle: 'short',
  }).format(date)
}

usePoll(refreshDeliveryStatus, 10000)
</script>

<style scoped>
.home-assistant-view {
  position: relative;
  min-height: 100dvh;
}

.home-assistant-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.97;
  filter: saturate(1.08) contrast(1.04) brightness(0.86);
}

.home-assistant-scene-bg::before {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 26%, rgba(80, 122, 142, 0.18), transparent 34%),
  radial-gradient(circle at 78% 18%, rgba(245, 165, 36, 0.14), transparent 34%);
  content: '';
}

.home-assistant-scene-bg::after {
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(8, 16, 20, 0.72), rgba(8, 16, 20, 0.28) 48%, rgba(8, 16, 20, 0.66)),
  linear-gradient(180deg, rgba(8, 16, 20, 0.24), rgba(8, 16, 20, 0.72));
  content: '';
}

.home-assistant-view-body {
  position: relative;
  z-index: 1;
  padding: clamp(40px, 7vh, 78px) clamp(22px, 5vw, 76px) clamp(28px, 5vh, 54px);
}

.home-assistant-showcase {
  display: flex;
  min-height: 164px;
  flex-direction: column;
  justify-content: center;
  margin-bottom: 20px;
}

.home-assistant-showcase-copy {
  max-width: 700px;
}

.home-assistant-showcase-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  margin-bottom: 14px;
  color: var(--accent-secondary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  line-height: 1;
  text-transform: uppercase;
}

.home-assistant-showcase-title {
  max-width: 1050px;
  margin: 0;
  color: var(--text-main);
  font-size: 56px;
  font-weight: 900;
  line-height: 1;
  letter-spacing: 0;
  text-wrap: balance;
  text-shadow: 0 30px 88px rgba(0, 0, 0, 0.62);
}

.home-assistant-showcase-subtitle {
  max-width: 690px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: 17px;
  line-height: 1.42;
  text-wrap: balance;
}

.home-assistant-layout {
  display: grid;
  width: min(100%, 840px);
  gap: 18px;
}

.home-assistant-layout--configured {
  grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
  width: min(100%, 1180px);
  align-items: start;
}

.home-assistant-main,
.home-assistant-aside {
  min-width: 0;
}

.home-assistant-status-panel {
  position: sticky;
  top: 24px;
}

.home-assistant-config-fields {
  min-inline-size: 0;
  margin: 0;
  padding: 0;
  border: 0;
}

.home-assistant-config-fields:disabled .home-assistant-webhook-preview,
.home-assistant-config-fields:disabled .webhook-credential-status {
  opacity: 0.52;
}

.home-assistant-disabled-hint {
  max-width: 520px;
  color: var(--text-muted);
}

.webhook-credential-status {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
  min-height: 42px;
  margin-top: 14px;
  padding: 9px 10px;
  border: 1px solid rgba(97, 217, 139, 0.18);
  border-radius: 7px;
  background: rgba(97, 217, 139, 0.06);
  color: var(--status-success);
}

.webhook-credential-label {
  flex: 1;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 700;
}

.webhook-credential-status .btn-ghost {
  min-height: 30px;
  padding: 5px 9px;
  font-size: 12px;
}

.home-assistant-delivery-status {
  padding-top: 2px;
}

.home-assistant-load-error {
  width: min(100%, 640px);
  padding: 18px;
  border: 1px solid rgba(220, 80, 80, 0.35);
  border-radius: 7px;
  background: rgba(120, 35, 35, 0.14);
}

.home-assistant-load-error h2 {
  margin: 0 0 6px;
  color: var(--text-main);
  font-size: 15px;
}

.home-assistant-load-error p {
  margin: 0 0 14px;
  color: var(--text-muted);
}

.home-assistant-delivery-status-head {
  display: flex;
  align-items: center;
  gap: 8px;
}

.home-assistant-delivery-status-label {
  color: var(--text-main);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.home-assistant-delivery-dot--ok {
  background: var(--status-success);
}

.home-assistant-delivery-dot--pending {
  background: var(--text-subtle);
}

.home-assistant-delivery-dot--failed {
  background: var(--status-danger);
}

.home-assistant-delivery-status .section-hint {
  margin-bottom: 0;
}

.home-assistant-delivery-last {
  padding-top: 10px;
  margin: 10px 0 0;
  border-top: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--text-subtle);
  font-family: var(--mono);
  font-size: 11px;
}

.player-state {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 22px;
  padding: 3px 7px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  background: rgba(255, 255, 255, 0.035);
  color: var(--text-subtle);
  font-size: 9px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.player-state--tested {
  border-color: rgba(55, 230, 138, 0.18);
  background: rgba(55, 230, 138, 0.08);
  color: var(--status-success);
}

.player-state--configured {
  border-color: rgba(48, 213, 200, 0.16);
  background: rgba(48, 213, 200, 0.07);
  color: var(--status-info);
}

.player-state--incomplete {
  border-color: rgba(245, 165, 36, 0.24);
  background: rgba(245, 165, 36, 0.08);
  color: var(--status-warning);
}

.webhook-url-preview {
  display: grid;
  gap: 5px;
  max-width: 620px;
  padding: 10px 12px;
  border-left: 2px solid var(--accent-secondary);
  background: rgba(194, 161, 107, 0.06);
}

.webhook-url-preview-label {
  color: var(--text-subtle);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.webhook-url-preview code {
  overflow-wrap: anywhere;
  color: var(--text-muted);
  font-family: var(--mono);
  font-size: 12px;
}

.home-assistant-restart-link {
  display: inline-block;
  margin-left: 5px;
  color: var(--accent-secondary);
  font-weight: 700;
  text-decoration: underline;
  text-underline-offset: 3px;
}

.home-assistant-advanced-config {
  max-width: none;
  border-top: 0;
  padding-top: 0;
}

.home-assistant-advanced-summary {
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.home-assistant-advanced-config--disabled .home-assistant-advanced-summary {
  color: var(--text-subtle);
  cursor: not-allowed;
}

@media (max-width: 768px) {
  .home-assistant-view-body {
    padding: 28px 16px 36px;
  }

  .home-assistant-showcase {
    min-height: 150px;
  }

  .home-assistant-showcase-title {
    font-size: 36px;
  }

  .home-assistant-showcase-subtitle {
    font-size: 15px;
  }

  .home-assistant-layout,
  .home-assistant-layout--configured {
    grid-template-columns: 1fr;
    width: 100%;
  }

  .home-assistant-status-panel {
    position: static;
  }
}
</style>
