import { ref, onMounted, onUnmounted } from 'vue'
import type { BackendEvent, FrontendAction } from '../types'

// 后端连接状态
export const isBackendReady = ref(false)
export const backendError = ref<string | null>(null)

// 事件监听器取消函数
let unsubscribe: (() => void) | null = null

// 使用全局变量防止 HMR 导致的重复初始化
declare global {
  interface Window {
    __useBackend_initialized?: boolean
  }
}
const isInitialized = () => !!window.__useBackend_initialized

/**
 * 发送指令到后端
 */
export function sendToBackend(action: FrontendAction) {
  console.log('[useBackend] 发送指令:', action)
  if (window.electronAPI) {
    window.electronAPI.sendToBackend(action)
  } else {
    console.error('[useBackend] electronAPI 不可用')
  }
}

/**
 * 注册后端事件监听
 */
export function onBackendEvent(callback: (event: BackendEvent) => void) {
  if (window.electronAPI) {
    return window.electronAPI.onBackendEvent(callback)
  }
  console.error('[useBackend] electronAPI 不可用')
  return () => {}
}

/**
 * 一次性监听后端事件
 */
export function onceBackendEvent(callback: (event: BackendEvent) => void) {
  if (window.electronAPI) {
    window.electronAPI.onceBackendEvent(callback)
  } else {
    console.error('[useBackend] electronAPI 不可用')
  }
}

/**
 * 切换到唤醒模式（后台运行）
 */
export function setWakeMode() {
  sendToBackend({ action: 'set_mode', mode: 'wake' })
}

/**
 * 切换到转写模式（前台交互）
 */
export function setTranscribeMode() {
  sendToBackend({ action: 'set_mode', mode: 'transcribe' })
}

/**
 * 获取历史指令
 */
export function requestHistory() {
  sendToBackend({ action: 'get_history' })
}

/**
 * 获取后端当前状态（解决前端启动晚错过事件的问题）
 */
export function requestStatus() {
  sendToBackend({ action: 'get_status' })
}

/**
 * 清空对话历史
 */
export function clearHistory() {
  sendToBackend({ action: 'clear_history' })
}

/**
 * 发送音频文件进行转写
 */
export function transcribeFile(filePath: string) {
  sendToBackend({ action: 'transcribe_file', file_path: filePath })
}

/**
 * 发送消息到AI对话
 */
export function sendMessage(content: string) {
  sendToBackend({ action: 'send_message', content })
}

/**
 * 取消正在进行的AI生成
 */
let lastCancelTime = 0
export function cancelGeneration() {
  const now = Date.now()
  // 防抖：500ms 内只允许一次取消
  if (now - lastCancelTime < 500) {
    console.log('[useBackend] 取消操作过于频繁，忽略')
    return
  }
  lastCancelTime = now
  console.log('[useBackend] 发送取消生成指令')
  sendToBackend({ action: 'cancel_generation' })
}

/**
 * 播放TTS语音
 */
export function ttsPlay(text: string) {
  console.log('[useBackend] 发送TTS播放指令:', text.slice(0, 30) + '...')
  sendToBackend({ action: 'tts_play', text })
}

/**
 * 停止TTS播放
 */
let lastTtsStopTime = 0
export function ttsStop() {
  const now = Date.now()
  // 防抖：300ms 内只允许一次停止
  if (now - lastTtsStopTime < 300) {
    console.log('[useBackend] 停止TTS操作过于频繁，忽略')
    return
  }
  lastTtsStopTime = now
  console.log('[useBackend] 发送TTS停止指令')
  sendToBackend({ action: 'tts_stop' })
}

/**
 * 显示主窗口
 */
export function showWindow() {
  if (window.electronAPI) {
    window.electronAPI.showWindow()
  }
}

/**
 * 隐藏主窗口（到托盘）
 */
export function hideWindow() {
  if (window.electronAPI) {
    window.electronAPI.hideWindow()
  }
}

/**
 * 最小化窗口（任务栏保留）
 */
export function minimizeWindow() {
  if (window.electronAPI) {
    window.electronAPI.minimizeWindow()
  }
}

/**
 * 获取后端路径（调试使用）
 */
export async function getBackendPath(): Promise<string> {
  if (window.electronAPI) {
    return await window.electronAPI.getBackendPath()
  }
  return ''
}

export function startLoading() {
  console.log('[useBackend] 通知后端开始加载模型')
  sendToBackend({ action: 'start_loading' })
}

/**
 * 设置彩蛋开关状态
 */
export function setEasterEggEnabled(enabled: boolean) {
  console.log('[useBackend] 设置彩蛋开关:', enabled)
  sendToBackend({ action: 'set_easter_egg', enabled })
}

// ================= 待办事项相关 API =================

/**
 * 添加待办事项
 * @param content 待办内容
 * @param dueDate 截止时间（可选，格式：YYYY-MM-DD HH:MM）
 */
export function addTodo(content: string, dueDate?: string) {
  console.log('[useBackend] 添加待办:', content, dueDate)
  sendToBackend({ action: 'add_todo', content, due_date: dueDate })
}

/**
 * 获取待办事项列表
 * @param filter 筛选条件：'today' 今天 | 'all' 全部（默认）
 */
export function listTodos(filter: 'today' | 'all' = 'all') {
  console.log('[useBackend] 获取待办列表:', filter)
  sendToBackend({ action: 'list_todos', filter })
}

/**
 * 完成待办事项
 * @param todoId 待办事项 ID
 */
export function completeTodo(todoId: number) {
  console.log('[useBackend] 完成待办:', todoId)
  sendToBackend({ action: 'complete_todo', todo_id: todoId })
}

/**
 * 删除待办事项
 * @param todoId 待办事项 ID
 */
export function deleteTodo(todoId: number) {
  console.log('[useBackend] 删除待办:', todoId)
  sendToBackend({ action: 'delete_todo', todo_id: todoId })
}

// ================= 长期记忆相关 API =================

/**
 * 查询长期记忆
 * @param query 查询关键词（可选）
 * @param after 起始时间戳（可选）
 * @param before 结束时间戳（可选）
 */
export function getMemories(query?: string, after?: number, before?: number) {
  console.log('[useBackend] 查询记忆:', query)
  sendToBackend({ action: 'get_memories', query, after, before })
}

/**
 * useBackend Composable
 * 提供后端通信的基础功能
 */
export function useBackend() {
  // 防止重复初始化
  if (isInitialized()) {
    console.log('[useBackend] 已初始化，跳过')
    return {
    isBackendReady,
    backendError,
    sendToBackend,
    onBackendEvent,
    onceBackendEvent,
    setWakeMode,
    setTranscribeMode,
    requestHistory,
    requestStatus,
    clearHistory,
    transcribeFile,
    sendMessage,
    cancelGeneration,
    ttsPlay,
    ttsStop,
    setEasterEggEnabled,
    addTodo,
    listTodos,
    completeTodo,
    deleteTodo,
    getMemories,
    showWindow,
    hideWindow,
    minimizeWindow,
    getBackendPath,
  }
}

  console.log('[useBackend] 开始初始化')

  onMounted(() => {
    // 防止重复注册
    if (unsubscribe) {
      console.log('[useBackend] onMounted: 已存在订阅，跳过')
      return
    }

    // 注册全局事件监听
    unsubscribe = onBackendEvent((event) => {
      // 处理基础连接状态
      switch (event.event) {
        case 'partial_ready':
        case 'full_ready':
          isBackendReady.value = true
          backendError.value = null
          break
        case 'error':
          backendError.value = event.msg
          break
      }
    })
  })

  onUnmounted(() => {
    // 清理事件监听
    console.log('[useBackend] onUnmounted: 清理订阅')
    if (unsubscribe) {
      unsubscribe()
      unsubscribe = null
    }
    window.__useBackend_initialized = false
  })

  window.__useBackend_initialized = true

  return {
    isBackendReady,
    backendError,
    sendToBackend,
    onBackendEvent,
    onceBackendEvent,
    setWakeMode,
    setTranscribeMode,
    requestHistory,
    requestStatus,
    clearHistory,
    transcribeFile,
    sendMessage,
    cancelGeneration,
    ttsPlay,
    ttsStop,
    setEasterEggEnabled,
    addTodo,
    listTodos,
    completeTodo,
    deleteTodo,
    getMemories,
    showWindow,
    hideWindow,
    minimizeWindow,
    getBackendPath,
  }
}
