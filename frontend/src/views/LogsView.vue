<template>
  <div class="view-content view-ambient logs-view">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="logs-scene-bg"></div>

    <div class="view-body logs-view-body">
      <section class="logs-showcase">
        <h1 class="logs-title">{{ $t('x-logs-title') }}</h1>
        <p class="logs-subtitle">{{ $t('x-logs-subtitle') }}</p>
        <div class="icon-action-row mt-3">
          <IconActionButton :label="$t('x-logs-refresh')" icon="refresh" @click="loadLogs"/>
          <IconActionButton
              :href="downloadHref"
              :label="$t('x-logs-download')"
              download="hcc.log"
              icon="download"
          />
        </div>
      </section>

      <div v-if="loading" style="font-size:12px;color:var(--text-muted)">{{ $t('x-logs-loading') }}</div>

      <template v-else>
        <div class="logs-kicker">
          <span class="s-dot dim"></span>
          <span>{{ $t('x-nav-support-section') }}</span>
        </div>
        <div class="logs-console">
          <div class="logs-levels">
            <div class="form-label label-with-help mb-2">
              <label>{{ $t('x-logs-levels-title') }}</label>
            </div>
            <p class="caption logs-levels-help">{{ $t('x-logs-levels-help') }}</p>
            <div class="logs-levels-row">
              <div class="logs-level-field">
                <label for="logs-file-level">{{ $t('x-logs-file-level-label') }}</label>
                <FormSelect
                    id="logs-file-level"
                    v-model="fileLogLevel"
                    :disabled="savingLevels"
                    :options="backendLevelOptions"
                    @change="saveLevels"
                />
              </div>
              <div class="logs-level-field">
                <label for="logs-console-level">{{ $t('x-logs-console-level-label') }}</label>
                <FormSelect
                    id="logs-console-level"
                    v-model="consoleLogLevel"
                    :disabled="savingLevels"
                    :options="backendLevelOptions"
                    @change="saveLevels"
                />
              </div>
            </div>
          </div>

          <div class="logs-filter-row">
            <div class="form-label label-with-help mb-2">
              <label for="logs-severity-filter">{{ $t('x-logs-filter-label') }}</label>
            </div>
            <FormSelect
                id="logs-severity-filter"
                v-model="minSeverity"
                :options="severityOptions"
                style="max-width:280px"
            />
          </div>

          <div v-if="entries.length" class="log-output">
            <div v-for="(entry, index) in filteredEntries" :key="index" class="log-line">
              <span class="log-timestamp">{{ entry.timestamp }}</span>
              <span :class="['log-level-chip', levelChipClass(entry.level)]">{{ levelLabel(entry.level) }}</span>
              <span class="log-message">{{ entry.message }}</span>
            </div>
            <p v-if="!filteredEntries.length" class="caption">{{ $t('x-logs-filter-empty') }}</p>
          </div>
          <pre v-else class="log-output log-output-raw">{{ rawText }}</pre>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {api} from '../api/index.js'
import {useConfigSectionSave} from '../composables/useConfigSectionSave.js'
import {useToast} from '../composables/useToast.js'
import heroBg from '../assets/backgrounds/bg-status.png'
import IconActionButton from '../components/IconActionButton.vue'
import FormSelect from '../components/FormSelect.vue'

const {t} = useI18n()
const {saveSection} = useConfigSectionSave()
const toast = useToast()

const SEVERITY_RANK = {DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3, CRITICAL: 4}

const loading = ref(true)
const rawText = ref('')
const entries = ref([])
const minSeverity = ref(0)

const fullConfig = ref({})
const fileLogLevel = ref(0)
const consoleLogLevel = ref(0)
const savingLevels = ref(false)

const severityOptions = computed(() => [
  {value: 0, label: t('x-logs-filter-all')},
  {value: SEVERITY_RANK.INFO, label: t('x-logs-filter-info')},
  {value: SEVERITY_RANK.WARNING, label: t('x-logs-filter-warning')},
  {value: SEVERITY_RANK.ERROR, label: t('x-logs-filter-error')},
])

const backendLevelOptions = computed(() => [
  {value: 0, label: t('x-logs-backend-level-off')},
  {value: 1, label: t('x-logs-backend-level-info')},
  {value: 2, label: t('x-logs-backend-level-debug')},
])

async function loadLevels() {
  try {
    const cfg = await api.getConfig()
    fullConfig.value = cfg
    const app = cfg.app || {}
    fileLogLevel.value = app.log_level ?? 0
    // null/undefined console level means "follow the file level".
    consoleLogLevel.value = app.console_log_level ?? fileLogLevel.value
  } catch { /* non-fatal: keep defaults */
  }
}

async function saveLevels() {
  savingLevels.value = true
  try {
    fullConfig.value.app = {
      ...(fullConfig.value.app || {}),
      log_level: fileLogLevel.value,
      console_log_level: consoleLogLevel.value,
    }
    fullConfig.value = await saveSection('app', fullConfig.value.app)
    toast.success(t('x-logs-level-saved'))
  } catch (e) {
    toast.error(e.message)
  } finally {
    savingLevels.value = false
  }
}

const filteredEntries = computed(() =>
    entries.value.filter((entry) => (SEVERITY_RANK[entry.level] ?? 1) >= minSeverity.value)
)

const downloadHref = computed(() => {
  const blob = new Blob([rawText.value], {type: 'text/plain'})
  return URL.createObjectURL(blob)
})

function levelLabel(level) {
  return t(`x-logs-level-${(level || 'info').toLowerCase()}`) || level
}

function levelChipClass(level) {
  if (level === 'ERROR' || level === 'CRITICAL') return 'log-level-error'
  if (level === 'WARNING') return 'log-level-warning'
  if (level === 'DEBUG') return 'log-level-debug'
  return 'log-level-info'
}

function parseLines(text) {
  const parsed = []
  for (const line of text.split('\n')) {
    if (!line.trim()) continue
    try {
      const record = JSON.parse(line)
      if (record && typeof record === 'object' && 'message' in record) {
        parsed.push({
          timestamp: record.timestamp || '',
          level: (record.level || 'INFO').toUpperCase(),
          message: record.message,
        })
        continue
      }
    } catch {
      // not a structured line (legacy plain-text log, or a non-JSON entry) — fall through
    }
    parsed.push({timestamp: '', level: 'INFO', message: line})
  }
  return parsed
}

async function loadLogs() {
  loading.value = true
  try {
    rawText.value = await api.getLogs()
    entries.value = parseLines(rawText.value)
  } catch (e) {
    rawText.value = t('x-logs-load-error', {error: e.message})
    entries.value = []
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadLevels()
  loadLogs()
})
</script>

<style scoped>
.logs-view {
  position: relative;
  min-height: 100dvh;
}

.logs-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.97;
  filter: saturate(1.2) contrast(1.04) brightness(1.12) sepia(0.08) hue-rotate(-5deg);
}

.logs-scene-bg::before {
  content: '';
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 18% 26%, rgba(80, 122, 142, 0.18), transparent 34%),
  radial-gradient(circle at 78% 18%, rgba(245, 165, 36, 0.18), transparent 34%),
  radial-gradient(circle at 12% 8%, rgba(194, 161, 107, 0.13), transparent 32%);
}

.logs-scene-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(8, 16, 20, 0.6), rgba(32, 56, 68, 0.12) 46%, rgba(8, 16, 20, 0.34)),
  linear-gradient(180deg, rgba(35, 61, 74, 0.08), rgba(8, 16, 20, 0.18) 52%, rgba(6, 13, 17, 0.68));
}

.logs-view-body {
  position: relative;
  z-index: 1;
  padding: clamp(40px, 7vh, 78px) clamp(22px, 5vw, 76px) clamp(28px, 5vh, 54px);
}

.logs-kicker {
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

.logs-title {
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

.logs-subtitle {
  max-width: 690px;
  margin: 12px 0 0;
  color: rgba(245, 247, 255, 0.78);
  font-size: clamp(17px, 1.4vw, 23px);
  line-height: 1.42;
  text-wrap: balance;
}

.logs-showcase {
  display: flex;
  min-height: clamp(150px, 24dvh, 260px);
  flex-direction: column;
  justify-content: center;
  margin-bottom: clamp(16px, 2.2vh, 26px);
}

.logs-console {
  display: grid;
  width: min(100%, 1480px);
  gap: 14px;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.22));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.4),
  inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(7px);
}

.logs-filter-row {
  min-width: 0;
}

.logs-levels {
  min-width: 0;
  padding-bottom: 12px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
}

.logs-levels-help {
  margin: 0 0 12px;
}

.logs-levels-row {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
}

.logs-level-field {
  display: grid;
  gap: 6px;
  min-width: 220px;
  flex: 1 1 240px;
  max-width: 320px;
}

.logs-level-field label {
  font-size: 12px;
  color: var(--text-muted);
}

.log-output {
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.72), rgba(13, 18, 20, 0.42));
  border: 1px solid rgba(255, 255, 255, 0.085);
  border-radius: 12px;
  padding: 16px;
  font-family: var(--mono);
  font-size: 11px;
  overflow: auto;
  max-height: 70vh;
  line-height: 1.7;
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.log-output-raw {
  color: var(--status-success);
  white-space: pre-wrap;
  word-break: break-all;
}

.log-line {
  display: flex;
  align-items: baseline;
  gap: 8px;
  white-space: pre-wrap;
  word-break: break-word;
  padding: 2px 0;
}

.log-timestamp {
  color: var(--text-subtle);
  flex-shrink: 0;
}

.log-message {
  color: var(--text-muted);
}

.log-level-chip {
  flex-shrink: 0;
  font-weight: 700;
  text-transform: uppercase;
  font-size: 10px;
  letter-spacing: .04em;
  border-radius: 4px;
  padding: 1px 6px;
}

.log-level-info {
  color: var(--status-info);
  background: rgba(48, 213, 200, 0.12);
}

.log-level-debug {
  color: var(--text-muted);
  background: rgba(139, 147, 167, 0.12);
}

.log-level-warning {
  color: var(--status-warning);
  background: rgba(245, 165, 36, 0.12);
}

.log-level-error {
  color: var(--status-danger);
  background: rgba(255, 92, 122, 0.12);
}

@media (max-width: 760px) {
  .log-line {
    flex-wrap: wrap;
  }
}
</style>
