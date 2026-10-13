# -*- coding: utf-8 -*-
"""Fix outdated test expectations: case preservation + addend 4-tuples + CMP imm alias."""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def fix(path, pairs):
    s = open(path, encoding='utf-8').read()
    orig = s
    for old, new in pairs:
        if old not in s:
            print(f"  [WARN] not found in {path}: {old[:60]!r}")
            continue
        s = s.replace(old, new)
    if s != orig:
        open(path, 'w', encoding='utf-8', newline='').write(s)
        print(f"  [OK] {path}")
    else:
        print(f"  [NO CHANGE] {path}")

# ===== test_assembler_linker.py =====
print("test_assembler_linker.py:")
fix('tests/test_assembler_linker.py', [
    # Test 1: uppercase labels so map contains uppercase
    ('''ORG 0x0100
start:
    MVI A, 0x42
    CALL sub
    HLT
sub:
    ADD B
    RET
my_data:
    DB 0x11, 0x22, 0x33''',
     '''ORG 0x0100
START:
    MVI A, 0x42
    CALL SUB
    HLT
SUB:
    ADD B
    RET
MY_DATA:
    DB 0x11, 0x22, 0x33'''),
    # Test 2: uppercase export/import/label
    ('''ORG 0x0200
EXPORT main
IMPORT helper
main:
    MVI A, 0x01
    CALL helper
    HLT''',
     '''ORG 0x0200
EXPORT MAIN
IMPORT HELPER
MAIN:
    MVI A, 0x01
    CALL HELPER
    HLT'''),
    # Test 6: addend 4-tuples
    ("expected = [(3, 2, 'HELPER'), (6, 2, 'HELPER'), (9, 2, 'HELPER')]",
     "expected = [(3, 2, 'HELPER', 0), (6, 2, 'HELPER', 0), (9, 2, 'HELPER', 0)]"),
    ("check(\"DW: 1 relocation\", r.relocations == [(0, 2, 'TBL')], str(r.relocations))",
     "check(\"DW: 1 relocation\", r.relocations == [(0, 2, 'TBL', 0)], str(r.relocations))"),
    ("check(\"LXI: 1 relocation\", r.relocations == [(1, 2, 'PTR')], str(r.relocations))",
     "check(\"LXI: 1 relocation\", r.relocations == [(1, 2, 'PTR', 0)], str(r.relocations))"),
])

# ===== test_alus_imm_verify.py =====
print("test_alus_imm_verify.py:")
fix('tests/test_alus_imm_verify.py', [
    ("5. CMP с immediate операндом НЕ принимается (только CPI)",
     "5. CMP с immediate операндом принимается как алиас CPI"),
    ('''def test_assembler_cmp_imm_rejected():
    """CMP с immediate операндом НЕ принимается (используйте CPI)."""
    asm = Assembler()
    r = asm.assemble('    ORG 0100H\\n        CMP 05H\\n        RET')
    # CMP 05H: main table has CMP as (0xB8, 'r', 1), tries to parse 05H as register
    # 05H is not a register, ALU_IMM_OPCODES no longer has 'CMP'
    # Should produce an error
    assert r.errors, f'Expected error for CMP 05H, but got binary: {r.binary.hex() if r.binary else "None"}'
    print(f'  PASS: assembler rejects CMP 05H (error: {r.errors[0]})')''',
     '''def test_assembler_cmp_imm_alias():
    """CMP с immediate операндом принимается как алиас CPI (0xFE)."""
    asm = Assembler()
    r = asm.assemble('    ORG 0100H\\n        CMP 05H\\n        RET')
    # CMP 05H -> CPI 05H (0xFE 05): ALU_IMM_OPCODES maps 'CMP' -> 0xFE
    assert r.binary == bytearray([0xFE, 0x05, 0xC9]), \\
        f'Expected FE 05 C9 (CPI 05H), got {r.binary.hex() if r.binary else "None"}'
    print('  PASS: assembler accepts CMP 05H as CPI 05H (FE 05)')'''),
    ("    test_assembler_cmp_imm_rejected()",
     "    test_assembler_cmp_imm_alias()"),
])
print("DONE")
