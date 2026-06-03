import json
import time
import os
import urllib.parse
import requests
from datetime import datetime


QWEATHER_API_KEY = os.environ.get("QWEATHER_API_KEY", "")
QWEATHER_API_HOST = os.environ.get("QWEATHER_API_HOST", "")
QWEATHER_DEFAULT_CITY = os.environ.get("QWEATHER_DEFAULT_CITY", "北京")

CACHE_TTL = {
    "now": 600,
    "today": 3600,
    "tomorrow": 3600,
    "week": 21600,
    "hour": 1800,
    "air": 1800,
    "warning": 300,
    "astronomy": 86400,
    "indices": 21600,
}


class WeatherTool:
    def __init__(self):
        self._cache = {}
        self._api_key = ""
        self._api_host = ""
        self._default_city = QWEATHER_DEFAULT_CITY

    def set_credentials(self, api_key, api_host):
        self._api_key = api_key if api_key else QWEATHER_API_KEY
        self._api_host = api_host if api_host else QWEATHER_API_HOST

    def set_default_city(self, city):
        self._default_city = city if city else QWEATHER_DEFAULT_CITY

    def execute(self, params, current_time_str, _hint, api_key=None, api_host=None):
        location = params.get("location", "").strip()
        sub_op = params.get("sub_op", "now")

        # 使用传入的或已设置的 API key 和 host
        if api_key:
            self._api_key = api_key
        if api_host:
            self._api_host = api_host

        # 检查 API Key 和 Host 是否配置
        if not self._api_key:
            return {
                "tool": "weather", "sub_op": sub_op,
                "result_text": "指挥官，气象扫描仪缺少 API Key，请在设置中配置和风天气 API Key。"
            }
        if not self._api_host:
            return {
                "tool": "weather", "sub_op": sub_op,
                "result_text": "指挥官，气象扫描仪缺少 API Host，请在设置中配置和风天气 API Host。"
            }

        if not location:
            location = self._default_city
            is_default = True
        else:
            is_default = False

        try:
            location_id, location_name = self._lookup_location(location)
            if not location_id:
                return {
                    "tool": "weather", "sub_op": sub_op,
                    "result_text": f"指挥官，未能找到「{location}」的位置信息，请确认城市名称。"
                }

            cache_key = f"{location_id}_{sub_op}"
            cached = self._get_cache(cache_key, sub_op)
            if cached:
                return {
                    "tool": "weather", "sub_op": sub_op,
                    "result_text": cached,
                    "data": {"location": location_name, "sub_op": sub_op, "cached": True}
                }

            raw_data = None
            if sub_op == "now":
                raw_data = self._api_get_weather_now(location_id)
                result_text = self._format_now(raw_data, location_name)
            elif sub_op == "today":
                raw_data = self._api_get_daily_forecast(location_id, "3d")
                result_text = self._format_today(raw_data, location_name)
            elif sub_op == "tomorrow":
                raw_data = self._api_get_daily_forecast(location_id, "3d")
                result_text = self._format_tomorrow(raw_data, location_name)
            elif sub_op == "week":
                raw_data = self._api_get_daily_forecast(location_id, "7d")
                if not raw_data:
                    raw_data = self._api_get_daily_forecast(location_id, "3d")
                result_text = self._format_week(raw_data, location_name)
            elif sub_op == "hour":
                raw_data = self._api_get_hourly_forecast(location_id)
                result_text = self._format_hourly(raw_data, location_name)
            elif sub_op == "air":
                raw_data = self._api_get_air_now(location_id)
                result_text = self._format_air(raw_data, location_name)
            elif sub_op == "warning":
                raw_data = self._api_get_warning(location_id)
                result_text = self._format_warning(raw_data, location_name)
            elif sub_op == "astronomy":
                raw_data = self._api_get_astronomy(location_id)
                result_text = self._format_astronomy(raw_data, location_name)
            elif sub_op == "indices":
                indices_type = params.get("indices_type", "全部")
                raw_data = self._api_get_indices(location_id)
                result_text = self._format_indices(raw_data, location_name, indices_type)
            else:
                raw_data = self._api_get_weather_now(location_id)
                result_text = self._format_now(raw_data, location_name)

            if is_default and "location" not in params:
                result_text += f"（已使用默认城市{location}）"

            self._set_cache(cache_key, result_text)

            # 提取关键数据返回给前端
            extracted_data = self._extract_data_for_frontend(sub_op, raw_data)

            return {
                "tool": "weather", "sub_op": sub_op,
                "result_text": result_text,
                "data": extracted_data
            }

        except Exception as e:
            print(f"[MCP-Weather] 查询失败: {e}")
            return {
                "tool": "weather", "sub_op": sub_op,
                "result_text": "指挥官，气象扫描仪暂时无法连接到星际网络，请稍后再试。"
            }

    def _lookup_location(self, location):
        cache_key = f"geo_{location}"
        entry = self._cache.get(cache_key)
        if entry and time.time() - entry["time"] < 86400:
            return entry["value"]["id"], entry["value"]["name"]

        params = {"location": location, "number": 1}
        url = f"{self._get_api_host()}/geo/v2/city/lookup?{urllib.parse.urlencode(params)}"
        data = self._api_get(url)

        if data and data.get("code") == "200":
            loc_list = data.get("location", [])
            if loc_list:
                loc = loc_list[0]
                self._cache[cache_key] = {
                    "value": {"id": loc["id"], "name": loc["name"]},
                    "time": time.time()
                }
                return loc["id"], loc["name"]

        return None, None

    def _extract_data_for_frontend(self, sub_op, raw_data):
        """提取前端需要的数据结构"""
        if not raw_data or raw_data.get("code") != "200":
            return {}

        if sub_op == "now":
            now = raw_data.get("now", {})
            return {
                "temp": now.get("temp"),
                "feelsLike": now.get("feelsLike"),
                "text": now.get("text"),
                "icon": now.get("icon"),
                "windDir": now.get("windDir"),
                "windScale": now.get("windScale"),
                "humidity": now.get("humidity"),
                "pressure": now.get("pressure"),
                "vis": now.get("vis")
            }
        elif sub_op in ["today", "tomorrow", "week"]:
            daily = raw_data.get("daily", [])
            return {
                "daily": [
                    {
                        "fxDate": d.get("fxDate"),
                        "tempMax": d.get("tempMax"),
                        "tempMin": d.get("tempMin"),
                        "textDay": d.get("textDay"),
                        "textNight": d.get("textNight"),
                        "iconDay": d.get("iconDay"),
                        "iconNight": d.get("iconNight"),
                        "windDirDay": d.get("windDirDay"),
                        "windScaleDay": d.get("windScaleDay")
                    }
                    for d in daily
                ]
            }
        elif sub_op == "hour":
            hourly = raw_data.get("hourly", [])
            return {
                "hourly": [
                    {
                        "fxTime": h.get("fxTime"),
                        "temp": h.get("temp"),
                        "text": h.get("text"),
                        "icon": h.get("icon"),
                        "windDir": h.get("windDir"),
                        "windScale": h.get("windScale"),
                        "humidity": h.get("humidity")
                    }
                    for h in hourly
                ]
            }
        elif sub_op == "air":
            now = raw_data.get("now", {})
            return {
                "aqi": now.get("aqi"),
                "category": now.get("category"),
                "pm2p5": now.get("pm2p5"),
                "pm10": now.get("pm10"),
                "no2": now.get("no2"),
                "so2": now.get("so2"),
                "co": now.get("co"),
                "o3": now.get("o3")
            }
        elif sub_op == "warning":
            warnings = raw_data.get("warning", [])
            return {
                "warning": [
                    {
                        "title": w.get("title"),
                        "level": w.get("level"),
                        "type": w.get("type"),
                        "text": w.get("text")
                    }
                    for w in warnings
                ]
            }
        elif sub_op == "astronomy":
            # 天文API返回的数据直接在根级别，不是嵌套在daily中
            return {
                "sunrise": raw_data.get("sunrise"),
                "sunset": raw_data.get("sunset"),
                "moonrise": raw_data.get("moonrise"),
                "moonset": raw_data.get("moonset"),
                "moonPhase": raw_data.get("moonPhase")
            }
        elif sub_op == "indices":
            daily = raw_data.get("daily", [])
            return {
                "daily": [
                    {
                        "name": d.get("name"),
                        "level": d.get("level"),
                        "category": d.get("category"),
                        "text": d.get("text"),
                        "type": d.get("type")
                    }
                    for d in daily
                ]
            }
        return {}

    def _format_now(self, now_data, location_name):
        if not now_data or now_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的实时天气数据。"

        now = now_data.get("now", {})
        temp = now.get("temp", "?")
        feels_like = now.get("feelsLike", "?")
        text = now.get("text", "?")
        wind_dir = now.get("windDir", "?")
        wind_scale = now.get("windScale", "?")
        humidity = now.get("humidity", "?")

        temp_val = int(temp) if temp.isdigit() or (temp.startswith("-") and temp[1:].isdigit()) else 0

        tip = self._generate_now_tip(text, temp_val, wind_scale)

        lines = [
            f"【{location_name}实时天气】",
            f"天气：{text}",
            f"气温：{temp}℃（体感{feels_like}℃）",
            f"风向：{wind_dir} {wind_scale}级",
            f"湿度：{humidity}%",
            f"",
            f"副官提示：{tip}"
        ]
        return "\n".join(lines)

    def _format_today(self, daily_data, location_name):
        if not daily_data or daily_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的今日预报数据。"

        daily_list = daily_data.get("daily", [])
        if not daily_list:
            return f"指挥官，{location_name}的今日预报数据暂不可用。"

        today = daily_list[0]
        text_day = today.get("textDay", "?")
        text_night = today.get("textNight", "?")
        temp_max = today.get("tempMax", "?")
        temp_min = today.get("tempMin", "?")

        try:
            t_max = int(temp_max)
            t_min = int(temp_min)
        except ValueError:
            t_max, t_min = 0, 0

        tip = self._generate_day_tip(t_max, t_min, text_day)

        lines = [
            f"【{location_name}今日预报】",
            f"白天：{text_day}，{temp_max}℃",
            f"夜间：{text_night}，{temp_min}℃",
            f"",
            f"副官提示：{tip}"
        ]
        return "\n".join(lines)

    def _format_tomorrow(self, daily_data, location_name):
        if not daily_data or daily_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的明日预报数据。"

        daily_list = daily_data.get("daily", [])
        if len(daily_list) < 2:
            return f"指挥官，{location_name}的明日预报数据暂不可用。"

        tomorrow = daily_list[1]
        text_day = tomorrow.get("textDay", "?")
        text_night = tomorrow.get("textNight", "?")
        temp_max = tomorrow.get("tempMax", "?")
        temp_min = tomorrow.get("tempMin", "?")
        wind_dir_day = tomorrow.get("windDirDay", "?")
        wind_scale_day = tomorrow.get("windScaleDay", "?")

        try:
            t_max = int(temp_max)
            t_min = int(temp_min)
        except ValueError:
            t_max, t_min = 0, 0

        rain_related = any(w in text_day for w in ["雨", "雪", "雹"])
        tip = self._generate_tomorrow_tip(t_max, t_min, text_day, rain_related)

        lines = [
            f"【{location_name}明日预报】",
            f"白天：{text_day}，{temp_max}℃",
            f"夜间：{text_night}，{temp_min}℃",
            f"风力：{wind_dir_day} {wind_scale_day}级",
            f"",
            f"副官提示：{tip}"
        ]
        return "\n".join(lines)

    def _format_week(self, daily_data, location_name):
        if not daily_data or daily_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的多日预报数据。"

        daily_list = daily_data.get("daily", [])
        if not daily_list:
            return f"指挥官，{location_name}的多日预报数据暂不可用。"

        lines = [f"【{location_name}未来{len(daily_list)}天预报】"]
        for day in daily_list:
            date_str = day.get("fxDate", "?")[-5:]
            text_day = day.get("textDay", "?")
            temp_min = day.get("tempMin", "?")
            temp_max = day.get("tempMax", "?")
            lines.append(f"{date_str} {text_day} {temp_min}℃~{temp_max}℃")

        has_rain = any("雨" in d.get("textDay", "") for d in daily_list)
        has_snow = any("雪" in d.get("textDay", "") for d in daily_list)
        if has_rain:
            lines.append(f"\n副官提示：预报期内有降雨，请指挥官提前做好出行安排。")
        elif has_snow:
            lines.append(f"\n副官提示：预报期内有降雪，请注意防寒保暖。")

        return "\n".join(lines)

    def _format_hourly(self, hourly_data, location_name):
        if not hourly_data or hourly_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的逐小时预报数据。"

        hourly_list = hourly_data.get("hourly", [])
        if not hourly_list:
            return f"指挥官，{location_name}的逐小时预报数据暂不可用。"

        lines = [f"【{location_name}逐小时预报】"]
        rain_hours = []
        for hour in hourly_list[:12]:
            fx_time = hour.get("fxTime", "?")
            if fx_time != "?" and len(fx_time) >= 16:
                fx_time = fx_time[11:16]
            temp = hour.get("temp", "?")
            text = hour.get("text", "?")
            lines.append(f"{fx_time} {text} {temp}℃")
            if "雨" in text or "雪" in text:
                rain_hours.append(fx_time)

        if rain_hours:
            lines.append(f"\n副官提示：预计{','.join(rain_hours[:3])}有降水，请指挥官合理安排出行时间。")

        return "\n".join(lines)

    def _format_air(self, air_data, location_name):
        if not air_data or air_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的空气质量数据。"

        now = air_data.get("now", {})
        aqi = now.get("aqi", "?")
        category = now.get("category", "?")
        pm25 = now.get("pm2p5", "?")
        pm10 = now.get("pm10", "?")

        advice = self._get_air_advice(category)

        lines = [
            f"【{location_name}空气质量】",
            f"AQI：{aqi}（{category}）",
            f"PM2.5：{pm25}μg/m³",
            f"PM10：{pm10}μg/m³",
            f"",
            f"副官提示：{advice}"
        ]
        return "\n".join(lines)

    def _format_warning(self, warning_data, location_name):
        if not warning_data or warning_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的预警信息。"

        warning_list = warning_data.get("warning", [])
        if not warning_list:
            return f"指挥官，{location_name}目前没有灾害预警，天气状况良好。"

        lines = [f"【{location_name}灾害预警】"]
        for warn in warning_list:
            title = warn.get("title", "?")
            level = warn.get("level", "?")
            text = warn.get("text", "?")
            lines.append(f"预警类型：{title}")
            lines.append(f"预警等级：{level}")
            if text:
                lines.append(f"预警内容：{text[:150]}")
            lines.append("")

        lines.append("副官提示：请指挥官注意安全，做好防护措施。")
        return "\n".join(lines)

    def _format_astronomy(self, astro_data, location_name):
        if not astro_data or astro_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的天文信息。"

        # 天文API返回的数据直接在根级别
        sunrise = astro_data.get("sunrise", "?")
        sunset = astro_data.get("sunset", "?")
        moonrise = astro_data.get("moonrise", "?")
        moonset = astro_data.get("moonset", "?")
        moon_phase = astro_data.get("moonPhase", "?")

        lines = [
            f"【{location_name}天文信息】",
            f"日出：{sunrise}",
            f"日落：{sunset}",
        ]
        if moonrise and moonrise != "-":
            lines.append(f"月出：{moonrise}")
            lines.append(f"月落：{moonset}")
            lines.append(f"月相：{moon_phase}")

        lines.append(f"\n副官提示：今日日照时长可见，适合户外行动安排。")
        return "\n".join(lines)

    def _format_indices(self, indices_data, location_name, indices_type):
        if not indices_data or indices_data.get("code") != "200":
            return f"指挥官，未能获取到{location_name}的生活指数数据。"

        daily_list = indices_data.get("daily", [])
        if not daily_list:
            return f"指挥官，{location_name}的生活指数数据暂不可用。"

        if indices_type != "全部":
            for item in daily_list:
                if indices_type in item.get("name", ""):
                    name = item.get("name", "?")
                    category = item.get("category", "?")
                    text = item.get("text", "")
                    return f"【{location_name}今日{name}】\n等级：{category}\n建议：{text}\n\n副官提示：已为您精准查询{name}。"
            return f"指挥官，暂未查询到{location_name}的{indices_type}指数数据。"

        key_names = ["穿衣", "紫外线", "感冒"]
        lines = [f"【{location_name}今日生活指数摘要】"]
        found_any = False
        for item in daily_list:
            for key in key_names:
                if key in item.get("name", ""):
                    name = item.get("name", "?")
                    category = item.get("category", "?")
                    lines.append(f"{name}：{category}")
                    found_any = True
                    break

        if not found_any:
            return f"指挥官，{location_name}的生活指数数据暂不可用。"

        lines.append(f"\n副官提示：如需了解洗车、钓鱼等其他指数，指挥官可以单独询问。")
        return "\n".join(lines)

    def _generate_now_tip(self, text, temp, wind_scale):
        tips = []
        try:
            scale = int(wind_scale) if wind_scale != "?" else 0
        except (ValueError, TypeError):
            scale = 0

        if any(w in text for w in ["雨", "雪", "雹"]):
            tips.append("请携带雨具，注意出行安全")
        elif scale >= 5:
            tips.append("风力较强，建议减少高空作业")

        if temp > 35:
            tips.append("高温天气，注意防暑降温")
        elif temp > 30:
            tips.append("天气炎热，多补充水分")
        elif temp < 0:
            tips.append("严寒天气，注意防寒保暖")
        elif temp < 10:
            tips.append("天气偏冷，建议穿着保暖外套")
        elif 18 <= temp <= 28:
            tips.append("天气舒适，适合外出活动")

        return "；".join(tips) if tips else "天气状况正常，可安排常规行动。"

    def _generate_day_tip(self, t_max, t_min, text_day):
        tips = []
        diff = abs(t_max - t_min) if t_max and t_min else 0

        if diff > 10:
            tips.append("昼夜温差较大，建议携带外套")

        if any(w in text_day for w in ["雨", "雪", "雹"]):
            tips.append("有降水预报，请携带雨具")
        elif t_max > 33:
            tips.append("高温天气，注意防暑降温")

        if t_min < 5:
            tips.append("夜间气温偏低，请做好防寒准备")

        return "；".join(tips) if tips else "天气状况良好，适合各类户外行动。"

    def _generate_tomorrow_tip(self, t_max, t_min, text_day, rain_related):
        tips = []
        diff = abs(t_max - t_min) if t_max and t_min else 0

        if rain_related:
            tips.append("明日有降水，请携带雨具")

        if diff > 10:
            tips.append("温差较大，请注意增减衣物")

        return "；".join(tips) if tips else "明日天气良好，可正常安排行动。"

    @staticmethod
    def _get_air_advice(category):
        advice_map = {
            "优": "空气质量优秀，适合所有户外活动。",
            "良": "空气质量良好，可正常活动。",
            "轻度污染": "敏感人群需减少户外活动。",
            "中度污染": "建议减少户外活动，佩戴口罩。",
            "重度污染": "避免户外活动，建议开启空气净化。",
            "严重污染": "禁止户外活动，紧闭门窗。"
        }
        return advice_map.get(category, "请根据空气指数合理安排出行。")

    def _get_api_host(self):
        """获取 API host，优先使用实例设置"""
        return getattr(self, '_api_host', QWEATHER_API_HOST)

    def _api_get_weather_now(self, location_id):
        params = {"location": location_id}
        url = f"{self._get_api_host()}/v7/weather/now?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_daily_forecast(self, location_id, days):
        params = {"location": location_id}
        url = f"{self._get_api_host()}/v7/weather/{days}?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_hourly_forecast(self, location_id):
        params = {"location": location_id}
        url = f"{self._get_api_host()}/v7/weather/24h?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_air_now(self, location_id):
        params = {"location": location_id}
        url = f"{self._get_api_host()}/v1/air/now?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_warning(self, location_id):
        params = {"location": location_id}
        url = f"{self._get_api_host()}/v7/warning/now?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_astronomy(self, location_id):
        # 天文API需要日期参数，格式为 yyyyMMdd
        today = datetime.now().strftime("%Y%m%d")
        params = {"location": location_id, "date": today}
        url = f"{self._get_api_host()}/v7/astronomy/sun?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get_indices(self, location_id):
        params = {"location": location_id, "type": "1,2,3,4,5,6,7,8,9"}
        url = f"{self._get_api_host()}/v7/indices/1d?{urllib.parse.urlencode(params)}"
        return self._api_get(url)

    def _api_get(self, url):
        try:
            if not url.startswith("http"):
                url = "https://" + url
            # 使用实例的 API key
            api_key = getattr(self, '_api_key', QWEATHER_API_KEY)
            resp = requests.get(url, params={"key": api_key}, timeout=10)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.HTTPError as e:
            print(f"[MCP-Weather] HTTP错误 {e.response.status_code}: {e.response.reason if e.response else e}")
            return None
        except requests.exceptions.ConnectionError as e:
            print(f"[MCP-Weather] 网络连接错误: {e}")
            return None
        except requests.exceptions.Timeout as e:
            print(f"[MCP-Weather] 请求超时: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[MCP-Weather] 请求异常: {e}")
            return None
        except json.JSONDecodeError as e:
            print(f"[MCP-Weather] JSON解析失败: {e}")
            return None
        except Exception as e:
            print(f"[MCP-Weather] API请求异常: {e}")
            return None

    def _get_cache(self, key, sub_op):
        entry = self._cache.get(key)
        if entry is None:
            return None
        ttl = CACHE_TTL.get(sub_op, 3600)
        if time.time() - entry["time"] > ttl:
            del self._cache[key]
            return None
        return entry["value"]

    def _set_cache(self, key, value):
        self._cache[key] = {"value": value, "time": time.time()}
