import { ref, onMounted } from 'vue'

// 设置数据接口
export interface Settings {
  glmApiKey: string
  qweatherApiKey: string
  qweatherApiHost: string
  qianfanApiKey: string
  forumSearchApiToken: string
  forumSearchBaseUrl: string
  defaultCity: string
}

// 默认设置
const defaultSettings: Settings = {
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

// 检查设置是否完整
export function checkSettings(): { valid: boolean; missing: string[] } {
  const missing: string[] = []

  if (!settings.value.glmApiKey) {
    missing.push('GLM API Key')
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
    syncSettingsToBackend
  }
}
