#!/usr/bin/env python3
"""Audit cycle 4: deep cross-module opcode consistency check."""
import sys, os, re
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

# === 1. Cross-module opcode consistency ===
from i8080_ci.disassembler import I8080Disassembler
import assemble8080.assembler as asm
from PySide6.QtWidgets import QApplication
import sys as sys_mod
app = QApplication.instance() or QApplication(sys_mod.argv)
import i8080_emulator as em
import common.i18n as i18n_mod

d80 = I8080Disassembler(); d80.set_cpu_type('i8080')
d85 = I8080Disassembler(); d85.set_cpu_type('i8085')

# For each 8085-specific opcode, verify:
# - Disassembler 8085 table has correct mnemonic
# - Assembler 8085 encodes to correct opcode
# - i18n has correct info
# - OPCODE_REFERENCE.md mentions it

opcodes_8085 = {
    'SIM':  0x30,
    'RIM':  0x20,
    'DSUB': 0x08,
    'ARHL': 0x10,
    'SHLX': 0xD9,
    'LHLX': 0xED,
    'RSTV': 0xCB,
}

for mn, op in opcodes_8085.items():
    # Disassembler 8085
    check(f"Disasm85 0x{op:02X}={mn}", mn in d85.table[op][1], f"got {d85.table[op]}")
    # Assembler 8085
    r = asm.assemble(".8085\n" + mn, cpu_type='i8085')
    check(f"Asm85 {mn}=0x{op:02X}", r.success and r.binary[0] == op, f"got {r.binary.hex() if r.binary else 'FAIL'}")
    # i18n EN
    info_en = i18n_mod.get_mnemonic_info(mn, 'en')
    check(f"i18n EN {mn}", info_en is not None and info_en[1] == f'0x{op:02X}', f"got {info_en}")
    # i18n RU
    info_ru = i18n_mod.get_mnemonic_info(mn, 'ru')
    check(f"i18n RU {mn}", info_ru is not None and info_ru[1] == f'0x{op:02X}', f"got {info_ru}")

# === 2. Cross-check 8080 undocumented opcodes ===
opcodes_8080_undoc = {
    'RET*': 0xD9,
    'JMP*': 0xCB,
    'CALL*': 0xDD,
}
for mn, op in opcodes_8080_undoc.items():
    check(f"Disasm80 0x{op:02X} contains {mn[:3]}", mn[:3] in d80.table[op][1] or 'NOP' in d80.table[op][1], f"got {d80.table[op]}")

# === 3. Verify all 256 disassembler entries have valid mnemonics ===
for cpu, table in [('8080', d80.table), ('8085', d85.table)]:
    for i in range(256):
        entry = table[i]
        check(f"{cpu} table[0x{i:02X}] has mnemonic", len(entry) >= 2 and isinstance(entry[1], str) and len(entry[1]) > 0, f"got {entry}")

# === 4. Verify assembler round-trip for all basic instructions ===
roundtrip_tests = [
    ('NOP', 0x00), ('HLT', 0x76), ('RET', 0xC9), ('JMP 0100H', 0xC3),
    ('CALL 0100H', 0xCD), ('MOV A,B', 0x78), ('MOV B,A', 0x47),
    ('MVI A,0x00', 0x3E), ('LXI H,0x0000', 0x21), ('PUSH B', 0xC5),
    ('POP B', 0xC1), ('ADD B', 0x80), ('SUB B', 0x90),
    ('INR A', 0x3C), ('DCR A', 0x3D), ('INX B', 0x03), ('DCX B', 0x0B),
    ('INX H', 0x23), ('DCX H', 0x2B), ('INX SP', 0x33), ('DCX SP', 0x3B),
    ('STAX B', 0x02), ('LDAX B', 0x0A), ('STAX D', 0x12), ('LDAX D', 0x1A),
    ('SHLD 0000H', 0x22), ('LHLD 0000H', 0x2A),
    ('DAD B', 0x09), ('DAD H', 0x29), ('DAD SP', 0x39),
    ('XCHG', 0xEB), ('SPHL', 0xF9), ('PCHL', 0xE9),
    ('IN 00H', 0xDB), ('OUT 00H', 0xD3),
]
for src, first_byte in roundtrip_tests:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm '{src}' first=0x{first_byte:02X}", r.success and r.binary[0] == first_byte,
          f"got {r.binary.hex() if r.binary else 'FAIL'}")

# === 5. STAX H / LDAX H aliases ===
check("Asm STAX H = 0x77", asm.assemble('STAX H', cpu_type='i8080').binary[0] == 0x77)
check("Asm LDAX H = 0x7E", asm.assemble('LDAX H', cpu_type='i8080').binary[0] == 0x7E)
# Disassembler should show canonical MOV, not STAX/LDAX
check("Disasm 0x77 = MOV M,A", 'MOV M,A' in d80.table[0x77][1], f"got {d80.table[0x77]}")
check("Disasm 0x7E = MOV A,M", 'MOV A,M' in d80.table[0x7E][1], f"got {d80.table[0x7E]}")
check("Disasm85 0x77 = MOV M,A", 'MOV M,A' in d85.table[0x77][1], f"got {d85.table[0x77]}")
check("Disasm85 0x7E = MOV A,M", 'MOV A,M' in d85.table[0x7E][1], f"got {d85.table[0x7E]}")

# === 6. OPCODE_REFERENCE.md cross-check ===
ref = open('OPCODE_REFERENCE.md', 'r', encoding='utf-8-sig', errors='replace').read()
for mn, op in opcodes_8085.items():
    check(f"REF {mn}=0x{op:02X}", mn in ref and f'0x{op:02X}' in ref, f"{mn} or 0x{op:02X} not found")

# === 7. Documentation consistency ===
readme = open('README.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("README: 978", '978' in readme, "missing")
check("README: no 964", '964' not in readme, "stale 964")
check("README: OPCODE_REFERENCE", 'OPCODE_REFERENCE' in readme, "missing")

guide = open('ASSEMBLER_GUIDE.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("GUIDE: OPCODE_REFERENCE", 'OPCODE_REFERENCE' in guide, "missing")
check("GUIDE: STAX H", 'STAX H' in guide, "missing")
check("GUIDE: LDAX H", 'LDAX H' in guide, "missing")
check("GUIDE: 0x77", '0x77' in guide, "missing")
check("GUIDE: 0x7E", '0x7E' in guide, "missing")

changes = open('CHANGES.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("CHANGES: 2.1.15", '2.1.15' in changes, "missing")

# === 8. Version consistency ===
import version
check("version: 2.1.15", version.__version__ == '2.1.15', f"got {version.__version__}")
pyproject = open('pyproject.toml', 'r', encoding='utf-8-sig', errors='replace').read()
check("pyproject: 2.1.15", '2.1.15' in pyproject, "missing")

# === 9. Project structure ===
for f in ['i8080_emulator.py', 'i8080_ci/disassembler.py', 'i8080_ci/main_window.py',
          'i8080_ci/assembler_widget.py', 'i8080_ci/views/disasm_view.py',
          'i8080_ci/views/hex_view.py', 'i8080_ci/models/watch_model.py',
          'assemble8080/assembler.py', 'common/i18n.py', 'run_tests.py',
          'build_snapshot.py', 'version.py', 'pyproject.toml',
          'OPCODE_REFERENCE.md', 'ASSEMBLER_GUIDE.md', 'README.md',
          'CHANGES.md', 'PROJECT_SNAPSHOT.md']:
    check(f"File: {f}", os.path.exists(f), "missing")

# === 10. Example files build ===
for ex in ['01_hello', '02_directives', '03_macros', '04_multifile']:
    check(f"Example {ex}/build.py", os.path.exists(f'assembler_example/{ex}/build.py'), "missing")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 4: {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
