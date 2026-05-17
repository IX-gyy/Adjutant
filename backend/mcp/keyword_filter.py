import re

MCP_KEYWORDS = {
    "todo": ["提醒", "待办", "任务", "安排", "别忘了", "要做的事", "记下来", "备忘", "提醒我", "日程", "有什么事情", "计划"],
    "weather": ["天气", "气温", "下雨", "下雪", "晴天", "阴天", "温度", "穿衣建议"],
    "system_status": ["电脑状态", "系统状态", "CPU", "内存占用", "磁盘", "电量", "网络", "卡", "慢"],
    "time_tool": ["时间", "几点", "日期", "几号", "星期", "倒计时", "计时", "还有多少天"],
    "web_search": ["查一下", "搜索", "找资料", "最新消息", "新闻", "百科", "怎么回事"],
}


class KeywordFilter:
    def __init__(self):
        self._compiled = {}
        for tool_name, keywords in MCP_KEYWORDS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            self._compiled[tool_name] = re.compile(pattern)

    def match(self, text):
        matched = []
        for tool_name, pattern in self._compiled.items():
            if pattern.search(text):
                matched.append(tool_name)
        return matched
