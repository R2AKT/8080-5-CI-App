"""Test: cross-module case-mismatch linking (PROMPT_i8080_ci_case_fix.md)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from assemble8080.assembler import assemble
from assemble8080.objfile import obj_from_asm_result, save_obj, load_obj
from assemble8080.linker import link

passed = 0
failed = 0

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name} {detail}")

print("=" * 60)
print("TEST: Cross-module case-mismatch linking")
print("=" * 60)

# Minimal repro from the prompt:
# Module A (defines main, calls helper)
# Module B (defines helper)
src_a = """main:
    call helper
    ret
"""
src_b = """helper:
    mvi a,0
    ret
"""

# Test 1: case-insensitive (default) - cross-module link works
r_a = assemble(src_a, filename="A.asm")
r_b = assemble(src_b, filename="B.asm")
check("A assembled", r_a.success)
check("B assembled", r_b.success)

obj_a = obj_from_asm_result(r_a, "A.asm")
obj_b = obj_from_asm_result(r_b, "B.asm")
obj_a.org = 0x0100
obj_b.org = 0x0200

# Verify the inconsistency described in the prompt
check("A: symbols in original case", 'main' in obj_a.symbols,
      f"(symbols={obj_a.symbols})")
check("A: imports in UPPER", 'HELPER' in obj_a.imports,
      f"(imports={obj_a.imports})")
check("B: symbols in original case", 'helper' in obj_b.symbols,
      f"(symbols={obj_b.symbols})")

res = link([obj_a, obj_b], origin=0, size=0x10000, fill=0xFF)
check("Link A+B: success", res.success,
      f"(errors={res.errors})")
if res.success:
    # call helper at 0x0100: opcode 0xCD, address at 0x0101 (low) - 0x0102 (high)
    # helper is at 0x0200, so address should be 0x00, 0x02
    addr_lo = res.binary[0x0101]
    addr_hi = res.binary[0x0102]
    check("call helper patched to 0x0200", addr_lo == 0x00 and addr_hi == 0x02,
          f"(got 0x{addr_hi:02X}{addr_lo:02X})")

# Test 2: case-insensitive - reference with different case than definition
src_a2 = """main:
    call HELPER
    ret
"""
r_a2 = assemble(src_a2, filename="A2.asm")
obj_a2 = obj_from_asm_result(r_a2, "A2.asm")
obj_a2.org = 0x0100
res2 = link([obj_a2, obj_b], origin=0, size=0x10000, fill=0xFF)
check("Link A2(HELPER)+B(helper): success (case-insensitive)", res2.success,
      f"(errors={res2.errors})")

# Test 3: case-sensitive - i and I are different
src_c1 = """i:
    mvi a,0
    ret
"""
src_c2 = """main:
    call I
    ret
"""
r_c1 = assemble(src_c1, filename="C1.asm", case_sensitive=True)
r_c2 = assemble(src_c2, filename="C2.asm", case_sensitive=True)
obj_c1 = obj_from_asm_result(r_c1, "C1.asm")
obj_c2 = obj_from_asm_result(r_c2, "C2.asm")
obj_c1.org = 0x0100
obj_c2.org = 0x0200
check("C1: case_sensitive flag in obj", obj_c1.case_sensitive == True)
check("C2: case_sensitive flag in obj", obj_c2.case_sensitive == True)
res3 = link([obj_c1, obj_c2], origin=0, size=0x10000, fill=0xFF)
check("Link C1(i)+C2(I): FAIL (case-sensitive, different case)", not res3.success,
      f"(success={res3.success})")

# Test 4: case-sensitive - same case matches
src_c3 = """main:
    call i
    ret
"""
r_c3 = assemble(src_c3, filename="C3.asm", case_sensitive=True)
obj_c3 = obj_from_asm_result(r_c3, "C3.asm")
obj_c3.org = 0x0200
res4 = link([obj_c1, obj_c3], origin=0, size=0x10000, fill=0xFF)
check("Link C1(i)+C3(i): success (case-sensitive, same case)", res4.success,
      f"(errors={res4.errors})")

# Test 5: save/load roundtrip preserves case_sensitive flag
import tempfile, os
tmp = tempfile.mktemp(suffix='.obj')
save_obj(tmp, obj_c1)
loaded = load_obj(tmp)
check("save/load: case_sensitive preserved", loaded.case_sensitive == True)
os.unlink(tmp)

# Test 6: old .obj (no case_sensitive field) loads with default False
import json
tmp2 = tempfile.mktemp(suffix='.obj')
d = {
    "format": "i8080-obj-v1",
    "name": "old",
    "source": "old.asm",
    "org": 0,
    "size": 2,
    "data": "0000",
    "symbols": {"X": 0},
    "exports": ["X"],
    "imports": [],
    "relocations": [],
}
with open(tmp2, 'w') as f:
    json.dump(d, f)
loaded2 = load_obj(tmp2)
check("old .obj: case_sensitive defaults to False", loaded2.case_sensitive == False)
os.unlink(tmp2)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
