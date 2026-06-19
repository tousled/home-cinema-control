<template>
  <div class="view-content view-ambient sala-view">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="sala-scene-bg"></div>

    <div class="view-body sala-view-body">
      <section class="sala-showcase">
        <h1 class="sala-showcase-title">{{ $t('x-sala-title') }}</h1>
        <p class="sala-showcase-subtitle">{{ $t('x-sala-subtitle') }} {{ $t('x-sala-summary-title') }}</p>
        <div class="sala-showcase-actions">
          <HelpTooltip v-if="arpAvailable" :text="$t('x-network-tooltip-scan')">
            <IconActionButton
                :label="$t('x-network-scan')"
                :loading="scanning"
                :loading-label="$t('x-network-scanning')"
                icon="network"
                @click="scan"
            />
          </HelpTooltip>
          <span v-if="devices.length" class="caption">
            {{ devices.length }} {{ $t('x-network-scan-found') }}
          </span>
        </div>
      </section>

      <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

      <template v-else>
        <div class="sala-kicker">
          <span class="s-dot dim"></span>
          <span>{{ $t('x-nav-config-section') }}</span>
        </div>
        <div class="sala-shell">
        <div class="sala-grid">
          <!-- TV section -->
          <section :class="roomAccentClass(tvState)" class="panel room-device-card">
            <div class="panel-head room-card-head">
              <div>
                <h2 class="panel-title label-with-help">
                  <Tv :size="13" :stroke-width="2.3"/>
                  {{ $t('x-tv-title') }}
                  <HelpTooltip :text="$t('x-tv-tooltip-section')"/>
                </h2>
                <p class="room-card-sub">{{ $t('x-tv-card-subtitle') }}</p>
              </div>
              <div class="room-card-controls">
                <span :class="['room-state', roomStateClass(tvState)]">{{ roomStateLabel(tvState) }}</span>
                <button
                    :aria-label="$t('x-tv-title')"
                    :aria-pressed="tv.enabled"
                    :class="['toggle-switch', tv.enabled && 'on']"
                    @click="tv.enabled = !tv.enabled"
                >
                  <div class="toggle-thumb"></div>
                </button>
              </div>
            </div>
            <div v-if="tv.enabled" class="panel-body">
              <div class="form-label label-with-help">
                <label for="tv-model">{{ $t('x-tv-model') }}</label>
                <HelpTooltip :text="$t('x-tv-tooltip-model')"/>
              </div>
              <FormSelect
                  id="tv-model"
                  v-model="tv.model"
                  :options="tvModels.map(m => ({ value: m, label: m }))"
                  class="mb-4"
              />

                <template v-if="tv.model === 'LG'">
                  <label class="form-label" for="tv-ip">{{ $t('x-tv-ip') }}</label>
                  <IpInput id="tv-ip" v-model="tv.ip" :devices="devices" class="mb-4"/>

                  <button :disabled="tvTestLoading" class="btn-ghost mb-4" @click="testTvConnection">
                    {{ tvTestLoading ? $t('x-common-testing') : $t('x-tv-test-connection') }}
                  </button>

                  <label class="form-label" for="tv-mac">{{ $t('x-tv-mac') }}</label>
                  <input id="tv-mac" v-model="tv.mac" :disabled="arpAvailable" class="form-input mb-1" type="text"/>
                  <p class="section-hint">{{ tv.mac ? $t('x-tv-mac-detected') : $t('x-tv-mac-pending') }}</p>
                  <p v-if="!arpAvailable" class="section-hint" style="color:var(--status-warning)">
                    {{ $t('x-tv-mac-linux-only') }}</p>

                  <div class="form-label label-with-help">
                    <label for="tv-hdmi-input">{{ $t('x-tv-hdmi-input') }}</label>
                    <HelpTooltip :text="$t('x-tv-tooltip-hdmi-input')"/>
                  </div>
                  <FormSelect
                      id="tv-hdmi-input"
                      v-model="selectedTvSourceIndex"
                      :options="tv.available_hdmi_inputs.map((src, i) => ({ value: i, label: src.nombre || src.name || src.id }))"
                      class="mb-3"
                  />

                  <div class="icon-action-row">
                    <HelpTooltip :text="$t('x-tv-action-detect-inputs-tooltip')">
                      <IconActionButton
                          :label="$t('x-tv-action-detect-inputs')"
                          :loading="tvSourcesLoading"
                          :loading-label="$t('x-tv-detecting-inputs')"
                          icon="scan"
                          @click="getTvSources"
                      />
                    </HelpTooltip>
                    <HelpTooltip :text="$t('x-tv-action-switch-player-tooltip')">
                      <IconActionButton
                          :label="$t('x-tv-action-switch-player')"
                          icon="player"
                          @click="tvSwitchInput"
                      />
                    </HelpTooltip>
                    <HelpTooltip
                        :text="$t('x-tv-action-restore-media-server-tooltip', {server: mediaServerBrand.label})">
                      <IconActionButton
                          :brand="mediaServerBrand.brand"
                          :label="$t('x-tv-action-restore-media-server', {server: mediaServerBrand.label})"
                          icon="server"
                          @click="tvRestoreInput"
                      />
                    </HelpTooltip>
                  </div>
                </template>

                <template v-if="tv.model === 'SCRIPTS'">
                  <label class="form-label" for="tv-startup-script">{{ $t('x-tv-startup-script') }}</label>
                  <input id="tv-startup-script" v-model="tv.startup_script" class="form-input mb-3" type="text"/>
                  <button class="btn-ghost mb-4" @click="tvSwitchInput">{{ $t('x-tv-test-startup-script') }}</button>

                  <label class="form-label" for="tv-shutdown-script">{{ $t('x-tv-shutdown-script') }}</label>
                  <input id="tv-shutdown-script" v-model="tv.shutdown_script" class="form-input mb-3" type="text"/>
                  <button class="btn-ghost mb-2" @click="tvRestoreInput">{{ $t('x-tv-test-shutdown-script') }}</button>
                </template>

              <div class="room-card-actions">
                <button class="btn-ghost" @click="saveTv">{{ $t('x-tv-save') }}</button>
              </div>
            </div>
            <div v-else class="panel-body room-disabled-body">
              <p>{{ $t('x-tv-disabled-copy') }}</p>
              <button class="btn-ghost" @click="saveTv">{{ $t('x-tv-save') }}</button>
            </div>
          </section>

          <!-- AV section -->
          <section :class="roomAccentClass(avState)" class="panel room-device-card">
            <div class="panel-head room-card-head">
              <div>
                <h2 class="panel-title label-with-help">
                  <Speaker :size="13" :stroke-width="2.3"/>
                  {{ $t('x-av-title') }}
                  <HelpTooltip :text="$t('x-av-tooltip-section')"/>
                </h2>
                <p class="room-card-sub">{{ $t('x-av-card-subtitle') }}</p>
              </div>
              <div class="room-card-controls">
                <span :class="['room-state', roomStateClass(avState)]">{{ roomStateLabel(avState) }}</span>
                <button
                    :aria-label="$t('x-av-title')"
                    :aria-pressed="av.enabled"
                    :class="['toggle-switch', av.enabled && 'on']"
                    @click="av.enabled = !av.enabled"
                >
                  <div class="toggle-thumb"></div>
                </button>
              </div>
            </div>
            <div v-if="av.enabled" class="panel-body">
              <div class="form-label label-with-help">
                <label for="av-model">{{ $t('x-av-model') }}</label>
                <HelpTooltip :text="$t('x-av-tooltip-model')"/>
              </div>
              <FormSelect
                  id="av-model"
                  v-model="av.model"
                  :options="avModels.map(m => ({ value: m, label: m }))"
                  class="mb-4"
                  @change="onAvModelChange"
              />

              <div class="form-label label-with-help">
                <label for="av-hdmi-delay">{{ $t('x-av-hdmi-delay') }}</label>
                <HelpTooltip :text="$t('x-av-tooltip-hdmi-delay')"/>
              </div>
              <input id="av-hdmi-delay" v-model.number="av.hdmi_switch_delay_seconds" class="form-input mb-3" step="0.5"
                     type="number"/>

              <div class="flex items-center gap-2 mb-4">
                <label class="flex items-center gap-2" style="cursor:pointer">
                  <input v-model="av.always_on" type="checkbox"/>
                  <span class="body-text">{{ $t('x-av-always-on') }}</span>
                </label>
                <HelpTooltip :text="$t('x-av-tooltip-always-on')"/>
              </div>

                <template v-if="av.model !== 'SCRIPTS'">
                  <label class="form-label" for="av-ip">{{ $t('x-av-ip') }}</label>
                  <IpInput id="av-ip" v-model="av.ip" :devices="devices" class="mb-4"/>

                  <div class="icon-action-row mb-4">
                    <HelpTooltip :text="$t('x-av-action-power-on-tooltip')">
                      <IconActionButton
                          :label="$t('x-av-action-power-on')"
                          :loading="avPowerOnLoading"
                          :loading-label="$t('x-common-testing')"
                          icon="powerOn"
                          @click="testAvPowerOn"
                      />
                    </HelpTooltip>
                    <HelpTooltip :text="$t('x-av-action-power-off-tooltip')">
                      <IconActionButton
                          :label="$t('x-av-action-power-off')"
                          :loading="avPowerOffLoading"
                          :loading-label="$t('x-common-testing')"
                          icon="powerOff"
                          @click="testAvPowerOff"
                      />
                    </HelpTooltip>
                  </div>

                  <div class="form-label label-with-help">
                    <label for="av-hdmi-input">{{ $t('x-av-hdmi-input') }}</label>
                    <HelpTooltip :text="$t('x-av-tooltip-hdmi-input')"/>
                  </div>
                  <FormSelect
                      id="av-hdmi-input"
                      v-model="selectedAvSource"
                      :options="av.available_hdmi_inputs.map(src => ({ value: src.Param, label: src.Name }))"
                      class="mb-3"
                      @change="onAvSourceChange"
                  />

                  <div class="icon-action-row">
                    <HelpTooltip :text="$t('x-av-action-detect-inputs-tooltip')">
                      <IconActionButton
                          :label="$t('x-av-action-detect-inputs')"
                          :loading="avSourcesLoading"
                          :loading-label="$t('x-av-detecting-inputs')"
                          icon="scan"
                          @click="getAvSources"
                      />
                    </HelpTooltip>
                    <HelpTooltip :text="$t('x-av-action-test-player-input-tooltip')">
                      <IconActionButton
                          :label="$t('x-av-action-test-player-input')"
                          :loading="avHdmiLoading"
                          :loading-label="$t('x-common-testing')"
                          icon="player"
                          @click="testAvHdmi"
                      />
                    </HelpTooltip>
                  </div>
                </template>

                <template v-if="av.model === 'SCRIPTS'">
                  <label class="form-label" for="av-power-on-script">{{ $t('x-av-power-on-script') }}</label>
                  <input id="av-power-on-script" v-model="av.power_on_command" class="form-input mb-3" type="text"/>
                  <button class="btn-ghost mb-4" @click="testAvPowerOn">{{ $t('x-av-test-power-on') }}</button>

                  <label class="form-label" for="av-hdmi-script">{{ $t('x-av-hdmi-script') }}</label>
                  <input id="av-hdmi-script" v-model="av.hdmi_input_command" class="form-input mb-3" type="text"/>
                  <button class="btn-ghost mb-4" @click="testAvHdmi">{{ $t('x-av-test-hdmi-switch') }}</button>

                  <label class="form-label" for="av-power-off-script">{{ $t('x-av-power-off-script') }}</label>
                  <input id="av-power-off-script" v-model="av.power_off_command" class="form-input mb-3" type="text"/>
                  <button class="btn-ghost mb-2" @click="testAvPowerOff">{{ $t('x-av-test-power-off') }}</button>
                </template>

              <div class="room-card-actions">
                <button class="btn-ghost" @click="saveAv">{{ $t('x-av-save') }}</button>
              </div>
            </div>
            <div v-else class="panel-body room-disabled-body">
              <p>{{ $t('x-av-disabled-copy') }}</p>
              <button class="btn-ghost" @click="saveAv">{{ $t('x-av-save') }}</button>
            </div>
          </section>

          <aside class="room-help-column">
            <div class="room-help-card">
              <p class="room-help-title">
                <Info :size="13" :stroke-width="2.3"/>
                {{ $t('x-sala-help-title') }}
              </p>
              <ol class="room-help-list">
                <li>{{ $t('x-sala-help-step-tv') }}</li>
                <li>{{ $t('x-sala-help-step-av') }}</li>
                <li>{{ $t('x-sala-help-step-save') }}</li>
              </ol>
            </div>
          </aside>
        </div>
      </div>

      <StepNav :current-step="4"/>
    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {Info, Speaker, Tv} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-sala.png'
import {useToast} from '../composables/useToast.js'
import StepNav from '../components/StepNav.vue'
import HelpTooltip from '../components/HelpTooltip.vue'
import IpInput from '../components/IpInput.vue'
import IconActionButton from '../components/IconActionButton.vue'
import FormSelect from '../components/FormSelect.vue'
import {useNetworkScan} from '../composables/useNetworkScan.js'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {t} = useI18n()
const toast = useToast()
const {saveSection} = useConfigSectionSave()

const loading = ref(true)
const fullConfig = ref({})
const arpAvailable = ref(true)
const {scanning, devices, scan} = useNetworkScan()

const mediaServerBrand = computed(() => {
  const type = (fullConfig.value?.media_server?.type || 'emby').toLowerCase()
  if (type === 'jellyfin') return {brand: 'jellyfin', label: 'Jellyfin'}
  if (type === 'plex') return {brand: 'plex', label: 'Plex'}
  if (type === 'emby') return {brand: 'emby', label: 'Emby'}
  return {brand: '', label: t('x-media-server-generic')}
})

/* TV state */
const tv = ref({})
const tvModels = ref([])
const selectedTvSourceIndex = ref(0)
const tvTestLoading = ref(false)
const tvSourcesLoading = ref(false)
const tvTested = ref(false)

const tvState = computed(() => {
  if (!tv.value.enabled) return 'disabled'
  if (!tv.value.model) return 'incomplete'
  if (tv.value.model === 'LG' && !tv.value.ip) return 'incomplete'
  if (tv.value.model === 'SCRIPTS' && !tv.value.startup_script) return 'incomplete'
  return tvTested.value ? 'tested' : 'configured'
})

watch(selectedTvSourceIndex, (i) => {
  tv.value.player_hdmi_input_id = i
})

watch(
    () => [tv.value.enabled, tv.value.model, tv.value.ip, tv.value.startup_script].join('|'),
    () => {
      tvTested.value = false
    },
)

function roomStateLabel(state) {
  return t(`x-room-state-${state}`)
}

function roomStateClass(state) {
  return `room-state--${state}`
}

const ROOM_ACCENT_BY_STATE = {
  tested: 'panel-accent-ok',
  configured: 'panel-accent-info',
  incomplete: 'panel-accent-warn',
  disabled: 'panel-accent-dim',
}

function roomAccentClass(state) {
  return ROOM_ACCENT_BY_STATE[state] || 'panel-accent-dim'
}

async function configWithSection(section, value) {
  const latest = await api.getConfig()
  const nextConfig = {
    ...latest,
    [section]: {...value},
  }
  fullConfig.value = nextConfig
  return nextConfig
}

async function saveConfigSection(section, value) {
  const savedConfig = await saveSection(section, value)
  fullConfig.value = savedConfig
  return savedConfig
}

async function testTvConnection() {
  tvTestLoading.value = true
  try {
    const result = await api.testTvConnection(await configWithSection('tv', tv.value))
    if (result?.tv) {
      tv.value = {...result.tv}
      selectedTvSourceIndex.value = tv.value.player_hdmi_input_id || 0
    }
    tvTested.value = true
    toast.success(t('x-tv-connection-ok'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    tvTestLoading.value = false
  }
}

async function getTvSources() {
  tvSourcesLoading.value = true
  try {
    const updated = await api.getTvSources(await configWithSection('tv', tv.value))
    tv.value = {...(updated.tv || {})}
    fullConfig.value = updated
    selectedTvSourceIndex.value = tv.value.player_hdmi_input_id || 0
    toast.success(t('x-tv-inputs-detected'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    tvSourcesLoading.value = false
  }
}

async function tvSwitchInput() {
  try {
    await api.tvSwitchInput(await configWithSection('tv', tv.value))
    tvTested.value = true
    toast.success(t('x-tv-input-switched'))
  } catch (e) {
    toast.error(e.message)
  }
}

async function tvRestoreInput() {
  try {
    await api.tvRestoreInput(await configWithSection('tv', tv.value))
    tvTested.value = true
    toast.success(t('x-tv-input-restored'))
  } catch (e) {
    toast.error(e.message)
  }
}

async function saveTv() {
  try {
    await saveConfigSection('tv', tv.value)
    toast.success(t('x-common-saved'))
  } catch (e) {
    toast.error(e.message)
  }
}

/* AV state */
const av = ref({})
const avModels = ref([])
const selectedAvSource = ref('')
const avPowerOnLoading = ref(false)
const avPowerOffLoading = ref(false)
const avSourcesLoading = ref(false)
const avHdmiLoading = ref(false)
const avTested = ref(false)

const avState = computed(() => {
  if (!av.value.enabled) return 'disabled'
  if (!av.value.model) return 'incomplete'
  if (av.value.model === 'SCRIPTS' && !av.value.power_on_command) return 'incomplete'
  if (av.value.model !== 'SCRIPTS' && !av.value.ip) return 'incomplete'
  return avTested.value ? 'tested' : 'configured'
})

watch(
    () => [av.value.enabled, av.value.model, av.value.ip, av.value.power_on_command, av.value.hdmi_input_command].join('|'),
    () => {
      avTested.value = false
    },
)

function onAvSourceChange() {
  av.value.player_hdmi_input = selectedAvSource.value
}

function onAvModelChange() {
  selectedAvSource.value = ''
  av.value.player_hdmi_input = ''
}

async function testAvPowerOn() {
  avPowerOnLoading.value = true
  try {
    await api.avPowerOn(await configWithSection('av', av.value))
    avTested.value = true
    toast.success(t('x-av-power-on-ok'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    avPowerOnLoading.value = false
  }
}

async function testAvPowerOff() {
  avPowerOffLoading.value = true
  try {
    await api.avPowerOff(await configWithSection('av', av.value))
    avTested.value = true
    toast.success(t('x-av-power-off-ok'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    avPowerOffLoading.value = false
  }
}

async function getAvSources() {
  avSourcesLoading.value = true
  try {
    const updated = await api.getAvSources(await configWithSection('av', av.value))
    av.value = {...(updated.av || {})}
    fullConfig.value = updated
    selectedAvSource.value = av.value.player_hdmi_input || ''
    toast.success(t('x-av-inputs-detected'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    avSourcesLoading.value = false
  }
}

async function testAvHdmi() {
  avHdmiLoading.value = true
  try {
    await api.avSwitchInput(await configWithSection('av', av.value))
    avTested.value = true
    toast.success(t('x-av-hdmi-ok'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    avHdmiLoading.value = false
  }
}

async function saveAv() {
  try {
    await saveConfigSection('av', av.value)
    toast.success(t('x-common-saved'))
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await api.getConfig()
    fullConfig.value = data
    tv.value = {...(data.tv || {})}
    av.value = {...(data.av || {})}
    tvModels.value = data.tv_dirs || ['LG', 'SCRIPTS']
    avModels.value = data.av_dirs || []
    selectedTvSourceIndex.value = tv.value.player_hdmi_input_id || 0
    selectedAvSource.value = av.value.player_hdmi_input || ''
    arpAvailable.value = data.arp_available !== false
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.sala-view {
  position: relative;
  min-height: 100dvh;
}

.sala-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.97;
  filter: saturate(1.2) contrast(1.04) brightness(1.12) sepia(0.08) hue-rotate(-5deg);
}

.sala-scene-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 26%, rgba(80, 122, 142, 0.18), transparent 34%),
  radial-gradient(circle at 78% 18%, rgba(245, 165, 36, 0.18), transparent 34%),
  radial-gradient(circle at 12% 8%, rgba(194, 161, 107, 0.13), transparent 32%);
}

.sala-scene-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(8, 16, 20, 0.6), rgba(32, 56, 68, 0.12) 46%, rgba(8, 16, 20, 0.34)),
  linear-gradient(180deg, rgba(35, 61, 74, 0.08), rgba(8, 16, 20, 0.18) 52%, rgba(6, 13, 17, 0.68));
}

.sala-view-body {
  position: relative;
  z-index: 1;
  padding: clamp(40px, 7vh, 78px) clamp(22px, 5vw, 76px) clamp(28px, 5vh, 54px);
}

.sala-kicker {
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

.sala-showcase-title {
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

.sala-showcase-subtitle {
  max-width: 800px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: clamp(15px, 1.15vw, 19px);
  line-height: 1.42;
  text-wrap: balance;
}

.sala-showcase-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 16px;
}

.sala-showcase {
  display: flex;
  min-height: clamp(132px, 21dvh, 228px);
  flex-direction: column;
  justify-content: center;
  margin-bottom: clamp(16px, 2.2vh, 26px);
}

.sala-shell {
  display: grid;
  gap: 18px;
  width: min(100%, 1500px);
  max-width: none;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.22));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.4),
  inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(7px);
}

.sala-grid {
  display: grid;
  grid-template-columns: minmax(320px, 1fr) minmax(320px, 1fr) minmax(260px, 0.75fr);
  gap: 16px;
  align-items: start;
}

.room-device-card {
  min-width: 0;
}

.room-card-head {
  align-items: flex-start;
  gap: 14px;
}

.room-card-controls {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.room-card-sub {
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
  margin: 4px 0 0;
}

.room-card-actions {
  display: flex;
  align-items: center;
  gap: 9px;
  flex-wrap: wrap;
  margin-top: 16px;
  padding-top: 14px;
  border-top: 1px solid var(--panel-border);
}

.room-disabled-body {
  display: grid;
  gap: 14px;
  justify-items: start;
  color: var(--text-muted);
  font-size: 12px;
  line-height: 1.5;
}

.room-disabled-body p {
  margin: 0;
}

.room-state {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  min-height: 22px;
  padding: 3px 7px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 6px;
  color: var(--text-subtle);
  background: rgba(255, 255, 255, 0.035);
  font-size: 9px;
  font-weight: 800;
  line-height: 1.1;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  white-space: nowrap;
}

.room-state--tested {
  color: var(--status-success);
  border-color: rgba(55, 230, 138, 0.18);
  background: rgba(55, 230, 138, 0.08);
}

.room-state--configured {
  color: var(--status-info);
  border-color: rgba(48, 213, 200, 0.16);
  background: rgba(48, 213, 200, 0.07);
}

.room-state--incomplete {
  color: var(--status-warning);
  border-color: rgba(245, 165, 36, 0.24);
  background: rgba(245, 165, 36, 0.08);
}

.room-state--disabled {
  color: var(--text-subtle);
}

.room-help-column {
  display: grid;
  gap: 12px;
  position: sticky;
  top: 18px;
}

.room-help-card {
  padding: 12px;
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  background: linear-gradient(165deg, rgba(255, 255, 255, 0.035), rgba(255, 255, 255, 0.005) 40%, transparent),
  var(--bg-panel);
  box-shadow: inset 0 1px 0 var(--panel-specular), 0 18px 40px -16px rgba(7, 11, 13, 0.65);
}

.room-help-title {
  display: flex;
  align-items: center;
  gap: 7px;
  color: var(--text-main);
  font-size: 12px;
  font-weight: 750;
  margin: 0 0 10px;
}

.room-help-list {
  display: grid;
  gap: 8px;
  margin: 0;
  padding-left: 17px;
  color: var(--text-muted);
  font-size: 11px;
  line-height: 1.45;
}

.icon-action-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 12px;
}

@media (max-width: 1180px) {
  .sala-grid {
    grid-template-columns: minmax(280px, 1fr) minmax(280px, 1fr);
  }

  .room-help-column {
    grid-column: 1 / -1;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    position: static;
  }
}

@media (max-width: 860px) {
  .sala-grid,
  .room-help-column {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .icon-action-row {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
