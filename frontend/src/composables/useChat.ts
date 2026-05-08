import { ref, computed, onMounted, onUnmounted } from 'vue'
import { onBackendEvent, sendMessage, cancelGeneration, clearHistory, requestHistory } from './useBackend'
import type { BackendEvent } from '../types'

// 消息类型定义
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

// 状态
export const messages = ref<ChatMessage[]>([])
export const isGenerating = ref(false)
export const currentResponse = ref('')
export const inputText = ref('')
export const isTranscribing = ref(false)  // 语音转写中状态

// 计算属性
export const hasMessages = computed(() => messages.value.length > 0)
export const canSend = computed(() => inputText.value.trim().length > 0 && !isGenerating.value)

// 事件取消订阅函数
let unsubscribe: (() => void) | null = null

// 使用全局变量防止 HMR 导致的重复初始化
const isInitialized = () => !!window.__useChat_initialized

/**
 * 生成唯一ID
 */
function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * 处理后端事件
 */
function handleBackendEvent(event: BackendEvent) {
  switch (event.event) {
    case 'history_loaded':
      // 加载历史记录，使用后端返回的时间戳
      messages.value = event.history.map((msg) => ({
        id: generateId(),
        role: msg.role as 'user' | 'assistant',
        content: msg.content,
        timestamp: msg.timestamp || Date.now(),
      }))
      break

    case 'chat_chunk':
      // 接收流式响应片段
      currentResponse.value += event.content
      break

    case 'chat_complete':
      // 生成完成，保存完整回复
      if (currentResponse.value) {
        messages.value.push({
          id: generateId(),
          role: 'assistant',
          content: currentResponse.value,
          timestamp: Date.now(),
        })
      }
      isGenerating.value = false
      currentResponse.value = ''
      break

    case 'chat_cancelled':
      // 生成被取消，保留已生成的内容
      if (currentResponse.value) {
        messages.value.push({
          id: generateId(),
          role: 'assistant',
          content: currentResponse.value,
          timestamp: Date.now(),
        })
      }
      isGenerating.value = false
      currentResponse.value = ''
      break

    case 'history_cleared':
      // 历史已清空
      messages.value = []
      break

    case 'error':
      // 错误处理
      if (isGenerating.value) {
        isGenerating.value = false
        currentResponse.value = ''
      }
      // 转写出错时也要重置状态
      if (isTranscribing.value) {
        isTranscribing.value = false
      }
      break
  }
}

/**
 * 发送用户消息
 */
export function sendChatMessage(content?: string): void {
  const text = content?.trim() || inputText.value.trim()
  if (!text || isGenerating.value) return

  // 添加用户消息
  messages.value.push({
    id: generateId(),
    role: 'user',
    content: text,
    timestamp: Date.now(),
  })

  // 清空输入框
  inputText.value = ''

  // 标记生成中状态
  isGenerating.value = true
  currentResponse.value = ''

  // 发送给后端
  sendMessage(text)
}

/**
 * 取消当前生成
 */
export function cancelChatGeneration(): void {
  if (!isGenerating.value) return
  cancelGeneration()
}

/**
 * 清空所有对话
 */
export function clearChatHistory(): void {
  clearHistory()
}

/**
 * 刷新对话历史
 */
export function refreshHistory(): void {
  requestHistory()
}

/**
 * 设置输入文本
 */
export function setInputText(text: string): void {
  inputText.value = text
}

/**
 * 追加输入文本（用于语音转写结果回填）
 */
export function appendInputText(text: string): void {
  if (inputText.value) {
    inputText.value += ' ' + text
  } else {
    inputText.value = text
  }
}

/**
 * 处理转写结果
 * 将语音转写文本填入输入框
 */
function handleTranscription(text: string): void {
  isTranscribing.value = false  // 转写完成
  if (text && text.trim()) {
    appendInputText(text)
  } else {
    alert('未能识别到语音内容，请重试')
  }
}

/**
 * useChat Composable
 * 提供对话状态管理功能
 */
export function useChat() {
  // 防止重复初始化
  if (isInitialized()) {
    console.log('[useChat] 已初始化，跳过')
    return {
      messages,
      isGenerating,
      currentResponse,
      inputText,
      hasMessages,
      canSend,
      sendChatMessage,
      cancelChatGeneration,
      clearChatHistory,
      refreshHistory,
      setInputText,
      appendInputText,
    }
  }

  console.log('[useChat] 开始初始化')

  onMounted(() => {
    // 防止重复注册
    if (unsubscribe) {
      console.log('[useChat] onMounted: 已存在订阅，跳过')
      return
    }

    console.log('[useChat] onMounted: 注册事件监听')
    // 注册事件监听
    unsubscribe = onBackendEvent((event) => {
      // 先处理转写结果
      if (event.event === 'transcription_result') {
        handleTranscription(event.text)
      }
      // 再处理对话事件
      handleBackendEvent(event)
    })

    // 请求历史记录
    requestHistory()
  })

  onUnmounted(() => {
    console.log('[useChat] onUnmounted: 清理订阅')
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }
    window.__useChat_initialized = false
  })

  window.__useChat_initialized = true

  console.log('[useChat] 初始化完成')

  return {
    messages,
    isGenerating,
    currentResponse,
    inputText,
    isTranscribing,
    hasMessages,
    canSend,
    sendChatMessage,
    cancelChatGeneration,
    clearChatHistory,
    refreshHistory,
    setInputText,
    appendInputText,
  }
}
