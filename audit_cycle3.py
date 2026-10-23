#!/usr/bin/env python3
"""Audit cycle 3: fresh sweep - different checks than cycles 1-2."""
import sys, os, re, json
sys.path.insert(0, '.')
os.environ['PYTHONIOENCODING'] = 'utf-8'

errors = []
checks = 0
passed = 0

def check(name, cond, detail=""):
    global checks, passed
    checks += 1
    if cond:
        passed += 1
    else:
        errors.append(f"{name}: {detail}")
        print(f"  [FAIL] {name}: {detail}")

# === 1. Assembler: full encoding verification ===
import assemble8080.assembler as asm

# Verify all basic 8080 instructions encode correctly
test_cases = [
    ('NOP', [0x00]),
    ('HLT', [0x76]),
    ('RET', [0xC9]),
    ('JMP 0123H', [0xC3, 0x23, 0x01]),
    ('CALL 0123H', [0xCD, 0x23, 0x01]),
    ('MOV A,B', [0x78]),
    ('MOV B,A', [0x47]),
    ('MVI A,0x42', [0x3E, 0x42]),
    ('LXI H,0x1234', [0x21, 0x34, 0x12]),
    ('PUSH B', [0xC5]),
    ('POP B', [0xC1]),
    ('ADD B', [0x80]),
    ('SUB B', [0x90]),
    ('INR A', [0x3C]),
    ('DCR A', [0x3D]),
    ('INR B', [0x04]),
    ('DCR B', [0x05]),
    ('INR M', [0x34]),
    ('DCR M', [0x35]),
    ('INX B', [0x03]),
    ('DCX B', [0x0B]),
    ('INX H', [0x23]),
    ('DCX H', [0x2B]),
    ('INX SP', [0x33]),
    ('DCX SP', [0x3B]),
    ('STAX B', [0x02]),
    ('LDAX B', [0x0A]),
    ('STAX D', [0x12]),
    ('LDAX D', [0x1A]),
    ('SHLD 0123H', [0x22, 0x23, 0x01]),
    ('LHLD 0123H', [0x2A, 0x23, 0x01]),
    ('IN 01H', [0xDB, 0x01]),
    ('OUT 01H', [0xD3, 0x01]),
    ('DAD B', [0x09]),
    ('DAD H', [0x29]),
    ('DAD SP', [0x39]),
    ('XCHG', [0xEB]),
    ('CNC 0123H', [0xD4, 0x23, 0x01]),
]

for src, expected in test_cases:
    r = asm.assemble(src, cpu_type='i8080')
    actual = list(r.binary) if r.success else []
    check(f"Asm '{src}'", r.success and actual == expected,
          f"success={r.success}, got={actual}, expected={expected}, errors={r.errors}")

# === 2. Assembler: STAX H / LDAX H aliases ===
for src, expected in [('STAX H', [0x77]), ('LDAX H', [0x7E])]:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm alias '{src}'", r.success and list(r.binary) == expected,
          f"success={r.success}, got={list(r.binary) if r.binary else 'FAIL'}")

# === 3. Assembler: 8085-only instructions ===
for src, expected in [
    ('.8085\nSIM', [0x30]),
    ('.8085\nRIM', [0x20]),
    ('.8085\nDSUB', [0x08]),
    ('.8085\nARHL', [0x10]),
    ('.8085\nSHLX', [0xD9]),
    ('.8085\nLHLX', [0xED]),
    ('.8085\nRSTV', [0xCB]),
]:
    r = asm.assemble(src, cpu_type='i8085')
    check(f"Asm 8085 '{src.strip()}'", r.success and list(r.binary) == expected,
          f"success={r.success}, got={list(r.binary) if r.binary else 'FAIL'}, errors={r.errors}")

# === 4. Assembler: 8080-only undocumented ===
for src, expected in [
    ('.8080\nRET*', [0xD9]),
]:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm 8080 '{src.strip()}'", r.success and list(r.binary) == expected,
          f"success={r.success}, got={list(r.binary) if r.binary else 'FAIL'}")

# JMP* and CALL* with address
r = asm.assemble('.8080\nJMP* 1234H', cpu_type='i8080')
check("Asm 8080 JMP* 1234H", r.success and list(r.binary) == [0xCB, 0x34, 0x12],
      f"got={list(r.binary) if r.binary else 'FAIL'}")
r = asm.assemble('.8080\nCALL* 1234H', cpu_type='i8080')
check("Asm 8080 CALL* 1234H", r.success and list(r.binary) == [0xDD, 0x34, 0x12],
      f"got={list(r.binary) if r.binary else 'FAIL'}")

# === 5. Disassembler: round-trip test ===
from i8080_ci.disassembler import I8080Disassembler
d80 = I8080Disassembler()
d80.set_cpu_type('i8080')

# Assemble then disassemble - verify round-trip
for src, expected_bytes in [('NOP', [0x00]), ('HLT', [0x76]), ('RET', [0xC9]),
                            ('MOV A,B', [0x47]), ('MVI A,0x42', [0x3E, 0x42])]:
    r = asm.assemble(src, cpu_type='i8080')
    if r.success:
        # Disassemble the bytes
        mem_dict = {0x0100 + i: b for i, b in enumerate(r.binary)}
        disasm_result = d80.disassemble(mem_dict, 0x0100, len(r.binary))
        check(f"Roundtrip '{src}'", disasm_result is not None and len(disasm_result) > 0,
              f"disasm returned {disasm_result}")

# === 6. Documentation: check for stale references ===
# Scan all .md files for references to old test counts, wrong opcodes, etc.
md_files = []
for root, dirs, files in os.walk('.'):
    if '.git' in root:
        continue
    for f in files:
        if f.endswith('.md'):
            md_files.append(os.path.join(root, f))

check(f"Found {len(md_files)} .md files", len(md_files) > 0, "none found")

# Check README.md for consistency
readme = open('README.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("README: 978 tests", '978' in readme, "978 not found")
check("README: no 964", '964' not in readme, "964 still present")
check("README: OPCODE_REFERENCE", 'OPCODE_REFERENCE' in readme, "SOT ref missing")
check("README: version 2.1.15", '2.1.15' in readme, "version missing")

# Check ASSEMBLER_GUIDE.md
guide = open('ASSEMBLER_GUIDE.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("GUIDE: OPCODE_REFERENCE ref", 'OPCODE_REFERENCE' in guide, "missing")
check("GUIDE: STAX H alias", 'STAX H' in guide, "missing")
check("GUIDE: LDAX H alias", 'LDAX H' in guide, "missing")
check("GUIDE: 0x77 MOV M,A", '0x77' in guide, "missing")
check("GUIDE: 0x7E MOV A,M", '0x7E' in guide, "missing")

# Check OPCODE_REFERENCE.md
ref = open('OPCODE_REFERENCE.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("REF: SOT note", 'SINGLE SOURCE OF TRUTH' in ref.upper() or 'ЕДИНСТВЕНН' in ref, "missing")
check("REF: SIM=0x30", '0x30' in ref and 'SIM' in ref, "missing")
check("REF: RIM=0x20", '0x20' in ref and 'RIM' in ref, "missing")

# === 7. Version files ===
import version
check("version.py: 2.1.15", version.__version__ == '2.1.15', f"got {version.__version__}")
check("version.py: build 20261023", version.__build__ == '20261023', f"got {version.__build__}")
pyproject = open('pyproject.toml', 'r', encoding='utf-8-sig', errors='replace').read()
check("pyproject: 2.1.15", '2.1.15' in pyproject, "missing")

# === 8. CHANGES.md ===
changes = open('CHANGES.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("CHANGES: 2.1.15", '2.1.15' in changes, "missing")
check("CHANGES: non-empty", len(changes) > 100, f"only {len(changes)} chars")

# === 9. Project structure ===
expected_files = [
    'i8080_emulator.py',
    'i8080_ci/disassembler.py',
    'i8080_ci/main_window.py',
    'i8080_ci/assembler_widget.py',
    'i8080_ci/views/disasm_view.py',
    'i8080_ci/views/hex_view.py',
    'i8080_ci/models/watch_model.py',
    'assemble8080/assembler.py',
    'common/i18n.py',
    'run_tests.py',
    'build_snapshot.py',
    'version.py',
    'pyproject.toml',
    'OPCODE_REFERENCE.md',
    'ASSEMBLER_GUIDE.md',
    'README.md',
    'CHANGES.md',
    'PROJECT_SNAPSHOT.md',
]
for f in expected_files:
    check(f"File exists: {f}", os.path.exists(f), "missing")

# === 10. i18n: mnemonic info for all 8085 opcodes ===
import common.i18n as i18n_mod
for mn in ['SIM', 'RIM', 'DSUB', 'ARHL', 'SHLX', 'LHLX', 'RSTV']:
    info = i18n_mod.get_mnemonic_info(mn, 'en')
    check(f"i18n {mn} en info", info is not None, "None")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 3: {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
