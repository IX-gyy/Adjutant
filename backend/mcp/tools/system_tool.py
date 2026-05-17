import psutil


class SystemTool:
    def __init__(self):
        pass

    def execute(self, params, current_time_str, _hint):
        sub_op = params.get("sub_op", "all")
        try:
            data = self._collect_data(sub_op)
            result_text = self._format_result(data, sub_op)
            return {"tool": "system_status", "sub_op": sub_op, "result_text": result_text, "data": data}
        except Exception as e:
            print(f"[MCP-System] 采集失败: {e}")
            return {"tool": "system_status", "sub_op": sub_op,
                    "result_text": "抱歉指挥官，战术扫描系统暂时离线，请稍后再试。"}

    def _collect_data(self, sub_op):
        data = {}

        if sub_op in ("all", "cpu"):
            data["cpu"] = {
                "usage": psutil.cpu_percent(interval=0.5),
                "cores": psutil.cpu_count(logical=False),
                "threads": psutil.cpu_count(logical=True)
            }

        if sub_op in ("all", "memory"):
            mem = psutil.virtual_memory()
            data["memory"] = {
                "total_gb": round(mem.total / (1024**3), 1),
                "used_gb": round(mem.used / (1024**3), 1),
                "usage": mem.percent
            }

        if sub_op in ("all", "disk"):
            disk = psutil.disk_usage("/")
            data["disk"] = {
                "total_gb": round(disk.total / (1024**3), 1),
                "used_gb": round(disk.used / (1024**3), 1),
                "usage": round(disk.used / disk.total * 100, 1)
            }

        if sub_op in ("all", "battery"):
            battery = psutil.sensors_battery()
            if battery:
                data["battery"] = {
                    "percent": battery.percent,
                    "plugged": battery.power_plugged,
                    "time_left_min": int(battery.secsleft / 60) if battery.secsleft != psutil.POWER_TIME_UNLIMITED else None
                }
            else:
                data["battery"] = None

        if sub_op in ("all", "network"):
            data["network"] = {"status": "connected"}
            try:
                import socket
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.settimeout(0.5)
                s.connect(("8.8.8.8", 80))
                data["network"]["ip"] = s.getsockname()[0]
                s.close()
            except Exception:
                data["network"]["status"] = "disconnected"

        return data

    def _format_result(self, data, sub_op):
        parts = []

        if "cpu" in data:
            c = data["cpu"]
            parts.append(f"CPU占用{c['usage']}%（{c['cores']}核{c['threads']}线程）")

        if "memory" in data:
            m = data["memory"]
            parts.append(f"内存使用{m['usage']}%（{m['used_gb']}G/{m['total_gb']}G）")

        if "disk" in data:
            d = data["disk"]
            parts.append(f"磁盘占用{d['usage']}%（{d['used_gb']}G/{d['total_gb']}G）")

        if "battery" in data:
            b = data["battery"]
            if b:
                plugged = "已接通电源" if b["plugged"] else "电池供电"
                parts.append(f"电量{b['percent']}%（{plugged}）")
            else:
                parts.append("无电池信息")

        if "network" in data:
            n = data["network"]
            if n["status"] == "connected":
                parts.append(f"网络已连接（IP: {n.get('ip', '未知')}）")
            else:
                parts.append("网络未连接")

        if not parts:
            return "战术扫描完成，未发现异常数据。"

        return "战术扫描报告：" + "；".join(parts) + "。"
