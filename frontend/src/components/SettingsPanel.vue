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
import { ref, computed, watch } from 'vue'
import { settings, saveSettings as saveSettingsToStorage, type Settings } from '../composables/useSettings'
import { onBackendEvent, sendToBackend } from '../composables/useBackend'
import { notification } from 'ant-design-vue'

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
  defaultCity: '北京'
})

// 测试状态
const testingGlm = ref(false)
const testingQweather = ref(false)

// 从存储加载数据到表单
watch(() => props.visible, (newVisible) => {
  if (newVisible) {
    formData.value = {
      glmApiKey: settings.value.glmApiKey,
      qweatherApiKey: settings.value.qweatherApiKey,
      qweatherApiHost: settings.value.qweatherApiHost,
      defaultCity: settings.value.defaultCity
    }
    testingGlm.value = false
    testingQweather.value = false
  }
})

// 验证表单
const isValid = computed(() => {
  return formData.value.glmApiKey.trim() !== '' &&
         formData.value.qweatherApiKey.trim() !== '' &&
         formData.value.qweatherApiHost.trim() !== ''
})

// GLM Key 是否填写
const glmKeyFilled = computed(() => formData.value.glmApiKey.trim() !== '')

// 和风天气 Key + Host 是否都填写
const qweatherFilled = computed(() =>
  formData.value.qweatherApiKey.trim() !== '' &&
  formData.value.qweatherApiHost.trim() !== ''
)

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

// 监听测试结果
function listenTestResult(type: 'glm' | 'qweather') {
  const unsubscribe = onBackendEvent((event: any) => {
    if (event.event === 'api_key_test_result' && event.type === type) {
      unsubscribe()
      if (type === 'glm') testingGlm.value = false
      else testingQweather.value = false

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
</style>
