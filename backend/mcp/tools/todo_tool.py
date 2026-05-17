import json

TODO_CLASSIFIER_PROMPT = """你是一个星际争霸泰伦帝国AI副官的行动中枢，专门处理待办事项。
当前时间：{current_time}

分析规则：
- 如果指挥官的发言明确要求"提醒"、"别忘了"、"记下来"、"备忘"、"提醒我"等，或者描述了一个需要未来提醒的事项，生成**添加**动作。
- 如果发言是在**查询**待办（如"有什么安排"、"待办列表"、"今天要做什么"），生成**列表查询**动作。
- 如果两者都不是，则 todo_action 为 null。

**添加动作**：需要推理出 content（完整的提醒描述）和 due_date（格式YYYY-MM-DD HH:MM，根据当前时间推算，未指定具体小时则默认为 09:00）。
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
- 不要在输出中包含任何记忆提取相关内容。"""


class TodoTool:
    def __init__(self, todo_manager, zhipu_client):
        self.todo_manager = todo_manager
        self.zhipu_client = zhipu_client

    def execute(self, params, current_time_str, existing_todos_hint):
        todo_action = self._classify_todo(params, current_time_str, existing_todos_hint)
        if todo_action is None:
            return {"tool": "todo", "sub_op": "none", "result_text": "已记录，指挥官。"}

        action_type = todo_action.get("type")
        if action_type == "add":
            return self._handle_add(todo_action)
        elif action_type == "list":
            return self._handle_list(todo_action)
        else:
            return {"tool": "todo", "sub_op": "unknown", "result_text": "信息已同步至帝国战术板，指挥官。"}

    def _classify_todo(self, params, current_time_str, existing_todos_hint):
        system_prompt = TODO_CLASSIFIER_PROMPT.format(current_time=current_time_str)

        user_message = params.get("user_message", "")
        try:
            response = self.zhipu_client.chat.completions.create(
                model="glm-4-flash",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"指挥官的发言：{user_message}\n{existing_todos_hint}\n\n请分析并输出 JSON。"}
                ],
                temperature=0.1,
                max_tokens=600
            )
            raw = response.choices[0].message.content
            json_start = raw.find('{')
            json_end = raw.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                data = json.loads(raw[json_start:json_end])
                return data.get("todo_action")
            return None
        except Exception as e:
            print(f"[MCP-TODO] GLM分类失败: {e}")
            return None

    def _handle_add(self, todo_action):
        items = todo_action.get("items", [])
        if not items or not self.todo_manager:
            return {"tool": "todo", "sub_op": "add", "result_text": "看起来您想添加提醒，但我没能解析出具体内容，请再描述清楚一些。"}

        added = []
        for item in items:
            content = item.get("content", "")
            due_date = item.get("due_date")
            if content:
                self.todo_manager.add_todo(content, due_date)
                added.append(item)

        if len(added) == 1:
            item = added[0]
            due = item.get("due_date")
            if due:
                result_text = f"已为您添加待办事项：{item['content']}，时间：{due}。"
            else:
                result_text = f"已为您添加待办事项：{item['content']}。"
        elif len(added) > 1:
            result_text = f"已为您添加 {len(added)} 项待办，指挥官。"
        else:
            result_text = "看起来您想添加提醒，但我没能解析出具体内容，请再描述清楚一些。"

        return {"tool": "todo", "sub_op": "add", "result_text": result_text, "items": added}

    def _handle_list(self, todo_action):
        if not self.todo_manager:
            return {"tool": "todo", "sub_op": "list", "result_text": "待办系统暂未就绪，指挥官。"}

        todos = self.todo_manager.list_todos("all")
        expired_ids = todo_action.get("expired_ids", [])
        expired_text = ""
        if expired_ids:
            deleted_content = []
            for eid in expired_ids:
                for t in todos:
                    if t["id"] == eid:
                        deleted_content.append(t["content"])
                        self.todo_manager.delete_todo(eid)
                        break
            if deleted_content:
                expired_text = " 以下已过期事项已自动归档：" + "、".join(deleted_content) + "。"

        todos = self.todo_manager.list_todos("all")
        if not todos:
            result_text = "您目前没有待办事项，指挥官。" + expired_text
        else:
            items_str = "\n".join([f"{i+1}. {t['content']}（截止：{t['due_date'] or '无'}）" for i, t in enumerate(todos)])
            result_text = f"您当前的事项如下：\n{items_str}" + expired_text

        return {"tool": "todo", "sub_op": "list", "result_text": result_text}
