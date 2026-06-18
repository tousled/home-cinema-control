<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-nav-support-section') }}</div>
      <h1 class="view-hero-title">{{ $t('x-logs-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-logs-subtitle') }}</div>
      <div class="icon-action-row mt-3">
        <IconActionButton :label="$t('x-logs-refresh')" icon="refresh" @click="loadLogs"/>
        <IconActionButton
            :href="downloadHref"
            :label="$t('x-logs-download')"
            download="hcc.log"
            icon="download"
        />
      </div>
    </div>

    <div class="view-body">
    <div v-if="loading" style="font-size:12px;color:var(--text-muted)">{{ $t('x-logs-loading') }}</div>

      <template v-else>
        <div class="form-label label-with-help mb-2">
          <label for="logs-severity-filter">{{ $t('x-logs-filter-label') }}</label>
        </div>
        <FormSelect
            id="logs-severity-filter"
            v-model="minSeverity"
            :options="severityOptions"
            class="mb-3"
            style="max-width:280px"
        />

        <div v-if="entries.length" class="log-output">
          <div v-for="(entry, index) in filteredEntries" :key="index" class="log-line">
            <span class="log-timestamp">{{ entry.timestamp }}</span>
            <span :class="['log-level-chip', levelChipClass(entry.level)]">{{ levelLabel(entry.level) }}</span>
            <span class="log-message">{{ entry.message }}</span>
          </div>
          <p v-if="!filteredEntries.length" class="caption">{{ $t('x-logs-filter-empty') }}</p>
        </div>
        <pre v-else class="log-output log-output-raw">{{ rawText }}</pre>
      </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-status.png'
import IconActionButton from '../components/IconActionButton.vue'
import FormSelect from '../components/FormSelect.vue'

const {t} = useI18n()

const SEVERITY_RANK = {DEBUG: 0, INFO: 1, WARNING: 2, ERROR: 3, CRITICAL: 4}

const loading = ref(true)
const rawText = ref('')
const entries = ref([])
const minSeverity = ref(0)

const severityOptions = computed(() => [
  {value: 0, label: t('x-logs-filter-all')},
  {value: SEVERITY_RANK.INFO, label: t('x-logs-filter-info')},
  {value: SEVERITY_RANK.WARNING, label: t('x-logs-filter-warning')},
  {value: SEVERITY_RANK.ERROR, label: t('x-logs-filter-error')},
])

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

onMounted(loadLogs)
</script>

<style scoped>
.log-output {
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 16px;
  font-family: var(--mono);
  font-size: 11px;
  overflow: auto;
  max-height: 70vh;
  line-height: 1.7;
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
