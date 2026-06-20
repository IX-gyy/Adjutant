import json
import sys
import time
import datetime
import threading
import os

from .keyword_filter import KeywordFilter, HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, CONFIDENCE_GAP
from .tools.todo_tool import TodoTool
from .tools.system_tool import SystemTool
from .tools.time_tool import TimeTool
from .tools.weather_tool import WeatherTool
from .tools.web_search_tool import WebSearchTool
from .tools.forum_search_tool import ForumSearchTool
from .tools.time_resolver import pre_resolve_message, build_date_reference


QWEATHER_DEFAULT_CITY = os.environ.get("QWEATHER_DEFAULT_CITY", "北京")

# ============================================================================
# GLM 分类器 Prompt —— 仅用于多意图平局时的简化二元确认（改动2）
# ============================================================================
TIEBREAKER_PROMPT = """你是一个快速的意图确认器。用户说了一句话，有两个可能的理解方向。
请判断用户的真实意图更接近哪一个。

选项 A: {intent_a} — {desc_a}
选项 B: {intent_b} — {desc_b}

只输出 A 或 B，不要输出任何其他内容。

用户输入: {user_input}"""

INTENT_SIMPLE_DESC = {
    "todo": "用户想添加或查看待办提醒事项",
    "weather": "用户想查询天气信息",
    "system_status": "用户想了解电脑系统运行状态",
    "time_tool": "用户想查询时间、日期或使用计时功能",
    "web_search": "用户想在网络上搜索信息",
    "forum_search": "用户想搜索集市/论坛的帖子",
}

# ============================================================================
# 方案A：TODO 追问上下文追踪 —— 肯定/否定关键词检测
# ============================================================================
PENDING_TODO_TTL = 3

AFFIRMATION_KEYWORDS = [
    # 正式中文
    "是的", "好的", "好", "可以", "行", "嗯", "对", "没错", "需要",
    "请", "麻烦", "帮我", "麻烦你", "帮我添加", "帮我设置", "帮我记",
    "记一下", "记录一下", "添加", "设置", "创建", "安排",
    # 口语/简略
    "好啊", "好呀", "好吧", "好的呀", "行吧", "行啊", "成", "成啊",
    "嗯嗯", "嗯好", "可以啊", "可以的", "要的", "要", "搞", "搞吧",
    "整", "整一个", "来吧", "来", "加一个", "加上", "记上", "记上吧",
    "那就", "那就麻烦", "有劳", "辛苦了", "拜托",
    # 英文
    "yes", "ok", "okay", "yeah", "yep", "sure", "please",
    "alright", "fine", "go ahead", "do it", "add", "yup", "ya",
    "yea", "k", "kk", "okie", "okey",
]

NEGATION_KEYWORDS = [
    # 正式中文
    "不用了", "不要了", "算了", "不了", "不需要", "不用", "不必了",
    "取消", "别", "不要", "别加了", "别记录了", "不用麻烦了",
    # 口语
    "算了算了", "还是算了", "不用啦", "不要啦", "改天", "改到其他",
    "再说", "先不用", "先不要", "暂时不用", "暂时不要", "不用管",
    "没关系的", "没事", "没事儿",
    # 英文
    "no", "nope", "nah", "never mind", "nevermind", "cancel",
    "skip", "ignore", "don't", "not now", "not anymore",
    "changed my mind",
]

# ============================================================================
# 过渡语
# ============================================================================
TRANSITION_TEXTS = {
    "todo": "正在翻阅您的行程计划，指挥官，请稍等……",
    "weather": "正在连接星际气象卫星，指挥官，请稍等……",
    "system_status": "正在扫描帝国终端运行状态，指挥官，请稍等……",
    "time_tool": "正在校准帝国标准时间，指挥官，请稍等……",
    "web_search": "正在连接星际情报网络，指挥官，请稍等……",
    "forum_search": "正在检索集市帖子，指挥官，请稍等……",
}

# 结果返回后的 TTS 引导语（用于结果较长、不适合完整朗读的工具）
TTS_GUIDANCE_TEXTS = {
    "forum_search": "指挥官，集市情报检索完毕，请查看屏幕上的详细结果。",
    "web_search": "指挥官，网络情报检索完毕，请查看屏幕上的详细结果。",
    "weather": "指挥官，气象情报已获取，请查看屏幕上的详细结果。",
    "system_status": "指挥官，系统扫描完成，请查看屏幕上的报告。",
}

# ============================================================================
# 改动4：中等置信度 TODO 追问 prompt
# ============================================================================
TODO_FOLLOWUP_PROMPT = """指挥官说："{user_message}"

这听上去像是指挥官提到了一个未来的计划或安排。请你以副官的口吻：
1. 先自然地回应指挥官的话（1-2句）
2. 然后自然地询问指挥官是否需要将这件事记录为待办提醒（1句）
3. 整体回复2-3句话，40-80字

对话历史：
{context}"""


class MCPManager:
    def __init__(self, zhipu_client, todo_manager, send_msg_fn, tts_queue,
                 state_lock, get_substate, set_substate, fallback_to_llm_fn=None,
                 default_city="北京", cancel_event=None, keyword_filter=None):
        self.zhipu_client = zhipu_client
        self.send_msg = send_msg_fn
        self.tts_queue = tts_queue
        self.state_lock = state_lock
        self._get_substate = get_substate
        self._set_substate = set_substate
        self._fallback_to_llm = fallback_to_llm_fn
        self.default_city = default_city
        self.cancel_event = cancel_event

        self.keyword_filter = keyword_filter if keyword_filter is not None else KeywordFilter()

        # 方案A：TODO 追问上下文追踪
        self.pending_todo_context = None

        self.tools = {}
        if todo_manager:
            self.tools["todo"] = TodoTool(todo_manager, zhipu_client)
        self.tools["weather"] = WeatherTool()
        self.tools["system_status"] = SystemTool()
        self.tools["time_tool"] = TimeTool(send_msg_fn, tts_queue)
        self.tools["web_search"] = WebSearchTool(zhipu_client)
        self.tools["forum_search"] = ForumSearchTool(zhipu_client)

    @property
    def enabled(self):
        return self.zhipu_client is not None

    # ========================================================================
    # 主入口
    # ========================================================================

    def process(self, user_message, chat_history=None):
        """
        新的意图检测流水线：
          1. 显式指令快速通道（改动3）
          2. 嵌入相似度匹配（改动1）
             - 高置信度 → 直接路由
             - 中等置信度 TODO → 追问确认（改动4）
             - 多意图平局 → GLM 简化确认（改动2）
          3. 关键词匹配后备（仅当嵌入模型不可用时）
        """
        if not self.enabled:
            return False

        with self.state_lock:
            if self._get_substate() != "idle":
                self.send_msg({"event": "error", "msg": "正在处理中，请稍后再试"})
                return True
            self._set_substate("generating")

        handled = self._try_route(user_message, chat_history)
        if not handled:
            with self.state_lock:
                self._set_substate("idle")
        return handled

    # ========================================================================
    # 方案A：TODO 追问上下文追踪
    # ========================================================================

    @staticmethod
    def _detect_affirmation(user_message):
        msg_lower = user_message.lower().strip()
        return any(kw in msg_lower for kw in AFFIRMATION_KEYWORDS)

    @staticmethod
    def _detect_negation(user_message):
        msg_lower = user_message.lower().strip()
        return any(kw in msg_lower for kw in NEGATION_KEYWORDS)

    def _check_pending_todo(self, user_message, chat_history):
        """检查 pending TODO 上下文。返回：
        'handled'  — 用户确认，已直接执行 TODO add
        'cleared'  — 用户否定/放弃，已清除 pending，继续正常路由
        'continue' — 既非肯定也非否定，继续正常路由（TTL 后续处理）
        None       — 无 pending 上下文
        """
        ctx = self.pending_todo_context
        if ctx is None:
            return None

        # 优先检测否定（安全性）
        if self._detect_negation(user_message):
            print(f"[MCP] TODO pending: 用户否定，清除上下文", file=sys.stderr, flush=True)
            self.pending_todo_context = None
            return 'cleared'

        # 检测肯定：关键词 + todo 语义分数 > 0.35（防止纯闲聊"好的"误触发）
        if self._detect_affirmation(user_message):
            scores = self.keyword_filter.match_semantic(user_message)
            todo_score = scores.get("todo", 0) if scores else 0
            if todo_score > 0.35:
                print(f"[MCP] TODO pending: 用户确认 (todo_score={todo_score:.3f})，直接执行 TODO add", file=sys.stderr, flush=True)
                original_msg = ctx["original_message"]
                original_history = ctx.get("original_history")
                self.pending_todo_context = None
                threading.Thread(
                    target=self._process_async,
                    args=(original_msg, ["todo"], original_history, {}),
                    daemon=True
                ).start()
                return 'handled'
            else:
                print(f"[MCP] TODO pending: 肯定词命中但 todo_score={todo_score:.3f} 过低，放行正常路由", file=sys.stderr, flush=True)

        return 'continue'

    def _try_route(self, user_message, chat_history):
        # ---- 第0层：TODO 追问上下文追踪（方案A） ----
        pending_result = self._check_pending_todo(user_message, chat_history)
        if pending_result == 'handled':
            return True

        # ---- 第1层：显式指令快速通道（改动3） ----
        explicit = self.keyword_filter.match_explicit(user_message)
        if explicit:
            tool_name, pre_params = explicit
            if tool_name in self.tools:
                print(f"[MCP] 显式指令直达: {tool_name}", file=sys.stderr, flush=True)
                if pending_result == 'continue' and tool_name == "todo":
                    self.pending_todo_context = None
                threading.Thread(
                    target=self._process_async,
                    args=(user_message, [tool_name], chat_history, pre_params),
                    daemon=True
                ).start()
                return True

        # ---- 第2层：嵌入相似度匹配（改动1） ----
        scores = self.keyword_filter.match_semantic(user_message)

        if scores:
            intents = list(scores.keys())
            best_intent = intents[0]
            best_score = scores[best_intent]
            second_score = scores[intents[1]] if len(intents) > 1 else 0

            print(f"[MCP] 语义匹配: {best_intent}={best_score:.3f}, #2={intents[1] if len(intents) > 1 else 'N/A'}={second_score:.3f}", file=sys.stderr, flush=True)

            # 情况A：高置信度单意图 → 直接路由
            if best_score >= HIGH_CONFIDENCE and (best_score - second_score) >= CONFIDENCE_GAP:
                if best_intent in self.tools:
                    print(f"[MCP] 高置信度路由: {best_intent}", file=sys.stderr, flush=True)
                    if pending_result == 'continue' and best_intent == "todo":
                        self.pending_todo_context = None
                    threading.Thread(
                        target=self._process_async,
                        args=(user_message, [best_intent], chat_history, {}),
                        daemon=True
                    ).start()
                    return True

            # 情况B：中等置信度 TODO → 追问确认（改动4）
            if best_intent == "todo" and best_score >= MEDIUM_CONFIDENCE:
                print(f"[MCP] 中等置信度TODO，进入追问流程 (score={best_score:.3f})", file=sys.stderr, flush=True)
                # 新追问替换旧 pending
                if self.pending_todo_context is not None:
                    print(f"[MCP] TODO pending: 新的 TODO 追问替换旧上下文", file=sys.stderr, flush=True)
                self.pending_todo_context = None
                threading.Thread(
                    target=self._handle_medium_confidence_todo,
                    args=(user_message, chat_history),
                    daemon=True
                ).start()
                return True

            # 情况C：多意图平局 → GLM 简化确认（改动2）
            if best_score - second_score < CONFIDENCE_GAP and second_score >= MEDIUM_CONFIDENCE:
                second_intent = intents[1]
                if best_intent in self.tools and second_intent in self.tools:
                    print(f"[MCP] 意图平局，GLM二选一: {best_intent} vs {second_intent}", file=sys.stderr, flush=True)
                    threading.Thread(
                        target=self._process_async,
                        args=(user_message, [best_intent, second_intent], chat_history, {}),
                        daemon=True
                    ).start()
                    return True

            # 情况D：所有分数都低 → 跳过语义路由，进入关键词后备层
            print(f"[MCP] 所有意图置信度不足", file=sys.stderr, flush=True)

        # ---- 第3层：关键词匹配后备（嵌入模型不可用时） ----
        matched_tools = self.keyword_filter.match(user_message)
        if matched_tools:
            registered = [t for t in matched_tools if t in self.tools]
            if registered:
                print(f"[MCP] 关键词后备匹配: {registered}", file=sys.stderr, flush=True)
                if pending_result == 'continue':
                    if "todo" in registered and len(registered) == 1:
                        self.pending_todo_context = None
                threading.Thread(
                    target=self._process_async,
                    args=(user_message, registered, chat_history, {}),
                    daemon=True
                ).start()
                return True

        # TTL 管理：pending 追问未确认，用户转移话题
        if pending_result == 'continue':
            self.pending_todo_context["ttl"] -= 1
            print(f"[MCP] TODO pending: 用户未确认，TTL={self.pending_todo_context['ttl']}", file=sys.stderr, flush=True)
            if self.pending_todo_context["ttl"] <= 0:
                print(f"[MCP] TODO pending: TTL 耗尽，清除上下文", file=sys.stderr, flush=True)
                self.pending_todo_context = None

        return False

    # ========================================================================
    # 异步工具执行
    # ========================================================================

    def _process_async(self, user_message, matched_tools, chat_history=None, pre_params=None):
        try:
            now = datetime.datetime.now()
            weekday_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
            current_time_str = now.strftime("%Y年%m月%d日") + f" {weekday_zh[now.weekday()]} " + now.strftime("%H:%M")
            # 使用共享函数构建日期参考表
            current_time_str += "\n日期参考：" + build_date_reference(now)

            # 预解析用户消息中的相对时间表达
            resolved_info = pre_resolve_message(user_message, now)

            tool_name = None
            params = pre_params if pre_params else {}

            registered = [t for t in matched_tools if t in self.tools]
            if not registered:
                self._fallback_to_llm_and_idle(user_message)
                return

            if len(registered) > 1:
                # 多个工具 → GLM 二选一确认（改动2）
                classification = self._classify(user_message, registered, current_time_str, chat_history)
                if classification is None:
                    if self.cancel_event and self.cancel_event.is_set():
                        self._cancel_and_notify()
                        return
                    self._fallback_to_llm_and_idle(user_message)
                    return

                tool_name = classification.get("tool", "normal")
                if tool_name == "normal":
                    self._fallback_to_llm_and_idle(user_message)
                    return

                # 合并分类器返回的参数
                cls_params = classification.get("params", {})
                if cls_params:
                    params.update(cls_params)
            else:
                # 单一工具 → 直接执行
                tool_name = registered[0]

            # 天气参数提取（覆盖单工具和 GLM 二选一两种路径）
            if tool_name == "weather" and not params.get("sub_op"):
                params["sub_op"] = self.keyword_filter.get_weather_sub_op(user_message)
                if params["sub_op"] == "indices":
                    params["indices_type"] = self.keyword_filter.get_indices_type(user_message)
                if not params.get("location"):
                    params["location"] = self.keyword_filter.get_weather_location(user_message)

            # 时间参数提取
            if tool_name == "time_tool" and not params.get("sub_op"):
                params["sub_op"] = self.keyword_filter.get_time_sub_op(user_message)

            tool = self.tools.get(tool_name)
            if tool is None:
                self._fallback_to_llm_and_idle(user_message)
                return

            params["user_message"] = resolved_info.get("enriched_message", user_message)
            params["resolved_dates"] = resolved_info.get("resolved", [])
            params["resolved_best_date"] = resolved_info.get("best_date_str")

            if self.cancel_event and self.cancel_event.is_set():
                self._cancel_and_notify()
                return

            # 方案A：执行 TODO 时清除 pending 上下文
            if tool_name == "todo":
                self.pending_todo_context = None

            transition_text = TRANSITION_TEXTS.get(tool_name, "正在处理您的请求，指挥官……")
            self._send_stream_message(transition_text)
            self.tts_queue.put({"type": "text", "content": transition_text})
            # 过渡语 TTS 在 generating 状态下入队，TTS 线程会跳过 tts_started
            # 这里手动补发，确保前端显示停止按钮（方案A）
            self.send_msg({"event": "tts_started"})

            existing_todos_hint = self._build_todos_hint(tool_name)

            if self.cancel_event and self.cancel_event.is_set():
                self._cancel_and_notify()
                return

            result = tool.execute(params, current_time_str, existing_todos_hint)
            result_text = result.get("result_text", "操作已完成，指挥官。")

            if self.cancel_event and self.cancel_event.is_set():
                self._cancel_and_notify()
                return

            self._send_stream_message(result_text)

            if self.cancel_event and self.cancel_event.is_set():
                self._cancel_and_notify()
                return

            # 部分工具结果较长，TTS 只播报引导语，不朗读完整结果
            guidance = TTS_GUIDANCE_TEXTS.get(tool_name)
            if guidance:
                self.tts_queue.put({"type": "text", "content": guidance})
            else:
                self.tts_queue.put({"type": "text", "content": result_text})

            with self.state_lock:
                self._set_substate("playing_tts")

        except Exception as e:
            print(f"[MCP] 异步处理异常: {e}", file=sys.stderr, flush=True)
            self._fallback_to_idle()

    # ========================================================================
    # 改动4：中等置信度 TODO 追问
    # ========================================================================

    def _handle_medium_confidence_todo(self, user_message, chat_history=None):
        """当嵌入模型判断用户可能在说 TODO，但不够确定时，主动追问确认。"""
        try:
            context = ""
            if chat_history and len(chat_history) > 0:
                recent = chat_history[-2:]  # 最近两轮
                context = "\n".join([
                    f"{'指挥官' if m['role'] == 'user' else '你'}: {m['content']}"
                    for m in recent
                ])

            prompt = TODO_FOLLOWUP_PROMPT.format(
                user_message=user_message,
                context=context if context else "（无对话历史）"
            )

            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": "你是泰伦帝国001号高级机械副官。称呼用户为'指挥官'。军旅干练，带一点冷幽默。回复2-3句话，40-80字。**绝对不要**在回复中输出'副官：'、'副官:'或任何角色前缀标签。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=120,
                timeout=15.0
            )
            reply = response.choices[0].message.content

            # 去除 GLM 可能在回复中输出的角色前缀
            reply = self._strip_role_prefix(reply)

            if self.cancel_event and self.cancel_event.is_set():
                self._cancel_and_notify()
                return

            self._send_stream_message(reply)
            self.tts_queue.put({"type": "text", "content": reply})
            # 同 _process_async：TTS 在 generating 状态入队，手动补发 tts_started
            self.send_msg({"event": "tts_started"})

            with self.state_lock:
                self._set_substate("playing_tts")

            # 方案A：设置 pending 上下文，等待用户确认/否认
            self.pending_todo_context = {
                "original_message": user_message,
                "original_history": chat_history,
                "ttl": PENDING_TODO_TTL,
            }
            print(f"[MCP] TODO pending: 已设置追问上下文，TTL={PENDING_TODO_TTL}", file=sys.stderr, flush=True)

        except Exception as e:
            print(f"[MCP] TODO追问失败: {e}", file=sys.stderr, flush=True)
            self._fallback_to_llm_and_idle(user_message)

    # ========================================================================
    # 改动2：简化 GLM 分类器 —— 只做二选一
    # ========================================================================

    def _classify(self, user_message, matched_tools, current_time_str, chat_history=None):
        # 单工具直接返回
        if len(matched_tools) == 1:
            return {"tool": matched_tools[0], "params": {}}

        # 多工具（实际应该是2个）做二选一
        intent_a = matched_tools[0]
        intent_b = matched_tools[1]
        desc_a = INTENT_SIMPLE_DESC.get(intent_a, intent_a)
        desc_b = INTENT_SIMPLE_DESC.get(intent_b, intent_b)

        prompt = TIEBREAKER_PROMPT.format(
            intent_a=intent_a,
            desc_a=desc_a,
            intent_b=intent_b,
            desc_b=desc_b,
            user_input=user_message
        )

        if self.cancel_event and self.cancel_event.is_set():
            return None

        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": prompt},
                ],
                temperature=0.1,
                max_tokens=10,
                timeout=15.0
            )
            raw = response.choices[0].message.content.strip().upper()

            if raw.startswith("A"):
                return {"tool": intent_a, "params": {}}
            elif raw.startswith("B"):
                return {"tool": intent_b, "params": {}}
            else:
                # 输出异常，回退到第一个工具
                print(f"[MCP] GLM二选一输出异常: '{raw}'，回退到 {intent_a}", file=sys.stderr, flush=True)
                return {"tool": intent_a, "params": {}}

        except Exception as e:
            print(f"[MCP] GLM二选一失败: {e}，回退到语义第一意图 {intent_a}", file=sys.stderr, flush=True)
            return {"tool": intent_a, "params": {}}

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _fallback_to_idle(self):
        with self.state_lock:
            self._set_substate("idle")

    def _cancel_and_notify(self):
        self.send_msg({"event": "chat_cancelled"})
        self.send_msg({"event": "tts_stopped"})
        with self.state_lock:
            self._set_substate("idle")

    def _fallback_to_llm_and_idle(self, user_message):
        if self._fallback_to_llm:
            self._fallback_to_llm(user_message)
        with self.state_lock:
            self._set_substate("idle")

    def _build_todos_hint(self, tool_name):
        if tool_name != "todo":
            return ""
        todo_tool = self.tools.get("todo")
        if todo_tool is None or todo_tool.todo_manager is None:
            return ""
        todos = todo_tool.todo_manager.list_todos("all")
        if not todos:
            return ""
        return "\n当前待办事项列表：\n" + "\n".join(
            [f"id={t['id']}, due={t['due_date']}, status={t['status']}, content={t['content']}" for t in todos]
        )

    @staticmethod
    def _strip_role_prefix(text):
        prefixes = ["副官：", "副官:", "副官 ", "指挥官：", "指挥官:", "指挥官 ", "<|im_start|>", "<|im_end|>"]
        for p in prefixes:
            if text.startswith(p):
                return text[len(p):]
        return text

    def _send_stream_message(self, text):
        for char in text:
            if self.cancel_event and self.cancel_event.is_set():
                return
            self.send_msg({"event": "chat_chunk", "content": char})
            time.sleep(0.02)
        self.send_msg({"event": "chat_complete"})
