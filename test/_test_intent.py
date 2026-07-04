import sys
sys.path.insert(0, 'C:/VibeCoding/adjutant/backend')
from mcp.keyword_filter import KeywordFilter, HIGH_CONFIDENCE, MEDIUM_CONFIDENCE, CONFIDENCE_GAP

kf = KeywordFilter()
print('=== 意图检测完整测试 ===')
print(f'阈值: HIGH={HIGH_CONFIDENCE}, MEDIUM={MEDIUM_CONFIDENCE}, GAP={CONFIDENCE_GAP}\n')

tests = [
    # (输入, 期望意图)
    ('提醒我明天下午开会', 'todo'),
    ('今天天气怎么样', 'weather'),
    ('现在几点了', 'time_tool'),
    ('帮我查量子计算', 'web_search'),
    ('待办列表', 'todo'),
    ('今天好累啊', 'normal'),
    ('我明天要开会', 'todo'),
    ('电脑好卡怎么回事', 'system_status'),
    ('别忘了买酱油', 'todo'),
    ('北京会下雨吗', 'weather'),
    ('帮我倒计时五分钟', 'time_tool'),
    ('今天心情真好', 'normal'),
]

for t, expected in tests:
    print(f'输入: "{t}" (期望: {expected})')

    explicit = kf.match_explicit(t)
    if explicit:
        tool, params = explicit
        print(f'  [显式] → {tool} {params}')

    scores = kf.match_semantic(t)
    if scores:
        top2 = list(scores.items())[:2]
        best_intent, best_score = top2[0]
        second_intent, second_score = top2[1] if len(top2) > 1 else ('-', 0)
        gap = round(best_score - second_score, 3)

        # 模拟路由判断
        if best_score >= HIGH_CONFIDENCE and gap >= CONFIDENCE_GAP:
            route = f'→ 直接路由到 {best_intent}'
        elif best_intent == 'todo' and best_score >= MEDIUM_CONFIDENCE:
            route = f'→ 追问确认 (TODO中等置信度)'
        elif gap < CONFIDENCE_GAP and second_score >= MEDIUM_CONFIDENCE:
            route = f'→ GLM二选一 ({best_intent} vs {second_intent})'
        else:
            route = '→ 正常对话'

        print(f'  [语义] #1: {best_intent}={best_score:.3f}  #2: {second_intent}={second_score:.3f}  gap={gap:.3f}  {route}')
    else:
        print(f'  [语义] 不可用')

    print()
