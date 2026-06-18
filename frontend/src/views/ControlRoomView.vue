<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${activeBg})` }" class="ambient-bg"></div>
    <!-- Hero -->
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-control-room-eyebrow') }}</div>
      <h1 class="view-hero-title">{{ $t('x-control-room-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-control-room-subtitle') }}</div>
      <div class="hero-status">
        <span :class="systemDotClass" class="s-dot inline-block mr-1"></span>
        {{ systemStatusLabel }}
      </div>
    </div>

    <div class="view-body">
    <!-- Component cards grid -->
    <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

    <template v-else>
      <div class="cards-grid mb-6">
        <!-- Emby / Media Server -->
        <div :class="serverCardClass" class="comp-card" @click="router.push('/media-server')">
          <div class="card-name">{{ $t('x-nav-media-server') }}</div>
          <div class="card-value">{{ serverCardValue }}</div>
          <div class="card-sub">{{ config.media_server?.server_url || '—' }}</div>
          <div class="mt-auto pt-2">
            <span :class="serverTagClass" class="tag">{{ serverTagLabel }}</span>
          </div>
        </div>

        <!-- OPPO / Media Player -->
        <div :class="oppoCardClass" class="comp-card" @click="router.push('/media-player')">
          <div class="card-name">{{ $t('x-nav-media-player') }}</div>
          <div class="card-value">{{ oppoCardValue }}</div>
          <div class="card-sub">{{ config.oppo?.ip || '—' }}</div>
          <div class="mt-auto pt-2">
            <span :class="oppoTagClass" class="tag">{{ oppoTagLabel }}</span>
          </div>
        </div>

        <!-- TV -->
        <div :class="tvCardClass" class="comp-card" @click="router.push('/sala')">
          <div class="card-name">{{ $t('x-control-room-tv') }}</div>
          <div class="card-value">{{ tvCardValue }}</div>
          <div class="card-sub">{{ config.tv?.model || '—' }} · {{ config.tv?.ip || '' }}</div>
          <div class="mt-auto pt-2">
            <span :class="tvTagClass" class="tag">{{ tvTagLabel }}</span>
          </div>
        </div>

        <!-- AV Receiver -->
        <div :class="avCardClass" class="comp-card" @click="router.push('/sala')">
          <div class="card-name">{{ $t('x-control-room-av') }}</div>
          <div class="card-value">{{ avCardValue }}</div>
          <div class="card-sub">{{ config.av?.model || '—' }} · {{ config.av?.ip || '' }}</div>
          <div class="mt-auto pt-2">
            <span :class="avTagClass" class="tag">{{ avTagLabel }}</span>
          </div>
        </div>

        <!-- Paths -->
        <div :class="pathsCardClass" class="comp-card" @click="router.push('/media-paths')">
          <div class="card-name">{{ $t('x-nav-paths') }}</div>
          <div class="card-value">{{ pathsCardValue }}</div>
          <div class="card-sub">{{ pathsCardSub }}</div>
          <div class="mt-auto pt-2">
            <span :class="pathsTagClass" class="tag">{{ pathsTagLabel }}</span>
          </div>
        </div>
      </div>

      <!-- Resources + Active session row -->
      <div class="bottom-row">
        <!-- Resources -->
        <div class="panel" style="flex:1">
          <div class="panel-head">
            <h2 class="panel-title">{{ $t('x-control-room-resources') }}</h2>
            <span class="mono version-badge">v{{ state.Version }}</span>
          </div>
          <div class="panel-body">
            <div class="mb-3">
              <div class="flex justify-between mb-1">
                <span class="metric-label">CPU</span>
                <span class="mono metric-value">{{ state.cpu_perc ?? '—' }}%</span>
              </div>
              <div class="meter">
                <div :class="meterClass(state.cpu_perc)" :style="{width: (state.cpu_perc||0)+'%'}"
                     class="meter-fill"></div>
              </div>
            </div>
            <div>
              <div class="flex justify-between mb-1">
                <span class="metric-label">RAM</span>
                <span class="mono metric-value">{{ state.mem_perc ?? '—' }}%</span>
              </div>
              <div class="meter">
                <div :class="meterClass(state.mem_perc)" :style="{width: (state.mem_perc||0)+'%'}"
                     class="meter-fill"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- Active session / Now playing -->
        <div class="panel" style="flex:2">
          <div class="panel-head">
            <h2 class="panel-title">{{ $t('x-control-room-now-playing') }}</h2>
            <span v-if="state.Playstate === 'Playing'" class="s-dot ok pulse"></span>
          </div>
          <div class="panel-body">
            <template v-if="state.ActiveSession?.title">
              <div class="now-playing-title">{{ state.ActiveSession.title }}</div>
              <div class="mono now-playing-path">{{ state.ActiveSession.content_directory }}</div>
              <div class="flex gap-2">
                <button class="btn-ghost btn-compact" @click="sendKey('STP')">■ Stop</button>
                <button class="btn-ghost btn-compact" @click="sendKey('PAU')">⏸ Pause</button>
              </div>
            </template>
            <template v-else>
              <div class="body-text">{{ playstateLabel }}</div>
            </template>
          </div>
        </div>
      </div>
    </template>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useRouter} from 'vue-router'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-control-room.png'
import {usePoll} from '../composables/usePoll.js'

const {t} = useI18n()
const router = useRouter()

const loading = ref(true)
const state = ref({})
const config = ref({})

const activeBg = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  return itemId ? `/api/now-playing/backdrop?item=${itemId}` : heroBg
})

usePoll(refresh, 8000)

/* ── playstate ── */
const playstateLabel = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return t('x-status-not-connected')
  if (ps === 'Free') return t('x-status-free')
  if (ps === 'Loading') return t('x-status-loading')
  if (ps === 'Playing') return t('x-status-playing')
  if (ps === 'Replay') return t('x-status-replay')
  return ps || '—'
})

const systemDotClass = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Playing') return 'ok pulse'
  if (ps === 'Not_Connected') return 'err'
  if (ps === 'Loading') return 'warn pulse'
  return 'ok'
})

const systemStatusLabel = computed(() => {
  if (state.value.Playstate === 'Playing') return t('x-control-room-status-playing')
  if (state.value.Playstate === 'Not_Connected') return t('x-control-room-status-disconnected')
  return t('x-control-room-status-idle')
})

/* ── server card ── */
const serverCardClass = computed(() => {
  if (!config.value.media_server?.server_url) return 'card-dim'
  if (state.value.Playstate === 'Playing') return 'card-playing'
  if (config.value.media_server?.access_token_configured) return 'card-ok'
  return 'card-warn'
})
const serverCardValue = computed(() => {
  if (!config.value.media_server?.server_url) return t('x-control-room-not-configured')
  return config.value.media_server?.display_name || 'Emby'
})
const serverTagClass = computed(() => {
  if (!config.value.media_server?.server_url) return 'tag-dim'
  if (config.value.media_server?.access_token_configured) return 'tag-ok'
  return 'tag-warn'
})
const serverTagLabel = computed(() => {
  if (!config.value.media_server?.server_url) return t('x-control-room-tag-unconfigured')
  if (config.value.media_server?.access_token_configured) return t('x-control-room-tag-auth')
  return t('x-control-room-tag-no-token')
})

/* ── oppo card ── */
const oppoCardClass = computed(() => {
  if (!config.value.oppo?.ip) return 'card-dim'
  if (state.value.Playstate === 'Playing') return 'card-playing'
  return 'card-ok'
})
const oppoCardValue = computed(() => {
  if (state.value.Playstate === 'Playing' && state.value.ActiveSession?.title) {
    return state.value.ActiveSession.title
  }
  if (!config.value.oppo?.ip) return t('x-control-room-not-configured')
  return 'OPPO'
})
const oppoTagClass = computed(() => {
  if (!config.value.oppo?.ip) return 'tag-dim'
  if (state.value.Playstate === 'Playing') return 'tag-blue'
  return 'tag-ok'
})
const oppoTagLabel = computed(() => {
  if (!config.value.oppo?.ip) return t('x-control-room-tag-unconfigured')
  if (state.value.Playstate === 'Playing') return t('x-control-room-tag-playing')
  return t('x-control-room-tag-ready')
})

/* ── tv card ── */
const tvCardClass = computed(() => {
  if (!config.value.tv?.enabled) return 'card-dim'
  return 'card-ok'
})
const tvCardValue = computed(() => config.value.tv?.enabled ? (config.value.tv?.model || 'TV') : t('x-control-room-disabled'))
const tvTagClass = computed(() => config.value.tv?.enabled ? 'tag-ok' : 'tag-dim')
const tvTagLabel = computed(() => config.value.tv?.enabled ? t('x-control-room-tag-enabled') : t('x-control-room-tag-disabled'))

/* ── av card ── */
const avCardClass = computed(() => {
  if (!config.value.av?.enabled) return 'card-dim'
  return 'card-ok'
})
const avCardValue = computed(() => config.value.av?.enabled ? (config.value.av?.model || 'AV') : t('x-control-room-disabled'))
const avTagClass = computed(() => config.value.av?.enabled ? 'tag-ok' : 'tag-dim')
const avTagLabel = computed(() => config.value.av?.enabled ? t('x-control-room-tag-enabled') : t('x-control-room-tag-disabled'))

/* ── paths card ── */
const pathMappings = computed(() => config.value.playback?.path_mappings || [])
const pathsCardClass = computed(() => {
  if (!pathMappings.value.length) return 'card-dim'
  const unverified = pathMappings.value.filter(p => !p.verified).length
  return unverified > 0 ? 'card-warn' : 'card-ok'
})
const pathsCardValue = computed(() => {
  const total = pathMappings.value.length
  if (!total) return t('x-control-room-no-paths')
  return `${total} ${total === 1 ? t('x-control-room-path') : t('x-control-room-paths')}`
})
const pathsCardSub = computed(() => {
  const verified = pathMappings.value.filter(p => p.verified).length
  const total = pathMappings.value.length
  if (!total) return ''
  return `${verified}/${total} ${t('x-control-room-verified')}`
})
const pathsTagClass = computed(() => {
  if (!pathMappings.value.length) return 'tag-dim'
  const unverified = pathMappings.value.filter(p => !p.verified).length
  return unverified > 0 ? 'tag-warn' : 'tag-ok'
})
const pathsTagLabel = computed(() => {
  if (!pathMappings.value.length) return t('x-control-room-tag-unconfigured')
  const unverified = pathMappings.value.filter(p => !p.verified).length
  return unverified > 0 ? t('x-control-room-tag-unverified') : t('x-control-room-tag-ok')
})

function meterClass(pct) {
  if (!pct) return 'meter-blue'
  if (pct < 50) return 'meter-ok'
  if (pct < 85) return 'meter-warn'
  return 'meter-err'
}

async function sendKey(k) {
  try {
    await api.sendKey(k)
  } catch { /* ignore */
  }
}

async function refresh() {
  try {
    state.value = await api.getState()
  } catch { /* ignore */
  }
}

onMounted(async () => {
  loading.value = true
  try {
    const [s, c] = await Promise.all([api.getState(), api.getConfig()])
    state.value = s
    config.value = c
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
/* ─── COMP CARD ──────────────────────────────────────────────────────── */
.comp-card {
  background: var(--bg-panel);
  border: 1px solid var(--panel-border);
  border-radius: 10px;
  padding: 16px 16px 14px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  cursor: pointer;
  text-decoration: none;
  color: inherit;
  min-height: 130px;
  transition: border-color 0.18s, transform 0.18s, box-shadow 0.18s;
}

.comp-card:hover {
  border-color: rgba(255, 255, 255, 0.13);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.25);
}

.comp-card.card-playing {
  background: rgba(47, 128, 237, 0.06);
  border-color: rgba(47, 128, 237, 0.25);
  box-shadow: inset 0 1px 0 rgba(86, 204, 242, 0.12);
  animation: breathe 3s ease-in-out infinite;
}

.comp-card.card-ok {
  border-left: 2px solid var(--status-success);
}

.comp-card.card-warn {
  border-left: 2px solid var(--status-warning);
}

.comp-card.card-err {
  border-left: 2px solid var(--status-danger);
}

.comp-card.card-dim {
  border-left: 2px solid var(--text-subtle);
  opacity: 0.7;
}

.card-name {
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: var(--text-subtle);
}

.card-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-main);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.card-sub {
  font-size: 12px;
  color: var(--text-subtle);
  font-family: var(--mono);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.hero-status {
  margin-top: 8px;
  font-size: 12px;
  font-weight: 500;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 6px;
}

.version-badge {
  font-size: 9px;
  color: var(--text-subtle);
}

.now-playing-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-main);
  margin-bottom: 6px;
}

.now-playing-path {
  font-size: 10px;
  color: var(--text-subtle);
  margin-bottom: 10px;
}

.btn-compact {
  padding: 5px 10px;
  font-size: 12px;
}

@keyframes breathe {
  0%, 100% {
    box-shadow: inset 0 1px 0 rgba(86, 204, 242, 0.12), 0 0 20px rgba(47, 128, 237, 0.04);
  }
  50% {
    box-shadow: inset 0 1px 0 rgba(86, 204, 242, 0.18), 0 0 32px rgba(47, 128, 237, 0.10);
  }
}

@media (prefers-reduced-motion: reduce) {
  .comp-card.card-playing {
    animation: none;
  }
}

/* ─── GRID ───────────────────────────────────────────────────────────── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 10px;
}

@media (max-width: 1100px) {
  .cards-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

.bottom-row {
  display: flex;
  gap: 10px;
}

@media (max-width: 760px) {
  .bottom-row {
    flex-direction: column;
  }
}
</style>
