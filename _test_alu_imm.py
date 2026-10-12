"""Test: ALU immediate form size in pass 1 (bug #1 fix)."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from assemble8080.assembler import assemble

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
print("TEST: ALU immediate form size in pass 1 (bug #1)")
print("=" * 60)

# Test 1: ALU-imm shifts subsequent label by correct amount
# MVI A,5 (2) + ADD 3 (2, imm) + HLT (1) = 5 bytes total
# LABEL after should be at offset 5
src1 = """
    MVI A, 5
    ADD 3
    HLT
LABEL:
    NOP
"""
r1 = assemble(src1)
check("ALU-imm: assembled OK", r1.success)
# LABEL should be at offset 5 (2+2+1)
check("ALU-imm: LABEL at offset 5", r1.symbols.get('LABEL') == 5,
      f"(got {r1.symbols.get('LABEL')})")

# Test 2: ALU-reg form is 1 byte
# MVI A,5 (2) + ADD B (1, reg) + HLT (1) = 4 bytes total
src2 = """
    MVI A, 5
    ADD B
    HLT
LABEL:
    NOP
"""
r2 = assemble(src2)
check("ALU-reg: assembled OK", r2.success)
check("ALU-reg: LABEL at offset 4", r2.symbols.get('LABEL') == 4,
      f"(got {r2.symbols.get('LABEL')})")

# Test 3: Multiple ALU-imm accumulate correctly
# MVI A,5 (2) + ADD 1 (2) + SUB 2 (2) + CMP 3 (2) + HLT (1) = 9 bytes
src3 = """
    MVI A, 5
    ADD 1
    SUB 2
    CMP 3
    HLT
LABEL:
    NOP
"""
r3 = assemble(src3)
check("Multi ALU-imm: assembled OK", r3.success)
check("Multi ALU-imm: LABEL at offset 9", r3.symbols.get('LABEL') == 9,
      f"(got {r3.symbols.get('LABEL')})")

# Test 4: ASxxxx 2-operand form "cmp a, #5" is 2 bytes
src4 = """
    MVI A, 5
    cmp a, #5
    HLT
LABEL:
    NOP
"""
r4 = assemble(src4)
check("ASxxxx cmp a,#5: assembled OK", r4.success)
# MVI A,5 (2) + CPI 5 (2) + HLT (1) = 5 bytes
check("ASxxxx cmp a,#5: LABEL at offset 5", r4.symbols.get('LABEL') == 5,
      f"(got {r4.symbols.get('LABEL')})")

# Test 5: # prefix immediate is 2 bytes
src5 = """
    MVI A, 5
    ADD #3
    HLT
LABEL:
    NOP
"""
r5 = assemble(src5)
check("# prefix: assembled OK", r5.success)
check("# prefix: LABEL at offset 5", r5.symbols.get('LABEL') == 5,
      f"(got {r5.symbols.get('LABEL')})")

# Test 6: M (memory) operand is 1 byte (register form)
src6 = """
    MVI A, 5
    ADD M
    HLT
LABEL:
    NOP
"""
r6 = assemble(src6)
check("ADD M: assembled OK", r6.success)
check("ADD M: LABEL at offset 4", r6.symbols.get('LABEL') == 4,
      f"(got {r6.symbols.get('LABEL')})")

# Test 7: Verify binary encoding matches (pass 2 correct)
# ADD 3 should be 0xC6 0x03
src7 = "ADD 3"
r7 = assemble(src7)
check("ADD 3 binary: 0xC6 0x03", r7.success and bytes(r7.binary) == b'\xC6\x03',
      f"(got {bytes(r7.binary).hex()})")

# Test 8: ADD B should be 0x80 (1 byte) — B is register code 0
src8 = "ADD B"
r8 = assemble(src8)
check("ADD B binary: 0x80", r8.success and bytes(r8.binary) == b'\x80',
      f"(got {bytes(r8.binary).hex()})")

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
