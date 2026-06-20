#!/usr/bin/env python3
"""小秋无状态问答 - 对话调用脚本

用法:
  python chat_client.py "用一句话介绍你自己"
  python chat_client.py              # 进入交互模式，输入 exit 或 Ctrl+C 退出

环境变量:
  SMART_QIU_BASE_URL   默认 http://127.0.0.1:18080
  SMART_QIU_API_TOKEN  API Key（与 config.yaml 中 security.api_token 一致）
"""

from __future__ import annotations

import argparse
import os
import sys

try:
    import requests
except ImportError:
    print("请先安装依赖: pip install requests", file=sys.stderr)
    sys.exit(1)

DEFAULT_BASE_URL = "https://ssemarket.cn"
CHAT_PATH = "/api/v1/agent/external/chat"
TIMEOUT_SECONDS = 120


def get_config() -> tuple[str, str]:
    base_url = os.environ.get("SMART_QIU_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    api_token = os.environ.get("SMART_QIU_API_TOKEN", "")
    if not api_token:
        print(
            "未设置 SMART_QIU_API_TOKEN，请在环境变量中配置 API Key。",
            file=sys.stderr,
        )
        sys.exit(1)
    return base_url, api_token


def chat(query: str, base_url: str, api_token: str) -> str:
    url = f"{base_url}{CHAT_PATH}"
    headers = {
        "Content-Type": "application/json",
        "X-API-Token": api_token,
    }

    resp = requests.post(
        url,
        headers=headers,
        json={"query": query},
        timeout=TIMEOUT_SECONDS,
    )

    if resp.ok:
        return resp.text

    request_id = resp.headers.get("X-Request-ID", "")
    detail = resp.text.strip() or resp.reason
    suffix = f" (X-Request-ID: {request_id})" if request_id else ""
    raise RuntimeError(f"HTTP {resp.status_code}: {detail}{suffix}")


def run_once(query: str) -> None:
    base_url, api_token = get_config()
    try:
        reply = chat(query, base_url, api_token)
    except requests.RequestException as exc:
        print(f"请求失败: {exc}", file=sys.stderr)
        sys.exit(1)
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        sys.exit(1)

    print(reply)


def run_interactive() -> None:
    base_url, api_token = get_config()
    print(f"已连接: {base_url}{CHAT_PATH}")
    print("无状态模式：每轮问答相互独立。输入 exit 或 quit 退出。\n")

    while True:
        try:
            query = input("你: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见。")
            break

        if not query:
            continue
        if query.lower() in {"exit", "quit", "q"}:
            print("再见。")
            break

        try:
            reply = chat(query, base_url, api_token)
        except requests.RequestException as exc:
            print(f"请求失败: {exc}\n", file=sys.stderr)
            continue
        except RuntimeError as exc:
            print(f"错误: {exc}\n", file=sys.stderr)
            continue

        print(f"\n小秋: {reply}\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="调用小秋无状态问答接口")
    parser.add_argument(
        "query",
        nargs="?",
        help="单次提问内容；省略则进入交互模式",
    )
    args = parser.parse_args()

    if args.query:
        run_once(args.query)
    else:
        run_interactive()


if __name__ == "__main__":
    main()
