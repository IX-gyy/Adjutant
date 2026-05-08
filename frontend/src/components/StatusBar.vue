<template>
  <div class="status-bar">
    <div class="status-title">
      <span class="app-name">副官AI</span>
    </div>
    <div class="status-indicators">
      <div
        class="status-item"
        :class="{ active: wakeReady }"
        title="唤醒模型"
      >
        <div class="status-dot" :class="{ active: wakeReady }"></div>
        <span class="status-label">唤醒</span>
      </div>
      <div
        class="status-item"
        :class="{ active: transcribeReady }"
        title="转写模型"
      >
        <div class="status-dot" :class="{ active: transcribeReady }"></div>
        <span class="status-label">转写</span>
      </div>
      <div
        class="status-item"
        :class="{ active: llmReady }"
        title="对话模型"
      >
        <div class="status-dot" :class="{ active: llmReady }"></div>
        <span class="status-label">对话</span>
      </div>
      <div
        class="status-item"
        :class="{ active: ttsReady }"
        title="TTS语音模型"
      >
        <div class="status-dot" :class="{ active: ttsReady }"></div>
        <span class="status-label">语音</span>
      </div>
    </div>
    <div class="window-controls">
      <button class="control-btn clear-history" @click="handleClearHistory" title="清除历史">
        <svg viewBox="0 0 24 24" width="12" height="12">
          <path
            fill="currentColor"
            d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
          />
        </svg>
      </button>
      <button class="control-btn minimize" @click="minimizeWindow" title="最小化">
        <svg viewBox="0 0 24 24" width="12" height="12">
          <rect x="4" y="11" width="16" height="2" fill="currentColor"/>
        </svg>
      </button>
      <button class="control-btn close" @click="closeWindow" title="关闭">
        <svg viewBox="0 0 24 24" width="12" height="12">
          <path
            fill="currentColor"
            d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
          />
        </svg>
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { hideWindow, clearHistory } from '../composables/useBackend'
import { Modal } from 'ant-design-vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'
import { h } from 'vue'

interface Props {
  wakeReady: boolean
  transcribeReady: boolean
  llmReady: boolean
  ttsReady: boolean
}

defineProps<Props>()

function minimizeWindow() {
  // 最小化窗口 - 任务栏保留图标
  if (window.electronAPI) {
    window.electronAPI.minimizeWindow()
  }
}

function closeWindow() {
  // 关闭按钮 - 隐藏到托盘（任务栏图标消失）
  hideWindow()
}

function handleClearHistory() {
  Modal.confirm({
    title: '确认清除历史记录？',
    icon: h(ExclamationCircleOutlined),
    content: '此操作将清空所有对话历史，无法恢复。',
    okText: '清除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      clearHistory()
    },
  })
}
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 16px;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  color: #fff;
  -webkit-app-region: drag;
  user-select: none;
}

.status-title {
  display: flex;
  align-items: center;
  gap: 12px;
  -webkit-app-region: no-drag;
}

.app-name {
  font-size: 14px;
  font-weight: 600;
  color: #52c41a;
  text-shadow: 0 0 10px rgba(82, 196, 26, 0.5);
}

.loading-text {
  font-size: 12px;
  color: #8c8c8c;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: 16px;
  -webkit-app-region: no-drag;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
  opacity: 0.4;
  transition: opacity 0.3s ease;
}

.status-item.active {
  opacity: 1;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #8c8c8c;
  transition: all 0.3s ease;
}

.status-dot.active {
  background: #52c41a;
  box-shadow: 0 0 8px rgba(82, 196, 26, 0.6);
}

.status-label {
  font-size: 11px;
  color: #bfbfbf;
}

.status-item.active .status-label {
  color: #fff;
}

.window-controls {
  display: flex;
  align-items: center;
  gap: 8px;
  -webkit-app-region: no-drag;
}

.control-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: #bfbfbf;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 4px;
  transition: all 0.2s ease;
}

.control-btn:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #fff;
}

.control-btn.close:hover {
  background: #ff4d4f;
}

.control-btn.clear-history:hover {
  background: #faad14;
}
</style>
