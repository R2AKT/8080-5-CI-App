# -*- coding: utf-8 -*-
"""Сборка примера 01: одиночный файл hello.asm -> hello.bin"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from _common import assemble_file, report, write_bin, save_map, hexdump

HERE = os.path.dirname(os.path.abspath(__file__))
ASM = os.path.join(HERE, 'hello.asm')
BIN = os.path.join(HERE, 'hello.bin')


def main():
    print("Пример 01: одиночный файл (hello.asm)")
    result = assemble_file(ASM)
    ok = report(result, 'hello.asm')
    if not ok:
        return 1

    # Сохранить бинарник и map-файл
    write_bin(BIN, result.binary)
    print(f"  Сохранено: {os.path.basename(BIN)}")
    MAP = os.path.join(HERE, 'hello.map')
    save_map(result, MAP, source_name='hello.asm')
    print(f"  Сохранено: {os.path.basename(MAP)}")
    print(hexdump(result.binary, start=result.origin))

    # Проверка ожидаемых байтов
    expected = bytes([
        0x21, 0x13, 0x01,  # LXI H, msg (0x0113)
        0xCD, 0x07, 0x01,  # CALL print_str (0x0107)
        0x76,               # HLT
        0x7E,               # MOV A, M
        0xB7,               # ORA A
        0xCA, 0x12, 0x01,  # JZ done (0x0112)
        0xD3, 0x01,         # OUT 0x01
        0x23,               # INX H
        0xC3, 0x07, 0x01,  # JMP loop (0x0107)
        0xC9,               # RET
        0x48, 0x45, 0x4C, 0x4C, 0x4F, 0x00,  # "HELLO", 0
    ])
    if result.binary == expected:
        print("  [OK]   Байты совпадают с ожидаемыми")
    else:
        print("  [FAIL] Байты не совпадают:")
        print("         ожидалось:", expected.hex(' '))
        print("         получено: ", result.binary.hex(' '))
        return 1

    print("  ИТОГ: пример 01 собран успешно")
    return 0


if __name__ == '__main__':
    sys.exit(main())
