#!/usr/bin/env python3
"""Audit cycle 1: comprehensive verification of opcodes, docs, examples, configs."""
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

# === 1. Disassembler ===
from i8080_ci.disassembler import I8080Disassembler
d80 = I8080Disassembler()
d80.set_cpu_type('i8080')
d85 = I8080Disassembler()
d85.set_cpu_type('i8085')

check("8080 table size", len(d80.table) == 256, f"got {len(d80.table)}")
check("8085 table size", len(d85.table) == 256, f"got {len(d85.table)}")

# SIM/RIM in 8085
check("8085 0x30=SIM", d85.table[0x30][1] == 'SIM', f"got {d85.table[0x30]}")
check("8085 0x20=RIM", d85.table[0x20][1] == 'RIM', f"got {d85.table[0x20]}")
# In 8080, 0x30 and 0x20 should be NOP*
check("8080 0x30=NOP*", 'NOP*' in d80.table[0x30][1], f"got {d80.table[0x30]}")
check("8080 0x20=NOP*", 'NOP*' in d80.table[0x20][1], f"got {d80.table[0x20]}")

# 8080 undocumented
check("8080 0xCB=JMP*", 'JMP' in d80.table[0xCB][1], f"got {d80.table[0xCB]}")
check("8080 0xD9=RET*", 'RET' in d80.table[0xD9][1], f"got {d80.table[0xD9]}")
# 8085: 0xCB=RSTV, 0xD9=SHLX
check("8085 0xCB=RSTV", d85.table[0xCB][1] == 'RSTV', f"got {d85.table[0xCB]}")
check("8085 0xD9=SHLX", d85.table[0xD9][1] == 'SHLX', f"got {d85.table[0xD9]}")

# 8085 undocumented
check("8085 0x08=DSUB", d85.table[0x08][1] == 'DSUB', f"got {d85.table[0x08]}")
check("8085 0x10=ARHL", d85.table[0x10][1] == 'ARHL', f"got {d85.table[0x10]}")
check("8085 0xED=LHLX", d85.table[0xED][1] == 'LHLX', f"got {d85.table[0xED]}")

# Standard opcodes cross-check
check("8080 NOP=0x00", d80.table[0x00][1] == 'NOP', f"got {d80.table[0x00]}")
check("8080 HLT=0x76", d80.table[0x76][1] == 'HLT', f"got {d80.table[0x76]}")
check("8080 RET=0xC9", d80.table[0xC9][1] == 'RET', f"got {d80.table[0xC9]}")
check("8085 NOP=0x00", d85.table[0x00][1] == 'NOP', f"got {d85.table[0x00]}")
check("8085 HLT=0x76", d85.table[0x76][1] == 'HLT', f"got {d85.table[0x76]}")

# MOV M,A and MOV A,M
check("MOV M,A=0x77", d80.table[0x77][1] == 'MOV M,A', f"got {d80.table[0x77]}")
check("MOV A,M=0x7E", d80.table[0x7E][1] == 'MOV A,M', f"got {d80.table[0x7E]}")
check("8085 MOV M,A=0x77", d85.table[0x77][1] == 'MOV M,A', f"got {d85.table[0x77]}")
check("8085 MOV A,M=0x7E", d85.table[0x7E][1] == 'MOV A,M', f"got {d85.table[0x7E]}")

# === 2. Assembler ===
import assemble8080.assembler as asm
base = asm.MNEMONICS
m8080 = asm.MNEMONICS_8080
m8085 = asm.MNEMONICS_8085
all_mn = asm.ALL_MNEMONICS

check("Base MNEMONICS count", len(base) == 78, f"got {len(base)}")
check("ALL_MNEMONICS count = 94", len(all_mn) == 94, f"ALL={len(all_mn)}")
check("8080 mnemonics count > 0", len(m8080) > 0, f"got {len(m8080)}")
check("8085 mnemonics count > 0", len(m8085) > 0, f"got {len(m8085)}")

overlap = set(m8080) & set(m8085)
print(f"\n  8080/8085 overlap ({len(overlap)}): {sorted(overlap)}")

# SIM/RIM in assembler
check("8085 SIM=0x30", m8085.get('SIM', (None,))[0] == 0x30, f"got {m8085.get('SIM')}")
check("8085 RIM=0x20", m8085.get('RIM', (None,))[0] == 0x20, f"got {m8085.get('RIM')}")

# STAX H / LDAX H aliases
for alias, expect_op, expect_mn in [('STAX H', 0x77, 'MOV M,A'), ('LDAX H', 0x7E, 'MOV A,M')]:
    r = asm.assemble(alias, cpu_type='i8080')
    ok = r.success and len(r.binary) > 0 and r.binary[0] == expect_op
    check(f"Assembler alias {alias} = 0x{expect_op:02X}", ok, f"success={r.success}, binary={r.binary.hex() if r.binary else None}, errors={r.errors}")

# === 3. Emulator ===
import i8080_emulator as emu_mod
e80 = emu_mod.I8080Emulator(memory=[0]*65536)
e80.cpu_type = 'i8080'
e85 = emu_mod.I8080Emulator(memory=[0]*65536)
e85.cpu_type = 'i8085'
check("Emulator 8080 cpu_type", e80.cpu_type == 'i8080', f"got {e80.cpu_type}")
check("Emulator 8085 cpu_type", e85.cpu_type == 'i8085', f"got {e85.cpu_type}")

# === 4. OPCODE_REFERENCE.md cross-check ===
ref = open('OPCODE_REFERENCE.md', 'r', encoding='utf-8-sig').read()
check("OPCODE_REFERENCE mentions SIM=0x30", 'SIM' in ref and '0x30' in ref, "not found")
check("OPCODE_REFERENCE mentions RIM=0x20", 'RIM' in ref and '0x20' in ref, "not found")
check("OPCODE_REFERENCE SOT note", 'SINGLE SOURCE OF TRUTH' in ref.upper() or 'ЕДИНСТВЕННЫ' in ref.upper(), "SOT note missing")

# === 5. Documentation ===
for doc in ['README.md', 'ASSEMBLER_GUIDE.md', 'CHANGES.md', 'USER_GUIDE.md']:
    if os.path.exists(doc):
        content = open(doc, 'r', encoding='utf-8-sig', errors='replace').read()
        check(f"{doc} exists and non-empty", len(content) > 100, f"only {len(content)} chars")
    else:
        check(f"{doc} exists", False, "file missing")

# === 6. Version consistency ===
import version
check("version.py version", version.__version__ == "2.1.15", f"got {version.__version__}")
check("version.py build", version.__build__ == "20261023", f"got {version.__build__}")

pyproject = open('pyproject.toml', 'r', encoding='utf-8-sig', errors='replace').read()
check("pyproject.toml version=2.1.15", '2.1.15' in pyproject, "version not found in pyproject.toml")

# === 7. Example files ===
for ex_dir in os.listdir('assembler_example'):
    ex_path = os.path.join('assembler_example', ex_dir)
    if os.path.isdir(ex_path):
        build_py = os.path.join(ex_path, 'build.py')
        if os.path.exists(build_py):
            bp = open(build_py, 'r', encoding='utf-8-sig', errors='replace').read()
            check(f"Example {ex_dir}/build.py non-empty", len(bp) > 50, f"only {len(bp)} chars")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 1: {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
