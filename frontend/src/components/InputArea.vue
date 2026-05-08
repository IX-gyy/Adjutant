<template>
  <div class="input-area">
    <!-- 状态提示区域（在输入框上方，不会导致输入框抖动） -->
    <div class="status-bar">
      <Transition name="fade">
        <!-- 录音状态 -->
        <div v-if="isRecording" class="status-item recording">
          <span class="recording-dot"></span>
          <span>正在录音 {{ formatDuration(recordingDuration) }}</span>
        </div>
        <!-- 转写状态 -->
        <div v-else-if="isTranscribing" class="status-item transcribing">
          <LoadingOutlined />
          <span>语音转写中...</span>
        </div>
        <!-- 生成中状态 -->
        <div v-else-if="isGenerating" class="status-item generating">
          <LoadingOutlined />
          <span>副官正在思考</span>
          <span class="generating-dots">...</span>
          <AButton
            type="link"
            size="small"
            danger
            class="cancel-btn"
            @click="$emit('cancel-generation')"
          >
            停止生成
          </AButton>
        </div>
        <!-- TTS播报中状态 -->
        <div v-else-if="isTtsPlaying" class="status-item tts-playing">
          <SoundOutlined />
          <span>正在播报</span>
          <span class="playing-dots">...</span>
          <AButton
            type="link"
            size="small"
            danger
            class="cancel-btn"
            @click="$emit('stop-tts')"
          >
            停止播报
          </AButton>
        </div>
      </Transition>
    </div>

    <div class="input-wrapper" :class="{ 'is-generating': isGenerating }">
      <textarea
        ref="textareaRef"
        v-model="inputValue"
        :disabled="disabled || isTranscribing || isGenerating"
        :placeholder="placeholder"
        class="input-textarea"
        rows="1"
        @keydown="handleKeydown"
        @input="handleInput"
      />
      <div class="input-actions">
        <!-- 语音按钮：转写中或生成中时显示 loading -->
        <AButton
          type="default"
          shape="circle"
          :loading="isTranscribing || isGenerating"
          :disabled="disabled || isGenerating || isTranscribing"
          class="voice-btn"
          :class="{ 'is-recording': isRecording }"
          @mousedown="startRecording"
          @mouseup="stopRecording"
          @mouseleave="stopRecording"
          @touchstart.prevent="startRecording"
          @touchend.prevent="stopRecording"
        >
          <template #icon>
            <AudioOutlined v-if="!isRecording && !isTranscribing && !isGenerating" />
            <PauseOutlined v-else-if="isRecording" />
          </template>
        </AButton>

        <!-- 发送按钮 -->
        <AButton
          type="primary"
          shape="circle"
          :disabled="!canSend || isTranscribing || isGenerating"
          :loading="isGenerating"
          class="send-btn"
          @click="handleSend"
        >
          <template #icon>
            <SendOutlined />
          </template>
        </AButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { Button as AButton } from 'ant-design-vue'
import { AudioOutlined, PauseOutlined, SendOutlined, LoadingOutlined, SoundOutlined } from '@ant-design/icons-vue'

interface Props {
  modelValue: string
  disabled?: boolean
  placeholder?: string
  isRecording?: boolean
  recordingDuration?: number
  audioLevel?: number
  isGenerating?: boolean
  isTranscribing?: boolean
  isTtsPlaying?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  disabled: false,
  placeholder: '输入消息...',
  isRecording: false,
  recordingDuration: 0,
  audioLevel: 0,
  isGenerating: false,
  isTranscribing: false,
  isTtsPlaying: false
})

const emit = defineEmits<{
  'update:modelValue': [value: string]
  'send': [value: string]
  'start-record': []
  'stop-record': []
  'cancel-generation': []
  'stop-tts': []
}>()

const textareaRef = ref<HTMLTextAreaElement>()
const inputValue = ref(props.modelValue)

const canSend = computed(() => {
  return inputValue.value.trim().length > 0 && !props.disabled && !props.isGenerating
})

// 同步外部 modelValue
watch(() => props.modelValue, (newVal) => {
  inputValue.value = newVal
  nextTick(adjustTextareaHeight)
})

// 同步内部 inputValue 到外部
watch(inputValue, (newVal) => {
  emit('update:modelValue', newVal)
  nextTick(adjustTextareaHeight)
})

function handleInput() {
  adjustTextareaHeight()
}

function adjustTextareaHeight() {
  const textarea = textareaRef.value
  if (!textarea) return

  textarea.style.height = 'auto'
  const newHeight = Math.min(textarea.scrollHeight, 120)
  textarea.style.height = `${newHeight}px`
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  const text = inputValue.value.trim()
  if (text && canSend.value) {
    emit('send', text)
    inputValue.value = ''
    nextTick(adjustTextareaHeight)
  }
}

function startRecording() {
  if (!props.disabled && !props.isGenerating && !props.isTranscribing) {
    emit('start-record')
  }
}

function stopRecording() {
  if (props.isRecording) {
    emit('stop-record')
  }
}

function formatDuration(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}
</script>

<style scoped>
.input-area {
  padding: 12px 16px;
  border-top: 1px solid #f0f0f0;
  background: #fff;
}

/* 状态栏 - 固定在输入框上方 */
.status-bar {
  height: 28px;
  margin-bottom: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  animation: fadeIn 0.2s ease;
}

.status-item.recording {
  color: #ff4d4f;
}

.status-item.transcribing {
  color: #1890ff;
}

.status-item.generating {
  color: #52c41a;
}

.status-item.tts-playing {
  color: #1890ff;
}

.generating-dots,
.playing-dots {
  animation: dots 1.5s infinite;
  width: 20px;
  text-align: left;
}

@keyframes dots {
  0%, 20% { content: '.'; }
  40% { content: '..'; }
  60%, 100% { content: '...'; }
}

.cancel-btn {
  margin-left: 8px;
  font-size: 12px;
  padding: 0 4px;
  height: 22px;
}

.recording-dot {
  width: 8px;
  height: 8px;
  background: #ff4d4f;
  border-radius: 50%;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% {
    opacity: 1;
    transform: scale(1);
  }
  50% {
    opacity: 0.5;
    transform: scale(1.2);
  }
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* 过渡动画 */
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 输入框区域 */
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: 8px;
  background: #f5f5f5;
  border-radius: 24px;
  padding: 8px 12px;
  transition: all 0.3s ease;
}

.input-wrapper.is-generating {
  background: #f6ffed;
  border: 1px solid #b7eb8f;
}

.input-textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: 14px;
  line-height: 1.5;
  resize: none;
  min-height: 20px;
  max-height: 120px;
  padding: 6px 8px;
  font-family: inherit;
}

.input-textarea::placeholder {
  color: #bfbfbf;
}

.input-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

/* 语音按钮 */
.voice-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-btn.is-recording {
  background: #ff4d4f;
  color: #fff;
  border-color: #ff4d4f;
  animation: recording-pulse 1s infinite;
}

.voice-btn.is-recording:hover {
  background: #ff7875;
  border-color: #ff7875;
  color: #fff;
}

@keyframes recording-pulse {
  0%, 100% {
    box-shadow: 0 0 0 0 rgba(255, 77, 79, 0.4);
  }
  50% {
    box-shadow: 0 0 0 8px rgba(255, 79, 79, 0);
  }
}

/* 发送按钮 */
.send-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
