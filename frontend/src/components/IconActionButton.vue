<template>
  <component
      :is="rootTag"
      :aria-disabled="disabled || loading ? 'true' : undefined"
      :aria-label="iconOnly ? label : undefined"
      :class="buttonClasses"
      :disabled="rootTag === 'button' ? disabled || loading : undefined"
      :download="rootTag === 'a' && download ? download : undefined"
      :href="rootTag === 'a' && !disabled && !loading ? href : undefined"
      :target="rootTag === 'a' && target ? target : undefined"
      :type="rootTag === 'button' ? 'button' : undefined"
      @click="handleClick"
  >
    <span
        :class="['icon-action-button__icon', brandIcon && 'icon-action-button__icon--brand']"
        :style="brandIconStyle"
        aria-hidden="true"
    >
      <svg
          v-if="brandIcon"
          class="icon-action-button__brand-svg"
          fill="currentColor"
          role="img"
          viewBox="0 0 24 24"
      >
        <title>{{ brandIcon.title }}</title>
        <path :d="brandIcon.path"/>
      </svg>

      <component
          :is="genericIcon"
          v-else
          :stroke-width="2"
          class="icon-action-button__svg"
      />
    </span>

    <span v-if="!iconOnly" class="icon-action-button__label">
      {{ loading && loadingLabel ? loadingLabel : label }}
    </span>
  </component>
</template>

<script setup>
import {computed} from 'vue'
import {
  AlertTriangle,
  CheckCircle,
  Circle,
  Copy,
  Download,
  FolderOpen,
  KeyRound,
  Pencil,
  Play,
  Plus,
  Power,
  PowerOff,
  RefreshCw,
  ScanSearch,
  Search,
  Server,
  Trash2,
  Wifi
} from '@lucide/vue'
import {siEmby, siJellyfin, siPlex} from 'simple-icons'

const props = defineProps({
  icon: {type: String, default: 'server'},
  brand: {type: String, default: ''},
  label: {type: String, required: true},
  loadingLabel: {type: String, default: ''},
  loading: {type: Boolean, default: false},
  disabled: {type: Boolean, default: false},
  href: {type: String, default: ''},
  download: {type: String, default: ''},
  target: {type: String, default: ''},
  variant: {type: String, default: 'default'},
  compact: {type: Boolean, default: false},
  iconOnly: {type: Boolean, default: false},
})

const emit = defineEmits(['click'])

const genericIcons = {
  search: Search,
  scan: ScanSearch,
  network: Wifi,
  refresh: RefreshCw,
  reload: RefreshCw,
  download: Download,
  copy: Copy,
  clear: Trash2,
  delete: Trash2,
  test: CheckCircle,
  check: CheckCircle,
  warning: AlertTriangle,
  circle: Circle,
  folder: FolderOpen,
  'folder-open': FolderOpen,
  key: KeyRound,
  add: Plus,
  plus: Plus,
  new: Plus,
  edit: Pencil,
  pencil: Pencil,
  player: Play,
  play: Play,
  power: Power,
  powerOn: Power,
  'power-on': Power,
  powerOff: PowerOff,
  'power-off': PowerOff,
  server: Server,
}

const brandIcons = {
  emby: siEmby,
  jellyfin: siJellyfin,
  plex: siPlex,
}

const rootTag = computed(() => props.href ? 'a' : 'button')
const normalizedBrand = computed(() => props.brand?.toLowerCase?.() || '')
const brandIcon = computed(() => brandIcons[normalizedBrand.value] || null)

const brandIconStyle = computed(() => {
  if (!brandIcon.value?.hex) return undefined
  return {'--icon-action-brand-color': `#${brandIcon.value.hex}`}
})

const genericIcon = computed(() => genericIcons[props.icon] || Server)

const buttonClasses = computed(() => [
  'icon-action-button',
  props.compact && 'icon-action-button--compact',
  props.iconOnly && 'icon-action-button--icon-only',
  props.variant === 'danger' && 'icon-action-button--danger',
  (props.disabled || props.loading) && 'icon-action-button--disabled',
])

function handleClick(event) {
  if (props.disabled || props.loading) {
    event.preventDefault()
    return
  }
  emit('click', event)
}
</script>

<style scoped>
/* ─── BASE ───────────────────────────────────────────────────────────── */
.icon-action-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 9px;
  min-height: 42px;
  padding: 9px 13px;
  border: 1px solid rgba(176, 190, 190, 0.16);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(220, 228, 226, 0.055), rgba(220, 228, 226, 0.018)),
  var(--bg-panel-elevated);
  color: var(--text-main);
  font-family: var(--font);
  font-size: 13px;
  font-weight: 650;
  cursor: pointer;
  text-decoration: none;
  white-space: nowrap;
  transition: border-color 0.14s ease, background 0.14s ease, transform 0.14s ease, box-shadow 0.14s ease;
}

.icon-action-button:hover:not(:disabled):not(.icon-action-button--disabled) {
  border-color: rgba(194, 161, 107, 0.34);
  background: linear-gradient(180deg, rgba(194, 161, 107, 0.10), rgba(127, 166, 181, 0.04)),
  var(--bg-panel-elevated);
  box-shadow: 0 10px 24px rgba(0, 0, 0, 0.18);
  transform: translateY(-1px);
}

.icon-action-button:focus-visible {
  outline: none;
  box-shadow: 0 0 0 3px rgba(194, 161, 107, 0.12);
}

.icon-action-button:disabled,
.icon-action-button--disabled {
  opacity: 0.48;
  cursor: not-allowed;
  transform: none;
  box-shadow: none;
}

/* ─── ICON CONTAINER ─────────────────────────────────────────────────── */
.icon-action-button__icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 25px;
  height: 25px;
  border-radius: 8px;
  background: rgba(194, 161, 107, 0.10);
  color: var(--accent-secondary);
  flex-shrink: 0;
}

.icon-action-button__icon--brand {
  background: color-mix(in srgb, var(--icon-action-brand-color, var(--accent-secondary)) 18%, transparent);
  color: var(--icon-action-brand-color, var(--accent-secondary));
}

.icon-action-button__svg,
.icon-action-button__brand-svg {
  width: 15px;
  height: 15px;
  display: block;
}

.icon-action-button__brand-svg {
  fill: currentColor;
}

.icon-action-button__label {
  line-height: 1;
}

/* ─── COMPACT ────────────────────────────────────────────────────────── */
.icon-action-button--compact {
  min-height: 34px;
  padding: 6px 9px;
  gap: 7px;
  border-radius: 8px;
  font-size: 12px;
}

.icon-action-button--compact .icon-action-button__icon {
  width: 21px;
  height: 21px;
  border-radius: 7px;
}

.icon-action-button--compact .icon-action-button__svg,
.icon-action-button--compact .icon-action-button__brand-svg {
  width: 13px;
  height: 13px;
}

/* ─── DANGER ─────────────────────────────────────────────────────────── */
.icon-action-button--danger {
  border-color: rgba(255, 92, 122, 0.22);
  color: #ff9aae;
}

.icon-action-button--danger .icon-action-button__icon {
  background: rgba(255, 92, 122, 0.09);
  color: var(--status-danger);
}

.icon-action-button--danger:hover:not(:disabled):not(.icon-action-button--disabled) {
  border-color: rgba(255, 92, 122, 0.38);
  background: linear-gradient(180deg, rgba(255, 92, 122, 0.10), rgba(255, 92, 122, 0.035)),
  var(--bg-panel-elevated);
}

/* ─── ICON-ONLY ──────────────────────────────────────────────────────── */
.icon-action-button--icon-only {
  justify-content: center;
  width: 34px;
  height: 34px;
  min-width: 34px;
  min-height: 34px;
  padding: 0;
  gap: 0;
  border: none;
  border-radius: 10px;
  background: rgba(194, 161, 107, 0.08);
  box-shadow: none;
  color: var(--accent-secondary);
}

.icon-action-button--icon-only:hover:not(:disabled):not(.icon-action-button--disabled) {
  border: none;
  background: rgba(194, 161, 107, 0.14);
  box-shadow: none;
  transform: none;
}

.icon-action-button--icon-only:focus-visible {
  border: none;
  box-shadow: 0 0 0 3px rgba(194, 161, 107, 0.14);
}

.icon-action-button--icon-only .icon-action-button__icon {
  background: transparent;
  color: inherit;
}

.icon-action-button--icon-only .icon-action-button__svg,
.icon-action-button--icon-only .icon-action-button__brand-svg {
  width: 16px;
  height: 16px;
}

.icon-action-button--icon-only .icon-action-button__label {
  display: none;
}

/* ─── ICON-ONLY + DANGER ─────────────────────────────────────────────── */
.icon-action-button--icon-only.icon-action-button--danger {
  border: none;
  background: rgba(255, 92, 122, 0.08);
  color: var(--status-danger);
}

.icon-action-button--icon-only.icon-action-button--danger:hover:not(:disabled):not(.icon-action-button--disabled) {
  border: none;
  background: rgba(255, 92, 122, 0.14);
  box-shadow: none;
  color: var(--status-danger);
  transform: none;
}

.icon-action-button--icon-only.icon-action-button--danger:focus-visible {
  border: none;
  box-shadow: 0 0 0 3px rgba(255, 92, 122, 0.16);
}

.icon-action-button--icon-only.icon-action-button--danger .icon-action-button__icon {
  background: transparent;
  color: var(--status-danger);
}

/* ─── RESPONSIVE ─────────────────────────────────────────────────────── */
@media (max-width: 640px) {
  /* Only affect alignment - width is controlled by container (grid stretches, flex keeps natural) */
  .icon-action-button {
    justify-content: flex-start;
  }

  .icon-action-button--icon-only {
    justify-content: center;
    width: 34px;
    min-width: 34px;
  }
}
</style>
