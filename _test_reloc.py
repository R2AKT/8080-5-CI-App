# -*- coding: utf-8 -*-
"""Test: internal relocations in relocatable mode."""
import sys, os
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assemble8080.assembler import assemble, Assembler
from assemble8080.objfile import obj_from_asm_result, save_obj, load_obj
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

print("=== Test 1: Relocatable mode (no .org) generates relocations for local labels ===")
src = """
START:
    MVI A, 5
    CALL SUBR
    JMP LOOP
    HLT
LOOP:
    DCR B
    JNZ LOOP
    RET
SUBR:
    INR A
    RET
"""
r = assemble(src)
check("Assembled OK", r.success, str(r.errors))
check("Relocatable mode", r.origin == 0, f"origin={r.origin:#x}")
check("Has relocations", len(r.relocations) > 0, f"got {len(r.relocations)}")
# Expected: CALL SUBR (offset 3), JMP LOOP (offset 6), JNZ LOOP (offset 12)
print(f"  Relocations: {r.relocations}")
check("CALL SUBR reloc", (3, 2, 'SUBR') in r.relocations, str(r.relocations))
check("JMP LOOP reloc", (6, 2, 'LOOP') in r.relocations, str(r.relocations))
check("JNZ LOOP reloc", (11, 2, 'LOOP') in r.relocations, str(r.relocations))
check("3 relocations total", len(r.relocations) == 3, f"got {len(r.relocations)}: {r.relocations}")

print("\n=== Test 2: Absolute mode (.org) does NOT generate relocations for local labels ===")
src_abs = """
ORG 0x100
START:
    MVI A, 5
    CALL SUBR
    JMP LOOP
    HLT
LOOP:
    DCR B
    JNZ LOOP
    RET
SUBR:
    INR A
    RET
"""
r = assemble(src_abs)
check("Assembled OK", r.success, str(r.errors))
check("Origin = 0x100", r.origin == 0x100, f"origin={r.origin:#x}")
check("No relocations (absolute mode)", len(r.relocations) == 0, f"got {r.relocations}")

print("\n=== Test 3: Linker applies internal relocations correctly ===")
# Module at org=0, link at 0x1000
src_mod = """
START:
    MVI A, 5
    CALL SUBR
    HLT
SUBR:
    INR A
    RET
"""
r = assemble(src_mod)
check("Module assembled", r.success, str(r.errors))
check("Module has relocations", len(r.relocations) == 1, f"got {r.relocations}")

obj = obj_from_asm_result(r, "test.asm")
check("Obj org=0", obj.org == 0, f"org={obj.org:#x}")
check("Obj has relocations", len(obj.relocations) == 1, f"got {obj.relocations}")

# Link at 0x1000: modify obj.org to simulate linker placing at 0x1000
obj.org = 0x1000
res = link([obj], origin=0, size=0x10000, fill=0xFF)
check("Link success", res.success, str(res.errors))
# CALL at offset 3 in module → absolute 0x1003
# SUBR is at offset 6 in module → absolute 0x1006
# Expected: CD 06 10 at address 0x1003
call_bytes = res.binary[0x1003:0x1005]
check("CALL patched to 0x1006", call_bytes == bytes([0x06, 0x10]), f"got {call_bytes.hex()}")
# MVI A, 5 at 0x1000
check("MVI A at 0x1000", res.binary[0x1000] == 0x3E, f"got {res.binary[0x1000]:#x}")
check("A=5 at 0x1001", res.binary[0x1001] == 0x05, f"got {res.binary[0x1001]:#x}")
# SUBR code at 0x1006: INR A (0x3C), RET (0xC9)
check("INR A at 0x1006", res.binary[0x1006] == 0x3C, f"got {res.binary[0x1006]:#x}")
check("RET at 0x1007", res.binary[0x1007] == 0xC9, f"got {res.binary[0x1007]:#x}")

print("\n=== Test 4: Link at 0x0000 (no shift) ===")
obj2 = obj_from_asm_result(r, "test.asm")
res2 = link([obj2], origin=0, size=0x10000, fill=0xFF)
check("Link at 0 success", res2.success, str(res2.errors))
# CALL at offset 3 → SUBR at offset 6 → CD 06 00
call_bytes2 = res2.binary[3:5]
check("CALL patched to 0x0006", call_bytes2 == bytes([0x06, 0x00]), f"got {call_bytes2.hex()}")

print("\n=== Test 5: crun8080lib.asm → >100 relocations ===")
crun_path = r"c:\smallc\crun8080lib.asm"
if os.path.exists(crun_path):
    with open(crun_path, 'r', encoding='utf-8', errors='replace') as f:
        crun_src = f.read()
    r_crun = assemble(crun_src, filename=crun_path)
    if r_crun.success:
        check("crun assembled", True)
        check(f">100 relocations (got {len(r_crun.relocations)})", len(r_crun.relocations) > 100,
              f"got {len(r_crun.relocations)}")
    else:
        # Expected: mul/div errors (known runtime bug)
        print(f"  (crun has errors: {len(r_crun.errors)} — expected mul/div issue)")
        print(f"  First errors: {[str(e) for e in r_crun.errors[:3]]}")
        # Still check relocations generated before error
        check(f"crun relocations > 100 (got {len(r_crun.relocations)})", len(r_crun.relocations) > 100,
              f"got {len(r_crun.relocations)}")
else:
    print(f"  SKIP: {crun_path} not found")

print("\n=== Test 6: DW with local label in relocatable mode ===")
src_dw = """
    DW TBL, 5
TBL:
    DB 1, 2, 3
"""
r = assemble(src_dw)
check("DW assembled", r.success, str(r.errors))
check("DW has 1 relocation", r.relocations == [(0, 2, 'TBL')], f"got {r.relocations}")

print("\n=== Test 7: LXI with local label in relocatable mode ===")
src_lxi = """
    LXI H, PTR
    HLT
PTR:
    DW 0x1234
"""
r = assemble(src_lxi)
check("LXI assembled", r.success, str(r.errors))
check("LXI has 1 relocation", r.relocations == [(1, 2, 'PTR')], f"got {r.relocations}")

print("\n=== Test 8: Numeric literal does NOT generate relocation ===")
src_num = """
    JMP 0x1234
    HLT
"""
r = assemble(src_num)
check("Numeric JMP assembled", r.success, str(r.errors))
check("No relocation for numeric", len(r.relocations) == 0, f"got {r.relocations}")

print(f"\n{'='*60}")
print(f"RESULT: {passed} passed, {failed} failed")
print(f"{'='*60}")
sys.exit(0 if failed == 0 else 1)
