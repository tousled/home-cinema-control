<template>
  <div class="ip-combobox">
    <input
        :id="id"
        :placeholder="placeholder"
        :value="modelValue"
        autocomplete="off"
        class="form-input"
        type="text"
        @blur="open = false"
        @focus="open = true"
        @input="$emit('update:modelValue', $event.target.value)"
    />
    <div v-if="open && filtered.length" class="ip-dropdown">
      <button
          v-for="d in filtered"
          :key="d.ip"
          class="ip-option"
          type="button"
          @mousedown.prevent="select(d)"
      >
        <span class="ip-option-addr">{{ d.ip }}</span>
        <span v-if="d.name || d.vendor" class="ip-option-name">{{ d.name || d.vendor }}</span>
      </button>
    </div>
  </div>
</template>

<script setup>
import {computed, ref} from 'vue'

const props = defineProps({
  modelValue: {type: String, default: ''},
  devices: {type: Array, default: () => []},
  id: {type: String, default: undefined},
  placeholder: {type: String, default: ''},
})

const emit = defineEmits(['update:modelValue'])
const open = ref(false)

const allDevices = computed(() => {
  const current = (props.modelValue ?? '').trim()
  if (!current || props.devices.some(d => d.ip === current)) return props.devices
  return [{ip: current, name: null, vendor: null}, ...props.devices]
})

const filtered = computed(() => {
  const q = (props.modelValue ?? '').toLowerCase().trim()
  if (!q) return allDevices.value
  return allDevices.value.filter(d =>
      d.ip.includes(q) ||
      (d.name && d.name.toLowerCase().includes(q)) ||
      (d.vendor && d.vendor.toLowerCase().includes(q))
  )
})

function select(d) {
  emit('update:modelValue', d.ip)
  open.value = false
}
</script>

<style scoped>
.ip-combobox {
  position: relative;
}

.ip-dropdown {
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

.ip-option {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  width: 100%;
  padding: 8px 12px;
  background: none;
  border: none;
  border-bottom: 1px solid rgba(255, 255, 255, 0.04);
  cursor: pointer;
  text-align: left;
}

.ip-option:last-child {
  border-bottom: none;
}

.ip-option:hover {
  background: rgba(255, 255, 255, 0.06);
}

.ip-option-addr {
  font-family: var(--mono);
  font-size: 12px;
  color: var(--text-main);
  flex-shrink: 0;
}

.ip-option-name {
  font-size: 11px;
  color: var(--text-subtle);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  text-align: right;
}
</style>
