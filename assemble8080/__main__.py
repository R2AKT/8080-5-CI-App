# -*- coding: utf-8 -*-
"""Точка входа CLI ассемблера: ``python -m assemble8080 [args]``.

Автономная сборка Intel 8080/8085 без GUI. Полное описание — в
ASSEMBLER_GUIDE.md (раздел «Командная строка / CLI»).
"""
import sys

from .assembler import _cli_main

# Надёжная кодировка вывода: Windows cp1251-консоль не знает эмодзи/UTF-8
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

if __name__ == "__main__":
    sys.exit(_cli_main())
