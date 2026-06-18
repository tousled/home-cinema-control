<template>
  <div class="toast-container">
    <transition-group name="toast">
      <div
          v-for="toast in toasts"
          :key="toast.id"
          :class="['toast', `toast-${toast.type}`]"
      >
        <span class="toast-icon">{{ toast.type === 'success' ? '✓' : '✕' }}</span>
        <span class="toast-msg">{{ toast.message }}</span>
        <button class="toast-dismiss" @click="dismiss(toast.id)">×</button>
      </div>
    </transition-group>
  </div>
</template>

<script setup>
import {useToast} from '../composables/useToast.js'

const {toasts, dismiss} = useToast()
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 24px;
  right: 24px;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 11px 14px;
  border-radius: 8px;
  background: rgba(14, 19, 32, 0.97);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(16px);
  box-shadow: 0 8px 28px rgba(0, 0, 0, 0.5);
  min-width: 240px;
  max-width: 340px;
  pointer-events: auto;
  font-family: var(--font);
}

.toast-success {
  border-left: 3px solid var(--status-success);
}

.toast-error {
  border-left: 3px solid var(--status-danger);
}

.toast-icon {
  font-size: 11px;
  font-weight: 800;
  flex-shrink: 0;
}

.toast-success .toast-icon {
  color: var(--status-success);
}

.toast-error .toast-icon {
  color: var(--status-danger);
}

.toast-msg {
  flex: 1;
  font-size: 13px;
  color: var(--text-main);
  line-height: 1.4;
}

.toast-dismiss {
  background: none;
  border: none;
  color: var(--text-subtle);
  cursor: pointer;
  font-size: 17px;
  line-height: 1;
  padding: 0 2px;
  flex-shrink: 0;
  font-family: var(--font);
  transition: color 0.1s;
}

.toast-dismiss:hover {
  color: var(--text-muted);
}

.toast-enter-active,
.toast-leave-active {
  transition: opacity 0.18s ease, transform 0.18s ease;
}

@media (prefers-reduced-motion: reduce) {
  .toast-enter-active,
  .toast-leave-active {
    transition: none;
  }
}

.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(16px);
}
</style>
