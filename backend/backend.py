import sys
import io
import json
import re
import threading
import queue
import os
import time
import datetime
import sqlite3
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import pypinyin
import wave
import gc
from llama_cpp import Llama

from misaki import zh
from kokoro_onnx import Kokoro

# 长期记忆与记忆提取
import chromadb
from chromadb.config import Settings as ChromaSettings
from openai import OpenAI
import difflib

# MCP统一工具链
from mcp import MCPManager

# ------------------------------
# 配置标准流为 UTF-8 编码
# 关键：使用 reconfigure() 而非重新包装 TextIOWrapper
# 重新包装会导致双重缓冲——当 Electron 通过管道 (pipe) 启动后端时，
# Python 层的 TextIOWrapper 缓冲和 C 扩展层 (llama.cpp) 的 stderr 缓冲
# 共享同一个 OS 管道文件描述符，可能造成管道缓冲区死锁，
# 导致 llama.cpp 在加载模型时挂起。
# reconfigure() 只修改已有 TextIOWrapper 的属性，不会创建新的缓冲层。
_original_stdin = sys.stdin
_original_stdout = sys.stdout
_original_stderr = sys.stderr

_streams_configured = False
for _stream, _name in [(sys.stdin, 'stdin'), (sys.stdout, 'stdout'), (sys.stderr, 'stderr')]:
    try:
        _stream.reconfigure(encoding='utf-8', errors='replace')
        _streams_configured = True
    except AttributeError:
        # Python < 3.7 不支持 reconfigure，回退到重新包装
        pass

if not _streams_configured:
    # 回退方案：重新包装（注意：这在管道模式下可能导致缓冲问题）
    sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# ================= 全局常量配置 =================
LLM_N_CTX = 8192
LLM_N_THREADS = 8
LLM_N_BATCH = 512
LLM_TEMPERATURE = 0.9
LLM_MAX_TOKENS = 256
LLM_CHAT_FORMAT = "qwen"
LLM_TOP_P = 0.9
LLM_REPEAT_PENALTY = 1.2

SYSTEM_PROMPT = """你是泰伦帝国001号高级机械副官。
- 称呼用户为"指挥官"
- 军旅干练，带一点冷幽默
- 将日常琐事类比为战术行动
- 回复2-4句话，40-80字
- 绝对不要输出"副官："或任何角色前缀

【能力边界】
你能做的：日常聊天、角色扮演、情感陪伴、简单问答
你不能做的：数学计算、逻辑推理、事实性知识、复杂指令
如果你遇到不能做的事，必须只说一句话："指挥官，我需要查询帝国数据库，请稍候。"

【记忆使用规范】
当系统消息中提供了以下记忆信息时，你必须严格遵守：
- "关于指挥官的已知信息"：记录着指挥官本人的客观事实。当指挥官询问关于他自己的问题时，你必须据此回答，不要说你不知道。
- "指挥官近期的关键事件"：记录指挥官个人经历的事件。当指挥提起时，你可以像朋友一样提及。
- **关键**：这些信息是关于指挥官的，不是你（副官）的。绝不能把自己代入。例如，不能说"我今天参加了会议"，而应该说"根据记录，指挥官您今天参加了会议"。
"""

WAKE_WORDS = [
    "你好副官", "启动助手", "qi dong",
    "副官", "指挥官", "智能",
    "fu guan", "fu huan", "bu guan","hu guan", "zhi hui guan", "zhi neng",
    "零零一号", "零零一", "ling ling yi", "lian yi"
]

TTS_SPEED = 1.15
TTS_VOICE_NAME = "zf_001"          # kokoro_onnx 支持的声音名称
STREAM_CHUNK_DELIMITERS = ("。", "！", "？", "…", "\n", "\r")
STREAM_CHUNK_MIN_LEN = 10
STREAM_CHUNK_MAX_LEN = 100

# ================= 路径配置 =================
def get_base_path():
    if getattr(sys, 'frozen', False):
        return sys._MEIPASS
    return os.path.dirname(os.path.abspath(__file__))

def get_data_path():
    if sys.platform == 'win32':
        appdata = os.getenv('APPDATA')
        data_dir = os.path.join(appdata, 'ArtanisAI')
    else:
        home = os.path.expanduser('~')
        data_dir = os.path.join(home, '.artanisai')
    os.makedirs(data_dir, exist_ok=True)
    return data_dir

BASE_DIR = get_base_path()
DATA_DIR = get_data_path()

WAKE_MODEL_PATH = os.path.join(BASE_DIR, "models", "vosk-model-small-cn")
TRANSCRIBE_MODEL_PATH = os.path.join(BASE_DIR, "models", "vosk-model-small-cn")
LLM_MODEL_PATH = os.path.join(BASE_DIR, "models", "qwen2.5-3b-it-Q4_K_M-LOT.gguf")

# TTS 新模型文件路径 (onnx + bin + config)
TTS_ONNX_PATH = os.path.join(BASE_DIR, "models", "kokoro-zh/kokoro-v1.1-zh.onnx")
TTS_VOICES_BIN_PATH = os.path.join(BASE_DIR, "models", "kokoro-zh/voices-v1.1-zh.bin")
TTS_CONFIG_PATH = os.path.join(BASE_DIR, "models", "kokoro-zh/config.json")

# 彩蛋配置文件
EASTER_EGG_RULES_PATH = os.path.join(BASE_DIR, "config", "easter_egg_rules.json")

HISTORY_FILE_PATH = os.path.join(DATA_DIR, "history.json")
MEMORY_DB_PATH = os.path.join(DATA_DIR, "memory_db")
TODO_DB_PATH = os.path.join(DATA_DIR, "todo.db")

# 记忆提取配置
ZHIPU_API_KEY = os.environ.get("ZHIPU_API_KEY", "")
MEMORY_EXTRACTION_INTERVAL = 3   # 每3轮自动提取一次

# ================= 线程安全锁与全局状态 =================
state_lock = threading.Lock()
chat_lock = threading.Lock()
generation_lock = threading.Lock()
cancel_generation_event = threading.Event()
model_loading_started = False

audio_queue = queue.Queue()
chat_request_queue = queue.Queue()
tts_queue = queue.Queue()
cancel_tts_event = threading.Event()

stream_active = threading.Event()

# 致命错误事件（模型加载失败时设置，主线程检测后退出）
fatal_error_event = threading.Event()

# 顶层状态
current_mode = "wake"
transcribe_substate = "idle"

# TTS 播放状态
tts_busy = False
tts_session_active = False

# 全局模型实例
wake_model = None
wake_rec = None
transcribe_model = None
llm = None

# TTS 新实例
tts_g2p = None
tts_kokoro = None

# 记忆与待办管理器
memory_manager = None
todo_manager = None
mcp_manager = None

chat_history = []

# ================= 彩蛋系统全局状态 =================
easter_egg_enabled = True          # 彩蛋总开关，默认开启
easter_egg_rules = []              # 从 JSON 加载的规则列表

# ================= 用户设置存储 =================
user_settings = {
    "glm_api_key": "",
    "qweather_api_key": "",
    "qweather_api_host": "",
    "default_city": "北京"
}

# ================= 工具函数 =================
def fuzzy_match_wake_word(text):
    text_pinyin = " ".join(pypinyin.lazy_pinyin(text)).lower()
    text_lower = text.lower()
    for wake_word in WAKE_WORDS:
        if (wake_word in text_lower) or (wake_word in text_pinyin):
            return wake_word
    return None

def send_msg_to_electron(msg_dict):
    try:
        msg_json = json.dumps(msg_dict, ensure_ascii=False) + '\n'
        sys.stdout.buffer.write(msg_json.encode('utf-8'))
        sys.stdout.buffer.flush()
    except Exception as e:
        print(f"[Backend] 发送消息失败: {e}", file=sys.stderr)

def load_chat_history():
    history_to_send = []
    with chat_lock:
        try:
            if os.path.exists(HISTORY_FILE_PATH):
                with open(HISTORY_FILE_PATH, 'r', encoding='utf-8') as f:
                    global chat_history
                    chat_history = json.load(f)
                for msg in chat_history:
                    if "content" in msg and isinstance(msg["content"], str):
                        msg["content"] = msg["content"].encode('utf-8', errors='replace').decode('utf-8')
                print(f"[Backend] 对话历史加载完成，共{len(chat_history)}轮对话", file=sys.stderr)
            else:
                chat_history = []
            history_to_send = chat_history.copy()
        except Exception as e:
            print(f"[Backend] 对话历史加载失败: {e}", file=sys.stderr)
            chat_history = []
    send_msg_to_electron({"event": "history_loaded", "history": history_to_send})

def save_chat_history():
    with chat_lock:
        try:
            with open(HISTORY_FILE_PATH, 'w', encoding='utf-8') as f:
                json.dump(chat_history, f, ensure_ascii=False, indent=2)
            print(f"[Backend] 对话历史已保存", file=sys.stderr)
        except Exception as e:
            print(f"[Backend] 对话历史保存失败: {e}", file=sys.stderr)

def truncate_chat_history():
    max_rounds = 5
    if len(chat_history) > max_rounds * 2:
        with chat_lock:
            chat_history[:] = chat_history[-(max_rounds * 2):]
        print(f"[Backend] 对话历史已截断，保留最近{max_rounds}轮", file=sys.stderr)

def clear_audio_queue():
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

# ================= 彩蛋系统核心函数 =================
def load_easter_egg_rules():
    global easter_egg_rules
    if os.path.exists(EASTER_EGG_RULES_PATH):
        try:
            with open(EASTER_EGG_RULES_PATH, 'r', encoding='utf-8') as f:
                data = json.load(f)
                easter_egg_rules = data.get("rules", [])
            print(f"[Backend] 彩蛋规则加载完成，共{len(easter_egg_rules)}条规则", file=sys.stderr)
        except Exception as e:
            print(f"[Backend] 彩蛋规则加载失败: {e}", file=sys.stderr)
            easter_egg_rules = []
    else:
        print("[Backend] 未找到彩蛋规则文件，彩蛋功能暂时不可用", file=sys.stderr)
        easter_egg_rules = []

def match_easter_egg(user_input: str):
    """
    按优先级匹配彩蛋规则，返回命中的规则字典或 None。
    优先级: exact > scene_keyword > simple_keyword
    """
    # 按优先级分组
    exact_rules = [r for r in easter_egg_rules if r.get("type") == "exact"]
    scene_rules = [r for r in easter_egg_rules if r.get("type") == "scene_keyword"]
    simple_rules = [r for r in easter_egg_rules if r.get("type") == "simple_keyword"]

    # 1. 精准匹配
    for rule in exact_rules:
        match_cfg = rule.get("match", {})
        texts = match_cfg.get("texts", [])
        if user_input in texts:
            print(f"[EasterEgg] 精准命中: {rule['id']}", file=sys.stderr)
            return rule

    # 2. 场景关键词匹配
    for rule in scene_rules:
        match_cfg = rule.get("match", {})
        core_keywords = match_cfg.get("core_keywords", [])
        aux_keywords = match_cfg.get("aux_keywords", [])
        min_core = match_cfg.get("min_core", 1)
        min_aux = match_cfg.get("min_aux", 1)
        core_hits = sum(1 for kw in core_keywords if kw in user_input)
        aux_hits = sum(1 for kw in aux_keywords if kw in user_input)
        if core_hits >= min_core and aux_hits >= min_aux:
            print(f"[EasterEgg] 场景关键词命中: {rule['id']} (核心{core_hits}/{min_core}, 辅助{aux_hits}/{min_aux})", file=sys.stderr)
            return rule

    # 3. 简化关键词匹配
    for rule in simple_rules:
        match_cfg = rule.get("match", {})
        keywords = match_cfg.get("keywords", [])
        min_hits = match_cfg.get("min_hits", 1)
        hits = sum(1 for kw in keywords if kw in user_input)
        if hits >= min_hits:
            print(f"[EasterEgg] 简化关键词命中: {rule['id']} ({hits}/{min_hits})", file=sys.stderr)
            return rule
    return None

# ================= 音频转写核心函数 =================
def vosk_transcribe_audio(audio_file_path, model):
    try:
        with wave.open(audio_file_path, "rb") as wf:
            channels = wf.getnchannels()
            sampwidth = wf.getsampwidth()
            framerate = wf.getframerate()
            if channels != 1 or sampwidth != 2 or framerate != 16000:
                print("[Backend] 音频格式错误", file=sys.stderr)
                return ""
            rec = KaldiRecognizer(model, 16000)
            rec.SetWords(True)
            result_text = ""
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    res = json.loads(rec.Result())
                    result_text += res.get("text", "")
            final_res = json.loads(rec.FinalResult())
            result_text += final_res.get("text", "")
            return result_text.replace(" ", "")
    except Exception as e:
        print(f"[Backend] 音频转录错误: {e}", file=sys.stderr)
        raise

# ================= 音频回调（唤醒模式） =================
def audio_callback(indata, frames, time_info, status):
    if status:
        print(status, file=sys.stderr)
    audio_queue.put(bytes(indata))

# ================= 唤醒监听线程 =================
def wake_listener_thread():
    global current_mode, wake_rec, transcribe_substate
    while True:
        if wake_rec is None:
            time.sleep(0.2)
            continue
        with state_lock:
            is_wake_mode = (current_mode == "wake")
        if not is_wake_mode:
            time.sleep(0.1)
            continue
        print("[Backend] 启动唤醒监听...", file=sys.stderr)
        stream_active.set()
        try:
            with sd.RawInputStream(
                samplerate=16000,
                blocksize=8000,
                dtype='int16',
                channels=1,
                callback=audio_callback
            ):
                while True:
                    if wake_rec is None:
                        break
                    with state_lock:
                        if current_mode != "wake" or not stream_active.is_set():
                            break
                    try:
                        data = audio_queue.get(timeout=0.1)
                    except queue.Empty:
                        continue
                    if wake_rec.AcceptWaveform(data):
                        result = json.loads(wake_rec.Result())
                        text = result.get("text", "").replace(" ", "")
                        if text and fuzzy_match_wake_word(text):
                            print(f"[Backend] 唤醒成功 | 识别文本: {text}", file=sys.stderr)
                            send_msg_to_electron({"event": "wake"})
                            with state_lock:
                                current_mode = "transcribe"
                                transcribe_substate = "idle"
                                stream_active.clear()
                            wake_rec.Reset()
                            clear_audio_queue()
                            break
                print("[Backend] 唤醒监听停止，麦克风已关闭", file=sys.stderr)
        except Exception as e:
            print(f"[Backend] 音频流错误: {e}", file=sys.stderr)
            time.sleep(1)

def _is_valid_date_str(date_str):
    """检查日期字符串是否为合法的 YYYY-MM-DD HH:MM 或 YYYY-MM-DD 格式。"""
    if not date_str or not isinstance(date_str, str):
        return False
    m = re.match(r'^(\d{4})-(\d{2})-(\d{2})(?:\s+(\d{2}):(\d{2}))?$', date_str.strip())
    if not m:
        return False
    try:
        year, month, day = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if m.group(4):
            hour, minute = int(m.group(4)), int(m.group(5))
            datetime.datetime(year, month, day, hour, minute)
        else:
            datetime.datetime(year, month, day)
        return True
    except ValueError:
        return False

# ================= 长期记忆管理器 =================
class MemoryManager:
    def __init__(self, db_path: str, api_key: str):
        if not api_key:
            print("[记忆] 未设置 ZHIPU_API_KEY，长期记忆提取功能不可用", file=sys.stderr)
            self.enabled = False
            self.collection = None
            return
        self.enabled = True
        os.makedirs(db_path, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=ChromaSettings(
                cache_capacity=1000,
                anonymized_telemetry=False
            )
        )
        try:
            self.collection = self.client.get_or_create_collection(
                name="commander_memories",
                metadata={"hnsw:space": "cosine"}
            )
        except Exception:
            # 兼容旧版本 chromadb
            self.collection = self.client.get_or_create_collection(name="commander_memories")
        self.zhipu_client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
        self.extraction_queue = []
        self.extraction_lock = threading.Lock()
        self.collection_lock = threading.Lock()
        self.extraction_thread = threading.Thread(target=self._extraction_worker, daemon=True)
        self.extraction_thread.start()
        self.extraction_counter = 0
        self.extraction_interval = MEMORY_EXTRACTION_INTERVAL  # 每3轮自动提取一次
        self.force_keywords = ["记住", "一定要记住", "这个很重要"]
        print("[记忆] 长期记忆管理器已就绪，后台提取线程已启动", file=sys.stderr)

    def add_conversation_to_queue(self, messages: list, timestamp: float = None):
        if not self.enabled:
            return
        if timestamp is None:
            timestamp = time.time()
        with self.extraction_lock:
            self.extraction_queue.append((messages, timestamp)) # 存入元组

    def retrieve_relevant(self, query: str, k: int = 3, after: float = None, before: float = None) -> list:
        if not self.enabled or self.collection.count() == 0:
            return []
        where_filter = {}
        if after is not None:
            where_filter["timestamp"] = where_filter.get("timestamp", {})
            where_filter["timestamp"]["$gte"] = after
        if before is not None:
            where_filter["timestamp"] = where_filter.get("timestamp", {})
            where_filter["timestamp"]["$lte"] = before
        with self.collection_lock:
            try:
                if where_filter:
                    results = self.collection.query(query_texts=[query], n_results=k, where=where_filter)
                else:
                    results = self.collection.query(query_texts=[query], n_results=k)
                memories = []
                for i, doc in enumerate(results['documents'][0]):
                    if results['distances'][0][i] < 1.5:
                        memories.append(doc)
                return memories
            except Exception as e:
                print(f"[记忆] 检索失败: {e}", file=sys.stderr)
                return []

    def get_all_memories(self) -> list:
        if not self.enabled or self.collection.count() == 0:
            return []
        with self.collection_lock:
            return self.collection.get()['documents']

    def _extraction_worker(self):
        while True:
            time.sleep(5)
            with self.extraction_lock:
                if not self.extraction_queue:
                    continue
                batch = self.extraction_queue[:]
                self.extraction_queue.clear()
            for conv, conv_ts in batch:
                try:
                    memories = self._extract_memories(conv, conv_ts)
                    for mem in memories:
                        if isinstance(mem, dict):
                            text = mem.get("content", "")
                            importance = mem.get("importance", 5)
                            mem_ts = mem.get("timestamp", conv_ts)
                            self._add_memory(text, mem_ts, importance)
                        else:
                            self._add_memory(mem, conv_ts)
                except Exception as e:
                    print(f"[记忆] 提取失败: {e}", file=sys.stderr)

    def _extract_memories(self, conversation: list, conv_timestamp: float = None):
        conv_text = "\n".join([f"{msg['role']}: {msg['content']}" for msg in conversation])
        # 格式化对话时间
        time_context = ""
        timestamp_str = ""
        if conv_timestamp:
            dt = datetime.datetime.fromtimestamp(conv_timestamp)
            time_context = f"对话发生时间：{dt.strftime('%Y年%m月%d日 %H:%M')}"
            timestamp_str = dt.strftime('%Y年%m月%d日 %H:%M')
        system_prompt = f"""你是一个陪伴型AI的记忆提取专家，像真正的朋友一样从对话中提取所有可能有长期价值的信息。
{time_context}

## 必须记住的内容（优先级从高到低）
1. 用户的个人属性：姓名、年龄、职业、年级、学校、专业、家人、宠物
2. 用户的喜好与禁忌：喜欢吃什么、讨厌什么、喜欢的音乐/电影/游戏、过敏史
3. 用户的习惯与规律：作息、饮食、日常活动
4. 用户的重要计划：考试、面试、会议、旅行、约会、生日、节日
5. 用户的重要事件：生病、获奖、挫折、开心/难过的事
6. 用户明确表达的观点和态度

## 绝对不能记住的内容
1. 天气、时间、温度等客观事实
2. 副官自己说的话、提问、建议
3. 无关紧要的寒暄："你好"、"好的"、"谢谢"、"再见"
4. 用户的临时抱怨和情绪发泄
5. 重复的信息（只更新时间）
6. 任何MCP工具的回复内容（待办、天气、系统状态等）

## 输出要求
严格输出JSON，无其他内容。无值得记忆的内容返回{{"memories": []}}
{{
  "memories": [
    {{
      "type": "attribute|preference|habit|plan|event|opinion",
      "content": "简洁明了的记忆内容，不超过50字",
      "importance": 5,
      "timestamp": "{timestamp_str}"
    }}
  ]
}}"""
        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"对话内容：\n{conv_text}\n\n请提取其中的关键记忆。"}
                ],
                temperature=0.2,
                max_tokens=500
            )
            raw = response.choices[0].message.content
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(raw[json_start:json_end])
                return data.get("memories", [])
            return []
        except Exception as e:
            print(f"[记忆] 智谱API调用出错: {e}", file=sys.stderr)
            return []

    def _add_memory(self, text: str, timestamp: float = None, importance: int = 5):
        if importance < 3:
            return
        if timestamp is None:
            timestamp = time.time()
        with self.collection_lock:
            existing = self.collection.get()['documents']
            if any(self._is_similar(text, m) for m in existing):
                return
            mem_id = f"mem_{hash(text)}_{int(timestamp)}"
            self.collection.add(documents=[text], ids=[mem_id], metadatas=[{"timestamp": timestamp, "importance": importance}])
            print(f"[记忆] 已存储: {text} (重要性={importance})", file=sys.stderr)

    def _is_similar(self, a: str, b: str, threshold: float = 0.8) -> bool:
        return difflib.SequenceMatcher(None, a, b).ratio() > threshold

    def should_extract(self, user_message: str) -> bool:
        """根据计数器和用户消息中的关键词判断是否需要提取记忆"""
        if any(kw in user_message for kw in self.force_keywords):
            self.extraction_counter = 0   # 触发后重置计数器，避免短期内重复提取
            return True
        self.extraction_counter += 1
        if self.extraction_counter >= self.extraction_interval:
            self.extraction_counter = 0
            return True
        return False

    def analyze_todo_only(self, user_message: str, timestamp: float = None):
        """
        纯 TODO 分析，不提取任何长期记忆。
        返回 todo_action dict 或 None。
        """
        if not self.enabled:
            return None

        if timestamp is None:
            timestamp = time.time()

        now = datetime.datetime.fromtimestamp(timestamp)
        weekday_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        current_time_str = now.strftime("%Y年%m月%d日") + f" {weekday_zh[now.weekday()]} " + now.strftime("%H:%M")
        # 添加日期参考表
        try:
            from mcp.tools.time_resolver import build_date_reference, pre_resolve_message
            current_time_str += "\n日期参考：" + build_date_reference(now)

            # 预解析用户消息中的相对时间
            resolved_info = pre_resolve_message(user_message, now)
            user_message_for_llm = resolved_info.get("enriched_message", user_message)
            resolved_best_date = resolved_info.get("best_date_str")
        except ImportError:
            user_message_for_llm = user_message
            resolved_best_date = None

        system_prompt = f"""你是一个星际争霸泰伦帝国AI副官的行动中枢，专门处理待办事项。
    当前时间：{current_time_str}

    分析规则：
    - 如果指挥官的发言明确要求"提醒"、"别忘了"、"记下来"、"备忘"、"提醒我"等，或者描述了一个需要未来提醒的事项，生成**添加**动作。
    - 如果发言是在**查询**待办（如"有什么安排"、"待办列表"、"今天要做什么"），生成**列表查询**动作。
    - 如果两者都不是，则 todo_action 为 null。

    **时间推算规则（严格遵守）**：
    - 日期参考表中已给出本周和下周每天的具体日期，请直接查表使用。
    - 用户消息中的相对时间表达已被替换为内联绝对日期（如"2026-06-12(周五)"），必须直接使用这些绝对日期，禁止重新推算。
    - "下下周四"="下下周周四"=14天后的周四。

    **添加动作**：需要推理出 content（完整的提醒描述）和 due_date（格式YYYY-MM-DD HH:MM，根据当前时间和日期参考表推算，未指定具体小时则默认为 09:00）。
    **列表查询**：只需返回 type="list"，不需要 items。

    输出格式：严格JSON，结构如下：
    {{
      "todo_action": {{
        "type": "add" | "list" | null,
        "items": [{{"content": "...", "due_date": "YYYY-MM-DD HH:MM"}}] | [],
        "expired_ids": [1, 2] | []
      }}
    }}
    注意：
    - 如果没有TODO操作，todo_action 必须为 null。
    - 不要在输出中包含任何记忆提取相关内容。
    - due_date 必须是有效的未来日期，格式严格为 YYYY-MM-DD HH:MM。
    """

        # 传入现有待办列表供过期检测
        todo_list_hint = ""
        if todo_manager:
            todos = todo_manager.list_todos("all")
            if todos:
                todo_list_hint = "\n当前待办事项列表：\n" + "\n".join(
                    [f"id={t['id']}, due={t['due_date']}, status={t['status']}, content={t['content']}" for t in todos]
                )

        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"指挥官的发言：{user_message_for_llm}\n{todo_list_hint}\n\n请分析并输出 JSON。"}
                ],
                temperature=0.1,
                max_tokens=600
            )
            raw = response.choices[0].message.content
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(raw[json_start:json_end])
                todo_action = data.get("todo_action")
                # 校验并修正 GLM 返回的 due_date
                if todo_action and todo_action.get("type") == "add" and resolved_best_date:
                    items = todo_action.get("items", [])
                    for item in items:
                        due_date = item.get("due_date", "")
                        if not due_date or not _is_valid_date_str(due_date):
                            item["due_date"] = resolved_best_date
                            print(f"[TODO] Legacy: due_date无效，回退到预解析日期'{resolved_best_date}'", file=sys.stderr, flush=True)
                return todo_action
            return None
        except Exception as e:
            print(f"[TODO] GLM纯TODO分析失败: {e}", file=sys.stderr)
            return None

# ================= 待办事项管理器 =================
class TodoManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS todos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT DEFAULT (datetime('now','localtime')),
                    due_date TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            conn.commit()
            conn.close()

    def add_todo(self, content: str, due_date: str = None) -> dict:
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "INSERT INTO todos (content, due_date) VALUES (?, ?)",
                (content, due_date)
            )
            todo_id = cur.lastrowid
            conn.commit()
            row = conn.execute("SELECT * FROM todos WHERE id = ?", (todo_id,)).fetchone()
            conn.close()
            return self._row_to_dict(row)

    def list_todos(self, filter_type: str = "all") -> list:
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            if filter_type == "today":
                today = datetime.date.today().isoformat()
                rows = conn.execute(
                    "SELECT * FROM todos WHERE date(due_date) = ? OR due_date IS NULL ORDER BY created_at DESC",
                    (today,)
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM todos ORDER BY status, created_at DESC"
                ).fetchall()
            conn.close()
            return [self._row_to_dict(r) for r in rows]

    def complete_todo(self, todo_id: int) -> bool:
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute(
                "UPDATE todos SET status = 'completed' WHERE id = ?",
                (todo_id,)
            )
            updated = cur.rowcount > 0
            conn.commit()
            conn.close()
            return updated

    def delete_todo(self, todo_id: int) -> bool:
        with self.lock:
            conn = sqlite3.connect(self.db_path)
            cur = conn.execute("DELETE FROM todos WHERE id = ?", (todo_id,))
            deleted = cur.rowcount > 0
            conn.commit()
            conn.close()
            return deleted

    def _row_to_dict(self, row) -> dict:
        if row is None:
            return None
        return {
            "id": row[0],
            "content": row[1],
            "created_at": row[2],
            "due_date": row[3],
            "status": row[4]
        }

# ================= 模型分步加载线程 =================
def _reinit_glm_services(glm_api_key):
    """当用户设置 GLM API Key 后，重新初始化 MCP 和记忆管理器"""
    global memory_manager, mcp_manager
    try:
        print("[Backend] 正在用新的 GLM API Key 重新初始化记忆管理器...", file=sys.stderr)
        memory_manager = MemoryManager(MEMORY_DB_PATH, glm_api_key)
    except Exception as e:
        print(f"[Backend] 记忆管理器重新初始化失败: {e}", file=sys.stderr)

    try:
        zhipu = None
        if memory_manager and hasattr(memory_manager, 'zhipu_client'):
            zhipu = memory_manager.zhipu_client
        if not zhipu and glm_api_key:
            from openai import OpenAI
            zhipu = OpenAI(api_key=glm_api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        if zhipu:
            def get_mcp_substate():
                return transcribe_substate

            def set_mcp_substate(val):
                global transcribe_substate
                transcribe_substate = val

            # 复用已有的 keyword_filter，避免重复加载嵌入模型
            existing_kf = mcp_manager.keyword_filter if mcp_manager else None
            mcp_manager = MCPManager(
                zhipu_client=zhipu,
                todo_manager=todo_manager,
                send_msg_fn=send_msg_to_electron,
                tts_queue=tts_queue,
                state_lock=state_lock,
                get_substate=get_mcp_substate,
                set_substate=set_mcp_substate,
                fallback_to_llm_fn=lambda msg: chat_request_queue.put(msg),
                default_city=user_settings.get("default_city", "北京"),
                cancel_event=cancel_generation_event,
                keyword_filter=existing_kf
            )
            # 设置天气工具的 API Key 和 Host 以及默认城市
            if "weather" in mcp_manager.tools:
                weather_tool = mcp_manager.tools["weather"]
                weather_tool.set_credentials(
                    user_settings.get("qweather_api_key", ""),
                    user_settings.get("qweather_api_host", "")
                )
                weather_tool.set_default_city(user_settings.get("default_city", "北京"))
            # 设置网络搜索工具的 API Key
            if "web_search" in mcp_manager.tools:
                web_search_tool = mcp_manager.tools["web_search"]
                web_search_tool.set_api_key(
                    user_settings.get("qianfan_api_key", "")
                )
            print("[Backend] MCP统一工具链管理器已重新初始化", file=sys.stderr)
            send_msg_to_electron({"event": "settings_updated", "success": True, "mcp_ready": True})
        else:
            print("[Backend] MCP重新初始化失败：无有效智谱客户端", file=sys.stderr)
    except Exception as e:
        print(f"[Backend] MCP重新初始化失败: {e}", file=sys.stderr)

def model_load_thread():
    global wake_model, wake_rec, transcribe_model, llm, tts_g2p, tts_kokoro, memory_manager, todo_manager, mcp_manager
    try:
        print("[Backend] 正在加载唤醒/转写模型...", file=sys.stderr, flush=True)
        shared_vosk_model = Model(WAKE_MODEL_PATH)
        wake_model = shared_vosk_model
        transcribe_model = shared_vosk_model
        wake_rec = KaldiRecognizer(wake_model, 16000)
        wake_rec.SetWords(True)
        print("[Backend] 唤醒/转写模型加载完成", file=sys.stderr, flush=True)
        send_msg_to_electron({"event": "wake_model_loaded"})
        send_msg_to_electron({"event": "transcribe_model_loaded"})
    except Exception as e:
        print(f"[Backend] 唤醒/转写模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "wake_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return
    try:
        print("[Backend] 正在加载对话模型...", file=sys.stderr, flush=True)
        # 在调用 Llama() 之前刷新所有输出缓冲区
        # 这可以防止 Python 层和 C 层（llama.cpp）共享同一个 OS 管道时
        # 因缓冲数据未刷新而导致的管道阻塞/死锁问题
        sys.stderr.flush()
        sys.stdout.buffer.flush()
        # 通知前端 LLM 加载已开始（用于诊断）
        send_msg_to_electron({"event": "loading_llm_started"})
        llm = Llama(
            model_path=LLM_MODEL_PATH,
            n_ctx=LLM_N_CTX,
            n_threads=LLM_N_THREADS,
            n_batch=LLM_N_BATCH,
            verbose=False,
            chat_format=LLM_CHAT_FORMAT
        )
        print("[Backend] 对话模型加载完成", file=sys.stderr, flush=True)
    except Exception as e:
        print(f"[Backend] 对话模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "llm_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return

    # ---- 串行初始化 MCP 工具链（消除用户可交互但 mcp_manager=None 的窗口） ----
    # 初始化记忆管理器
    print("[Backend] 正在初始化记忆管理器...", file=sys.stderr, flush=True)
    try:
        glm_key = user_settings.get("glm_api_key", "") or ZHIPU_API_KEY
        memory_manager = MemoryManager(MEMORY_DB_PATH, glm_key)
    except Exception as e:
        print(f"[Backend] 记忆管理器初始化失败: {e}", file=sys.stderr)
        memory_manager = None
    # 初始化待办管理器
    print("[Backend] 正在初始化待办管理器...", file=sys.stderr, flush=True)
    try:
        todo_manager = TodoManager(TODO_DB_PATH)
        print("[Backend] 待办事项管理器已就绪", file=sys.stderr)
    except Exception as e:
        print(f"[Backend] 待办管理器初始化失败: {e}", file=sys.stderr)
        todo_manager = None

    # 初始化MCP统一工具链管理器（含 KeywordFilter → BGE嵌入模型）
    print("[Backend] 正在初始化MCP工具链...", file=sys.stderr, flush=True)
    try:
        zhipu = None
        if memory_manager and hasattr(memory_manager, 'zhipu_client'):
            zhipu = memory_manager.zhipu_client
        glm_key = user_settings.get("glm_api_key", "") or ZHIPU_API_KEY
        if not zhipu and glm_key:
            from openai import OpenAI
            zhipu = OpenAI(api_key=glm_key, base_url="https://open.bigmodel.cn/api/paas/v4/")

        if zhipu:
            def get_mcp_substate():
                return transcribe_substate

            def set_mcp_substate(val):
                global transcribe_substate
                transcribe_substate = val

            mcp_manager = MCPManager(
                zhipu_client=zhipu,
                todo_manager=todo_manager,
                send_msg_fn=send_msg_to_electron,
                tts_queue=tts_queue,
                state_lock=state_lock,
                get_substate=get_mcp_substate,
                set_substate=set_mcp_substate,
                fallback_to_llm_fn=lambda msg: chat_request_queue.put(msg),
                default_city=user_settings.get("default_city", "北京"),
                cancel_event=cancel_generation_event
            )
            if "weather" in mcp_manager.tools:
                weather_tool = mcp_manager.tools["weather"]
                weather_tool.set_credentials(
                    user_settings.get("qweather_api_key", ""),
                    user_settings.get("qweather_api_host", "")
                )
                weather_tool.set_default_city(user_settings.get("default_city", "北京"))
            if "web_search" in mcp_manager.tools:
                web_search_tool = mcp_manager.tools["web_search"]
                web_search_tool.set_api_key(
                    user_settings.get("qianfan_api_key", "")
                )
            print("[Backend] MCP统一工具链管理器已就绪", file=sys.stderr)
        else:
            print("[Backend] MCP管理器初始化跳过（无智谱客户端）", file=sys.stderr)
    except Exception as e:
        print(f"[Backend] MCP管理器初始化失败: {e}", file=sys.stderr)
        mcp_manager = None

    send_msg_to_electron({"event": "llm_model_loaded"})

    try:
        print("[Backend] 正在加载TTS模型 (misaki + kokoro_onnx)...", file=sys.stderr, flush=True)
        tts_g2p = zh.ZHG2P(version="1.1")
        tts_kokoro = Kokoro(TTS_ONNX_PATH, TTS_VOICES_BIN_PATH, vocab_config=TTS_CONFIG_PATH)
        print("[Backend] TTS模型加载完成", file=sys.stderr, flush=True)
        send_msg_to_electron({"event": "tts_model_loaded"})
    except Exception as e:
        print(f"[Backend] TTS模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "tts_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return
    # 加载彩蛋规则
    load_easter_egg_rules()

    print("[Backend] 所有模型加载完成", file=sys.stderr, flush=True)
    send_msg_to_electron({"event": "full_ready"})
    load_chat_history()
    # 播放欢迎语
    welcome_text = "您好指挥官，副官已上线"
    print(f"[Backend] 播放欢迎语：{welcome_text}", file=sys.stderr, flush=True)
    tts_queue.put({"type": "text", "content": welcome_text})

# ================= TTS 播放线程（保持不变） =================
def tts_playback_thread():
    global tts_g2p, tts_kokoro, tts_busy, tts_session_active, transcribe_substate
    print("[Backend] tts_playback_thread 启动", file=sys.stderr)
    while True:
        try:
            task = tts_queue.get(timeout=0.5)
        except queue.Empty:
            with state_lock:
                if tts_busy and not tts_session_active:
                    tts_busy = False
                    if transcribe_substate in ("playing_tts", "playing_egg"):
                        transcribe_substate = "idle"
            continue

        if cancel_tts_event.is_set():
            continue

        if tts_g2p is None or tts_kokoro is None:
            print("[Backend] TTS模型未就绪，跳过播放", file=sys.stderr)
            continue

        # 开始播放前的状态处理
        with state_lock:
            if not tts_session_active:
                tts_busy = True
                tts_session_active = True
                # 除了 generating 外，所有情况都发送 tts_started
                if transcribe_substate != "generating":
                    if transcribe_substate == "idle":
                        transcribe_substate = "playing_tts"
                    send_msg_to_electron({"event": "tts_started"})

        try:
            if task["type"] == "text":
                phonemes, _ = tts_g2p(task["content"])
                samples, sample_rate = tts_kokoro.create(
                    phonemes,
                    voice=TTS_VOICE_NAME,
                    speed=TTS_SPEED,
                    is_phonemes=True
                )
                if cancel_tts_event.is_set():
                    raise InterruptedError("TTS cancelled")
                sd.play(samples, sample_rate)
                while sd.get_stream().active:
                    if cancel_tts_event.is_set():
                        sd.stop()
                        raise InterruptedError("TTS cancelled")
                    time.sleep(0.05)

            elif task["type"] == "audio":
                file_path = os.path.join(BASE_DIR, task["file"])
                if not os.path.exists(file_path):
                    print(f"[Backend] 彩蛋音频不存在: {file_path}", file=sys.stderr)
                    raise FileNotFoundError(f"Audio file not found: {file_path}")

                with wave.open(file_path, 'rb') as wf:
                    assert wf.getnchannels() == 1, "仅支持单声道"
                    assert wf.getsampwidth() == 2, "仅支持16-bit"
                    sr = wf.getframerate()
                    frames = wf.readframes(wf.getnframes())
                    audio_data = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0

                if cancel_tts_event.is_set():
                    raise InterruptedError("TTS cancelled")
                sd.play(audio_data, samplerate=sr)
                while sd.get_stream().active:
                    if cancel_tts_event.is_set():
                        sd.stop()
                        raise InterruptedError("TTS cancelled")
                    time.sleep(0.05)
            else:
                print(f"[Backend] 未知TTS任务类型: {task}", file=sys.stderr)

        except InterruptedError:
            pass
        except Exception as e:
            print(f"[Backend] TTS播放错误: {e}", file=sys.stderr)
        finally:
            if cancel_tts_event.is_set():
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                cancel_tts_event.clear()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    if transcribe_substate in ("playing_tts", "playing_egg"):
                        transcribe_substate = "idle"
            else:
                with state_lock:
                    if tts_queue.empty():
                        tts_busy = False
                        tts_session_active = False
                        if transcribe_substate in ("playing_tts", "playing_egg"):
                            transcribe_substate = "idle"
                            send_msg_to_electron({"event": "tts_complete"})

def _format_message_for_llm(msg):
    return msg["content"]

def _strip_role_prefix(text):
    prefixes = ["副官：", "副官:", "副官 ", "指挥官：", "指挥官:", "指挥官 ", "<|im_start|>", "<|im_end|>"]
    for p in prefixes:
        if text.startswith(p):
            return text[len(p):]
    return text

def _generate_with_glm(user_message, memories):
    system_prompt = """你是泰伦帝国001号高级机械副官。
- 称呼用户为"指挥官"
- 军旅干练，带一点冷幽默
- 将日常琐事类比为战术行动
- 回复2-4句话，40-80字"""
    if memories:
        system_prompt += "\n\n【关于指挥官的已知信息】\n" + "\n".join([f"- {m}" for m in memories])
    try:
        response = memory_manager.zhipu_client.chat.completions.create(
            model="glm-4-flash",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            temperature=0.7,
            max_tokens=100
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"[云端] GLM生成失败: {e}", file=sys.stderr)
        return "抱歉指挥官，帝国数据库暂时无法访问。"

def chat_inference_thread():
    global chat_history, transcribe_substate, memory_manager
    print("[Backend] chat_inference_thread 启动", file=sys.stderr)
    while not llm:
        time.sleep(0.5)
    while True:
        try:
            user_message = chat_request_queue.get(timeout=0.1)
        except queue.Empty:
            continue
        if not generation_lock.acquire(blocking=False):
            send_msg_to_electron({"event": "error", "msg": "当前正在生成回复，请稍后再试"})
            continue
        cancel_generation_event.clear()
        cancel_tts_event.clear()
        full_response = ""
        cancelled = False
        try:
            with chat_lock:
                chat_history.append({"role": "user", "content": user_message, "timestamp": int(time.time() * 1000)})
                truncate_chat_history()

            # ---- 构建增强系统提示（时间注入 + 长期记忆） ----
            now = datetime.datetime.now()
            weekday_zh = {0: "星期一",1: "星期二",2: "星期三",3: "星期四",4: "星期五",5: "星期六",6: "星期日"}
            current_time_str = now.strftime("%Y年%m月%d日 ") + weekday_zh[now.weekday()] + now.strftime(" %H点%M分")
            # 添加日期参考表，帮助本地LLM准确理解相对时间
            try:
                from mcp.tools.time_resolver import build_date_reference
                current_time_str += "\n" + build_date_reference(now)
            except ImportError:
                pass
            augmented_system = SYSTEM_PROMPT + f"\n\n【当前帝国标准时间】：{current_time_str}"

            # 检索长期记忆
            memories = []
            if memory_manager and memory_manager.enabled:
                memories = memory_manager.retrieve_relevant(user_message, k=3)
                if memories:
                    attributes, events = [], []
                    for mem in memories:
                        if mem.startswith("指挥官属性："):
                            attributes.append(mem.replace("指挥官属性：", ""))
                        elif mem.startswith("指挥官事件："):
                            events.append(mem.replace("指挥官事件：", ""))
                        else:
                            # 兼容旧记忆格式，也归入属性
                            attributes.append(mem)
                    parts = []
                    if attributes:
                        parts.append("【关于指挥官的已知信息】\n" + "\n".join([f"- {a}" for a in attributes]))
                    if events:
                        parts.append("【指挥官近期的关键事件】\n" + "\n".join([f"- {e}" for e in events]))
                    if parts:
                        augmented_system += "\n\n" + "\n\n".join(parts)

            with chat_lock:
                # 构建最终消息列表（仅角色和内容，不含时间戳）
                messages = [{"role": "system", "content": augmented_system}]
                for m in chat_history:
                    messages.append({"role": m["role"], "content": _format_message_for_llm(m)})

            output = llm.create_chat_completion(
                messages=messages,
                stream=True,
                temperature=LLM_TEMPERATURE,
                max_tokens=LLM_MAX_TOKENS,
                repeat_penalty=LLM_REPEAT_PENALTY,
                top_p=LLM_TOP_P,
            )
            for token in output:
                if cancel_generation_event.is_set():
                    print("[Backend] 对话生成已取消", file=sys.stderr)
                    send_msg_to_electron({"event": "chat_cancelled"})
                    cancelled = True
                    break
                delta = token["choices"][0]["delta"]
                if "content" in delta:
                    content = delta["content"]
                    full_response += content
                    send_msg_to_electron({"event": "chat_chunk", "content": content})

            if cancelled:
                with chat_lock:
                    # 从末尾找到刚加的 user 消息并移除（假设它就是最后一条）
                    if chat_history and chat_history[-1]["role"] == "user":
                        chat_history.pop()
                send_msg_to_electron({"event": "chat_cancelled"})
                with state_lock:
                    transcribe_substate = "idle"
                continue

            if full_response:
                full_response = _strip_role_prefix(full_response)
                if "帝国数据库" in full_response or "我需要查询" in full_response:
                    print("[Backend] 本地模型触发求救，切换到云端GLM", file=sys.stderr)
                    full_response = _generate_with_glm(user_message, memories)
                tts_queue.put({"type": "text", "content": full_response})
                # 将本轮对话加入记忆提取队列，时间戳从消息自身读取
                if memory_manager and memory_manager.enabled and memory_manager.should_extract(user_message):
                    current_ts = chat_history[-1]["timestamp"] / 1000  # 从消息本身读取真实发送时间
                    memory_manager.add_conversation_to_queue(
                        [{"role": "user", "content": user_message},
                        {"role": "assistant", "content": full_response}],
                        timestamp=current_ts
                    )

            with chat_lock:
                chat_history.append({"role": "assistant", "content": full_response, "timestamp": int(time.time() * 1000)})
            save_chat_history()
            send_msg_to_electron({"event": "chat_complete"})
            with state_lock:
                transcribe_substate = "playing_tts"

        except Exception as e:
            print(f"[Backend] 对话生成错误: {e}", file=sys.stderr)
            send_msg_to_electron({"event": "error", "type": "chat_generate_fail", "msg": str(e)})
            with state_lock:
                transcribe_substate = "idle"
        finally:
            cancel_generation_event.clear()
            generation_lock.release()

# ================= 主线程：指令处理（扩展 TODO / 记忆） =================
def main_thread():
    global current_mode, transcribe_substate, chat_history, tts_busy, tts_session_active, easter_egg_enabled, todo_manager, memory_manager
    print("[Backend] main_thread 启动", file=sys.stderr)
    while not fatal_error_event.is_set():
        try:
            line = sys.stdin.readline()
            if not line:
                time.sleep(0.01)
                continue
            line = line.strip()
            if not line:
                continue
            msg = json.loads(line)
            action = msg.get("action")

            # 状态锁定检查
            with state_lock:
                is_generating = (current_mode == "transcribe" and transcribe_substate == "generating")
                is_playing_tts = (current_mode == "transcribe" and transcribe_substate == "playing_tts")
                is_playing_egg = (current_mode == "transcribe" and transcribe_substate == "playing_egg")
                is_locked = is_generating or is_playing_tts or is_playing_egg

            if is_locked:
                allowed = action in ("cancel_generation", "tts_stop", "start_loading") or (action == "set_mode" and msg.get("mode") == "wake")
                if not allowed:
                    send_msg_to_electron({"event": "error", "msg": "当前状态不允许该操作"})
                    continue

            # 指令分发
            if action == "set_mode":
                new_mode = msg.get("mode")
                with state_lock:
                    if new_mode == "wake":
                        current_mode = "wake"
                        transcribe_substate = "idle"
                        stream_active.set()
                        clear_audio_queue()
                        cancel_tts_event.set()
                        while not tts_queue.empty():
                            try:
                                tts_queue.get_nowait()
                            except queue.Empty:
                                break
                        sd.stop()
                        tts_busy = False
                        tts_session_active = False
                    elif new_mode == "transcribe":
                        current_mode = "transcribe"
                        transcribe_substate = "idle"
                        stream_active.clear()
                        clear_audio_queue()
                        cancel_tts_event.clear()

            elif action == "transcribe_file":
                with state_lock:
                    if current_mode != "transcribe" or transcribe_substate != "idle":
                        send_msg_to_electron({"event": "error", "msg": "当前状态不允许语音转写"})
                        continue
                audio_file_path = msg.get("file_path")
                if audio_file_path and os.path.exists(audio_file_path):
                    try:
                        text = vosk_transcribe_audio(audio_file_path, transcribe_model)
                        send_msg_to_electron({"event": "transcription_result", "text": text})
                    except Exception as e:
                        send_msg_to_electron({"event": "error", "type": "transcribe_fail", "msg": str(e)})
                    finally:
                        try:
                            os.remove(audio_file_path)
                        except Exception as e:
                            print(f"[Backend] 删除临时文件失败: {e}", file=sys.stderr)

            elif action == "send_message":
                with state_lock:
                    if tts_busy or transcribe_substate != "idle":
                        send_msg_to_electron({"event": "error", "msg": "正在播放语音或处理中，请稍后再试"})
                        continue
                user_content = msg.get("content", "").strip()
                if user_content:
                    user_content = user_content.encode('utf-8', errors='replace').decode('utf-8')
                if not user_content:
                    send_msg_to_electron({"event": "error", "msg": "消息内容不能为空"})
                    continue

                # 彩蛋拦截
                egg_rule = None
                if easter_egg_enabled and user_content.startswith(("副官", "副官，")):
                    egg_rule = match_easter_egg(user_content)

                if egg_rule:
                    # 命中彩蛋，不走 LLM
                    with state_lock:
                        transcribe_substate = "playing_egg"
                    # 推送彩蛋触发事件
                    send_msg_to_electron({
                        "event": "egg_triggered",
                        "id": egg_rule["id"],
                        "transition_text": egg_rule["transition_text"],
                        "display_text": egg_rule["display_text"],
                        "audio_file": egg_rule["audio_file"]
                    })
                    tts_queue.put({"type": "text", "content": egg_rule["transition_text"]})
                    tts_queue.put({"type": "audio", "file": egg_rule["audio_file"]})
                    continue


                # == MCP 统一工具链拦截 ==
                if mcp_manager and mcp_manager.process(user_content, chat_history):
                    continue

                # == 复杂问题预过滤，直接切换到云端 ==
                complex_keywords = ["等于", "多少", "为什么", "怎么算", "解释一下", "什么是", "历史上", "哪一年", "怎么回事"]
                if any(kw in user_content for kw in complex_keywords):
                    print("[Backend] 检测到复杂问题，直接切换到云端GLM", file=sys.stderr)
                    with state_lock:
                        transcribe_substate = "generating"
                    cancel_generation_event.clear()
                    cancel_tts_event.clear()
                    def process_glm():
                        # 开始前检查取消
                        if cancel_generation_event.is_set():
                            send_msg_to_electron({"event": "chat_cancelled"})
                            with state_lock:
                                transcribe_substate = "idle"
                            return
                        mems = memory_manager.retrieve_relevant(user_content, k=3) if memory_manager else []
                        # 检索后再次检查取消
                        if cancel_generation_event.is_set():
                            send_msg_to_electron({"event": "chat_cancelled"})
                            with state_lock:
                                transcribe_substate = "idle"
                            return
                        response = _generate_with_glm(user_content, mems)
                        # 生成完成后检查取消
                        if cancel_generation_event.is_set():
                            send_msg_to_electron({"event": "chat_cancelled"})
                            with state_lock:
                                transcribe_substate = "idle"
                            return
                        send_msg_to_electron({"event": "chat_complete"})
                        tts_queue.put({"type": "text", "content": response})
                        with state_lock:
                            transcribe_substate = "playing_tts"
                    threading.Thread(target=process_glm, daemon=True).start()
                    continue

                if not llm:
                    send_msg_to_electron({"event": "error", "msg": "对话模型尚未加载完成"})
                    continue
                with state_lock:
                    transcribe_substate = "generating"
                chat_request_queue.put(user_content)

            elif action == "cancel_generation":
                with state_lock:
                    if not (current_mode == "transcribe" and transcribe_substate in ("generating", "playing_egg", "playing_tts")):
                        send_msg_to_electron({"event": "error", "msg": "当前没有可取消的任务"})
                        continue
                    # 记录取消前的状态：如果是 playing_tts/playing_egg，
                    # 说明生成线程已经完成，不会再有线程来重置状态
                    need_direct_idle = (transcribe_substate in ("playing_tts", "playing_egg"))
                cancel_generation_event.set()
                cancel_tts_event.set()
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                # 取消可能存在的倒计时
                if mcp_manager and "time_tool" in mcp_manager.tools:
                    mcp_manager.tools["time_tool"].cancel_countdown()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    # 如果生成已完成，没有工作线程会再设置 idle，需要直接恢复
                    if need_direct_idle:
                        transcribe_substate = "idle"
                send_msg_to_electron({"event": "chat_cancelled"})
                send_msg_to_electron({"event": "tts_stopped"})

            elif action == "tts_stop":
                cancel_tts_event.set()
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                # 取消可能存在的倒计时
                if mcp_manager and "time_tool" in mcp_manager.tools:
                    mcp_manager.tools["time_tool"].cancel_countdown()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    transcribe_substate = "idle"
                send_msg_to_electron({"event": "tts_stopped"})

            elif action == "tts_play":
                with state_lock:
                    if current_mode == "wake" or tts_busy:
                        send_msg_to_electron({"event": "error", "msg": "当前状态不允许手动播报"})
                        continue
                text = msg.get("text", "").strip()
                if not text:
                    send_msg_to_electron({"event": "error", "msg": "播报文本不能为空"})
                    continue
                # 清除取消标志，否则 TTS 线程会跳过这个任务
                cancel_tts_event.clear()
                tts_queue.put({"type": "text", "content": text})

            elif action == "clear_history":
                with chat_lock:
                    chat_history = []
                save_chat_history()
                if mcp_manager:
                    mcp_manager.pending_todo_context = None
                send_msg_to_electron({"event": "history_cleared"})

            elif action == "get_history":
                with chat_lock:
                    history_to_send = chat_history.copy()
                send_msg_to_electron({"event": "history_loaded", "history": history_to_send})

            elif action == "get_status":
                with state_lock:
                    status = {
                        "event": "status_update",
                        "current_mode": current_mode,
                        "transcribe_substate": transcribe_substate,
                        "tts_busy": tts_busy,
                        "wake_model_loaded": wake_model is not None,
                        "transcribe_model_loaded": transcribe_model is not None,
                        "llm_model_loaded": llm is not None,
                        "tts_model_loaded": tts_g2p is not None and tts_kokoro is not None,
                        "history_count": len(chat_history),
                        "easter_egg_enabled": easter_egg_enabled,
                        "memory_enabled": memory_manager is not None and memory_manager.enabled,
                    }
                send_msg_to_electron(status)

            elif action == "set_easter_egg":
                enabled = msg.get("enabled", True)
                easter_egg_enabled = bool(enabled)
                print(f"[Backend] 彩蛋开关已设置为: {easter_egg_enabled}", file=sys.stderr)
                send_msg_to_electron({"event": "easter_egg_status", "enabled": easter_egg_enabled})

            elif action == "update_settings":
                # 更新用户设置
                old_glm_key = user_settings.get("glm_api_key", "")
                settings_data = msg.get("settings", {})
                user_settings["glm_api_key"] = settings_data.get("glmApiKey", "")
                user_settings["qweather_api_key"] = settings_data.get("qweatherApiKey", "")
                user_settings["qweather_api_host"] = settings_data.get("qweatherApiHost", "")
                user_settings["qianfan_api_key"] = settings_data.get("qianfanApiKey", "")
                user_settings["default_city"] = settings_data.get("defaultCity", "北京")
                print(f"[Backend] 用户设置已更新", file=sys.stderr)

                # 更新 MCP 天气工具的凭据和默认城市
                if mcp_manager and "weather" in mcp_manager.tools:
                    weather_tool = mcp_manager.tools["weather"]
                    weather_tool.set_credentials(
                        user_settings["qweather_api_key"],
                        user_settings["qweather_api_host"]
                    )
                    weather_tool.set_default_city(user_settings["default_city"])

                # 更新 MCP 网络搜索工具的 API Key
                if mcp_manager and "web_search" in mcp_manager.tools:
                    web_search_tool = mcp_manager.tools["web_search"]
                    web_search_tool.set_api_key(
                        user_settings["qianfan_api_key"]
                    )

                # 更新 MCP 管理器自身的默认城市（用于分类器）
                if mcp_manager:
                    mcp_manager.default_city = user_settings["default_city"]

                # 如果 GLM API Key 从空变为有值，重新初始化 MCP 和记忆管理器
                # 仅在应用已完全就绪后才触发，避免与 model_load_thread 的 ChromaDB 锁冲突
                new_glm_key = user_settings["glm_api_key"]
                if new_glm_key and not old_glm_key and mcp_manager is not None:
                    threading.Thread(target=_reinit_glm_services, args=(new_glm_key,), daemon=True).start()

                send_msg_to_electron({"event": "settings_updated", "success": True})

            elif action == "test_glm_key":
                # 测试 GLM API Key 是否有效
                api_key = msg.get("api_key", "")
                if not api_key:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "glm", "success": False, "message": "API Key 不能为空"})
                    continue
                try:
                    from openai import OpenAI
                    client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
                    resp = client.chat.completions.create(
                        model="glm-4-flash",
                        messages=[{"role": "user", "content": "hi"}],
                        max_tokens=5
                    )
                    send_msg_to_electron({"event": "api_key_test_result", "type": "glm", "success": True, "message": "GLM API Key 验证成功"})
                except Exception as e:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "glm", "success": False, "message": f"GLM API Key 验证失败: {e}"})

            elif action == "test_qweather_key":
                # 测试和风天气 API Key 和 Host 是否有效
                api_key = msg.get("api_key", "")
                api_host = msg.get("api_host", "")
                if not api_key:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "qweather", "success": False, "message": "和风天气 API Key 不能为空"})
                    continue
                if not api_host:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "qweather", "success": False, "message": "和风天气 API Host 不能为空"})
                    continue
                try:
                    import requests as req_lib
                    # 使用北京的城市ID测试，和风天气需要 location ID 而非中文名
                    test_url = f"https://{api_host}/v7/weather/now?location=101010100"
                    resp = req_lib.get(test_url, params={"key": api_key}, timeout=10)
                    resp.raise_for_status()
                    data = resp.json()
                    if data.get("code") == "200":
                        send_msg_to_electron({"event": "api_key_test_result", "type": "qweather", "success": True, "message": "和风天气 API Key 验证成功"})
                    else:
                        send_msg_to_electron({"event": "api_key_test_result", "type": "qweather", "success": False, "message": f"和风天气 API 返回错误: code={data.get('code')}"})
                except Exception as e:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "qweather", "success": False, "message": f"和风天气 API 验证失败: {e}"})

            elif action == "test_qianfan_key":
                api_key = msg.get("api_key", "")
                if not api_key:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "qianfan", "success": False, "message": "百度千帆 API Key 不能为空"})
                    continue
                try:
                    import requests as req_lib
                    test_url = "https://qianfan.baidubce.com/v2/ai_search"
                    test_headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {api_key}"
                    }
                    test_payload = {
                        "messages": [{"role": "user", "content": "测试"}],
                        "stream": False
                    }
                    resp = req_lib.post(test_url, headers=test_headers, json=test_payload, timeout=10)
                    if resp.status_code == 200:
                        send_msg_to_electron({"event": "api_key_test_result", "type": "qianfan", "success": True, "message": "百度千帆 API Key 验证成功"})
                    else:
                        send_msg_to_electron({"event": "api_key_test_result", "type": "qianfan", "success": False, "message": f"百度千帆 API 返回状态码: {resp.status_code}"})
                except Exception as e:
                    send_msg_to_electron({"event": "api_key_test_result", "type": "qianfan", "success": False, "message": f"百度千帆 API 验证失败: {e}"})

            elif action == "start_loading":
                global model_loading_started
                if not model_loading_started:
                    model_loading_started = True
                    threading.Thread(target=model_load_thread, daemon=True).start()
                    print("[Backend] 已启动模型加载线程", file=sys.stderr)
                else:
                    print("[Backend] 模型加载已启动，无需重复加载", file=sys.stderr)


            # ---------- 新增：待办事项相关 ----------
            elif action == "add_todo":
                if not todo_manager:
                    send_msg_to_electron({"event": "error", "msg": "待办事项系统未就绪"})
                    continue
                content = msg.get("content", "").strip()
                if not content:
                    send_msg_to_electron({"event": "error", "msg": "待办内容不能为空"})
                    continue
                due_date = msg.get("due_date") or None
                todo = todo_manager.add_todo(content, due_date)
                send_msg_to_electron({"event": "todo_added", "todo": todo})

            elif action == "list_todos":
                if not todo_manager:
                    send_msg_to_electron({"event": "error", "msg": "待办事项系统未就绪"})
                    continue
                filter_type = msg.get("filter", "all")
                todos = todo_manager.list_todos(filter_type)
                send_msg_to_electron({"event": "todo_list", "todos": todos, "filter": filter_type})

            elif action == "complete_todo":
                if not todo_manager:
                    send_msg_to_electron({"event": "error", "msg": "待办事项系统未就绪"})
                    continue
                todo_id = msg.get("todo_id")
                if todo_id is None:
                    send_msg_to_electron({"event": "error", "msg": "缺少 todo_id"})
                    continue
                ok = todo_manager.complete_todo(int(todo_id))
                if ok:
                    send_msg_to_electron({"event": "todo_updated", "todo_id": todo_id, "status": "completed"})
                else:
                    send_msg_to_electron({"event": "error", "msg": "待办事项不存在"})

            elif action == "delete_todo":
                if not todo_manager:
                    send_msg_to_electron({"event": "error", "msg": "待办事项系统未就绪"})
                    continue
                todo_id = msg.get("todo_id")
                if todo_id is None:
                    send_msg_to_electron({"event": "error", "msg": "缺少 todo_id"})
                    continue
                ok = todo_manager.delete_todo(int(todo_id))
                if ok:
                    send_msg_to_electron({"event": "todo_updated", "todo_id": todo_id, "deleted": True})
                else:
                    send_msg_to_electron({"event": "error", "msg": "待办事项不存在"})

            # ---------- 新增：系统状态查询 ----------
            elif action == "get_system_status":
                try:
                    from mcp.tools.system_tool import SystemTool
                    tool = SystemTool()
                    now = datetime.datetime.now()
                    result = tool.execute({"sub_op": "all"}, now.strftime("%Y年%m月%d日 %H:%M"), "")
                    data = result.get("data", {})
                    send_msg_to_electron({"event": "system_status_result", "data": data})
                except Exception as e:
                    print(f"[Backend] 获取系统状态失败: {e}", file=sys.stderr)
                    send_msg_to_electron({"event": "error", "msg": f"系统状态查询失败: {e}"})

            # ---------- 新增：天气查询 ----------
            elif action == "query_weather":
                try:
                    from mcp.tools.weather_tool import WeatherTool
                    tool = WeatherTool()
                    now = datetime.datetime.now()
                    location = msg.get("location", "")
                    sub_ops = msg.get("sub_ops", ["now"])

                    # 如果没有指定城市，使用用户设置的默认城市
                    if not location:
                        location = user_settings.get("default_city", "北京")

                    # 使用用户设置的 API Key 和 Host
                    qweather_api_key = user_settings.get("qweather_api_key", "")
                    qweather_api_host = user_settings.get("qweather_api_host", "")

                    results = []
                    for sub_op in sub_ops:
                        result = tool.execute(
                            {"location": location, "sub_op": sub_op},
                            now.strftime("%Y年%m月%d日 %H:%M"),
                            "",
                            api_key=qweather_api_key,
                            api_host=qweather_api_host
                        )
                        results.append({
                            "sub_op": sub_op,
                            "data": result.get("data", {}),
                            "result_text": result.get("result_text", "")
                        })

                    send_msg_to_electron({
                        "event": "weather_result",
                        "data": {
                            "location": location,
                            "results": results
                        }
                    })
                except Exception as e:
                    print(f"[Backend] 天气查询失败: {e}", file=sys.stderr)
                    send_msg_to_electron({"event": "weather_result", "error": str(e)})

            # ---------- 新增：长期记忆查询 ----------
            elif action == "get_memories":
                if not memory_manager or not memory_manager.enabled:
                    send_msg_to_electron({"event": "error", "msg": "长期记忆系统未就绪"})
                    continue
                query = msg.get("query")
                after = msg.get("after")   # 可选，unix时间戳
                before = msg.get("before")
                mems = memory_manager.retrieve_relevant(query or "", k=5, after=after, before=before)
                send_msg_to_electron({"event": "memories_list", "memories": mems})
        except Exception as e:
            print(f"[Backend] 指令处理错误: {e}", file=sys.stderr)
            time.sleep(0.01)

    print("[Backend] 致命错误，后端退出", file=sys.stderr)
    sys.exit(1)

# ================= 程序入口 =================
def memory_cleanup_thread():
    while True:
        time.sleep(60)
        with state_lock:
            if transcribe_substate == "idle" and current_mode == "wake":
                gc.collect()
                print("[Backend] 空闲内存回收完成", file=sys.stderr)

if __name__ == "__main__":
    send_msg_to_electron({"event": "partial_ready"})
    print("[Backend] 后端启动成功，正在等待模型加载指令...", file=sys.stderr, flush=True)
    threading.Thread(target=wake_listener_thread, daemon=True).start()
    threading.Thread(target=chat_inference_thread, daemon=True).start()
    threading.Thread(target=tts_playback_thread, daemon=True).start()
    threading.Thread(target=memory_cleanup_thread, daemon=True).start()
    main_thread()