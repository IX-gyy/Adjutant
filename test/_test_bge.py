"""
bge-small-zh-v1.5 中文嵌入模型 Demo
用法: python _test_bge.py

模型路径: backend/models/bge-small-zh-v1.5/
如未下载，请先从 https://hf-mirror.com/BAAI/bge-small-zh-v1.5/tree/main 下载所有文件
"""
import sys
import os
import time
import numpy as np

# 模型本地路径
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "backend", "models", "bge-small-zh-v1.5")

# ============================================================================
# 意图示例库（和 keyword_filter.py 一致）
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
# 显式指令快速通道（和 keyword_filter.py 一致）
# ============================================================================
EXPLICIT_ROUTES = [
    (["提醒我", "别忘了", "记一下", "帮我记", "帮我加个提醒", "帮我加一个提醒"], "todo", {"sub_op": "add"}),
    (["待办列表", "有什么安排", "今天要做什么", "还有什么事", "我的任务"], "todo", {"sub_op": "list"}),
    (["天气", "会下雨", "会下雪", "温度多少", "气温多少", "台风"], "weather", {}),
    (["现在几点", "今天几号", "星期几", "现在什么时间", "当前时间"], "time_tool", {"sub_op": "current_time"}),
    (["电脑状态", "系统状态", "CPU占用", "内存使用", "磁盘空间", "电脑好卡", "电脑卡", "电脑慢", "电脑性能", "系统卡", "电脑怎么"], "system_status", {"sub_op": "all"}),
    (["帮我查", "搜索一下", "帮我搜", "帮我找"], "web_search", {}),
]

# ============================================================================
# 阈值
# ============================================================================
HIGH = 0.70
MEDIUM = 0.55
GAP = 0.08


def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


def load_model():
    """加载 bge-small-zh-v1.5 模型（优先本地路径）"""
    print(f"模型路径: {MODEL_PATH}")

    if not os.path.isdir(MODEL_PATH):
        print(f"\n错误：模型目录不存在！")
        print(f"请从 https://hf-mirror.com/BAAI/bge-small-zh-v1.5/tree/main 下载所有文件")
        print(f"放入 {MODEL_PATH}/")
        sys.exit(1)

    # 检查关键文件是否存在
    required = ["config.json", "model.safetensors", "tokenizer.json", "vocab.txt"]
    missing = [f for f in required if not os.path.isfile(os.path.join(MODEL_PATH, f))]
    if missing:
        print(f"\n错误：缺少模型文件: {missing}")
        print(f"请从 https://hf-mirror.com/BAAI/bge-small-zh-v1.5/tree/main 补全")
        sys.exit(1)

    print("正在加载 bge-small-zh-v1.5 模型...")
    t0 = time.time()

    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(MODEL_PATH)
        print(f"  加载成功, 耗时 {time.time()-t0:.1f}s")
        return model
    except ImportError:
        print("  sentence-transformers 未安装，尝试 FlagEmbedding...")

    try:
        from FlagEmbedding import FlagModel
        model = FlagModel(MODEL_PATH,
                          query_instruction_for_retrieval="为这个句子生成表示以用于检索相关文章：")
        print(f"  加载成功, 耗时 {time.time()-t0:.1f}s")
        return model
    except ImportError:
        pass

    print("\n错误：请先安装以下任一库：")
    print("  pip install sentence-transformers")
    print("  pip install FlagEmbedding")
    sys.exit(1)


def match_explicit(text):
    for keywords, tool_name, default_params in EXPLICIT_ROUTES:
        for kw in keywords:
            if kw in text:
                return (tool_name, default_params.copy())
    return None


def main():
    # 加载模型
    model = load_model()

    # 预计算各类别的平均嵌入
    print("正在预计算意图类别平均向量...")
    t0 = time.time()
    intent_embeddings = {}
    for intent, examples in INTENT_EXAMPLES.items():
        embeddings = model.encode(examples, normalize_embeddings=True)
        intent_embeddings[intent] = np.mean(embeddings, axis=0)
    print(f"  完成, 耗时 {time.time()-t0:.1f}s\n")

    # 测试用例
    tests = [
        ("提醒我明天下午开会", "todo"),
        ("今天天气怎么样", "weather"),
        ("现在几点了", "time_tool"),
        ("帮我查量子计算", "web_search"),
        ("待办列表", "todo"),
        ("今天好累啊", "normal"),
        ("我明天要开会", "todo"),
        ("电脑好卡怎么回事", "system_status"),
        ("别忘了买酱油", "todo"),
        ("北京会下雨吗", "weather"),
        ("帮我倒计时五分钟", "time_tool"),
        ("今天心情真好", "normal"),
        ("电脑还剩多少内存", "system_status"),
        ("好困想去睡觉了", "normal"),
        ("深圳有没有暴雨预警", "weather"),
        ("还有多少天过年", "time_tool"),
        ("帮我找一下最近的新闻", "web_search"),
        ("今天晚上吃什么呢", "normal"),
    ]

    print(f"{'输入':22s} | {'期望':12s} | {'显式':30s} | {'语义 #1':20s} | {'#2':20s} | {'路由判断'}")
    print("-" * 140)

    correct_semantic = 0
    total_semantic = 0

    for text, expected in tests:
        # 显式路由
        explicit = match_explicit(text)
        explicit_str = f"{explicit[0]}" if explicit else "-"

        # 语义匹配
        t1 = time.time()
        query_emb = model.encode([text], normalize_embeddings=True)[0]
        elapsed = (time.time() - t1) * 1000

        scores = {}
        for intent, avg_emb in intent_embeddings.items():
            scores[intent] = round(float(cosine(query_emb, avg_emb)), 3)
        scores = dict(sorted(scores.items(), key=lambda x: x[1], reverse=True))

        intents = list(scores.keys())
        best_intent = intents[0]
        best_score = scores[best_intent]
        second_intent = intents[1] if len(intents) > 1 else "-"
        second_score = scores[second_intent] if len(intents) > 1 else 0
        gap = round(best_score - second_score, 3)

        total_semantic += 1
        if best_intent == expected:
            correct_semantic += 1

        # 路由判断
        if best_score >= HIGH and gap >= GAP:
            route = f"→ {best_intent}"
        elif best_intent == "todo" and best_score >= MEDIUM:
            route = "→ TODO追问"
        elif gap < GAP and second_score >= MEDIUM:
            route = f"→ GLM({best_intent}|{second_intent})"
        else:
            route = "→ 正常对话"

        sn = f"{best_intent}={best_score:.3f}"
        s2 = f"{second_intent}={second_score:.3f}" if second_intent != "-" else "-"

        print(f"{text:22s} | {expected:12s} | {explicit_str:30s} | {sn:20s} | {s2:20s} | {route}")

    print("-" * 140)
    print(f"\n语义匹配准确率: {correct_semantic}/{total_semantic} = {correct_semantic/total_semantic*100:.1f}%")
    print(f"模型单次推理延迟: {elapsed:.1f}ms")


if __name__ == "__main__":
    main()
