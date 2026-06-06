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
        :disabled="disabled || isTranscribing || isGenerating || isTtsPlaying"
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
          :disabled="disabled || isGenerating || isTranscribing || isTtsPlaying"
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
          :disabled="!canSend || isTranscribing || isGenerating || isTtsPlaying"
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
/* 主题修改：InputArea 深灰黑背景 */
.input-area {
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  border-top: 1px solid var(--terran-border-primary);
  background: var(--terran-bg-secondary);
}

/* 状态栏 - 固定在输入框上方 */
.status-bar {
  height: 28px;
  margin-bottom: var(--terran-spacing-sm);
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 主题修改：状态项使用CSS变量 */
.status-item {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  animation: fadeIn 0.2s ease;
}

/* 主题修改：录音状态使用帝国暗红 */
.status-item.recording {
  color: var(--terran-danger);
  text-shadow: var(--terran-text-glow-danger);
}

.status-item.transcribing {
  color: var(--terran-info);
}

.status-item.generating {
  color: var(--terran-primary);
  text-shadow: var(--terran-text-glow-primary);
}

.status-item.tts-playing {
  color: var(--terran-info);
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

/* 主题修改：取消按钮样式 */
.cancel-btn {
  margin-left: var(--terran-spacing-sm);
  font-size: var(--terran-font-size-xs);
  padding: 0 var(--terran-spacing-xs);
  height: 22px;
}

/* 主题修改：录音指示点使用暗红色 */
.recording-dot {
  width: 8px;
  height: 8px;
  background: var(--terran-danger);
  border-radius: var(--terran-radius-circle);
  animation: pulse 1s infinite;
  box-shadow: var(--terran-glow-danger);
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
  transition: opacity var(--terran-transition-base);
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}

/* 主题修改：输入框区域深灰黑背景 */
.input-wrapper {
  display: flex;
  align-items: flex-end;
  gap: var(--terran-spacing-sm);
  background: var(--terran-input-bg);
  border: var(--terran-input-border);
  border-radius: 24px;
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  transition: all var(--terran-transition-slow);
}

/* 主题修改：输入框聚焦带主色发光边框 */
.input-wrapper:focus-within {
  border: var(--terran-input-focus-border);
  box-shadow: var(--terran-input-focus-glow);
}

.input-wrapper.is-generating {
  background: var(--terran-bg-secondary);
  border: 1px solid var(--terran-primary);
  box-shadow: var(--terran-glow-primary);
}

/* 主题修改：输入框样式 */
.input-textarea {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  font-size: var(--terran-font-size-md);
  line-height: var(--terran-line-height-normal);
  color: var(--terran-text-primary);
  resize: none;
  min-height: 20px;
  max-height: 120px;
  padding: 6px 8px;
  font-family: inherit;
}

.input-textarea::placeholder {
  color: var(--terran-text-tertiary);
}

.input-textarea:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.input-actions {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
}

/* 主题修改：语音按钮录音状态为暗红+脉冲动画 */
.voice-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.voice-btn.is-recording {
  background: var(--terran-danger);
  color: #fff;
  border-color: var(--terran-danger);
  animation: recordingPulse 1s infinite;
}

.voice-btn.is-recording:hover {
  background: var(--terran-danger-light);
  border-color: var(--terran-danger-light);
  color: #fff;
}

/* 主题修改：发送按钮主色+hover发光 */
.send-btn {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.send-btn:not(:disabled):hover {
  box-shadow: var(--terran-glow-primary);
}

/* 主题修改：Ant Design 按钮深度样式覆盖 */
:deep(.ant-btn) {
  border-radius: var(--terran-radius-circle) !important;
}

:deep(.ant-btn-primary) {
  background: var(--terran-btn-primary-bg) !important;
  border-color: var(--terran-btn-primary-bg) !important;
}

:deep(.ant-btn-primary:not(:disabled):hover) {
  background: var(--terran-btn-primary-hover) !important;
  border-color: var(--terran-btn-primary-hover) !important;
  box-shadow: var(--terran-glow-primary);
}

:deep(.ant-btn-dangerous) {
  color: var(--terran-danger) !important;
}
</style>
