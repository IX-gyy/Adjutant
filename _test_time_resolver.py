"""
测试 time_resolver 模块的相对时间解析功能。

用法：
    python _test_time_resolver.py

或直接作为模块运行：
    python -m pytest _test_time_resolver.py -v
"""

import datetime
import sys
import os

# 确保能导入 backend 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

from mcp.tools.time_resolver import (
    resolve_relative_time,
    resolve_relative_time_str,
    pre_resolve_message,
    build_date_reference,
)


# ============================================================================
# 测试辅助
# ============================================================================

PASS = 0
FAIL = 0


def check(name, expression, base_str, expected_str):
    """测试单条相对时间表达解析。
    - base_str: "YYYY-MM-DD" 或 "YYYY-MM-DD HH:MM"
    - expected_str: 同上
    """
    global PASS, FAIL
    base_fmt = "%Y-%m-%d %H:%M" if " " in base_str else "%Y-%m-%d"
    base = datetime.datetime.strptime(base_str, base_fmt)

    dt, conf = resolve_relative_time(expression, base)
    result_str = dt.strftime("%Y-%m-%d %H:%M") if dt else "None"

    # 判断是否通过 (比较前截断到期望精度)
    expected_has_time = " " in expected_str
    if not expected_has_time:
        result_str = dt.strftime("%Y-%m-%d") if dt else "None"

    ok = result_str == expected_str
    if ok:
        PASS += 1
        print(f"  PASS [{name}] '{expression}' @ {base_str} -> {result_str} (conf={conf})")
    else:
        FAIL += 1
        print(f"  FAIL [{name}] '{expression}' @ {base_str} -> {result_str}, expected {expected_str} (conf={conf})")
    return ok


def check_pre_resolve(name, text, base_str, expected_best_date=None, expect_resolved=True,
                      expected_inline=None):
    """测试 pre_resolve_message 函数。

    - expected_inline: 验证 enriched_message 中包含内联替换的绝对日期
    """
    global PASS, FAIL
    base = datetime.datetime.strptime(base_str, "%Y-%m-%d")
    info = pre_resolve_message(text, base)

    resolved = info["resolved"]
    best = info["best_date_str"]
    enriched = info["enriched_message"]

    ok = True
    if expect_resolved:
        if not resolved:
            ok = False
        if expected_best_date and best:
            if not best.startswith(expected_best_date):
                ok = False
        # 验证内联替换格式：enriched_message 中不应包含旧的 [预解析时间：...] 格式
        # 而应包含 YYYY-MM-DD(周X) 内联格式
        if "[预解析时间：" in enriched:
            print(f"  WARN [{name}] enriched_message 仍使用旧的追加提示格式")
            ok = False
        if expected_inline and expected_inline not in enriched:
            print(f"  WARN [{name}] enriched_message 中未找到预期内联日期'{expected_inline}': {enriched}")
            ok = False

    if ok:
        PASS += 1
        print(f"  PASS [{name}] '{text}' -> best={best}, enriched={enriched}")
    else:
        FAIL += 1
        print(f"  FAIL [{name}] '{text}' -> best={best}, enriched={enriched}, expected_best={expected_best_date}")
    return ok


# ============================================================================
# 测试用例
# ============================================================================

def test_basic_relative_days():
    """基础相对天数：明天 / 后天 / 大后天。"""
    print("\n--- 基础相对天数 ---")
    check("明天", "明天", "2026-06-09", "2026-06-10")
    check("后天", "后天", "2026-06-09", "2026-06-11")
    check("大后天", "大后天", "2026-06-09", "2026-06-12")
    check("明天(跨月)", "明天", "2026-06-30", "2026-07-01")
    check("后天(跨月)", "后天", "2026-06-29", "2026-07-01")

    # 带时间的变体
    check("明天下午3点", "明天下午3点", "2026-06-09", "2026-06-10 15:00")
    check("明天上午9点", "明天上午9点", "2026-06-09", "2026-06-10 09:00")
    check("后天晚上8点", "后天晚上8点", "2026-06-09", "2026-06-11 20:00")


def test_weekday_expressions():
    """星期表达：这周X / 下周X / 周X。"""
    print("\n--- 星期表达 ---")
    # base = 2026-06-09 (周二, weekday=1)

    # 这周X（base=2026-06-09 周二）
    check("这周四(Tue)", "这周四", "2026-06-09", "2026-06-11")   # Tue→Thu this week = +2
    check("这周三(Tue)", "这周三", "2026-06-09", "2026-06-10")   # Tue→Wed this week = +1
    check("这周二(Tue,今天)", "这周二", "2026-06-09", "2026-06-09") # Tue→Tue = today
    check("这周一(Tue,已过)", "这周一", "2026-06-09", "2026-06-15") # Tue→Mon already passed → push

    # 这周X (Bug ①: 周四说"这周五"→本周五=明天，不是下周五)
    check("这周五(Thu,未过)", "这周五开会", "2026-06-11", "2026-06-12")
    # 周四说"这周四" → 今天就是周四
    check("这周四(Thu,今天)", "这周四", "2026-06-11", "2026-06-11")

    # 这周X (Bug ④: 周四说"这周一"→本周一已过，推至下周一)
    check("这周一(Thu,已过)", "这周一有任务", "2026-06-11", "2026-06-15")
    check("这周三(Thu,已过)", "这周三", "2026-06-11", "2026-06-17")   # 本周三已过 → 下周三
    check("这周二(Thu,已过)", "这周二", "2026-06-11", "2026-06-16")

    # 这周X（周五说"这周一" → 本周一已过 → 下周一）
    check("这周一(周五说)", "这周一", "2026-06-12", "2026-06-15")
    # 周五说"这周五" → 今天就是周五 → 就是今天
    check("这周五(周五说)", "这周五", "2026-06-12", "2026-06-12")

    # 下周X
    check("下周四(Tue)", "下周四", "2026-06-09", "2026-06-18")   # Tue→next Thu = this Thu + 7 = +9
    check("下周三(Fri)", "下周三", "2026-06-12", "2026-06-17")   # Fri→this Wed = past, next Wed = +5
    check("下周一(Sun)", "下周一", "2026-06-14", "2026-06-15")   # Sun→next Mon = +1 (this Mon already passed)

    # 裸周X（无前缀）(Bug ③: 周四说"周三"→最近的下个周三=6月17日)
    check("周四(裸)", "周四", "2026-06-09", "2026-06-11")        # Tue→nearest Thu = this Thu = +2
    check("周一(裸Fri)", "周一", "2026-06-12", "2026-06-15")     # Fri→nearest Mon = next Mon = +3
    check("周三(裸Thu)", "周三", "2026-06-11", "2026-06-17")     # Thu→nearest Wed = next Wed = +6
    check("周三(裸Wed)", "周三", "2026-06-10", "2026-06-10")     # Wed→nearest Wed = today

    # 下下周X (Bug ②: 周四说"下下周一"→6月22日，不是下周一6月15日)
    check("下下周周四", "下下周周四", "2026-06-09", "2026-06-25")  # Tue→this Thu + 14 = +16
    check("下下周一(Tue)", "下下周一", "2026-06-09", "2026-06-22") # Tue→two Mondays later
    check("下下周一(Thu)", "下下周一出发", "2026-06-11", "2026-06-22") # Thu→下下周一=June 22
    check("下下周一(Thu,含时间)", "下下周一早上八点出发", "2026-06-11", "2026-06-22 08:00")
    check("下下周五", "下下周五", "2026-06-12", "2026-06-26")     # Fri→two Fridays later
    check("下下周一(Mon)", "下下周一", "2026-06-15", "2026-06-29") # from Mon, 下下周一 = +14


def test_specific_date():
    """具体日期：X月X日 / X月X号。"""
    print("\n--- 具体日期 ---")
    # 未来日期（同年）
    check("6月15日", "6月15日", "2026-06-09", "2026-06-15")
    check("12月25日", "12月25号", "2026-06-09", "2026-12-25")
    # 已过日期（推到明年）
    check("3月1日(已过)", "3月1日", "2026-06-09", "2027-03-01")
    # 带时间
    check("6月15日下午2点", "6月15日下午2点", "2026-06-09", "2026-06-15 14:00")


def test_numeric_offset():
    """数字偏移：X天后 / 半个月后。"""
    print("\n--- 数字偏移 ---")
    check("3天后", "3天后", "2026-06-09", "2026-06-12")
    check("7天后", "7天后", "2026-06-09", "2026-06-16")
    check("半个月后", "半个月后", "2026-06-09", "2026-06-24")
    check("1天后", "1天后", "2026-06-09", "2026-06-10")


def test_month_expressions():
    """月份表达：下个月X号 / 月底 / 年底。"""
    print("\n--- 月份表达 ---")
    check("下个月5号", "下个月5号", "2026-06-09", "2026-07-05")
    check("下个月1号", "下个月1号", "2026-06-09", "2026-07-01")
    check("下个月15号(跨年)", "下个月15号", "2026-12-09", "2027-01-15")
    check("月底", "月底", "2026-06-09", "2026-06-30")
    check("月底(2月)", "月底", "2026-02-09", "2026-02-28")
    check("年底", "年底", "2026-06-09", "2026-12-31")


def test_evening_expressions():
    """晚间表达：今晚 / 明晚 / 后天晚上。"""
    print("\n--- 晚间表达 ---")
    check("今晚", "今晚", "2026-06-09", "2026-06-09 20:00")
    check("明晚", "明晚", "2026-06-09", "2026-06-10 20:00")
    check("后天晚上", "后天晚上", "2026-06-09", "2026-06-11 20:00")


def test_other_keywords():
    """其他关键词：周末 / 今天 / 下周(裸) / 过年。"""
    print("\n--- 其他关键词 ---")
    check("周末(Tue)", "周末", "2026-06-09", "2026-06-13")   # 周六
    check("周末(Sat)", "周末", "2026-06-13", "2026-06-20")   # 今天就是周六 → 下周六
    check("今天", "今天下午开会", "2026-06-09 14:00", "2026-06-09 14:00")
    check("下周(裸)", "下周有一个会议", "2026-06-09", "2026-06-15")  # 下周一


def test_time_of_day():
    """时段解析：上午 / 下午 / 晚上 / 中午。"""
    print("\n--- 时段解析 ---")
    check("上午8点", "明天上午8点", "2026-06-09", "2026-06-10 08:00")
    check("中午12点", "明天中午12点", "2026-06-09", "2026-06-10 12:00")
    check("下午1点", "明天下午1点", "2026-06-09", "2026-06-10 13:00")
    check("下午5点", "明天下午5点", "2026-06-09", "2026-06-10 17:00")
    check("晚上9点", "明天晚上9点", "2026-06-09", "2026-06-10 21:00")
    check("下午3点半", "明天下午3点半", "2026-06-09", "2026-06-10 15:30")
    # 时间格式 HH:MM
    check("时间格式", "明天14:30", "2026-06-09", "2026-06-10 14:30")


def test_pre_resolve():
    """pre_resolve_message 集成测试。"""
    print("\n--- pre_resolve_message 集成 ---")
    # 单时间表达
    check_pre_resolve(
        "单时间", "我下周四有一个会议，提醒我",
        "2026-06-09",
        expected_best_date="2026-06-18",
        expected_inline="2026-06-18(周四)"
    )
    # 无时间表达
    check_pre_resolve(
        "无时间", "今天天气不错",
        "2026-06-09", expect_resolved=False
    )
    # 带具体时间的提醒
    check_pre_resolve(
        "带时间", "提醒我明天下午3点开会",
        "2026-06-09",
        expected_best_date="2026-06-10",
        expected_inline="2026-06-10(周三)"
    )

    # Bug ①: 这周五 → 本周五（不是下周五）
    check_pre_resolve(
        "Bug1-这周五", "这周五要交程序分析作业，记得提醒我",
        "2026-06-11",
        expected_best_date="2026-06-12",
        expected_inline="2026-06-12(周五)"
    )

    # Bug ②: 下下周一 → 6月22日（不是下周一6月15日）
    check_pre_resolve(
        "Bug2-下下周一", "下下周一早上八点出发提醒我",
        "2026-06-11",
        expected_best_date="2026-06-22",
        expected_inline="2026-06-22(周一)"
    )

    # Bug ③: 裸"周三" → 最近的下个周三
    check_pre_resolve(
        "Bug3-周三", "周三晚上有个饭局别忘了",
        "2026-06-11",
        expected_best_date="2026-06-17",
        expected_inline="2026-06-17(周三)"
    )

    # Bug ④: 这周一（已过）→ 下周一
    check_pre_resolve(
        "Bug4-这周一(已过)", "这周一有一个任务",
        "2026-06-11",
        expected_best_date="2026-06-15",
        expected_inline="2026-06-15(周一)"
    )


def test_build_date_reference():
    """build_date_reference 输出格式。"""
    print("\n--- build_date_reference ---")
    base = datetime.datetime(2026, 6, 9)  # 周二
    ref = build_date_reference(base)
    # 应包含"本周"和"下周"
    assert "本周" in ref, "应包含本周日期"
    assert "下周" in ref, "应包含下周日期"
    # 应包含正确的日期
    assert "一06月08日" in ref, f"本周一应为06月08日，实际: {ref}"
    assert "二06月09日" in ref, f"本周二应为06月09日，实际: {ref}"
    assert "四06月11日" in ref, f"本周四应为06月11日，实际: {ref}"
    print(f"  PASS [build_date_reference] {ref}")


# ============================================================================
# 主入口
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("time_resolver 单元测试")
    print(f"基准日期: {datetime.date.today()} (用于'今天'等相对表达)")
    print("=" * 60)

    test_basic_relative_days()
    test_weekday_expressions()
    test_specific_date()
    test_numeric_offset()
    test_month_expressions()
    test_evening_expressions()
    test_other_keywords()
    test_time_of_day()
    test_pre_resolve()
    test_build_date_reference()

    print("\n" + "=" * 60)
    total = PASS + FAIL
    print(f"结果: {PASS}/{total} 通过, {FAIL} 失败")
    if FAIL > 0:
        print("❌ 有测试失败！")
        sys.exit(1)
    else:
        print("✅ 全部测试通过！")
