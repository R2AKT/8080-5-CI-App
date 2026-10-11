"""Test: undefined symbols in LXI and DW generate relocations (v2.1.11 fix)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from assemble8080.assembler import assemble
from assemble8080.objfile import obj_from_asm_result
from assemble8080.linker import link

passed = 0
failed = 0

def check(name, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {name}")
    else:
        failed += 1
        print(f"  FAIL: {name}")

print("=" * 60)
print("TEST: Undefined symbols in LXI and DW (v2.1.11)")
print("=" * 60)

# Test 1: LXI with undefined symbol → import + relocation
src1 = """
    MVI A, 5
    LXI H, UNDEFINED_SYM
    HLT
"""
r1 = assemble(src1)
check("LXI undefined: assembled OK", r1.success)
check("LXI undefined: has relocations", len(r1.relocations) == 1)
check("LXI undefined: relocation symbol", r1.relocations[0][2] == 'UNDEFINED_SYM')
check("LXI undefined: symbol in imports", 'UNDEFINED_SYM' in r1.imports)

# Test 2: DW with undefined symbol → import + relocation
src2 = """
    MVI A, 5
    DW UNDEFINED_SYM
    HLT
"""
r2 = assemble(src2)
check("DW undefined: assembled OK", r2.success)
check("DW undefined: has relocations", len(r2.relocations) == 1)
check("DW undefined: relocation symbol", r2.relocations[0][2] == 'UNDEFINED_SYM')
check("DW undefined: symbol in imports", 'UNDEFINED_SYM' in r2.imports)

# Test 3: LXI with $-label undefined → import + relocation
src3 = """
    MVI A, 5
    LXI H, $99
    HLT
"""
r3 = assemble(src3)
check("LXI $99 undefined: assembled OK", r3.success)
check("LXI $99 undefined: has relocations", len(r3.relocations) == 1)
check("LXI $99 undefined: relocation symbol", r3.relocations[0][2] == '$99')
check("LXI $99 undefined: symbol in imports", '$99' in r3.imports)

# Test 4: DW with $-label undefined → import + relocation
src4 = """
    MVI A, 5
    DW $99
    HLT
"""
r4 = assemble(src4)
check("DW $99 undefined: assembled OK", r4.success)
check("DW $99 undefined: has relocations", len(r4.relocations) == 1)
check("DW $99 undefined: relocation symbol", r4.relocations[0][2] == '$99')
check("DW $99 undefined: symbol in imports", '$99' in r4.imports)

# Test 5: Linker resolves undefined LXI symbol from global_symbols
src5 = """
    MVI A, 5
    LXI H, EXTERNAL
    HLT
"""
r5 = assemble(src5)
obj5 = obj_from_asm_result(r5, "test5.asm")
obj5.org = 0x0100

# Create a second object that defines EXTERNAL
src5b = """
EXTERNAL:
    NOP
    RET
"""
r5b = assemble(src5b)
obj5b = obj_from_asm_result(r5b, "test5b.asm")
obj5b.org = 0x0200
obj5b.exports = {'EXTERNAL'}

res5 = link([obj5, obj5b], origin=0, size=0x10000, fill=0xFF)
check("Link LXI external: success", res5.success)
# LXI H at 0x0102: opcode 0x21, then address at 0x0103-0x0104
# EXTERNAL is at 0x0200, so address should be 0x00, 0x02
addr_lo = res5.binary[0x0103]
addr_hi = res5.binary[0x0104]
check("Link LXI external: address = 0x0200", addr_lo == 0x00 and addr_hi == 0x02)

# Test 6: Linker resolves undefined DW symbol from global_symbols
src6 = """
    MVI A, 5
    DW EXTERNAL
    HLT
"""
r6 = assemble(src6)
obj6 = obj_from_asm_result(r6, "test6.asm")
obj6.org = 0x0100

res6 = link([obj6, obj5b], origin=0, size=0x10000, fill=0xFF)
check("Link DW external: success", res6.success)
# DW at 0x0102: address at 0x0102-0x0103
# EXTERNAL is at 0x0200, so address should be 0x00, 0x02
addr_lo = res6.binary[0x0102]
addr_hi = res6.binary[0x0103]
check("Link DW external: address = 0x0200", addr_lo == 0x00 and addr_hi == 0x02)

# Test 7: Absolute mode - undefined symbol in LXI → relocation (linker resolves)
src7 = """
ORG 0x100
    MVI A, 5
    LXI H, UNDEFINED_SYM
    HLT
"""
r7 = assemble(src7)
check("LXI undefined absolute: assembled OK", r7.success)
check("LXI undefined absolute: has relocation (linker resolves)", len(r7.relocations) == 1)

# Test 8: Absolute mode - undefined symbol in DW → relocation (linker resolves)
src8 = """
ORG 0x100
    MVI A, 5
    DW UNDEFINED_SYM
    HLT
"""
r8 = assemble(src8)
check("DW undefined absolute: assembled OK", r8.success)
check("DW undefined absolute: has relocation (linker resolves)", len(r8.relocations) == 1)

# Test 9: Absolute mode - defined local symbol in LXI → no relocation
src9 = """
ORG 0x100
    MVI A, 5
    LXI H, LOCAL
    HLT
LOCAL:
    NOP
"""
r9 = assemble(src9)
check("LXI local absolute: assembled OK", r9.success)
check("LXI local absolute: no relocations", len(r9.relocations) == 0)

# Test 10: Absolute mode - defined local symbol in DW → no relocation
src10 = """
ORG 0x100
    MVI A, 5
    DW LOCAL
    HLT
LOCAL:
    NOP
"""
r10 = assemble(src10)
check("DW local absolute: assembled OK", r10.success)
check("DW local absolute: no relocations", len(r10.relocations) == 0)

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
