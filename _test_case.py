"""Test: label case preservation + case sensitivity (v2.1.12)."""
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
print("TEST: Label case preservation + case sensitivity")
print("=" * 60)

# Test 1: Default (case-insensitive) - original case preserved in output
src1 = """
main:
    MVI A, 5
    CALL helper
    HLT
helper:
    RET
"""
r1 = assemble(src1)
check("Default: assembled OK", r1.success)
check("Default: 'main' in symbols (original case)", 'main' in r1.symbols,
      f"(symbols={list(r1.symbols.keys())})")
check("Default: 'helper' in symbols (original case)", 'helper' in r1.symbols,
      f"(symbols={list(r1.symbols.keys())})")
check("Default: 'MAIN' NOT in symbols (not uppercased)", 'MAIN' not in r1.symbols)

# Test 2: Default - case-insensitive matching (i and I match)
src2 = """
myLabel:
    MVI A, 5
    JMP mylabel
    HLT
"""
r2 = assemble(src2)
check("Case-insensitive: assembled OK", r2.success)
check("Case-insensitive: 'myLabel' in symbols", 'myLabel' in r2.symbols,
      f"(symbols={list(r2.symbols.keys())})")

# Test 3: Case-sensitive - i and I are different
src3 = """
myLabel:
    MVI A, 5
    HLT
"""
r3a = assemble(src3, case_sensitive=True)
check("Case-sensitive: assembled OK", r3a.success)
check("Case-sensitive: 'myLabel' in symbols", 'myLabel' in r3a.symbols,
      f"(symbols={list(r3a.symbols.keys())})")

# Test 4: Case-sensitive - reference with different case is unresolved
src4 = """
myLabel:
    MVI A, 5
    JMP MYLABEL
    HLT
"""
r4 = assemble(src4, case_sensitive=True)
# In case-sensitive mode, MYLABEL != myLabel, so it should be a warning (undefined)
check("Case-sensitive: different case -> warning", 
      any('MYLABEL' in w or 'mylabel' in w.lower() for w in r4.warnings) or not r4.success,
      f"(warnings={r4.warnings}, success={r4.success})")

# Test 5: Case-sensitive - same case matches
src5 = """
myLabel:
    MVI A, 5
    JMP myLabel
    HLT
"""
r5 = assemble(src5, case_sensitive=True)
check("Case-sensitive: same case matches (no warning)", 
      not any('myLabel' in w or 'MYLABEL' in w for w in r5.warnings),
      f"(warnings={r5.warnings})")

# Test 6: Single-letter labels (the bug #2 scenario)
src6 = """
main:
    lxi h, #1
    shld i
    ret
i:
    .dw 0
"""
r6 = assemble(src6)
check("Single-letter: assembled OK", r6.success)
check("Single-letter: 'i' in symbols (original case)", 'i' in r6.symbols,
      f"(symbols={list(r6.symbols.keys())})")
check("Single-letter: 'I' NOT in symbols", 'I' not in r6.symbols)

# Test 7: Single-letter label 'a' not confused with register A
src7 = """
main:
    MVI A, 5
    HLT
a:
    .dw 0
"""
r7 = assemble(src7)
check("Label 'a': assembled OK", r7.success)
check("Label 'a': 'a' in symbols", 'a' in r7.symbols,
      f"(symbols={list(r7.symbols.keys())})")

print()
print("=" * 60)
print(f"RESULTS: {passed} passed, {failed} failed")
print("=" * 60)

if failed == 0:
    print("ALL TESTS PASSED")
else:
    print("SOME TESTS FAILED")
    sys.exit(1)
