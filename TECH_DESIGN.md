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

## 技术栈

| 模块 | 技术选型 | 核心依赖 |
|------|----------|----------|
| 前端 | Electron + Vue3 + TypeScript + Vite | - |
| 后端 | Python 3.10（Windows Embeddable Package） | vosk、sounddevice、llama-cpp-python、torch、kokoro、chromadb、openai |
| 语音唤醒/转写 | Vosk | vosk-model-small-cn |
| AI 对话 | Llama.cpp | qwen2_5_3b-instruct-q4_k_m-LOT.gguf |
| 长期记忆 | ChromaDB（向量库） + 智谱 GLM-4-Flash API（记忆提取） | chromadb、openai SDK |
| TODO 管理 | SQLite 本地数据库 | sqlite3 |
| 语音合成（TTS） | Kokoro-82M + OnnxRuntime | kokoro-v1_1-zh.onnx |
| 打包工具 | electron-builder（前端） | - |

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
│   │   ├── TodoPanel.vue       # 待办事项面板（计划）
│   │   └── StatusBar.vue
│   ├── composables/     # 组合式函数
│   │   ├── useBackend.ts
│   │   ├── useChat.ts
│   │   └── useTTS.ts
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
- **自动截断**：每次本地 LLM 生成回复前，会检查 token 数量，若接近上下文窗口限制（90%），自动删除最旧的消息（仅影响内存，不影响文件）
- **手动清理**：用户点击"清理历史"按钮时，清空内存和文件中的所有短期历史
- **不进入短期历史**：TODO 对话和彩蛋对话不会写入 chat_history，确保本地 LLM 不会感知这些事件

#### 长期记忆提取
- 普通对话完成后，若满足提取条件（每 N 轮或包含"记住"等关键词），将对话送入 GLM 提取关键信息
- TODO 对话和彩蛋对话**不会**进入长期记忆提取流程
- 长期记忆在每次对话时检索相关条目，注入到 prompt 中供 LLM 使用

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

## 版本渐进路线

- **v1.0**：基础语音交互 + 短期记忆（已完成）。
- **v2.0**：混合长期记忆 + 基础时间感知。
- **v2.1**：结构化 TODO 系统 + 记忆时间范围检索 + 前端 TODO 面板。
- **v2.3**：周期性提醒、自我反思记忆、工具调用扩展。

---
