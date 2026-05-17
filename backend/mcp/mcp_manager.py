import json
import time
import datetime
import threading

from .keyword_filter import KeywordFilter
from .tools.todo_tool import TodoTool
from .tools.system_tool import SystemTool
from .tools.time_tool import TimeTool


CLASSIFIER_PROMPT_TEMPLATE = """你是一个严格的意图分类器，只输出JSON格式，不添加任何其他内容。

## 任务
分析用户输入，判断其属于以下哪个工具类别，并提取必要的参数。

## 工具类别及参数说明
{tool_descriptions}

## 规则
1. 严格按照上述类别分类，不得新增类别
2. 若参数不明确，在params中注明"missing": ["参数名"]
3. 若用户同时请求多个操作，对于todo工具返回第一个最明确的操作；对于其他工具按优先级处理
4. 绝对禁止输出任何JSON以外的内容

当前时间：{current_time}

用户输入: {user_input}"""

TOOL_DESCRIPTIONS = {
    "todo": """1. todo: 待办事项管理
   - 子操作: add(添加), list(查询), complete(完成), delete(删除)
   - 参数: content(待办内容), due_date(截止时间, ISO格式YYYY-MM-DD HH:MM), todo_id(待办ID)""",
    "system_status": """2. system_status: 系统状态查询
   - 子操作: cpu, memory, disk, battery, network, all(全部)
   - 参数: sub_op(子操作类型, 默认all)""",
    "time_tool": """3. time_tool: 时间管理工具
   - 子操作: current_time(当前时间), date_calc(日期计算), countdown(倒计时), stopwatch(秒表)
   - 参数: duration(倒计时时长, 分钟), target_date(目标日期, YYYY-MM-DD), stopwatch_action(start/pause/reset/status)""",
}

TRANSITION_TEXTS = {
    "todo": "正在翻阅您的行程计划，指挥官，请稍等……",
    "system_status": "正在扫描帝国终端运行状态，指挥官，请稍等……",
    "time_tool": "正在校准帝国标准时间，指挥官，请稍等……",
}


class MCPManager:
    def __init__(self, zhipu_client, todo_manager, send_msg_fn, tts_queue,
                 state_lock, get_substate, set_substate, fallback_to_llm_fn=None):
        self.zhipu_client = zhipu_client
        self.send_msg = send_msg_fn
        self.tts_queue = tts_queue
        self.state_lock = state_lock
        self._get_substate = get_substate
        self._set_substate = set_substate
        self._fallback_to_llm = fallback_to_llm_fn

        self.keyword_filter = KeywordFilter()

        self.tools = {}
        if todo_manager:
            self.tools["todo"] = TodoTool(todo_manager, zhipu_client)
        self.tools["system_status"] = SystemTool()
        self.tools["time_tool"] = TimeTool(send_msg_fn, tts_queue)

    @property
    def enabled(self):
        return self.zhipu_client is not None

    def process(self, user_message):
        """快速判断是否由MCP接管。返回True表示已接管（不要走LLM），False表示应走正常LLM流程。"""
        if not self.enabled:
            return False

        matched_tools = self.keyword_filter.match(user_message)
        if not matched_tools:
            return False

        with self.state_lock:
            if self._get_substate() != "idle":
                self.send_msg({"event": "error", "msg": "正在处理中，请稍后再试"})
                return True
            self._set_substate("generating")

        threading.Thread(target=self._process_async, args=(user_message, matched_tools), daemon=True).start()
        return True

    def _process_async(self, user_message, matched_tools):
        try:
            now = datetime.datetime.now()
            current_time_str = now.strftime("%Y年%m月%d日 %H:%M")

            tool_name = None
            params = {}

            registered = [t for t in matched_tools if t in self.tools]
            if len(registered) == 1:
                tool_name = registered[0]
            elif registered:
                classification = self._classify(user_message, registered, current_time_str)
                if classification is None:
                    self._fallback_to_llm_and_idle(user_message)
                    return

                tool_name = classification.get("tool", "normal")
                if tool_name == "normal":
                    self._fallback_to_llm_and_idle(user_message)
                    return

                params = classification.get("params", {})
            else:
                self._fallback_to_llm_and_idle(user_message)
                return

            tool = self.tools.get(tool_name)
            if tool is None:
                self._fallback_to_llm_and_idle(user_message)
                return

            params["user_message"] = user_message

            transition_text = TRANSITION_TEXTS.get(tool_name, "正在处理您的请求，指挥官……")
            self._send_stream_message(transition_text)
            self.tts_queue.put({"type": "text", "content": transition_text})

            existing_todos_hint = self._build_todos_hint(tool_name)

            result = tool.execute(params, current_time_str, existing_todos_hint)
            result_text = result.get("result_text", "操作已完成，指挥官。")

            self._send_stream_message(result_text)
            self.tts_queue.put({"type": "text", "content": result_text})

            with self.state_lock:
                self._set_substate("playing_tts")

        except Exception as e:
            print(f"[MCP] 异步处理异常: {e}")
            self._fallback_to_idle()

    def _fallback_to_idle(self):
        with self.state_lock:
            self._set_substate("idle")

    def _fallback_to_llm_and_idle(self, user_message):
        if self._fallback_to_llm:
            self._fallback_to_llm(user_message)
        with self.state_lock:
            self._set_substate("idle")

    def _classify(self, user_message, matched_tools, current_time_str):
        available = {t: TOOL_DESCRIPTIONS[t] for t in matched_tools if t in TOOL_DESCRIPTIONS}
        if not available:
            return None

        desc_lines = [desc for desc in available.values()]
        desc_lines.append(f"{len(available) + 1}. normal: 不属于任何MCP工具，进入正常对话流程")
        tool_descriptions = "\n".join(desc_lines)

        prompt = CLASSIFIER_PROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions,
            current_time=current_time_str,
            user_input=user_message
        )

        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.1,
                max_tokens=300
            )
            raw = response.choices[0].message.content
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                return json.loads(raw[json_start:json_end])
            return None
        except Exception as e:
            print(f"[MCP] GLM分类失败: {e}")
            return None

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

    def _send_stream_message(self, text):
        for char in text:
            self.send_msg({"event": "chat_chunk", "content": char})
            time.sleep(0.02)
        self.send_msg({"event": "chat_complete"})
