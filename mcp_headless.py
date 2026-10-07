# -*- coding: utf-8 -*-
"""
mcp_headless.py — headless-запуск MCP-сервера i8080-5 CI без GUI.

Точка входа для VS Code-плагина i8080_ci-vscode. Поднимает один экземпляр
MCP-сервера (SSE, порт 8000 по умолчанию) на базе HeadlessHost — без PySide6-GUI.

Использование:
    python mcp_headless.py --profile full --port 8000
    python mcp_headless.py --profile empty8085 --host 127.0.0.1 --port 8000

Остановка: Ctrl+C (SIGINT) или SIGTERM.
"""
from __future__ import annotations

import os
import sys
import time
import signal
import argparse

# ВАЖНО: offscreen-платформу ставим ДО импорта PySide6, чтобы QObject
# (I8080Emulator) не пытался создавать GUI-контекст.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

# Корень проекта в sys.path
_PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


def _print_banner(profile: str, cpu: str, host: str, port: int) -> None:
    print("=" * 60, flush=True)
    print("  i8080-5 CI — Headless MCP Server", flush=True)
    print("=" * 60, flush=True)
    print(f"  Профиль : {profile}", flush=True)
    print(f"  CPU     : {cpu}", flush=True)
    print(f"  SSE     : http://{host}:{port}/sse", flush=True)
    print(f"  PID     : {os.getpid()}", flush=True)
    print("=" * 60, flush=True)
    print("  Готов к подключению. Остановка: Ctrl+C", flush=True)
    print("=" * 60, flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Headless MCP-сервер i8080-5 CI (без GUI)"
    )
    parser.add_argument(
        "--profile", default="full",
        help="Имя профиля системы (по умолчанию: full)",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Хост для SSE (по умолчанию: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8000,
        help="Порт для SSE (по умолчанию: 8000)",
    )
    args = parser.parse_args()

    # Импорт после установки QT_QPA_PLATFORM
    from i8080_ci.headless_host import HeadlessHost
    from mcp_server import MCPServerManager

    # --- Создаём headless-хост и загружаем профиль ---
    host_obj = HeadlessHost(project_root=_PROJECT_ROOT)
    try:
        cpu = host_obj.load_profile(args.profile)
    except Exception as e:
        print(f"[i8080-ci] ОШИБКА загрузки профиля '{args.profile}': {e}",
              file=sys.stderr, flush=True)
        return 2

    _print_banner(args.profile, cpu, args.host, args.port)

    # --- Поднимаем MCP-сервер ---
    server = MCPServerManager(host_obj, host=args.host, port=args.port)
    server.start()

    # --- Живём, пока не попросят остановиться ---
    stop = {"flag": False}

    def _handle_signal(signum, frame):
        stop["flag"] = True

    signal.signal(signal.SIGINT, _handle_signal)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, _handle_signal)

    try:
        while not stop["flag"]:
            if not server.running:
                # Сервер упал — выходим с ошибкой
                print("[i8080-ci] MCP-сервер остановился unexpectedly.",
                      file=sys.stderr, flush=True)
                return 1
            time.sleep(0.5)
    finally:
        server.stop()
        print("[i8080-ci] Headless MCP-сервер остановлен.", flush=True)

    return 0


if __name__ == "__main__":
    sys.exit(main())
