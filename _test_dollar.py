# -*- coding: utf-8 -*-
"""Test: $-labels get relocations in relocatable mode."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assemble8080.assembler import assemble
from assemble8080.objfile import obj_from_asm_result
from assemble8080.linker import link

passed = 0
failed = 0

def check(name, cond, msg=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} — {msg}")

print("=== Test 1: $-labels generate relocations ===")
src = """
$0:
    MVI A, 5
    JZ $1
    JMP $0
    HLT
$1:
    DCR B
    JNZ $1
    RET
"""
r = assemble(src)
check("Assembled OK", r.success, str(r.errors))
check("Has relocations", len(r.relocations) >= 3, f"got {len(r.relocations)}: {r.relocations}")
# JZ $1 at offset 3, JMP $0 at offset 6, JNZ $1 at offset 11
check("JZ $1 reloc", (3, 2, '$1') in r.relocations, str(r.relocations))
check("JMP $0 reloc", (6, 2, '$0') in r.relocations, str(r.relocations))
check("JNZ $1 reloc", (11, 2, '$1') in r.relocations, str(r.relocations))

print("\n=== Test 2: Linker resolves $-labels correctly ===")
obj = obj_from_asm_result(r, "test.asm")
check("Obj has $0 symbol", '$0' in obj.symbols, f"symbols={list(obj.symbols.keys())}")
check("Obj has $1 symbol", '$1' in obj.symbols, f"symbols={list(obj.symbols.keys())}")

# Link at 0x0100
obj.org = 0x0100
res = link([obj], origin=0, size=0x10000, fill=0xFF)
check("Link success", res.success, str(res.errors))
# $0 is at offset 0 → 0x0100
# $1 is at offset 9 → 0x0109
# JZ $1: opcode at 0x0102, address field at 0x0103-0x0104 → should be 0x0109
jz_target = res.binary[0x0103] | (res.binary[0x0104] << 8)
check(f"JZ $1 → 0x0109 (got 0x{jz_target:04X})", jz_target == 0x0109, f"got 0x{jz_target:04X}")
# JMP $0: opcode at 0x0105, address field at 0x0106-0x0107 → should be 0x0100
jmp_target = res.binary[0x0106] | (res.binary[0x0107] << 8)
check(f"JMP $0 → 0x0100 (got 0x{jmp_target:04X})", jmp_target == 0x0100, f"got 0x{jmp_target:04X}")

print("\n=== Test 3: crun8080lib.asm still 366 relocations (was 353 before ALU-imm fix) ===")
crun_path = r"c:\smallc\crun8080lib.asm"
if os.path.exists(crun_path):
    with open(crun_path, 'r', encoding='utf-8', errors='replace') as f:
        crun_src = f.read()
    r_crun = assemble(crun_src, filename=crun_path)
    check(f"crun: {len(r_crun.relocations)} relocations (expect 366)", len(r_crun.relocations) == 366,
          f"got {len(r_crun.relocations)}")

print(f"\n{'='*60}")
print(f"RESULT: {passed} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
