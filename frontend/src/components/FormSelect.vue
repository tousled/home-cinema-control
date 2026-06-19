<template>
  <div class="form-select-wrap">
    <button
        :id="id"
        :aria-expanded="open ? 'true' : 'false'"
        :class="['form-select-trigger', open && 'form-select-trigger--open']"
        :disabled="disabled"
        type="button"
        @blur="open = false"
        @click="open = !open"
    >
      <span class="form-select-val">{{ selectedLabel }}</span>
      <svg
          aria-hidden="true"
          class="form-select-chevron"
          fill="none"
          stroke="currentColor"
          stroke-linecap="round"
          stroke-linejoin="round"
          stroke-width="2.5"
          viewBox="0 0 24 24"
      >
        <polyline points="6 9 12 15 18 9"/>
      </svg>
    </button>
    <div v-if="open" class="form-select-dropdown" role="listbox">
      <button
          v-for="opt in options"
          :key="opt.value"
          :aria-selected="opt.value === modelValue"
          :class="['form-select-opt', opt.value === modelValue && 'form-select-opt--active']"
          role="option"
          type="button"
          @mousedown.prevent="pick(opt)"
      >
        {{ opt.label }}
      </button>
    </div>
  </div>
</template>

<script setup>
import {computed, ref} from 'vue'

const props = defineProps({
  modelValue: {default: null},
  options: {type: Array, default: () => []},
  id: {type: String, default: undefined},
  disabled: {type: Boolean, default: false},
})

const emit = defineEmits(['update:modelValue', 'change'])
const open = ref(false)

const selectedLabel = computed(() => {
  const opt = props.options.find(o => o.value === props.modelValue)
  return opt ? opt.label : '—'
})

function pick(opt) {
  emit('update:modelValue', opt.value)
  emit('change', opt.value)
  open.value = false
}
</script>

<style scoped>
.form-select-wrap {
  position: relative;
  display: block;
  width: 100%;
  max-width: 420px;
}

.form-select-trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
  background: rgba(220, 228, 226, 0.045);
  border: 1px solid rgba(176, 190, 190, 0.12);
  border-radius: 6px;
  padding: 8px 11px;
  color: var(--text-main);
  font-family: var(--font);
  font-size: 14px;
  text-align: left;
  outline: none;
  cursor: pointer;
  transition: border-color 0.15s, box-shadow 0.15s;
}

.form-select-trigger:focus,
.form-select-trigger--open {
  border-color: rgba(127, 166, 181, 0.45);
  box-shadow: 0 0 0 3px rgba(127, 166, 181, 0.08);
}

.form-select-trigger:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.form-select-chevron {
  width: 13px;
  height: 13px;
  color: rgba(176, 190, 190, 0.48);
  flex-shrink: 0;
  transition: transform 0.15s;
}

.form-select-trigger--open .form-select-chevron {
  transform: rotate(180deg);
}

.form-select-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  max-height: 220px;
  overflow-y: auto;
  background: var(--bg-panel-elevated);
  border: 1px solid var(--panel-border);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
  z-index: 100;
}

.form-select-opt {
  display: block;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  border-bottom: 1px solid rgba(176, 190, 190, 0.08);
  color: var(--text-muted);
  font-family: var(--font);
  font-size: 13px;
  cursor: pointer;
  text-align: left;
}

.form-select-opt:last-child {
  border-bottom: none;
}

.form-select-opt:hover {
  background: rgba(176, 190, 190, 0.08);
  color: var(--text-main);
}

.form-select-opt--active {
  color: var(--accent-secondary);
  background: rgba(194, 161, 107, 0.06);
}
</style>
