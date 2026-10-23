# -*- coding: utf-8 -*-
"""Сборка примера 04: многофайловая сборка с линковкой.

main.asm + helper.asm -> main.obj + helper.obj -> (app.lnk) -> app.bin + app.map
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _common import (assemble_file, report, save_obj_file, run_link,
                     write_bin, hexdump, read)

HERE = os.path.dirname(os.path.abspath(__file__))
MAIN_ASM = os.path.join(HERE, 'main.asm')
HELPER_ASM = os.path.join(HERE, 'helper.asm')
MAIN_OBJ = os.path.join(HERE, 'main.obj')
HELPER_OBJ = os.path.join(HERE, 'helper.obj')
LNK = os.path.join(HERE, 'app.lnk')
BIN = os.path.join(HERE, 'app.bin')
MAP = os.path.join(HERE, 'app.map')


def main():
    print("Пример 04: многофайловая сборка с линковкой")

    # 1. Ассемблировать main.asm -> main.obj
    r_main = assemble_file(MAIN_ASM)
    if not report(r_main, 'main.asm'):
        return 1
    save_obj_file(r_main, MAIN_OBJ, 'main.asm')
    print(f"  Сохранено: {os.path.basename(MAIN_OBJ)} "
          f"(exports={r_main.exports}, imports={r_main.imports}, "
          f"relocations={len(r_main.relocations)})")

    # 2. Ассемблировать helper.asm -> helper.obj
    r_helper = assemble_file(HELPER_ASM)
    if not report(r_helper, 'helper.asm'):
        return 1
    save_obj_file(r_helper, HELPER_OBJ, 'helper.asm')
    print(f"  Сохранено: {os.path.basename(HELPER_OBJ)} "
          f"(exports={r_helper.exports})")

    # Проверка: main импортирует HELPER, helper экспортирует HELPER
    fails = 0

    def check(name, cond):
        nonlocal fails
        if cond:
            print(f"  [OK]   {name}")
        else:
            print(f"  [FAIL] {name}")
            fails += 1

    check("main.asm: IMPORT HELPER", 'HELPER' in r_main.imports)
    check("main.asm: EXPORT main", 'main' in r_main.exports)
    check("main.asm: relocation для CALL HELPER", len(r_main.relocations) == 1)
    check("helper.asm: EXPORT HELPER", 'HELPER' in r_helper.exports)

    # 3. Линковка по app.lnk
    print("  Линковка по app.lnk ...")
    lr = run_link(LNK)
    if not lr.success:
        print(f"  [FAIL] Линковка:")
        for e in lr.errors:
            print(f"         {e}")
        return 1
    print(f"  [OK]   Линковка: {len(lr.binary)} байт, "
          f"символов: {len(lr.symbols)}")
    for w in lr.warnings:
        print(f"         (warn) {w}")

    # 4. Проверка результата
    check("app.bin создан", os.path.exists(BIN))
    check("app.map создан", os.path.exists(MAP))

    b = lr.binary
    # main.asm в 0x0100: MVI A,0x42 (3E 42) + CALL HELPER (CD 06 01) + HLT (76)
    check("app.bin[0x0100]: 3E 42 CD 06 01 76",
          b[0x0100:0x0106] == bytes([0x3E, 0x42, 0xCD, 0x06, 0x01, 0x76]))
    # helper.asm в 0x0106: ADD B (80) + RET (C9) — последовательная раскладка от ORIGIN
    check("app.bin[0x0106]: 80 C9 (helper после main)",
          b[0x0106:0x0108] == bytes([0x80, 0xC9]))
    # CALL HELPER должен быть пропатчен на 0x0106 (little-endian: 06 01)
    check("CALL HELPER пропатчен на 0x0106",
          b[0x0103:0x0105] == bytes([0x06, 0x01]))

    # Проверка map-файла
    if os.path.exists(MAP):
        map_text = read(MAP)
        check("app.map содержит HELPER", 'HELPER' in map_text)
        check("app.map содержит MAIN", 'MAIN' in map_text)
    else:
        check("app.map существует", False)

    # Hexdump ключевых областей
    print("  app.bin [0x0100..0x0105]:")
    print(hexdump(b[0x0100:0x0106], start=0x0100))
    print("  app.bin [0x0106..0x0107]:")
    print(hexdump(b[0x0106:0x0108], start=0x0106))

    if fails:
        print(f"  ИТОГ: пример 04 — {fails} проверок не пройдено")
        return 1
    print("  ИТОГ: пример 04 собран и слинкован успешно, все проверки пройдены")
    return 0


if __name__ == '__main__':
    sys.exit(main())
