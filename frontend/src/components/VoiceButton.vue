<template>
  <button
    class="voice-btn"
    :class="{
      'is-recording': isRecording,
      'is-disabled': disabled
    }"
    :disabled="disabled"
    @mousedown="startRecording"
    @mouseup="stopRecording"
    @mouseleave="stopRecording"
    @touchstart.prevent="startRecording"
    @touchend.prevent="stopRecording"
  >
    <div class="voice-icon">
      <svg v-if="!isRecording" viewBox="0 0 24 24" width="20" height="20">
        <path
          fill="currentColor"
          d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"
        />
        <path
          fill="currentColor"
          d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"
        />
      </svg>
      <svg v-else viewBox="0 0 24 24" width="20" height="20">
        <rect x="6" y="6" width="12" height="12" rx="2" fill="currentColor" />
      </svg>
    </div>
    <div v-if="isRecording" class="audio-level-bar">
      <div
        class="audio-level-fill"
        :style="{ height: `${audioLevel}%` }"
      />
    </div>
  </button>
</template>

<script setup lang="ts">
interface Props {
  isRecording: boolean
  audioLevel: number
  disabled: boolean
}

defineProps<Props>()

const emit = defineEmits<{
  start: []
  stop: []
}>()

function startRecording() {
  emit('start')
}

function stopRecording() {
  emit('stop')
}
</script>

<style scoped>
.voice-btn {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  border: none;
  background: #f0f0f0;
  color: #595959;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  transition: all 0.2s ease;
  overflow: hidden;
}

.voice-btn:hover:not(:disabled) {
  background: #e6f7ff;
  color: #1890ff;
}

.voice-btn.is-recording {
  background: #ff4d4f;
  color: #fff;
  animation: recording-pulse 1s infinite;
}

.voice-btn.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

@keyframes recording-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(255, 77, 79, 0);
  }
}

.voice-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
}

.audio-level-bar {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 100%;
  background: rgba(255, 255, 255, 0.3);
  display: flex;
  align-items: flex-end;
}

.audio-level-fill {
  width: 100%;
  background: rgba(255, 255, 255, 0.5);
  transition: height 0.1s ease;
}
</style>
