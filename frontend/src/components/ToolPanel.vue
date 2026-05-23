<template>
  <div class="tool-panel-overlay" v-if="visible" @click.self="closePanel">
    <div class="tool-panel">
      <!-- 面板头部 -->
      <div class="panel-header">
        <div class="header-title">
          <svg class="header-icon" viewBox="0 0 24 24" width="18" height="18">
            <path
              fill="currentColor"
              d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"
            />
          </svg>
          <span class="title-text">战术工具箱</span>
        </div>
        <button class="close-btn" @click="closePanel" title="关闭">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path
              fill="currentColor"
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </div>

      <!-- 工具选择器 -->
      <div class="tool-selector">
        <button
          v-for="tool in tools"
          :key="tool.id"
          class="tool-tab"
          :class="{ active: currentTool === tool.id }"
          @click="switchTool(tool.id)"
        >
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" :d="tool.icon" />
          </svg>
          <span>{{ tool.name }}</span>
        </button>
      </div>

      <!-- 工具内容区域 -->
      <div class="tool-content">
        <!-- 待办事项工具 -->
        <div v-if="currentTool === 'todo'" class="tool-section">
          <!-- 筛选标签 -->
          <div class="filter-tabs">
            <button
              class="filter-tab"
              :class="{ active: todoFilter === 'all' }"
              @click="switchTodoFilter('all')"
            >
              全部
            </button>
            <button
              class="filter-tab"
              :class="{ active: todoFilter === 'today' }"
              @click="switchTodoFilter('today')"
            >
              今日
            </button>
          </div>

          <!-- 待办列表 -->
          <div class="todo-list" v-if="todos.length > 0">
            <div
              v-for="todo in todos"
              :key="todo.id"
              class="todo-item"
              :class="{ completed: todo.status === 'completed' }"
            >
              <div class="todo-checkbox" @click="toggleTodo(todo.id)">
                <svg v-if="todo.status === 'completed'" viewBox="0 0 24 24" width="14" height="14">
                  <path
                    fill="currentColor"
                    d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"
                  />
                </svg>
              </div>
              <div class="todo-content">
                <div class="todo-text">{{ todo.content }}</div>
                <div class="todo-meta" v-if="todo.due_date">
                  <svg viewBox="0 0 24 24" width="12" height="12">
                    <path
                      fill="currentColor"
                      d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"
                    />
                  </svg>
                  <span :class="{ overdue: isOverdue(todo.due_date) && todo.status !== 'completed' }">
                    {{ formatDate(todo.due_date) }}
                  </span>
                </div>
              </div>
              <button class="delete-btn" @click="removeTodo(todo.id)" title="删除">
                <svg viewBox="0 0 24 24" width="14" height="14">
                  <path
                    fill="currentColor"
                    d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                  />
                </svg>
              </button>
            </div>
          </div>

          <!-- 空状态 -->
          <div class="empty-state" v-else>
            <svg viewBox="0 0 24 24" width="48" height="48">
              <path
                fill="currentColor"
                d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
              />
            </svg>
            <p>暂无待办事项</p>
            <span>指挥官，当前没有战术安排</span>
          </div>

          <!-- 添加新待办 -->
          <div class="add-todo-form">
            <input
              v-model="newTodoContent"
              type="text"
              class="todo-input"
              placeholder="输入新的战术指令..."
              @keydown.enter="addNewTodo"
            />
            <input
              v-model="newTodoDate"
              type="datetime-local"
              class="date-input"
              :min="minDateTime"
            />
            <button
              class="add-btn"
              :disabled="!canAddTodo"
              @click="addNewTodo"
            >
              <svg viewBox="0 0 24 24" width="16" height="16">
                <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
              </svg>
            </button>
          </div>
        </div>

        <!-- 番茄钟工具 -->
        <div v-if="currentTool === 'pomodoro'" class="tool-section pomodoro-section">
          <div class="pomodoro-display">
            <div class="timer-circle" :class="{ running: isTimerRunning, paused: isTimerPaused }">
              <div class="timer-time">{{ formatTime(timerSeconds) }}</div>
              <div class="timer-status">{{ timerStatusText }}</div>
            </div>
          </div>

          <div class="pomodoro-controls">
            <button
              v-if="!isTimerRunning && !isTimerPaused"
              class="control-btn primary"
              @click="startTimer"
            >
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M8 5v14l11-7z"/>
              </svg>
              <span>开始</span>
            </button>
            <button
              v-if="isTimerRunning"
              class="control-btn warning"
              @click="pauseTimer"
            >
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
              </svg>
              <span>暂停</span>
            </button>
            <button
              v-if="isTimerPaused"
              class="control-btn primary"
              @click="resumeTimer"
            >
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M8 5v14l11-7z"/>
              </svg>
              <span>继续</span>
            </button>
            <button
              v-if="isTimerRunning || isTimerPaused"
              class="control-btn danger"
              @click="stopTimer"
            >
              <svg viewBox="0 0 24 24" width="20" height="20">
                <path fill="currentColor" d="M6 6h12v12H6z"/>
              </svg>
              <span>停止</span>
            </button>
          </div>

          <div class="pomodoro-presets">
            <div class="preset-label">快速设置</div>
            <div class="preset-buttons">
              <button
                v-for="preset in timerPresets"
                :key="preset.minutes"
                class="preset-btn"
                :class="{ active: timerDuration === preset.minutes * 60 }"
                @click="setTimerDuration(preset.minutes * 60)"
              >
                {{ preset.label }}
              </button>
            </div>
          </div>

          <!-- 后端触发的倒计时提醒 -->
          <div v-if="backendCountdownActive" class="backend-countdown-notice">
            <div class="notice-icon">🔔</div>
            <div class="notice-content">
              <div class="notice-title">后端倒计时进行中</div>
              <div class="notice-text">{{ backendCountdownText }}</div>
            </div>
          </div>
        </div>

        <!-- 系统状态工具 -->
        <div v-if="currentTool === 'system'" class="tool-section system-section">
          <div v-if="systemLoading" class="system-loading">
            <div class="loading-spinner"></div>
            <span>正在扫描系统状态...</span>
          </div>

          <div v-else-if="systemData" class="system-grid">
            <!-- CPU -->
            <div class="system-card" v-if="systemData.cpu">
              <div class="card-icon cpu">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M9 2v2H7V2h2zm10 2v2h-2V4h2zM9 20v2H7v-2h2zm10 0v2h-2v-2h2zM4 9h2v2H4V9zm0 4h2v2H4v-2zm16-4h-2v2h2V9zm0 4h-2v2h2v-2zM13 2h-2v3h2V2zm0 17h-2v3h2v-3zM2 13h3v-2H2v2zm17 0h3v-2h-3v2zM6 6h12v12H6V6z"/>
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">CPU</div>
                <div class="card-value">{{ systemData.cpu.usage }}%</div>
                <div class="card-detail">{{ systemData.cpu.cores }}核{{ systemData.cpu.threads }}线程</div>
              </div>
              <div class="card-bar">
                <div class="bar-fill" :style="{ width: systemData.cpu.usage + '%' }" :class="getUsageClass(systemData.cpu.usage)"></div>
              </div>
            </div>

            <!-- 内存 -->
            <div class="system-card" v-if="systemData.memory">
              <div class="card-icon memory">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M17 3H7c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h10c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H7V5h10v14zM9 7h2v2H9V7zm0 4h2v2H9v-2zm0 4h2v2H9v-2z"/>
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">内存</div>
                <div class="card-value">{{ systemData.memory.usage }}%</div>
                <div class="card-detail">{{ systemData.memory.used_gb }}G / {{ systemData.memory.total_gb }}G</div>
              </div>
              <div class="card-bar">
                <div class="bar-fill" :style="{ width: systemData.memory.usage + '%' }" :class="getUsageClass(systemData.memory.usage)"></div>
              </div>
            </div>

            <!-- 磁盘 -->
            <div class="system-card" v-if="systemData.disk">
              <div class="card-icon disk">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">磁盘</div>
                <div class="card-value">{{ systemData.disk.usage }}%</div>
                <div class="card-detail">{{ systemData.disk.used_gb }}G / {{ systemData.disk.total_gb }}G</div>
              </div>
              <div class="card-bar">
                <div class="bar-fill" :style="{ width: systemData.disk.usage + '%' }" :class="getUsageClass(systemData.disk.usage)"></div>
              </div>
            </div>

            <!-- 电池 -->
            <div class="system-card" v-if="systemData.battery !== undefined">
              <div class="card-icon battery" :class="{ charging: systemData.battery?.plugged }">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M15.67 4H14V2h-4v2H8.33C7.6 4 7 4.6 7 5.33v15.33C7 21.4 7.6 22 8.33 22h7.33c.74 0 1.34-.6 1.34-1.33V5.33C17 4.6 16.4 4 15.67 4z"/>
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">电量</div>
                <div class="card-value">{{ systemData.battery ? systemData.battery.percent + '%' : 'N/A' }}</div>
                <div class="card-detail">{{ systemData.battery ? (systemData.battery.plugged ? '已接通电源' : '电池供电') : '无电池信息' }}</div>
              </div>
              <div class="card-bar" v-if="systemData.battery">
                <div class="bar-fill" :style="{ width: systemData.battery.percent + '%' }" :class="getBatteryClass(systemData.battery.percent)"></div>
              </div>
            </div>

            <!-- 网络 -->
            <div class="system-card" v-if="systemData.network">
              <div class="card-icon network" :class="{ connected: systemData.network.status === 'connected' }">
                <svg viewBox="0 0 24 24" width="24" height="24">
                  <path fill="currentColor" d="M1 9l2 2c4.97-4.97 13.03-4.97 18 0l2-2C16.93 2.93 7.08 2.93 1 9zm8 8l3 3 3-3c-1.65-1.66-4.34-1.66-6 0zm-4-4l2 2c2.76-2.76 7.24-2.76 10 0l2-2C15.14 9.14 8.87 9.14 5 13z"/>
                </svg>
              </div>
              <div class="card-content">
                <div class="card-label">网络</div>
                <div class="card-value">{{ systemData.network.status === 'connected' ? '已连接' : '未连接' }}</div>
                <div class="card-detail" v-if="systemData.network.ip">{{ systemData.network.ip }}</div>
              </div>
            </div>
          </div>

          <div v-else class="system-empty">
            <svg viewBox="0 0 24 24" width="48" height="48">
              <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>
            <p>系统状态获取失败</p>
            <button class="retry-btn" @click="refreshSystemStatus">重试</button>
          </div>

          <button class="refresh-btn" @click="refreshSystemStatus" :disabled="systemLoading">
            <svg viewBox="0 0 24 24" width="16" height="16" :class="{ spinning: systemLoading }">
              <path fill="currentColor" d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
            </svg>
            <span>刷新状态</span>
          </button>
        </div>

        <!-- 天气查询工具 -->
        <div v-if="currentTool === 'weather'" class="tool-section weather-section">
          <WeatherPanel :visible="currentTool === 'weather'" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { listTodos, addTodo, completeTodo, deleteTodo, getSystemStatus } from '../composables/useBackend'
import WeatherPanel from './WeatherPanel.vue'
import type { TodoItem, SystemStatusResultEvent } from '../types'

interface Props {
  visible: boolean
  todos: TodoItem[]
  currentFilter: 'all' | 'today'
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:currentFilter': [value: 'all' | 'today']
  'refresh-todos': []
  'countdown-complete': [duration: number, text: string]
}>()

// 工具配置
const tools = [
  {
    id: 'todo',
    name: '待办事项',
    icon: 'M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z'
  },
  {
    id: 'pomodoro',
    name: '番茄钟',
    icon: 'M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42C16.07 4.74 14.12 4 12 4c-4.97 0-9 4.03-9 9s4.02 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z'
  },
  {
    id: 'weather',
    name: '天气查询',
    icon: 'M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z'
  },
  {
    id: 'system',
    name: '系统状态',
    icon: 'M20 18c1.1 0 1.99-.9 1.99-2L22 5c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v11c0 1.1.9 2 2 2H0c0 1.1.9 2 2 2h20c1.1 0 2-.9 2-2h-4zM4 5h16v11H4V5z'
  }
]

// 当前选中的工具
const currentTool = ref('todo')

// 待办事项状态
const todoFilter = ref<'all' | 'today'>(props.currentFilter)
const newTodoContent = ref('')
const newTodoDate = ref('')

// 番茄钟状态
const timerSeconds = ref(25 * 60)
const timerDuration = ref(25 * 60)
const isTimerRunning = ref(false)
const isTimerPaused = ref(false)
let timerInterval: number | null = null

const timerPresets = [
  { minutes: 5, label: '5分钟' },
  { minutes: 15, label: '15分钟' },
  { minutes: 25, label: '25分钟' },
  { minutes: 45, label: '45分钟' },
  { minutes: 60, label: '60分钟' }
]

const timerStatusText = computed(() => {
  if (isTimerRunning.value) return '进行中'
  if (isTimerPaused.value) return '已暂停'
  return '准备就绪'
})

// 后端倒计时状态
const backendCountdownActive = ref(false)
const backendCountdownText = ref('')

// 系统状态
const systemData = ref<SystemStatusResultEvent['data'] | null>(null)
const systemLoading = ref(false)

// 计算属性
const canAddTodo = computed(() => newTodoContent.value.trim().length > 0)

const minDateTime = computed(() => {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
})

// 监听面板显示
watch(() => props.visible, (isVisible) => {
  if (isVisible) {
    if (currentTool.value === 'todo') {
      emit('refresh-todos')
    } else if (currentTool.value === 'system') {
      refreshSystemStatus()
    }
  }
})

// 监听工具切换
watch(currentTool, (tool) => {
  if (tool === 'todo') {
    emit('refresh-todos')
  } else if (tool === 'system') {
    refreshSystemStatus()
  }
})

// 方法
function closePanel() {
  emit('update:visible', false)
}

function switchTool(toolId: string) {
  currentTool.value = toolId
}

function switchTodoFilter(filter: 'all' | 'today') {
  todoFilter.value = filter
  emit('update:currentFilter', filter)
  listTodos(filter)
}

function toggleTodo(todoId: number) {
  completeTodo(todoId)
}

function removeTodo(todoId: number) {
  deleteTodo(todoId)
}

function addNewTodo() {
  if (!canAddTodo.value) return
  const content = newTodoContent.value.trim()
  const dueDate = newTodoDate.value || undefined
  addTodo(content, dueDate)
  newTodoContent.value = ''
  newTodoDate.value = ''
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const isToday = date.toDateString() === now.toDateString()
  if (isToday) {
    return `今天 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
  }
  return `${date.getMonth() + 1}月${date.getDate()}日 ${date.getHours().toString().padStart(2, '0')}:${date.getMinutes().toString().padStart(2, '0')}`
}

function isOverdue(dateStr: string): boolean {
  const date = new Date(dateStr)
  return date < new Date()
}

// 番茄钟方法
function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60)
  const secs = seconds % 60
  return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`
}

function setTimerDuration(seconds: number) {
  if (isTimerRunning.value || isTimerPaused.value) {
    stopTimer()
  }
  timerDuration.value = seconds
  timerSeconds.value = seconds
}

function startTimer() {
  if (isTimerRunning.value) return
  isTimerRunning.value = true
  isTimerPaused.value = false
  timerInterval = window.setInterval(() => {
    if (timerSeconds.value > 0) {
      timerSeconds.value--
    } else {
      completeTimer()
    }
  }, 1000)
}

function pauseTimer() {
  if (!isTimerRunning.value) return
  isTimerRunning.value = false
  isTimerPaused.value = true
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
}

function resumeTimer() {
  if (isTimerRunning.value || !isTimerPaused.value) return
  startTimer()
}

function stopTimer() {
  isTimerRunning.value = false
  isTimerPaused.value = false
  if (timerInterval) {
    clearInterval(timerInterval)
    timerInterval = null
  }
  timerSeconds.value = timerDuration.value
}

function completeTimer() {
  stopTimer()
  emit('countdown-complete', timerDuration.value / 60, `番茄钟 ${timerDuration.value / 60} 分钟倒计时已结束`)
}

// 后端倒计时触发
function triggerBackendCountdown(_duration: number, text: string) {
  backendCountdownActive.value = true
  backendCountdownText.value = text
  // 可以在这里添加视觉提醒
}

function clearBackendCountdown() {
  backendCountdownActive.value = false
  backendCountdownText.value = ''
}

// 系统状态方法
async function refreshSystemStatus() {
  systemLoading.value = true
  try {
    const result = await getSystemStatus()
    systemData.value = result
  } catch (error) {
    console.error('获取系统状态失败:', error)
    systemData.value = null
  } finally {
    systemLoading.value = false
  }
}

function getUsageClass(usage: number): string {
  if (usage < 50) return 'low'
  if (usage < 80) return 'medium'
  return 'high'
}

function getBatteryClass(percent: number): string {
  if (percent > 50) return 'low'
  if (percent > 20) return 'medium'
  return 'high'
}

// 暴露方法给父组件
defineExpose({
  triggerBackendCountdown,
  clearBackendCountdown
})

onMounted(() => {
  if (props.visible && currentTool.value === 'todo') {
    emit('refresh-todos')
  }
})

onUnmounted(() => {
  if (timerInterval) {
    clearInterval(timerInterval)
  }
})
</script>

<style scoped>
/* 遮罩层 */
.tool-panel-overlay {
  position: fixed;
  inset: 0;
  z-index: 2000;
  background: var(--terran-bg-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
  animation: fadeIn 0.2s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* 面板主体 */
.tool-panel {
  width: 520px;
  max-width: 90vw;
  max-height: 85vh;
  background: var(--terran-bg-secondary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-lg);
  box-shadow: var(--terran-shadow-elevated), 0 0 30px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* 面板头部 */
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  background: var(--terran-statusbar-bg);
  border-bottom: 1px solid var(--terran-border-primary);
}

.header-title {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
}

.header-icon {
  color: var(--terran-primary);
  filter: drop-shadow(var(--terran-glow-primary));
}

.title-text {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-lg);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
  letter-spacing: 1px;
}

.close-btn {
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

.close-btn:hover {
  background: var(--terran-danger);
  color: #fff;
  box-shadow: var(--terran-glow-danger);
}

/* 工具选择器 */
.tool-selector {
  display: flex;
  padding: var(--terran-spacing-sm);
  gap: var(--terran-spacing-xs);
  background: var(--terran-bg-tertiary);
  border-bottom: 1px solid var(--terran-border-primary);
  overflow-x: auto;
}

.tool-tab {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  padding: 8px 16px;
  border: none;
  background: transparent;
  color: var(--terran-text-secondary);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
  white-space: nowrap;
}

.tool-tab:hover {
  color: var(--terran-text-primary);
  background: var(--terran-bg-quaternary);
}

.tool-tab.active {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
  font-weight: var(--terran-font-weight-bold);
}

/* 工具内容区域 */
.tool-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--terran-spacing-md);
  max-height: 55vh;
}

.tool-section {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-md);
}

/* 筛选标签 */
.filter-tabs {
  display: flex;
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-md);
  padding: 2px;
  border: 1px solid var(--terran-border-primary);
  width: fit-content;
}

.filter-tab {
  padding: 4px 12px;
  border: none;
  background: transparent;
  color: var(--terran-text-secondary);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-xs);
  cursor: pointer;
  border-radius: var(--terran-radius-sm);
  transition: all var(--terran-transition-base);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.filter-tab:hover {
  color: var(--terran-text-primary);
}

.filter-tab.active {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
  font-weight: var(--terran-font-weight-bold);
}

/* 待办列表 */
.todo-list {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-sm);
}

.todo-item {
  display: flex;
  align-items: flex-start;
  gap: var(--terran-spacing-sm);
  padding: var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.todo-item:hover {
  border-color: var(--terran-border-secondary);
  background: var(--terran-bg-quaternary);
}

.todo-item.completed {
  opacity: 0.6;
}

.todo-item.completed .todo-text {
  text-decoration: line-through;
  color: var(--terran-text-tertiary);
}

.todo-checkbox {
  width: 20px;
  height: 20px;
  border: 2px solid var(--terran-border-secondary);
  border-radius: var(--terran-radius-sm);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--terran-transition-base);
  flex-shrink: 0;
  margin-top: 2px;
}

.todo-checkbox:hover {
  border-color: var(--terran-primary);
}

.todo-item.completed .todo-checkbox {
  background: var(--terran-primary);
  border-color: var(--terran-primary);
  color: var(--terran-bg-primary);
}

.todo-content {
  flex: 1;
  min-width: 0;
}

.todo-text {
  font-size: var(--terran-font-size-md);
  color: var(--terran-text-primary);
  line-height: var(--terran-line-height-normal);
  word-break: break-word;
}

.todo-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: var(--terran-spacing-xs);
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  font-family: var(--terran-font-mono);
}

.todo-meta svg {
  color: var(--terran-info);
}

.todo-meta .overdue {
  color: var(--terran-danger);
}

.delete-btn {
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--terran-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--terran-radius-sm);
  transition: all var(--terran-transition-base);
  flex-shrink: 0;
  opacity: 0;
}

.todo-item:hover .delete-btn {
  opacity: 1;
}

.delete-btn:hover {
  background: var(--terran-danger);
  color: #fff;
}

/* 空状态 */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--terran-spacing-3xl);
  color: var(--terran-text-tertiary);
  text-align: center;
}

.empty-state svg {
  margin-bottom: var(--terran-spacing-md);
  opacity: 0.5;
}

.empty-state p {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-lg);
  color: var(--terran-text-secondary);
  margin: 0 0 var(--terran-spacing-xs);
}

.empty-state span {
  font-size: var(--terran-font-size-sm);
}

/* 添加待办表单 */
.add-todo-form {
  display: flex;
  gap: var(--terran-spacing-sm);
  align-items: center;
  padding-top: var(--terran-spacing-md);
  border-top: 1px solid var(--terran-border-primary);
}

.todo-input {
  flex: 1;
  padding: 8px 12px;
  background: var(--terran-bg-secondary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-primary);
  font-size: var(--terran-font-size-md);
  outline: none;
  transition: all var(--terran-transition-base);
}

.todo-input:focus {
  border-color: var(--terran-primary);
  box-shadow: var(--terran-glow-primary);
}

.todo-input::placeholder {
  color: var(--terran-text-tertiary);
}

.date-input {
  padding: 6px 10px;
  background: var(--terran-bg-secondary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-primary);
  font-size: var(--terran-font-size-sm);
  font-family: var(--terran-font-mono);
  outline: none;
  cursor: pointer;
  transition: all var(--terran-transition-base);
}

.date-input:focus {
  border-color: var(--terran-primary);
}

.date-input::-webkit-calendar-picker-indicator {
  filter: invert(0.7);
  cursor: pointer;
}

.date-input::-webkit-calendar-picker-indicator:hover {
  filter: invert(1);
}

.add-btn {
  width: 36px;
  height: 36px;
  border: none;
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
  flex-shrink: 0;
}

.add-btn:hover:not(:disabled) {
  background: var(--terran-primary-light);
  box-shadow: var(--terran-glow-primary);
}

.add-btn:disabled {
  background: var(--terran-bg-quaternary);
  color: var(--terran-text-tertiary);
  cursor: not-allowed;
}

/* 番茄钟样式 */
.pomodoro-section {
  align-items: center;
  padding: var(--terran-spacing-lg);
}

.pomodoro-display {
  margin-bottom: var(--terran-spacing-lg);
}

.timer-circle {
  width: 180px;
  height: 180px;
  border-radius: 50%;
  border: 4px solid var(--terran-border-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--terran-bg-tertiary);
  transition: all var(--terran-transition-base);
}

.timer-circle.running {
  border-color: var(--terran-primary);
  box-shadow: 0 0 20px var(--terran-primary-glow);
}

.timer-circle.paused {
  border-color: var(--terran-warning);
  box-shadow: 0 0 20px var(--terran-warning-glow);
}

.timer-time {
  font-family: var(--terran-font-mono);
  font-size: 48px;
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.timer-status {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-secondary);
  margin-top: var(--terran-spacing-xs);
}

.pomodoro-controls {
  display: flex;
  gap: var(--terran-spacing-md);
  margin-bottom: var(--terran-spacing-lg);
}

.control-btn {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  padding: 10px 20px;
  border: none;
  border-radius: var(--terran-radius-md);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-md);
  cursor: pointer;
  transition: all var(--terran-transition-base);
}

.control-btn.primary {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
}

.control-btn.primary:hover {
  background: var(--terran-primary-light);
  box-shadow: var(--terran-glow-primary);
}

.control-btn.warning {
  background: var(--terran-warning);
  color: var(--terran-bg-primary);
}

.control-btn.warning:hover {
  background: var(--terran-warning-light, #ffc53d);
  box-shadow: var(--terran-warning-glow);
}

.control-btn.danger {
  background: var(--terran-danger);
  color: #fff;
}

.control-btn.danger:hover {
  background: var(--terran-danger-light);
  box-shadow: var(--terran-glow-danger);
}

.pomodoro-presets {
  width: 100%;
}

.preset-label {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  margin-bottom: var(--terran-spacing-sm);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.preset-buttons {
  display: flex;
  gap: var(--terran-spacing-sm);
  flex-wrap: wrap;
  justify-content: center;
}

.preset-btn {
  padding: 6px 12px;
  border: 1px solid var(--terran-border-primary);
  background: var(--terran-bg-tertiary);
  color: var(--terran-text-secondary);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.preset-btn:hover {
  border-color: var(--terran-border-secondary);
  color: var(--terran-text-primary);
}

.preset-btn.active {
  background: var(--terran-primary);
  border-color: var(--terran-primary);
  color: var(--terran-bg-primary);
}

.backend-countdown-notice {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-md);
  padding: var(--terran-spacing-md);
  background: var(--terran-info-glow);
  border: 1px solid var(--terran-info);
  border-radius: var(--terran-radius-md);
  margin-top: var(--terran-spacing-md);
}

.notice-icon {
  font-size: 24px;
}

.notice-content {
  flex: 1;
}

.notice-title {
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.notice-text {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-secondary);
}

/* 系统状态样式 */
.system-section {
  align-items: center;
}

.system-loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-md);
  padding: var(--terran-spacing-3xl);
  color: var(--terran-text-secondary);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--terran-border-primary);
  border-top-color: var(--terran-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.system-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--terran-spacing-md);
  width: 100%;
}

.system-card {
  display: flex;
  flex-direction: column;
  padding: var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.system-card:hover {
  border-color: var(--terran-border-secondary);
}

.card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--terran-radius-md);
  margin-bottom: var(--terran-spacing-sm);
}

.card-icon.cpu {
  background: var(--terran-info-glow);
  color: var(--terran-info);
}

.card-icon.memory {
  background: var(--terran-primary-glow);
  color: var(--terran-primary);
}

.card-icon.disk {
  background: var(--terran-warning-glow);
  color: var(--terran-warning);
}

.card-icon.battery {
  background: var(--terran-danger-glow);
  color: var(--terran-danger);
}

.card-icon.battery.charging {
  background: var(--terran-primary-glow);
  color: var(--terran-primary);
}

.card-icon.network {
  background: var(--terran-text-muted);
  color: var(--terran-text-secondary);
}

.card-icon.network.connected {
  background: var(--terran-primary-glow);
  color: var(--terran-primary);
}

.card-content {
  margin-bottom: var(--terran-spacing-sm);
}

.card-label {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 2px;
}

.card-value {
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-xl);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.card-detail {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-tertiary);
  margin-top: 2px;
}

.card-bar {
  height: 4px;
  background: var(--terran-bg-secondary);
  border-radius: 2px;
  overflow: hidden;
  margin-top: auto;
}

.bar-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.bar-fill.low {
  background: var(--terran-primary);
}

.bar-fill.medium {
  background: var(--terran-warning);
}

.bar-fill.high {
  background: var(--terran-danger);
}

.system-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--terran-spacing-3xl);
  color: var(--terran-text-tertiary);
  text-align: center;
}

.system-empty svg {
  margin-bottom: var(--terran-spacing-md);
  opacity: 0.5;
}

.system-empty p {
  font-family: var(--terran-font-display);
  font-size: var(--terran-font-size-lg);
  color: var(--terran-text-secondary);
  margin: 0 0 var(--terran-spacing-md);
}

.retry-btn {
  padding: 8px 16px;
  border: 1px solid var(--terran-primary);
  background: transparent;
  color: var(--terran-primary);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.retry-btn:hover {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
}

.refresh-btn {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  padding: 10px 20px;
  margin-top: var(--terran-spacing-md);
  border: 1px solid var(--terran-border-primary);
  background: var(--terran-bg-tertiary);
  color: var(--terran-text-secondary);
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all var(--terran-transition-base);
}

.refresh-btn:hover:not(:disabled) {
  border-color: var(--terran-primary);
  color: var(--terran-primary);
}

.refresh-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-btn svg.spinning {
  animation: spin 1s linear infinite;
}

/* 滚动条样式 */
.tool-content::-webkit-scrollbar {
  width: 6px;
}

.tool-content::-webkit-scrollbar-track {
  background: var(--terran-bg-tertiary);
}

.tool-content::-webkit-scrollbar-thumb {
  background: var(--terran-border-secondary);
  border-radius: 3px;
}

.tool-content::-webkit-scrollbar-thumb:hover {
  background: var(--terran-primary);
}
</style>
