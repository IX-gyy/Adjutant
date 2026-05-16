<template>
  <div class="todo-panel-overlay" v-if="visible" @click.self="closePanel">
    <div class="todo-panel">
      <!-- 面板头部 -->
      <div class="panel-header">
        <div class="header-title">
          <svg class="header-icon" viewBox="0 0 24 24" width="18" height="18">
            <path
              fill="currentColor"
              d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"
            />
          </svg>
          <span class="title-text">战术日程表</span>
        </div>
        <div class="header-actions">
          <!-- 筛选切换 -->
          <div class="filter-tabs">
            <button
              class="filter-tab"
              :class="{ active: currentFilter === 'all' }"
              @click="switchFilter('all')"
            >
              全部
            </button>
            <button
              class="filter-tab"
              :class="{ active: currentFilter === 'today' }"
              @click="switchFilter('today')"
            >
              今日
            </button>
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
      </div>

      <!-- 面板内容 -->
      <div class="panel-content">
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
      </div>

      <!-- 添加新待办 -->
      <div class="panel-footer">
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
            :disabled="!canAdd"
            @click="addNewTodo"
          >
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
            </svg>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { listTodos, addTodo, completeTodo, deleteTodo } from '../composables/useBackend'
import type { TodoItem } from '../types'

interface Props {
  visible: boolean
  todos: TodoItem[]
  currentFilter: 'all' | 'today'
}

const props = defineProps<Props>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'update:currentFilter': [value: 'all' | 'today']
  'refresh': []
}>()

// 本地状态
const newTodoContent = ref('')
const newTodoDate = ref('')

// 计算属性
const canAdd = computed(() => newTodoContent.value.trim().length > 0)

const minDateTime = computed(() => {
  const now = new Date()
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset())
  return now.toISOString().slice(0, 16)
})

// 监听面板显示，自动刷新数据
watch(() => props.visible, (isVisible) => {
  if (isVisible) {
    emit('refresh')
  }
})

// 方法
function closePanel() {
  emit('update:visible', false)
}

function switchFilter(filter: 'all' | 'today') {
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
  if (!canAdd.value) return

  const content = newTodoContent.value.trim()
  const dueDate = newTodoDate.value || undefined

  addTodo(content, dueDate)

  // 清空输入
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

onMounted(() => {
  if (props.visible) {
    emit('refresh')
  }
})
</script>

<style scoped>
/* 遮罩层 */
.todo-panel-overlay {
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
.todo-panel {
  width: 480px;
  max-width: 90vw;
  max-height: 80vh;
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

.header-actions {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-md);
}

/* 筛选标签 */
.filter-tabs {
  display: flex;
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-md);
  padding: 2px;
  border: 1px solid var(--terran-border-primary);
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

/* 关闭按钮 */
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

/* 面板内容 */
.panel-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--terran-spacing-md);
  max-height: 50vh;
}

/* 滚动条样式 */
.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: var(--terran-bg-tertiary);
}

.panel-content::-webkit-scrollbar-thumb {
  background: var(--terran-border-secondary);
  border-radius: 3px;
}

.panel-content::-webkit-scrollbar-thumb:hover {
  background: var(--terran-primary);
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

/* 复选框 */
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

/* 待办内容 */
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

/* 删除按钮 */
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

/* 面板底部 */
.panel-footer {
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  border-top: 1px solid var(--terran-border-primary);
  background: var(--terran-bg-tertiary);
}

.add-todo-form {
  display: flex;
  gap: var(--terran-spacing-sm);
  align-items: center;
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

/* 日期选择器样式覆盖 */
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
</style>
