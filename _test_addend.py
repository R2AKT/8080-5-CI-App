"""Test: verify label+addend and $ replacement fixes."""
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'assemble8080'))
sys.stdout.reconfigure(encoding='utf-8')

from assembler import Assembler

passed = 0
failed = 0

def check(desc, cond):
    global passed, failed
    if cond:
        passed += 1
        print(f"  PASS: {desc}")
    else:
        failed += 1
        print(f"  FAIL: {desc}")

# Test 1: lxi h, $1000+#0 → relocation with addend 0
asm = Assembler()
asm._relocatable = True
result = asm.assemble("lxi h,$1000+#0\n")
check("lxi h,$1000+#0: no errors", not result.errors)
check("lxi h,$1000+#0: has relocation", len(asm._relocations) == 1)
if asm._relocations:
    r = asm._relocations[0]
    check(f"  reloc symbol='$1000' (got '{r[2]}')", r[2] == '$1000')
    check(f"  reloc addend=0 (got {r[3]})", r[3] == 0)

# Test 2: lxi h, $1000+#6 → relocation with addend 6
asm = Assembler()
asm._relocatable = True
result = asm.assemble("lxi h,$1000+#6\n")
check("lxi h,$1000+#6: no errors", not result.errors)
check("lxi h,$1000+#6: has relocation", len(asm._relocations) == 1)
if asm._relocations:
    r = asm._relocations[0]
    check(f"  reloc symbol='$1000' (got '{r[2]}')", r[2] == '$1000')
    check(f"  reloc addend=6 (got {r[3]})", r[3] == 6)

# Test 3: lxi h, $1000-#2 → relocation with addend -2
asm = Assembler()
asm._relocatable = True
result = asm.assemble("lxi h,$1000-#2\n")
check("lxi h,$1000-#2: no errors", not result.errors)
if asm._relocations:
    r = asm._relocations[0]
    check(f"  reloc addend=-2 (got {r[3]})", r[3] == -2)

# Test 4: shld hello → relocation with addend 0
asm = Assembler()
asm._relocatable = True
result = asm.assemble("shld hello\n")
check("shld hello: no errors", not result.errors)
check("shld hello: has relocation", len(asm._relocations) == 1)
if asm._relocations:
    r = asm._relocations[0]
    check(f"  reloc symbol='HELLO' (got '{r[2]}')", r[2] == 'HELLO')
    check(f"  reloc addend=0 (got {r[3]})", r[3] == 0)

# Test 5: lxi h, #42 → immediate, no relocation
asm = Assembler()
asm._relocatable = True
result = asm.assemble("lxi h,#42\n")
check("lxi h,#42: no errors", not result.errors)
check("lxi h,#42: no relocation", len(asm._relocations) == 0)
check("lxi h,#42: value=0x002A", result.binary[1:3] == bytes([0x2A, 0x00]))

# Test 6: $ standalone → PC value, no relocation
asm = Assembler()
asm._relocatable = True
result = asm.assemble("lxi h,$\n")
check("lxi h,$: no errors", not result.errors)
check("lxi h,$: no relocation", len(asm._relocations) == 0)

# Test 7: $N local label NOT replaced by PC
asm = Assembler()
asm._relocatable = True
# Define $1000 as a local label first
result = asm.assemble("$1000:\n  lxi h,$1000\n")
check("$1000 label: no errors", not result.errors)
# $1000 should be treated as a label reference, not PC substitution
check("$1000 label: has relocation", len(asm._relocations) == 1)
if asm._relocations:
    r = asm._relocations[0]
    check(f"  reloc symbol='$1000' (got '{r[2]}')", r[2] == '$1000')

# Test 8: _parse_label_addend unit tests
asm = Assembler()
check("_parse_label_addend('hello')", asm._parse_label_addend('hello') == ('HELLO', 0))
check("_parse_label_addend('hello+5')", asm._parse_label_addend('hello+5') == ('HELLO', 5))
check("_parse_label_addend('hello-3')", asm._parse_label_addend('hello-3') == ('HELLO', -3))
check("_parse_label_addend('$1000+#6')", asm._parse_label_addend('$1000+#6') == ('$1000', 6))
check("_parse_label_addend('#42') is None", asm._parse_label_addend('#42') is None)
check("_parse_label_addend('a+b') is None (b not numeric)", asm._parse_label_addend('a+b') is None)

print(f"\n{'='*60}")
print(f"ADDEND TEST: {passed} passed, {failed} failed")
print(f"{'='*60}")
if failed == 0:
    print("ALL TESTS PASSED")
else:
    sys.exit(1)
