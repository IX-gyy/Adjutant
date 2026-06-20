import os
import sys
import re
import threading
import numpy as np

# ============================================================================
# 阈值配置
# ============================================================================
HIGH_CONFIDENCE = 0.70       # 高置信度：直接路由到工具
MEDIUM_CONFIDENCE = 0.55     # 中等置信度：TODO 走追问确认流程
CONFIDENCE_GAP = 0.08        # 最高分与次高分的最小差距

# ============================================================================
# MCP 关键词表（已瘦身：移除高频日常词）
# ============================================================================
MCP_KEYWORDS = {
    "todo": [
        "提醒", "待办", "任务", "安排", "别忘了", "要做的事",
        "记下来", "备忘", "提醒我", "日程", "有什么事情", "计划",
    ],
    # 瘦身后的天气词：只保留气象核心术语
    # 移除的日常词（不再参与触发）：现在、外面、今天、明天、冷、热、下午、晚上、几点、小时、时段
    "weather": [
        "天气", "气温", "温度", "下雨", "下雪", "晴天", "阴天", "刮风", "风大",
        "降温", "升温", "降雨", "降雪", "雾", "霜", "霾", "雾霾",
        "空气质量", "PM2.5", "PM10", "AQI", "空气指数", "污染",
        "预警", "台风", "暴雨", "大风", "寒潮", "高温", "雷电", "冰雹",
        "日出", "日落", "月相", "月出", "月落", "月亮",
        "穿衣", "穿", "紫外线", "感冒", "洗车", "钓鱼", "运动", "晾晒", "生活指数",
    ],
    "system_status": ["电脑状态", "系统状态", "CPU", "内存占用", "磁盘", "电量", "网络", "卡", "慢"],
    "time_tool": ["时间", "几点", "日期", "几号", "星期", "倒计时", "计时", "还有多少天"],
    "web_search": ["查一下", "搜索", "找资料", "最新消息", "新闻", "百科", "怎么回事"],
    "forum_search": [
        "搜帖子", "查帖子", "找帖子", "论坛帖子", "集市帖子",
        "论坛搜索", "帖子搜索", "集市搜索", "搜论坛", "查论坛",
    ],
}

# ============================================================================
# 显式指令快速通道：100% 确定，不走模型
# ============================================================================
EXPLICIT_ROUTES = [
    # (关键词列表, 工具名, 默认参数)
    # TODO 添加类 —— 显式触发词
    (["提醒我", "别忘了", "记一下", "帮我记", "帮我加个提醒", "帮我加一个提醒"], "todo", {"sub_op": "add"}),
    # TODO 查询类
    (["待办列表", "有什么安排", "今天要做什么", "还有什么事", "我的任务"], "todo", {"sub_op": "list"}),
    # 天气类 —— "天气" 是高度特异性词
    (["天气", "会下雨", "会下雪", "温度多少", "气温多少", "台风"], "weather", {}),
    # 时间类
    (["现在几点", "今天几号", "星期几", "现在什么时间", "当前时间"], "time_tool", {"sub_op": "current_time"}),
    # 日期计算类 —— "距离...还有几天" 模式
    (["距离", "还有几天", "还剩几天", "还有多少天"], "time_tool", {"sub_op": "date_calc"}),
    # 倒计时
    (["倒计时", "计时"], "time_tool", {"sub_op": "countdown"}),
    # 系统类
    (["电脑状态", "系统状态", "CPU占用", "内存使用", "磁盘空间", "电脑好卡", "电脑卡", "电脑慢", "电脑性能", "系统卡"], "system_status", {"sub_op": "all"}),
    # 搜索类
    (["帮我查", "搜索一下", "帮我搜", "帮我找"], "web_search", {}),
    # 论坛帖子搜索类
    (["搜帖子", "查帖子", "找帖子", "论坛搜索", "集市搜索",
      "搜一下论坛", "查一下论坛", "论坛里搜", "搜论坛"], "forum_search", {}),
]

# ============================================================================
# 意图示例库 —— 用于嵌入相似度匹配
# ============================================================================
INTENT_EXAMPLES = {
    "todo": [
        "提醒我明天下午三点开会",
        "别忘了买牛奶",
        "帮我记一下下周要去体检",
        "我明天要开会需要提醒",
        "下周三记得提醒我去面试",
        "我要记住今天要交报告",
        "得提醒自己下午有课",
        "记下来明天是截止日期",
        "帮我加一个提醒周五交材料",
        "周六有个约会别忘了",
        "这周五要出差需要记住",
        "后天要去面试提醒我一下",
        "明天记得给客户回电话",
        "下周一早上有个重要会议",
        "今晚八点有个视频通话",
    ],
    "weather": [
        "查询北京的天气怎么样",
        "上海会不会下雨",
        "深圳气温多少度",
        "广东有没有台风预警",
        "空气质量指数好不好",
        "出门需要带雨伞吗",
        "周末适不适合出去游玩",
        "降温了要不要多穿件衣服",
        "暴雨预警发布了没有",
        "未来几天天气趋势如何",
        "紫外线强度高不高要防晒吗",
        "最近雾霾污染严重吗",
        "气温会不会回升变暖",
        "今年有寒潮来袭吗",
        "假期天气好不好适合出行吗",
    ],
    "time_tool": [
        "现在几点了",
        "今天几号星期几",
        "帮我倒计时五分钟",
        "还有多少天过年",
        "现在是什么时间",
        "计时十分钟",
        "倒计时半小时",
        "距离周末还有几天",
        "帮我定个十分钟后的提醒",
        "还要等多久",
    ],
    "system_status": [
        "电脑状态怎么样",
        "CPU占用多少",
        "内存使用情况",
        "磁盘空间还有多少",
        "网络连接状态",
        "电脑怎么这么卡",
        "帮我看看系统运行状态",
        "电脑还剩多少内存",
        "检查一下电脑性能",
    ],
    "web_search": [
        "帮我查一下量子计算是什么",
        "搜索最近的科技新闻",
        "帮我找一下相关资料",
        "最新消息是什么",
        "查一下这个问题的答案",
        "帮我搜一下北京到上海的航班",
    ],
    "forum_search": [
        "论坛里有没有关于AI的帖子",
        "帮我搜一下集市的帖子",
        "查一下论坛里关于显卡的讨论",
        "集市上有人在讨论星际公民吗",
        "论坛最近有什么新帖子",
        "帮我找一下关于Python的帖子",
        "搜一下论坛里关于装机的内容",
        "看看集市上有没有人聊这个话题",
        "论坛上有没有人发过关于摄影的帖子",
        "集市里有什么好玩的帖子",
    ],
    "normal": [
        "今天好累啊想早点休息",
        "我饿了想吃东西",
        "你好呀最近怎么样",
        "心情不太好有点低落",
        "刚才路上堵车迟到了",
        "晚饭吃什么好呢",
        "我今天开了个会很充实",
        "这个新游戏真好玩",
        "好困啊想去睡觉了",
        "周末去哪里玩比较好呢",
        "最近好忙都没空休息",
        "昨天看了个电影真好看",
        "感觉自己最近状态不错",
        "你怎么看待人工智能的发展",
        "中午吃啥好呢纠结",
        "今天工作完成得很顺利",
        "刚才和朋友聊天很开心",
        "最近在学习新的技能",
        "晚上想去跑步锻炼",
        "买了一本新书准备读",
    ],
}


# ============================================================================
# 中国主要城市列表 —— 用于天气查询中的城市名提取
# 按长度降序排列，确保长名优先匹配（避免"吉林"误匹配"吉林市"）
# ============================================================================
_COMMON_CHINESE_CITIES_RAW = [
    # 直辖市
    "北京", "上海", "天津", "重庆",
    # 省会城市
    "广州", "深圳", "成都", "武汉", "杭州", "南京", "西安", "长沙",
    "沈阳", "郑州", "济南", "青岛", "哈尔滨", "长春", "昆明", "贵阳",
    "南宁", "海口", "兰州", "西宁", "银川", "乌鲁木齐", "呼和浩特",
    "石家庄", "太原", "合肥", "南昌", "福州", "拉萨",
    # 计划单列市 & 重要城市
    "大连", "厦门", "宁波", "苏州", "无锡", "东莞", "佛山", "珠海",
    "惠州", "中山", "江门", "湛江", "茂名", "肇庆", "汕头", "汕尾",
    "潮州", "揭阳", "梅州", "河源", "清远", "韶关", "阳江", "云浮",
    "温州", "绍兴", "嘉兴", "湖州", "金华", "台州", "丽水", "衢州",
    "舟山", "南通", "徐州", "常州", "扬州", "镇江", "泰州", "盐城",
    "淮安", "连云港", "宿迁", "淄博", "烟台", "潍坊", "临沂", "济宁",
    "泰安", "威海", "日照", "德州", "聊城", "菏泽", "滨州", "东营",
    "洛阳", "南阳", "许昌", "开封", "新乡", "信阳", "焦作", "安阳",
    "平顶山", "商丘", "周口", "驻马店", "漯河", "鹤壁", "濮阳", "三门峡",
    "襄阳", "宜昌", "荆州", "黄冈", "孝感", "十堰", "荆门", "黄石",
    "鄂州", "咸宁", "恩施", "随州",
    "桂林", "柳州", "玉林", "北海", "梧州", "钦州", "百色", "河池",
    "贵港", "防城港",
    "绵阳", "宜宾", "南充", "德阳", "乐山", "泸州", "达州", "广安",
    "自贡", "眉山", "内江", "遂宁", "广元", "资阳", "巴中", "雅安",
    "遵义", "毕节", "六盘水", "铜仁", "安顺",
    "九江", "赣州", "景德镇", "上饶", "宜春", "吉安", "抚州", "萍乡",
    "新余", "鹰潭",
    "岳阳", "株洲", "湘潭", "衡阳", "常德", "郴州", "邵阳", "怀化",
    "益阳", "永州", "娄底", "张家界",
    "泉州", "漳州", "龙岩", "三明", "南平", "宁德", "莆田",
    "宝鸡", "咸阳", "渭南", "延安", "榆林", "汉中", "安康",
    "大庆", "齐齐哈尔", "佳木斯", "牡丹江", "鸡西",
    "吉林", "延吉", "四平", "通化", "松原", "白城",
    "大理", "丽江", "曲靖", "玉溪", "保山", "昭通", "普洱", "临沧",
    "三亚", "儋州", "三沙",
    "包头", "赤峰", "鄂尔多斯", "呼伦贝尔", "通辽",
    "天水", "酒泉", "敦煌", "嘉峪关",
    "哈密", "克拉玛依", "吐鲁番", "喀什", "伊犁",
    "日喀则", "林芝", "那曲",
    "黄山", "宏村",
    "香港", "澳门",
    "台北", "高雄", "台中", "台南", "新竹", "基隆",
]
# 按长度降序排列
COMMON_CHINESE_CITIES = sorted(set(_COMMON_CHINESE_CITIES_RAW), key=len, reverse=True)


class KeywordFilter:
    # 类级嵌入模型缓存 —— 所有实例共享，避免重复加载
    _ef = None
    _intent_embeddings = {}
    _using_bge = False
    _init_lock = threading.Lock()
    _initialized = False

    def __init__(self):
        # 编译关键词正则（保留用于后备）
        self._compiled = {}
        for tool_name, keywords in MCP_KEYWORDS.items():
            pattern = "|".join(re.escape(kw) for kw in keywords)
            self._compiled[tool_name] = re.compile(pattern)

        # 初始化嵌入模型（类级缓存 + 线程锁，多实例安全）
        self._init_embedding()

    def _init_embedding(self):
        # 类级锁 + 已初始化检查：防止多线程并发加载
        with KeywordFilter._init_lock:
            if KeywordFilter._initialized:
                return
            # 加载 GGUF 格式的 bge-small-q8-zh-v1.5 嵌入模型
            # PyInstaller 打包后 __file__ 指向 PYZ 虚拟路径，需改用 sys._MEIPASS
            if getattr(sys, 'frozen', False):
                base = sys._MEIPASS
            else:
                base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            gguf_path = os.path.join(base, "models", "bge-small-q8-zh-v1.5.gguf")

            if os.path.isfile(gguf_path):
                try:
                    from llama_cpp import Llama
                    KeywordFilter._ef = Llama(
                        model_path=gguf_path,
                        n_ctx=512,
                        n_threads=8,
                        embedding=True,
                        verbose=False
                    )
                    KeywordFilter._using_bge = True
                    # 预计算各类别的平均嵌入向量
                    for intent, examples in INTENT_EXAMPLES.items():
                        embeddings = []
                        for text in examples:
                            output = KeywordFilter._ef.create_embedding(text)
                            emb = np.array(output["data"][0]["embedding"], dtype=np.float32)
                            # L2 归一化
                            norm = np.linalg.norm(emb)
                            if norm > 0:
                                emb = emb / norm
                            embeddings.append(emb)
                        KeywordFilter._intent_embeddings[intent] = np.mean(embeddings, axis=0)
                    print(f"[KeywordFilter] BGE GGUF嵌入模型就绪，{len(KeywordFilter._intent_embeddings)}个意图类别已加载", file=sys.stderr, flush=True)
                    KeywordFilter._initialized = True
                    return
                except Exception as e:
                    print(f"[KeywordFilter] BGE GGUF模型加载失败: {e}，将回退到关键词模式", file=sys.stderr, flush=True)

            # 如果 GGUF 加载失败，回退到关键词模式
            print(f"[KeywordFilter] 未找到 GGUF 模型或加载失败，将回退到关键词模式", file=sys.stderr, flush=True)
            KeywordFilter._ef = None
            KeywordFilter._initialized = True

    # ---- 原有方法（保留向后兼容） ----

    def match(self, text):
        """关键词匹配（后备方案）"""
        matched = []
        for tool_name, pattern in self._compiled.items():
            if pattern.search(text):
                matched.append(tool_name)
        return matched

    def get_weather_sub_op(self, text):
        """天气子操作判断（保持原有逻辑不变）"""
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
        """生活指数类型判断（保持原有逻辑不变）"""
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

    # ---- 新增方法 ----

    def get_time_sub_op(self, text):
        """时间工具子操作判断"""
        date_calc_kw = ["距离", "还有几天", "还剩几天", "还有多少天", "多少天", "还要几天"]
        countdown_kw = ["计时", "倒计时"]
        stopwatch_kw = ["秒表", "计时器"]
        current_kw = ["现在几点", "几号", "星期几", "什么时间"]

        for kw in current_kw:
            if kw in text:
                return "current_time"
        for kw in date_calc_kw:
            if kw in text:
                return "date_calc"
        for kw in countdown_kw:
            if kw in text:
                return "countdown"
        for kw in stopwatch_kw:
            if kw in text:
                return "stopwatch"
        return "current_time"

    def get_weather_location(self, text):
        """
        从用户消息中提取城市名。
        返回城市名（str）或空字符串。
        """
        for city in COMMON_CHINESE_CITIES:
            if city in text:
                # 防止"吉林市"被"吉林"误匹配 —— 长名优先已由排序保证
                return city
        return ""

    def match_explicit(self, text):
        """
        显式指令快速通道。
        返回 (tool_name, params) 或 None。
        """
        for keywords, tool_name, default_params in self._explicit_routes:
            for kw in keywords:
                if kw in text:
                    return (tool_name, default_params.copy())
        return None

    @property
    def _explicit_routes(self):
        """惰性构建，避免类加载时的循环引用"""
        return EXPLICIT_ROUTES

    def match_semantic(self, text):
        """
        嵌入相似度匹配。
        返回 {intent: score} 字典，按相似度降序排列。
        如果嵌入模型不可用，返回空字典。
        """
        if KeywordFilter._ef is None:
            return {}

        try:
            # 使用 GGUF 模型生成查询文本的嵌入向量
            output = KeywordFilter._ef.create_embedding(text)
            query_embedding = np.array(output["data"][0]["embedding"], dtype=np.float32)
            # L2 归一化
            norm = np.linalg.norm(query_embedding)
            if norm > 0:
                query_embedding = query_embedding / norm

            scores = {}
            for intent, avg_embedding in KeywordFilter._intent_embeddings.items():
                similarity = self._cosine_similarity(query_embedding, avg_embedding)
                scores[intent] = round(float(similarity), 3)

            return dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))
        except Exception as e:
            print(f"[KeywordFilter] 语义匹配失败: {e}", file=sys.stderr, flush=True)
            return {}

    @staticmethod
    def _cosine_similarity(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

    @property
    def embedding_available(self):
        return KeywordFilter._ef is not None
