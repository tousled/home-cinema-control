<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${idleSceneBg})` }" class="ambient-bg"></div>

    <div :class="['view-body', 'control-room-body', {'control-room-body--idle': !loading}]">
      <div v-if="loading" class="text-sm" style="color:var(--text-muted)">{{ $t('x-common-loading') }}</div>

      <template v-else>
        <div
            :style="{ backgroundImage: `url(${idleSceneBg})` }"
            class="room-idle-art"
        ></div>

        <section class="room-idle-landing">
          <div class="room-idle-copy">
            <div class="view-hero-eyebrow">{{ $t('x-control-room-idle-eyebrow') }}</div>
            <h1 class="room-idle-title">{{ $t('x-control-room-idle-title') }}</h1>
            <p class="room-idle-subtitle">{{ $t('x-control-room-idle-subtitle') }}</p>
            <div class="room-idle-actions">
              <button class="btn-primary room-idle-remote-button" type="button" @click="router.push('/remote')">
                <Gamepad2 :size="18" :stroke-width="2.2" aria-hidden="true"/>
                <span>{{ $t('x-control-room-open-remote') }}</span>
              </button>
              <div class="room-idle-status">
                <span :class="systemDotClass" class="s-dot"></span>
                <span>{{ systemStatusLabel }}</span>
              </div>
            </div>
          </div>
        </section>

        <div class="cards-grid room-status-grid">
        <div :class="serverCardClass" class="comp-card" @click="router.push('/media-server')">
          <div class="card-name">{{ $t('x-nav-media-server') }}</div>
          <div class="card-value">{{ serverCardValue }}</div>
          <div class="card-sub">{{ mediaServerProvider.server_url || '—' }}</div>
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

        <div class="room-idle-meta">
          <span>{{ $t('x-control-room-resources') }}</span>
          <strong>CPU {{ state.cpu_perc ?? '—' }}%</strong>
          <strong>RAM {{ state.mem_perc ?? '—' }}%</strong>
          <span class="mono">v{{ state.Version }}</span>
      </div>
    </template>
    </div>
  </div>
</template>

<script setup>
import {Gamepad2} from '@lucide/vue'
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {useRouter} from 'vue-router'
import {api} from '../api/index.js'
import idleSceneBg from '../assets/backgrounds/bg-control-room-idle.png'
import {usePoll} from '../composables/usePoll.js'
import {useMediaServerBrand} from '../composables/useMediaServerBrand.js'
import {useActiveMediaServer} from '../composables/useActiveMediaServer.js'

const {t} = useI18n()
const router = useRouter()

const loading = ref(true)
const state = ref({})
const config = ref({})
const {type: mediaServerType, provider: mediaServerProvider} = useActiveMediaServer(() => config.value)
const {brand} = useMediaServerBrand(mediaServerType)

const hasActiveSession = computed(() => Boolean(state.value.ActiveSession?.title))

usePoll(refresh, 8000)

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
  if (!mediaServerProvider.value.server_url) return 'card-dim'
  if (state.value.Playstate === 'Playing') return 'card-playing'
  if (mediaServerProvider.value.access_token_configured) return 'card-ok'
  return 'card-warn'
})
const serverCardValue = computed(() => {
  if (!mediaServerProvider.value.server_url) return t('x-control-room-not-configured')
  return mediaServerProvider.value.display_name || brand.value.label
})
const serverTagClass = computed(() => {
  if (!mediaServerProvider.value.server_url) return 'tag-dim'
  if (mediaServerProvider.value.access_token_configured) return 'tag-ok'
  return 'tag-warn'
})
const serverTagLabel = computed(() => {
  if (!mediaServerProvider.value.server_url) return t('x-control-room-tag-unconfigured')
  if (mediaServerProvider.value.access_token_configured) return t('x-control-room-tag-auth')
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
/* ─── ACTIVE ROOM STAGE ──────────────────────────────────────────────── */
.control-room-body {
  position: relative;
  max-width: 1600px;
}

.control-room-body--idle {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: clamp(28px, 4vh, 48px);
  min-height: 100dvh;
  max-width: none;
  padding: clamp(46px, 8vh, 86px) clamp(24px, 5vw, 76px) clamp(24px, 4vh, 44px);
  overflow: hidden;
  isolation: isolate;
}

.room-idle-art {
  position: absolute;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  overflow: hidden;
  border-radius: 0;
  background-position: center right;
  background-size: cover;
  filter: saturate(1.08) contrast(1.03);
  opacity: 0.9;
}

.room-idle-art::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(7, 11, 13, 0.62), rgba(7, 11, 13, 0.18) 42%, rgba(7, 11, 13, 0.44)),
  linear-gradient(180deg, rgba(7, 11, 13, 0.02), rgba(7, 11, 13, 0.28) 58%, rgba(7, 11, 13, 0.7));
}

.room-status-grid,
.room-idle-landing,
.room-idle-meta {
  position: relative;
  z-index: 1;
}

.room-idle-landing {
  display: flex;
  align-items: end;
  justify-content: center;
  text-align: center;
}

.room-idle-copy {
  width: min(980px, 100%);
}

.room-idle-title {
  max-width: 1060px;
  margin: 10px auto 0;
  color: var(--text-main);
  font-size: clamp(44px, 6.2vw, 96px);
  font-weight: 900;
  line-height: 0.95;
  letter-spacing: 0;
  text-wrap: balance;
  text-shadow: 0 28px 88px rgba(0, 0, 0, 0.72);
}

.room-idle-subtitle {
  max-width: 680px;
  margin: 18px auto 0;
  color: rgba(245, 247, 255, 0.72);
  font-size: clamp(17px, 1.45vw, 23px);
  line-height: 1.42;
  text-wrap: balance;
}

.room-idle-actions {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 22px;
}

.room-idle-remote-button {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  min-height: 42px;
  padding: 10px 16px;
  box-shadow: 0 16px 42px rgba(127, 166, 181, 0.32),
  inset 0 1px 0 rgba(255, 255, 255, 0.13);
}

.room-idle-status {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 10px 13px;
  border-radius: 999px;
  background: rgba(7, 11, 13, 0.46);
  border: 1px solid rgba(255, 255, 255, 0.075);
  color: rgba(245, 247, 255, 0.72);
  font-size: 12px;
  font-weight: 700;
  backdrop-filter: blur(8px);
}

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
  background: rgba(127, 166, 181, 0.06);
  border-color: rgba(127, 166, 181, 0.25);
  box-shadow: inset 0 1px 0 rgba(194, 161, 107, 0.12);
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

.control-room-body--idle .room-status-grid {
  width: min(100%, 1480px);
  align-self: center;
  margin: 0;
  padding: 14px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.58), rgba(13, 18, 20, 0.2));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 32px 90px rgba(0, 0, 0, 0.46),
  inset 0 1px 0 rgba(255, 255, 255, 0.045);
  backdrop-filter: blur(6px);
}

.control-room-body--idle .comp-card {
  min-height: 142px;
  padding: 17px 17px 15px;
  background: rgba(24, 17, 13, 0.82);
  border-color: rgba(255, 255, 255, 0.09);
  box-shadow: 0 18px 46px rgba(0, 0, 0, 0.24);
}

.control-room-body--idle .comp-card:hover {
  transform: translateY(-3px);
  border-color: rgba(194, 161, 107, 0.34);
  box-shadow: 0 22px 54px rgba(0, 0, 0, 0.34),
  0 0 36px -20px rgba(194, 161, 107, 0.7);
}

.control-room-body--idle .card-value {
  font-size: 18px;
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

.room-idle-meta {
  align-self: center;
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 9px 12px;
  border-radius: 999px;
  background: rgba(7, 11, 13, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.065);
  color: rgba(139, 147, 167, 0.86);
  font-size: 11px;
  backdrop-filter: blur(8px);
}

.room-idle-meta strong {
  color: rgba(245, 247, 255, 0.72);
  font-family: var(--mono);
  font-size: 11px;
  font-weight: 700;
}

@keyframes breathe {
  0%, 100% {
    box-shadow: inset 0 1px 0 rgba(194, 161, 107, 0.12), 0 0 20px rgba(127, 166, 181, 0.04);
  }
  50% {
    box-shadow: inset 0 1px 0 rgba(194, 161, 107, 0.18), 0 0 32px rgba(127, 166, 181, 0.10);
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
  margin-bottom: 24px;
}

@media (max-width: 1100px) {
  .cards-grid {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .control-room-body--idle {
    min-height: 100dvh;
    padding-top: 56px;
  }

  .control-room-body--idle .room-status-grid {
    width: min(100%, 940px);
  }
}

@media (max-width: 760px) {
  .cards-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .control-room-body--idle {
    gap: 22px;
    padding: 36px 16px 24px;
    overflow: visible;
  }

  .room-idle-landing {
    align-items: center;
  }

  .room-idle-title {
    font-size: clamp(36px, 12vw, 52px);
  }

  .room-idle-subtitle {
    font-size: 15px;
  }

  .room-idle-actions {
    align-items: stretch;
    width: 100%;
  }

  .room-idle-remote-button,
  .room-idle-status {
    justify-content: center;
    width: 100%;
  }

  .control-room-body--idle .room-status-grid {
    padding: 10px;
  }

  .control-room-body--idle .comp-card {
    min-height: 126px;
    padding: 14px;
  }
}

@media (max-width: 520px) {
  .cards-grid {
    grid-template-columns: 1fr;
  }

  .room-idle-meta {
    width: 100%;
    border-radius: 14px;
  }
}
</style>
