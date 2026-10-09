<template>
  <div class="view-content view-ambient home-assistant-view">
    <div :style="{backgroundImage: `url(${heroBg})`}" class="ambient-bg"></div>
    <div :style="{backgroundImage: `url(${heroBg})`}" class="home-assistant-scene-bg"></div>
    <div class="view-body home-assistant-view-body">
      <section class="home-assistant-showcase">
        <h1 class="home-assistant-showcase-title">{{ $t('x-home-assistant-title') }}</h1>
        <p class="home-assistant-showcase-subtitle">{{ $t('x-home-assistant-subtitle') }}</p>
      </section>

      <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

      <template v-else>
        <div class="home-assistant-kicker">
          <span class="s-dot dim"></span>
          <span>{{ $t('x-nav-config-section') }}</span>
        </div>

        <div class="home-assistant-form">
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

              <div class="form-label label-with-help">
                <label for="ha-base-url">{{ $t('x-home-assistant-url') }}</label>
                <HelpTooltip :text="$t('x-home-assistant-tooltip-url')"/>
              </div>
              <input id="ha-base-url" v-model.trim="homeAssistant.base_url"
                     :placeholder="$t('x-home-assistant-url-placeholder')"
                     class="form-input mb-1" type="url">
              <div v-if="homeAssistant.base_url" class="webhook-url-preview mb-4">
                <span class="webhook-url-preview-label">{{ $t('x-home-assistant-webhook-url') }}</span>
                <code>{{ webhookUrlPreview }}</code>
              </div>

              <template v-if="isWebhookConfigured && !changingWebhook">
                <div class="webhook-credential-status">
                  <CheckCircle2 :size="18" :stroke-width="2.2"/>
                  <span class="webhook-credential-label">{{ $t('x-home-assistant-webhook-configured') }}</span>
                  <button class="btn-ghost" @click="changingWebhook = true">
                    {{ $t('x-home-assistant-change-webhook') }}
                  </button>
                </div>
              </template>

              <template v-else>
                <div class="form-label label-with-help">
                  <label for="ha-webhook-id">{{ $t('x-home-assistant-webhook-id') }}</label>
                  <HelpTooltip :text="$t('x-home-assistant-tooltip-webhook-id')"/>
                </div>
                <input id="ha-webhook-id" v-model.trim="homeAssistant.webhook_id" autocomplete="new-password"
                       class="form-input mb-1" type="password">
                <div class="flex gap-2">
                  <button v-if="changingWebhook" class="btn-ghost" @click="cancelWebhookChange">
                    {{ $t('x-common-cancel') }}
                  </button>
                </div>
              </template>
            </div>
          </section>

          <section class="panel mb-4">
            <div class="panel-body">
              <details class="advanced-config home-assistant-advanced-config">
                <summary class="home-assistant-advanced-summary">
                  <SlidersHorizontal :size="13" :stroke-width="2.3"/>
                  <span>{{ $t('x-home-assistant-advanced-toggle') }}</span>
                  <HelpTooltip :text="$t('x-home-assistant-tooltip-options')"/>
                </summary>
                <div class="advanced-config-body">
                  <div class="form-label label-with-help">
                    <label for="ha-timeout">{{ $t('x-home-assistant-timeout') }}</label>
                    <HelpTooltip :text="$t('x-home-assistant-tooltip-timeout')"/>
                  </div>
                  <input id="ha-timeout" v-model.number="homeAssistant.timeout_seconds" class="form-input mb-2"
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
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {RouterLink} from 'vue-router'
import {Cable, CheckCircle2, SlidersHorizontal} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-home-assistant.png'
import {useToast} from '../composables/useToast.js'
import HelpTooltip from '../components/HelpTooltip.vue'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {t} = useI18n()
const toast = useToast()
const {saving, saveSection} = useConfigSectionSave()
const loading = ref(true)
const changingWebhook = ref(false)
const homeAssistant = ref({enabled: false, base_url: '', webhook_id: '', timeout_seconds: 3})

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
  if (isConfigured.value) return {key: 'tested', label: t('x-home-assistant-state-configured')}
  if (homeAssistant.value.enabled) return {key: 'configured', label: t('x-home-assistant-state-incomplete')}
  return {key: 'incomplete', label: t('x-home-assistant-state-disabled')}
})

const connectionAccentClass = computed(() => {
  if (connectionState.value.key === 'tested') return 'panel-accent-ok'
  if (connectionState.value.key === 'configured') return 'panel-accent-info'
  return 'panel-accent-warn'
})

async function saveConfig() {
  try {
    const saved = await saveSection('home_assistant', homeAssistant.value)
    homeAssistant.value = {...homeAssistant.value, ...(saved.home_assistant || {})}
    homeAssistant.value.webhook_id = ''
    changingWebhook.value = false
    toast.success(t('x-common-saved'))
  } catch (error) {
    toast.error(error.message)
  }
}

onMounted(async () => {
  try {
    const config = await api.getConfig()
    homeAssistant.value = {
      ...homeAssistant.value,
      ...(config.home_assistant || {}),
      webhook_id: '',
    }
  } finally {
    loading.value = false
  }
})

function cancelWebhookChange() {
  homeAssistant.value.webhook_id = ''
  changingWebhook.value = false
}
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
  min-height: 116px;
  flex-direction: column;
  justify-content: center;
  margin-bottom: 14px;
}

.home-assistant-showcase-title {
  max-width: 1050px;
  margin: 0;
  color: var(--text-main);
  font-size: clamp(34px, 4.1vw, 62px);
  font-weight: 900;
  line-height: 0.96;
  letter-spacing: 0;
  text-wrap: balance;
  text-shadow: 0 30px 88px rgba(0, 0, 0, 0.62);
}

.home-assistant-showcase-subtitle {
  max-width: 690px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: clamp(15px, 1.15vw, 19px);
  line-height: 1.42;
  text-wrap: balance;
}

.home-assistant-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  gap: 9px;
  padding: 7px 12px;
  margin-bottom: 12px;
  border: 1px solid rgba(255, 255, 255, 0.075);
  border-radius: 999px;
  background: rgba(7, 11, 13, 0.42);
  color: var(--accent-secondary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
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

.home-assistant-form {
  width: min(100%, 840px);
  padding: 14px;
  border: 1px solid rgba(255, 255, 255, 0.085);
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.22));
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.4), inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(7px);
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

@media (max-width: 768px) {
  .home-assistant-view-body {
    padding: 28px 16px 36px;
  }

  .home-assistant-showcase {
    min-height: 150px;
  }

  .home-assistant-showcase-title {
    font-size: clamp(32px, 9vw, 46px);
  }
}
</style>
