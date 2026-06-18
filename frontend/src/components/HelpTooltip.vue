<template>
  <span
      ref="triggerWrapRef"
      class="help-tooltip"
      @focusin="show"
      @focusout="hide"
      @mouseenter="show"
      @mouseleave="hide"
      @keydown.esc="hide"
  >
    <slot>
      <button
          :aria-describedby="open ? tooltipId : undefined"
          :aria-label="text"
          class="help-tooltip-trigger"
          type="button"
      >
        ?
      </button>
    </slot>

    <Teleport to="body">
      <span
          v-if="open"
          :id="tooltipId"
          ref="bubbleRef"
          :class="['help-tooltip-bubble', placementClass]"
          :style="bubbleStyle"
          role="tooltip"
      >
        {{ text }}
      </span>
    </Teleport>
  </span>
</template>

<script setup>
import {computed, nextTick, onBeforeUnmount, ref} from 'vue'

let nextTooltipId = 0

const props = defineProps({
  text: {type: String, required: true},
})

const tooltipId = `help-tooltip-${++nextTooltipId}`

const open = ref(false)
const triggerWrapRef = ref(null)
const bubbleRef = ref(null)
const placement = ref('top')

const bubblePosition = ref({
  left: 0,
  top: 0,
})

const placementClass = computed(() => (
    placement.value === 'bottom'
        ? 'help-tooltip-bubble--bottom'
        : 'help-tooltip-bubble--top'
))

const bubbleStyle = computed(() => ({
  left: `${bubblePosition.value.left}px`,
  top: `${bubblePosition.value.top}px`,
}))

function show() {
  if (open.value) return

  open.value = true

  nextTick(() => {
    updatePosition()
    addFloatingListeners()
  })
}

function hide() {
  open.value = false
  removeFloatingListeners()
}

function updatePosition() {
  const trigger = triggerWrapRef.value
  const bubble = bubbleRef.value

  if (!trigger || !bubble) return

  const margin = 12
  const gap = 8
  const triggerRect = trigger.getBoundingClientRect()
  const bubbleRect = bubble.getBoundingClientRect()

  const preferredLeft = triggerRect.left + triggerRect.width / 2
  const minLeft = margin + bubbleRect.width / 2
  const maxLeft = window.innerWidth - margin - bubbleRect.width / 2

  const left = clamp(preferredLeft, minLeft, maxLeft)

  const topCandidate = triggerRect.top - gap - bubbleRect.height
  const hasRoomAbove = topCandidate >= margin

  placement.value = hasRoomAbove ? 'top' : 'bottom'

  const top = hasRoomAbove
      ? topCandidate
      : triggerRect.bottom + gap

  bubblePosition.value = {
    left,
    top: clamp(top, margin, window.innerHeight - margin - bubbleRect.height),
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max)
}

function addFloatingListeners() {
  window.addEventListener('resize', updatePosition)
  window.addEventListener('scroll', updatePosition, true)
}

function removeFloatingListeners() {
  window.removeEventListener('resize', updatePosition)
  window.removeEventListener('scroll', updatePosition, true)
}

onBeforeUnmount(removeFloatingListeners)
</script>

<style scoped>
.help-tooltip {
  display: inline-flex;
  align-items: center;
  flex-shrink: 0;
}

.help-tooltip-trigger {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 17px;
  height: 17px;
  border: 1px solid rgba(86, 204, 242, 0.28);
  border-radius: 999px;
  background: rgba(86, 204, 242, 0.08);
  color: var(--accent-secondary);
  font-family: var(--mono);
  font-size: 10px;
  line-height: 1;
  cursor: help;
}

.help-tooltip-trigger:focus-visible {
  outline: none;
  border-color: var(--accent-secondary);
  box-shadow: 0 0 0 3px rgba(86, 204, 242, 0.12);
}

.help-tooltip-bubble {
  position: fixed;
  z-index: 10000;
  width: min(280px, calc(100vw - 24px));
  padding: 9px 11px;
  border: 1px solid rgba(86, 204, 242, 0.22);
  border-radius: 8px;
  background: #0b1020;
  box-shadow: 0 14px 36px rgba(0, 0, 0, 0.38);
  color: var(--text-main);
  font-size: 12px;
  font-weight: 500;
  line-height: 1.45;
  text-transform: none;
  letter-spacing: 0;
  pointer-events: none;
  transform: translateX(-50%);
}

.help-tooltip-bubble::after {
  content: "";
  position: absolute;
  left: 50%;
  width: 9px;
  height: 9px;
  border-right: 1px solid rgba(86, 204, 242, 0.22);
  border-bottom: 1px solid rgba(86, 204, 242, 0.22);
  background: #0b1020;
}

.help-tooltip-bubble--top::after {
  top: 100%;
  transform: translate(-50%, -50%) rotate(45deg);
}

.help-tooltip-bubble--bottom::after {
  bottom: 100%;
  transform: translate(-50%, 50%) rotate(225deg);
}
</style>