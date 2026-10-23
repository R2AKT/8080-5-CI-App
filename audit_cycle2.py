#!/usr/bin/env python3
"""Audit cycle 2: comprehensive sweep of all project areas."""
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

# === 1. Disassembler full table audit ===
from i8080_ci.disassembler import I8080Disassembler
d80 = I8080Disassembler()
d80.set_cpu_type('i8080')
d85 = I8080Disassembler()
d85.set_cpu_type('i8085')

# Verify all 256 opcodes have entries in both tables
for i in range(256):
    check(f"8080 table[0x{i:02X}] exists", i in d80.table, f"missing")
    check(f"8085 table[0x{i:02X}] exists", i in d85.table, f"missing")

# Spot-check critical opcodes
critical_8080 = {
    0x00: 'NOP', 0x76: 'HLT', 0xC9: 'RET', 0xC3: 'JMP',
    0x77: 'MOV M,A', 0x7E: 'MOV A,M', 0x06: 'MVI B,',
    0x01: 'LXI B,', 0x21: 'LXI H,', 0xC5: 'PUSH B',
    0xCD: 'CALL', 0xC0: 'RNZ', 0xC2: 'JNZ',
    0xC7: 'RST 0', 0xFF: 'RST 7', 0xEF: 'RST 5',
}
for op, mn in critical_8080.items():
    check(f"8080 0x{op:02X} contains '{mn}'", mn in d80.table[op][1], f"got {d80.table[op]}")

critical_8085 = {
    0x30: 'SIM', 0x20: 'RIM', 0x08: 'DSUB', 0x10: 'ARHL',
    0xD9: 'SHLX', 0xED: 'LHLX', 0xCB: 'RSTV',
    0x00: 'NOP', 0x76: 'HLT', 0xC9: 'RET',
}
for op, mn in critical_8085.items():
    check(f"8085 0x{op:02X} contains '{mn}'", mn in d85.table[op][1], f"got {d85.table[op]}")

# === 2. Assembler opcode encoding ===
import assemble8080.assembler as asm

# Verify STAX H / LDAX H aliases
for src, expect_op in [('STAX H', 0x77), ('LDAX H', 0x7E)]:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm {src} = 0x{expect_op:02X}", r.success and r.binary[0] == expect_op,
          f"success={r.success}, binary={r.binary.hex() if r.binary else 'FAIL'}")

# Verify canonical STAX/LDAX unchanged
for src, expect_op in [('STAX B', 0x02), ('STAX D', 0x12), ('LDAX B', 0x0A), ('LDAX D', 0x1A)]:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm {src} = 0x{expect_op:02X}", r.success and r.binary[0] == expect_op,
          f"success={r.success}, binary={r.binary.hex() if r.binary else 'FAIL'}")

# Verify 8085-only mnemonics
for mn, expect_op in [('SIM', 0x30), ('RIM', 0x20), ('DSUB', 0x08), ('ARHL', 0x10)]:
    r = asm.assemble(f".8085\n{mn}", cpu_type='i8085')
    check(f"Asm 8085 {mn} = 0x{expect_op:02X}", r.success and r.binary[0] == expect_op,
          f"success={r.success}, binary={r.binary.hex() if r.binary else 'FAIL'}")

# Verify 8080-only mnemonics
for mn, expect_op in [('RET*', 0xD9), ('JMP*', None), ('CALL*', None)]:
    r = asm.assemble(f".8080\n{mn} 1234H" if mn != 'RET*' else f".8080\n{mn}", cpu_type='i8080')
    if mn == 'RET*':
        check(f"Asm 8080 {mn} = 0x{expect_op:02X}", r.success and r.binary[0] == expect_op,
              f"success={r.success}, binary={r.binary.hex() if r.binary else 'FAIL'}")
    else:
        check(f"Asm 8080 {mn} succeeds", r.success, f"success={r.success}, errors={r.errors}")

# === 3. Emulator behavior ===
from PySide6.QtWidgets import QApplication
import sys as sys_mod
app = QApplication.instance() or QApplication(sys_mod.argv)
import i8080_emulator as em

def make_emu(program, cpu_type="i8080", extra_mem=None):
    memory = {}
    for i, b in enumerate(program):
        memory[i] = b
    if extra_mem:
        memory.update(extra_mem)
    return em.I8080Emulator(memory, cpu_type=cpu_type) if False else (lambda e: (setattr(e,'cpu_type',cpu_type), e)[1])(em.I8080Emulator(memory))

# 8085 SIM
emu = make_emu([0x3E, 0x0F, 0x30], "i8085")
emu.run(10)
check("Emu 8085 SIM: irq_enabled_85", emu.irq_enabled_85, f"got {emu.irq_enabled_85}")
check("Emu 8085 SIM: irq_mask=0x07", emu.irq_mask == 0x07, f"got {emu.irq_mask}")

# 8085 RIM (after SIM)
emu = make_emu([0x3E, 0x0F, 0x30, 0x20], "i8085")
emu.run(10)
check("Emu 8085 RIM: MSE bit", emu.a & 0x08, f"A={hex(emu.a)}")
check("Emu 8085 RIM: mask bits", emu.a & 0x07 == 0x07, f"A={hex(emu.a)}")

# 8085 DSUB
emu = make_emu([0x21, 0x00, 0x01, 0x01, 0x50, 0x00, 0x08, 0x76], "i8085")
emu.run(10)
check("Emu 8085 DSUB: HL=00B0", emu.get_reg_pair('HL') == 0x00B0, f"got {hex(emu.get_reg_pair('HL'))}")

# 8085 ARHL
emu = make_emu([0x21, 0x00, 0x80, 0x10, 0x76], "i8085")
emu.run(10)
check("Emu 8085 ARHL: HL=C000", emu.get_reg_pair('HL') == 0xC000, f"got {hex(emu.get_reg_pair('HL'))}")

# 8080 NOP* at 0x08, 0x30
emu80 = make_emu([0x21, 0x00, 0x01, 0x08, 0x76], "i8080")
emu80.run(10)
check("Emu 8080 0x08=NOP*: HL unchanged", emu80.get_reg_pair('HL') == 0x0100, f"got {hex(emu80.get_reg_pair('HL'))}")

emu80b = make_emu([0x21, 0x00, 0x01, 0x30, 0x76], "i8080")
emu80b.run(10)
check("Emu 8080 0x30=NOP*: HL unchanged", emu80b.get_reg_pair('HL') == 0x0100, f"got {hex(emu80b.get_reg_pair('HL'))}")

# === 4. Documentation consistency ===
ref = open('OPCODE_REFERENCE.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("OPCODE_REFERENCE SOT", 'SINGLE SOURCE OF TRUTH' in ref.upper(), "missing")
check("OPCODE_REFERENCE SIM=0x30", '0x30' in ref and 'SIM' in ref, "missing")
check("OPCODE_REFERENCE RIM=0x20", '0x20' in ref and 'RIM' in ref, "missing")
check("OPCODE_REFERENCE DSUB=0x08", '0x08' in ref and 'DSUB' in ref, "missing")
check("OPCODE_REFERENCE ARHL=0x10", '0x10' in ref and 'ARHL' in ref, "missing")

guide = open('ASSEMBLER_GUIDE.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("ASSEMBLER_GUIDE SOT ref", 'OPCODE_REFERENCE' in guide, "missing")
check("ASSEMBLER_GUIDE STAX H", 'STAX H' in guide, "missing")
check("ASSEMBLER_GUIDE LDAX H", 'LDAX H' in guide, "missing")
check("ASSEMBLER_GUIDE 0x77", '0x77' in guide, "missing")
check("ASSEMBLER_GUIDE 0x7E", '0x7E' in guide, "missing")

readme = open('README.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("README 978", '978' in readme, "missing")
check("README OPCODE_REFERENCE", 'OPCODE_REFERENCE' in readme, "missing")
check("README 2.1.15", '2.1.15' in readme, "missing")

changes = open('CHANGES.md', 'r', encoding='utf-8-sig', errors='replace').read()
check("CHANGES 2.1.15", '2.1.15' in changes, "missing")

# === 5. Version consistency ===
import version
check("version.py 2.1.15", version.__version__ == '2.1.15', f"got {version.__version__}")
pyproject = open('pyproject.toml', 'r', encoding='utf-8-sig', errors='replace').read()
check("pyproject 2.1.15", '2.1.15' in pyproject, "missing")

# === 6. Example files ===
for ex in ['01_hello', '02_directives', '03_macros', '04_multifile']:
    bp = os.path.join('assembler_example', ex, 'build.py')
    check(f"Example {ex}/build.py exists", os.path.exists(bp), "missing")

# === 7. GUI files ===
for f in ['i8080_ci/main_window.py', 'i8080_ci/views/disasm_view.py',
          'i8080_ci/views/hex_view.py', 'i8080_ci/models/watch_model.py',
          'i8080_ci/assembler_widget.py', 'i8080_ci/disassembler.py']:
    check(f"GUI {f} exists", os.path.exists(f), "missing")

# === 8. i18n ===
import common.i18n as i18n_mod
check("i18n LANGS", hasattr(i18n_mod, 'LANGS'), "missing")
check("i18n get_mnemonic_info", callable(i18n_mod.get_mnemonic_info), "missing")
check("i18n SIM en", i18n_mod.get_mnemonic_info('SIM', 'en') is not None, "None")
check("i18n RIM en", i18n_mod.get_mnemonic_info('RIM', 'en') is not None, "None")

# === 9. OPCODE_REFERENCE.md completeness ===
opcode_refs = set(re.findall(r'0x([0-9A-Fa-f]{2})', ref))
check("OPCODE_REFERENCE >= 200 opcodes", len(opcode_refs) >= 200, f"only {len(opcode_refs)}")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 2: {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
