<template>
  <div class="app-shell" @keydown.esc="mobileNavOpen = false">
    <a class="skip-link" href="#main-content">Skip to content</a>
    <button
        :aria-expanded="mobileNavOpen"
        aria-controls="app-sidebar"
        aria-label="Open navigation"
        class="mobile-nav-toggle"
        type="button"
        @click="mobileNavOpen = !mobileNavOpen"
    >
      <img :src="brandMark" alt="" aria-hidden="true" class="mobile-nav-toggle-mark">
      <span class="mobile-nav-toggle-title">Home Cinema Control</span>
      <span aria-hidden="true" class="mobile-nav-toggle-lines">
        <span></span>
        <span></span>
      </span>
    </button>

    <div
        v-if="mobileNavOpen"
        aria-hidden="true"
        class="mobile-nav-backdrop"
        @click="mobileNavOpen = false"
    ></div>

    <!-- Sidebar -->
    <aside id="app-sidebar" :class="['sidebar', mobileNavOpen && 'sidebar--open']">
      <!-- Logo -->
      <div class="sidebar-logo">
        <img :src="brandMark" alt="" aria-hidden="true" class="logo-mark">
        <div class="logo-text">
          <span class="logo-name">Home Cinema</span>
          <span class="logo-sub">Control</span>
        </div>
      </div>

      <!-- Nav -->
      <nav aria-label="Main navigation" class="sidebar-nav">
        <div class="nav-section">
          <p class="nav-section-label">{{ $t('x-nav-operation-section') }}</p>
          <RouterLink class="nav-item" to="/control-room">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <rect height="7" rx="1" width="7" x="3" y="3"/>
              <rect height="7" rx="1" width="7" x="14" y="3"/>
              <rect height="7" rx="1" width="7" x="3" y="14"/>
              <rect height="7" rx="1" width="7" x="14" y="14"/>
            </svg>
            <span>{{ $t('x-nav-control-room') }}</span>
          </RouterLink>
          <RouterLink class="nav-item" to="/remote">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <rect height="20" rx="4" width="8" x="8" y="2"/>
              <path d="M12 6v4"/>
              <circle cx="12" cy="14" fill="currentColor" r="1" stroke="none"/>
            </svg>
            <span>{{ $t('x-nav-remote') }}</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <p class="nav-section-label">{{ $t('x-nav-config-section') }}</p>
          <RouterLink class="nav-item" to="/media-server">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <rect height="8" rx="2" width="20" x="2" y="2"/>
              <rect height="8" rx="2" width="20" x="2" y="14"/>
              <path d="M6 6h.01"/>
              <path d="M6 18h.01"/>
            </svg>
            <span>{{ $t('x-nav-media-server') }}</span>
            <span :style="{ color: stepDotColor(readiness?.media_server?.status) }" class="nav-dot">●</span>
          </RouterLink>
          <RouterLink class="nav-item" to="/media-player">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <circle cx="12" cy="12" r="10"/>
              <circle cx="12" cy="12" r="3"/>
            </svg>
            <span>{{ $t('x-nav-media-player') }}</span>
            <span :style="{ color: stepDotColor(readiness?.media_player?.status) }" class="nav-dot">●</span>
          </RouterLink>
          <RouterLink class="nav-item" to="/media-paths">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <path d="M8 3 4 7l4 4"/>
              <path d="M4 7h16"/>
              <path d="m16 21 4-4-4-4"/>
              <path d="M20 17H4"/>
            </svg>
            <span>{{ $t('x-nav-paths') }}</span>
            <span :style="{ color: stepDotColor(readiness?.media_paths?.status) }" class="nav-dot">●</span>
          </RouterLink>
          <RouterLink class="nav-item" to="/sala">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <rect height="14" rx="2" width="20" x="2" y="7"/>
              <path d="M17 2 12 7 7 2"/>
            </svg>
            <span>{{ $t('x-nav-sala') }}</span>
            <span :style="{ color: stepDotColor(roomReadinessStatus) }" class="nav-dot">●</span>
          </RouterLink>
        </div>

        <div class="nav-section">
          <p class="nav-section-label">{{ $t('x-nav-support-section') }}</p>
          <RouterLink class="nav-item" to="/status">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <path d="M22 12h-4l-3 9L9 3l-3 9H2"/>
            </svg>
            <span>{{ $t('x-nav-diag') }}</span>
            <span v-if="versionStore.newVersionAvailable" class="nav-dot" style="color:var(--status-warning)">●</span>
          </RouterLink>
          <RouterLink class="nav-item" to="/logs">
            <svg class="nav-icon" fill="none" stroke="currentColor" stroke-linecap="round" stroke-linejoin="round"
                 stroke-width="2" viewBox="0 0 24 24">
              <path d="M3 6h18"/>
              <path d="M3 10h18"/>
              <path d="M3 14h18"/>
              <path d="M3 18h18"/>
            </svg>
            <span>{{ $t('x-nav-logs') }}</span>
          </RouterLink>
        </div>
      </nav>

      <!-- Footer: language picker -->
      <div class="sidebar-footer">
        <button
            :aria-expanded="langOpen"
            aria-haspopup="listbox"
            aria-label="Select language"
            class="lang-picker"
            @click="langOpen = !langOpen"
        >
          <span class="lang-flag">{{ currentLangFlag }}</span>
          <span class="lang-label">{{ currentLang }}</span>
          <span class="lang-chevron">{{ langOpen ? '▲' : '▼' }}</span>
        </button>
        <div v-if="langOpen" class="lang-popover" role="listbox">
          <button
              v-for="l in langs"
              :key="l"
              :aria-selected="l === currentLang"
              role="option"
              :class="['lang-opt', l === currentLang && 'lang-opt-active']"
              @click="setLang(l)"
          >{{ langFlag(l) }} {{ l }}
          </button>
        </div>
      </div>
    </aside>

    <!-- Main -->
    <main id="main-content" class="app-main">
      <RouterView/>
    </main>

    <!-- Toast notifications -->
    <ToastContainer/>

    <!-- Migration modal -->
    <div v-if="showMigration" aria-labelledby="migration-title" aria-modal="true" class="modal-backdrop" role="dialog">
      <div class="modal-box">
        <h2 id="migration-title" class="modal-title">{{ $t('x-migration-title') }}</h2>
        <p class="modal-body">{{ $t('x-migration-description') }}</p>
        <div class="modal-actions">
          <button :disabled="migrating" class="btn-ghost" @click="skipMigration">
            {{ $t('x-migration-skip') }}
          </button>
          <button ref="applyBtn" :disabled="migrating" class="btn-primary" @click="applyMigration">
            {{ migrating ? $t('x-migration-applying') : $t('x-migration-apply') }}
          </button>
        </div>
        <p v-if="migrationError" class="mt-3" style="font-size:13px;color:var(--status-danger)">{{ migrationError }}</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import {onMounted, ref, computed, watch, nextTick} from 'vue'
import {RouterLink, RouterView, useRoute} from 'vue-router'
import {api} from './api/index.js'
import ToastContainer from './components/ToastContainer.vue'
import {useSetupReadiness} from './composables/useSetupReadiness.js'
import {useConfigSectionSave} from './composables/useConfigSectionSave.js'
import {useVersionStore} from './stores/version.js'
import brandMark from './assets/branding/hcc-mark.png'

const {readiness} = useSetupReadiness()
const {saveSection} = useConfigSectionSave()
const versionStore = useVersionStore()
const route = useRoute()
const mobileNavOpen = ref(false)

function stepDotColor(status) {
  if (status === 'verified') return 'var(--status-success)'
  if (status === 'configured') return 'var(--status-success)'
  if (status === 'stale') return 'var(--status-warning)'
  if (status === 'incomplete') return 'var(--status-warning)'
  return 'var(--text-subtle)'
}

const roomReadinessStatus = computed(() => {
  const tvStatus = readiness.value?.tv?.status || 'disabled'
  const avStatus = readiness.value?.av?.status || 'disabled'
  if (tvStatus === 'incomplete' || avStatus === 'incomplete' || tvStatus === 'stale' || avStatus === 'stale') {
    return 'incomplete'
  }
  if (tvStatus === 'verified' || avStatus === 'verified') return 'verified'
  if (tvStatus === 'configured' || avStatus === 'configured') return 'configured'
  return 'disabled'
})

const showMigration = ref(false)
const migrating = ref(false)
const migrationError = ref('')
const applyBtn = ref(null)

watch(() => route.fullPath, () => {
  mobileNavOpen.value = false
})

watch(showMigration, async (val) => {
  if (val) {
    await nextTick()
    applyBtn.value?.focus()
  }
})

const langs = ref([])
const currentLang = ref('')
const langOpen = ref(false)
const fullConfig = ref({})

const currentLangFlag = computed(() => langFlag(currentLang.value))

function langFlag(l) {
  if (l === 'es-ES') return '🇪🇸'
  if (l === 'en-US') return '🇺🇸'
  return '🌐'
}

async function setLang(l) {
  langOpen.value = false
  if (l === currentLang.value) return
  try {
    fullConfig.value.app = {
      ...(fullConfig.value.app || {}),
      language: l,
    }
    await saveSection('app', fullConfig.value.app)
    setTimeout(() => window.location.reload(), 200)
  } catch { /* ignore */
  }
}

onMounted(async () => {
  try {
    const {available} = await api.getMigrationStatus()
    showMigration.value = available
  } catch { /* non-fatal */
  }

  try {
    const data = await api.getConfig()
    fullConfig.value = data
    langs.value = data.langs || []
    currentLang.value = data.app?.language || 'es-ES'
  } catch { /* ignore */
  }
})

async function applyMigration() {
  migrating.value = true
  migrationError.value = ''
  try {
    await api.applyMigration()
    showMigration.value = false
  } catch (e) {
    migrationError.value = e.message
  } finally {
    migrating.value = false
  }
}

async function skipMigration() {
  migrating.value = true
  migrationError.value = ''
  try {
    await api.skipMigration()
    showMigration.value = false
  } catch (e) {
    migrationError.value = e.message
  } finally {
    migrating.value = false
  }
}
</script>

<style>
/* ─── SKIP LINK ──────────────────────────────────────────────────────── */
.skip-link {
  position: absolute;
  top: -100%;
  left: 8px;
  padding: 8px 16px;
  background: var(--accent-primary);
  color: #fff;
  border-radius: 0 0 6px 6px;
  font-size: 13px;
  font-weight: 600;
  z-index: 999;
  text-decoration: none;
}

.skip-link:focus {
  top: 0;
}

/* ─── SHELL LAYOUT ───────────────────────────────────────────────────── */
.app-shell {
  display: flex;
  height: 100vh;
  overflow: hidden;
  background: var(--bg-main);
}

.mobile-nav-toggle,
.mobile-nav-backdrop {
  display: none;
}

.mobile-nav-toggle {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 56px;
  align-items: center;
  gap: 10px;
  padding: 0 14px;
  background: rgba(5, 7, 17, 0.94);
  border: 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.07);
  color: var(--text-main);
  z-index: 260;
  backdrop-filter: blur(14px);
  font-family: var(--font);
}

.mobile-nav-toggle-mark {
  width: 32px;
  height: 32px;
  border-radius: 10px;
  object-fit: cover;
  display: block;
  box-shadow: 0 0 0 1px rgba(184, 135, 70, 0.36), 0 8px 18px rgba(0, 0, 0, 0.22);
}

.mobile-nav-toggle-title {
  flex: 1;
  text-align: left;
  font-size: 13px;
  font-weight: 700;
}

.mobile-nav-toggle-lines {
  display: inline-flex;
  flex-direction: column;
  gap: 5px;
  width: 22px;
}

.mobile-nav-toggle-lines span {
  display: block;
  height: 2px;
  border-radius: 999px;
  background: var(--text-muted);
}


/* ─── SIDEBAR ────────────────────────────────────────────────────────── */
.sidebar {
  width: 208px;
  flex-shrink: 0;
  background: var(--bg-sidebar);
  border-right: 1px solid rgba(255, 255, 255, 0.04);
  display: flex;
  flex-direction: column;
  overflow: visible;
  position: relative;
  z-index: 1;
}

.sidebar-logo {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 18px 16px 16px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
}

.logo-mark {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: block;
  flex-shrink: 0;
  object-fit: cover;
  box-shadow: 0 0 0 1px rgba(184, 135, 70, 0.34), 0 10px 22px rgba(0, 0, 0, 0.26);
}

.logo-text {
  display: flex;
  flex-direction: column;
  line-height: 1.2;
}

.logo-name {
  font-size: 13px;
  font-weight: 800;
  color: var(--text-main);
  letter-spacing: -0.01em;
}

.logo-sub {
  font-size: 12px;
  color: var(--text-subtle);
  font-weight: 700;
  margin-top: 0.25em;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: 12px 10px;
  scrollbar-width: none;
}

.sidebar-nav::-webkit-scrollbar {
  display: none;
}

.nav-section {
  margin-bottom: 4px;
}

.nav-section-label {
  font-size: 12px;
  font-weight: 900;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--text-subtle);
  padding: 10px 8px 5px;
}

.nav-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
  opacity: 0.7;
}

.nav-item:hover .nav-icon,
.nav-item.router-link-active .nav-icon {
  opacity: 1;
}

.nav-dot {
  font-size: 9px;
  margin-left: auto;
  flex-shrink: 0;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 7px 10px;
  border-radius: 6px;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-muted);
  text-decoration: none;
  transition: background 0.1s, color 0.1s;
  margin-bottom: 1px;
}

.nav-item:hover {
  background: rgba(255, 255, 255, 0.04);
  color: var(--text-main);
}

.nav-item.router-link-active {
  background: rgba(47, 128, 237, 0.10);
  color: var(--accent-secondary);
  border-left: 2px solid var(--accent-primary);
  padding-left: 8px;
}

/* ─── SIDEBAR FOOTER / LANG PICKER ──────────────────────────────────── */
.sidebar-footer {
  padding: 12px 10px;
  border-top: 1px solid rgba(255, 255, 255, 0.04);
  position: relative;
}

.lang-picker {
  display: flex;
  align-items: center;
  gap: 7px;
  padding: 7px 10px;
  border-radius: 6px;
  cursor: pointer;
  transition: background 0.1s;
}

.lang-picker:hover {
  background: rgba(255, 255, 255, 0.04);
}

.lang-flag {
  font-size: 14px;
  line-height: 1;
}

.lang-label {
  font-size: 12px;
  color: var(--text-muted);
  font-weight: 500;
  flex: 1;
}

.lang-chevron {
  font-size: 10px;
  color: var(--text-subtle);
}

.lang-popover {
  position: absolute;
  bottom: calc(100% - 4px);
  left: 10px;
  right: 10px;
  background: var(--bg-panel-elevated);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 8px;
  padding: 4px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.lang-opt {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  padding: 8px 10px;
  border-radius: 5px;
  border: none;
  background: none;
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  text-align: left;
  transition: background 0.1s, color 0.1s;
}

.lang-opt:hover {
  background: rgba(255, 255, 255, 0.05);
  color: var(--text-main);
}

.lang-opt-active {
  color: var(--accent-secondary) !important;
}

/* ─── MAIN CONTENT ───────────────────────────────────────────────────── */
.app-main {
  flex: 1;
  overflow-y: auto;
  padding: 0;
}


@media (max-width: 820px) and (orientation: portrait), (max-width: 680px) {
  .app-shell {
    display: block;
    height: 100dvh;
    min-height: 100dvh;
    padding-top: 56px;
  }

  .mobile-nav-toggle {
    display: flex;
  }

  .mobile-nav-backdrop {
    display: block;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.58);
    z-index: 240;
  }

  .sidebar {
    position: fixed;
    top: 0;
    bottom: 0;
    left: 0;
    width: min(84vw, 320px);
    max-width: 320px;
    transform: translateX(-100%);
    transition: transform 0.18s ease;
    z-index: 300;
    box-shadow: 24px 0 72px rgba(0, 0, 0, 0.58);
  }

  .sidebar.sidebar--open {
    transform: translateX(0);
  }

  .app-main {
    width: 100%;
    height: calc(100dvh - 56px);
    overflow-y: auto;
    -webkit-overflow-scrolling: touch;
  }
}

/* ─── MIGRATION MODAL ────────────────────────────────────────────────── */
.modal-backdrop {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.65);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 200;
}

.modal-box {
  background: var(--bg-panel-elevated);
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 12px;
  padding: 24px;
  max-width: 420px;
  width: calc(100% - 32px);
  box-shadow: 0 24px 64px rgba(0, 0, 0, 0.5);
}

.modal-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text-main);
  margin-bottom: 8px;
}

.modal-body {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 20px;
  line-height: 1.6;
}

.modal-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}
</style>
