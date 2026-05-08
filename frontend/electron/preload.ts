import { contextBridge, ipcRenderer } from 'electron'

// 后端事件类型定义（与 backend.py 推送的事件对应）
export type BackendEvent =
  | { event: 'partial_ready' }
  | { event: 'wake_model_loaded' }
  | { event: 'transcribe_model_loaded' }
  | { event: 'llm_model_loaded' }
  | { event: 'tts_model_loaded' }
  | { event: 'full_ready' }
  | { event: 'ready' }
  | { event: 'wake' }
  | { event: 'transcription_result'; text: string }
  | { event: 'chat_chunk'; content: string }
  | { event: 'chat_complete' }
  | { event: 'chat_cancelled' }
  | { event: 'tts_started' }
  | { event: 'tts_stopped' }
  | { event: 'tts_complete' }
  | { event: 'history_loaded'; history: Array<{ role: string; content: string }> }
  | { event: 'history_cleared' }
  | { event: 'error'; type?: string; msg: string }

// 前端指令类型定义（发送给 backend.py）
export type FrontendAction =
  | { action: 'set_mode'; mode: 'wake' | 'transcribe' }
  | { action: 'transcribe_file'; file_path: string }
  | { action: 'send_message'; content: string }
  | { action: 'cancel_generation' }
  | { action: 'clear_history' }
  | { action: 'get_history' }
  | { action: 'tts_play'; text: string }
  | { action: 'tts_stop' }
  | { action: 'start_loading' };



// 暴露给渲染进程的 API
contextBridge.exposeInMainWorld('electronAPI', {
  // 发送指令到主进程（由主进程转发给后端 Python）
  sendToBackend: (action: FrontendAction) => {
    ipcRenderer.send('to-backend', action)
  },

  // 注册后端事件回调
  onBackendEvent: (callback: (event: BackendEvent) => void) => {
    const handler = (_: unknown, data: BackendEvent) => callback(data)
    ipcRenderer.on('from-backend', handler)
    // 返回取消订阅函数
    return () => {
      ipcRenderer.removeListener('from-backend', handler)
    }
  },

  // 注册一次性后端事件回调
  onceBackendEvent: (callback: (event: BackendEvent) => void) => {
    const handler = (_: unknown, data: BackendEvent) => callback(data)
    ipcRenderer.once('from-backend', handler)
  },

  // 窗口控制
  showWindow: () => ipcRenderer.send('show-window'),
  hideWindow: () => ipcRenderer.send('hide-window'),
  minimizeWindow: () => ipcRenderer.send('minimize-window'),

  // 获取后端可执行文件路径（用于调试或特殊场景）
  getBackendPath: () => ipcRenderer.invoke('get-backend-path'),

  // 保存临时音频文件
  saveTempAudio: (data: ArrayBuffer, fileName: string) => ipcRenderer.invoke('save-temp-audio', data, fileName),
})

// TypeScript 类型声明（供前端使用）
declare global {
  interface Window {
    electronAPI: {
      sendToBackend: (action: FrontendAction) => void
      onBackendEvent: (callback: (event: BackendEvent) => void) => () => void
      onceBackendEvent: (callback: (event: BackendEvent) => void) => void
      showWindow: () => void
      hideWindow: () => void
      minimizeWindow: () => void
      getBackendPath: () => Promise<string>
      saveTempAudio: (data: ArrayBuffer, fileName: string) => Promise<string>
    }
  }
}
