import datetime
import threading
import time


class TimeTool:
    def __init__(self, send_msg_fn, tts_queue):
        self.send_msg = send_msg_fn
        self.tts_queue = tts_queue
        self._countdown_timer = None
        self._countdown_lock = threading.Lock()
        self._stopwatch_start = None
        self._stopwatch_elapsed = 0.0
        self._stopwatch_running = False

    def execute(self, params, current_time_str, _hint):
        sub_op = params.get("sub_op", "current_time")
        user_message = params.get("user_message", "")

        if sub_op == "current_time":
            return self._handle_current_time()
        elif sub_op == "date_calc":
            target_date = params.get("target_date")
            return self._handle_date_calc(target_date, current_time_str)
        elif sub_op == "countdown":
            duration = params.get("duration")
            return self._handle_countdown(duration)
        elif sub_op == "stopwatch":
            action = params.get("stopwatch_action", "start")
            return self._handle_stopwatch(action)
        else:
            return self._handle_current_time()

    def _handle_current_time(self):
        now = datetime.datetime.now()
        weekday_zh = ["星期一", "星期二", "星期三", "星期四", "星期五", "星期六", "星期日"]
        text = now.strftime(f"%Y年%m月%d日 {weekday_zh[now.weekday()]} %H点%M分")
        return {
            "tool": "time_tool",
            "sub_op": "current_time",
            "result_text": f"当前时间是{text}。",
            "data": {"datetime": text}
        }

    def _handle_date_calc(self, target_date, current_time_str):
        if not target_date:
            return {
                "tool": "time_tool",
                "sub_op": "date_calc",
                "result_text": "请告诉我目标日期，指挥官。",
                "data": {"error": "missing_target_date"}
            }
        try:
            target = datetime.datetime.strptime(target_date, "%Y-%m-%d")
            now = datetime.datetime.now()
            delta = target - now.replace(hour=0, minute=0, second=0, microsecond=0)
            days = delta.days
            if days < 0:
                return {
                    "tool": "time_tool",
                    "sub_op": "date_calc",
                    "result_text": f"目标日期{target_date}已经过去{abs(days)}天了，指挥官。",
                    "data": {"days": days, "target_date": target_date}
                }
            elif days == 0:
                return {
                    "tool": "time_tool",
                    "sub_op": "date_calc",
                    "result_text": f"今天就是{target_date}，指挥官。",
                    "data": {"days": 0, "target_date": target_date}
                }
            else:
                return {
                    "tool": "time_tool",
                    "sub_op": "date_calc",
                    "result_text": f"距离{target_date}还有{days}天，指挥官。",
                    "data": {"days": days, "target_date": target_date}
                }
        except ValueError:
            return {
                "tool": "time_tool",
                "sub_op": "date_calc",
                "result_text": "日期格式不正确，请使用YYYY-MM-DD格式，指挥官。",
                "data": {"error": "invalid_date_format"}
            }

    def _handle_countdown(self, duration):
        if duration is None or duration <= 0:
            return {
                "tool": "time_tool",
                "sub_op": "countdown",
                "result_text": "请告诉我倒计时时长（分钟），指挥官。",
                "data": {"error": "missing_duration"}
            }

        with self._countdown_lock:
            if self._countdown_timer:
                self._countdown_timer.cancel()
            self._countdown_timer = threading.Timer(duration * 60, self._countdown_complete, args=[duration])
            self._countdown_timer.start()

        return {
            "tool": "time_tool",
            "sub_op": "countdown",
            "result_text": f"已设置{duration}分钟倒计时，指挥官。时间到后我会提醒您。",
            "data": {"duration_min": duration}
        }

    def _countdown_complete(self, duration):
        text = f"指挥官，您设置的{duration}分钟倒计时已结束。"
        self.send_msg({"event": "countdown_complete", "duration": duration, "text": text})
        self.tts_queue.put({"type": "text", "content": text})
        with self._countdown_lock:
            self._countdown_timer = None

    def cancel_countdown(self):
        with self._countdown_lock:
            if self._countdown_timer:
                self._countdown_timer.cancel()
                self._countdown_timer = None
                return True
            return False

    def _handle_stopwatch(self, action):
        if action == "start":
            if not self._stopwatch_running:
                self._stopwatch_start = time.time()
                self._stopwatch_running = True
                return {
                    "tool": "time_tool",
                    "sub_op": "stopwatch",
                    "result_text": "秒表已开始，指挥官。",
                    "data": {"action": "start", "elapsed_sec": self._stopwatch_elapsed}
                }
            else:
                return {
                    "tool": "time_tool",
                    "sub_op": "stopwatch",
                    "result_text": "秒表正在运行中，指挥官。",
                    "data": {"action": "start", "elapsed_sec": self._get_stopwatch_elapsed()}
                }
        elif action == "pause":
            if self._stopwatch_running:
                self._stopwatch_elapsed += time.time() - self._stopwatch_start
                self._stopwatch_running = False
                elapsed = self._stopwatch_elapsed
                return {
                    "tool": "time_tool",
                    "sub_op": "stopwatch",
                    "result_text": f"秒表已暂停，累计用时{self._format_duration(elapsed)}，指挥官。",
                    "data": {"action": "pause", "elapsed_sec": elapsed}
                }
            else:
                return {
                    "tool": "time_tool",
                    "sub_op": "stopwatch",
                    "result_text": "秒表未在运行，指挥官。",
                    "data": {"action": "pause", "elapsed_sec": self._stopwatch_elapsed}
                }
        elif action == "reset":
            self._stopwatch_start = None
            self._stopwatch_elapsed = 0.0
            self._stopwatch_running = False
            return {
                "tool": "time_tool",
                "sub_op": "stopwatch",
                "result_text": "秒表已重置，指挥官。",
                "data": {"action": "reset", "elapsed_sec": 0}
            }
        elif action == "status":
            elapsed = self._get_stopwatch_elapsed()
            status = "运行中" if self._stopwatch_running else "已暂停"
            return {
                "tool": "time_tool",
                "sub_op": "stopwatch",
                "result_text": f"秒表状态：{status}，累计用时{self._format_duration(elapsed)}，指挥官。",
                "data": {"action": "status", "elapsed_sec": elapsed, "running": self._stopwatch_running}
            }
        else:
            return {
                "tool": "time_tool",
                "sub_op": "stopwatch",
                "result_text": "不支持的秒表操作，指挥官。",
                "data": {"error": "unknown_action"}
            }

    def _get_stopwatch_elapsed(self):
        if self._stopwatch_running:
            return self._stopwatch_elapsed + (time.time() - self._stopwatch_start)
        return self._stopwatch_elapsed

    @staticmethod
    def _format_duration(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        if hours > 0:
            return f"{hours}小时{minutes}分{secs}秒"
        elif minutes > 0:
            return f"{minutes}分{secs}秒"
        else:
            return f"{secs}秒"
