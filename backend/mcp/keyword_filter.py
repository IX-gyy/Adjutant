import re

MCP_KEYWORDS = {
    "todo": ["提醒", "待办", "任务", "安排", "别忘了", "要做的事", "记下来", "备忘", "提醒我", "日程", "有什么事情", "计划"],
    "weather": [
        "天气", "气温", "温度", "下雨", "下雪", "晴天", "阴天", "刮风", "风大", "冷", "热",
        "降温", "升温", "降雨", "降雪", "雾", "霜", "霾", "雾霾",
        "空气质量", "PM2.5", "PM10", "AQI", "空气指数", "污染",
        "预警", "台风", "暴雨", "大风", "寒潮", "高温", "雷电", "冰雹",
        "日出", "日落", "月相", "月出", "月落", "月亮",
        "穿衣", "穿", "紫外线", "感冒", "洗车", "钓鱼", "运动", "晾晒", "生活指数",
        "现在", "外面", "这会儿", "当前", "实时",
        "今天", "今日", "明天", "明日", "这周", "本周", "下周", "未来几天",
        "几点", "下午", "晚上", "上午", "中午", "小时", "时段",
    ],
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

    def get_weather_sub_op(self, text):
        warning_keywords = ["预警", "台风", "暴雨", "大风", "寒潮", "高温", "雷电", "冰雹"]
        air_keywords = ["空气质量", "AQI", "PM2.5", "PM10", "雾霾", "空气指数", "污染"]
        astronomy_keywords = ["日出", "日落", "月相", "月出", "月落", "月亮"]
        hour_keywords = ["几点", "下午", "晚上", "上午", "中午", "小时", "时段"]
        now_keywords = ["现在", "外面", "这会儿", "当前", "实时"]
        today_keywords = ["今天", "今日"]
        tomorrow_keywords = ["明天", "明日"]
        week_keywords = ["这周", "本周", "下周", "未来几天", "一周"]

        for kw in warning_keywords:
            if kw in text:
                return "warning"
        for kw in air_keywords:
            if kw in text:
                return "air"
        for kw in astronomy_keywords:
            if kw in text:
                return "astronomy"
        if self.get_indices_type(text) != "全部" or "生活指数" in text:
            return "indices"
        for kw in hour_keywords:
            if kw in text:
                return "hour"
        for kw in now_keywords:
            if kw in text:
                return "now"
        for kw in today_keywords:
            if kw in text:
                return "today"
        for kw in tomorrow_keywords:
            if kw in text:
                return "tomorrow"
        for kw in week_keywords:
            if kw in text:
                return "week"
        return "now"

    def get_indices_type(self, text):
        indices_map = [
            (["穿什么", "穿衣", "外套", "穿衣服", "穿"], "穿衣"),
            (["紫外线", "防晒"], "紫外线"),
            (["感冒", "容易生病", "着凉"], "感冒"),
            (["洗车"], "洗车"),
            (["钓鱼"], "钓鱼"),
            (["运动", "锻炼", "跑步", "健身"], "运动"),
            (["晾晒", "晒被子", "晒衣服"], "晾晒"),
            (["旅游", "出行", "出去玩"], "旅游"),
        ]
        for keywords, indices_type in indices_map:
            for kw in keywords:
                if kw in text:
                    return indices_type
        return "全部"
