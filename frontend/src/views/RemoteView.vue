<template>
  <div class="view-content view-ambient">
    <div :style="{ backgroundImage: `url(${activeBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${heroBg})` }" class="view-hero-bg">
      <div class="view-hero-eyebrow">{{ $t('x-nav-operation-section') }}</div>
      <h1 class="view-hero-title">{{ $t('x-remote-title') }}</h1>
      <div class="view-hero-sub">{{ $t('x-remote-subtitle') }}</div>
    </div>

    <div class="view-body">
      <div :class="['remote-layout', !hasNowPlaying && 'remote-layout--solo']">
        <div class="remote-device">
          <!-- OLED status strip -->
          <div class="remote-screen">
            <div v-if="stateLoading" class="remote-screen-loading">…</div>
            <template v-else>
              <div class="remote-screen-row">
                <span :class="stateDotClass" class="s-dot"></span>
                <span class="remote-screen-state">{{ playstateLabel }}</span>
              </div>
              <div class="remote-screen-title">{{ state.ActiveSession?.title || $t('x-remote-idle') }}</div>
            </template>
          </div>

          <div class="remote-body">
            <!-- Power row -->
            <div class="remote-group remote-group--power">
              <button :aria-label="$t('x-remote-key-power-on')" class="remote-key remote-key--labeled remote-key--on"
                      @click="key('PON')">
                <Power :size="16" :stroke-width="2.25"/>
                <span>{{ $t('x-remote-key-power-on') }}</span>
              </button>
              <button :aria-label="$t('x-remote-key-eject')" class="remote-key" @click="key('EJT')">
                <Disc3 :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-power-off')" class="remote-key remote-key--labeled remote-key--off"
                      @click="key('POF')">
                <PowerOff :size="16" :stroke-width="2.25"/>
                <span>{{ $t('x-remote-key-power-off') }}</span>
              </button>
            </div>

            <div class="remote-divider"><span>{{ $t('x-remote-section-navigation') }}</span></div>

            <!-- D-pad -->
            <div class="remote-dpad">
              <button :aria-label="$t('x-remote-key-up')" class="remote-dpad__btn remote-dpad__btn--up"
                      @click="key('NUP')">
                <ChevronUp :size="18" :stroke-width="2.25"/>
              </button>
              <button :aria-label="$t('x-remote-key-left')" class="remote-dpad__btn remote-dpad__btn--left"
                      @click="key('NLT')">
                <ChevronLeft :size="18" :stroke-width="2.25"/>
              </button>
              <button :aria-label="$t('x-remote-key-ok')" class="remote-dpad__btn remote-dpad__btn--ok"
                      @click="key('SEL')">
                {{ $t('x-remote-key-ok') }}
              </button>
              <button :aria-label="$t('x-remote-key-right')" class="remote-dpad__btn remote-dpad__btn--right"
                      @click="key('NRT')">
                <ChevronRight :size="18" :stroke-width="2.25"/>
              </button>
              <button :aria-label="$t('x-remote-key-down')" class="remote-dpad__btn remote-dpad__btn--down"
                      @click="key('NDN')">
                <ChevronDown :size="18" :stroke-width="2.25"/>
              </button>
            </div>

            <div class="remote-divider"><span>{{ $t('x-remote-section-info') }}</span></div>

            <!-- Info / audio / sub -->
            <div class="remote-group remote-group--info">
              <button :aria-label="$t('x-remote-key-osd')" class="remote-key" @click="key('OSD')">
                <Info :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-extended-info')" class="remote-key" @click="key('INH')">
                <ListVideo :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-audio')" class="remote-key remote-key--accent" @click="key('AUD')">
                <Music2 :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-subtitles')" class="remote-key" @click="key('SUB')">
                <Subtitles :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-return')" class="remote-key" @click="key('RET')">
                <CornerUpLeft :size="16" :stroke-width="2"/>
              </button>
            </div>

            <div class="remote-divider"><span>{{ $t('x-remote-section-playback') }}</span></div>

            <!-- Transport -->
            <div class="remote-group remote-group--transport">
              <button :aria-label="$t('x-remote-key-stop')" class="remote-key" @click="key('STP')">
                <Square :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-play')" class="remote-key remote-key--accent" @click="key('PLA')">
                <Play :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-pause')" class="remote-key" @click="key('PAU')">
                <Pause :size="16" :stroke-width="2"/>
              </button>
            </div>
            <div class="remote-group remote-group--seek">
              <button :aria-label="$t('x-remote-key-previous')" class="remote-key" @click="key('PRE')">
                <SkipBack :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-rewind')" class="remote-key" @click="key('REV')">
                <Rewind :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-fast-forward')" class="remote-key" @click="key('FWD')">
                <FastForward :size="16" :stroke-width="2"/>
              </button>
              <button :aria-label="$t('x-remote-key-next')" class="remote-key" @click="key('NXT')">
                <SkipForward :size="16" :stroke-width="2"/>
              </button>
            </div>
          </div>
        </div>

        <div v-if="hasNowPlaying" class="panel now-playing">
          <div class="panel-head">
            <h2 class="panel-title">{{ $t('x-remote-now-playing-title') }}</h2>
          </div>
          <div class="panel-body now-playing-body">
            <img
                v-if="posterSrc && !posterError"
                :alt="state.ActiveSession?.title || ''"
                :src="posterSrc"
                class="now-playing-poster"
                @error="posterError = true"
            />
            <dl class="now-playing-info">
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-status') }}</dt>
                <dd>{{ playstateLabel }}</dd>
              </div>
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-title') }}</dt>
                <dd>
                  {{ state.ActiveSession?.title || '—' }}
                  <span v-if="state.ActiveSession?.production_year" class="now-playing-year">
                    ({{ state.ActiveSession.production_year }})
                  </span>
                </dd>
              </div>
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-protocol') }}</dt>
                <dd>{{ protocolLabel }}</dd>
              </div>
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-server') }}</dt>
                <dd class="mono">{{ state.ActiveSession?.content_server || '—' }}</dd>
              </div>
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-folder') }}</dt>
                <dd class="mono truncate">{{ state.ActiveSession?.content_directory || '—' }}</dd>
              </div>
              <div class="now-playing-row">
                <dt>{{ $t('x-remote-info-file') }}</dt>
                <dd class="mono truncate">{{ state.ActiveSession?.playback_file_name || '—' }}</dd>
              </div>
              <div v-if="state.ActiveSession?.playback_file_format" class="now-playing-row">
                <dt>{{ $t('x-remote-info-format') }}</dt>
                <dd class="mono">{{ state.ActiveSession.playback_file_format.toUpperCase() }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {computed, onMounted, ref} from 'vue'
import {useI18n} from 'vue-i18n'
import {
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  ChevronUp,
  CornerUpLeft,
  Disc3,
  FastForward,
  Info,
  ListVideo,
  Music2,
  Pause,
  Play,
  Power,
  PowerOff,
  Rewind,
  SkipBack,
  SkipForward,
  Square,
  Subtitles,
} from '@lucide/vue'
import {api} from '../api/index.js'
import heroBg from '../assets/backgrounds/bg-control-room.png'
import {useToast} from '../composables/useToast.js'
import {usePoll} from '../composables/usePoll.js'

const {t} = useI18n()
const toast = useToast()

const state = ref({})
const stateLoading = ref(true)

const activeBg = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  return itemId ? `/api/now-playing/backdrop?item=${itemId}` : heroBg
})

const hasNowPlaying = computed(() => Boolean(state.value.ActiveSession?.media_item_id))

const posterError = ref(false)
const posterSrc = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  if (!itemId) {
    posterError.value = false
    return null
  }
  return `/api/now-playing/poster?item=${itemId}`
})

const protocolLabel = computed(() => {
  const protocol = state.value.ActiveSession?.network_protocol
  if (protocol === 'cifs') return t('x-remote-protocol-smb')
  if (protocol === 'nfs') return t('x-remote-protocol-nfs')
  return '—'
})

usePoll(refreshState, 5000)

const playstateLabel = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return t('x-remote-not-connected')
  if (ps === 'Free') return t('x-remote-free')
  if (ps === 'Loading') return t('x-remote-loading')
  if (ps === 'Playing') return t('x-remote-playing')
  if (ps === 'Replay') return t('x-remote-replay')
  return ps || '—'
})

const stateDotClass = computed(() => {
  const ps = state.value.Playstate
  if (ps === 'Not_Connected') return 'err'
  if (ps === 'Playing') return 'ok pulse'
  if (ps === 'Loading') return 'warn pulse'
  return 'dim'
})

async function refreshState() {
  try {
    state.value = await api.getState()
  } catch { /* ignore */
  }
}

onMounted(async () => {
  try {
    state.value = await api.getState()
  } finally {
    stateLoading.value = false
  }
})

async function key(k) {
  try {
    await api.sendKey(k)
  } catch (e) {
    toast.error(e.message)
  }
}
</script>

<style scoped>
.remote-layout {
  display: flex;
  gap: 32px;
  align-items: flex-start;
  max-width: 1180px;
}

.remote-layout--solo {
  justify-content: center;
}

@media (max-width: 760px) {
  .remote-layout {
    flex-direction: column;
    align-items: center;
    gap: 28px;
  }
}

/* ─── REMOTE DEVICE SHELL ────────────────────────────────────────────── */
.remote-device {
  width: 296px;
  flex-shrink: 0;
  padding: 18px;
  border-radius: 28px;
  background: linear-gradient(160deg, rgba(255, 255, 255, 0.05), rgba(255, 255, 255, 0.01)), var(--bg-panel);
  border: 1px solid var(--panel-border);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.45),
  inset 0 1px 0 var(--panel-specular),
  0 0 56px -12px rgba(47, 128, 237, 0.42);
}

.remote-screen {
  border-radius: 14px;
  background: #04060c;
  border: 1px solid rgba(86, 204, 242, 0.14);
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.6);
  padding: 12px 14px;
  min-height: 56px;
  font-family: var(--mono);
  margin-bottom: 16px;
}

.remote-screen-loading {
  font-size: 10px;
  color: var(--text-subtle);
}

.remote-screen-row {
  display: flex;
  align-items: center;
  gap: 7px;
  margin-bottom: 3px;
}

.remote-screen-state {
  font-size: 10px;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--text-muted);
}

.remote-screen-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-body {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.remote-divider {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 14px 0 10px;
}

.remote-divider::before,
.remote-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: var(--panel-border);
}

.remote-divider span {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--text-subtle);
  white-space: nowrap;
}

/* ─── KEYS ───────────────────────────────────────────────────────────── */
.remote-group {
  display: flex;
  justify-content: center;
  gap: 8px;
  width: 100%;
}

.remote-group--power {
  justify-content: space-between;
}

.remote-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  padding: 0;
  border-radius: 10px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: var(--bg-panel-elevated);
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, transform 0.1s ease;
}

.remote-key--labeled {
  width: auto;
  gap: 6px;
  padding: 0 12px;
}

.remote-key:hover {
  background: rgba(255, 255, 255, 0.07);
  border-color: rgba(255, 255, 255, 0.16);
  color: var(--text-main);
  transform: translateY(-1px);
}

.remote-key:active {
  transform: translateY(0);
}

.remote-key:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(86, 204, 242, 0.16);
}

.remote-key--accent {
  color: var(--accent-secondary);
  border-color: rgba(86, 204, 242, 0.22);
  background: rgba(86, 204, 242, 0.08);
}

.remote-key--accent:hover {
  background: rgba(86, 204, 242, 0.16);
  border-color: rgba(86, 204, 242, 0.34);
  color: var(--accent-secondary);
}

.remote-key--on {
  color: var(--status-success);
  border-color: rgba(55, 230, 138, 0.22);
  background: rgba(55, 230, 138, 0.08);
}

.remote-key--on:hover {
  background: rgba(55, 230, 138, 0.16);
  border-color: rgba(55, 230, 138, 0.34);
  color: var(--status-success);
}

.remote-key--off {
  color: var(--status-danger);
  border-color: rgba(255, 92, 122, 0.22);
  background: rgba(255, 92, 122, 0.08);
}

.remote-key--off:hover {
  background: rgba(255, 92, 122, 0.16);
  border-color: rgba(255, 92, 122, 0.34);
  color: var(--status-danger);
}

/* ─── D-PAD ──────────────────────────────────────────────────────────── */
.remote-dpad {
  display: grid;
  grid-template-areas:
    ".    up    ."
    "left ok    right"
    ".    down  .";
  grid-template-columns: 46px 52px 46px;
  grid-template-rows: 40px 52px 40px;
  gap: 3px;
  width: fit-content;
  margin: 0 auto;
}

.remote-dpad__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: var(--bg-panel-elevated);
  color: var(--text-muted);
  cursor: pointer;
  transition: background 0.14s ease, color 0.14s ease;
}

.remote-dpad__btn:hover {
  background: rgba(255, 255, 255, 0.08);
  color: var(--text-main);
}

.remote-dpad__btn:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(86, 204, 242, 0.16);
  z-index: 1;
}

.remote-dpad__btn--up {
  grid-area: up;
  border-radius: 12px 12px 0 0;
}

.remote-dpad__btn--left {
  grid-area: left;
  border-radius: 12px 0 0 12px;
}

.remote-dpad__btn--right {
  grid-area: right;
  border-radius: 0 12px 12px 0;
}

.remote-dpad__btn--down {
  grid-area: down;
  border-radius: 0 0 12px 12px;
}

.remote-dpad__btn--ok {
  grid-area: ok;
  border-radius: 50%;
  background: var(--accent-primary);
  border-color: var(--accent-primary);
  color: #fff;
  font-family: var(--font);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.04em;
  box-shadow: 0 6px 18px rgba(47, 128, 237, 0.35);
}

.remote-dpad__btn--ok:hover {
  background: var(--accent-secondary);
  border-color: var(--accent-secondary);
  color: #07101c;
}

/* ─── NOW PLAYING PANEL ──────────────────────────────────────────────── */
.now-playing {
  flex: 1;
  min-width: 420px;
  max-width: 760px;
  align-self: flex-start;
}

.now-playing-body {
  display: flex;
  gap: 24px;
  align-items: stretch;
}

.now-playing-poster {
  width: 190px;
  height: 100%;
  object-fit: cover;
  border-radius: 8px;
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.55);
  display: block;
  flex-shrink: 0;
}

.now-playing-info {
  flex: 1;
  min-width: 0;
}

.now-playing-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  padding: 9px 0;
  border-bottom: 1px solid var(--panel-border);
}

.now-playing-row:first-child {
  padding-top: 0;
}

.now-playing-row:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.now-playing-row dt {
  font-size: 10px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--text-subtle);
  white-space: nowrap;
}

.now-playing-row dd {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-main);
  text-align: right;
  min-width: 0;
}

.now-playing-year {
  font-weight: 500;
  color: var(--text-muted);
}

.now-playing-row dd.mono {
  font-family: var(--mono);
  font-size: 12px;
  font-weight: 400;
  color: var(--text-muted);
}

.now-playing-row dd.truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

@media (max-width: 760px) {
  .now-playing {
    width: 100%;
    min-width: 0;
    max-width: 360px;
  }

  .now-playing-body {
    gap: 14px;
  }

  .now-playing-poster {
    width: 100px;
  }
}
</style>
