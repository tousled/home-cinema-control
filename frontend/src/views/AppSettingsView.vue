<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-nav-service-section') }}</div>
      <h1 class="view-hero-title">{{ $t('x-settings-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-settings-subtitle') }}</div>
    </div>

    <div class="view-form">
    <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <div class="panel mb-4">
        <div class="panel-body">
          <div class="form-label label-with-help">
            <label for="app-language">{{ $t('x-settings-language') }}</label>
            <HelpTooltip :text="$t('x-settings-tooltip-language')"/>
          </div>
          <FormSelect
              id="app-language"
              v-model="app.language"
              :options="langs.map(l => ({ value: l, label: l }))"
              class="mb-4"
          />

          <div class="form-label label-with-help">
            <label for="app-log-level">{{ $t('x-settings-log-level') }}</label>
            <HelpTooltip :text="$t('x-settings-tooltip-log-level')"/>
          </div>
          <FormSelect
              id="app-log-level"
              v-model="app.log_level"
              :options="[
                { value: 0, label: `0 — ${$t('x-settings-log-level-min')}` },
                { value: 1, label: `1 — ${$t('x-settings-log-level-normal')}` },
                { value: 2, label: `2 — ${$t('x-settings-log-level-verbose')}` },
              ]"
              class="mb-4"
          />

          <div class="form-label label-with-help">
            <label for="app-status-refresh">{{ $t('x-settings-status-refresh') }}</label>
            <HelpTooltip :text="$t('x-settings-tooltip-status-refresh')"/>
          </div>
          <FormSelect
              id="app-status-refresh"
              v-model="app.status_refresh_interval_seconds"
              :options="[
                { value: 0, label: `0 — ${$t('x-settings-no-refresh')}` },
                { value: 2, label: '2' },
                { value: 5, label: '5' },
                { value: 10, label: '10' },
                { value: 30, label: '30' },
                { value: 60, label: '60' },
              ]"
          />
        </div>
      </div>

      <button class="btn-ghost" @click="saveConfig">{{ $t('x-common-save') }}</button>
    </template>
    </div>
  </div>
</template>

<script setup>
import {onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-control-room.png'
import {useToast} from '../composables/useToast.js'
import HelpTooltip from '../components/HelpTooltip.vue'
import FormSelect from '../components/FormSelect.vue'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'

const {t} = useI18n()
const toast = useToast()
const {saveSection} = useConfigSectionSave()

const loading = ref(true)

const app = ref({})
const langs = ref([])
const fullConfig = ref({})
const originalLanguage = ref('')

async function saveConfig() {
  const languageChanged = app.value.language !== originalLanguage.value
  try {
    fullConfig.value = await saveSection('app', app.value)
    toast.success(t('x-common-saved'))
    if (languageChanged) {
      setTimeout(() => window.location.reload(), 500)
    }
  } catch (e) {
    toast.error(e.message)
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const data = await api.getConfig()
    fullConfig.value = data
    app.value = {...(data.app || {})}
    langs.value = data.langs || []
    originalLanguage.value = app.value.language || ''
  } finally {
    loading.value = false
  }
})
</script>
