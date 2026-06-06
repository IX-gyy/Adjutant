# 阿塔尼斯 AI 语音助手（泰伦帝国副官版） v2.0

基于 Electron + Vue3 + TypeScript + Python 开发的桌面端 AI 语音助手，人设为《星际争霸 2》泰伦帝国机械副官，支持语音唤醒、语音转写、AI 对话（赫尔墨斯长期记忆）、语音合成（TTS）全流程交互。

## 核心功能

1. **语音唤醒**：后台静默运行，通过预设唤醒词（支持拼音模糊匹配）唤出应用窗口；
2. **语音转写**：按住按钮录音，松开后自动转写为文字并填入输入框，支持手动修正；
3. **AI 对话（升级版）**：
   - **本地副官模型**：基于 Qwen2.5-3B 生成回复，角色扮演稳定，流式输出；
   - **赫尔墨斯记忆核心**：双层记忆架构（短期会话记忆 + 长期向量记忆），长期记忆支持跨会话语义检索；
   - **混合记忆提取**：云端智谱 GLM-4-Flash 异步提取对话中的关键事实、偏好，写入 ChromaDB 向量库；
   - **结构化 TODO 系统**：完全由云端智谱 GLM-4-Flash 驱动，本地副官模型不感知；后端 SQLite 管理待办事项，支持添加、查询、完成等操作，通过固定格式回复与用户交互；
   - **时间感知**：注入系统时间，理解相对时间表述（“今天”“明天”），记忆附带时间元数据。
4. **语音合成（TTS）**：基于 Kokoro-82M 模型，AI 回复同时自动播报，支持手动停止/重新播报；
5. **纯 CPU 运行**：无需独立 GPU，适配普通办公电脑。
6. **设置与 API Key 管理**：用户可在设置面板中输入和管理 API Key（GLM API Key、和风天气 API Key 及 API Host），设置本地持久化存储，缺失时给出警告提示。

## 技术栈

| 模块 | 技术选型 | 核心依赖 |
|------|----------|----------|
| 前端 | Electron + Vue3 + TypeScript + Vite | - |
| 后端 | Python 3.10（Windows Embeddable Package） | vosk、sounddevice、llama-cpp-python、kokoro、chromadb、openai |
| 语音唤醒/转写 | Vosk | vosk-model-small-cn |
| AI 对话 | Llama.cpp | qwen2_5_3b-instruct-q4_k_m-LOT.gguf |
| 意图识别 | BGE 中文嵌入模型（GGUF格式） | bge-small-q8-zh-v1.5.gguf |
| 长期记忆 | ChromaDB（向量库） + 智谱 GLM-4-Flash API（记忆提取） | chromadb、openai SDK |
| TODO 管理 | SQLite 本地数据库 | sqlite3 |
| 语音合成（TTS） | Kokoro-82M + OnnxRuntime | kokoro-v1_1-zh.onnx |
| 打包工具 | electron-builder（前端） | - |

## 内存优化配置

为适应低配置运行环境，进行了以下内存优化：

| 优化项 | 配置值 | 说明 |
|--------|--------|------|
| LLM上下文窗口 | 8192 tokens | 降低自16384，减少内存占用 |
| ChromaDB缓存 | cache_capacity=1000 | 限制向量缓存大小 |
| 短期历史限制 | 5轮 | 固定保留最近5轮对话 |
| 记忆提取间隔 | 3轮 | 每3轮触发一次长期记忆提取 |
| Vosk模型共享 | 单例模式 | 多线程共享同一个模型实例 |
| 空闲内存回收 | 定时触发 | 5分钟无活动后释放非关键资源 |

### Vosk模型共享机制
- 转写线程和唤醒线程共享同一个Vosk模型实例
- 使用 `shared_vosk_model` 全局变量避免重复加载
- 模型在应用启动时加载，退出时释放

### 空闲内存回收
- 后台启动 `memory_cleanup_thread()` 守护线程
- 5分钟无对话活动时触发内存清理
- 清理内容包括：释放临时缓存、重置非关键状态

## 项目目录结构

```
frontend/
├── package.json
├── electron/
│   ├── main.ts          # Electron 主进程：启动 Python 后端、窗口管理
│   └── preload.ts       # 预加载脚本：暴露安全 API 给渲染进程
├── src/                  # Vue 前端源码
│   ├── main.ts          # Vue 应用入口
│   ├── App.vue          # 根组件
│   ├── components/      # UI 组件
│   │   ├── ChatWindow.vue
│   │   ├── MessageList.vue
│   │   ├── InputArea.vue
│   │   ├── VoiceButton.vue
│   │   ├── WeatherPanel.vue    # 天气查询面板
│   │   ├── SettingsPanel.vue   # 设置面板（API Key 管理）
│   │   ├── TodoPanel.vue       # 待办事项面板（计划）
│   │   └── StatusBar.vue
│   ├── composables/     # 组合式函数
│   │   ├── useBackend.ts
│   │   ├── useChat.ts
│   │   ├── useTTS.ts
│   │   └── useSettings.ts      # 设置管理（含本地存储）
│   ├── stores/          # Pinia 状态管理
│   ├── types/           # TypeScript 类型定义
│   └── styles/          # 样式文件
├── public/
└── backend/              # pyinstaller打包好的后端
    ├── backend.exe       # 后端
    ├── memory_db/        # ChromaDB 持久化目录（跨会话长期记忆）
    ├── todo.db           # SQLite 待办事项数据库
    └── models/           # 模型文件
        ├── vosk-model-small-cn/
        ├── qwen2_5_3b-instruct-q4_k_m-LOT.gguf
        ├── bge-small-q8-zh-v1.5.gguf   # BGE 中文嵌入模型（GGUF格式）
        └── kokoro-zh/
            ├── kokoro-v1.1-zh.onnx
            ├── config.json
            └── voices-v1.1-zh.bin
```

## 状态机设计

### 核心原则
- 单进程多线程架构：主线程（状态管理/通信）+ 唤醒监听线程 + LLM 推理线程 + TTS 播报线程；
- 线程安全：所有全局状态读写加锁保护；
- 分步加载：模型异步加载，优先解锁核心功能。

### 1. 全局状态定义
```python
# 顶层主状态
current_mode: "wake" | "transcribe"
# 一级子状态（transcribe 模式下）
transcribe_substate: "idle" | "generating" | "playing_tts" | "playing_egg"
# 二级子状态（TTS 相关）
tts_substate: "idle" | "playing"
# 线程同步
state_lock, chat_lock, tts_lock, generation_lock
cancel_generation_event, cancel_tts_event
# 队列
audio_queue, chat_request_queue, tts_request_queue
```

### 2. 启动阶段状态流转
```
主线程启动
    ├─ 初始化全局状态、锁、事件、队列
    ├─ 初始化记忆核心（ChromaDB + SQLite TODO 表）
    ├─ 推送 partial_ready → 前端秒开窗口
    └─ 后台模型加载线程（异步）
        ├─ 加载唤醒模型 → 推送 wake_model_loaded
        ├─ 加载转写模型 → 推送 transcribe_model_loaded
        ├─ 加载 LLM 模型 → 推送 llm_model_loaded
        ├─ 加载 TTS 模型 → 推送 tts_model_loaded
        └─ 全量加载完成 → 推送 full_ready → 加载长期记忆向量库与待办事项
启动守护线程：唤醒监听 / LLM 推理 / TTS 播报 / 后台记忆提取
主线程进入指令循环
```

### 3. 顶层主状态：current_mode = "wake"（后台唤醒）
- **状态**：窗口隐藏，麦克风打开，仅唤醒功能生效；
- **流转**：
  - 检测到唤醒词 / 前端发送 `set_mode=transcribe` → 清空 `audio_queue` → 关闭麦克风 → 切换 `current_mode=transcribe`；
  - 从 `transcribe` 切回 → 触发 `cancel_tts_event` → 清空 `tts_request_queue` → 打开麦克风。

### 4. 顶层主状态：current_mode = "transcribe"（前台交互）
#### 子状态 4.1：transcribe_substate = "idle"（空闲）
- **状态**：窗口显示，麦克风关闭，全功能解锁；
- **允许操作**：
  - `transcribe_file`：语音转写 → 推送 `transcription_result`；
  - `send_message`：发送对话 → 切换 `generating`；
  - **新增**：`add_todo`、`list_todos`、`complete_todo`、`delete_todo` 等 TODO 操作；
  - **新增**：`get_memories` 查询长期记忆；
  - `tts_play`：手动播报 → 放入 `tts_request_queue` → 切换 `tts_substate=playing`；
  - `set_mode=wake`：关闭窗口 → 切回 `wake`。

#### 子状态 4.2：transcribe_substate = "generating"（AI 生成中）
- **状态**：交互锁定，仅允许取消生成；
- **流转**：
  - LLM 流式生成 → 推送 `chat_chunk` → 累计片段放入 `tts_request_queue`（逐段播报策略）；
  - 生成完成 → 将本轮对话加入短期记忆，并若满足条件（每 N 轮或含特定意图）将对话片段送入后台记忆提取队列 → 持久化 → 推送 `chat_complete` → 切换 `playing_tts`（如有未播 TTS）或 `idle`；
  - 用户取消 → 触发 `cancel_generation_event` + `cancel_tts_event` → 切换 `idle`。

#### 子状态 4.3：transcribe_substate = "playing_tts"（TTS 播报中，包括 TODO 回复）
- **状态**：交互锁定，仅允许停止播报/关闭窗口；
- **在此状态下的2种可能流程**：
  1. **普通 AI 回复**：TTS 线程从队列取文本 → 合成音频 → 播放；
  2. **TODO 请求**：用户消息被 TODO 关键词拦截后，过渡语+结果语合并为完整回复，推送 `chat_complete` 后设置为此状态，完整文本放入 TTS 队列播放。
- **流转**：
  - 播报完成 → 推送 `tts_complete` → 切换 `idle`；
  - 用户停止/取消 → 触发 `cancel_tts_event` → 清空队列 → 切换 `idle`。

## 前后端通信协议

### 前端 → 后端（指令）

| 指令              | 参数                         | 说明                             |
| ----------------- | ---------------------------- | -------------------------------- |
| set_mode          | mode: "wake" \| "transcribe" | 切换顶层状态                     |
| transcribe_file   | file_path: str               | 语音转写                         |
| send_message      | content: str                 | 发送对话；若内容包含 TODO 关键词（“提醒”“别忘了”等），后端将直接进入 TODO 流程，不经过本地 LLM|
| cancel_generation | -                            | 取消生成（可取消 generating/playing_egg/playing_tts 状态） |
| **add_todo**      | content: str, due_date?: str | 添加待办事项                     |
| **list_todos**    | filter?: "today" \| "all"    | 获取待办列表                     |
| **complete_todo** | todo_id: int                 | 完成待办                         |
| **delete_todo**   | todo_id: int                 | 删除待办                         |
| tts_play          | text: str                    | 手动播报                         |
| tts_stop          | -                            | 停止播报                         |
| clear_history     | -                            | 清空短期历史                     |
| get_history       | -                            | 获取对话历史                     |
| **get_memories**  | query?: str                  | 查询长期记忆（可选关键词）       |
| set_easter_egg    | enabled: boolean             | 设置彩蛋开关                     |
| get_status        | -                            | 获取系统状态                     |
| **save_settings** | settings: object             | 保存设置（API Key、城市等）     |
| **test_glm_key**  | api_key: string              | 测试 GLM API Key 是否有效      |
| **test_qweather_key** | api_key: string, api_host: string | 测试和风天气 API Key 和 Host |

### 后端 → 前端（事件）

| 事件                    | 参数                              | 说明                       |
| ----------------------- | --------------------------------- | -------------------------- |
| partial_ready           | -                                 | 后端启动完成               |
| wake_model_loaded       | -                                 | 唤醒模型加载完成           |
| transcribe_model_loaded | -                                 | 转写模型加载完成           |
| llm_model_loaded        | -                                 | LLM 模型加载完成           |
| tts_model_loaded        | -                                 | TTS 模型加载完成           |
| full_ready              | -                                 | 全量加载完成               |
| wake                    | -                                 | 检测到唤醒词               |
| transcription_result    | text: str                         | 转写结果                   |
| chat_chunk              | content: str                      | LLM 流式片段               |
| chat_complete           | content?: str                     | 生成完成（TODO流程时返回完整内容） |
| chat_cancelled          | -                                 | 生成已取消                 |
| **todo_added**          | todo: {id, content, due_date}     | 待办已添加                 |
| **todo_list**           | todos: list                       | 返回待办列表               |
| **todo_updated**        | todo: {id, status, ...}           | 待办状态更新               |
| tts_started             | -                                 | TTS 开始播报               |
| tts_stopped             | -                                 | TTS 已停止                 |
| tts_complete            | -                                 | TTS 播报完成               |
| **memories_list**       | memories: list                    | 长期记忆列表               |
| history_loaded          | history: list                     | 对话历史                   |
| history_cleared         | -                                 | 历史已清空                 |
| error                   | type: str, msg: str               | 错误信息                   |
| egg_triggered           | id, transition_text, display_text, audio_file | 彩蛋触发       |
| easter_egg_status       | enabled: boolean                  | 彩蛋开关状态更新           |
| **memory_extraction_status** | status: "idle" \| "processing" | 记忆提取后台状态（可选） |
| **api_key_test_result** | type: "glm" \| "qweather", success: boolean, message: str | API Key 测试结果 |

## 彩蛋系统

### 功能概述
彩蛋系统是副官AI的特色功能，当用户输入特定触发词时，会播放蒙斯克元首的经典语音，增强交互趣味性。

### 前置校验规则
1. **全局彩蛋开关**：只有开关处于「开启」状态时，才会进入彩蛋匹配流程
2. **强制前缀校验**：所有彩蛋触发，必须满足用户输入以「副官」/「副官，」开头

### 触发流程
```
用户输入 → 前缀校验 → 彩蛋开关检查 → JSON规则匹配 → 推送egg_triggered事件
                                              ↓
                                       匹配失败 → 正常LLM流程
```

### 匹配优先级（从高到低）
1. **精准指令匹配**：100% 完全匹配用户输入的整句话，无模糊匹配，用于隐藏高稀有度彩蛋
2. **场景关键词匹配**：必须同时命中 2 组及以上关键词，避免单字误触，用于日常自然触发
3. **简化关键词匹配**：必须命中至少 1 个≥2 字的核心关键词，低门槛易探索

### 前端展示效果
- **过渡消息**：副官头像 + 普通消息样式，显示「收到元首加密通讯，请聆听最高指示」
- **元首通讯消息**：蒙斯克专属头像 + 帝国红金样式 +【元首通讯】标识

### 音频播报流程
1. 先播放副官过渡语的 TTS（副官默认音色）
2. 再播放蒙斯克的预录语音（本地音频文件）
3. 播报完成后推送 `tts_complete` 事件

### 指令与事件扩展
| 指令/事件 | 参数 | 说明 |
|-----------|------|------|
| set_easter_egg | enabled: boolean | 设置彩蛋开关状态 |
| get_status | - | 获取状态（返回包含 easter_egg_enabled）|

### 项目目录结构（含彩蛋）
```
backend/
├── config/
│   └── easter_egg_rules.json    # 彩蛋匹配规则配置
├── assets/
│   └── audio/                   # 彩蛋音频文件
│       ├── cherish.wav
│       ├── confident.wav
│       ├── danger.wav
│       ├── determination.wav
│       ├── employ.wav
│       ├── encourage.wav
│       ├── focus.wav
│       ├── home.wav
│       ├── invaluable_time.wav
│       ├── launch.wav
│       ├── noisy.wav
│       ├── people.wav
│       ├── people2.wav
│       ├── protect.wav
│       ├── radiation.wav
│       ├── urge.wav
│       ├── victory.wav
│       └── emperor_paranoia.wav
├── backend.exe
└── ...
```

---

## AI 对话模块详细设计（赫尔墨斯记忆核心）

### 架构图

```
用户消息 → 短期记忆 (ConversationManager) → 检索长期记忆 (ChromaDB) 
           ↓                                        ↓
         构建增强 Prompt（系统人设 + 时间注入 + 长期记忆片段 + 短期历史）
           ↓
         本地 LLM 流式生成回复 → 更新短期记忆
           ↓
         后台记忆提取线程（每 N 轮或含“记住”时触发）
           → 将最近对话发送给智谱 GLM-4-Flash
           → 提取关键信息并写入 ChromaDB（附带时间戳）
```

### 记忆分层

| 记忆类型 | 实现方式 | 生命周期 | 说明 |
|----------|----------|----------|------|
| 工作记忆 | 当前用户消息 + 上下文 Prompt | 单次推理 | 临时推理所需 |
| 短期记忆 | chat_history 内存数组 + history.json 持久化 | 当前会话 | 启动时从文件加载，对话时直接使用 |
| 长期情景记忆 | ChromaDB 向量集合 | 持久化 | 由 GLM 提取，包含属性、事件，附带时间元数据 |
| 语义记忆 | ChromaDB 中“指挥官属性”类条目 | 持久化 | 如“指挥官是大三学生” |
| 程序性记忆（未来） | 副官对话风格、行为规则 | 固化在 System Prompt | 暂不动态更新 |

#### 短期记忆机制
- **chat_history**：内存中的数组，每次对话时直接加载到 LLM prompt 中
- **history.json**：磁盘文件，用于持久化保存，下次启动时加载到 chat_history
- **自动截断**：固定保留最近5轮对话（用户2轮+副官2轮+系统1轮），超出部分自动删除最旧消息
- **手动清理**：用户点击"清理历史"按钮时，清空内存和文件中的所有短期历史
- **不进入短期历史**：TODO 对话和彩蛋对话不会写入 chat_history，确保本地 LLM 不会感知这些事件

#### 长期记忆提取
- 普通对话完成后，每3轮对话自动触发一次记忆提取（`MEMORY_EXTRACTION_INTERVAL = 3`）
- 提取内容经过 importance 过滤，仅保留 importance >= 7 的高价值记忆条目
- TODO 对话和彩蛋对话**不会**进入长期记忆提取流程
- 长期记忆在每次对话时检索相关条目，注入到 prompt 中供 LLM 使用

### 主动求救机制

本地副官模型（Qwen2.5-3B）虽然高效省资源，但在某些复杂问题面前能力有限。当检测到以下求救信号时，系统自动切换到云端GLM-4-Flash：

#### 求救信号检测
当本地模型回复中出现以下关键词时，触发切换：
- "帝国数据库"：表示需要查询实时/专业信息
- "我需要查询"：表示需要外部知识

#### 切换流程
```
本地 LLM 生成中 → 检测到求救信号 → 切换到 GLM-4-Flash 重新生成
           ↓
    结果直接返回用户，不经过本地模型二次处理
```

#### 复杂问题预过滤
对于明确需要云端能力的复杂问题，直接预过滤到GLM，避免本地模型无效尝试：

| 关键词 | 问题类型 | 直接路由 |
|--------|----------|----------|
| 最新 | 时效性信息 | → GLM |
| 新闻 | 实时资讯 | → GLM |
| 查一下 | 信息检索 | → GLM |
| 搜索 | 网络搜索 | → GLM |
| 百科 | 知识问答 | → GLM |
| 怎么办 | 建议咨询 | → GLM |
| 解释 | 概念说明 | → GLM |
| 什么是 | 定义解释 | → GLM |
| 介绍一下 | 介绍说明 | → GLM |

#### 能力边界声明
System Prompt 中明确定义副官的能力边界，提示模型在无法回答时主动告知用户会使用云端能力协助。

### TODO 系统数据模型

```sql
CREATE TABLE todos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    due_date TEXT,
    status TEXT DEFAULT 'pending'  -- pending/completed
);
```

- **添加待办**：用户消息命中"提醒""别忘了"等关键词 → 后端拦截，不进入本地 LLM；
  - 先推送过渡语："正在翻阅您的行程计划，指挥官，请稍等……"
  - 调用 GLM-4-Flash 分析意图并提取内容与时间 → 写入 SQLite → 推送结果确认语（含截止时间）。
  - **重要**：TODO 流程的对话**不会写入短期历史**（chat_history/history.json），确保本地 LLM 不会感知 TODO 事件。
- **查询待办**：用户询问"有什么安排"等 → 同理拦截，GLM 判断为列表查询，必要时自动清理过期项并返回清单。
- **完成/删除**：仅支持前端面板手动操作（点击按钮），不通过自然语言指令执行。

### 时间感知注入

在构建 Promp 时，始终在系统提示末尾附加：

```
当前时间：2026年5月11日 星期一下午3点28分
```

短期记忆中的每条消息格式为：

```
[2026-05-11 15:23:01] 指挥官: 我刚才经过足球场...
[2026-05-11 15:23:15] 副官: 指挥官，那里现在热闹吗？
```

长期记忆条目元数据包含 `timestamp`，支持按时间过滤。

### 待办与记忆隔离原则
- 本地副官模型**不接触任何待办/约定类信息**；长期记忆库（ChromaDB）**不存储约定条目**。
- 所有待办识别、时间计算、过期处理全部由 GLM-4-Flash 在单次调用中完成。
- 用户发起的待办查询与添加请求，通过固定过渡语+结果语两段式回复交互，保证表达统一且不依赖本地模型生成。

---

## 统一MCP工具链架构设计

### 一、核心架构总览

采用"**多层意图检测+GLM精准执行**"架构，兼顾响应速度、准确性和用户体验。所有功能共享同一套分类、路由、状态管理和通信机制。

#### 1. 四层意图检测流程
```
用户输入 → 【第0层：TODO追问上下文追踪】
           ↓（无pending或已处理）
    【第1层：显式指令快速通道】
           ↓（未命中显式指令）
    【第2层：BGE嵌入语义匹配】
           ↓（高置信度直接路由）
           ├─ 高置信度单意图 → 直接执行工具
           ├─ 中等置信度TODO → 追问确认（GLM生成追问语）
           ├─ 多意图平局 → GLM二选一确认
           └─ 低置信度 → 进入第3层
    【第3层：关键词匹配后备】
           ↓（未命中）
    进入本地LLM正常对话流程
```

**关键优化**：
- **显式指令直达**：当用户输入包含明确工具关键词（如"提醒我"→todo）时，跳过语义匹配直接执行
- **语义相似度匹配**：使用 BGE 中文嵌入模型计算用户输入与各类别示例的相似度，支持模糊语义理解
- **TODO 追问机制**：当语义匹配判断可能是 TODO 但置信度不足时，主动询问用户确认
- **多意图平局处理**：当两个意图分数接近时，使用 GLM 做最终二选一

#### 2. 核心设计原则
- **分层决策**：简单明确的意图走快速通道，模糊意图走语义匹配，冲突意图走 GLM 裁决
- **记忆完全隔离**：所有MCP相关对话**不写入短期记忆、不送入长期记忆提取队列、本地模型完全不可见**
- **状态机复用**：所有MCP任务都在`transcribe_substate = "generating"`状态下执行，复用现有锁、取消事件和队列机制
- **统一错误处理**：所有工具的错误返回标准化格式，由GLM统一生成用户友好的错误提示
- **可插拔扩展**：新增工具只需添加意图示例、关键词规则和工具类，无需修改核心架构

### 二、BGE 嵌入语义匹配

使用 `bge-small-q8-zh-v1.5.gguf` 模型（GGUF 格式，约 100MB，加载时间 < 1 秒）进行语义相似度计算。

#### 1. 意图示例库
为每个工具类别预定义 15-20 条典型示例语句：
```python
INTENT_EXAMPLES = {
    "todo": ["提醒我明天下午三点开会", "别忘了买牛奶", ...],
    "weather": ["查询北京的天气怎么样", "上海会不会下雨", ...],
    "time_tool": ["现在几点了", "帮我倒计时五分钟", ...],
    "system_status": ["电脑状态怎么样", "CPU占用多少", ...],
    "web_search": ["帮我查一下量子计算是什么", ...],
    "normal": ["今天好累啊想早点休息", "晚饭吃什么好呢", ...]
}
```

#### 2. 相似度计算流程
1. 预计算每个意图类别的平均嵌入向量（启动时一次性计算）
2. 用户输入时，计算查询文本的嵌入向量
3. 计算与各类别平均向量的余弦相似度
4. 返回排序后的意图分数字典

#### 3. 置信度阈值
- **高置信度**（≥0.70，且与第二名差距≥0.08）：直接路由到对应工具
- **中等置信度**（≥0.55）：针对 TODO 意图触发追问确认
- **低置信度**（<0.55）：进入关键词后备层或回退到正常对话

### 三、显式指令快速通道

维护显式关键词到工具的映射，支持参数预提取：
```python
EXPLICIT_ROUTES = [
    (["提醒我", "别忘了", "记一下"], "todo", {"sub_op": "add"}),
    (["待办列表", "有什么安排"], "todo", {"sub_op": "list"}),
    (["天气", "会下雨", "温度多少"], "weather", {}),
    (["现在几点", "今天几号"], "time_tool", {"sub_op": "current_time"}),
    (["电脑状态", "CPU占用"], "system_status", {"sub_op": "all"}),
    (["帮我查", "搜索一下"], "web_search", {}),
]
```

### 四、TODO 追问上下文追踪

当语义匹配判断用户可能在说 TODO 但置信度不足（0.55-0.70）时：

1. **生成追问语**：调用 GLM-4-Flash 生成自然询问（如"指挥官是指需要我记录这个提醒吗？"）
2. **设置 pending 上下文**：保存原始消息和 TTL（生存时间，默认 3 轮）
3. **等待用户确认**：
   - 肯定词（"是的"、"好"、"ok"等）+ TODO 语义分数 > 0.35 → 执行 TODO 添加
   - 否定词（"不用了"、"算了"等）→ 清除上下文，继续正常路由
   - TTL 耗尽（用户 3 轮未确认）→ 自动清除上下文

### 五、GLM 二选一分类器

当两个意图的分数接近（差距 < 0.08）且都达到中等置信度时：
```
用户输入: "今天天气怎么样，顺便提醒我明天开会"
语义匹配: weather=0.72, todo=0.68 (差距 0.04 < 0.08)
→ 调用 GLM 二选一
→ 输出 A 或 B
→ 执行对应工具
```

### 六、MCP 任务分发器

根据意图检测结果，将任务分发到对应的工具处理函数：

| 工具类别 | 处理类 | 数据源 | 特殊说明 |
|----------|--------|--------|----------|
| todo | TodoTool | SQLite本地数据库 | 支持追问确认机制 |
| weather | WeatherTool | 和风天气QWeather API | 支持 9 种子操作 |
| system_status | SystemTool | psutil库 | 实时系统状态 |
| time_tool | TimeTool | 系统时间 | 支持倒计时/计时器 |
| web_search | WebSearchTool | 百度千帆搜索API | 需配置 API Key |

---

## 天气查询系统详细设计

### 一、用户场景分类与子操作映射

采用"**语义场景+时间维度+信息类型**"三维度判断体系：

| 场景大类 | 典型用户话术 | 映射子操作 | 优先级 |
|----------|--------------|------------|--------|
| 即时状态感知 | "外面冷不冷？""现在热吗？" | now | 最高 |
| 当日完整预报 | "今天天气怎么样？" | today | 高 |
| 次日预报 | "明天会下雨吗？" | tomorrow | 高 |
| 多日趋势预报 | "这周天气怎么样？" | week | 中 |
| 小时级精准预报 | "今天下午几点下雨？" | hour | 中 |
| 空气质量专项 | "今天空气质量怎么样？" | air | 中 |
| 灾害预警查询 | "有没有台风预警？" | warning | 高（安全优先） |
| 天文信息查询 | "今天几点日出？" | astronomy | 低 |
| 生活决策辅助 | "今天适合洗车吗？""穿什么？" | indices | 高 |

### 二、和风天气API映射

| 子操作 | API接口 | 核心字段 | 缓存时间 |
|--------|---------|----------|----------|
| now | v7/weather/now | temp, text, windDir, windScale, humidity | 10分钟 |
| today/tomorrow | v7/weather/3d | tempMin, tempMax, textDay, textNight | 1小时 |
| week | v7/weather/7d | 每日tempMin, tempMax, textDay | 6小时 |
| hour | v7/weather/24h | 未来24小时temp, text, time | 30分钟 |
| air | v7/air/now | aqi, category, pm2p5, pm10 | 30分钟 |
| warning | v7/warning/now | title, level, text | 5分钟 |
| astronomy | v7/astronomy/sun | sunrise, sunset | 24小时 |
| indices | v7/indices/1d | typeName, level, text | 6小时 |

### 三、生活指数细化方案

#### 1. indices_type提取逻辑

| 用户输入关键词 | 映射的indices_type |
|---------------|-------------------|
| 穿什么、穿衣、外套、穿衣服 | 穿衣 |
| 紫外线、防晒 | 紫外线 |
| 感冒、容易生病、着凉 | 感冒 |
| 洗车 | 洗车 |
| 钓鱼 | 钓鱼 |
| 运动、锻炼、跑步、健身 | 运动 |
| 晾晒、晒被子、晒衣服 | 晾晒 |
| 旅游、出行、出去玩 | 旅游 |
| 无以上关键词 | 全部 |

#### 2. 分级返回策略

- **具体类型**（如"穿衣"、"洗车"）：只返回该指数单条结果，TTS约3秒
  - 格式：【{location}今日{indices_type}指数】+ 等级 + 建议

- **全部**（仅用户泛问"生活指数"时触发）：返回穿衣+紫外线+感冒三个最常用指数摘要，TTS约8秒

### 四、副官风格回复模板

| 子操作 | 回复格式 |
|--------|----------|
| now | 【{location}实时天气】天气：{text} 气温：{temp}℃ 风向：{windDir} {windScale}级 湿度：{humidity}% |
| today | 【{location}今日预报】白天：{textDay}，{tempMax}℃ 夜间：{textNight}，{tempMin}℃ |
| air | 【{location}实时空气质量】AQI：{aqi}（{category}）PM2.5：{pm2p5}μg/m³ |
| warning | ⚠️【{location}灾害预警】预警类型：{title} 预警等级：{level} |
| indices | 【{location}今日{indices_type}指数】等级：{category} 建议：{text} |

### 五、异常处理

| 场景 | 处理方式 |
|------|----------|
| API调用失败 | "指挥官，天气服务暂时不可用，请稍后再试。" |
| 地点不存在 | "指挥官，未查询到{location}的天气信息，请确认地点名称是否正确。" |
| 无预警信息 | "指挥官，{location}当前无任何灾害预警。" |
| 缓存命中 | "指挥官，这是最新的天气信息。" |

---

## 设置与 API Key 管理

### 功能概述
设置面板用于集中管理应用的敏感配置信息，包括 API Key 等，确保这些信息不再硬编码在后端代码中，而是由用户自行输入并本地持久化存储。

### 管理项

| 配置项 | 说明 | 必填 | 用途 |
|--------|------|------|------|
| GLM API Key | 智谱 GLM-4-Flash API 密钥 | 是 | AI 对话、记忆提取、TODO 处理 |
| 和风天气 API Key | 和风天气 API 密钥 | 是 | 天气查询功能 |
| 和风天气 API Host | 和风天气 API 域名 | 是 | 天气查询功能 |
| 默认城市 | 天气查询默认城市 | 否 | AI 天气查询及面板默认展示 |

### 持久化机制
- 前端使用 `localStorage` 本地存储设置数据
- 应用启动时自动加载本地设置并同步到后端
- 设置变更后立即保存并推送到后端

### API Key 测试功能
- 在设置面板中为 GLM 和和风天气分别提供测试按钮
- 测试结果通过 `api_key_test_result` 事件返回前端
- 测试通过后才允许保存设置

### 缺失值处理
- 应用启动时检查各项必填配置
- 若存在缺失，通过警告提示用户前往设置补充
- AI 对话和天气查询功能会根据缺失的 Key 返回对应提示

### 前后端同步
```
前端 (useSettings.ts) ←→ 后端 (backend.py)
     ↓                        ↓
  localStorage           全局状态
```

---

## 版本渐进路线

- **v1.0**：基础语音交互 + 短期记忆（已完成）。
- **v2.0**：混合长期记忆 + 基础时间感知。
- **v2.1**：结构化 TODO 系统 + 记忆时间范围检索 + 前端 TODO 面板。
- **v2.2**：统一MCP架构 + 天气查询系统 + 系统状态查询 + 时间工具 + **API Key 本地管理（设置面板）**。
- **v2.3**：**BGE 嵌入语义匹配** + **TODO 追问确认机制** + **多意图平局处理** + **GGUF 格式 BGE 模型**（当前版本）。
- **v2.4**：周期性提醒、自我反思记忆、工具调用扩展。
---
