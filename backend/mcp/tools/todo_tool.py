import json
import re
import datetime

TODO_CLASSIFIER_PROMPT = """你是一个星际争霸泰伦帝国AI副官的行动中枢，专门处理待办事项。
当前时间：{current_time}

分析规则：
- 如果指挥官的发言明确要求"提醒"、"别忘了"、"记下来"、"备忘"、"提醒我"等，或者描述了一个需要未来提醒的事项，生成**添加**动作。
- 如果发言是在**查询**待办（如"有什么安排"、"待办列表"、"今天要做什么"），生成**列表查询**动作。
- 如果两者都不是，则 todo_action 为 null。

**时间推算规则（严格遵守）**：
- "本周"指本周一到本周日，"下周"指下周一到下周日。
- 日期参考表中已给出本周和下周每天的具体日期，请直接查表使用，不要心算。
- 用户消息中的相对时间表达已被替换为内联绝对日期（如"2026-06-12(周五)"），必须直接使用这些绝对日期，禁止重新推算。
- "下下周四"="下下周周四"=14天后的周四（不是本周四，不是下周周四）。
- "大后天"=今天+3天。
- 未指定具体小时则默认为 09:00。

**添加动作**：需要推理出 content（完整的提醒描述）和 due_date（格式YYYY-MM-DD HH:MM，根据当前时间和日期参考表推算）。
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
- due_date 必须是有效的未来日期，格式严格为 YYYY-MM-DD HH:MM。"""


class TodoTool:
    def __init__(self, todo_manager, zhipu_client, cloud_model="glm-4.7-flash"):
        self.todo_manager = todo_manager
        self.zhipu_client = zhipu_client
        self.cloud_model = cloud_model

    def execute(self, params, current_time_str, existing_todos_hint):
        resolved_dates = params.get("resolved_dates", [])
        resolved_best_date = params.get("resolved_best_date")
        todo_action = self._classify_todo(params, current_time_str, existing_todos_hint,
                                           resolved_dates, resolved_best_date)
        if todo_action is None:
            return {"tool": "todo", "sub_op": "none", "result_text": "已记录，指挥官。"}

        action_type = todo_action.get("type")
        if action_type == "add":
            return self._handle_add(todo_action, resolved_best_date)
        elif action_type == "list":
            return self._handle_list(todo_action)
        else:
            return {"tool": "todo", "sub_op": "unknown", "result_text": "信息已同步至帝国战术板，指挥官。"}

    def _classify_todo(self, params, current_time_str, existing_todos_hint,
                        resolved_dates=None, resolved_best_date=None):
        system_prompt = TODO_CLASSIFIER_PROMPT.format(current_time=current_time_str)

        user_message = params.get("user_message", "")
        try:
            response = self.zhipu_client.chat.completions.create(
                model=self.cloud_model,
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
                todo_action = data.get("todo_action")
                # 校验并修正 GLM 返回的 due_date
                if todo_action and todo_action.get("type") == "add":
                    todo_action = self._validate_and_fix_dates(
                        todo_action, resolved_dates, resolved_best_date)
                return todo_action
            return None
        except Exception as e:
            print(f"[MCP-TODO] GLM分类失败: {e}")
            return None

    def _validate_and_fix_dates(self, todo_action, resolved_dates, resolved_best_date):
        """校验 GLM 返回的 due_date 是否合法，并对比预解析结果修正偏差。"""
        items = todo_action.get("items", [])
        if not items:
            return todo_action

        fixed_items = []
        for item in items:
            due_date = item.get("due_date", "")

            if not due_date or not self._is_valid_date(due_date):
                # GLM 返回的日期无效，尝试从预解析结果中回退
                fallback_date = resolved_best_date
                if resolved_dates:
                    try:
                        best = max(resolved_dates, key=lambda x: x[2] if len(x) > 2 else 0)
                        fallback_date = best[1] if len(best) > 1 else fallback_date
                    except (ValueError, IndexError):
                        pass

                if fallback_date and self._is_valid_date(fallback_date):
                    item["due_date"] = fallback_date
                    print(f"[MCP-TODO] due_date无效'{due_date}'，回退到预解析日期'{fallback_date}'", flush=True)
                else:
                    item["due_date"] = None
                    print(f"[MCP-TODO] due_date无效'{due_date}'，且无预解析日期可用", flush=True)
                fixed_items.append(item)
                continue

            # GLM 返回的日期有效，但可能与预解析结果严重偏离
            # 对比日期部分（忽略时间），如果偏差超过1天则用预解析结果覆盖
            if resolved_best_date and self._is_valid_date(resolved_best_date):
                try:
                    glm_dt = datetime.datetime.strptime(due_date.strip()[:10], "%Y-%m-%d")
                    pre_dt = datetime.datetime.strptime(resolved_best_date.strip()[:10], "%Y-%m-%d")
                    diff_days = abs((glm_dt - pre_dt).days)
                    if diff_days > 1:
                        # 保留 GLM 返回的时间部分，只覆盖日期部分
                        glm_time = due_date.strip()[11:] if len(due_date.strip()) > 10 else "09:00"
                        new_date = pre_dt.strftime("%Y-%m-%d") + " " + glm_time
                        print(f"[MCP-TODO] GLM日期'{due_date}'与预解析'{resolved_best_date}'偏差{diff_days}天，已修正为'{new_date}'", flush=True)
                        item["due_date"] = new_date
                except (ValueError, IndexError):
                    pass

            fixed_items.append(item)

        todo_action["items"] = fixed_items
        return todo_action

    @staticmethod
    def _is_valid_date(date_str):
        """检查日期字符串是否为合法的 YYYY-MM-DD HH:MM 或 YYYY-MM-DD 格式。"""
        if not date_str or not isinstance(date_str, str):
            return False
        # 尝试匹配 YYYY-MM-DD HH:MM
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

    def _handle_add(self, todo_action, resolved_best_date=None):
        items = todo_action.get("items", [])
        if not items or not self.todo_manager:
            return {"tool": "todo", "sub_op": "add", "result_text": "看起来您想添加提醒，但我没能解析出具体内容，请再描述清楚一些。"}

        added = []
        for item in items:
            content = item.get("content", "")
            due_date = item.get("due_date")
            # 最终兜底：如果 due_date 仍然无效，尝试用预解析日期
            if due_date and not self._is_valid_date(due_date):
                if resolved_best_date and self._is_valid_date(resolved_best_date):
                    due_date = resolved_best_date
                else:
                    due_date = None
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
