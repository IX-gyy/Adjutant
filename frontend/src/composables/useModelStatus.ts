import { ref, computed } from 'vue'
import { message } from 'ant-design-vue'
import { onBackendEvent, requestStatus, startLoading } from './useBackend'
import type { BackendEvent } from '../types'


// 模型加载状态
export const wakeModelLoaded = ref(false)
export const transcribeModelLoaded = ref(false)
export const llmModelLoaded = ref(false)
export const ttsModelLoaded = ref(false)
export const allModelsLoaded = ref(false)
export const backendReady = ref(false)

// 全局加载状态（用于页面遮罩）
export const isLoading = ref(true)

// 计算属性
export const isWakeReady = computed(() => wakeModelLoaded.value)
export const isTranscribeReady = computed(() => transcribeModelLoaded.value)
export const isLlmReady = computed(() => llmModelLoaded.value)
export const isTtsReady = computed(() => ttsModelLoaded.value)
export const isFullyReady = computed(() => allModelsLoaded.value)

let unsubscribe: (() => void) | null = null
let isRegistered = false
let statusRetryTimer: ReturnType<typeof setTimeout> | null = null
const MAX_STATUS_RETRIES = 5
let statusRetryCount = 0

// 检查是否所有模型都已加载，更新 isLoading
function checkAllLoaded() {
  const allLoaded =
    wakeModelLoaded.value && transcribeModelLoaded.value &&
    llmModelLoaded.value && ttsModelLoaded.value

  allModelsLoaded.value = allLoaded
  if (allLoaded) {
    isLoading.value = false
    if (statusRetryTimer) {
      clearTimeout(statusRetryTimer)
      statusRetryTimer = null
    }
  }
}

// 根据后端状态恢复 message 提示链
function restoreLoadingMessages(
  wake: boolean, transcribe: boolean, llm: boolean, tts: boolean
) {
  message.destroy('system_init')

  if (!wake) {
    message.loading({ content: '正在加载唤醒模型...', duration: 0, key: 'wake_model_loading' })
  } else {
    message.success({ content: '唤醒模型加载完成', duration: 2, key: 'wake_model_loading' })
  }

  if (!transcribe) {
    if (wake) {
      message.loading({ content: '正在加载转写模型...', duration: 0, key: 'transcribe_model_loading' })
    }
  } else {
    message.success({ content: '转写模型加载完成', duration: 2, key: 'transcribe_model_loading' })
  }

  if (!llm) {
    if (wake && transcribe) {
      message.loading({ content: '正在加载对话模型...', duration: 0, key: 'llm_model_loading' })
    }
  } else {
    message.success({ content: '对话模型加载完成', duration: 2, key: 'llm_model_loading' })
  }

  if (!tts) {
    if (wake && transcribe && llm) {
      message.loading({ content: '正在加载TTS语音模型...', duration: 0, key: 'tts_model_loading' })
    }
  } else {
    message.success({ content: 'TTS语音模型加载完成', duration: 2, key: 'tts_model_loading' })
  }

  if (wake && transcribe && llm && tts) {
    message.success({ content: '🎉 所有模型加载完成，副官已就绪！', duration: 3 })
    checkAllLoaded()
  }
}

// 请求状态（带重试）
function scheduleStatusRequest() {
  if (statusRetryCount >= MAX_STATUS_RETRIES) {
    console.warn('[useModelStatus] 重试请求状态已达上限，停止重试')
    message.error({ content: '无法获取模型加载状态，请重启应用', duration: 3 })
    return
  }
  statusRetryCount++
  console.log(`[useModelStatus] 请求后端状态，第${statusRetryCount}次`)
  requestStatus()

  // 设置下一次重试
  statusRetryTimer = setTimeout(() => {
    // 如果仍未收到任何模型加载事件或状态更新，则重试
    if (!wakeModelLoaded.value && !transcribeModelLoaded.value && !llmModelLoaded.value && !ttsModelLoaded.value) {
      scheduleStatusRequest()
    }
  }, 2000)
}

// 事件处理器
function handleBackendEvent(event: BackendEvent) {
  // 一旦收到任何有效事件，停止重试
  if (statusRetryTimer) {
    clearTimeout(statusRetryTimer)
    statusRetryTimer = null
    statusRetryCount = 0
  }

  switch (event.event) {
    case 'partial_ready':
      backendReady.value = true
      // 后端刚启动，所有模型尚未加载
      wakeModelLoaded.value = false
      transcribeModelLoaded.value = false
      llmModelLoaded.value = false
      ttsModelLoaded.value = false
      isLoading.value = true
      // 显示第一个加载提示
      message.destroy('system_init')
      message.loading({ content: '正在加载唤醒模型...', duration: 0, key: 'wake_model_loading' })
      break

    case 'wake_model_loaded':
      wakeModelLoaded.value = true
      message.success({ content: '唤醒模型加载完成', duration: 2, key: 'wake_model_loading' })
      message.loading({ content: '正在加载转写模型...', duration: 0, key: 'transcribe_model_loading' })
      checkAllLoaded()
      break

    case 'transcribe_model_loaded':
      transcribeModelLoaded.value = true
      message.success({ content: '转写模型加载完成', duration: 2, key: 'transcribe_model_loading' })
      message.loading({ content: '正在加载对话模型...', duration: 0, key: 'llm_model_loading' })
      checkAllLoaded()
      break

    case 'llm_model_loaded':
      llmModelLoaded.value = true
      message.success({ content: '对话模型加载完成', duration: 2, key: 'llm_model_loading' })
      message.loading({ content: '正在加载TTS语音模型...', duration: 0, key: 'tts_model_loading' })
      checkAllLoaded()
      break

    case 'tts_model_loaded':
      ttsModelLoaded.value = true
      message.success({ content: 'TTS语音模型加载完成', duration: 2, key: 'tts_model_loading' })
      checkAllLoaded()
      break

    case 'full_ready':
      wakeModelLoaded.value = true
      transcribeModelLoaded.value = true
      llmModelLoaded.value = true
      ttsModelLoaded.value = true
      allModelsLoaded.value = true
      backendReady.value = true
      isLoading.value = false
      message.destroy('system_init')
      message.destroy('wake_model_loading')
      message.destroy('transcribe_model_loading')
      message.destroy('llm_model_loading')
      message.destroy('tts_model_loading')
      message.success({ content: '🎉 所有模型加载完成，副官已就绪！', duration: 3 })
      break

    case 'status_update': {
      // 根据后端当前状态更新
      backendReady.value = true
      wakeModelLoaded.value = event.wake_model_loaded
      transcribeModelLoaded.value = event.transcribe_model_loaded
      llmModelLoaded.value = event.llm_model_loaded
      ttsModelLoaded.value = event.tts_model_loaded
      checkAllLoaded()
      // 根据状态显示或关闭 message
      restoreLoadingMessages(
        event.wake_model_loaded,
        event.transcribe_model_loaded,
        event.llm_model_loaded,
        event.tts_model_loaded
      )
      break
    }

    case 'error':
      console.error('[useModelStatus] 后端错误:', event)
      message.error({ content: `加载错误: ${event.msg}`, duration: 3 })
      break
  }
}

// 确保监听器注册（幂等）
function ensureListener() {
  if (isRegistered || !window.electronAPI) return
  isRegistered = true
  unsubscribe = onBackendEvent(handleBackendEvent)

  // 首先显示启动提示
  message.loading({ content: '系统启动中，请稍后...', duration: 0, key: 'system_init' })

  // 立即主动请求一次状态，并启动重试逻辑
  scheduleStatusRequest()

  // 延迟一小段 保证前端已完成渲染，然后通知后端开始加载模型
  setTimeout(() => {
    startLoading()
  }, 100) // 短暂延迟确保Vue加载完成
}

// 模块加载时尽快注册
if (typeof window !== 'undefined') {
  setTimeout(() => {
    if (window.electronAPI) {
      ensureListener()
    }
  }, 0)
}

// 工具函数
export function isModelLoaded(type: string): boolean {
  switch (type) {
    case 'wake': return wakeModelLoaded.value
    case 'transcribe': return transcribeModelLoaded.value
    case 'llm': return llmModelLoaded.value
    case 'tts': return ttsModelLoaded.value
    default: return false
  }
}

export function getLoadingStatus(): string {
  const loaded = []
  if (wakeModelLoaded.value) loaded.push('唤醒')
  if (transcribeModelLoaded.value) loaded.push('转写')
  if (llmModelLoaded.value) loaded.push('对话')
  if (ttsModelLoaded.value) loaded.push('TTS')
  if (loaded.length === 0) return '正在加载模型...'
  if (loaded.length === 4) return '所有模型已加载'
  return `已加载: ${loaded.join('、')} 模型`
}

export function resetModelStatus(): void {
  wakeModelLoaded.value = false
  transcribeModelLoaded.value = false
  llmModelLoaded.value = false
  ttsModelLoaded.value = false
  allModelsLoaded.value = false
  backendReady.value = false
  isLoading.value = true
  message.destroy()
}

export function useModelStatus() {
  if (!isRegistered) ensureListener()
  return {
    wakeModelLoaded,
    transcribeModelLoaded,
    llmModelLoaded,
    ttsModelLoaded,
    allModelsLoaded,
    backendReady,
    isLoading,
    isWakeReady,
    isTranscribeReady,
    isLlmReady,
    isTtsReady,
    isFullyReady,
    isModelLoaded,
    getLoadingStatus,
    resetModelStatus,
  }
}