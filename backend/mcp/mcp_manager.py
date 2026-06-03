import json
import time
import datetime
import threading
import os

from .keyword_filter import KeywordFilter
from .tools.todo_tool import TodoTool
from .tools.system_tool import SystemTool
from .tools.time_tool import TimeTool
from .tools.weather_tool import WeatherTool
from .tools.web_search_tool import WebSearchTool


QWEATHER_DEFAULT_CITY = os.environ.get("QWEATHER_DEFAULT_CITY", "北京")

CLASSIFIER_PROMPT_TEMPLATE = """你是一个严格的意图分类器，只输出JSON格式，不添加任何其他内容。

## 任务
分析用户输入，判断其属于以下哪个工具类别，并提取必要的参数。

## 工具类别及参数说明
{tool_descriptions}

## 核心判断标准
✅ 归为工具：用户明确要求执行某个操作
❌ 归为normal：只是闲聊、抱怨、陈述事实
示例：
- ✅ "今天天气怎么样？" → weather
- ❌ "今天天气不错" → normal
- ✅ "提醒我明天开会" → todo
- ❌ "我明天要开会" → normal

## 上下文参考
{context}

## 规则
1. 严格按照上述类别分类，不得新增类别
2. 若参数不明确，在params中注明"missing": ["参数名"]
3. 若用户同时请求多个操作，对于todo工具返回第一个最明确的操作；对于其他工具按优先级处理
4. 绝对禁止输出任何JSON以外的内容

匹配到的工具关键词：{matched_keywords}
当前时间：{current_time}
用户默认城市：{default_city}

用户输入: {user_input}"""

TOOL_DESCRIPTIONS = {
    "todo": """1. todo: 待办事项管理
   - 子操作: add(添加), list(查询), complete(完成), delete(删除)
   - 参数: content(待办内容), due_date(截止时间, ISO格式YYYY-MM-DD HH:MM), todo_id(待办ID)""",

    "weather": """2. weather: 天气查询
   - 子操作: now(实时天气), today(今日预报), tomorrow(明日预报), week(多日预报), hour(逐小时预报), air(空气质量), warning(灾害预警), astronomy(天文信息), indices(生活指数)
   - 参数:
     * location: 城市名称，必须从用户输入中提取。如用户说"北京天气"→location=北京。如果用户没说城市，location留空""。
     * sub_op: 子操作类型，根据以下规则精准判断
     * indices_type: 仅indices子操作时填写（穿衣/紫外线/感冒/洗车/钓鱼/运动/晾晒/全部）
   - 触发关键词: 天气、气温、下雨、下雪、温度、冷、热、空气质量、AQI、PM2.5、雾霾、预警、台风、暴雨、日出、日落、穿衣、紫外线、感冒、洗车等
   - 注意：这些触发关键词（如"现在""今天""外面""几点"等）经常出现在日常对话中，仅当用户确实在询问天气相关内容时才归类为weather，否则归normal

【天气子操作判断规则（优先级从高到低）】
1. 安全优先：只要包含"预警/台风/暴雨/寒潮/大风"等极端天气词 → sub_op=warning
2. 专项查询：包含"空气质量/AQI/PM2.5/雾霾" → sub_op=air；包含"日出/日落/月相" → sub_op=astronomy
3. 生活决策：询问"穿什么/适合什么/要不要/容易感冒/洗车/钓鱼/晾晒/紫外线" → sub_op=indices
4. 时间粒度：
   - 提及"几点/下午/晚上/上午/中午/小时"等具体时段 → sub_op=hour
   - 仅提及"现在/外面/这会儿/此刻/当前" → sub_op=now
   - 仅提及"今天/今日" → sub_op=today
   - 提及"明天/明日" → sub_op=tomorrow
   - 提及"这周/本周/下周/未来几天/一周" → sub_op=week
5. 歧义默认：仅说"天气"无任何修饰 → sub_op=now，location取默认城市

【真实示例】
- "外面冷不冷？" → {{"tool":"weather", "params":{{"sub_op":"now", "location":""}}}}
- "北京天气怎么样" → {{"tool":"weather", "params":{{"sub_op":"today", "location":"北京"}}}}
- "上海明天会下雨吗" → {{"tool":"weather", "params":{{"sub_op":"tomorrow", "location":"上海"}}}}
- "今天下午几点下雨" → {{"tool":"weather", "params":{{"sub_op":"hour", "location":""}}}}
- "深圳有没有台风预警" → {{"tool":"weather", "params":{{"sub_op":"warning", "location":"深圳"}}}}
- "明天穿什么合适" → {{"tool":"weather", "params":{{"sub_op":"indices", "indices_type":"穿衣", "location":""}}}}
- "北京空气质量怎么样" → {{"tool":"weather", "params":{{"sub_op":"air", "location":"北京"}}}}""",

    "system_status": """3. system_status: 系统状态查询
   - 子操作: cpu, memory, disk, battery, network, all(全部)
   - 参数: sub_op(子操作类型, 默认all)""",

    "time_tool": """4. time_tool: 时间管理工具
   - 子操作: current_time(当前时间), date_calc(日期计算), countdown(倒计时), stopwatch(秒表)
   - 参数: duration(倒计时时长, 分钟), target_date(目标日期, YYYY-MM-DD), stopwatch_action(start/pause/reset/status)""",

    "web_search": """5. web_search: 网络搜索查询
   - 说明：通过百度千帆智能搜索查询实时信息
   - 参数：无特殊参数，直接使用用户输入作为查询内容
   - 触发规则：用户明确要求搜索、查询、查找信息时触发""",
}

TRANSITION_TEXTS = {
    "todo": "正在翻阅您的行程计划，指挥官，请稍等……",
    "weather": "正在连接星际气象卫星，指挥官，请稍等……",
    "system_status": "正在扫描帝国终端运行状态，指挥官，请稍等……",
    "time_tool": "正在校准帝国标准时间，指挥官，请稍等……",
    "web_search": "正在连接星际情报网络，指挥官，请稍等……",
}


class MCPManager:
    def __init__(self, zhipu_client, todo_manager, send_msg_fn, tts_queue,
                 state_lock, get_substate, set_substate, fallback_to_llm_fn=None,
                 default_city="北京", cancel_event=None):
        self.zhipu_client = zhipu_client
        self.send_msg = send_msg_fn
        self.tts_queue = tts_queue
        self.state_lock = state_lock
        self._get_substate = get_substate
        self._set_substate = set_substate
        self._fallback_to_llm = fallback_to_llm_fn
        self.default_city = default_city
        self.cancel_event = cancel_event

        self.keyword_filter = KeywordFilter()

        self.tools = {}
        if todo_manager:
            self.tools["todo"] = TodoTool(todo_manager, zhipu_client)
        self.tools["weather"] = WeatherTool()
        self.tools["system_status"] = SystemTool()
        self.tools["time_tool"] = TimeTool(send_msg_fn, tts_queue)
        self.tools["web_search"] = WebSearchTool(zhipu_client)

    @property
    def enabled(self):
        return self.zhipu_client is not None

    def process(self, user_message, chat_history=None):
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

        threading.Thread(target=self._process_async, args=(user_message, matched_tools, chat_history), daemon=True).start()
        return True

    def _process_async(self, user_message, matched_tools, chat_history=None):
        try:
            now = datetime.datetime.now()
            current_time_str = now.strftime("%Y年%m月%d日 %H:%M")

            tool_name = None
            params = {}

            registered = [t for t in matched_tools if t in self.tools]
            if not registered:
                self._fallback_to_llm_and_idle(user_message)
                return

            if self._needs_classifier(registered):
                classification = self._classify(user_message, registered, current_time_str, chat_history)
                if classification is None:
                    self._fallback_to_llm_and_idle(user_message)
                    return

                tool_name = classification.get("tool", "normal")
                if tool_name == "normal":
                    self._fallback_to_llm_and_idle(user_message)
                    return

                params = classification.get("params", {})
            else:
                tool_name = registered[0]
                if tool_name == "weather":
                    sub_op = self.keyword_filter.get_weather_sub_op(user_message)
                    params["sub_op"] = sub_op
                    if sub_op == "indices":
                        params["indices_type"] = self.keyword_filter.get_indices_type(user_message)

            tool = self.tools.get(tool_name)
            if tool is None:
                self._fallback_to_llm_and_idle(user_message)
                return

            params["user_message"] = user_message

            # 检查是否已被取消
            if self.cancel_event and self.cancel_event.is_set():
                self.send_msg({"event": "chat_cancelled"})
                self._fallback_to_idle()
                return

            transition_text = TRANSITION_TEXTS.get(tool_name, "正在处理您的请求，指挥官……")
            self._send_stream_message(transition_text)
            self.tts_queue.put({"type": "text", "content": transition_text})

            existing_todos_hint = self._build_todos_hint(tool_name)

            # 工具执行前再次检查取消
            if self.cancel_event and self.cancel_event.is_set():
                self.send_msg({"event": "chat_cancelled"})
                self._fallback_to_idle()
                return

            result = tool.execute(params, current_time_str, existing_todos_hint)
            result_text = result.get("result_text", "操作已完成，指挥官。")

            # 结果发送前检查取消
            if self.cancel_event and self.cancel_event.is_set():
                self.send_msg({"event": "chat_cancelled"})
                self._fallback_to_idle()
                return

            self._send_stream_message(result_text)
            self.tts_queue.put({"type": "text", "content": result_text})

            with self.state_lock:
                self._set_substate("playing_tts")

        except Exception as e:
            print(f"[MCP] 异步处理异常: {e}")
            self._fallback_to_idle()

    def _needs_classifier(self, registered):
        return len(registered) > 1

    def _fallback_to_idle(self):
        with self.state_lock:
            self._set_substate("idle")

    def _fallback_to_llm_and_idle(self, user_message):
        if self._fallback_to_llm:
            self._fallback_to_llm(user_message)
        with self.state_lock:
            self._set_substate("idle")

    def _classify(self, user_message, matched_tools, current_time_str, chat_history=None):
        available = {t: TOOL_DESCRIPTIONS[t] for t in matched_tools if t in TOOL_DESCRIPTIONS}
        if not available:
            return None

        desc_lines = [desc for desc in available.values()]
        desc_lines.append(f"{len(available) + 1}. normal: 不属于任何MCP工具，进入正常对话流程")
        tool_descriptions = "\n".join(desc_lines)

        context = ""
        if chat_history and len(chat_history) > 0:
            context = "最近对话历史：\n"
            for msg in chat_history[-3:]:
                role = "指挥官" if msg["role"] == "user" else "副官"
                context += f"{role}: {msg['content']}\n"

        matched_keywords_str = ", ".join(matched_tools)

        prompt = CLASSIFIER_PROMPT_TEMPLATE.format(
            tool_descriptions=tool_descriptions,
            current_time=current_time_str,
            default_city=self.default_city,
            context=context,
            matched_keywords=matched_keywords_str,
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
                max_tokens=400
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
