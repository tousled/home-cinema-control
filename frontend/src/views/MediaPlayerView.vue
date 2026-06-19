<template>
  <div class="view-content view-ambient media-player-view">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="media-player-scene-bg"></div>

    <div class="view-body media-player-view-body">
      <section class="media-player-showcase">
        <h1 class="media-player-showcase-title">{{ $t('x-media-player-title') }}</h1>
        <p class="media-player-showcase-subtitle">{{ $t('x-media-player-subtitle') }}</p>
      </section>

      <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <div class="media-player-kicker">
        <span class="s-dot dim"></span>
        <span>{{ $t('x-nav-config-section') }}</span>
      </div>
      <div class="media-player-form">
        <div :class="connectionAccentClass" class="panel mb-3">
        <div class="panel-head">
          <h2 class="panel-title label-with-help">
            <Cable :size="13" :stroke-width="2.3"/>
            {{ $t('x-media-player-section-connection') }}
            <HelpTooltip :text="$t('x-media-player-tooltip-connection')"/>
          </h2>
          <span :class="['player-state', `player-state--${oppoState}`]">{{ oppoStateLabel }}</span>
        </div>
        <div class="panel-body">
          <div v-if="arpAvailable" class="flex items-center gap-3 mb-3">
            <HelpTooltip :text="$t('x-network-tooltip-scan')">
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
          <div class="form-label label-with-help">
            <label for="oppo-ip">{{ $t('x-media-player-ip') }}</label>
            <HelpTooltip :text="$t('x-media-player-tooltip-ip')"/>
          </div>
          <IpInput id="oppo-ip" v-model="oppo.ip" :devices="devices" class="mb-4" placeholder="192.168.1.x"/>
        </div>
      </div>

      <div class="panel mb-4">
        <div class="panel-head">
          <h2 class="panel-title label-with-help">
            <SlidersHorizontal :size="13" :stroke-width="2.3"/>
            {{ $t('x-media-player-section-options') }}
            <HelpTooltip :text="$t('x-media-player-tooltip-options')"/>
          </h2>
        </div>
        <div class="panel-body">
          <div class="space-y-3">
            <div class="flex items-center gap-2">
              <label class="flex items-center gap-2" style="cursor:pointer">
                <input v-model="oppo.always_on" type="checkbox"/>
                <span class="body-text">{{ $t('x-media-player-always-on') }}</span>
              </label>
              <HelpTooltip :text="$t('x-media-player-tooltip-always-on')"/>
            </div>
          </div>

          <details class="advanced-config mt-4">
            <summary>{{ $t('x-media-player-advanced-toggle') }}</summary>
            <div class="advanced-config-body">
              <div class="form-label label-with-help">
                <label for="oppo-conn-timeout">{{ $t('x-media-player-timeout-connection') }}</label>
                <HelpTooltip :text="$t('x-media-player-tooltip-timeout-connection')"/>
              </div>
              <input id="oppo-conn-timeout" v-model.number="oppo.connection_timeout_seconds" class="form-input mb-3"
                     min="1" step="1" type="number"/>

              <div class="form-label label-with-help">
                <label for="oppo-start-timeout">{{ $t('x-media-player-timeout-playback-start') }}</label>
                <HelpTooltip :text="$t('x-media-player-tooltip-timeout-playback-start')"/>
              </div>
              <input id="oppo-start-timeout" v-model.number="oppo.playback_start_timeout_seconds"
                     class="form-input mb-3"
                     min="1" step="1" type="number"/>

              <div class="form-label label-with-help">
                <label for="oppo-nfs-timeout">{{ $t('x-media-player-timeout-nfs-mount') }}</label>
                <HelpTooltip :text="$t('x-media-player-tooltip-timeout-nfs-mount')"/>
              </div>
              <input id="oppo-nfs-timeout" v-model.number="oppo.nfs_mount_timeout_seconds" class="form-input mb-4"
                     min="1" step="1" type="number"/>

              <div class="flex items-center gap-2 mb-3">
                <label class="flex items-center gap-2" style="cursor:pointer">
                  <input v-model="oppo.autoscript" type="checkbox"/>
                  <span class="body-text">{{ $t('x-media-player-autoscript') }}</span>
                </label>
                <HelpTooltip :text="$t('x-media-player-tooltip-autoscript')"/>
              </div>

              <button :disabled="restoringDefaults" class="btn-ghost" @click="restoreAdvancedDefaults">
                {{ restoringDefaults ? $t('x-common-loading') : $t('x-media-player-restore-defaults') }}
              </button>
            </div>
          </details>
        </div>
      </div>

      <div class="flex gap-3">
        <button :disabled="testing" class="btn-ghost" @click="testOppo">
          {{ testing ? $t('x-common-testing') : $t('x-media-player-test-connection') }}
        </button>
        <button class="btn-ghost" @click="saveConfig">{{ $t('x-common-save') }}</button>
      </div>

      <StepNav :current-step="2"/>
      </div><!-- /media-player-form -->
    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
import {Cable, SlidersHorizontal} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-media-player.png'
import {useToast} from '../composables/useToast.js'
import {useNetworkScan} from '../composables/useNetworkScan.js'
import StepNav from '../components/StepNav.vue'
import HelpTooltip from '../components/HelpTooltip.vue'
import IpInput from '../components/IpInput.vue'
import IconActionButton from '../components/IconActionButton.vue'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {t} = useI18n()
const toast = useToast()
const {scanning, devices, scan} = useNetworkScan()
const {saveSection} = useConfigSectionSave()

const loading = ref(true)
const testing = ref(false)
const restoringDefaults = ref(false)
const arpAvailable = ref(true)
const oppo = ref({})
const fullConfig = ref({})
const oppoTested = ref(false)

const oppoState = computed(() => {
  if (!oppo.value.ip) return 'incomplete'
  return oppoTested.value ? 'tested' : 'configured'
})

const oppoStateLabel = computed(() => t(`x-media-player-state-${oppoState.value}`))

const connectionAccentClass = computed(() => {
  if (oppoState.value === 'tested') return 'panel-accent-ok'
  if (oppoState.value === 'configured') return 'panel-accent-info'
  return 'panel-accent-warn'
})

watch(() => oppo.value.ip, () => {
  oppoTested.value = false
})

async function configWithOppo() {
  const latest = await api.getConfig()
  return {
    ...latest,
    oppo: {...oppo.value},
  }
}

async function testOppo() {
  testing.value = true
  try {
    await api.checkOppo(await configWithOppo())
    oppoTested.value = true
    toast.success(t('x-media-player-connection-ok'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    testing.value = false
  }
}

async function restoreAdvancedDefaults() {
  restoringDefaults.value = true
  try {
    const defaults = await api.getOppoAdvancedDefaults()
    oppo.value = {...oppo.value, ...defaults}
    toast.success(t('x-media-player-defaults-restored'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    restoringDefaults.value = false
  }
}

async function saveConfig() {
  try {
    fullConfig.value = await saveSection('oppo', oppo.value)
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
    arpAvailable.value = data.arp_available !== false
    oppo.value = {...(data.oppo || {})}
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.media-player-view {
  position: relative;
  min-height: 100dvh;
}

.media-player-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.97;
  filter: saturate(1.2) contrast(1.04) brightness(1.12) sepia(0.08) hue-rotate(-5deg);
}

.media-player-scene-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 26%, rgba(80, 122, 142, 0.18), transparent 34%),
  radial-gradient(circle at 78% 18%, rgba(245, 165, 36, 0.18), transparent 34%),
  radial-gradient(circle at 12% 8%, rgba(194, 161, 107, 0.13), transparent 32%);
}

.media-player-scene-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(8, 16, 20, 0.6), rgba(32, 56, 68, 0.12) 46%, rgba(8, 16, 20, 0.34)),
  linear-gradient(180deg, rgba(35, 61, 74, 0.08), rgba(8, 16, 20, 0.18) 52%, rgba(6, 13, 17, 0.68));
}

.media-player-view-body {
  position: relative;
  z-index: 1;
  padding: clamp(40px, 7vh, 78px) clamp(22px, 5vw, 76px) clamp(28px, 5vh, 54px);
}

.media-player-form {
  width: min(100%, 840px);
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.22));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.4),
  inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(7px);
}

.media-player-kicker {
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

.media-player-showcase-title {
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

.media-player-showcase-subtitle {
  max-width: 690px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: clamp(15px, 1.15vw, 19px);
  line-height: 1.42;
  text-wrap: balance;
}

.media-player-showcase {
  display: flex;
  min-height: clamp(126px, 20dvh, 218px);
  flex-direction: column;
  justify-content: center;
  margin-bottom: clamp(16px, 2.2vh, 26px);
}

.player-state {
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

.player-state--tested {
  color: var(--status-success);
  border-color: rgba(55, 230, 138, 0.18);
  background: rgba(55, 230, 138, 0.08);
}

.player-state--configured {
  color: var(--status-info);
  border-color: rgba(48, 213, 200, 0.16);
  background: rgba(48, 213, 200, 0.07);
}

.player-state--incomplete {
  color: var(--status-warning);
  border-color: rgba(245, 165, 36, 0.24);
  background: rgba(245, 165, 36, 0.08);
}
</style>
