// ================= 后端事件类型 =================

/**
 * 后端基础事件接口
 */
export interface BaseBackendEvent {
  event: string
}

/**
 * 后端启动完成事件
 */
export interface PartialReadyEvent extends BaseBackendEvent {
  event: 'partial_ready'
}

/**
 * 唤醒模型加载完成事件
 */
export interface WakeModelLoadedEvent extends BaseBackendEvent {
  event: 'wake_model_loaded'
}

/**
 * 转写模型加载完成事件
 */
export interface TranscribeModelLoadedEvent extends BaseBackendEvent {
  event: 'transcribe_model_loaded'
}

/**
 * 对话模型加载完成事件
 */
export interface LlmModelLoadedEvent extends BaseBackendEvent {
  event: 'llm_model_loaded'
}

/**
 * TTS模型加载完成事件
 */
export interface TtsModelLoadedEvent extends BaseBackendEvent {
  event: 'tts_model_loaded'
}

/**
 * 所有模型加载完成事件
 */
export interface FullReadyEvent extends BaseBackendEvent {
  event: 'full_ready'
}

/**
 * 兼容原有逻辑的就绪事件
 */
export interface ReadyEvent extends BaseBackendEvent {
  event: 'ready'
}

/**
 * 唤醒词检测事件
 */
export interface WakeEvent extends BaseBackendEvent {
  event: 'wake'
}

/**
 * 语音转写结果事件
 */
export interface TranscriptionResultEvent extends BaseBackendEvent {
  event: 'transcription_result'
  text: string
}

/**
 * AI对话流式输出事件
 */
export interface ChatChunkEvent extends BaseBackendEvent {
  event: 'chat_chunk'
  content: string
}

/**
 * 清除已累积的流式输出（本地模型求救切换到 GLM 时使用）
 */
export interface ChatChunkClearEvent extends BaseBackendEvent {
  event: 'chat_chunk_clear'
}

/**
 * AI对话生成完成事件
 */
export interface ChatCompleteEvent extends BaseBackendEvent {
  event: 'chat_complete'
}

/**
 * AI对话生成取消事件
 */
export interface ChatCancelledEvent extends BaseBackendEvent {
  event: 'chat_cancelled'
}

/**
 * TTS开始播报事件
 */
export interface TtsStartedEvent extends BaseBackendEvent {
  event: 'tts_started'
}

/**
 * TTS停止播报事件
 */
export interface TtsStoppedEvent extends BaseBackendEvent {
  event: 'tts_stopped'
}

/**
 * TTS播报完成事件
 */
export interface TtsCompleteEvent extends BaseBackendEvent {
  event: 'tts_complete'
}

/**
 * 历史消息对象
 */
export interface HistoryMessage {
  role: 'user' | 'assistant' | 'system'
  content: string
  timestamp?: number
}

/**
 * 对话历史加载完成事件
 */
export interface HistoryLoadedEvent extends BaseBackendEvent {
  event: 'history_loaded'
  history: HistoryMessage[]
}

/**
 * 对话历史清空事件
 */
export interface HistoryClearedEvent extends BaseBackendEvent {
  event: 'history_cleared'
}

/**
 * 错误事件
 */
export interface ErrorEvent extends BaseBackendEvent {
  event: 'error'
  type?: string
  msg: string
}

/**
 * 状态更新事件（前端连接后查询后端当前状态）
 */
export interface StatusUpdateEvent extends BaseBackendEvent {
  event: 'status_update'
  current_mode: 'wake' | 'transcribe'
  transcribe_substate: 'idle' | 'generating' | 'playing_tts'
  tts_busy: boolean
  wake_model_loaded: boolean
  transcribe_model_loaded: boolean
  llm_model_loaded: boolean
  tts_model_loaded: boolean
  history_count: number
  easter_egg_enabled?: boolean
  memory_enabled?: boolean
}

/**
 * 待办事项对象
 */
export interface TodoItem {
  id: number
  content: string
  created_at: string
  due_date?: string
  status: 'pending' | 'completed'
}

/**
 * 待办事项已添加事件
 */
export interface TodoAddedEvent extends BaseBackendEvent {
  event: 'todo_added'
  todo: TodoItem
}

/**
 * 待办事项列表事件
 */
export interface TodoListEvent extends BaseBackendEvent {
  event: 'todo_list'
  todos: TodoItem[]
  filter: string
}

/**
 * 待办事项更新事件
 */
export interface TodoUpdatedEvent extends BaseBackendEvent {
  event: 'todo_updated'
  todo_id: number
  status?: string
  deleted?: boolean
}

/**
 * 长期记忆条目（含完整元数据）
 */
export interface MemoryItem {
  id: string
  content: string
  timestamp: number
  importance: number
  type: string  // attribute|preference|habit|plan|event|opinion|fact
  score?: number  // 语义检索时的相关性评分
}

/**
 * 长期记忆列表事件
 */
export interface MemoriesListEvent extends BaseBackendEvent {
  event: 'memories_list'
  memories: MemoryItem[] | string[]
  total?: number  // 总记忆数量（透明度模式）
}

/**
 * 单条记忆删除事件
 */
export interface MemoryDeletedEvent extends BaseBackendEvent {
  event: 'memory_deleted'
  mem_id: string
}

/**
 * 所有记忆清空事件
 */
export interface MemoriesClearedEvent extends BaseBackendEvent {
  event: 'memories_cleared'
  count: number
}

/**
 * 记忆已更新事件（包括语义更新和矛盾删除）
 */
export interface MemoryUpdatedEvent extends BaseBackendEvent {
  event: 'memory_updated'
  mem_id: string
  content?: string       // 存在表示更新，不存在表示删除
  type?: string
  importance?: number
  timestamp?: number
  deleted?: boolean      // true 表示删除操作
}

/**
 * 倒计时完成事件
 */
export interface CountdownCompleteEvent extends BaseBackendEvent {
  event: 'countdown_complete'
  duration: number
  text: string
}

/**
 * 系统状态结果事件
 */
export interface SystemStatusResultEvent extends BaseBackendEvent {
  event: 'system_status_result'
  data: {
    cpu?: { usage: number; cores: number; threads: number }
    memory?: { total_gb: number; used_gb: number; usage: number }
    disk?: { total_gb: number; used_gb: number; usage: number }
    battery?: { percent: number; plugged: boolean; time_left_min?: number } | null
    network?: { status: string; ip?: string }
  }
}

/**
 * 彩蛋触发事件
 */
export interface EggTriggeredEvent extends BaseBackendEvent {
  event: 'egg_triggered'
  id: string
  transition_text: string
  display_text: string
  audio_file: string
}

/**
 * 彩蛋状态更新事件
 */
export interface EasterEggStatusEvent extends BaseBackendEvent {
  event: 'easter_egg_status'
  enabled: boolean
}

/**
 * 后端事件联合类型
 */
export type BackendEvent =
  | PartialReadyEvent
  | WakeModelLoadedEvent
  | TranscribeModelLoadedEvent
  | LlmModelLoadedEvent
  | TtsModelLoadedEvent
  | FullReadyEvent
  | ReadyEvent
  | WakeEvent
  | TranscriptionResultEvent
  | ChatChunkEvent
  | ChatChunkClearEvent
  | ChatCompleteEvent
  | ChatCancelledEvent
  | TtsStartedEvent
  | TtsStoppedEvent
  | TtsCompleteEvent
  | HistoryLoadedEvent
  | HistoryClearedEvent
  | ErrorEvent
  | StatusUpdateEvent
  | EggTriggeredEvent
  | EasterEggStatusEvent
  | TodoAddedEvent
  | TodoListEvent
  | TodoUpdatedEvent
  | MemoriesListEvent
  | MemoryDeletedEvent
  | MemoriesClearedEvent
  | MemoryUpdatedEvent
  | CountdownCompleteEvent
  | SystemStatusResultEvent
  | WeatherResultEvent
  | SettingsUpdatedEvent
  | ApiKeyTestResultEvent

// ================= 前端指令类型 =================

/**
 * 基础指令接口
 */
export interface BaseFrontendAction {
  action: string
}

/**
 * 设置模式指令
 */
export interface SetModeAction extends BaseFrontendAction {
  action: 'set_mode'
  mode: 'wake' | 'transcribe'
}

/**
 * 转写音频文件指令
 */
export interface TranscribeFileAction extends BaseFrontendAction {
  action: 'transcribe_file'
  file_path: string
}

/**
 * 发送对话消息指令
 */
export interface SendMessageAction extends BaseFrontendAction {
  action: 'send_message'
  content: string
}

/**
 * 取消生成指令
 */
export interface CancelGenerationAction extends BaseFrontendAction {
  action: 'cancel_generation'
}

/**
 * 清空历史指令
 */
export interface ClearHistoryAction extends BaseFrontendAction {
  action: 'clear_history'
}

/**
 * 获取历史指令
 */
export interface GetHistoryAction extends BaseFrontendAction {
  action: 'get_history'
}

/**
 * 获取状态指令
 */
export interface GetStatusAction extends BaseFrontendAction {
  action: 'get_status'
}

/**
 * TTS播放指令
 */
export interface TtsPlayAction extends BaseFrontendAction {
  action: 'tts_play'
  text: string
}

/**
 * TTS停止指令
 */
export interface TtsStopAction extends BaseFrontendAction {
  action: 'tts_stop'
}

/**
 * 开始加载模型指令
 */
export interface StartLoadingAction extends BaseFrontendAction {
  action: 'start_loading'
}

/**
 * 设置彩蛋开关指令
 */
export interface SetEasterEggAction extends BaseFrontendAction {
  action: 'set_easter_egg'
  enabled: boolean
}

/**
 * 添加待办事项指令
 */
export interface AddTodoAction extends BaseFrontendAction {
  action: 'add_todo'
  content: string
  due_date?: string
}

/**
 * 获取待办事项列表指令
 */
export interface ListTodosAction extends BaseFrontendAction {
  action: 'list_todos'
  filter?: 'today' | 'all'
}

/**
 * 完成待办事项指令
 */
export interface CompleteTodoAction extends BaseFrontendAction {
  action: 'complete_todo'
  todo_id: number
}

/**
 * 删除待办事项指令
 */
export interface DeleteTodoAction extends BaseFrontendAction {
  action: 'delete_todo'
  todo_id: number
}

/**
 * 获取长期记忆指令
 */
export interface GetMemoriesAction extends BaseFrontendAction {
  action: 'get_memories'
  query?: string
  after?: number
  before?: number
}

/**
 * 删除单条记忆指令
 */
export interface DeleteMemoryAction extends BaseFrontendAction {
  action: 'delete_memory'
  mem_id: string
}

/**
 * 清空所有长期记忆指令
 */
export interface ClearAllMemoriesAction extends BaseFrontendAction {
  action: 'clear_all_memories'
}

/**
 * 手动更新单条记忆内容
 */
export interface UpdateMemoryAction extends BaseFrontendAction {
  action: 'update_memory'
  mem_id: string
  content: string
  importance?: number
  type?: string
}

/**
 * 查询系统状态指令
 */
export interface GetSystemStatusAction extends BaseFrontendAction {
  action: 'get_system_status'
}

/**
 * 查询天气指令
 */
export interface QueryWeatherAction extends BaseFrontendAction {
  action: 'query_weather'
  location?: string
  sub_ops?: string[]
}

/**
 * 云端模型提供商类型
 */
export type CloudProvider = 'glm' | 'deepseek' | 'openai' | 'custom'

/**
 * 云端模型配置
 */
export interface CloudModelConfig {
  provider: CloudProvider
  apiKey: string
  model: string
  baseUrl: string
}

/**
 * 更新设置指令
 */
export interface UpdateSettingsAction extends BaseFrontendAction {
  action: 'update_settings'
  settings: {
    // Cloud LLM (new)
    cloudProvider?: CloudProvider
    cloudApiKey?: string
    cloudModel?: string
    cloudBaseUrl?: string
    // Legacy GLM key (backward compatibility)
    glmApiKey?: string
    // Weather
    qweatherApiKey?: string
    qweatherApiHost?: string
    // Web search
    qianfanApiKey?: string
    // Forum search
    forumSearchApiToken?: string
    forumSearchBaseUrl?: string
    // Default city
    defaultCity?: string
    // Per-provider API keys
    cloudApiKeys?: Record<string, string>
    // Enhanced mode
    enhancedMode?: boolean
  }
}

/**
 * 天气查询结果事件
 */
export interface WeatherResultEvent extends BaseBackendEvent {
  event: 'weather_result'
  data?: {
    location: string
    results: Array<{
      sub_op: string
      data: any
      result_text: string
    }>
  }
  error?: string
}

/**
 * 设置更新结果事件
 */
export interface SettingsUpdatedEvent extends BaseBackendEvent {
  event: 'settings_updated'
  success: boolean
  enhanced_mode?: boolean
  model_reloading?: boolean
  model_reload_success?: boolean
  mcp_ready?: boolean
}

/**
 * 测试 GLM API Key 指令（保留向后兼容）
 */
export interface TestGlmKeyAction extends BaseFrontendAction {
  action: 'test_glm_key'
  api_key: string
}

/**
 * 测试云端模型 API Key 指令
 */
export interface TestCloudKeyAction extends BaseFrontendAction {
  action: 'test_cloud_key'
  provider: CloudProvider
  api_key: string
  model: string
  base_url: string
}

/**
 * 测试和风天气 API Key 指令
 */
export interface TestQweatherKeyAction extends BaseFrontendAction {
  action: 'test_qweather_key'
  api_key: string
  api_host: string
}

/**
 * 测试百度千帆 API Key 指令
 */
export interface TestQianfanKeyAction extends BaseFrontendAction {
  action: 'test_qianfan_key'
  api_key: string
}

/**
 * 测试集市搜索（小秋）API Key 指令
 */
export interface TestForumSearchKeyAction extends BaseFrontendAction {
  action: 'test_forum_search_key'
  api_token: string
  base_url: string
}

/**
 * API Key 测试结果事件
 */
export interface ApiKeyTestResultEvent extends BaseBackendEvent {
  event: 'api_key_test_result'
  type: 'cloud' | 'glm' | 'qweather' | 'qianfan' | 'forum_search'
  success: boolean
  message: string
}

/**
 * 前端指令联合类型
 */
export type FrontendAction =
  | SetModeAction
  | TranscribeFileAction
  | SendMessageAction
  | CancelGenerationAction
  | ClearHistoryAction
  | GetHistoryAction
  | GetStatusAction
  | TtsPlayAction
  | TtsStopAction
  | StartLoadingAction
  | SetEasterEggAction
  | AddTodoAction
  | ListTodosAction
  | CompleteTodoAction
  | DeleteTodoAction
  | GetMemoriesAction
  | DeleteMemoryAction
  | ClearAllMemoriesAction
  | UpdateMemoryAction
  | GetSystemStatusAction
  | QueryWeatherAction
  | UpdateSettingsAction
  | TestGlmKeyAction
  | TestCloudKeyAction
  | TestQweatherKeyAction
  | TestQianfanKeyAction
  | TestForumSearchKeyAction

// ================= 对话相关类型 =================

/**
 * 聊天消息
 */
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: number
}

/**
 * 对话状态
 */
export interface ChatState {
  messages: ChatMessage[]
  isGenerating: boolean
  currentResponse: string
  inputText: string
}

// ================= 模型状态类型 =================

/**
 * 模型加载状态
 */
export interface ModelStatus {
  wakeModelLoaded: boolean
  transcribeModelLoaded: boolean
  llmModelLoaded: boolean
  ttsModelLoaded: boolean
  allModelsLoaded: boolean
  backendReady: boolean
}

/**
 * 模型类型
 */
export type ModelType = 'wake' | 'transcribe' | 'llm'

// ================= 录音相关类型 =================

/**
 * 录音状态
 */
export interface AudioRecordState {
  isRecording: boolean
  recordingDuration: number
  audioLevel: number
}

/**
 * 音频配置
 */
export interface AudioConfig {
  sampleRate: number
  channelCount: number
  echoCancellation: boolean
  noiseSuppression: boolean
}

// ================= 应用状态类型 =================

/**
 * 应用运行模式
 */
export type AppMode = 'wake' | 'transcribe'

/**
 * 转写子状态
 */
export type TranscribeSubstate = 'idle' | 'generating' | 'playing_tts'

/**
 * 应用完整状态
 */
export interface AppState {
  currentMode: AppMode
  transcribeSubstate: TranscribeSubstate
  isBackendReady: boolean
  backendError: string | null
}

// ================= Electron API 类型 =================

/**
 * Electron 暴露的 API
 */
export interface ElectronAPI {
  sendToBackend: (action: FrontendAction) => void
  onBackendEvent: (callback: (event: BackendEvent) => void) => () => void
  onceBackendEvent: (callback: (event: BackendEvent) => void) => void
  showWindow: () => void
  hideWindow: () => void
  minimizeWindow: () => void
  getBackendPath: () => Promise<string>
  saveTempAudio: (data: ArrayBuffer, fileName: string) => Promise<string>
  openExternal: (url: string) => void
}

/**
 * 扩展 Window 接口
 */
declare global {
  interface Window {
    electronAPI: ElectronAPI
    // HMR 防护标志
    __useBackend_initialized?: boolean
    __useChat_initialized?: boolean
    __useModelStatus_initialized?: boolean
    __useTTS_initialized?: boolean
  }
}

// ================= 组件 Props 类型 =================

/**
 * 消息列表组件 Props
 */
export interface MessageListProps {
  messages: ChatMessage[]
  isGenerating: boolean
  currentResponse: string
}

/**
 * 单条消息组件 Props
 */
export interface MessageItemProps {
  message: ChatMessage
  isLast: boolean
}

/**
 * 输入区域组件 Props
 */
export interface InputAreaProps {
  modelValue: string
  disabled: boolean
  placeholder?: string
}

/**
 * 语音按钮组件 Props
 */
export interface VoiceButtonProps {
  isRecording: boolean
  audioLevel: number
  disabled: boolean
}

/**
 * 状态栏组件 Props
 */
export interface StatusBarProps {
  wakeReady: boolean
  transcribeReady: boolean
  llmReady: boolean
  loadingText: string
}

// ================= 工具函数类型 =================

/**
 * 取消订阅函数
 */
export type UnsubscribeFn = () => void

/**
 * 事件处理器
 */
export type EventHandler<T> = (event: T) => void

/**
 * 异步操作结果
 */
export interface AsyncResult<T> {
  data?: T
  error?: string
  loading: boolean
}
