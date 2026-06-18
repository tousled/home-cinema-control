<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-nav-config-section') }}</div>
      <h1 class="view-hero-title">{{ $t('x-media-player-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-media-player-subtitle') }}</div>
    </div>

    <div class="view-form">
    <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <div class="panel mb-3">
        <div class="panel-head">
          <h2 class="panel-title label-with-help">
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
    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref, watch} from 'vue'
import {useI18n} from 'vue-i18n'
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
