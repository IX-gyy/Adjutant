import { ref, onMounted, onUnmounted } from 'vue'
import { onBackendEvent, ttsPlay as sendTtsPlay, ttsStop as sendTtsStop } from './useBackend'
import type { BackendEvent } from '../types'

// TTS状态
export const isTtsPlaying = ref(false)
export const isTtsLoading = ref(false)
export const currentTtsMessageId = ref<string | null>(null)

// 事件取消订阅函数
let unsubscribe: (() => void) | null = null

// 使用全局变量防止 HMR 导致的重复初始化
const isInitialized = () => !!window.__useTTS_initialized

/**
 * 处理后端事件
 */
function handleBackendEvent(event: BackendEvent) {
  switch (event.event) {
    case 'tts_started':
      isTtsPlaying.value = true
      isTtsLoading.value = false
      break

    case 'tts_stopped':
      isTtsPlaying.value = false
      isTtsLoading.value = false
      currentTtsMessageId.value = null
      break

    case 'tts_complete':
      isTtsPlaying.value = false
      isTtsLoading.value = false
      currentTtsMessageId.value = null
      break

    case 'chat_complete':
    case 'chat_cancelled':
      // AI生成完成或取消时，重置TTS加载状态
      isTtsLoading.value = false
      break
  }
}

/**
 * 播放指定消息的TTS
 * @param messageId 消息ID
 * @param text 要播放的文本
 */
export function playTts(messageId: string, text: string): void {
  if (!text || !text.trim()) return

  // 如果正在播放同一条消息，则停止
  if (currentTtsMessageId.value === messageId && isTtsPlaying.value) {
    stopTts()
    return
  }

  // 如果正在播放其他消息，先停止
  if (isTtsPlaying.value) {
    sendTtsStop()
  }

  currentTtsMessageId.value = messageId
  isTtsLoading.value = true
  sendTtsPlay(text)
}

/**
 * 停止TTS播放
 */
export function stopTts(): void {
  if (!isTtsPlaying.value && !isTtsLoading.value) return
  sendTtsStop()
}

/**
 * 检查指定消息是否正在播放
 */
export function isPlayingMessage(messageId: string): boolean {
  return currentTtsMessageId.value === messageId && isTtsPlaying.value
}

/**
 * useTTS Composable
 * 提供TTS语音合成功能
 */
export function useTTS() {
  // 防止重复初始化
  if (isInitialized()) {
    console.log('[useTTS] 已初始化，跳过')
    return {
      isTtsPlaying,
      isTtsLoading,
      currentTtsMessageId,
      playTts,
      stopTts,
      isPlayingMessage,
    }
  }

  console.log('[useTTS] 开始初始化')

  onMounted(() => {
    // 防止重复注册
    if (unsubscribe) {
      console.log('[useTTS] onMounted: 已存在订阅，跳过')
      return
    }

    console.log('[useTTS] onMounted: 注册事件监听')
    // 注册事件监听
    unsubscribe = onBackendEvent(handleBackendEvent)
  })

  onUnmounted(() => {
    console.log('[useTTS] onUnmounted: 清理订阅')
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }
    window.__useTTS_initialized = false
  })

  window.__useTTS_initialized = true

  console.log('[useTTS] 初始化完成')

  return {
    isTtsPlaying,
    isTtsLoading,
    currentTtsMessageId,
    playTts,
    stopTts,
    isPlayingMessage,
  }
}
