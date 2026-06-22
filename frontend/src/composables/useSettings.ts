import { ref, onMounted } from 'vue'

// 云端模型提供商类型
export type CloudProvider = 'glm' | 'deepseek' | 'openai' | 'custom'

// 设置数据接口
export interface Settings {
  // Cloud LLM config
  cloudProvider: CloudProvider
  cloudApiKey: string              // 当前提供商的 API Key (读写兼容)
  cloudApiKeys: Record<string, string>  // 每个提供商的 API Key { glm: 'xxx', deepseek: '', ... }
  cloudModel: string
  cloudBaseUrl: string
  // Legacy GLM key (backward compat)
  glmApiKey: string
  // Weather
  qweatherApiKey: string
  qweatherApiHost: string
  // Web search
  qianfanApiKey: string
  // Forum search
  forumSearchApiToken: string
  forumSearchBaseUrl: string
  // Default city
  defaultCity: string
}

// 提供商预设（模型名使用各 API 要求的准确格式）
export const PROVIDER_PRESETS: Record<CloudProvider, { label: string; baseUrl: string; model: string }> = {
  glm:      { label: '智谱 GLM',   baseUrl: 'https://open.bigmodel.cn/api/paas/v4/', model: 'glm-4.7-flash' },
  deepseek: { label: 'DeepSeek',   baseUrl: 'https://api.deepseek.com/v1',           model: 'deepseek-v4-flash' },
  openai:   { label: 'OpenAI',     baseUrl: 'https://api.openai.com/v1',             model: 'gpt-4o-mini' },
  custom:   { label: '自定义',     baseUrl: '',                                       model: '' },
}

// 默认设置
const defaultSettings: Settings = {
  cloudProvider: 'glm',
  cloudApiKey: '',
  cloudApiKeys: {},
  cloudModel: 'glm-4.7-flash',
  cloudBaseUrl: 'https://open.bigmodel.cn/api/paas/v4/',
  glmApiKey: '',
  qweatherApiKey: '',
  qweatherApiHost: '',
  qianfanApiKey: '',
  forumSearchApiToken: '',
  forumSearchBaseUrl: 'https://ssemarket.cn',
  defaultCity: '北京'
}

// 本地存储键名
const SETTINGS_KEY = 'adjutant_settings'

// 响应式设置数据
export const settings = ref<Settings>({ ...defaultSettings })

// 加载设置
export function loadSettings(): Settings {
  try {
    const saved = localStorage.getItem(SETTINGS_KEY)
    if (saved) {
      const parsed = JSON.parse(saved)

      // 迁移：旧版仅有 glmApiKey 时，自动转换为新版 cloud 字段
      if (parsed.glmApiKey && !parsed.cloudApiKey && !parsed.cloudProvider) {
        parsed.cloudApiKey = parsed.glmApiKey
        parsed.cloudProvider = 'glm'
        parsed.cloudModel = 'glm-4.7-flash'
        parsed.cloudBaseUrl = 'https://open.bigmodel.cn/api/paas/v4/'
        if (!parsed.cloudApiKeys) parsed.cloudApiKeys = {}
        parsed.cloudApiKeys['glm'] = parsed.glmApiKey
        console.log('[Settings] 已从旧版 glmApiKey 迁移至新版 cloudApiKey')
      }

      // 确保 cloudApiKeys 存在
      if (!parsed.cloudApiKeys) {
        parsed.cloudApiKeys = {}
        if (parsed.cloudApiKey) {
          parsed.cloudApiKeys[parsed.cloudProvider || 'glm'] = parsed.cloudApiKey
        }
      }

      settings.value = { ...defaultSettings, ...parsed }
    }
  } catch (e) {
    console.error('[Settings] 加载设置失败:', e)
  }
  return settings.value
}

// 保存设置
export function saveSettings(newSettings: Partial<Settings>) {
  settings.value = { ...settings.value, ...newSettings }
  try {
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings.value))
    // 同步到后端
    syncSettingsToBackend()
  } catch (e) {
    console.error('[Settings] 保存设置失败:', e)
  }
}

// 同步设置到后端
export function syncSettingsToBackend() {
  if (window.electronAPI) {
    // 转换为纯对象，避免 Vue 响应式代理导致的结构化克隆错误
    const plainSettings: Settings = {
      cloudProvider: settings.value.cloudProvider,
      cloudApiKey: settings.value.cloudApiKey,
      cloudApiKeys: { ...settings.value.cloudApiKeys },
      cloudModel: settings.value.cloudModel,
      cloudBaseUrl: settings.value.cloudBaseUrl,
      glmApiKey: settings.value.glmApiKey,
      qweatherApiKey: settings.value.qweatherApiKey,
      qweatherApiHost: settings.value.qweatherApiHost,
      qianfanApiKey: settings.value.qianfanApiKey,
      forumSearchApiToken: settings.value.forumSearchApiToken,
      forumSearchBaseUrl: settings.value.forumSearchBaseUrl,
      defaultCity: settings.value.defaultCity
    }
    window.electronAPI.sendToBackend({
      action: 'update_settings',
      settings: plainSettings
    })
  }
}

// 获取单个设置项
export function getSetting<K extends keyof Settings>(key: K): Settings[K] {
  return settings.value[key]
}

// 获取当前提供商的 API Key
export function getCurrentCloudApiKey(): string {
  const keys = settings.value.cloudApiKeys || {}
  return keys[settings.value.cloudProvider] || settings.value.cloudApiKey || ''
}

// 检查设置是否完整
export function checkSettings(): { valid: boolean; missing: string[] } {
  const missing: string[] = []

  if (!getCurrentCloudApiKey()) {
    missing.push('云端模型 API Key')
  }
  if (!settings.value.qweatherApiKey) {
    missing.push('和风天气 API Key')
  }
  if (!settings.value.qweatherApiHost) {
    missing.push('和风天气 API Host')
  }
  if (!settings.value.qianfanApiKey) {
    missing.push('百度千帆 API Key')
  }

  return { valid: missing.length === 0, missing }
}

// 初始化设置
export function useSettings() {
  onMounted(() => {
    loadSettings()
    syncSettingsToBackend()
  })

  return {
    settings,
    saveSettings,
    loadSettings,
    getSetting,
    checkSettings,
    getCurrentCloudApiKey,
    syncSettingsToBackend
  }
}
