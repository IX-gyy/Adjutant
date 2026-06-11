"""
时间解析模块 —— 将中文自然语言相对时间表达解析为绝对日期时间。

设计原则：
  - 纯确定性 Python，零外部依赖
  - 先匹配具体规则，再匹配通用规则
  - 返回 (datetime, confidence) 元组
  - 幂等：相同输入 + 相同基准时间 → 相同输出

使用方式：
  from .time_resolver import resolve_relative_time, pre_resolve_message
"""

import re
import datetime


# ============================================================================
# 常量
# ============================================================================

WEEKDAY_MAP = {
    "周一": 0, "星期一": 0,
    "周二": 1, "星期二": 1,
    "周三": 2, "星期三": 2,
    "周四": 3, "星期四": 3,
    "周五": 4, "星期五": 4,
    "周六": 5, "星期六": 5,
    "周日": 6, "星期日": 6, "星期天": 6,
}

WEEKDAY_ZH = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 时间词 → 24小时制小时数
TIME_PERIOD_MAP = {
    "凌晨": lambda h: h if h <= 6 else h,        # 凌晨X点 → X (通常0-6)
    "早上": lambda h: h,                           # 早上X点 → X (通常6-9)
    "上午": lambda h: h,                           # 上午X点 → X (通常8-11)
    "中午": lambda h: 12 if h == 12 else 12 + h if h <= 2 else h,  # 中午 → 12:00左右
    "下午": lambda h: h + 12 if h < 12 else h,     # 下午X点 → X+12
    "傍晚": lambda h: h + 12 if h < 12 else h,     # 傍晚X点 → X+12 (通常17-19)
    "晚上": lambda h: h + 12 if h < 12 else h,     # 晚上X点 → X+12 (通常19-23)
    "今夜": lambda h: h + 12 if h < 12 else h,
}

# 模糊时间段
FUZZY_TIME_MAP = {
    "早上": "08:00",
    "上午": "09:00",
    "中午": "12:00",
    "下午": "14:00",
    "傍晚": "17:00",
    "晚上": "19:00",
    "今夜": "20:00",
    "今晚": "19:00",
    "明早": "08:00",
    "明晚": "19:00",
    "后天早上": "08:00",
    "后天晚上": "19:00",
}

# 中国节假日（粗略日期，后续可扩展为查表）
SPRING_FESTIVAL_DATES = {
    2025: (1, 29), 2026: (2, 17), 2027: (2, 6),
    2028: (1, 26), 2029: (2, 13), 2030: (2, 3),
}


# ============================================================================
# 核心函数
# ============================================================================

def resolve_relative_time(text: str, base_datetime: datetime.datetime = None):
    """
    将文本中的第一个相对时间表达解析为绝对 datetime。

    Args:
        text: 包含相对时间表达的自然语言文本
        base_datetime: 基准时间，默认为当前系统时间

    Returns:
        (datetime, confidence) 或 (None, 0.0)
        confidence: 1.0=确定性匹配, 0.6-0.9=推断匹配, 0.0=未解析
    """
    if base_datetime is None:
        base_datetime = datetime.datetime.now()

    result, confidence = _resolve_date_and_time(text, base_datetime)
    return result, confidence


def resolve_relative_time_str(text: str, base_datetime: datetime.datetime = None,
                               fmt: str = "%Y-%m-%d %H:%M"):
    """
    便捷方法：返回格式化的日期字符串。

    Returns:
        (date_string, confidence) 或 (None, 0.0)
    """
    dt, conf = resolve_relative_time(text, base_datetime)
    if dt is None:
        return None, 0.0
    return dt.strftime(fmt), conf


def pre_resolve_message(text: str, base_datetime: datetime.datetime = None):
    """
    扫描用户消息，解析第一个相对时间表达，并内联替换为绝对日期。

    核心设计：将原始消息中的"这周五"/"下周一"等模糊表达直接替换为
    "2026-06-12(周五)"这样的绝对日期，让 LLM 不再看到模糊的相对表达，
    从根源上消除 LLM 自行推算错误的可能性。

    Args:
        text: 用户原始消息
        base_datetime: 基准时间

    Returns:
        {
            "resolved": [(expression, date_str, confidence), ...],
            "enriched_message": str,  # 内联替换后的消息
            "best_date_str": str | None,  # 置信度最高的日期（用于 fallback）
        }
    """
    if base_datetime is None:
        base_datetime = datetime.datetime.now()

    dt, conf = _resolve_date_and_time(text, base_datetime)

    if dt is None:
        return {
            "resolved": [],
            "enriched_message": text,
            "best_date_str": None,
        }

    date_str = dt.strftime("%Y-%m-%d %H:%M")
    best_date_str = date_str

    # 找到被匹配的原始表达文本
    expr_text = _find_matched_expression(text)
    resolved = [(expr_text, date_str, conf)]

    # 内联替换：将相对时间表达替换为绝对日期
    weekday_zh = WEEKDAY_ZH[dt.weekday()]
    # 如果解析出了具体时间，附上时间；否则只附日期
    if dt.hour != 9 or dt.minute != 0:
        replacement = f"{dt.strftime('%Y-%m-%d')}({weekday_zh}) {dt.strftime('%H:%M')}"
    else:
        replacement = f"{dt.strftime('%Y-%m-%d')}({weekday_zh})"
    enriched = text.replace(expr_text, replacement, 1)

    return {
        "resolved": resolved,
        "enriched_message": enriched,
        "best_date_str": best_date_str,
    }


# ============================================================================
# 内部实现
# ============================================================================

def _resolve_date_and_time(text: str, base: datetime.datetime):
    """
    解析日期 + 时间的组合表达。
    返回 (datetime, confidence)。
    """
    # 尝试所有模式，按匹配长度降序（长匹配更具体）
    patterns = []

    for pattern_fn in _PATTERN_FUNCTIONS:
        result = pattern_fn(text, base)
        if result is not None:
            dt, conf = result
            patterns.append((dt, conf))

    if not patterns:
        return None, 0.0

    # 返回置信度最高的结果
    best = max(patterns, key=lambda x: x[1])
    return best


def _find_all_time_expressions(text: str, base: datetime.datetime):
    """
    查找文本中的第一个相对时间表达并解析。
    返回 [(expression, date_str, confidence), ...]。

    注意：当前 v2 只处理第一个匹配。多时间表达场景较少见。
    """
    resolved = []
    dt, conf = _resolve_date_and_time(text, base)
    if dt is not None:
        expr_text = _find_matched_expression(text)
        resolved.append((expr_text, dt.strftime("%Y-%m-%d %H:%M"), conf))
    return resolved


def _find_matched_expression(text: str):
    """逆向查找被匹配的原始表达文本（用于内联替换）。

    按优先级从高到低排列正则，确保优先匹配更具体的模式。
    """
    candidates = [
        # 下下个月X号
        r'下下个?月\s*\d{1,2}\s*[日号]',
        # 下个月X号
        r'下个?月\s*\d{1,2}\s*[日号]',
        # X月X日/X号
        r'\d{1,2}\s*月\s*\d{1,2}\s*[日号]',
        # 下下周X (含 "下下周周四"、"下下周一"、"下下周 一" 等变体)
        r'下下个?周\s*(?:周)?\s*[一二三四五六日天]',
        r'下下个?星期\s*(?:星期)?\s*[一二三四五六日天]',
        # 大后天/大前天
        r'大后天',
        r'大前天',
        # 这周X/本周X/下周X/下星期X/裸周X
        r'(?:这周|本周|下周|下个?星期)\s*[一二三四五六日天]',
        r'周[一二三四五六日天]',
        r'星期[一二三四五六日天]',
        # 晚间表达（具体模式在前）
        r'后天晚上|后天夜里',
        r'明晚|明天晚上',
        r'今晚|今天晚上|今夜',
        # 后天/前天
        r'后天',
        r'前天',
        # 明天/今天
        r'明天|明日',
        r'今天|今日',
        # X天后
        r'\d+\s*天\s*[后以]',
        # 半个月后
        r'半\s*个?\s*月\s*[后以]',
        # 周末
        r'周末',
        # 月底/月末/年底/年末
        r'月底|月末',
        r'年底|年末',
        # 孤立的"下周"/"这周"/"本周"（未被上面匹配的）
        r'下周',
        r'这周|本周',
        # 孤立的"下个月"
        r'下个?月',
        # X小时后/X分钟后
        r'\d+\s*个?\s*小?时\s*[后以]',
        r'\d+\s*分\s*钟?\s*[后以]',
        # 过年/春节
        r'过年|春节',
    ]
    for pattern in candidates:
        m = re.search(pattern, text)
        if m:
            return m.group(0)
    return text[:30]


# ============================================================================
# 模式匹配函数列表（按优先级顺序排列）
# ============================================================================

def _match_specific_date(text: str, base: datetime.datetime):
    """匹配 'X月X日' 或 'X月X号' 格式。"""
    m = re.search(r'(\d{1,2})\s*月\s*(\d{1,2})\s*[日号]', text)
    if not m:
        return None

    month, day = int(m.group(1)), int(m.group(2))
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None

    year = base.year
    target = datetime.datetime(year, month, day)
    # 如果该日期今年已过，推到明年
    if target < base.replace(hour=0, minute=0, second=0, microsecond=0):
        target = datetime.datetime(year + 1, month, day)

    # 提取时间部分
    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val)
    else:
        target = target.replace(hour=9, minute=0)  # 默认 09:00

    return target, 1.0


def _match_next_next_month(text: str, base: datetime.datetime):
    """匹配 '下下个月X号' 或 '下下月X号' 格式。"""
    m = re.search(r'下下个?月\s*(\d{1,2})\s*[日号]', text)
    if not m:
        return None

    day = int(m.group(1))
    if not (1 <= day <= 31):
        return None

    # 下下个月 = current month + 2
    month = base.month + 2
    year = base.year
    if month > 12:
        month -= 12
        year += 1

    # 确保日期有效（如2月30日）
    try:
        target = datetime.datetime(year, month, day)
    except ValueError:
        return None

    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val)
    else:
        target = target.replace(hour=9, minute=0)

    return target, 0.9


def _match_next_month(text: str, base: datetime.datetime):
    """匹配 '下个月X号' 或 '下月X号' 格式。"""
    m = re.search(r'下个?月\s*(\d{1,2})\s*[日号]', text)
    if not m:
        return None

    day = int(m.group(1))
    if not (1 <= day <= 31):
        return None

    month = base.month + 1
    year = base.year
    if month > 12:
        month = 1
        year += 1

    try:
        target = datetime.datetime(year, month, day)
    except ValueError:
        return None

    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val)
    else:
        target = target.replace(hour=9, minute=0)

    return target, 0.95


def _match_next_month_generic(text: str, base: datetime.datetime):
    """匹配孤立的'下个月'（没有指定X号），默认1号。"""
    if "下个月" not in text and "下月" not in text:
        return None

    # 如果已被 _match_next_month 处理过（含X号），跳过
    if re.search(r'下个?月\s*\d{1,2}\s*[日号]', text):
        return None

    month = base.month + 1
    year = base.year
    if month > 12:
        month = 1
        year += 1

    try:
        target = datetime.datetime(year, month, 1, 9, 0)
    except ValueError:
        return None

    return target, 0.6


def _match_next_next_week(text: str, base: datetime.datetime):
    """匹配 '下下周X' 格式。"""
    # 支持 "下下周X" 和 "下下周周X"（如 "下下周周四"）两种写法
    m = re.search(r'下下个?周\s*(?:周)?\s*([一二三四五六日天])', text)
    if not m:
        m = re.search(r'下下个?星期\s*(?:星期)?\s*([一二三四五六日天])', text)
    if not m:
        return None

    day_char = m.group(1)
    target_weekday = _char_to_weekday(day_char)
    if target_weekday is None:
        return None

    # 计算本周一的日期
    monday = base - datetime.timedelta(days=base.weekday())
    # 下下周X = 本周一 + 14 + target_weekday
    target = monday + datetime.timedelta(days=14 + target_weekday)

    # 如果下下周 X 在当天之前或就是今天 → 不会发生在正常语义下
    # （"下下周"总是未来，至少 +14 天）

    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val)
    else:
        target = target.replace(hour=9, minute=0)

    return target, 1.0


def _match_this_next_week(text: str, base: datetime.datetime):
    """匹配 '这周X', '本周X', '下周X', '下星期X' 格式和裸 '周X'/'星期X'。"""
    # 排除 "下下周X" / "下下周一" 等被误判为 "下周X"
    if "下下周" in text or "下下星期" in text:
        return None
    if re.search(r'下下\s*周\s*[一二三四五六日天]', text):
        return None

    is_this_week = any(kw in text for kw in ["这周", "本周"])
    is_next_week = any(kw in text for kw in ["下周", "下个星期", "下星期"])

    # 尝试匹配带前缀的
    m = re.search(r'(这周|本周|下周|下个星期|下星期|周|星期)([一二三四五六日天])', text)
    if not m:
        m = re.search(r'(周[一二三四五六日天])|(星期[一二三四五六日天])', text)
    if not m:
        return None

    matched = m.group(0)
    day_char = m.group(2) if m.lastindex and m.lastindex >= 2 else matched[-1]
    if not day_char:
        # try extracting from named groups
        for g in m.groups():
            if g and len(g) == 1:
                day_char = g
                break

    target_weekday = _char_to_weekday(day_char)
    if target_weekday is None:
        return None

    # 计算本周一的日期
    monday = base - datetime.timedelta(days=base.weekday())
    # 本周的目标日期
    this_week_x = monday + datetime.timedelta(days=target_weekday)

    if is_this_week:
        # "这周X"：取本周的X
        target = this_week_x
        # 如果本周X已过，对TODO场景下推到下周
        if target.date() < base.date():
            target = target + datetime.timedelta(days=7)
            conf = 0.75  # 略低的置信度：用户可能指的是已过去的本周X
        else:
            conf = 1.0
    elif is_next_week:
        # "下周X"：取下周的X
        target = this_week_x + datetime.timedelta(days=7)
        conf = 1.0
    else:
        # 裸 "周X"/"星期X"：取最近的下一个X
        days_until = (target_weekday - base.weekday()) % 7
        if days_until == 0 and base.time() > datetime.time(0, 0):
            # 如果今天就是X且不是凌晨，默认就是今天
            target = base.replace(hour=9, minute=0, second=0, microsecond=0)
            conf = 0.7
            _apply_time(target, text)
            return target, conf
        target = base + datetime.timedelta(days=days_until)
        conf = 0.85

    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
    else:
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)

    return target, conf


def _match_days_later(text: str, base: datetime.datetime):
    """匹配 'X天后' 格式。"""
    m = re.search(r'(\d+)\s*天\s*[后以]', text)
    if not m:
        return None

    days = int(m.group(1))
    target = base + datetime.timedelta(days=days)

    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
    else:
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)

    return target, 0.95


def _match_half_month(text: str, base: datetime.datetime):
    """匹配 '半个月后' 格式。"""
    if re.search(r'半\s*个?\s*月\s*[后以]', text):
        target = base + datetime.timedelta(days=15)
        time_str = _extract_time(text)
        if time_str:
            h, m_val = time_str
            target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
        else:
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 0.9
    return None


def _match_hours_later(text: str, base: datetime.datetime):
    """匹配 'X小时后' 格式。"""
    m = re.search(r'(\d+)\s*个?\s*小?时\s*[后以]', text)
    if not m:
        return None

    hours = int(m.group(1))
    target = base + datetime.timedelta(hours=hours)
    return target, 0.95


def _match_minutes_later(text: str, base: datetime.datetime):
    """匹配 'X分钟后' 格式。"""
    m = re.search(r'(\d+)\s*分\s*钟?\s*[后以]', text)
    if not m:
        return None

    minutes = int(m.group(1))
    target = base + datetime.timedelta(minutes=minutes)
    return target, 0.95


def _match_day_after_tomorrow(text: str, base: datetime.datetime):
    """匹配 '大后天' 格式。"""
    if "大后天" in text:
        target = base + datetime.timedelta(days=3)
        time_str = _extract_time(text)
        if time_str:
            h, m_val = time_str
            target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
        else:
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0
    return None


def _match_day_before_yesterday(text: str, base: datetime.datetime):
    """匹配 '大前天' 格式（较少用于TODO但支持）。"""
    if "大前天" in text:
        target = base - datetime.timedelta(days=3)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0
    return None


def _match_day_after_tomorrow_obsolete(text: str, base: datetime.datetime):
    """匹配 '大後天'（繁体）格式。"""
    if "大後天" in text:
        target = base + datetime.timedelta(days=3)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0
    return None


def _match_day_before_yesterday_obsolete(text: str, base: datetime.datetime):
    """匹配 '大前天'（繁体）格式。"""
    if "大前天" in text:
        return _match_day_before_yesterday(text, base)
    return None


def _match_tomorrow_yesterday(text: str, base: datetime.datetime):
    """匹配 '后天'/'前天' 格式（因为含'天'字，需在'明天'之前匹配）。"""
    if "后天" in text:
        target = base + datetime.timedelta(days=2)
        time_str = _extract_time(text)
        if time_str:
            h, m_val = time_str
            target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
        else:
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0

    if "前天" in text:
        target = base - datetime.timedelta(days=2)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0

    return None


def _match_tomorrow(text: str, base: datetime.datetime):
    """匹配 '明天'/'明日' 格式。"""
    if "明天" in text or "明日" in text:
        target = base + datetime.timedelta(days=1)
        time_str = _extract_time(text)
        if time_str:
            h, m_val = time_str
            target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
        else:
            target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 1.0
    return None


def _match_today(text: str, base: datetime.datetime):
    """匹配 '今天'/'今日' 格式。"""
    if "今天" in text or "今日" in text:
        target = base.replace(second=0, microsecond=0)
        time_str = _extract_time(text)
        if time_str:
            h, m_val = time_str
            target = target.replace(hour=h, minute=m_val)
        else:
            # 保留原始小时，不强制设为09:00
            pass
        return target, 1.0
    return None


def _match_tonight_evening(text: str, base: datetime.datetime):
    """匹配 '今晚'/'明晚'/'后天晚上' 等晚间表达。"""
    # 后天晚上（在后天之前匹配，避免被'晚上'单独捕获）
    if "后天晚上" in text or "后天夜里" in text:
        target = base + datetime.timedelta(days=2)
        time_str = _extract_time(text)
        if time_str:
            target = target.replace(hour=time_str[0], minute=time_str[1], second=0, microsecond=0)
        else:
            target = target.replace(hour=20, minute=0, second=0, microsecond=0)
        return target, 1.0

    if "明晚" in text or "明天晚上" in text or "明晚" in text:
        target = base + datetime.timedelta(days=1)
        time_str = _extract_time(text)
        if time_str:
            target = target.replace(hour=time_str[0], minute=time_str[1], second=0, microsecond=0)
        else:
            target = target.replace(hour=20, minute=0, second=0, microsecond=0)
        return target, 1.0

    if "今晚" in text or "今天晚上" in text or "今夜" in text:
        target = base.replace(second=0, microsecond=0)
        time_str = _extract_time(text)
        if time_str:
            target = target.replace(hour=time_str[0], minute=time_str[1])
        else:
            target = target.replace(hour=20, minute=0)
        return target, 1.0

    # 早上/中午/晚上 + 时间已经在 _extract_time 中处理
    return None


def _match_weekend(text: str, base: datetime.datetime):
    """匹配 '周末' 格式（默认周六上午9点）。"""
    if "周末" in text:
        days_until_sat = (5 - base.weekday()) % 7
        if days_until_sat == 0:
            days_until_sat = 7  # 今天就是周六，取下周
        target = base + datetime.timedelta(days=days_until_sat)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 0.95
    return None


def _match_next_week_generic(text: str, base: datetime.datetime):
    """匹配孤立的 '下周'（没有指定星期几），默认下周一。"""
    if "下周" not in text:
        return None
    # 如果已被 _match_this_next_week 处理，跳过
    if re.search(r'下周[一二三四五六日天]', text):
        return None
    if re.search(r'下个?星期[一二三四五六日天]', text):
        return None
    # 如果已被 "下下周" 捕获
    if re.search(r'下下周', text):
        return None

    days_until = (7 - base.weekday()) % 7
    if days_until == 0:
        days_until = 7
    target = base + datetime.timedelta(days=days_until)
    target = target.replace(hour=9, minute=0, second=0, microsecond=0)
    return target, 0.7


def _match_month_end(text: str, base: datetime.datetime):
    """匹配 '月底'/'月末' 格式（当月最后一天）。"""
    if "月底" in text or "月末" in text:
        if base.month == 12:
            target = datetime.datetime(base.year + 1, 1, 1) - datetime.timedelta(days=1)
        else:
            target = datetime.datetime(base.year, base.month + 1, 1) - datetime.timedelta(days=1)
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
        return target, 0.9
    return None


def _match_year_end(text: str, base: datetime.datetime):
    """匹配 '年底'/'年末' 格式。"""
    if "年底" in text or "年末" in text:
        target = datetime.datetime(base.year, 12, 31, 9, 0)
        if target < base.replace(hour=0, minute=0, second=0, microsecond=0):
            target = datetime.datetime(base.year + 1, 12, 31, 9, 0)
        return target, 0.9
    return None


def _match_spring_festival(text: str, base: datetime.datetime):
    """匹配 '过年'/'春节' 格式。"""
    if "过年" in text or "春节" in text:
        # 从预定义表中查找春节日期
        sf = SPRING_FESTIVAL_DATES.get(base.year)
        if sf is None:
            # 未定义的年份，粗略估算
            sf = (2, 10)
        target = datetime.datetime(base.year, sf[0], sf[1], 9, 0)
        if target < base.replace(hour=0, minute=0, second=0, microsecond=0):
            next_year = base.year + 1
            sf = SPRING_FESTIVAL_DATES.get(next_year, (2, 10))
            target = datetime.datetime(next_year, sf[0], sf[1], 9, 0)
        return target, 0.8
    return None


def _match_this_week_generic(text: str, base: datetime.datetime):
    """匹配孤立的 '这周'/'本周'（没有指定星期几），默认本周一（或今天如果是周一）。"""
    if not any(kw in text for kw in ["这周", "本周"]):
        return None
    # 如果已被 _match_this_next_week 处理，跳过
    if re.search(r'(这周|本周)[一二三四五六日天]', text):
        return None

    # 本周一
    monday = base - datetime.timedelta(days=base.weekday())
    target = monday.replace(hour=9, minute=0, second=0, microsecond=0)
    if target.date() < base.date():
        # 如果本周一已过（对于"这周"意味着当前正在进行的一周）
        # 对于TODO场景，"这周"作为截止日期默认指向周日
        target = monday + datetime.timedelta(days=6)  # 本周日
        target = target.replace(hour=9, minute=0, second=0, microsecond=0)
    return target, 0.65


# ============================================================================
# 模式匹配优先级列表（越靠前优先级越高）
# ============================================================================

_PATTERN_FUNCTIONS = [
    _match_next_next_month,     # 下下个月X号
    _match_next_month,          # 下个月X号
    _match_specific_date,       # X月X日/X号
    _match_next_next_week,      # 下下周X
    _match_this_next_week,      # 这周X/下周X/周X (已排除下下周)
    _match_day_after_tomorrow,  # 大后天
    _match_day_before_yesterday,  # 大前天
    _match_tonight_evening,     # 今晚/明晚/后天晚上 (须在后天之前，含显式时间)
    _match_tomorrow_yesterday,  # 后天/前天
    _match_tomorrow,            # 明天/明日
    _match_today,               # 今天/今日
    _match_days_later,          # X天后
    _match_half_month,          # 半个月后
    _match_weekend,             # 周末
    _match_month_end,           # 月底/月末
    _match_year_end,            # 年底/年末
    _match_next_week_generic,   # 孤立的"下周"
    _match_this_week_generic,   # 孤立的"这周"/"本周"
    _match_next_month_generic,  # 孤立的"下个月"
    _match_hours_later,         # X小时后
    _match_minutes_later,       # X分钟后
    _match_spring_festival,     # 过年/春节
]

# 确保没有重复项
assert len(_PATTERN_FUNCTIONS) == len(set(_PATTERN_FUNCTIONS)), \
    "Duplicate pattern functions detected!"


# ============================================================================
# 辅助函数
# ============================================================================

def _char_to_weekday(char: str):
    """将 '一'/'二'/.../'日' 转换为 weekday 编号 (0=周一, 6=周日)。"""
    mapping = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
    return mapping.get(char)


def _cn_num_to_int(cn_str: str):
    """将中文数字字符串转为整数（支持1-59的时分表达）。

    支持：一/二/三...十/十一...五十九、两（同二）
    """
    simple_map = {
        "零": 0, "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
        "六": 6, "七": 7, "八": 8, "九": 9, "十": 10,
        "两": 2,
    }
    cn_str = cn_str.strip()
    if cn_str in simple_map:
        return simple_map[cn_str]
    # 十X = 10+X（十一、十二...十九）
    if cn_str.startswith("十") and len(cn_str) == 2:
        unit = simple_map.get(cn_str[1])
        if unit is not None:
            return 10 + unit
    # X十 = X*10（二十、三十...）
    if len(cn_str) == 2 and cn_str[1] == "十":
        tens = simple_map.get(cn_str[0])
        if tens is not None:
            return tens * 10
    # X十Y = X*10 + Y
    if len(cn_str) == 3 and cn_str[1] == "十":
        tens = simple_map.get(cn_str[0])
        units = simple_map.get(cn_str[2])
        if tens is not None and units is not None:
            return tens * 10 + units
    return None


def _extract_time(text: str):
    """
    从文本中提取时间（小时, 分钟）。
    支持：上午9点, 下午3点30, 晚上8点半, 中午12点, 早上八点 等。

    Returns:
        (hour, minute) 或 None
    """
    cn_digit = r'[零一二三四五六七八九十两]'
    cn_digit_compound = r'(?:十[一二三四五六七八九]?|[一二三四五六七八九]十[一二三四五六七八九]?|[零一二三四五六七八九两])'

    # 匹配模式：时间段 + (中文数字或阿拉伯数字) + 点/时 + 可选分
    m = re.search(
        r'(凌晨|早上|上午|中午|下午|傍晚|晚上|今夜|今早|明早)'
        r'(' + cn_digit_compound + r'|\d{1,2})\s*[点时]\s*'
        r'(?:(' + cn_digit_compound + r'|\d{1,2})\s*分?)?'
        r'(?:半)?',
        text
    )
    if m:
        period = m.group(1)
        hour_raw = m.group(2)
        minute_raw = m.group(3)

        # 解析小时
        hour = int(hour_raw) if hour_raw.isdigit() else _cn_num_to_int(hour_raw)
        if hour is None:
            return None

        # 解析分钟
        minute = 0
        if minute_raw:
            minute = int(minute_raw) if minute_raw.isdigit() else _cn_num_to_int(minute_raw)
            if minute is None:
                minute = 0

        # 检测"半"：在匹配位置附近查找
        search_start = max(0, m.start() - 1)
        search_end = min(len(text), m.end() + 2)
        if "半" in text[search_start:search_end]:
            minute = 30

        converter = TIME_PERIOD_MAP.get(period)
        if converter:
            hour = converter(hour)
        return (hour, minute)

    # 简化模式：仅有 "X点" 或 "X点半"（无时段）
    m_simple = re.search(
        r'(' + cn_digit_compound + r'|\d{1,2})\s*点\s*'
        r'(?:(' + cn_digit_compound + r'|\d{1,2})\s*分?|半)?',
        text
    )
    if m_simple:
        hour_raw = m_simple.group(1)
        minute_raw = m_simple.group(2)
        hour = int(hour_raw) if hour_raw.isdigit() else _cn_num_to_int(hour_raw)
        if hour is None:
            return None
        minute = 0
        if minute_raw:
            minute = int(minute_raw) if minute_raw.isdigit() else _cn_num_to_int(minute_raw)
            if minute is None:
                minute = 0
        if "半" in text:
            minute = 30
        if hour <= 6:
            hour += 12  # 1-6点很可能是下午
        return (hour, minute)

    # 时间格式：HH:MM
    m_colon = re.search(r'(\d{1,2}):(\d{2})', text)
    if m_colon:
        hour = int(m_colon.group(1))
        minute = int(m_colon.group(2))
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            return (hour, minute)

    return None


def _apply_time(target: datetime.datetime, text: str):
    """解析文本中的时间并应用到目标 datetime 上（原地修改）。"""
    time_str = _extract_time(text)
    if time_str:
        h, m_val = time_str
        target = target.replace(hour=h, minute=m_val, second=0, microsecond=0)
    return target


# ============================================================================
# 便捷函数：构建日期参考表（复用自 mcp_manager）
# ============================================================================

def build_date_reference(base: datetime.datetime = None):
    """
    构建日期参考表，用于注入 LLM prompt。
    返回本周和下周每天的具体日期字符串。

    Example:
        "本周：一06月09日 二06月10日 三06月11日 四06月12日 五06月13日 六06月14日 日06月15日
         下周：一06月16日 二06月17日 三06月18日 四06月19日 五06月20日 六06月21日 日06月22日"
    """
    if base is None:
        base = datetime.datetime.now()

    week_start = base - datetime.timedelta(days=base.weekday())
    day_abbr = ["一", "二", "三", "四", "五", "六", "日"]

    parts = []
    parts.append("本周：" + " ".join(
        f"{day_abbr[i]}{(week_start + datetime.timedelta(days=i)).strftime('%m月%d日')}"
        for i in range(7)
    ))
    next_week_start = week_start + datetime.timedelta(days=7)
    parts.append("下周：" + " ".join(
        f"{day_abbr[i]}{(next_week_start + datetime.timedelta(days=i)).strftime('%m月%d日')}"
        for i in range(7)
    ))
    return "；".join(parts)
