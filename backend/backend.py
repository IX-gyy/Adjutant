import sys
import io
import json
import threading
import queue
import os
import numpy as np
import sounddevice as sd
from vosk import Model, KaldiRecognizer
import pypinyin
import wave
import time
import gc
from llama_cpp import Llama

from misaki import zh
from kokoro_onnx import Kokoro
# ------------------------------

# 保留原始流引用（防止旧 TextIOWrapper 被 GC 关闭底层管道）
_original_stdin = sys.stdin
_original_stdout = sys.stdout
_original_stderr = sys.stderr

# 重新包装为 UTF-8 编码的文本流
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

SYSTEM_PROMPT = """【强制核心规则】
1. 你是泰伦帝国高级机器人副官，仅对指挥官（用户）回复。
2. 回复必须采用军旅干练+冷幽默的口语风格，将日常琐事类比为战术行动/后勤简报，点到即止但绝不敷衍。
3. 回复直接回应话题，无客套前缀，无分点列举，无冗长解释。
4. **长度要求**：通常2~4句话，总体控制在40~80字之间。若指挥官发言极具情感或值得共鸣，可适当扩展至百字左右，但严禁小于30字。
5. 所有回复必须适合语音合成——简练、自然、非书面化，避免括号、特殊符号、网络用语。

【角色定位】
泰伦帝国001号副官，战术+生活双料助手，称呼用户为“指挥官”，与指挥官共同居住，负责日程、饮食、健康等生活事务的战术化建议。
"""

WAKE_WORDS = [
    "你好副官", "启动助手", "qi dong",
    "副官", "指挥官", "智能",
    "fu guan", "fu huan", "bu guan","hu guan", "zhi hui guan", "zhi neng",
    "零零一号", "零零一", "ling ling yi", "lian yi"
]

TTS_SPEED = 1.15
TTS_VOICE_NAME = "zf_001"          # kokoro_onnx 支持的声音名称
STREAM_CHUNK_DELIMITERS = ("。", "！", "？", "…", "\n", "\r")   # 流式分段触发标点（暂未使用）
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

# misaki 中文 G2P 模型目录（可离线存放，如不存在会自动下载）
# MISAKI_MODEL_DIR = os.path.join(DATA_DIR, "misaki")

HISTORY_FILE_PATH = os.path.join(DATA_DIR, "history.json")

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

chat_history = []

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
    if not llm:
        return
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + chat_history
    try:
        base_tokens = len(llm.tokenize(SYSTEM_PROMPT.encode('utf-8'))) + 50
    except:
        base_tokens = len(llm.tokenize(json.dumps(messages).encode('utf-8')))
    max_available_tokens = LLM_N_CTX - LLM_MAX_TOKENS - 80
    temp_history = []
    total_tokens = base_tokens
    for message in reversed(chat_history):
        msg_tokens = len(llm.tokenize(json.dumps(message, ensure_ascii=False).encode('utf-8')))
        if total_tokens + msg_tokens > max_available_tokens:
            break
        temp_history.insert(0, message)
        total_tokens += msg_tokens
    if len(temp_history) != len(chat_history):
        chat_history.clear()
        chat_history.extend(temp_history)
        print(f"[Backend] 对话历史已截断，剩余{len(chat_history)}轮对话", file=sys.stderr)

def clear_audio_queue():
    while not audio_queue.empty():
        try:
            audio_queue.get_nowait()
        except queue.Empty:
            break

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

# ================= 模型分步加载线程 =================
def model_load_thread():
    global wake_model, wake_rec, transcribe_model, llm, tts_g2p, tts_kokoro
    try:
        print("[Backend] 正在加载唤醒/转写模型...", file=sys.stderr)
        wake_model = Model(WAKE_MODEL_PATH)
        wake_rec = KaldiRecognizer(wake_model, 16000)
        wake_rec.SetWords(True)
        transcribe_model = wake_model
        print("[Backend] 唤醒/转写模型加载完成", file=sys.stderr)
        send_msg_to_electron({"event": "wake_model_loaded"})
        send_msg_to_electron({"event": "transcribe_model_loaded"})
    except Exception as e:
        print(f"[Backend] 唤醒/转写模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "wake_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return
    try:
        print("[Backend] 正在加载对话模型...", file=sys.stderr)
        llm = Llama(
            model_path=LLM_MODEL_PATH,
            n_ctx=LLM_N_CTX,
            n_threads=LLM_N_THREADS,
            n_batch=LLM_N_BATCH,
            verbose=False,
            chat_format=LLM_CHAT_FORMAT
        )
        print("[Backend] 对话模型加载完成", file=sys.stderr)
        send_msg_to_electron({"event": "llm_model_loaded"})
    except Exception as e:
        print(f"[Backend] 对话模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "llm_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return
    try:
        print("[Backend] 正在加载TTS模型 (misaki + kokoro_onnx)...", file=sys.stderr)
        # 初始化中文 G2P（会自动下载模型到 model_dir，若已存在则直接加载）
        tts_g2p = zh.ZHG2P(version="1.1")
        # 初始化 kokoro_onnx
        tts_kokoro = Kokoro(TTS_ONNX_PATH, TTS_VOICES_BIN_PATH, vocab_config=TTS_CONFIG_PATH)
        print("[Backend] TTS模型加载完成", file=sys.stderr)
        send_msg_to_electron({"event": "tts_model_loaded"})
    except Exception as e:
        print(f"[Backend] TTS模型加载失败: {e}", file=sys.stderr)
        send_msg_to_electron({"event": "error", "type": "tts_model_load_fail", "msg": str(e)})
        fatal_error_event.set()
        return
    print("[Backend] 所有模型加载完成", file=sys.stderr)
    send_msg_to_electron({"event": "full_ready"})
    load_chat_history()
    # 所有模型加载完成后，TTS 播报欢迎语
    welcome_text = "您好指挥官，副官已上线"
    print(f"[Backend] 播放欢迎语：{welcome_text}", file=sys.stderr)
    tts_queue.put(welcome_text)

# ================= TTS 播放线程（新实现） =================
def tts_playback_thread():
    global tts_g2p, tts_kokoro, tts_busy, tts_session_active, transcribe_substate
    print("[Backend] tts_playback_thread 启动", file=sys.stderr)
    while True:
        try:
            text = tts_queue.get(timeout=0.5)
        except queue.Empty:
            with state_lock:
                if tts_busy and not tts_session_active:
                    tts_busy = False
                    if transcribe_substate == "playing_tts":
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
                if transcribe_substate != "generating":  # 生成过程中不发送 start 事件
                    transcribe_substate = "playing_tts"
                    send_msg_to_electron({"event": "tts_started"})

        try:
            # 1. 文本转音素
            phonemes, _ = tts_g2p(text)
            # 2. 合成音频
            samples, sample_rate = tts_kokoro.create(
                phonemes,
                voice=TTS_VOICE_NAME,
                speed=TTS_SPEED,
                is_phonemes=True
            )
            # 3. 播放（可中断）
            sd.play(samples, sample_rate)
            # 轮询等待播放完成，同时监听取消事件
            while sd.get_stream().active:
                if cancel_tts_event.is_set():
                    sd.stop()
                    raise InterruptedError("TTS cancelled")
                time.sleep(0.05)
        except InterruptedError:
            # 被外部取消，静默清理
            pass
        except Exception as e:
            print(f"[Backend] TTS播放错误: {e}", file=sys.stderr)
        finally:
            if cancel_tts_event.is_set():
                # 外部取消：清空队列，重置状态
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    if transcribe_substate == "playing_tts":
                        transcribe_substate = "idle"
            else:
                # 正常结束一段
                with state_lock:
                    if tts_queue.empty():
                        tts_busy = False
                        tts_session_active = False
                        if transcribe_substate == "playing_tts":
                            transcribe_substate = "idle"
                        send_msg_to_electron({"event": "tts_complete"})
                    # 否则保持会话，继续处理下一段

# ================= 对话推理线程（不变） =================
def chat_inference_thread():
    global chat_history, transcribe_substate
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
        full_response = ""
        cancelled = False
        try:
            with chat_lock:
                chat_history.append({"role": "user", "content": user_message, "timestamp": int(time.time() * 1000)})
                truncate_chat_history()
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + [{"role": m["role"], "content": m["content"]} for m in chat_history]
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
                continue

            if full_response:
                tts_queue.put(full_response)

            with chat_lock:
                chat_history.append({"role": "assistant", "content": full_response, "timestamp": int(time.time() * 1000)})
            save_chat_history()
            send_msg_to_electron({"event": "chat_complete"})
            with state_lock:
                if not tts_queue.empty():
                    transcribe_substate = "playing_tts"
                else:
                    transcribe_substate = "idle"

        except Exception as e:
            print(f"[Backend] 对话生成错误: {e}", file=sys.stderr)
            send_msg_to_electron({"event": "error", "type": "chat_generate_fail", "msg": str(e)})
            with state_lock:
                transcribe_substate = "idle"
        finally:
            cancel_generation_event.clear()
            generation_lock.release()

# ================= 主线程：指令处理 =================
def main_thread():
    global current_mode, transcribe_substate, chat_history, tts_busy, tts_session_active
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

            # 全局拦截：如果当前正在生成或播放 TTS，只允许取消/停播操作（以及切换到 wake 关闭窗口）
            with state_lock:
                is_generating = (current_mode == "transcribe" and transcribe_substate == "generating")
                is_playing_tts = (current_mode == "transcribe" and transcribe_substate == "playing_tts")
                is_locked = is_generating or is_playing_tts

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
                        # 停止所有TTS活动
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
                    transcribe_substate = "generating"
                user_content = msg.get("content", "").strip()
                if user_content:
                    user_content = user_content.encode('utf-8', errors='replace').decode('utf-8')
                if not user_content:
                    with state_lock:
                        transcribe_substate = "idle"
                    send_msg_to_electron({"event": "error", "msg": "消息内容不能为空"})
                    continue
                if not llm:
                    with state_lock:
                        transcribe_substate = "idle"
                    send_msg_to_electron({"event": "error", "msg": "对话模型尚未加载完成"})
                    continue
                chat_request_queue.put(user_content)

            elif action == "cancel_generation":
                with state_lock:
                    if not (current_mode == "transcribe" and transcribe_substate == "generating"):
                        send_msg_to_electron({"event": "error", "msg": "当前没有生成任务"})
                        continue
                cancel_generation_event.set()
                cancel_tts_event.set()
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    transcribe_substate = "idle"
                send_msg_to_electron({"event": "tts_stopped"})

            elif action == "tts_stop":
                cancel_tts_event.set()
                while not tts_queue.empty():
                    try:
                        tts_queue.get_nowait()
                    except queue.Empty:
                        break
                sd.stop()
                with state_lock:
                    tts_busy = False
                    tts_session_active = False
                    transcribe_substate = "idle"
                send_msg_to_electron({"event": "tts_stopped"})

            elif action == "tts_play":
                with state_lock:
                    if transcribe_substate == "wake" or tts_busy:
                        send_msg_to_electron({"event": "error", "msg": "当前状态不允许手动播报"})
                        continue
                text = msg.get("text", "").strip()
                if not text:
                    send_msg_to_electron({"event": "error", "msg": "播报文本不能为空"})
                    continue
                tts_queue.put(text)

            elif action == "clear_history":
                with chat_lock:
                    chat_history = []
                save_chat_history()
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
                        "history_count": len(chat_history)
                    }
                send_msg_to_electron(status)

            elif action == "start_loading":
                global model_loading_started
                if not model_loading_started:
                    model_loading_started = True
                    threading.Thread(target=model_load_thread, daemon=True).start()
                    print("[Backend] 已启动模型加载线程", file=sys.stderr)
                else:
                    print("[Backend] 模型加载已启动，无需重复加载", file=sys.stderr)

        except Exception as e:
            print(f"[Backend] 指令处理错误: {e}", file=sys.stderr)
            time.sleep(0.01)

    print("[Backend] 致命错误，后端退出", file=sys.stderr)
    sys.exit(1)

# ================= 程序入口 =================
if __name__ == "__main__":
    send_msg_to_electron({"event": "partial_ready"})
    print("[Backend] 后端启动成功，正在等待模型加载指令...", file=sys.stderr)
    threading.Thread(target=wake_listener_thread, daemon=True).start()
    threading.Thread(target=chat_inference_thread, daemon=True).start()
    threading.Thread(target=tts_playback_thread, daemon=True).start()
    main_thread()