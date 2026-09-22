# -*- coding: utf-8 -*-
"""Сборка примера 02: все директивы (directives.asm) -> directives.bin"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _common import assemble_file, report, write_bin, save_map, hexdump

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, 'directives.asm')
BIN = os.path.join(HERE, 'directives.bin')


def main():
    print("Пример 02: все директивы (directives.asm)")
    result = assemble_file(ASM)
    ok = report(result, 'directives.asm')
    if not ok:
        return 1

    write_bin(BIN, result.binary)
    print(f"  Сохранено: {os.path.basename(BIN)}")
    MAP = os.path.join(HERE, 'directives.map')
    save_map(result, MAP, source_name='directives.asm')
    print(f"  Сохранено: {os.path.basename(MAP)}")
    print(hexdump(result.binary, start=result.origin))

    fails = 0

    def check(name, cond):
        nonlocal fails
        if cond:
            print(f"  [OK]   {name}")
        else:
            print(f"  [FAIL] {name}")
            fails += 1

    b = result.binary
    # #if VERSION>=2 -> строка "v2"
    check("#if: встроена строка 'v2'", b"v2" in b)
    check("#include defs.inc: нет ошибок подключения", ok)
    check("#path + #include extra.inc: нет ошибок подключения", ok)
    # MACRO PUTCHAR 'A' -> MVI A,'A' (3E 41) + OUT 0x01 (D3 01)
    check("MACRO: PUTCHAR 'A' -> 3E 41 D3 01", bytes([0x3E, 0x41, 0xD3, 0x01]) in b)
    check("MACRO: PUTCHAR 'B' -> 3E 42 D3 01", bytes([0x3E, 0x42, 0xD3, 0x01]) in b)
    # REPT 3 -> три 0xAA подряд
    check("REPT 3: три байта 0xAA подряд", bytes([0xAA, 0xAA, 0xAA]) in b)
    # DB строка
    check("DB: строка 'DATA'", b"DATA" in b)
    # DW 0x1234, 0x5678 -> 34 12 78 56 (little-endian)
    check("DW: 0x1234,0x5678 -> 34 12 78 56", bytes([0x34, 0x12, 0x78, 0x56]) in b)
    # DS 8 -> восемь нулей подряд
    check("DS 8: восемь нулей подряд", bytes(8) in b)

    # Проверка символов (EQU)
    syms = result.symbols
    check("EQU: BASE = 0x0200", syms.get('BASE') == 0x0200)
    check("EQU: BUF_END = 0x0210", syms.get('BUF_END') == 0x0210)
    check("EQU (defs.inc): LED_ON = 0xFF", syms.get('LED_ON') == 0xFF)
    check("EQU (extra.inc): EXTRA_FLAG = 1", syms.get('EXTRA_FLAG') == 1)
    check("Метка: local_label определена", 'LOCAL_LABEL' in syms)
    check("Метка: global_label определена", 'GLOBAL_LABEL' in syms)

    if fails:
        print(f"  ИТОГ: пример 02 — {fails} проверок не пройдено")
        return 1
    print("  ИТОГ: пример 02 собран успешно, все проверки пройдены")
    return 0


if __name__ == '__main__':
    sys.exit(main())
