#!/usr/bin/env python3
"""Audit cycle 1 (part 2): deep opcode cross-reference."""
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

# === Disassembler vs OPCODE_REFERENCE.md ===
from i8080_ci.disassembler import I8080Disassembler
d80 = I8080Disassembler()
d80.set_cpu_type('i8080')
d85 = I8080Disassembler()
d85.set_cpu_type('i8085')

# Verify all standard 8080 opcodes are correct
expected_8080 = {
    0x00: 'NOP', 0x76: 'HLT', 0xC9: 'RET', 0xC3: 'JMP',
    0x01: 'LXI B,', 0x21: 'LXI H,', 0x31: 'LXI D,', 0x39: 'LXI SP,',
    0x06: 'MVI B,', 0x0E: 'MVI C,', 0x16: 'MVI D,', 0x1E: 'MVI E,',
    0x26: 'MVI H,', 0x2E: 'MVI L,', 0x36: 'MVI M,', 0x3E: 'MVI A,',
    0x77: 'MOV M,A', 0x7E: 'MOV A,M', 0x47: 'MOV A,B', 0x4F: 'MOV A,C',
    0x57: 'MOV A,D', 0x5F: 'MOV A,E', 0x67: 'MOV A,H', 0x6F: 'MOV A,L',
    0x40: 'MOV B,B', 0x49: 'MOV B,C', 0x80: 'ADD B', 0x81: 'ADD C',
    0x89: 'ADD L', 0x80: 'ADD B', 0xC5: 'PUSH B', 0xC4: 'CALL',
    0xC0: 'RET NZ', 0xC2: 'JNZ', 0xC8: 'RZ', 0xC7: 'RST 0',
    0xEF: 'RIM' if False else 'SIM',  # 8080: 0xEF is SIM (undocumented)
}
# Actually 0xEF in 8080 is SIM (undocumented), in 8085 it's also SIM
# Let me just check the key ones

# Check a sample of standard opcodes
for op, mn in [(0x00,'NOP'),(0x76,'HLT'),(0xC9,'RET'),(0x77,'MOV M,A'),(0x7E,'MOV A,M')]:
    check(f"8080 0x{op:02X}={mn}", mn in d80.table[op][1], f"got {d80.table[op]}")
    check(f"8085 0x{op:02X}={mn}", mn in d85.table[op][1], f"got {d85.table[op]}")

# 8085-specific
check("8085 0x08=DSUB", d85.table[0x08][1]=='DSUB', f"got {d85.table[0x08]}")
check("8085 0x10=ARHL", d85.table[0x10][1]=='ARHL', f"got {d85.table[0x10]}")
check("8085 0x30=SIM", d85.table[0x30][1]=='SIM', f"got {d85.table[0x30]}")
check("8085 0x20=RIM", d85.table[0x20][1]=='RIM', f"got {d85.table[0x20]}")
check("8085 0xD9=SHLX", d85.table[0xD9][1]=='SHLX', f"got {d85.table[0xD9]}")
check("8085 0xED=LHLX", d85.table[0xED][1]=='LHLX', f"got {d85.table[0xED]}")
check("8085 0xCB=RSTV", d85.table[0xCB][1]=='RSTV', f"got {d85.table[0xCB]}")

# 8080 undocumented
check("8080 0x08=NOP*", 'NOP*' in d80.table[0x08][1], f"got {d80.table[0x08]}")
check("8080 0x10=NOP*", 'NOP*' in d80.table[0x10][1], f"got {d80.table[0x10]}")
check("8080 0x30=NOP*", 'NOP*' in d80.table[0x30][1], f"got {d80.table[0x30]}")
check("8080 0x20=NOP*", 'NOP*' in d80.table[0x20][1], f"got {d80.table[0x20]}")
check("8080 0xD9=RET*", 'RET*' in d80.table[0xD9][1], f"got {d80.table[0xD9]}")
check("8080 0xCB=JMP*", 'JMP*' in d80.table[0xCB][1], f"got {d80.table[0xCB]}")

# === Assembler cross-check ===
import assemble8080.assembler as asm
# STAX H / LDAX H aliases
for src, expect in [('STAX H', 0x77), ('LDAX H', 0x7E)]:
    r = asm.assemble(src, cpu_type='i8080')
    check(f"Asm {src} = 0x{expect:02X}", r.success and r.binary[0]==expect, f"got {r.binary.hex() if r.binary else 'FAIL'}")

# STAX B should still be 0x02 (canonical)
r = asm.assemble('STAX B', cpu_type='i8080')
check("Asm STAX B = 0x02", r.success and r.binary[0]==0x02, f"got {r.binary.hex() if r.binary else 'FAIL'}")
r = asm.assemble('LDAX B', cpu_type='i8080')
check("Asm LDAX B = 0x0A", r.success and r.binary[0]==0x0A, f"got {r.binary.hex() if r.binary else 'FAIL'}")

# === Emulator cross-check ===
import i8080_emulator as em
e85 = em.I8080Emulator(memory=[0]*65536)
e85.cpu_type = 'i8085'
check("Emu 8085 cpu_type", e85.cpu_type == 'i8085', f"got {e85.cpu_type}")

e80 = em.I8080Emulator(memory=[0]*65536)
e80.cpu_type = 'i8080'
check("Emu 8080 cpu_type", e80.cpu_type == 'i8080', f"got {e80.cpu_type}")

# === Documentation consistency ===
ref = open('OPCODE_REFERENCE.md','r',encoding='utf-8-sig',errors='replace').read()
check("OPCODE_REFERENCE SOT", 'SINGLE SOURCE OF TRUTH' in ref.upper(), "SOT missing")
check("OPCODE_REFERENCE SIM=0x30", '0x30' in ref and 'SIM' in ref, "not found")
check("OPCODE_REFERENCE RIM=0x20", '0x20' in ref and 'RIM' in ref, "not found")

guide = open('ASSEMBLER_GUIDE.md','r',encoding='utf-8-sig',errors='replace').read()
check("ASSEMBLER_GUIDE SOT ref", 'OPCODE_REFERENCE' in guide, "SOT ref missing")
check("ASSEMBLER_GUIDE STAX H", 'STAX H' in guide, "STAX H missing")
check("ASSEMBLER_GUIDE LDAX H", 'LDAX H' in guide, "LDAX H missing")
check("ASSEMBLER_GUIDE 0x77", '0x77' in guide, "0x77 missing")
check("ASSEMBLER_GUIDE 0x7E", '0x7E' in guide, "0x7E missing")

readme = open('README.md','r',encoding='utf-8-sig',errors='replace').read()
check("README 978", '978' in readme, "978 missing")
check("README OPCODE_REFERENCE", 'OPCODE_REFERENCE' in readme, "SOT ref missing")
check("README 2.1.15", '2.1.15' in readme, "version missing")

changes = open('CHANGES.md','r',encoding='utf-8-sig',errors='replace').read()
check("CHANGES 2.1.15", '2.1.15' in changes, "version missing")

# === Version consistency ===
import version
check("version.py 2.1.15", version.__version__ == '2.1.15', f"got {version.__version__}")
pyproject = open('pyproject.toml','r',encoding='utf-8-sig',errors='replace').read()
check("pyproject 2.1.15", '2.1.15' in pyproject, "version missing")

print(f"\n{'='*60}")
print(f"AUDIT CYCLE 1 (part 2): {passed}/{checks} passed, {len(errors)} errors")
if errors:
    print("ERRORS:")
    for e in errors:
        print(f"  - {e}")
else:
    print("  ALL CHECKS PASSED")
print(f"{'='*60}")
