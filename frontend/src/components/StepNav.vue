<template>
  <div class="step-nav">
    <button
        v-if="prevStep"
        class="btn-ghost"
        @click="router.push(prevStep.route)"
    >
      ← {{ $t(prevStep.label) }}
    </button>
    <span v-else/>

    <button
        v-if="isLastStep"
        class="btn-ghost"
        @click="router.push('/control-room')"
    >
      {{ $t('x-setup-done') }}
    </button>
    <button
        v-else-if="nextStep"
        class="btn-ghost"
        @click="router.push(nextStep.route)"
    >
      {{ $t(nextStep.label) }} →
    </button>
  </div>
</template>

<script setup>
import {computed} from 'vue'
import {useRouter} from 'vue-router'

const props = defineProps({
  currentStep: {type: Number, required: true},
})

const router = useRouter()

const SETUP_STEPS = [
  {route: '/media-server', label: 'x-setup-step-media-server'},
  {route: '/media-player', label: 'x-setup-step-media-player'},
  {route: '/media-paths', label: 'x-setup-step-paths'},
  {route: '/sala', label: 'x-setup-step-room'},
]

const stepIndex = computed(() => props.currentStep - 1)
const prevStep = computed(() => stepIndex.value > 0 ? SETUP_STEPS[stepIndex.value - 1] : null)
const nextStep = computed(() => stepIndex.value < SETUP_STEPS.length - 1 ? SETUP_STEPS[stepIndex.value + 1] : null)
const isLastStep = computed(() => stepIndex.value === SETUP_STEPS.length - 1)
</script>

<style scoped>
.step-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--panel-border);
}
</style>
