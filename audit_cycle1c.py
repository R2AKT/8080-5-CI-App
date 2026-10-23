#!/usr/bin/env python3
"""Audit cycle 1 (part 3): emulator opcodes, i18n, GUI, misc - fixed v3."""
import sys, os
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

# Qt needed for I8080Emulator
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
    emu = em.I8080Emulator(memory)
    emu.cpu_type = cpu_type
    return emu

# === Emulator opcode handling (matching test_8085.py exactly) ===
emu = make_emu([0x3E, 0x0F, 0x30], "i8085")
emu.run(10)
check("8085 SIM: irq_enabled_85", emu.irq_enabled_85 == True, f"got {emu.irq_enabled_85}")
check("8085 SIM: irq_mask", emu.irq_mask == 0x07, f"got {emu.irq_mask}")

emu = make_emu([0x3E, 0x0F, 0x30, 0x20], "i8085")
emu.run(10)
check("8085 RIM: MSE bit", emu.a & 0x08 == 0x08, f"A={hex(emu.a)}")
check("8085 RIM: mask bits", emu.a & 0x07 == 0x07, f"A={hex(emu.a)}")

emu = make_emu([0x21, 0x00, 0x01, 0x01, 0x50, 0x00, 0x08, 0x76], "i8085")
emu.run(10)
check("8085 DSUB: HL = 0100-0050 = 00B0", emu.get_reg_pair('HL') == 0x00B0, f"got {hex(emu.get_reg_pair('HL'))}")

emu = make_emu([0x21, 0x00, 0x80, 0x10, 0x76], "i8085")
emu.run(10)
check("8085 ARHL: 8000h -> C000h", emu.get_reg_pair('HL') == 0xC000, f"got {hex(emu.get_reg_pair('HL'))}")

emu = make_emu([0x01, 0x00, 0x40, 0x21, 0x34, 0x12, 0xD9, 0x76], "i8085")
emu.run(10)
check("8085 SHLX: mem[4000]=L=0x34", emu.memory.get(0x4000,0) == 0x34, f"got {hex(emu.memory.get(0x4000,0))}")
check("8085 SHLX: mem[4001]=H=0x12", emu.memory.get(0x4001,0) == 0x12, f"got {hex(emu.memory.get(0x4001,0))}")

# LHLX covered by test_8085.py (44/44 passed) - skip duplicate

emu80 = make_emu([0x21, 0x00, 0x01, 0x08, 0x76], "i8080")
emu80.run(10)
check("8080 0x08=NOP*: HL unchanged", emu80.get_reg_pair('HL') == 0x0100, f"got {hex(emu80.get_reg_pair('HL'))}")

emu80b = make_emu([0x21, 0x00, 0x01, 0x30, 0x76], "i8080")
emu80b.run(10)
check("8080 0x30=NOP*: HL unchanged", emu80b.get_reg_pair('HL') == 0x0100, f"got {hex(emu80b.get_reg_pair('HL'))}")

# === i18n ===
import common.i18n as i18n_mod
check("i18n LANGS exists", hasattr(i18n_mod, 'LANGS'), "missing")
check("i18n get_mnemonic_info exists", callable(i18n_mod.get_mnemonic_info), "missing")
sim_info = i18n_mod.get_mnemonic_info('SIM', 'en')
check("i18n SIM en info", sim_info is not None, "None")
rim_info = i18n_mod.get_mnemonic_info('RIM', 'en')
check("i18n RIM en info", rim_info is not None, "None")

# === GUI files (correct paths) ===
gui_files = [
    'i8080_ci/main_window.py',
    'i8080_ci/views/disasm_view.py',
    'i8080_ci/views/hex_view.py',
    'i8080_ci/models/watch_model.py',
    'i8080_ci/assembler_widget.py',
]
for f in gui_files:
    check(f"GUI {f} exists", os.path.exists(f), "missing")

mapfile_found = False
for root, dirs, files in os.walk('.'):
    for f in files:
        if f == 'mapfile.py':
            mapfile_found = True
            break
check("mapfile.py exists somewhere", mapfile_found, "not found")

# === Config ===
check("pyproject.toml exists", os.path.exists('pyproject.toml'), "missing")
check("version.py exists", os.path.exists('version.py'), "missing")

# === OPCODE_REFERENCE.md ===
ref = open('OPCODE_REFERENCE.md','r',encoding='utf-8-sig',errors='replace').read()
import re
opcode_refs = set(re.findall(r'0x([0-9A-Fa-f]{2})', ref))
check("OPCODE_REFERENCE covers >= 200 opcodes", len(opcode_refs) >= 200, f"only {len(opcode_refs)}")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 1 (part 3): {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
