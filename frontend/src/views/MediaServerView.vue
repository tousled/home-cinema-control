<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-nav-config-section') }}</div>
      <h1 class="view-hero-title">{{ $t('x-media-server-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-media-server-subtitle') }}</div>
    </div>

    <div class="view-body">
    <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <div class="media-server-grid">
        <div class="media-server-main">
          <!-- Connection -->
          <div class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title label-with-help">
                {{ $t('x-media-server-section-connection') }}
                <HelpTooltip :text="$t('x-media-server-tooltip-connection')"/>
              </h2>
            </div>
            <div class="panel-body">
              <div class="form-label label-with-help">
                <label for="ms-url">{{ $t('x-media-server-url') }}</label>
                <HelpTooltip :text="$t('x-media-server-tooltip-url')"/>
              </div>
              <input
                  id="ms-url"
                  v-model="config.media_server.server_url"
                  class="form-input mb-3"
                  placeholder="http://192.168.1.x:8096"
                  type="text"
              />
            </div>
          </div>

          <!-- Auth -->
          <div class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title label-with-help">
                {{ $t('x-media-server-section-auth') }}
                <HelpTooltip :text="$t('x-media-server-tooltip-auth')"/>
              </h2>
            </div>
            <div class="panel-body">

              <!-- Token active: show status + change-password button -->
              <template v-if="config.media_server.access_token_configured && !changingPassword">
                <div class="token-status mb-3">
                  <span class="token-status-icon">✓</span>
                  <div>
                    <div class="token-status-label">{{ $t('x-media-server-token-active') }}</div>
                    <div class="token-status-user">{{ $t('x-media-server-user') }}: {{
                        config.media_server.display_name
                      }}
                    </div>
                  </div>
                </div>
                <button class="btn-ghost" @click="changingPassword = true">
                  {{ $t('x-media-server-change-password') }}
                </button>
              </template>

              <!-- No token or changing password: show credential form -->
              <template v-else>
                <label class="form-label" for="ms-user">{{ $t('x-media-server-user') }}</label>
                <input id="ms-user" v-model="login.user_name" autocomplete="username" class="form-input mb-3"
                       type="text"/>

                <div class="pw-label-row mb-1">
                  <label class="form-label" for="ms-password" style="margin-bottom:0">{{
                      $t('x-media-server-password')
                    }}</label>
                  <HelpTooltip :text="$t('x-media-server-password-hint')"/>
                </div>
                <input
                    id="ms-password"
                    v-model="login.password"
                    :placeholder="$t('x-media-server-password-placeholder')"
                    autocomplete="current-password"
                    class="form-input mb-4"
                    type="password"
                />

                <div class="flex gap-2">
                  <button :disabled="!canGetToken || tokenLoading" class="btn-ghost" @click="getToken">
                    {{ tokenLoading ? $t('x-media-server-getting-token') : $t('x-media-server-get-token') }}
                  </button>
                  <button v-if="changingPassword" class="btn-ghost" @click="cancelChangePassword">
                    {{ $t('x-common-cancel') }}
                  </button>
                </div>
              </template>
            </div>
          </div>

          <!-- Monitored device -->
          <div class="panel mb-3">
            <div class="panel-head">
              <h2 class="panel-title label-with-help">
                {{ $t('x-media-server-section-device') }}
                <HelpTooltip :text="$t('x-media-server-tooltip-device')"/>
              </h2>
            </div>
            <div class="panel-body">
              <p class="section-hint">{{ $t('x-media-server-device-hint') }}</p>
              <div v-if="loadingDevices" class="text-xs" style="color:var(--text-muted)">
                {{ $t('x-media-server-loading-devices') }}
              </div>
              <template v-else>
                <FormSelect
                    v-model="config.playback.hcc_controlled_device"
                    :options="devices.map(d => ({ value: d.Id, label: d.Name }))"
                    class="mb-3"
                />
                <HelpTooltip :text="$t('x-media-server-tooltip-reload-devices')">
                  <IconActionButton
                      :label="$t('x-media-server-reload-devices')"
                      :loading="loadingDevices"
                      :loading-label="$t('x-media-server-loading-devices')"
                      icon="refresh"
                      @click="loadDevices"
                  />
                </HelpTooltip>
              </template>
            </div>
          </div>

          <div class="flex gap-3 flex-wrap">
            <button :disabled="checkLoading" class="btn-ghost" @click="checkEmby">
              {{ checkLoading ? $t('x-common-testing') : $t('x-media-server-test-connection') }}
            </button>
            <button class="btn-ghost" @click="saveConfig">{{ $t('x-common-save') }}</button>
          </div>
          <p class="section-hint mt-2">{{ $t('x-media-server-test-apply-hint') }}</p>
        </div>

        <!-- Library paths readiness -->
        <aside v-if="config.media_server.access_token_configured" class="media-server-side">
          <div class="panel">
            <div class="panel-head">
              <h2 class="panel-title label-with-help">
                {{ $t('x-media-server-section-library-paths') }}
                <HelpTooltip :text="$t('x-media-server-tooltip-library-paths')"/>
              </h2>
            </div>
            <div class="panel-body">
              <div v-if="loadingLibraryPaths" class="text-xs" style="color:var(--text-muted)">
                {{ $t('x-media-server-loading-library-paths') }}
              </div>

              <div v-else-if="libraryPathsError" class="library-warning">
                <AlertTriangle :size="17" :stroke-width="2"/>
                <div>
                  <p class="library-warning-title">{{ $t('x-media-server-library-paths-error') }}</p>
                  <p class="library-warning-copy">{{ libraryPathsError }}</p>
                </div>
              </div>

              <div v-else-if="!libraryPaths.length" class="library-warning">
                <AlertTriangle :size="17" :stroke-width="2"/>
                <div>
                  <p class="library-warning-title">{{ $t('x-media-server-no-library-paths-title') }}</p>
                  <p class="library-warning-copy">
                    {{ $t('x-media-server-no-library-paths-copy', {type: mediaServerTypeLabel}) }}
                  </p>
                </div>
              </div>

              <div v-else class="library-path-list">
                <div v-for="lib in libraryPaths" :key="`${lib.library_name}:${lib.source_path}`"
                     class="library-path-row">
                  <CheckCircle :size="16" :stroke-width="2.3"/>
                  <div>
                    <p class="library-path-name">{{ lib.library_name }}</p>
                    <p class="library-path-value mono">{{ lib.source_path }}</p>
                  </div>
                </div>
              </div>

              <IconActionButton
                  :label="$t('x-media-server-refresh-library-paths')"
                  :loading="loadingLibraryPaths"
                  :loading-label="$t('x-media-server-loading-library-paths')"
                  class="mt-3"
                  icon="refresh"
                  @click="loadLibraryPaths"
              />
            </div>
          </div>
        </aside>
      </div>

      <StepNav :current-step="1"/>
    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {AlertTriangle, CheckCircle} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-media-server.png'
import {useToast} from '../composables/useToast.js'
import StepNav from '../components/StepNav.vue'
import HelpTooltip from '../components/HelpTooltip.vue'
import IconActionButton from '../components/IconActionButton.vue'
import FormSelect from '../components/FormSelect.vue'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {t} = useI18n()
const toast = useToast()
const {saveSection} = useConfigSectionSave()

const loading = ref(true)
const loadingDevices = ref(false)
const loadingLibraryPaths = ref(false)
const tokenLoading = ref(false)
const checkLoading = ref(false)
const changingPassword = ref(false)

const config = ref({
  media_server: {server_url: '', type: 'emby'},
  playback: {hcc_controlled_device: '', use_all_libraries: true},
})
const login = ref({user_name: '', password: ''})
const devices = ref([])
const libraryPaths = ref([])
const libraryPathsError = ref('')

const canGetToken = computed(() =>
    !!(config.value.media_server?.server_url && login.value.user_name && login.value.password),
)

const mediaServerTypeLabel = computed(() => {
  const type = config.value.media_server?.type || 'emby'
  return type.charAt(0).toUpperCase() + type.slice(1)
})

function cancelChangePassword() {
  changingPassword.value = false
  login.value.password = ''
}

async function loadDevices() {
  loadingDevices.value = true
  try {
    const full = await api.getConfigWithDevices()
    devices.value = full.devices || []
    if (!config.value.playback) config.value.playback = {}
    config.value.playback.hcc_controlled_device =
        full.playback?.hcc_controlled_device || config.value.playback.hcc_controlled_device
  } catch {
    devices.value = []
  } finally {
    loadingDevices.value = false
  }
}

async function loadLibraryPaths() {
  loadingLibraryPaths.value = true
  libraryPathsError.value = ''
  try {
    libraryPaths.value = await api.getLibraryPaths()
  } catch (e) {
    libraryPaths.value = []
    libraryPathsError.value = e.message
  } finally {
    loadingLibraryPaths.value = false
  }
}

async function getToken() {
  tokenLoading.value = true
  try {
    const updated = await api.configureEmbyToken(await configWithServerSetup(), {
      user_name: login.value.user_name,
      password: login.value.password,
    })
    config.value = updated
    login.value.password = ''
    changingPassword.value = false
    toast.success(t('x-media-server-token-ok'))
    await Promise.all([loadDevices(), loadLibraryPaths()])
  } catch (e) {
    toast.error(e.message)
  } finally {
    tokenLoading.value = false
  }
}

async function checkEmby() {
  checkLoading.value = true
  try {
    const updated = await api.checkEmby(await configWithServerSetup())
    config.value = updated
    toast.success(t('x-media-server-connection-ok'))
    await Promise.all([loadDevices(), loadLibraryPaths()])
  } catch (e) {
    toast.error(e.message)
  } finally {
    checkLoading.value = false
  }
}

async function saveConfig() {
  try {
    config.value = await saveSection('media-server', serverSetupSection())
    toast.success(t('x-common-saved'))
  } catch (e) {
    toast.error(e.message)
  }
}

function serverSetupSection() {
  return {
    media_server: config.value.media_server || {},
    playback: {
      hcc_controlled_device: config.value.playback?.hcc_controlled_device || '',
    },
  }
}

async function configWithServerSetup() {
  const latest = await api.getConfig()
  return {
    ...latest,
    media_server: {
      ...(latest.media_server || {}),
      ...(config.value.media_server || {}),
    },
    playback: {
      ...(latest.playback || {}),
      hcc_controlled_device: config.value.playback?.hcc_controlled_device || '',
    },
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await api.getConfig()
    config.value = data
    if (!config.value.media_server) config.value.media_server = {type: 'emby'}
    if (!config.value.playback) config.value.playback = {}
    login.value.user_name = data.media_server?.display_name || ''
    if (data.media_server?.access_token_configured) {
      await Promise.all([loadDevices(), loadLibraryPaths()])
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.media-server-grid {
  display: grid;
  grid-template-columns: minmax(480px, 1fr) minmax(360px, 0.8fr);
  gap: 18px;
  align-items: start;
  max-width: 1180px;
}

.media-server-main,
.media-server-side {
  min-width: 0;
}

@media (max-width: 900px) {
  .media-server-grid {
    grid-template-columns: 1fr;
  }
}

.token-status {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 12px;
  background: rgba(39, 174, 96, 0.07);
  border: 1px solid rgba(39, 174, 96, 0.18);
  border-radius: 7px;
}

.token-status-icon {
  font-size: 13px;
  font-weight: 800;
  color: var(--status-success);
  flex-shrink: 0;
}

.token-status-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-main);
  line-height: 1.3;
}

.token-status-user {
  font-size: 11px;
  color: var(--text-muted);
}

.pw-label-row {
  display: flex;
  align-items: center;
  gap: 6px;
}

.library-warning {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 11px 12px;
  border: 1px solid rgba(245, 165, 36, 0.22);
  border-radius: 8px;
  background: rgba(245, 165, 36, 0.07);
}

.library-warning svg {
  color: var(--status-warning);
  flex-shrink: 0;
  margin-top: 1px;
}

.library-warning-title {
  color: var(--text-main);
  font-size: 13px;
  font-weight: 750;
  margin: 0 0 3px;
}

.library-warning-copy {
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
  margin: 0;
}

.library-path-list {
  display: grid;
  gap: 8px;
}

.library-path-row {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 10px 12px;
  border: 1px solid rgba(55, 230, 138, 0.14);
  border-radius: 8px;
  background: rgba(55, 230, 138, 0.055);
}

.library-path-row svg {
  color: var(--status-success);
  flex-shrink: 0;
  margin-top: 2px;
}

.library-path-name {
  color: var(--text-main);
  font-size: 13px;
  font-weight: 750;
  margin: 0 0 3px;
}

.library-path-value {
  color: var(--text-muted);
  font-size: 11px;
  overflow-wrap: anywhere;
  margin: 0;
}

.mono {
  font-family: var(--mono);
}
</style>
