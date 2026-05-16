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
      <!-- 彩蛋滑动开关 -->
      <div
        class="easter-egg-toggle"
        :class="{ active: easterEggEnabled }"
        @click="toggleEasterEgg"
        :title="easterEggEnabled ? '彩蛋已开启' : '彩蛋已关闭'"
      >
        <div class="toggle-track">
          <div class="toggle-thumb">
            <!-- 电源图标 -->
            <svg class="power-icon" viewBox="0 0 24 24" width="10" height="10">
              <path
                fill="currentColor"
                d="M12 3a1 1 0 0 1 1 1v8a1 1 0 1 1-2 0V4a1 1 0 0 1 1-1zm-5.657 3.343a1 1 0 0 1 0 1.414 7 7 0 1 0 9.9 0 1 1 0 1 1 1.414-1.414 9 9 0 1 1-12.728 0 1 1 0 0 1 1.414 0z"
              />
            </svg>
          </div>
        </div>
      </div>
      <!-- 待办事项按钮 -->
      <button class="control-btn todo-btn" @click="openTodoPanel" title="战术日程表">
        <svg viewBox="0 0 24 24" width="12" height="12">
          <path
            fill="currentColor"
            d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
          />
        </svg>
      </button>
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
import { ref, onMounted, h } from 'vue'
import { hideWindow, clearHistory, setEasterEggEnabled, requestStatus, onBackendEvent } from '../composables/useBackend'
import { Modal } from 'ant-design-vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'

interface Props {
  wakeReady: boolean
  transcribeReady: boolean
  llmReady: boolean
  ttsReady: boolean
}

defineProps<Props>()

const easterEggEnabled = ref(true)

const emit = defineEmits<{
  'open-todo': []
}>()

onMounted(() => {
  // 监听彩蛋状态更新
  onBackendEvent((event) => {
    if (event.event === 'easter_egg_status') {
      easterEggEnabled.value = event.enabled
    } else if (event.event === 'status_update' && event.easter_egg_enabled !== undefined) {
      easterEggEnabled.value = event.easter_egg_enabled
    }
  })
  // 请求当前状态
  requestStatus()
})

function toggleEasterEgg() {
  const newValue = !easterEggEnabled.value
  easterEggEnabled.value = newValue
  setEasterEggEnabled(newValue)
}

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

function openTodoPanel() {
  emit('open-todo')
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
/* 主题修改：StatusBar 舰桥风格深色渐变 */
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--terran-spacing-sm) var(--terran-spacing-lg);
  /* 舰桥风格深色渐变 */
  background: var(--terran-statusbar-bg);
  border-bottom: var(--terran-statusbar-border);
  color: var(--terran-text-primary);
  -webkit-app-region: drag;
  user-select: none;
}

.status-title {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-md);
  -webkit-app-region: no-drag;
}

/* 主题修改：应用名称带主色发光效果 */
.app-name {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-primary);
  text-shadow: var(--terran-text-glow-primary);
  letter-spacing: 1px;
}

.status-indicators {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-lg);
  -webkit-app-region: no-drag;
}

/* 主题修改：状态指示器样式 */
.status-item {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  opacity: 0.4;
  transition: opacity var(--terran-transition-slow);
}

.status-item.active {
  opacity: 1;
}

/* 主题修改：状态指示灯 */
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: var(--terran-radius-circle);
  background: var(--terran-status-inactive);
  transition: all var(--terran-transition-slow);
}

/* 主题修改：激活状态带发光效果 */
.status-dot.active {
  background: var(--terran-status-active);
  box-shadow: var(--terran-glow-primary);
  animation: pulse 2s infinite;
}

.status-label {
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-item.active .status-label {
  color: var(--terran-text-primary);
}

/* 窗口控制按钮 */
.window-controls {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  -webkit-app-region: no-drag;
}

.control-btn {
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--terran-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.control-btn:hover {
  background: var(--terran-bg-quaternary);
  color: var(--terran-text-primary);
}

/* 主题修改：关闭按钮hover对应颜色反馈 */
.control-btn.close:hover {
  background: var(--terran-danger);
  color: #fff;
  box-shadow: var(--terran-glow-danger);
}

/* 主题修改：清除历史按钮hover对应颜色反馈 */
.control-btn.clear-history:hover {
  background: var(--terran-warning);
  color: var(--terran-bg-primary);
  box-shadow: var(--terran-glow-warning);
}

/* 主题修改：待办按钮hover对应颜色反馈 */
.control-btn.todo-btn:hover {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
  box-shadow: var(--terran-glow-primary);
}

/* 彩蛋滑动开关样式 */
.easter-egg-toggle {
  cursor: pointer;
  padding: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.toggle-track {
  width: 44px;
  height: 22px;
  background: var(--terran-bg-quaternary);
  border-radius: 11px;
  position: relative;
  transition: all 0.3s ease;
  border: 1px solid var(--terran-border-secondary);
}

.easter-egg-toggle.active .toggle-track {
  background: rgba(255, 77, 79, 0.3);
  border-color: var(--terran-danger);
  box-shadow: 0 0 8px rgba(255, 77, 79, 0.5), inset 0 0 4px rgba(255, 77, 79, 0.2);
}

.toggle-thumb {
  width: 18px;
  height: 18px;
  border-radius: 50%;
  background: var(--terran-bg-tertiary);
  position: absolute;
  top: 1px;
  left: 1px;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  border: 1px solid var(--terran-border-secondary);
}

.easter-egg-toggle.active .toggle-thumb {
  transform: translateX(22px);
  background: var(--terran-danger);
  border-color: var(--terran-danger);
  box-shadow: 0 0 10px rgba(255, 77, 79, 0.8), 0 0 20px rgba(255, 77, 79, 0.4);
}

.power-icon {
  width: 10px;
  height: 10px;
  color: var(--terran-text-secondary);
  opacity: 0.6;
  transition: all 0.3s ease;
}

.easter-egg-toggle.active .power-icon {
  color: #fff;
  opacity: 1;
}

.easter-egg-toggle:hover .toggle-track {
  border-color: var(--terran-border-primary);
}

.easter-egg-toggle.active:hover .toggle-track {
  border-color: var(--terran-danger);
  box-shadow: 0 0 12px rgba(255, 77, 79, 0.7), inset 0 0 6px rgba(255, 77, 79, 0.3);
}

/* 主题修改：最小化按钮hover效果 */
.control-btn.minimize:hover {
  background: var(--terran-info);
  color: #fff;
  box-shadow: var(--terran-glow-info);
}
</style>
