# -*- coding: utf-8 -*-
"""Сборка примера 03: макросы, REPT, условная сборка (macros.asm) -> macros.bin"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _common import assemble_file, report, write_bin, save_map, hexdump

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, 'macros.asm')
BIN = os.path.join(HERE, 'macros.bin')


def main():
    print("Пример 03: макросы, REPT, условная сборка (macros.asm)")
    result = assemble_file(ASM)
    ok = report(result, 'macros.asm')
    if not ok:
        return 1

    write_bin(BIN, result.binary)
    print(f"  Сохранено: {os.path.basename(BIN)}")
    MAP = os.path.join(HERE, 'macros.map')
    save_map(result, MAP, source_name='macros.asm')
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
    # PUTCHAR 'X' -> MVI A,'X' (3E 58) + OUT 0x01 (D3 01)
    check("MACRO: PUTCHAR 'X' -> 3E 58 D3 01", bytes([0x3E, 0x58, 0xD3, 0x01]) in b)
    check("MACRO: PUTCHAR 'Y' -> 3E 59 D3 01", bytes([0x3E, 0x59, 0xD3, 0x01]) in b)
    # STORE16 0x0200, 0x1234 -> 21 00 02 11 34 12 73 23 72
    #   LXI H,0x0200 (21 00 02) + LXI D,0x1234 (11 34 12)
    #   + MOV M,E (73) + INX H (23) + MOV M,D (72)
    store16 = bytes([0x21, 0x00, 0x02, 0x11, 0x34, 0x12, 0x73, 0x23, 0x72])
    check("MACRO: STORE16 0x0200,0x1234", store16 in b)
    # OUTER (вложенный) -> 2 x NOP
    check("Вложенный макрос OUTER -> 2 x NOP", bytes([0x00, 0x00]) in b)
    # DBPAIR 0x55 -> 55 55
    check("MACRO &-префикс: DBPAIR 0x55 -> 55 55", bytes([0x55, 0x55]) in b)
    # REPT 3 NOP -> 3 x 00
    check("REPT 3: три NOP подряд", bytes([0x00, 0x00, 0x00]) in b)
    # #if DEBUG -> "DEBUG"
    check("#if DEBUG: строка 'DEBUG'", b"DEBUG" in b)
    check("#else: строки 'RELEASE' нет", b"RELEASE" not in b)

    if fails:
        print(f"  ИТОГ: пример 03 — {fails} проверок не пройдено")
        return 1
    print("  ИТОГ: пример 03 собран успешно, все проверки пройдены")
    return 0


if __name__ == '__main__':
    sys.exit(main())
