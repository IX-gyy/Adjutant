import os
import requests

FORUM_SEARCH_DEFAULT_BASE_URL = "https://ssemarket.cn"


class ForumSearchTool:
    """集市帖子搜索工具 —— 调用小秋无状态问答 API 查询论坛帖子"""

    def __init__(self, zhipu_client):
        self.zhipu_client = zhipu_client
        self.api_token = os.environ.get("SMART_QIU_API_TOKEN", "")
        self.base_url = os.environ.get("SMART_QIU_BASE_URL", FORUM_SEARCH_DEFAULT_BASE_URL).rstrip("/")

    def set_credentials(self, api_token, base_url=None):
        """更新 API 凭据（由 Settings 面板或环境变量传入）"""
        if api_token is not None:
            self.api_token = api_token
        if base_url is not None:
            self.base_url = base_url.rstrip("/")

    def test_connection(self) -> tuple:
        """测试连通性。返回 (success: bool, message: str)"""
        if not self.api_token:
            return False, "未配置 API Token，请在设置中填写小秋 API Token"

        url = f"{self.base_url}/api/v1/agent/external/chat"
        try:
            resp = requests.post(
                url,
                headers={
                    "Content-Type": "application/json",
                    "X-API-Token": self.api_token,
                },
                json={"query": "测试连接"},
                timeout=30,
            )
            if resp.ok:
                return True, "小秋集市搜索连接成功"
            else:
                detail = resp.text.strip()[:100] if resp.text else f"HTTP {resp.status_code}"
                return False, f"连接失败：{detail}"
        except requests.ConnectionError:
            return False, f"无法连接到 {self.base_url}，请检查 API 地址是否正确"
        except requests.Timeout:
            return False, "连接超时，请检查网络或 API 地址"
        except Exception as e:
            return False, f"测试失败：{str(e)[:100]}"

    def execute(self, params, current_time_str, _hint):
        """执行集市帖子搜索。返回 {"tool": "forum_search", "result_text": ...}"""
        user_message = params.get("user_message", "")

        if not self.api_token:
            return {
                "tool": "forum_search",
                "result_text": "指挥官，集市搜索需要配置小秋 API Token，请在设置中填写后再试。"
            }

        try:
            print(f"[MCP-ForumSearch] 开始搜索集市帖子，Base URL: {self.base_url}", flush=True)
            raw_response = self._call_api(user_message)
            print(f"[MCP-ForumSearch] API 返回长度: {len(raw_response)} 字符", flush=True)
            result_text = self._format_response(raw_response, current_time_str)
            return {"tool": "forum_search", "result_text": result_text}
        except requests.ConnectionError:
            print(f"[MCP-ForumSearch] 连接失败: {self.base_url}", flush=True)
            return {
                "tool": "forum_search",
                "result_text": "指挥官，无法连接到集市情报节点，请确认小秋服务是否正常运行。"
            }
        except requests.Timeout:
            return {
                "tool": "forum_search",
                "result_text": "指挥官，集市情报检索超时，请稍后再试。"
            }
        except Exception as e:
            import traceback
            print(f"[MCP-ForumSearch] 查询失败: {e}", flush=True)
            traceback.print_exc()
            return {
                "tool": "forum_search",
                "result_text": "指挥官，集市情报检索暂时不可用，请稍后再试。"
            }

    def _call_api(self, query: str) -> str:
        """调用小秋无状态问答 API"""
        url = f"{self.base_url}/api/v1/agent/external/chat"
        resp = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-API-Token": self.api_token,
            },
            json={"query": query},
            timeout=120,
        )

        if resp.status_code == 400:
            body = resp.text.strip()
            raise Exception(f"请求参数错误：{body}")
        elif resp.status_code == 401:
            raise Exception("API Token 无效，请检查设置")
        elif resp.status_code == 502:
            body = resp.text.strip()
            raise Exception(f"小秋服务异常：{body}")
        elif not resp.ok:
            body = resp.text.strip() or resp.reason
            raise Exception(f"HTTP {resp.status_code}: {body}")

        return resp.text

    def _format_response(self, raw_text: str, current_time_str: str) -> str:
        """将小秋返回的原文润色为副官口吻。
        保留所有帖子标题和链接，不压缩信息，仅转换语气风格。
        GLM 不可用时直接返回原文。"""
        if self.zhipu_client:
            try:
                return self._restyle_with_glm(raw_text, current_time_str)
            except Exception as e:
                print(f"[MCP-ForumSearch] GLM 润色失败: {e}", flush=True)
                # GLM 失败时直接返回原文（含所有链接）
                pass

        return f"【帝国情报部·集市检索结果】\n\n{raw_text}"

    def _restyle_with_glm(self, raw_text: str, _current_time_str: str) -> str:
        """用 GLM-4-Flash 将搜索结果转为副官口吻，同时保留全部帖子链接和分类结构。"""
        prompt = f"""你是泰伦帝国001号高级机械副官。请将以下集市帖子的搜索结果，以指挥官能理解的方式汇报。

严格要求：
- 称呼用户为"指挥官"
- 回复风格：军旅干练，带一点冷幽默
- 必须保留所有帖子的标题和链接，格式为 Markdown 链接 [标题](URL)
- 必须保留原文中的分类/分组结构（如"保研流程类""经验分享类"等）
- 如果原文末尾有总结段落，用自己的话重新组织，但不丢失关键信息
- 原文中没有的信息绝对不要编造
- 开头标注：【帝国情报部·集市检索结果】
- 不要压缩信息量，原文中列出的每一条帖子都要保留

以下是集市原始搜索结果，请按上述要求改写：

{raw_text}"""

        response = self.zhipu_client.chat.completions.create(
            model="glm-4-flash",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=1000,
            timeout=30
        )
        return response.choices[0].message.content.strip()
