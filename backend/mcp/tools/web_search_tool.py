import json
import os
import requests

QIANFAN_API_KEY = os.environ.get("QIANFAN_API_KEY", "")


class WebSearchTool:
    def __init__(self, zhipu_client):
        self.zhipu_client = zhipu_client
        self.api_key = QIANFAN_API_KEY

    def set_api_key(self, api_key):
        self.api_key = api_key

    def execute(self, params, current_time_str, _hint):
        user_message = params.get("user_message", "")

        if not self.api_key:
            return {
                "tool": "web_search",
                "result_text": "指挥官，星际情报网络需要百度千帆 API Key 才能接入，请在设置中配置。"
            }

        try:
            print(f"[MCP-WebSearch] 开始搜索，API Key前4位: {self.api_key[:4]}...", flush=True)
            raw_results = self._search(user_message)
            print(f"[MCP-WebSearch] 搜索结果数: {len(raw_results)}", flush=True)
            result_text = self._generate_response(user_message, raw_results, current_time_str)
            return {"tool": "web_search", "result_text": result_text}
        except Exception as e:
            import traceback
            print(f"[MCP-WebSearch] 查询失败: {e}", flush=True)
            traceback.print_exc()
            return {
                "tool": "web_search",
                "result_text": "指挥官，星际网络连接中断，请稍后再试。"
            }

    def _search(self, query):
        url = "https://qianfan.baidubce.com/v2/ai_search"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        payload = {
            "messages": [{"role": "user", "content": query}],
            "stream": False
        }
        response = requests.post(url, headers=headers, json=payload, timeout=15)
        if response.status_code != 200:
            raise Exception(f"搜索API返回状态码 {response.status_code}")

        data = response.json()
        print(f"[MCP-WebSearch] API返回顶层键: {list(data.keys())}", flush=True)
        references = data.get("references", [])
        print(f"[MCP-WebSearch] references数量: {len(references)}", flush=True)
        snippets = []
        for item in references[:5]:
            snippets.append({
                "title": item.get("title", ""),
                "snippet": item.get("content", ""),
                "url": item.get("url", ""),
                "website": item.get("website", "")
            })
        return snippets

    def _generate_response(self, user_query, search_results, current_time_str):
        if not search_results:
            return "指挥官，未检索到相关情报，请尝试换个关键词。"

        references = ""
        for i, item in enumerate(search_results, 1):
            references += f"[{i}] {item['title']}（{item['website']}）\n   {item['snippet']}\n\n"

        prompt = f"""你是泰伦帝国001号高级机械副官。

请根据以下搜索结果，回答指挥官的问题。

要求：
- 称呼用户为"指挥官"
- 回复风格：军旅干练，带一点冷幽默
- 回答必须基于搜索结果，不得编造
- 如果搜索结果中没有相关信息，请明确告知
- 回复长度：100-200字
- 开头标注：【帝国情报部检索结果】

搜索结果：
{references}

指挥官的问题：{user_query}"""

        response = self.zhipu_client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=500,
            timeout=15
        )
        return response.choices[0].message.content.strip()
