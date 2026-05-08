# 阿塔尼斯 AI 语音助手（泰伦帝国副官版）
基于 Electron + Vue3 + TypeScript + Python 开发的桌面端 AI 语音助手，人设为《星际争霸 2》泰伦帝国机械副官，支持语音唤醒、语音转写、AI 对话、语音合成（TTS）全流程交互。

## 核心功能
1. **语音唤醒**：后台静默运行，通过预设唤醒词（支持拼音模糊匹配）唤出应用窗口；
2. **语音转写**：按住按钮录音，松开后自动转写为文字并填入输入框，支持手动修正；
3. **AI 对话**：基于 Qwen2.5-3B 模型，支持流式输出、本次会话短期记忆、跨会话历史记忆；
4. **语音合成（TTS）**：基于 Kokoro-82M 模型，AI 回复同时自动播报，支持手动停止/重新播报；
5. **纯 CPU 运行**：无需独立 GPU，适配普通办公电脑。

## 技术栈
| 模块 | 技术选型 | 核心依赖 |
|------|----------|----------|
| 前端 | Electron + Vue3 + TypeScript + Vite | - |
| 后端 | Python 3.10（Windows Embeddable Package） | vosk、sounddevice、llama-cpp-python、torch、kokoro |
| 语音唤醒/转写 | Vosk | vosk-model-small-cn |
| AI 对话 | Llama.cpp | qwen2_5_3b-instruct-q4_k_m-LOT.gguf |
| 语音合成（TTS） | Kokoro-82M | kokoro-v1_1-zh.onnx |
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
    ├── backend.exe     # 后端
    ├── history.json      # 对话历史持久化
    └── models/           # 模型文件
        ├── vosk-model-small-cn/
        ├── qwen1_5_1_8b-chat-q4_k_m.gguf
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
transcribe_substate: "idle" | "generating" | "playing_tts"
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
    ├─ 推送 partial_ready → 前端秒开窗口
    └─ 后台模型加载线程（异步）
        ├─ 加载唤醒模型 → 推送 wake_model_loaded
        ├─ 加载转写模型 → 推送 transcribe_model_loaded
        ├─ 加载 LLM 模型 → 推送 llm_model_loaded
        ├─ 加载 TTS 模型 → 推送 tts_model_loaded
        └─ 全量加载完成 → 推送 full_ready → 加载 history.json
启动守护线程：唤醒监听 / LLM 推理 / TTS 播报
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
  - `tts_play`：手动播报 → 放入 `tts_request_queue` → 切换 `tts_substate=playing`；
  - `set_mode=wake`：关闭窗口 → 切回 `wake`。

#### 子状态 4.2：transcribe_substate = "generating"（AI 生成中）
- **状态**：交互锁定，仅允许取消生成；
- **持续动作**：LLM 流式生成 → 推送 `chat_chunk` → 累计片段放入 `tts_request_queue`（逐段播报策略）；
- **流转**：
  - 生成完成 → 追加历史 → 持久化 → 推送 `chat_complete` → 切换 `playing_tts`（如有未播 TTS）或 `idle`；
  - 用户取消 → 触发 `cancel_generation_event` + `cancel_tts_event` → 切换 `idle`。

#### 子状态 4.3：transcribe_substate = "playing_tts"（TTS 播报中）
- **状态**：交互锁定，仅允许停止播报/关闭窗口；
- **持续动作**：TTS 线程从 `tts_request_queue` 取文本 → 合成音频 → 播放；
- **流转**：
  - 播报完成 → 推送 `tts_complete` → 切换 `idle`；
  - 用户停止 → 触发 `cancel_tts_event` → 清空队列 → 切换 `idle`。

## 前后端通信协议
### 前端 → 后端（指令）
| 指令              | 参数                         | 说明         |
| ----------------- | ---------------------------- | ------------ |
| set_mode          | mode: "wake" \| "transcribe" | 切换顶层状态 |
| transcribe_file   | file_path: str               | 语音转写     |
| send_message      | content: str                 | 发送对话     |
| cancel_generation | -                            | 取消生成     |
| tts_play          | text: str                    | 手动播报     |
| tts_stop          | -                            | 停止播报     |
| clear_history     | -                            | 清空历史     |
| get_history       | -                            | 获取历史     |

### 后端 → 前端（事件）
| 事件                    | 参数                | 说明             |
| ----------------------- | ------------------- | ---------------- |
| partial_ready           | -                   | 后端启动完成     |
| wake_model_loaded       | -                   | 唤醒模型加载完成 |
| transcribe_model_loaded | -                   | 转写模型加载完成 |
| llm_model_loaded        | -                   | LLM 模型加载完成 |
| tts_model_loaded        | -                   | TTS 模型加载完成 |
| full_ready              | -                   | 全量加载完成     |
| wake                    | -                   | 检测到唤醒词     |
| transcription_result    | text: str           | 转写结果         |
| chat_chunk              | content: str        | LLM 流式片段     |
| chat_complete           | -                   | 生成完成         |
| chat_cancelled          | -                   | 生成已取消       |
| tts_started             | -                   | TTS 开始播报     |
| tts_stopped             | -                   | TTS 已停止       |
| tts_complete            | -                   | TTS 播报完成     |
| history_loaded          | history: list       | 对话历史         |
| history_cleared         | -                   | 历史已清空       |
| error                   | type: str, msg: str | 错误信息         |
