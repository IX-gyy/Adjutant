<template>
  <div class="settings-overlay" v-if="visible" @click.self="closePanel">
    <div class="settings-panel">
      <div class="settings-header">
        <h2 class="settings-title">
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58a.49.49 0 0 0 .12-.61l-1.92-3.32a.488.488 0 0 0-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54a.484.484 0 0 0-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L3.16 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58a.49.49 0 0 0-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
          </svg>
          系统设置
        </h2>
        <button class="close-btn" @click="closePanel">
          <svg viewBox="0 0 24 24" width="20" height="20">
            <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
      </div>

      <div class="settings-content">
        <!-- API Keys Section -->
        <div class="settings-section">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
            </svg>
            API 密钥管理
          </h3>

          <div class="form-group">
            <label class="form-label">
              GLM API Key
              <span class="required">*</span>
            </label>
            <div class="input-row">
              <input
                v-model="formData.glmApiKey"
                type="password"
                class="form-input"
                placeholder="请输入 GLM API Key"
              />
              <button
                class="btn-test"
                :disabled="!glmKeyFilled || testingGlm"
                @click="testGlmKey"
              >
                <svg v-if="testingGlm" class="spinner" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="32" stroke-linecap="round"/>
                </svg>
                <span v-else>测试</span>
              </button>
            </div>
            <span class="form-hint">用于 AI 对话功能</span>
          </div>

          <div class="form-group">
            <label class="form-label">
              和风天气 API Key
              <span class="required">*</span>
            </label>
            <div class="input-row">
              <input
                v-model="formData.qweatherApiKey"
                type="password"
                class="form-input"
                placeholder="请输入和风天气 API Key"
              />
            </div>
            <span class="form-hint">用于天气查询功能</span>
          </div>

          <div class="form-group">
            <label class="form-label">
              和风天气 API Host
              <span class="required">*</span>
            </label>
            <div class="input-row">
              <input
                v-model="formData.qweatherApiHost"
                type="text"
                class="form-input"
                placeholder="例如：devapi.qweather.com"
              />
              <button
                class="btn-test"
                :disabled="!qweatherFilled || testingQweather"
                @click="testQweatherKey"
              >
                <svg v-if="testingQweather" class="spinner" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="32" stroke-linecap="round"/>
                </svg>
                <span v-else>测试</span>
              </button>
            </div>
            <span class="form-hint">开发版使用 devapi.qweather.com，商业版使用 api.qweather.com</span>
          </div>

          <div class="form-group">
            <label class="form-label">
              百度千帆 API Key
              <span class="required">*</span>
            </label>
            <div class="input-row">
              <input
                v-model="formData.qianfanApiKey"
                type="password"
                class="form-input"
                placeholder="请输入百度千帆 API Key"
              />
              <button
                class="btn-test"
                :disabled="!qianfanKeyFilled || testingQianfan"
                @click="testQianfanKey"
              >
                <svg v-if="testingQianfan" class="spinner" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="32" stroke-linecap="round"/>
                </svg>
                <span v-else>测试</span>
              </button>
            </div>
            <span class="form-hint">用于网络信息搜索功能，每日100次免费额度</span>
          </div>
        </div>

        <!-- 集市帖子搜索（小秋）Section -->
        <div class="settings-section">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
            </svg>
            集市帖子搜索（小秋）
          </h3>

          <div class="form-group">
            <label class="form-label">API Token</label>
            <div class="input-row">
              <input
                v-model="formData.forumSearchApiToken"
                type="password"
                class="form-input"
                placeholder="请输入小秋 API Token"
              />
              <button
                class="btn-test"
                :disabled="!forumSearchTokenFilled || testingForumSearch"
                @click="testForumSearchKey"
              >
                <svg v-if="testingForumSearch" class="spinner" viewBox="0 0 24 24" width="14" height="14">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" stroke-width="3" stroke-dasharray="32" stroke-linecap="round"/>
                </svg>
                <span v-else>测试</span>
              </button>
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">API 地址</label>
            <input
              v-model="formData.forumSearchBaseUrl"
              type="text"
              class="form-input"
              placeholder="https://ssemarket.cn"
            />
          </div>
          <span class="form-hint">用于查询集市/论坛的帖子内容。需要从管理员获取 API Token，也可使用本地小秋 Docker 服务（http://127.0.0.1:18080）</span>
        </div>

        <!-- Default City Section -->
        <div class="settings-section">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
            </svg>
            默认城市
          </h3>

          <div class="form-group">
            <label class="form-label">默认城市</label>
            <input
              v-model="formData.defaultCity"
              type="text"
              class="form-input"
              placeholder="请输入默认城市"
            />
            <span class="form-hint">AI 天气查询和天气面板将默认使用此城市</span>
          </div>
        </div>

        <!-- 长期记忆管理区域 -->
        <div class="settings-section">
          <h3 class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M13 3a9 9 0 0 0-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42A8.954 8.954 0 0 0 13 21a9 9 0 0 0 0-18zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z"/>
            </svg>
            长期记忆管理
          </h3>

          <div class="memory-stats">
            <div class="stat-item">
              <span class="stat-label">已存储记忆</span>
              <span class="stat-value">{{ memoryCount }} 条</span>
            </div>
            <button class="btn-load" @click="loadMemories" :disabled="loadingMemories">
              {{ loadingMemories ? '加载中...' : (memoriesLoaded ? '刷新记忆列表' : '查看所有记忆') }}
            </button>
          </div>

          <!-- 记忆列表 -->
          <div v-if="memoriesLoaded && memories.length > 0" class="memory-list">
            <div
              v-for="mem in memories"
              :key="mem.id"
              class="memory-item"
            >
              <div class="memory-type-badge">{{ getMemoryTypeLabel(mem.type || 'fact') }}</div>
              <div class="memory-content">{{ mem.content }}</div>
              <div class="memory-meta">
                <span class="memory-importance" :title="`重要性: ${mem.importance}/10`">
                  {{ '★'.repeat(Math.round((mem.importance || 5) / 2)) }}{{ '☆'.repeat(5 - Math.round((mem.importance || 5) / 2)) }}
                </span>
                <span class="memory-date">{{ formatMemoryDate(mem.timestamp) }}</span>
              </div>
              <button class="memory-delete-btn" @click="deleteSingleMemory(mem.id)" title="删除此记忆">
                <svg viewBox="0 0 24 24" width="10" height="10">
                  <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                </svg>
              </button>
            </div>
          </div>

          <div v-else-if="memoriesLoaded && memories.length === 0" class="memory-empty">
            <span>暂无长期记忆</span>
            <span class="hint">AI 会在对话过程中自动提取有价值的信息</span>
          </div>

          <!-- 危险操作区 -->
          <div class="danger-zone" v-if="memoryCount > 0">
            <div class="danger-zone-label">危险操作</div>
            <button class="btn-danger" @click="handleClearAllMemories">
              <svg viewBox="0 0 24 24" width="14" height="14">
                <path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
              删除所有长期记忆
            </button>
          </div>
        </div>
      </div>

      <div class="settings-footer">
        <button class="btn btn-secondary" @click="closePanel">取消</button>
        <button class="btn btn-primary" @click="saveSettings" :disabled="!isValid">
          <svg viewBox="0 0 24 24" width="14" height="14">
            <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
          </svg>
          保存设置
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from 'vue'
import { settings, saveSettings as saveSettingsToStorage, type Settings } from '../composables/useSettings'
import { onBackendEvent, sendToBackend } from '../composables/useBackend'
import { notification, Modal } from 'ant-design-vue'
import { ExclamationCircleOutlined } from '@ant-design/icons-vue'
import type { MemoryItem } from '../types'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

// 表单数据
const formData = ref<Settings>({
  glmApiKey: '',
  qweatherApiKey: '',
  qweatherApiHost: '',
  qianfanApiKey: '',
  forumSearchApiToken: '',
  forumSearchBaseUrl: 'https://ssemarket.cn',
  defaultCity: '北京'
})

// 测试状态
const testingGlm = ref(false)
const testingQweather = ref(false)
const testingQianfan = ref(false)
const testingForumSearch = ref(false)

// 从存储加载数据到表单
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    formData.value = {
      glmApiKey: settings.value.glmApiKey,
      qweatherApiKey: settings.value.qweatherApiKey,
      qweatherApiHost: settings.value.qweatherApiHost,
      qianfanApiKey: settings.value.qianfanApiKey,
      forumSearchApiToken: settings.value.forumSearchApiToken,
      forumSearchBaseUrl: settings.value.forumSearchBaseUrl,
      defaultCity: settings.value.defaultCity
    }
    testingGlm.value = false
    testingQweather.value = false
    testingQianfan.value = false
    testingForumSearch.value = false
  }
})

// 验证表单
const isValid = computed(() => {
  return formData.value.glmApiKey.trim() !== '' &&
         formData.value.qweatherApiKey.trim() !== '' &&
         formData.value.qweatherApiHost.trim() !== '' &&
         formData.value.qianfanApiKey.trim() !== ''
})

// GLM Key 是否填写
const glmKeyFilled = computed(() => formData.value.glmApiKey.trim() !== '')

// 和风天气 Key + Host 是否都填写
const qweatherFilled = computed(() =>
  formData.value.qweatherApiKey.trim() !== '' &&
  formData.value.qweatherApiHost.trim() !== ''
)

// 百度千帆 Key 是否填写
const qianfanKeyFilled = computed(() => formData.value.qianfanApiKey.trim() !== '')

// 集市搜索（小秋）Token 是否填写（可选功能，不加入 isValid 校验）
const forumSearchTokenFilled = computed(() => formData.value.forumSearchApiToken.trim() !== '')

// ========== 长期记忆管理状态 ==========
const memories = ref<MemoryItem[]>([])
const memoryCount = ref(0)
const memoriesLoaded = ref(false)
const loadingMemories = ref(false)

function loadMemories() {
  loadingMemories.value = true
  sendToBackend({ action: 'get_memories' })

  const unsubscribe = onBackendEvent((event: any) => {
    if (event.event === 'memories_list') {
      unsubscribe()
      loadingMemories.value = false
      memoriesLoaded.value = true
      if (Array.isArray(event.memories)) {
        const list = event.memories as any[]
        if (list.length > 0 && typeof list[0] === 'object') {
          memories.value = list as MemoryItem[]
        } else {
          memories.value = list.map((content: string, idx: number) => ({
            id: `legacy_${idx}`,
            content,
            timestamp: 0,
            importance: 5,
            type: 'fact'
          }))
        }
      }
      memoryCount.value = event.total || memories.value.length
    }
  })

  setTimeout(() => {
    if (loadingMemories.value) {
      loadingMemories.value = false
      notification.error({ message: '加载超时', description: '无法获取记忆列表' })
    }
  }, 10000)
}

function deleteSingleMemory(memId: string) {
  Modal.confirm({
    title: '确认删除此记忆？',
    icon: h(ExclamationCircleOutlined),
    content: '此操作不可撤销。',
    okText: '删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      sendToBackend({ action: 'delete_memory', mem_id: memId })
      memories.value = memories.value.filter(m => m.id !== memId)
      memoryCount.value = Math.max(0, memoryCount.value - 1)
    }
  })
}

function handleClearAllMemories() {
  Modal.confirm({
    title: '确认删除所有长期记忆？',
    icon: h(ExclamationCircleOutlined),
    content: '此操作将永久删除 AI 对您的所有记忆（包括偏好、习惯、计划等），且不可恢复。当前对话不受影响。',
    okText: '全部删除',
    okType: 'danger',
    cancelText: '取消',
    onOk() {
      sendToBackend({ action: 'clear_all_memories' })
      const unsubscribe = onBackendEvent((event: any) => {
        if (event.event === 'memories_cleared') {
          unsubscribe()
          memories.value = []
          memoryCount.value = 0
          memoriesLoaded.value = true
          notification.success({
            message: '记忆已清空',
            description: `已删除 ${event.count} 条长期记忆`,
            duration: 3
          })
        }
      })
    }
  })
}

function getMemoryTypeLabel(type: string): string {
  const labels: Record<string, string> = {
    attribute: '属性',
    preference: '偏好',
    habit: '习惯',
    plan: '计划',
    event: '事件',
    opinion: '观点',
    fact: '信息'
  }
  return labels[type] || '信息'
}

function formatMemoryDate(timestamp: number): string {
  if (!timestamp) return ''
  const d = new Date(timestamp * 1000)
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// 打开设置面板时自动获取记忆数量
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    const unsub = onBackendEvent((event: any) => {
      if (event.event === 'memories_list') {
        unsub()
        memoryCount.value = event.total || 0
      }
    })
    sendToBackend({ action: 'get_memories' })
  }
})

// 关闭面板
function closePanel() {
  emit('update:visible', false)
}

// 保存设置
function saveSettings() {
  saveSettingsToStorage(formData.value)
  notification.success({
    message: '设置已保存',
    description: 'API Key 和默认城市已更新，正在同步到后端。',
    duration: 3
  })
  closePanel()
}

// 测试 GLM API Key
function testGlmKey() {
  if (!glmKeyFilled.value) return
  testingGlm.value = true
  sendToBackend({
    action: 'test_glm_key',
    api_key: formData.value.glmApiKey
  })
  listenTestResult('glm')
}

// 测试和风天气 API Key
function testQweatherKey() {
  if (!qweatherFilled.value) return
  testingQweather.value = true
  sendToBackend({
    action: 'test_qweather_key',
    api_key: formData.value.qweatherApiKey,
    api_host: formData.value.qweatherApiHost
  })
  listenTestResult('qweather')
}

// 测试百度千帆 API Key
function testQianfanKey() {
  if (!qianfanKeyFilled.value) return
  testingQianfan.value = true
  sendToBackend({
    action: 'test_qianfan_key',
    api_key: formData.value.qianfanApiKey
  })
  listenTestResult('qianfan')
}

// 测试集市搜索（小秋）API
function testForumSearchKey() {
  if (!forumSearchTokenFilled.value) return
  testingForumSearch.value = true
  sendToBackend({
    action: 'test_forum_search_key',
    api_token: formData.value.forumSearchApiToken,
    base_url: formData.value.forumSearchBaseUrl
  })
  listenTestResult('forum_search')
}

// 监听测试结果
function listenTestResult(type: 'glm' | 'qweather' | 'qianfan' | 'forum_search') {
  const unsubscribe = onBackendEvent((event: any) => {
    if (event.event === 'api_key_test_result' && event.type === type) {
      unsubscribe()
      if (type === 'glm') testingGlm.value = false
      else if (type === 'qweather') testingQweather.value = false
      else if (type === 'qianfan') testingQianfan.value = false
      else testingForumSearch.value = false

      if (event.success) {
        notification.success({
          message: '测试通过',
          description: event.message || 'API Key 有效',
          duration: 3
        })
      } else {
        notification.error({
          message: '测试失败',
          description: event.message || 'API Key 无效，请检查',
          duration: 5
        })
      }
    }
  })
  // 超时处理
  setTimeout(() => {
    if (type === 'glm' && testingGlm.value) {
      testingGlm.value = false
      notification.error({ message: '测试超时', description: '后端无响应', duration: 3 })
    } else if (type === 'qweather' && testingQweather.value) {
      testingQweather.value = false
      notification.error({ message: '测试超时', description: '后端无响应', duration: 3 })
    } else if (type === 'qianfan' && testingQianfan.value) {
      testingQianfan.value = false
      notification.error({ message: '测试超时', description: '后端无响应', duration: 3 })
    }
  }, 15000)
}
</script>

<style scoped>
.settings-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.7);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  backdrop-filter: blur(4px);
}

.settings-panel {
  width: 500px;
  max-width: 90vw;
  max-height: 80vh;
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-lg);
  border: 1px solid var(--terran-border-primary);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.settings-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  background: var(--terran-bg-tertiary);
  border-bottom: 1px solid var(--terran-border-primary);
}

.settings-title {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  margin: 0;
  font-size: var(--terran-font-size-lg);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.settings-title svg {
  color: var(--terran-primary);
}

.close-btn {
  background: transparent;
  border: none;
  color: var(--terran-text-secondary);
  cursor: pointer;
  padding: var(--terran-spacing-xs);
  border-radius: var(--terran-radius-sm);
  transition: all 0.2s ease;
}

.close-btn:hover {
  color: var(--terran-text-primary);
  background: var(--terran-bg-hover);
}

.settings-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--terran-spacing-lg);
}

.settings-section {
  margin-bottom: var(--terran-spacing-xl);
}

.settings-section:last-child {
  margin-bottom: 0;
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  margin: 0 0 var(--terran-spacing-md) 0;
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-semibold);
  color: var(--terran-primary);
  padding-bottom: var(--terran-spacing-sm);
  border-bottom: 1px solid var(--terran-border-primary);
}

.form-group {
  margin-bottom: var(--terran-spacing-md);
}

.input-row {
  display: flex;
  gap: var(--terran-spacing-sm);
}

.input-row .form-input {
  flex: 1;
}

.btn-test {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  min-width: 56px;
  height: 36px;
  padding: 0 var(--terran-spacing-sm);
  background: var(--terran-bg-tertiary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-secondary);
  font-size: var(--terran-font-size-xs);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-test:hover:not(:disabled) {
  border-color: var(--terran-primary);
  color: var(--terran-primary);
  background: rgba(var(--terran-primary-rgb), 0.1);
}

.btn-test:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.spinner {
  animation: spin 1s linear infinite;
}

.form-label {
  display: block;
  margin-bottom: var(--terran-spacing-xs);
  font-size: var(--terran-font-size-sm);
  font-weight: var(--terran-font-weight-medium);
  color: var(--terran-text-primary);
}

.required {
  color: var(--terran-error);
  margin-left: 2px;
}

.form-input {
  width: 100%;
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-primary);
  font-size: var(--terran-font-size-sm);
  transition: all 0.2s ease;
}

.form-input:focus {
  outline: none;
  border-color: var(--terran-primary);
  box-shadow: 0 0 0 2px rgba(var(--terran-primary-rgb), 0.2);
}

.form-input::placeholder {
  color: var(--terran-text-muted);
}

.form-hint {
  display: block;
  margin-top: var(--terran-spacing-xs);
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
}

.settings-footer {
  display: flex;
  justify-content: flex-end;
  gap: var(--terran-spacing-md);
  padding: var(--terran-spacing-md) var(--terran-spacing-lg);
  background: var(--terran-bg-tertiary);
  border-top: 1px solid var(--terran-border-primary);
}

.btn {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  border: none;
  border-radius: var(--terran-radius-md);
  font-size: var(--terran-font-size-sm);
  font-weight: var(--terran-font-weight-medium);
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--terran-primary);
  color: var(--terran-bg-primary);
}

.btn-primary:hover:not(:disabled) {
  background: var(--terran-primary-hover);
}

.btn-secondary {
  background: var(--terran-bg-tertiary);
  color: var(--terran-text-secondary);
  border: 1px solid var(--terran-border-primary);
}

.btn-secondary:hover {
  background: var(--terran-bg-hover);
  color: var(--terran-text-primary);
}

/* ==================== 长期记忆管理样式 ==================== */

.memory-stats {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-md);
  margin-bottom: var(--terran-spacing-md);
}

.stat-item {
  display: flex;
  gap: var(--terran-spacing-sm);
  align-items: center;
}

.stat-label {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-secondary);
}

.stat-value {
  font-family: var(--terran-font-mono);
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-primary);
}

.btn-load {
  padding: 4px 12px;
  border: 1px solid var(--terran-border-primary);
  background: var(--terran-bg-secondary);
  color: var(--terran-text-secondary);
  font-size: var(--terran-font-size-xs);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all 0.2s ease;
}

.btn-load:hover:not(:disabled) {
  border-color: var(--terran-primary);
  color: var(--terran-primary);
}

.btn-load:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* 记忆列表 */
.memory-list {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-sm);
  max-height: 260px;
  overflow-y: auto;
  margin-bottom: var(--terran-spacing-md);
}

.memory-item {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  gap: var(--terran-spacing-xs);
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  border-radius: var(--terran-radius-md);
  border-left: 3px solid var(--terran-border-primary);
  background: var(--terran-bg-tertiary);
  transition: all 0.2s ease;
  position: relative;
}

.memory-item:hover {
  background: var(--terran-bg-quaternary);
}

.memory-type-badge {
  padding: 1px 6px;
  border-radius: var(--terran-radius-sm);
  font-size: 10px;
  font-weight: var(--terran-font-weight-bold);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  background: var(--terran-bg-secondary);
  color: var(--terran-text-secondary);
  flex-shrink: 0;
}

.memory-content {
  flex: 1;
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-primary);
  line-height: 1.4;
  min-width: 0;
  word-break: break-word;
}

.memory-meta {
  display: flex;
  gap: var(--terran-spacing-md);
  align-items: center;
  width: 100%;
  margin-top: 2px;
}

.memory-importance {
  font-size: 10px;
  color: #d4a017;
  letter-spacing: 1px;
}

.memory-date {
  font-size: 10px;
  color: var(--terran-text-tertiary);
  font-family: var(--terran-font-mono);
}

.memory-delete-btn {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  border: none;
  background: transparent;
  color: var(--terran-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--terran-radius-sm);
  opacity: 0;
  transition: all 0.2s ease;
}

.memory-item:hover .memory-delete-btn {
  opacity: 1;
}

.memory-delete-btn:hover {
  background: #ff4d4f;
  color: #fff;
}

.memory-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--terran-spacing-lg);
  color: var(--terran-text-tertiary);
  font-size: var(--terran-font-size-sm);
}

.memory-empty .hint {
  font-size: var(--terran-font-size-xs);
  margin-top: var(--terran-spacing-xs);
}

/* 危险操作区 */
.danger-zone {
  padding: var(--terran-spacing-md);
  border: 1px solid #ff4d4f;
  border-radius: var(--terran-radius-md);
  background: rgba(255, 77, 79, 0.05);
}

.danger-zone-label {
  font-size: var(--terran-font-size-xs);
  color: #ff4d4f;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: var(--terran-spacing-sm);
}

.btn-danger {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  border: 1px solid #ff4d4f;
  background: transparent;
  color: #ff4d4f;
  font-size: var(--terran-font-size-sm);
  cursor: pointer;
  border-radius: var(--terran-radius-md);
  transition: all 0.2s ease;
  width: 100%;
  justify-content: center;
}

.btn-danger:hover {
  background: #ff4d4f;
  color: #fff;
}
</style>
