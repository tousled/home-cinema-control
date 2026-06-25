<template>
  <div class="view-content view-ambient status-view">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="status-scene-bg"></div>

    <div class="view-body status-view-body">
    <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <section class="status-showcase">
        <h1 class="status-title">{{ $t('x-diag-title') }}</h1>
        <p class="status-subtitle">{{ $t('x-diag-subtitle') }}</p>
      </section>

      <div class="status-kicker">
        <span :class="stateDotClass" class="s-dot"></span>
        <span>{{ $t('x-nav-support-section') }}</span>
      </div>
      <div class="status-grid">
        <!-- Left column -->
        <div>
      <!-- Playback state -->
          <div :class="playbackAccentClass" class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title">
                <Activity :size="13" :stroke-width="2.3"/>
                {{ $t('x-nav-status') }}
              </h2>
            </div>
        <div class="panel-body">
          <div class="flex items-center gap-3 mb-3">
            <span :class="stateDotClass" class="s-dot"></span>
            <span style="font-size:14px;font-weight:600;color:var(--text-main)">{{ playstateLabel }}</span>
          </div>
          <template v-if="state.ActiveSession?.title">
            <div class="session-with-poster">
              <div class="session-left">
                <img v-if="posterSrc && !posterError" :src="posterSrc" alt="" class="session-poster"
                     @error="posterError = true"/>
                <div class="flex gap-2 mt-2">
                  <button class="btn-ghost" @click="sendKey('STP')">■ Stop</button>
                  <button class="btn-ghost" @click="sendKey('PLA')">▶ Play</button>
                  <button class="btn-ghost" @click="sendKey('PAU')">⏸ Pause</button>
                </div>
              </div>
              <div class="session-info">
                <div class="detail-row">
                  <span class="detail-label">{{ $t('x-status-label-title') }}</span>
                  <span class="detail-value">{{ state.ActiveSession.title }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ $t('x-status-label-server') }}</span>
                  <span class="detail-value">{{ state.ActiveSession.content_server }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ $t('x-status-label-directory') }}</span>
                  <span class="detail-value mono" style="font-size:11px">{{
                      state.ActiveSession.content_directory
                    }}</span>
                </div>
                <div class="detail-row">
                  <span class="detail-label">{{ $t('x-status-label-file') }}</span>
                  <span class="detail-value mono" style="font-size:11px">{{
                      state.ActiveSession.playback_file_name
                    }}</span>
                </div>
              </div>
            </div>
          </template>
        </div>
      </div>

      <!-- Last failure diagnostic -->
          <div :class="failureAccentClass" class="panel mb-3">
        <div class="panel-head">
          <h2 class="panel-title">
            <ShieldAlert :size="13" :stroke-width="2.3"/>
            {{ $t('x-diag-section-last-failure') }}
          </h2>
          <div class="flex gap-2">
            <IconActionButton :label="$t('x-diag-copy-summary')" icon="copy" @click="copySupportSummary"/>
            <IconActionButton
                v-if="state.LastDiagnostic"
                :label="$t('x-diag-clear')"
                icon="clear"
                @click="clearDiagnostic"
            />
          </div>
        </div>
        <div class="panel-body">
          <template v-if="state.LastDiagnostic">
            <div :style="{ borderColor: diagColor(state.LastDiagnostic.severity), background: diagBg(state.LastDiagnostic.severity) }"
                 class="diag-badge mb-3">
              <span class="diag-code">{{ state.LastDiagnostic.code }}</span>
              <span class="diag-component">{{ state.LastDiagnostic.component }}</span>
            </div>
            <dl class="space-y-2" style="font-size:12px">
              <div>
                <dt style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-subtle);margin-bottom:2px">
                  {{ $t('x-diag-reason') }}
                </dt>
                <dd style="color:var(--text-muted)">{{ diagnosticReason(state.LastDiagnostic) }}</dd>
              </div>
              <div>
                <dt style="font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-subtle);margin-bottom:2px">
                  {{ $t('x-diag-suggestion') }}
                </dt>
                <dd style="color:var(--text-muted)">{{ diagnosticSuggestion(state.LastDiagnostic) }}</dd>
              </div>
            </dl>
          </template>
          <p v-else class="caption">{{ $t('x-diag-none') }}</p>

          <div v-if="state.DiagnosticHistory?.length" class="diag-history">
            <div class="diag-history-title">{{ $t('x-diag-history') }}</div>
            <ul>
              <li v-for="diag in state.DiagnosticHistory" :key="`${diag.code}-${diag.timestamp}`">
                <span class="diag-history-code">{{ diag.code }}</span>
                <span class="diag-history-component">{{ diag.component }}</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
        </div><!-- /left column -->

        <!-- Right column -->
        <div>
      <!-- Resources -->
          <div :class="resourcesAccentClass" class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title">
                <Cpu :size="13" :stroke-width="2.3"/>
                {{ $t('x-status-resources') }}
              </h2>
            </div>
        <div class="panel-body">
          <div class="mb-4">
            <div class="flex justify-between mb-1">
              <span class="metric-label">CPU</span>
              <span class="mono metric-value">{{ state.cpu_perc }}%</span>
            </div>
            <div class="meter">
              <div :class="barMeterClass(state.cpu_perc)" :style="{width: state.cpu_perc+'%'}" class="meter-fill"></div>
            </div>
          </div>
          <div>
            <div class="flex justify-between mb-1">
              <span class="metric-label">RAM</span>
              <span class="mono metric-value">{{ state.mem_perc }}%</span>
            </div>
            <div class="meter">
              <div :class="barMeterClass(state.mem_perc)" :style="{width: state.mem_perc+'%'}" class="meter-fill"></div>
            </div>
          </div>
        </div>
      </div>

      <!-- Version -->
          <div :class="versionAccentClass" class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title">
                <PackageCheck :size="13" :stroke-width="2.3"/>
                {{ $t('x-status-section-version') }}
              </h2>
            </div>
        <div class="panel-body">
          <div v-if="versionLoading" class="caption">{{
              $t('x-status-checking-version')
            }}
          </div>
          <template v-else>
            <dl class="space-y-1 mb-3" style="font-size:12px;color:var(--text-muted)">
              <div class="flex gap-2">
                <dt style="color:var(--text-subtle)">{{ $t('x-status-installed-version') }}</dt>
                <dd class="mono">{{ versionInfo?.current_version || state.Version || '—' }}</dd>
              </div>
              <div class="flex gap-2">
                <dt style="color:var(--text-subtle)">{{ $t('x-status-available-version') }}</dt>
                <dd class="mono">{{ versionInfo?.version || '—' }}</dd>
              </div>
            </dl>
            <p v-if="versionInfo?.new_version" style="font-size:12px;color:var(--status-warning);margin-bottom:8px">
              {{ $t('x-status-new-version', {version: versionInfo.version}) }}
            </p>
            <p v-else-if="!versionInfo?.error" style="font-size:12px;color:var(--status-success);margin-bottom:8px">
              {{ $t('x-status-up-to-date') }}
            </p>
            <p v-if="versionInfo?.error" style="font-size:12px;color:var(--status-danger);margin-bottom:8px">
              {{ $t('x-status-version-error', {error: versionInfo.error}) }}
            </p>
            <div class="icon-action-row mb-3" style="margin-top:0">
              <a
                  v-if="versionInfo?.release_url"
                  :href="versionInfo.release_url"
                  class="btn-ghost"
                  target="_blank"
              >{{ $t('x-status-view-release') }}</a>
              <IconActionButton :label="$t('x-status-check-version')" icon="refresh" @click="checkVersion"/>
              <IconActionButton
                  v-if="versionInfo?.new_version"
                  :disabled="updateLoading"
                  :label="updateLoading ? $t('x-common-loading') : $t('x-status-update')"
                  icon="download"
                  @click="triggerUpdate"
              />
            </div>

            <!-- Update result -->
            <div v-if="updateResult" class="update-result mb-3">
              <template v-if="updateResult.success">
                <p style="font-size:12px;color:var(--status-success)">{{ $t('x-status-update-triggered') }}</p>
              </template>
              <template v-else-if="updateResult.instructions">
                <p style="font-size:12px;color:var(--text-muted);margin-bottom:6px">
                  {{ $t('x-status-update-instructions-note') }}
                </p>
                <code class="update-cmd">{{ updateResult.instructions }}</code>
              </template>
              <template v-else-if="updateResult.error">
                <p style="font-size:12px;color:var(--status-danger)">
                  {{ $t('x-status-update-error', {error: updateResult.error}) }}
                </p>
              </template>
            </div>

            <!-- Rollback info -->
            <div v-if="versionStore.rollbackInfo?.available" class="update-result mb-3">
              <p style="font-size:12px;color:var(--text-muted);margin-bottom:6px">
                {{ $t('x-status-rollback-note', {version: versionStore.rollbackInfo.previous_version}) }}
              </p>
              <code class="update-cmd">{{ versionStore.rollbackInfo.instructions }}</code>
            </div>

            <!-- Webhook URL -->
            <div class="mb-3">
              <div class="flex items-center gap-2 mb-1">
                <label
                    style="font-size:11px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:var(--text-subtle)">
                  {{ $t('x-status-webhook-url-label') }}
                </label>
                <HelpTooltip :text="$t('x-status-tooltip-webhook-url')"/>
              </div>
              <div class="flex gap-2">
                <input
                    v-model="webhookUrl"
                    :placeholder="$t('x-status-webhook-url-placeholder')"
                    class="form-input"
                    style="font-size:12px;flex:1"
                    type="url"
                />
                <button :disabled="webhookSaving" class="btn-ghost" style="font-size:12px;white-space:nowrap"
                        @click="saveWebhookUrl">
                  {{ webhookSaving ? $t('x-common-loading') : $t('x-common-save') }}
                </button>
              </div>
            </div>

            <div class="flex items-center gap-2">
              <label class="flex items-center gap-2" style="cursor:pointer">
                <input
                    :checked="includePrerelease"
                    type="checkbox"
                    @change="onTogglePrerelease($event.target.checked)"
                />
                <span style="font-size:12px;color:var(--text-muted)">{{ $t('x-status-include-prerelease') }}</span>
              </label>
              <HelpTooltip :text="$t('x-status-tooltip-include-prerelease')"/>
            </div>
          </template>
        </div>
      </div>
        </div><!-- /right column -->
      </div><!-- /status-grid -->

      <!-- Actions -->
      <div class="icon-action-row" style="margin-top:16px">
        <IconActionButton :label="$t('x-status-refresh')" icon="refresh" @click="refreshState"/>
        <button :disabled="restarting" class="btn-service-action" @click="restartService">
          {{ restarting ? $t('x-status-restarting') : $t('x-status-restart') }}
        </button>
      </div>

    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {Activity, Cpu, PackageCheck, ShieldAlert} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-status.png'
import {useToast} from '../composables/useToast.js'
import {usePoll} from '../composables/usePoll.js'
import HelpTooltip from '../components/HelpTooltip.vue'
import IconActionButton from '../components/IconActionButton.vue'
import {useVersionStore} from '../stores/version.js'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'
import {useDiagnosticText} from '../composables/useDiagnosticText.js'

const {t} = useI18n()
const toast = useToast()
const versionStore = useVersionStore()
const {saveSection} = useConfigSectionSave()
const {diagnosticReason, diagnosticSuggestion} = useDiagnosticText()

const state = ref({})
const loading = ref(true)
const versionInfo = ref(null)
const versionLoading = ref(false)
const includePrerelease = ref(false)
const restarting = ref(false)
const posterError = ref(false)
const updateLoading = ref(false)
const updateResult = ref(null)
const webhookUrl = ref('')
const webhookSaving = ref(false)
const fullConfig = ref({})
const posterSrc = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  if (!itemId) {
    posterError.value = false;
    return null
  }
  return `/api/now-playing/poster?item=${itemId}`
})

usePoll(refreshState, 10000)

const playstateLabel = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return t('x-status-not-connected')
  if (ps === 'Free') return t('x-status-free')
  if (ps === 'Loading') return t('x-status-loading')
  if (ps === 'Playing') return t('x-status-playing')
  if (ps === 'Replay') return t('x-status-replay')
  return ps || '—'
})

const stateDotClass = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return 'err'
  if (ps === 'Playing') return 'ok pulse'
  if (ps === 'Loading') return 'warn pulse'
  return 'dim'
})

const playbackAccentClass = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return 'panel-accent-err'
  if (ps === 'Playing') return 'panel-accent-ok'
  if (ps === 'Loading') return 'panel-accent-warn'
  return 'panel-accent-dim'
})

const failureAccentClass = computed(() => {
  const severity = state.value.LastDiagnostic?.severity
  if (severity === 'error') return 'panel-accent-err'
  if (severity === 'warning') return 'panel-accent-warn'
  return 'panel-accent-dim'
})

function barMeterClass(pct) {
  if (pct < 50) return 'meter-ok'
  if (pct < 85) return 'meter-warn'
  return 'meter-err'
}

const resourcesAccentClass = computed(() => {
  const worst = Math.max(state.value.cpu_perc || 0, state.value.mem_perc || 0)
  if (worst >= 85) return 'panel-accent-err'
  if (worst >= 50) return 'panel-accent-warn'
  return 'panel-accent-ok'
})

function diagColor(severity) {
  if (severity === 'error') return 'var(--status-danger)'
  if (severity === 'warning') return 'var(--status-warning)'
  return 'var(--accent-primary)'
}

const versionAccentClass = computed(() => {
  if (versionInfo.value?.error) return 'panel-accent-err'
  if (versionInfo.value?.new_version) return 'panel-accent-warn'
  return 'panel-accent-ok'
})

function diagBg(severity) {
  if (severity === 'error') return 'rgba(255,92,122,0.06)'
  if (severity === 'warning') return 'rgba(245,165,36,0.06)'
  return 'rgba(47,128,237,0.06)'
}

async function clearDiagnostic() {
  try {
    await api.clearDiagnostics()
  } catch {/* ignore */
  }
  state.value = {...state.value, LastDiagnostic: null}
}

async function copySupportSummary() {
  try {
    const summary = await api.getSupportSummary()
    const text = JSON.stringify(summary, null, 2)
    await navigator.clipboard.writeText(text)
    toast.success(t('x-diag-summary-copied'))
  } catch (e) {
    toast.error(e.message || t('x-diag-summary-copy-error'))
  }
}

async function refreshState() {
  try {
    state.value = await api.getState()
  } catch {/* ignore */
  }
}

async function checkVersion() {
  versionLoading.value = true
  try {
    versionInfo.value = await api.checkVersion(includePrerelease.value)
    versionStore.setVersionInfo(versionInfo.value)
  } catch (e) {
    versionInfo.value = {error: e.message}
  } finally {
    versionLoading.value = false
  }
}

async function triggerUpdate() {
  updateLoading.value = true
  updateResult.value = null
  try {
    updateResult.value = await api.updateVersion()
  } catch (e) {
    updateResult.value = {success: false, webhook_configured: false, error: e.message}
  } finally {
    updateLoading.value = false
  }
}

async function onTogglePrerelease(checked) {
  includePrerelease.value = checked
  try {
    fullConfig.value.app = {
      ...(fullConfig.value.app || {}),
      include_prerelease: checked,
    }
    fullConfig.value = await saveSection('app', fullConfig.value.app)
  } catch (e) {
    includePrerelease.value = !checked
    toast.error(e.message)
    return
  }
  await checkVersion()
}

async function saveWebhookUrl() {
  webhookSaving.value = true
  try {
    fullConfig.value.app = {
      ...(fullConfig.value.app || {}),
      update_webhook_url: webhookUrl.value.trim(),
    }
    fullConfig.value = await saveSection('app', fullConfig.value.app)
    toast.success(t('x-status-webhook-saved'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    webhookSaving.value = false
  }
}

async function restartService() {
  restarting.value = true
  try {
    await api.restart()
    toast.success(t('x-status-restarted'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    restarting.value = false
  }
}

async function sendKey(key) {
  try {
    await api.sendKey(key)
  } catch {/* ignore */
  }
}

onMounted(async () => {
  loading.value = true
  try {
    state.value = await api.getState()
    try {
      const data = await api.getConfig()
      fullConfig.value = data
      webhookUrl.value = data.app?.update_webhook_url || ''
      includePrerelease.value = data.app?.include_prerelease || false
    } catch { /* non-fatal */
    }
    await checkVersion()
    await versionStore.loadRollbackInfo()
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.status-view {
  position: relative;
  min-height: 100dvh;
}

.status-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.97;
  filter: saturate(1.2) contrast(1.04) brightness(1.12) sepia(0.08) hue-rotate(-5deg);
}

.status-scene-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 26%, rgba(80, 122, 142, 0.18), transparent 34%),
  radial-gradient(circle at 78% 18%, rgba(245, 165, 36, 0.18), transparent 34%),
  radial-gradient(circle at 12% 8%, rgba(194, 161, 107, 0.13), transparent 32%);
}

.status-scene-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(8, 16, 20, 0.6), rgba(32, 56, 68, 0.12) 46%, rgba(8, 16, 20, 0.34)),
  linear-gradient(180deg, rgba(35, 61, 74, 0.08), rgba(8, 16, 20, 0.18) 52%, rgba(6, 13, 17, 0.68));
}

.status-view-body {
  position: relative;
  z-index: 1;
  padding: clamp(40px, 7vh, 78px) clamp(22px, 5vw, 76px) clamp(28px, 5vh, 54px);
}

.status-kicker {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  gap: 9px;
  padding: 7px 12px;
  border-radius: 999px;
  background: rgba(7, 11, 13, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.075);
  color: var(--accent-secondary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
  margin-bottom: 12px;
}

.status-title {
  max-width: 1050px;
  margin: 0;
  color: var(--text-main);
  font-size: clamp(40px, 5vw, 78px);
  font-weight: 900;
  line-height: 0.96;
  letter-spacing: 0;
  text-wrap: balance;
  text-shadow: 0 30px 88px rgba(0, 0, 0, 0.62);
}

.status-subtitle {
  max-width: 690px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: clamp(17px, 1.4vw, 23px);
  line-height: 1.42;
  text-wrap: balance;
}

.status-showcase {
  display: flex;
  min-height: clamp(150px, 24dvh, 260px);
  flex-direction: column;
  justify-content: center;
  margin-bottom: clamp(16px, 2.2vh, 26px);
}

.session-with-poster {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.session-left {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}

.session-poster {
  width: 100px;
  border-radius: 6px;
  box-shadow: 0 6px 20px rgba(0, 0, 0, 0.55);
  display: block;
}

@media (max-width: 640px) {
  .session-with-poster {
    flex-direction: column;
    gap: 12px;
  }

  .session-left {
    flex-direction: row;
    align-items: center;
    gap: 12px;
  }

  .session-poster {
    width: 64px;
  }
}

.session-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.detail-row {
  display: flex;
  gap: 8px;
  font-size: 12px;
  color: var(--text-muted);
  min-width: 0;
}

.detail-label {
  font-weight: 600;
  color: var(--text-subtle);
  min-width: 5.5em;
  flex-shrink: 0;
  white-space: nowrap;
}

.detail-value {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.status-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
  align-items: start;
  width: min(100%, 1320px);
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.22));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.4),
  inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(7px);
}

.status-grid > div {
  min-width: 0;
}

@media (max-width: 760px) {
  .status-grid {
    grid-template-columns: 1fr;
  }
}

.diag-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 5px 10px;
  border: 1px solid;
  border-radius: 5px;
}

.diag-code {
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 600;
  color: var(--text-main);
}

.diag-component {
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: var(--text-subtle);
}

.diag-history {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.diag-history-title {
  margin-bottom: 8px;
  color: var(--text-subtle);
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.diag-history ul {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin: 0;
  padding: 0;
  list-style: none;
}

.diag-history li {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--text-muted);
  font-size: 11px;
}

.diag-history-code {
  font-family: var(--mono);
  color: var(--text-main);
}

.diag-history-component {
  color: var(--text-subtle);
  text-transform: uppercase;
}

.update-result {
  padding: 10px 12px;
  border-radius: 6px;
  border: 1px solid rgba(255, 255, 255, 0.07);
  background: rgba(255, 255, 255, 0.03);
}

.update-cmd {
  display: block;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--accent-secondary);
  word-break: break-all;
  margin-top: 4px;
}
</style>
