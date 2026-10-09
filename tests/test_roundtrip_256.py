# -*- coding: utf-8 -*-
"""Round-trip test: assemble -> disassemble -> re-assemble -> compare, all 256 opcodes.

Проверяет согласованность ассемблера и дизассемблера для обоих CPU (i8080/i8085):
  A) ПОКРЫТИЕ: все 256 значений старшего байта дизассемблируются в непустой текст.
  B) ROUND-TRIP: программа из ВСЕХ documented-опкодов -> дизассемблер -> ассемблер
     -> байты совпадают с исходными (undocumented NOP*/RET*/CALL*/JMP* не являются
     реальными инструкциями и в byte-сравнение не входят).

Запуск: python tests/test_roundtrip_256.py [N]   (N = число циклов, по умолчанию 3)
"""
import sys
import os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from i8080_ci.disassembler import I8080Disassembler
from assemble8080.assembler import assemble

OP = 0x11


def build_program(dis, documented_only):
    prog = bytearray()
    for op in range(256):
        if op not in dis.table:
            continue
        size, fmt = dis.table[op]
        if documented_only and ("NOP*" in fmt or "RET*" in fmt or "CALL*" in fmt or "JMP*" in fmt):
            continue
        prog.append(op)
        for _ in range(size - 1):
            prog.append(OP)
    return bytes(prog)


def run_cycle(cpu_type):
    dis = I8080Disassembler(cpu_type=cpu_type)

    # A) Покрытие: все 256 дизассемблируются в непустой текст
    full = build_program(dis, documented_only=False)
    mem = {i: b for i, b in enumerate(full)}
    lines = dis.disassemble(mem, 0, len(full))
    n_ops = len(lines)
    empty = sum(1 for _, _, asm, _, _ in lines if not asm.strip())
    coverage_ok = (n_ops == 256 and empty == 0)

    # B) Round-trip только documented
    prog = build_program(dis, documented_only=True)
    mem2 = {i: b for i, b in enumerate(prog)}
    lines2 = dis.disassemble(mem2, 0, len(prog))
    src = ["ORG 0"] + [asm for _, _, asm, undoc, _ in lines2] + ["END"]
    res = assemble("\n".join(src), cpu_type=cpu_type)
    rt_ok = res.success and bytes(res.binary) == prog
    return coverage_ok, n_ops, empty, len(prog), rt_ok, list(res.errors)


def main():
    cycles = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    all_ok = True
    for c in range(1, cycles + 1):
        print(f"=== Цикл {c}/{cycles} ===")
        cycle_ok = True
        for cpu in ("i8080", "i8085"):
            cov_ok, n_ops, empty, n_doc, rt_ok, errors = run_cycle(cpu)
            ok = cov_ok and rt_ok
            status = "OK  " if ok else "FAIL"
            print(f"  [{status}] {cpu}: покрытие {n_ops}/256 (пустых {empty}), "
                  f"round-trip {n_doc} documented байт {'совпал' if rt_ok else 'НЕ совпал'}")
            if not ok:
                cycle_ok = False
                for e in errors[:5]:
                    print(f"         {e}")
        print(f"  ИТОГ цикла {c}: {'PASS' if cycle_ok else 'FAIL'}")
        if not cycle_ok:
            all_ok = False
            break
    print("=" * 50)
    print(f"ВСЕ {cycles} ЦИКЛА: {'PASS' if all_ok else 'FAIL'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
