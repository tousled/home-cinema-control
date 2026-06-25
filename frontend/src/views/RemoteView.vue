<template>
  <div class="view-content view-ambient remote-view">
    <div :style="{ backgroundImage: `url(${remoteBg})` }" class="ambient-bg"></div>
    <div :style="{ backgroundImage: `url(${remoteBg})` }" class="remote-scene-bg"></div>

    <div class="view-body remote-view-body">
      <section :class="['remote-experience', hasNowPlaying ? 'remote-experience--playing' : 'remote-experience--idle']">
        <div class="remote-showcase">
          <div class="remote-showcase-kicker">
            <span :class="stateDotClass" class="s-dot"></span>
            <span>{{ hasNowPlaying ? $t('x-remote-now-playing-title') : $t('x-nav-operation-section') }}</span>
          </div>

          <p v-if="!hasNowPlaying" class="remote-showcase-subtitle">
            {{ $t('x-remote-subtitle') }}
          </p>

          <div v-if="hasNowPlaying" class="remote-media-deck">
            <div class="remote-poster-frame">
              <img
                  v-if="posterSrc && !posterError"
                  :alt="state.ActiveSession?.title || ''"
                  :src="posterSrc"
                  class="remote-poster"
                  @error="posterError = true"
              />
              <div v-else class="remote-poster-fallback">
                {{ state.ActiveSession?.title || 'HCC' }}
              </div>
            </div>

            <div class="remote-media-details">
              <div v-if="state.ActiveSession?.production_year" class="remote-media-year">
                {{ state.ActiveSession.production_year }}
              </div>

              <div class="remote-media-pills">
                <div class="remote-media-pill">
                  <span>{{ $t('x-remote-info-status') }}</span>
                  <strong>{{ playstateLabel }}</strong>
                </div>
                <div class="remote-media-pill">
                  <span>{{ $t('x-remote-info-protocol') }}</span>
                  <strong>{{ protocolLabel }}</strong>
                </div>
                <div v-if="state.ActiveSession?.playback_file_format" class="remote-media-pill">
                  <span>{{ $t('x-remote-info-format') }}</span>
                  <strong>{{ state.ActiveSession.playback_file_format.toUpperCase() }}</strong>
                </div>
              </div>

              <dl class="remote-media-info">
                <div class="remote-media-row">
                  <dt>{{ $t('x-remote-info-server') }}</dt>
                  <dd class="mono">{{ state.ActiveSession?.content_server || '—' }}</dd>
                </div>
                <div class="remote-media-row">
                  <dt>{{ $t('x-remote-info-folder') }}</dt>
                  <dd class="mono truncate">{{ state.ActiveSession?.content_directory || '—' }}</dd>
                </div>
                <div class="remote-media-row">
                  <dt>{{ $t('x-remote-info-file') }}</dt>
                  <dd class="mono truncate">{{ state.ActiveSession?.playback_file_name || '—' }}</dd>
                </div>
              </dl>
            </div>
          </div>
        </div>

        <aside class="remote-control-dock">
          <div :class="['remote-device', hasNowPlaying && 'remote-device--active']">
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
        </aside>
      </section>
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
import idleSceneBg from '../assets/backgrounds/bg-control-room-idle.png'
import {useToast} from '../composables/useToast.js'
import {usePoll} from '../composables/usePoll.js'

const {t} = useI18n()
const toast = useToast()

const state = ref({})

const activeBg = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  return itemId ? `/api/v1/now-playing/backdrop?item=${itemId}` : idleSceneBg
})

const hasNowPlaying = computed(() => Boolean(state.value.ActiveSession?.title))

const remoteBg = computed(() => hasNowPlaying.value ? activeBg.value : idleSceneBg)

const posterError = ref(false)
const posterSrc = computed(() => {
  const itemId = state.value.ActiveSession?.media_item_id
  if (!itemId) {
    posterError.value = false
    return null
  }
  return `/api/v1/now-playing/poster?item=${itemId}`
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
  state.value = await api.getState()
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
.remote-view {
  position: relative;
  min-height: 100dvh;
}

.remote-scene-bg {
  position: fixed;
  inset: 0;
  z-index: 0;
  pointer-events: none;
  background-position: center;
  background-size: cover;
  opacity: 0.92;
  filter: saturate(1.1) contrast(1.04) brightness(1.04);
}

.remote-scene-bg::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(90deg, rgba(7, 11, 13, 0.64), rgba(7, 11, 13, 0.22) 45%, rgba(7, 11, 13, 0.46)),
  linear-gradient(180deg, rgba(7, 11, 13, 0.02), rgba(7, 11, 13, 0.32) 58%, rgba(7, 11, 13, 0.72));
}

.remote-view-body {
  position: relative;
  z-index: 1;
  min-height: 100dvh;
  padding: clamp(32px, 6vh, 72px) clamp(22px, 4vw, 68px);
}

.remote-experience {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(310px, 360px);
  align-items: center;
  gap: clamp(28px, 4vw, 64px);
  width: min(100%, 1580px);
  min-height: calc(100dvh - clamp(64px, 12vh, 144px));
  margin: 0 auto;
}

.remote-experience--idle {
  grid-template-columns: minmax(0, 1fr) minmax(310px, 380px);
}

.remote-showcase {
  min-width: 0;
}

.remote-experience--idle .remote-showcase {
  align-self: center;
  max-width: 760px;
}

.remote-showcase-kicker {
  display: inline-flex;
  align-items: center;
  gap: 9px;
  padding: 7px 10px;
  border-radius: 999px;
  background: rgba(7, 11, 13, 0.42);
  border: 1px solid rgba(255, 255, 255, 0.075);
  color: var(--accent-secondary);
  font-size: 10px;
  font-weight: 900;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  backdrop-filter: blur(8px);
}

.remote-showcase-title {
  max-width: 1050px;
  margin: 18px 0 0;
  color: var(--text-main);
  font-size: clamp(46px, 6vw, 100px);
  font-weight: 900;
  line-height: 0.94;
  letter-spacing: 0;
  text-wrap: balance;
  text-shadow: 0 30px 88px rgba(0, 0, 0, 0.72);
}

.remote-experience--playing .remote-showcase-title {
  max-width: 980px;
  font-size: clamp(42px, 5.4vw, 88px);
}

.remote-showcase-subtitle {
  max-width: 620px;
  margin: 18px 0 0;
  color: rgba(245, 247, 255, 0.72);
  font-size: clamp(17px, 1.35vw, 22px);
  line-height: 1.45;
  text-wrap: balance;
}

.remote-media-deck {
  display: grid;
  grid-template-columns: minmax(220px, 330px) minmax(0, 1fr);
  gap: clamp(22px, 3vw, 40px);
  align-items: end;
  width: min(100%, 1030px);
  margin-top: clamp(24px, 4vh, 44px);
}

.remote-poster-frame {
  position: relative;
  width: 100%;
  aspect-ratio: 2 / 3;
  padding: 5px;
  border-radius: 18px;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.26), rgba(194, 161, 107, 0.18) 42%, rgba(245, 165, 36, 0.22));
  box-shadow: 0 32px 84px rgba(0, 0, 0, 0.62),
  0 0 58px -14px rgba(194, 161, 107, 0.52);
}

.remote-poster-frame::after {
  content: '';
  position: absolute;
  inset: 5px;
  pointer-events: none;
  border-radius: 13px;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.13);
}

.remote-poster,
.remote-poster-fallback {
  display: flex;
  width: 100%;
  height: 100%;
  border-radius: 13px;
}

.remote-poster {
  object-fit: cover;
}

.remote-poster-fallback {
  align-items: flex-end;
  justify-content: center;
  padding: 26px;
  background: radial-gradient(circle at 50% 18%, rgba(220, 228, 226, 0.18), transparent 32%),
  linear-gradient(160deg, #172126, #0A0F12 58%, #2A1114);
  color: var(--text-main);
  font-size: 24px;
  font-weight: 800;
  text-align: center;
}

.remote-media-details {
  min-width: 0;
  padding: 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(13, 18, 20, 0.72), rgba(13, 18, 20, 0.42));
  border: 1px solid rgba(255, 255, 255, 0.085);
  box-shadow: 0 28px 74px rgba(0, 0, 0, 0.38);
  backdrop-filter: blur(8px);
}

.remote-media-year {
  margin-bottom: 13px;
  color: rgba(245, 247, 255, 0.56);
  font-size: 15px;
  font-weight: 800;
}

.remote-media-pills {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  margin-bottom: 18px;
}

.remote-media-pill {
  min-width: 0;
  padding: 12px 13px;
  border-radius: 12px;
  background: rgba(7, 11, 13, 0.44);
  border: 1px solid rgba(255, 255, 255, 0.065);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.035);
}

.remote-media-pill span {
  display: block;
  margin-bottom: 5px;
  color: rgba(139, 147, 167, 0.78);
  font-size: 9px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
}

.remote-media-pill strong {
  display: block;
  overflow: hidden;
  color: var(--text-main);
  font-size: 13px;
  font-weight: 800;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-media-info {
  display: grid;
  gap: 8px;
  min-width: 0;
  margin: 0;
}

.remote-media-row {
  display: grid;
  grid-template-columns: 118px minmax(0, 1fr);
  align-items: baseline;
  gap: 18px;
  padding: 11px 0;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
}

.remote-media-row:last-child {
  border-bottom: 1px solid rgba(255, 255, 255, 0.06);
}

.remote-media-row dt {
  color: rgba(139, 147, 167, 0.62);
  font-size: 10px;
  font-weight: 800;
  letter-spacing: 0;
  text-transform: uppercase;
  white-space: nowrap;
}

.remote-media-row dd {
  min-width: 0;
  margin: 0;
  color: rgba(245, 247, 255, 0.72);
  font-size: 12px;
  font-weight: 400;
  text-align: right;
}

.remote-media-row dd.truncate {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.remote-control-dock {
  display: flex;
  justify-content: center;
  min-width: 0;
}

.remote-device {
  position: relative;
  width: 336px;
  flex-shrink: 0;
  padding: 22px;
  border-radius: 34px;
  background: radial-gradient(circle at 50% 0%, rgba(194, 161, 107, 0.16), transparent 36%),
  linear-gradient(155deg, rgba(255, 255, 255, 0.07), rgba(255, 255, 255, 0.015) 42%, rgba(0, 0, 0, 0.2)),
  repeating-linear-gradient(101deg, rgba(255, 255, 255, 0.016) 0px, rgba(255, 255, 255, 0.016) 1px, transparent 1px, transparent 4px),
  #172228;
  border: 1px solid rgba(255, 255, 255, 0.08);
  box-shadow: 0 30px 86px rgba(0, 0, 0, 0.52),
  0 0 70px -18px rgba(194, 161, 107, 0.46),
  inset 0 1px 0 var(--panel-specular),
  inset 0 -18px 44px rgba(0, 0, 0, 0.28);
  transition: box-shadow 0.6s ease;
}

.remote-device--active {
  animation: remote-device-glow 3.2s ease-in-out infinite;
}

@keyframes remote-device-glow {
  0%, 100% {
    box-shadow: 0 30px 86px rgba(0, 0, 0, 0.52),
    0 0 70px -18px rgba(194, 161, 107, 0.46),
    inset 0 1px 0 var(--panel-specular),
    inset 0 -18px 44px rgba(0, 0, 0, 0.28);
  }
  50% {
    box-shadow: 0 30px 86px rgba(0, 0, 0, 0.52),
    0 0 88px -10px rgba(194, 161, 107, 0.72),
    inset 0 1px 0 var(--panel-specular),
    inset 0 -18px 44px rgba(0, 0, 0, 0.28);
  }
}

@media (prefers-reduced-motion: reduce) {
  .remote-device--active {
    animation: none;
  }
}

.remote-device::before {
  content: '';
  position: absolute;
  inset: 11px;
  pointer-events: none;
  border-radius: 28px;
  border: 1px solid rgba(255, 255, 255, 0.035);
}

.remote-device::after {
  content: '';
  position: absolute;
  top: 28px;
  right: 22px;
  bottom: 28px;
  width: 1px;
  pointer-events: none;
  background: linear-gradient(to bottom, transparent, rgba(255, 255, 255, 0.12), transparent);
  opacity: 0.4;
}

.remote-body {
  position: relative;
  z-index: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.remote-divider {
  display: flex;
  align-items: center;
  width: 100%;
  gap: 8px;
  margin: 18px 0 12px;
}

.remote-divider::before,
.remote-divider::after {
  content: '';
  flex: 1;
  height: 1px;
  background: linear-gradient(to right, transparent, rgba(255, 255, 255, 0.09), transparent);
  box-shadow: 0 1px 0 rgba(0, 0, 0, 0.4);
}

.remote-divider span {
  color: rgba(139, 147, 167, 0.6);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  white-space: nowrap;
}

.remote-group {
  display: flex;
  justify-content: center;
  width: 100%;
  gap: 9px;
}

.remote-group--power {
  justify-content: space-between;
}

.remote-key {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 42px;
  height: 42px;
  padding: 0;
  border-radius: 13px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02)),
  var(--bg-panel-elevated);
  color: var(--text-muted);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07),
  inset 0 -2px 4px rgba(0, 0, 0, 0.22),
  0 8px 18px rgba(0, 0, 0, 0.24);
  font-family: var(--font);
  font-size: 11px;
  font-weight: 700;
  cursor: pointer;
  transition: background 0.14s ease, border-color 0.14s ease, color 0.14s ease, transform 0.1s ease, box-shadow 0.14s ease;
}

.remote-key--labeled {
  width: auto;
  gap: 7px;
  padding: 0 13px;
}

.remote-key:hover {
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.11), rgba(255, 255, 255, 0.035)),
  #1B272B;
  border-color: rgba(255, 255, 255, 0.16);
  color: var(--text-main);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.08),
  inset 0 -2px 4px rgba(0, 0, 0, 0.18),
  0 12px 24px rgba(0, 0, 0, 0.3);
  transform: translateY(-1px);
}

.remote-key:active {
  transform: translateY(1px) scale(0.97);
  box-shadow: inset 0 2px 6px rgba(0, 0, 0, 0.42),
  0 4px 10px rgba(0, 0, 0, 0.2);
}

/* Continuous "instrument strip" treatment for the info & seek rows —
   adjoining keys read as one machined bar instead of loose squares. */
.remote-group--info,
.remote-group--seek {
  gap: 0;
  padding: 3px;
  border-radius: 15px;
  background: rgba(0, 0, 0, 0.18);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04),
  inset 0 -1px 0 rgba(0, 0, 0, 0.3);
}

.remote-group--info .remote-key,
.remote-group--seek .remote-key {
  flex: 1;
  border-radius: 11px;
  border-color: transparent;
  background: transparent;
  box-shadow: none;
}

.remote-group--info .remote-key:not(:last-child),
.remote-group--seek .remote-key:not(:last-child) {
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  border-radius: 0;
}

.remote-group--info .remote-key:first-child,
.remote-group--seek .remote-key:first-child {
  border-radius: 11px 0 0 11px;
}

.remote-group--info .remote-key:last-child,
.remote-group--seek .remote-key:last-child {
  border-radius: 0 11px 11px 0;
}

.remote-group--info .remote-key:hover,
.remote-group--seek .remote-key:hover {
  background: rgba(255, 255, 255, 0.06);
  color: var(--text-main);
  transform: none;
  box-shadow: none;
}

.remote-group--info .remote-key:active,
.remote-group--seek .remote-key:active {
  transform: none;
  background: rgba(0, 0, 0, 0.2);
}

.remote-group--info .remote-key--accent,
.remote-group--seek .remote-key--accent {
  color: var(--accent-secondary);
  background: rgba(194, 161, 107, 0.1);
}

.remote-group--info .remote-key--accent:hover,
.remote-group--seek .remote-key--accent:hover {
  color: var(--accent-secondary);
  background: rgba(194, 161, 107, 0.18);
}

/* Transport row keeps its primary action as a larger, glowing focal button. */
.remote-group--transport {
  align-items: center;
  gap: 14px;
  margin-bottom: 2px;
}

.remote-group--transport .remote-key--accent {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  color: #fff;
  border-color: rgba(194, 161, 107, 0.5);
  background: radial-gradient(circle at 36% 26%, rgba(255, 255, 255, 0.22), transparent 38%),
  var(--accent-primary);
  box-shadow: 0 12px 28px rgba(127, 166, 181, 0.46),
  0 0 0 6px rgba(194, 161, 107, 0.08),
  inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.remote-group--transport .remote-key--accent:hover {
  background: radial-gradient(circle at 36% 26%, rgba(255, 255, 255, 0.26), transparent 38%),
  var(--accent-secondary);
  border-color: rgba(194, 161, 107, 0.7);
  color: #071014;
  transform: translateY(-1px);
}

.remote-key:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(194, 161, 107, 0.16);
}

.remote-key--accent {
  color: var(--accent-secondary);
  border-color: rgba(194, 161, 107, 0.24);
  background: linear-gradient(180deg, rgba(194, 161, 107, 0.15), rgba(194, 161, 107, 0.055)),
  #172126;
}

.remote-key--accent:hover {
  color: var(--accent-secondary);
  border-color: rgba(194, 161, 107, 0.38);
  background: linear-gradient(180deg, rgba(194, 161, 107, 0.24), rgba(194, 161, 107, 0.08)),
  #223136;
}

.remote-key--on {
  color: var(--status-success);
  border-color: rgba(55, 230, 138, 0.24);
  background: linear-gradient(180deg, rgba(55, 230, 138, 0.15), rgba(55, 230, 138, 0.05)),
  #10241d;
}

.remote-key--on:hover {
  color: var(--status-success);
  border-color: rgba(55, 230, 138, 0.38);
  background: linear-gradient(180deg, rgba(55, 230, 138, 0.23), rgba(55, 230, 138, 0.08)),
  #122b22;
}

.remote-key--off {
  color: var(--status-danger);
  border-color: rgba(255, 92, 122, 0.24);
  background: linear-gradient(180deg, rgba(255, 92, 122, 0.14), rgba(255, 92, 122, 0.05)),
  #291621;
}

.remote-key--off:hover {
  color: var(--status-danger);
  border-color: rgba(255, 92, 122, 0.38);
  background: linear-gradient(180deg, rgba(255, 92, 122, 0.22), rgba(255, 92, 122, 0.08)),
  #321725;
}

.remote-dpad {
  position: relative;
  display: grid;
  grid-template-areas:
    ".    up    ."
    "left ok    right"
    ".    down  .";
  grid-template-columns: 54px 64px 54px;
  grid-template-rows: 48px 64px 48px;
  width: fit-content;
  gap: 4px;
  margin: 4px auto 2px;
  padding: 14px;
  border-radius: 30px;
  background: radial-gradient(circle at 50% 50%, rgba(194, 161, 107, 0.14), transparent 64%),
  rgba(0, 0, 0, 0.18);
  border: 1px solid rgba(255, 255, 255, 0.05);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.04),
  inset 0 -12px 26px rgba(0, 0, 0, 0.22);
}

.remote-dpad__btn {
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px solid rgba(255, 255, 255, 0.09);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.08), rgba(255, 255, 255, 0.02)),
  var(--bg-panel-elevated);
  color: var(--text-muted);
  box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.06);
  cursor: pointer;
  transition: background 0.14s ease, color 0.14s ease, transform 0.1s ease, border-color 0.14s ease;
}

.remote-dpad__btn:hover {
  color: var(--text-main);
  border-color: rgba(255, 255, 255, 0.16);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.12), rgba(255, 255, 255, 0.035)),
  #1B272B;
  transform: translateY(-1px);
}

.remote-dpad__btn:focus-visible {
  z-index: 1;
  outline: none;
  box-shadow: 0 0 0 3px rgba(194, 161, 107, 0.16);
}

.remote-dpad__btn--up {
  grid-area: up;
  border-radius: 14px 14px 5px 5px;
}

.remote-dpad__btn--left {
  grid-area: left;
  border-radius: 14px 5px 5px 14px;
}

.remote-dpad__btn--right {
  grid-area: right;
  border-radius: 5px 14px 14px 5px;
}

.remote-dpad__btn--down {
  grid-area: down;
  border-radius: 5px 5px 14px 14px;
}

.remote-dpad__btn--ok {
  grid-area: ok;
  border-radius: 50%;
  background: radial-gradient(circle at 36% 26%, rgba(255, 255, 255, 0.18), transparent 34%),
  var(--accent-primary);
  border-color: rgba(194, 161, 107, 0.55);
  color: #fff;
  box-shadow: 0 10px 24px rgba(127, 166, 181, 0.42),
  0 0 0 5px rgba(194, 161, 107, 0.1),
  inset 0 1px 0 rgba(255, 255, 255, 0.18);
  font-family: var(--font);
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
}

.remote-dpad__btn--ok:hover {
  color: #071014;
  border-color: rgba(194, 161, 107, 0.72);
  background: radial-gradient(circle at 36% 26%, rgba(255, 255, 255, 0.22), transparent 34%),
  var(--accent-secondary);
}

@media (max-width: 980px) {
  .remote-experience,
  .remote-experience--idle {
    grid-template-columns: 1fr;
    justify-items: center;
    align-items: center;
    gap: 28px;
  }

  .remote-showcase {
    width: 100%;
    max-width: 820px;
    text-align: center;
  }

  .remote-showcase-kicker {
    margin-inline: auto;
  }

  .remote-media-deck {
    grid-template-columns: minmax(180px, 260px) minmax(0, 1fr);
    margin-inline: auto;
    text-align: left;
  }
}

@media (min-width: 1280px) {
  .remote-device {
    width: 352px;
  }
}

@media (min-width: 1680px) {
  .remote-experience {
    grid-template-columns: minmax(0, 1fr) minmax(340px, 390px);
  }
}

@media (max-width: 720px) {
  .remote-view-body {
    padding: 28px 16px 30px;
  }

  .remote-experience {
    min-height: auto;
  }

  .remote-showcase-title,
  .remote-experience--playing .remote-showcase-title {
    font-size: clamp(36px, 12vw, 54px);
  }

  .remote-showcase-subtitle {
    font-size: 15px;
  }

  .remote-media-deck {
    grid-template-columns: 1fr;
    justify-items: center;
    gap: 18px;
  }

  .remote-poster-frame {
    width: min(210px, 66vw);
  }

  .remote-media-details {
    width: 100%;
  }

  .remote-media-pills {
    grid-template-columns: 1fr;
  }

  .remote-media-row {
    grid-template-columns: 1fr;
    gap: 5px;
  }

  .remote-media-row dd {
    text-align: left;
  }

  .remote-device {
    width: min(100%, 336px);
  }
}

@media (max-width: 420px) {
  .remote-device {
    padding: 16px;
  }

  .remote-key--labeled {
    padding: 0 10px;
  }
}
</style>
