<template>
  <div class="weather-panel" v-if="visible">
    <div class="weather-header">
      <div class="location-search">
        <input
          v-model="searchLocation"
          type="text"
          class="location-input"
          placeholder="输入城市名称..."
          @keydown.enter="searchWeather"
        />
        <button class="search-btn" @click="searchWeather" :disabled="loading">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
          </svg>
        </button>
      </div>
      <div class="location-display" v-if="currentLocation">
        <svg viewBox="0 0 24 24" width="14" height="14">
          <path fill="currentColor" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        <span>{{ currentLocation }}</span>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="weather-loading">
      <div class="loading-spinner"></div>
      <span>正在连接气象卫星...</span>
    </div>

    <!-- 错误状态 -->
    <div v-else-if="error" class="weather-error">
      <svg viewBox="0 0 24 24" width="48" height="48">
        <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
      </svg>
      <p>{{ error }}</p>
      <button class="retry-btn" @click="refreshWeather">重试</button>
    </div>

    <!-- 天气内容 - 可滚动区域 -->
    <div v-else-if="weatherData" class="weather-content" ref="weatherContent">
      <!-- 第一页：当前天气 + 逐小时预报 -->
      <div class="weather-page page-current">
        <!-- 当前天气大卡片 -->
        <div class="current-weather-card">
          <div class="current-main">
            <i :class="['weather-icon-large', getWeatherIconClass(weatherData.now?.icon)]"></i>
            <div class="current-temp">{{ weatherData.now?.temp }}°</div>
            <div class="current-text">{{ weatherData.now?.text }}</div>
          </div>
          <div class="current-details">
            <div class="detail-item">
              <span class="detail-label">体感</span>
              <span class="detail-value">{{ weatherData.now?.feelsLike }}°</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">湿度</span>
              <span class="detail-value">{{ weatherData.now?.humidity }}%</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">风向</span>
              <span class="detail-value">{{ weatherData.now?.windDir }}</span>
            </div>
            <div class="detail-item">
              <span class="detail-label">风力</span>
              <span class="detail-value">{{ weatherData.now?.windScale }}级</span>
            </div>
          </div>
        </div>

        <!-- 今日逐小时预报 -->
        <div class="hourly-section" v-if="hourlyData.length > 0">
          <div class="section-title">
            <svg viewBox="0 0 24 24" width="16" height="16">
              <path fill="currentColor" d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
            </svg>
            <span>今日逐小时预报</span>
          </div>
          <div class="hourly-scroll">
            <div
              v-for="hour in hourlyData.slice(0, 24)"
              :key="hour.fxTime"
              class="hourly-item"
            >
              <div class="hourly-time">{{ formatHourTime(hour.fxTime) }}</div>
              <i :class="['weather-icon', getWeatherIconClass(hour.icon)]"></i>
              <div class="hourly-temp">{{ hour.temp }}°</div>
              <div class="hourly-text">{{ hour.text }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 第二页：多日趋势预报 -->
      <div class="weather-page page-forecast">
        <div class="section-title">
          <svg viewBox="0 0 24 24" width="16" height="16">
            <path fill="currentColor" d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-1.99.9-1.99 2L3 19c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM9 10H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm-8 4H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z"/>
          </svg>
          <span>未来7日趋势预报</span>
        </div>
        <div class="daily-forecast" v-if="dailyData.length > 0">
          <div
            v-for="day in dailyData"
            :key="day.fxDate"
            class="daily-item"
          >
            <div class="daily-date">{{ formatDailyDate(day.fxDate) }}</div>
            <div class="daily-day">{{ getWeekDay(day.fxDate) }}</div>
            <div class="daily-icons">
              <div class="day-icon">
                <i :class="['weather-icon', getWeatherIconClass(day.iconDay)]"></i>
                <span>白天</span>
              </div>
              <div class="night-icon">
                <i :class="['weather-icon', getWeatherIconClass(day.iconNight)]"></i>
                <span>夜间</span>
              </div>
            </div>
            <div class="daily-temps">
              <div class="temp-high">{{ day.tempMax }}°</div>
              <div class="temp-bar">
                <div class="temp-bar-fill" :style="getTempBarStyle(day)"></div>
              </div>
              <div class="temp-low">{{ day.tempMin }}°</div>
            </div>
            <div class="daily-text">
              <span>{{ day.textDay }}</span>
              <span class="text-separator">|</span>
              <span>{{ day.textNight }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 第三页：杂项信息 -->
      <div class="weather-page page-extras">
        <!-- 空气质量 -->
        <div class="extra-card air-quality" v-if="airData">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
            </svg>
            <span>空气质量</span>
          </div>
          <div class="air-main">
            <div class="aqi-value" :class="getAqiClass(airData.aqi)">{{ airData.aqi }}</div>
            <div class="aqi-level">{{ airData.category }}</div>
          </div>
          <div class="air-details">
            <div class="air-item">
              <span class="air-label">PM2.5</span>
              <span class="air-value">{{ airData.pm2p5 }}μg/m³</span>
            </div>
            <div class="air-item">
              <span class="air-label">PM10</span>
              <span class="air-value">{{ airData.pm10 }}μg/m³</span>
            </div>
          </div>
        </div>

        <!-- 灾害预警 -->
        <div class="extra-card warnings" v-if="warnings.length > 0">
          <div class="card-header warning">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="currentColor" d="M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z"/>
            </svg>
            <span>灾害预警</span>
          </div>
          <div class="warning-list">
            <div
              v-for="(warning, index) in warnings"
              :key="index"
              class="warning-item"
              :class="getWarningClass(warning.level)"
            >
              <div class="warning-title">{{ warning.title }}</div>
              <div class="warning-text">{{ warning.text }}</div>
            </div>
          </div>
        </div>
        <div class="extra-card warnings empty" v-else>
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
            </svg>
            <span>灾害预警</span>
          </div>
          <div class="empty-text">当前无灾害预警</div>
        </div>

        <!-- 天文信息 -->
        <div class="extra-card astronomy" v-if="astronomyData">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="currentColor" d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7zm2.85 11.1l-.85.6V16h-4v-2.3l-.85-.6A4.997 4.997 0 0 1 7 9c0-2.76 2.24-5 5-5s5 2.24 5 5c0 1.63-.8 3.16-2.15 4.1z"/>
            </svg>
            <span>天文信息</span>
          </div>
          <div class="astro-grid">
            <div class="astro-item">
              <span class="astro-label">日出</span>
              <span class="astro-value">{{ astronomyData.sunrise }}</span>
            </div>
            <div class="astro-item">
              <span class="astro-label">日落</span>
              <span class="astro-value">{{ astronomyData.sunset }}</span>
            </div>
            <div class="astro-item">
              <span class="astro-label">月升</span>
              <span class="astro-value">{{ astronomyData.moonrise }}</span>
            </div>
            <div class="astro-item">
              <span class="astro-label">月落</span>
              <span class="astro-value">{{ astronomyData.moonset }}</span>
            </div>
            <div class="astro-item full">
              <span class="astro-label">月相</span>
              <span class="astro-value">{{ astronomyData.moonPhase }}</span>
            </div>
          </div>
        </div>

        <!-- 生活指数 -->
        <div class="extra-card indices" v-if="indicesData.length > 0">
          <div class="card-header">
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>
            <span>生活决策辅助</span>
          </div>
          <div class="indices-grid">
            <div
              v-for="index in indicesData.slice(0, 6)"
              :key="index.type"
              class="index-item"
            >
              <div class="index-name">{{ index.name }}</div>
              <div class="index-level" :class="getIndexLevelClass(index.level)">{{ index.level }}</div>
              <div class="index-category">{{ index.category }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 刷新按钮 -->
      <button class="refresh-weather-btn" @click="refreshWeather" :disabled="loading">
        <svg viewBox="0 0 24 24" width="16" height="16" :class="{ spinning: loading }">
          <path fill="currentColor" d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z"/>
        </svg>
        <span>刷新数据</span>
      </button>
    </div>

    <!-- 空状态 -->
    <div v-else class="weather-empty">
      <svg viewBox="0 0 24 24" width="64" height="64">
        <path fill="currentColor" d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM19 18H6c-2.21 0-4-1.79-4-4 0-2.05 1.53-3.76 3.56-3.97l1.07-.11.5-.95C8.08 7.14 9.94 6 12 6c2.62 0 4.96 1.88 5.46 4.38l.27 1.36 1.38.12c1.63.14 2.89 1.51 2.89 3.14 0 1.76-1.43 3.2-3.2 3.2z"/>
      </svg>
      <p>暂无天气数据</p>
      <span>请输入城市名称查询天气</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { onBackendEvent, sendToBackend } from '../composables/useBackend'
import { settings, saveSettings } from '../composables/useSettings'

interface Props {
  visible: boolean
}

const props = defineProps<Props>()

// 状态
const loading = ref(false)
const error = ref('')
const searchLocation = ref('')
const currentLocation = ref(settings.value.defaultCity)

// 天气数据
const weatherData = ref<any>(null)
const hourlyData = ref<any[]>([])
const dailyData = ref<any[]>([])
const airData = ref<any>(null)
const warnings = ref<any[]>([])
const astronomyData = ref<any>(null)
const indicesData = ref<any[]>([])

// 监听可见性变化，自动查询
watch(() => props.visible, (newVisible) => {
  if (newVisible && !weatherData.value && !loading.value) {
    searchWeather()
  }
})

onMounted(() => {
  if (props.visible) {
    searchWeather()
  }
})

// 查询天气
function searchWeather() {
  loading.value = true
  error.value = ''

  const location = searchLocation.value.trim() || ''

  // 发送查询请求
  sendToBackend({
    action: 'query_weather',
    location: location,
    sub_ops: ['now', 'hour', 'week', 'air', 'warning', 'astronomy', 'indices']
  })

  // 设置超时
  const timeout = setTimeout(() => {
    loading.value = false
    error.value = '查询超时，请稍后重试'
  }, 10000)

  // 监听响应
  const unsubscribe = onBackendEvent((event: any) => {
    if (event.event === 'weather_result') {
      clearTimeout(timeout)
      unsubscribe()
      loading.value = false

      if (event.error) {
        error.value = event.error
        return
      }

      const data = event.data
      const newLocation = data.location || location || settings.value.defaultCity
      currentLocation.value = newLocation

      // 保存城市设置到本地存储
      if (newLocation !== settings.value.defaultCity) {
        saveSettings({ defaultCity: newLocation })
      }

      // 解析各个子操作的结果
      if (data.results) {
        data.results.forEach((result: any) => {
          switch (result.sub_op) {
            case 'now':
              weatherData.value = { now: result.data }
              break
            case 'hour':
              hourlyData.value = result.data?.hourly || []
              break
            case 'week':
              dailyData.value = result.data?.daily || []
              break
            case 'air':
              airData.value = result.data?.now || null
              break
            case 'warning':
              warnings.value = result.data?.warning || []
              break
            case 'astronomy':
              astronomyData.value = result.data || null
              break
            case 'indices':
              indicesData.value = result.data?.daily || []
              break
          }
        })
      }
    }
  })
}

// 刷新天气
function refreshWeather() {
  searchWeather()
}

// 获取天气图标类名
function getWeatherIconClass(iconCode: string | number | undefined): string {
  if (!iconCode) return 'qi-999'
  return `qi-${iconCode}`
}

// 格式化小时时间
function formatHourTime(fxTime: string): string {
  if (!fxTime) return '--:--'
  const date = new Date(fxTime)
  return `${date.getHours().toString().padStart(2, '0')}:00`
}

// 格式化日期
function formatDailyDate(fxDate: string): string {
  if (!fxDate) return ''
  const date = new Date(fxDate)
  return `${date.getMonth() + 1}/${date.getDate()}`
}

// 获取星期几
function getWeekDay(fxDate: string): string {
  if (!fxDate) return ''
  const date = new Date(fxDate)
  const days = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']
  const today = new Date()
  const tomorrow = new Date(today)
  tomorrow.setDate(tomorrow.getDate() + 1)

  if (date.toDateString() === today.toDateString()) return '今天'
  if (date.toDateString() === tomorrow.toDateString()) return '明天'
  return days[date.getDay()]
}

// 获取温度条样式
function getTempBarStyle(day: any): any {
  const min = parseInt(day.tempMin) || 0
  const max = parseInt(day.tempMax) || 0
  const range = max - min
  const maxRange = 20 // 假设最大温差20度
  const width = Math.min((range / maxRange) * 100, 100)
  return { width: `${width}%` }
}

// 获取AQI等级类名
function getAqiClass(aqi: string | number): string {
  const val = parseInt(aqi as string) || 0
  if (val <= 50) return 'excellent'
  if (val <= 100) return 'good'
  if (val <= 150) return 'light'
  if (val <= 200) return 'moderate'
  if (val <= 300) return 'heavy'
  return 'severe'
}

// 获取预警等级类名
function getWarningClass(level: string): string {
  if (!level) return ''
  if (level.includes('红')) return 'red'
  if (level.includes('橙')) return 'orange'
  if (level.includes('黄')) return 'yellow'
  if (level.includes('蓝')) return 'blue'
  return ''
}

// 获取指数等级类名
function getIndexLevelClass(level: string): string {
  if (!level) return ''
  if (level.includes('舒适') || level.includes('适宜') || level.includes('好')) return 'good'
  if (level.includes('不宜') || level.includes('差')) return 'bad'
  return 'normal'
}
</script>

<style scoped>
@import 'qweather-icons/font/qweather-icons.css';

.weather-panel {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-lg);
  overflow: hidden;
}

.weather-header {
  padding: var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border-bottom: 1px solid var(--terran-border-primary);
}

.location-search {
  display: flex;
  gap: var(--terran-spacing-sm);
  margin-bottom: var(--terran-spacing-sm);
}

.location-input {
  flex: 1;
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  background: var(--terran-bg-primary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-primary);
  font-size: var(--terran-font-size-md);
  outline: none;
  transition: all var(--terran-transition-fast);
}

.location-input:focus {
  border-color: var(--terran-primary);
  box-shadow: 0 0 0 2px var(--terran-primary-glow);
}

.search-btn {
  padding: var(--terran-spacing-sm) var(--terran-spacing-md);
  background: var(--terran-primary);
  border: none;
  border-radius: var(--terran-radius-md);
  color: var(--terran-bg-primary);
  cursor: pointer;
  transition: all var(--terran-transition-fast);
  display: flex;
  align-items: center;
  justify-content: center;
}

.search-btn:hover:not(:disabled) {
  background: var(--terran-primary-light);
  box-shadow: 0 0 8px var(--terran-primary-glow);
}

.search-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.location-display {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  color: var(--terran-primary);
  font-size: var(--terran-font-size-sm);
}

.weather-loading,
.weather-error,
.weather-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--terran-spacing-md);
  color: var(--terran-text-secondary);
  padding: var(--terran-spacing-xl);
}

.loading-spinner {
  width: 40px;
  height: 40px;
  border: 3px solid var(--terran-border-primary);
  border-top-color: var(--terran-primary);
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

.retry-btn {
  padding: var(--terran-spacing-sm) var(--terran-spacing-lg);
  background: var(--terran-primary);
  border: none;
  border-radius: var(--terran-radius-md);
  color: var(--terran-bg-primary);
  cursor: pointer;
  font-size: var(--terran-font-size-md);
  transition: all var(--terran-transition-fast);
}

.retry-btn:hover {
  background: var(--terran-primary-light);
  box-shadow: 0 0 8px var(--terran-primary-glow);
}

.weather-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--terran-spacing-md);
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-lg);
}

.weather-page {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-md);
}

/* 当前天气卡片 */
.current-weather-card {
  background: linear-gradient(135deg, var(--terran-bg-tertiary) 0%, var(--terran-bg-quaternary) 100%);
  border-radius: var(--terran-radius-lg);
  padding: var(--terran-spacing-xl);
  border: 1px solid var(--terran-border-primary);
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-lg);
}

.current-main {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-sm);
}

.weather-icon-large {
  font-size: 80px;
  color: var(--terran-primary);
  filter: drop-shadow(0 0 10px var(--terran-primary-glow));
}

.current-temp {
  font-size: 64px;
  font-weight: var(--terran-font-weight-black);
  color: var(--terran-text-primary);
  line-height: 1;
}

.current-text {
  font-size: var(--terran-font-size-xl);
  color: var(--terran-text-secondary);
}

.current-details {
  display: flex;
  justify-content: center;
  gap: var(--terran-spacing-xl);
  flex-wrap: wrap;
}

.detail-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-xs);
}

.detail-label {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-tertiary);
}

.detail-value {
  font-size: var(--terran-font-size-lg);
  color: var(--terran-text-primary);
  font-weight: var(--terran-font-weight-medium);
}

/* 逐小时预报 */
.hourly-section {
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-lg);
  padding: var(--terran-spacing-md);
  border: 1px solid var(--terran-border-primary);
}

.section-title {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  color: var(--terran-primary);
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-medium);
  margin-bottom: var(--terran-spacing-md);
}

.hourly-scroll {
  display: flex;
  gap: var(--terran-spacing-md);
  overflow-x: auto;
  padding-bottom: var(--terran-spacing-sm);
}

.hourly-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--terran-spacing-xs);
  padding: var(--terran-spacing-sm);
  min-width: 60px;
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-md);
  border: 1px solid var(--terran-border-primary);
}

.hourly-time {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-tertiary);
}

.weather-icon {
  font-size: 28px;
  color: var(--terran-primary);
}

.hourly-temp {
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.hourly-text {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  white-space: nowrap;
}

/* 多日预报 */
.page-forecast {
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-lg);
  padding: var(--terran-spacing-md);
  border: 1px solid var(--terran-border-primary);
}

.daily-forecast {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-sm);
}

.daily-item {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-md);
  padding: var(--terran-spacing-sm);
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-md);
  border: 1px solid var(--terran-border-primary);
}

.daily-date {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-tertiary);
  min-width: 40px;
}

.daily-day {
  font-size: var(--terran-font-size-md);
  color: var(--terran-primary);
  font-weight: var(--terran-font-weight-medium);
  min-width: 40px;
}

.daily-icons {
  display: flex;
  gap: var(--terran-spacing-sm);
  flex: 1;
}

.day-icon,
.night-icon {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
}

.day-icon span,
.night-icon span {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-tertiary);
}

.daily-temps {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  min-width: 100px;
}

.temp-high {
  color: var(--terran-danger-light);
  font-weight: var(--terran-font-weight-bold);
}

.temp-low {
  color: var(--terran-info-light);
  font-weight: var(--terran-font-weight-bold);
}

.temp-bar {
  flex: 1;
  height: 4px;
  background: var(--terran-border-primary);
  border-radius: 2px;
  overflow: hidden;
}

.temp-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--terran-info-light), var(--terran-danger-light));
  border-radius: 2px;
}

.daily-text {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-secondary);
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-xs);
  min-width: 120px;
}

.text-separator {
  color: var(--terran-text-tertiary);
}

/* 杂项信息 */
.page-extras {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: var(--terran-spacing-md);
}

.extra-card {
  background: var(--terran-bg-tertiary);
  border-radius: var(--terran-radius-lg);
  padding: var(--terran-spacing-md);
  border: 1px solid var(--terran-border-primary);
}

.card-header {
  display: flex;
  align-items: center;
  gap: var(--terran-spacing-sm);
  color: var(--terran-primary);
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-medium);
  margin-bottom: var(--terran-spacing-md);
  padding-bottom: var(--terran-spacing-sm);
  border-bottom: 1px solid var(--terran-border-primary);
}

.card-header.warning {
  color: var(--terran-danger);
}

/* 空气质量 */
.air-main {
  display: flex;
  align-items: baseline;
  gap: var(--terran-spacing-sm);
  margin-bottom: var(--terran-spacing-md);
}

.aqi-value {
  font-size: 48px;
  font-weight: var(--terran-font-weight-black);
}

.aqi-value.excellent { color: #52c41a; }
.aqi-value.good { color: #73d13d; }
.aqi-value.light { color: #faad14; }
.aqi-value.moderate { color: #ff7a45; }
.aqi-value.heavy { color: #ff4d4f; }
.aqi-value.severe { color: #a8071a; }

.aqi-level {
  font-size: var(--terran-font-size-lg);
  color: var(--terran-text-secondary);
}

.air-details {
  display: flex;
  gap: var(--terran-spacing-lg);
}

.air-item {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-xs);
}

.air-label {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-tertiary);
}

.air-value {
  font-size: var(--terran-font-size-md);
  color: var(--terran-text-primary);
  font-weight: var(--terran-font-weight-medium);
}

/* 预警 */
.warning-list {
  display: flex;
  flex-direction: column;
  gap: var(--terran-spacing-sm);
}

.warning-item {
  padding: var(--terran-spacing-sm);
  border-radius: var(--terran-radius-md);
  border-left: 4px solid;
}

.warning-item.red {
  background: rgba(230, 57, 70, 0.15);
  border-left-color: var(--terran-danger);
}

.warning-item.orange {
  background: rgba(250, 173, 20, 0.15);
  border-left-color: var(--terran-warning);
}

.warning-item.yellow {
  background: rgba(250, 173, 20, 0.1);
  border-left-color: #fadb14;
}

.warning-item.blue {
  background: rgba(24, 144, 255, 0.1);
  border-left-color: var(--terran-info);
}

.warning-title {
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
  margin-bottom: var(--terran-spacing-xs);
}

.warning-text {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-secondary);
  line-height: 1.5;
}

.empty-text {
  color: var(--terran-text-tertiary);
  font-size: var(--terran-font-size-sm);
  text-align: center;
  padding: var(--terran-spacing-md);
}

/* 天文信息 */
.astro-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--terran-spacing-sm);
}

.astro-item {
  display: flex;
  justify-content: space-between;
  padding: var(--terran-spacing-sm);
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-sm);
}

.astro-item.full {
  grid-column: span 2;
}

.astro-label {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-text-tertiary);
}

.astro-value {
  font-size: var(--terran-font-size-sm);
  color: var(--terran-primary);
  font-weight: var(--terran-font-weight-medium);
}

/* 生活指数 */
.indices-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: var(--terran-spacing-sm);
}

.index-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--terran-spacing-sm);
  background: var(--terran-bg-secondary);
  border-radius: var(--terran-radius-sm);
  text-align: center;
}

.index-name {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-tertiary);
  margin-bottom: var(--terran-spacing-xs);
}

.index-level {
  font-size: var(--terran-font-size-md);
  font-weight: var(--terran-font-weight-bold);
  color: var(--terran-text-primary);
}

.index-level.good {
  color: var(--terran-primary);
}

.index-level.bad {
  color: var(--terran-danger);
}

.index-level.normal {
  color: var(--terran-warning);
}

.index-category {
  font-size: var(--terran-font-size-xs);
  color: var(--terran-text-secondary);
  margin-top: var(--terran-spacing-xs);
}

/* 刷新按钮 */
.refresh-weather-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--terran-spacing-sm);
  padding: var(--terran-spacing-md);
  background: var(--terran-bg-tertiary);
  border: 1px solid var(--terran-border-primary);
  border-radius: var(--terran-radius-md);
  color: var(--terran-text-secondary);
  cursor: pointer;
  transition: all var(--terran-transition-fast);
  margin-top: var(--terran-spacing-md);
}

.refresh-weather-btn:hover:not(:disabled) {
  border-color: var(--terran-primary);
  color: var(--terran-primary);
}

.refresh-weather-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.refresh-weather-btn svg.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>