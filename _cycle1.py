"""CYCLE 1: Full opcode verification - assembler, emulator, disassembler."""
import sys, os
os.environ['QT_QPA_PLATFORM'] = 'offscreen'
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from assemble8080.assembler import Assembler
from i8080_emulator import I8080Emulator
from i8080_ci.disassembler import I8080Disassembler

passed = 0
failed = 0
errors = []

def check(desc, actual, expected):
    global passed, failed
    if actual == expected:
        passed += 1
    else:
        failed += 1
        errors.append(f"{desc}: got {actual!r}, expected {expected!r}")
        print(f"  FAIL: {desc}: got {actual!r}, expected {expected!r}")

def asm(source, cpu=None):
    a = Assembler()
    if cpu:
        a.cpu_type = cpu
    return a.assemble(source)

def make_emu(program, cpu_type="i8080", extra_mem=None):
    memory = {}
    for i, b in enumerate(program):
        memory[i] = b
    if extra_mem:
        memory.update(extra_mem)
    emu = I8080Emulator(memory)
    emu.cpu_type = cpu_type
    return emu

# ============================================================
print("=" * 70)
print("CYCLE 1: ASSEMBLER OPCODE VERIFICATION")
print("=" * 70)

# Single-byte
tests = [
    ("NOP", [0x00]), ("RLC", [0x07]), ("RRC", [0x0F]),
    ("RAL", [0x17]), ("RAR", [0x1F]), ("DAA", [0x27]),
    ("CMA", [0x2F]), ("STC", [0x37]), ("CMC", [0x3F]),
    ("HLT", [0x76]), ("RET", [0xC9]), ("XTHL", [0xE3]),
    ("PCHL", [0xE9]), ("XCHG", [0xEB]), ("SPHL", [0xF9]),
    ("EI", [0xFB]), ("DI", [0xF3]),
]
for mn, exp in tests:
    r = asm(mn)
    check(f"asm {mn}", bytes(r.binary), bytes(exp))

# MOV
tests_mov = [
    ("MOV B,B",[0x40]),("MOV B,C",[0x41]),("MOV B,A",[0x47]),
    ("MOV C,B",[0x48]),("MOV C,E",[0x4B]),("MOV C,M",[0x4E]),
    ("MOV A,B",[0x78]),("MOV A,A",[0x7F]),
    ("MOV L,B",[0x68]),("MOV H,A",[0x67]),("MOV M,B",[0x70]),
]
for code, exp in tests_mov:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# MVI
tests_mvi = [
    ("MVI B,1",[0x06,0x01]),("MVI C,2",[0x0E,0x02]),
    ("MVI A,255",[0x3E,0xFF]),("MVI H,16",[0x26,0x10]),
    ("MVI L,32",[0x2E,0x20]),("MVI M,66",[0x36,0x42]),
]
for code, exp in tests_mvi:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# INR/DCR
tests_id = [
    ("INR B",[0x04]),("INR C",[0x0C]),("INR A",[0x3C]),
    ("DCR B",[0x05]),("DCR C",[0x0D]),("DCR A",[0x3D]),
    ("INR M",[0x34]),("DCR M",[0x35]),
]
for code, exp in tests_id:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# ALU r
tests_alu = [
    ("ADD B",[0x80]),("ADD A",[0x87]),("ADC B",[0x88]),
    ("SUB B",[0x90]),("SBB B",[0x98]),("ANA B",[0xA0]),
    ("XRA B",[0xA8]),("ORA B",[0xB0]),("CMP B",[0xB8]),("CMP A",[0xBF]),
]
for code, exp in tests_alu:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# ALU immediate (official)
tests_ai = [
    ("ADI 5",[0xC6,0x05]),("ACI 1",[0xCE,0x01]),
    ("SUI 3",[0xD6,0x03]),("SBI 7",[0xDE,0x07]),
    ("ANI 255",[0xE6,0xFF]),("XRI 170",[0xEE,0xAA]),
    ("ORI 85",[0xF6,0x55]),("CPI 16",[0xFE,0x10]),
]
for code, exp in tests_ai:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# ALU immediate (shorthand)
tests_as = [
    ("ADD 5",[0xC6,0x05]),("SUB 3",[0xD6,0x03]),("CMP 16",[0xFE,0x10]),
]
for code, exp in tests_as:
    r = asm(code)
    check(f"asm {code} shorthand", bytes(r.binary), bytes(exp))

# 16-bit
tests_16 = [
    ("LXI B,0x1234",[0x01,0x34,0x12]),("LXI D,0x5678",[0x11,0x78,0x56]),
    ("LXI H,0x9ABC",[0x21,0xBC,0x9A]),("LXI SP,0xFF00",[0x31,0x00,0xFF]),
    ("SHLD 0x2000",[0x22,0x00,0x20]),("LHLD 0x3000",[0x2A,0x00,0x30]),
    ("STA 0x4000",[0x32,0x00,0x40]),("LDA 0x5000",[0x3A,0x00,0x50]),
    ("JMP 0x1000",[0xC3,0x00,0x10]),("CALL 0x2000",[0xCD,0x00,0x20]),
]
for code, exp in tests_16:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# Conditional J
tests_cj = [
    ("JNZ 0x1000",[0xC2,0x00,0x10]),("JZ 0x1000",[0xCA,0x00,0x10]),
    ("JNC 0x1000",[0xD2,0x00,0x10]),("JC 0x1000",[0xDA,0x00,0x10]),
    ("JPO 0x1000",[0xE2,0x00,0x10]),("JPE 0x1000",[0xEA,0x00,0x10]),
    ("JP 0x1000",[0xF2,0x00,0x10]),("JM 0x1000",[0xFA,0x00,0x10]),
]
for code, exp in tests_cj:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# Conditional C
tests_cc = [
    ("CNZ 0x1000",[0xC4,0x00,0x10]),("CZ 0x1000",[0xCC,0x00,0x10]),
    ("CNC 0x1000",[0xD4,0x00,0x10]),("CC 0x1000",[0xDC,0x00,0x10]),
    ("CPO 0x1000",[0xE4,0x00,0x10]),("CPE 0x1000",[0xEC,0x00,0x10]),
    ("CP 0x1000",[0xF4,0x00,0x10]),("CM 0x1000",[0xFC,0x00,0x10]),
]
for code, exp in tests_cc:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# Conditional R
tests_cr = [
    ("RNZ",[0xC0]),("RZ",[0xC8]),("RNC",[0xD0]),("RC",[0xD8]),
    ("RPO",[0xE0]),("RPE",[0xE8]),("RP",[0xF0]),("RM",[0xF8]),
]
for code, exp in tests_cr:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# RST
tests_rst = [
    ("RST 0",[0xC7]),("RST 1",[0xCF]),("RST 2",[0xD7]),("RST 3",[0xDF]),
    ("RST 4",[0xE7]),("RST 5",[0xEF]),("RST 6",[0xF7]),("RST 7",[0xFF]),
]
for code, exp in tests_rst:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# PUSH/POP
tests_pp = [
    ("PUSH B",[0xC5]),("PUSH D",[0xD5]),("PUSH H",[0xE5]),("PUSH PSW",[0xF5]),
    ("POP B",[0xC1]),("POP D",[0xD1]),("POP H",[0xE1]),("POP PSW",[0xF1]),
]
for code, exp in tests_pp:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# RP ops
tests_rp = [
    ("INX B",[0x03]),("INX D",[0x13]),("INX H",[0x23]),("INX SP",[0x33]),
    ("DCX B",[0x0B]),("DCX D",[0x1B]),("DCX H",[0x2B]),("DCX SP",[0x3B]),
    ("DAD B",[0x09]),("DAD D",[0x19]),("DAD H",[0x29]),("DAD SP",[0x39]),
    ("STAX B",[0x02]),("STAX D",[0x12]),("LDAX B",[0x0A]),("LDAX D",[0x1A]),
]
for code, exp in tests_rp:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# IN/OUT
tests_io = [("IN 1",[0xDB,0x01]),("OUT 2",[0xD3,0x02])]
for code, exp in tests_io:
    r = asm(code)
    check(f"asm {code}", bytes(r.binary), bytes(exp))

# 8085
tests_85 = [
    ("SIM",[0x30]),("RIM",[0x20]),("DSUB",[0x08]),("ARHL",[0x10]),
    ("RDEL",[0x18]),("SHLX",[0xD9]),("LHLX",[0xED]),("RSTV",[0xCB]),
]
for code, exp in tests_85:
    r = asm(code, cpu='i8085')
    check(f"asm 8085 {code}", bytes(r.binary), bytes(exp))

tests_85op = [
    ("LDHI 0x34",[0x28,0x34]),("LDSI 0x78",[0x38,0x78]),
    ("JNK 0x1000",[0xDD,0x00,0x10]),("JK 0x2000",[0xFD,0x00,0x20]),
]
for code, exp in tests_85op:
    r = asm(code, cpu='i8085')
    check(f"asm 8085 {code}", bytes(r.binary), bytes(exp))

# 8080 undocumented
tests_80u = [
    ("RET*",[0xD9]),("JMP* 0x1234",[0xCB,0x34,0x12]),
    ("CALL* 0x1234",[0xDD,0x34,0x12]),
]
for code, exp in tests_80u:
    r = asm(code)
    check(f"asm 8080 {code}", bytes(r.binary), bytes(exp))

print(f"  Assembler: {passed} passed, {failed} failed")

# ============================================================
print("\n" + "=" * 70)
print("CYCLE 1: EMULATOR EXECUTION VERIFICATION")
print("=" * 70)

emu_p, emu_f = 0, 0
def emu_check(desc, actual, expected):
    global emu_p, emu_f
    if actual == expected:
        emu_p += 1
    else:
        emu_f += 1
        errors.append(f"EMU {desc}: got {actual!r}, expected {expected!r}")
        print(f"  EMU FAIL: {desc}: got {actual!r}, expected {expected!r}")

# Basic ALU
e = make_emu([0x3E,0x05,0x76]); e.run(10)
emu_check("MVI A,5", e.a, 0x05)

e = make_emu([0x3E,0x03,0x0E,0x04,0x81,0x76]); e.run(10)
emu_check("ADD C (3+4)", e.a, 0x07)

e = make_emu([0x3E,0x05,0xC6,0x03,0x76]); e.run(10)
emu_check("ADI 3 (5+3)", e.a, 0x08)

e = make_emu([0x3E,0x05,0xD6,0x02,0x76]); e.run(10)
emu_check("SUI 2 (5-2)", e.a, 0x03)

e = make_emu([0x3E,0xFF,0xE6,0x0F,0x76]); e.run(10)
emu_check("ANI 0F", e.a, 0x0F)

e = make_emu([0x3E,0xFF,0xEE,0x0F,0x76]); e.run(10)
emu_check("XRI 0F", e.a, 0xF0)

e = make_emu([0x3E,0xF0,0xF6,0x0F,0x76]); e.run(10)
emu_check("ORI 0F", e.a, 0xFF)

# INR/DCR
e = make_emu([0x06,0x00,0x04,0x76]); e.run(10)
emu_check("INR B", e.b, 0x01)

e = make_emu([0x06,0x01,0x05,0x76]); e.run(10)
emu_check("DCR B", e.b, 0x00)

# MOV
e = make_emu([0x06,0x42,0x78,0x76]); e.run(10)
emu_check("MOV A,B", e.a, 0x42)

# RLC/RRC
e = make_emu([0x3E,0x80,0x07,0x76]); e.run(10)
emu_check("RLC 0x80", e.a, 0x01)

e = make_emu([0x3E,0x01,0x0F,0x76]); e.run(10)
emu_check("RRC 0x01", e.a, 0x80)

# RAL/RAR
e = make_emu([0x3E,0x80,0x17,0x76]); e.run(10)
emu_check("RAL 0x80 (C=0)", e.a, 0x00)

e = make_emu([0x3E,0x01,0x1F,0x76]); e.run(10)
emu_check("RAR 0x01 (C=0)", e.a, 0x00)

# CMA
e = make_emu([0x3E,0x0F,0x2F,0x76]); e.run(10)
emu_check("CMA 0x0F", e.a, 0xF0)

# DAA
e = make_emu([0x3E,0x09,0xC6,0x09,0x27,0x76]); e.run(20)
emu_check("DAA (9+9=18)", e.a, 0x18)

# 8085: SIM
e = make_emu([0x3E,0x0F,0x30,0x76], "i8085"); e.run(10)
emu_check("8085 SIM: irq_enabled_85", e.irq_enabled_85, True)

# 8085: RIM
e = make_emu([0x3E,0x0F,0x30,0x20,0x76], "i8085"); e.run(10)
emu_check("8085 RIM: A has mask", e.a & 0x07, 0x07)

# 8085: DSUB
e = make_emu([0x21,0x00,0x01,0x01,0x50,0x00,0x08,0x76], "i8085"); e.run(10)
emu_check("8085 DSUB: HL=0100-0050", e.get_reg_pair('HL'), 0x00B0)

# 8085: ARHL
e = make_emu([0x21,0x00,0x80,0x10,0x76], "i8085"); e.run(10)
emu_check("8085 ARHL: 8000h->C000h", e.get_reg_pair('HL'), 0xC000)

# 8080: 0x08 = NOP
e = make_emu([0x21,0x00,0x01,0x08,0x76], "i8080"); e.run(10)
emu_check("8080: 0x08 NOP (HL=0100)", e.get_reg_pair('HL'), 0x0100)

# 8080: 0xCB = JMP
e = make_emu([0x3E,0x11,0x3E,0x22,0xCB,0x02,0x00,0x76], "i8080"); e.run(10)
emu_check("8080: 0xCB JMP (A=22h)", e.a, 0x22)

# 8080: 0xD9 = RET
e = make_emu([0x31,0x00,0x50,0x01,0x00,0x40,0xC5,0xD9,0x76], "i8080",
             extra_mem={0x4000: 0x76}); e.run(10)
emu_check("8080: 0xD9 RET (halted)", e.halted, True)

print(f"  Emulator: {emu_p} passed, {emu_f} failed")

# ============================================================
print("\n" + "=" * 70)
print("CYCLE 1: DISASSEMBLER VERIFICATION")
print("=" * 70)

dis_p, dis_f = 0, 0
def dis_check(desc, opcode, expected_prefix, cpu='i8080'):
    global dis_p, dis_f
    d = I8080Disassembler(cpu_type=cpu)
    mn = d.get_mnemonic(opcode)
    if mn and mn.startswith(expected_prefix):
        dis_p += 1
    else:
        dis_f += 1
        errors.append(f"DIS {desc}: 0x{opcode:02X} = {mn!r}, expected prefix {expected_prefix!r}")
        print(f"  DIS FAIL: {desc}: 0x{opcode:02X} = {mn!r}, expected prefix {expected_prefix!r}")

# Single-byte
dis_check("NOP", 0x00, "NOP")
dis_check("RLC", 0x07, "RLC")
dis_check("RRC", 0x0F, "RRC")
dis_check("RAL", 0x17, "RAL")
dis_check("RAR", 0x1F, "RAR")
dis_check("DAA", 0x27, "DAA")
dis_check("CMA", 0x2F, "CMA")
dis_check("HLT", 0x76, "HLT")
dis_check("RET", 0xC9, "RET")
dis_check("XTHL", 0xE3, "XTHL")
dis_check("PCHL", 0xE9, "PCHL")
dis_check("XCHG", 0xEB, "XCHG")
dis_check("SPHL", 0xF9, "SPHL")
dis_check("EI", 0xFB, "EI")
dis_check("DI", 0xF3, "DI")

# MOV range
dis_check("MOV B,B", 0x40, "MOV")
dis_check("MOV A,A", 0x7F, "MOV")

# ALU
dis_check("ADD B", 0x80, "ADD")
dis_check("CMP A", 0xBF, "CMP")

# ALU imm
dis_check("ADI", 0xC6, "ADI")
dis_check("CPI", 0xFE, "CPI")

# Conditional
dis_check("RNZ", 0xC0, "RNZ")
dis_check("JNZ", 0xC2, "JNZ")
dis_check("JMP", 0xC3, "JMP")
dis_check("RST 0", 0xC7, "RST")
dis_check("PUSH B", 0xC5, "PUSH")
dis_check("POP B", 0xC1, "POP")

# 8085
dis_check("8085 SIM", 0x30, "SIM", cpu='i8085')
dis_check("8085 RIM", 0x20, "RIM", cpu='i8085')
dis_check("8085 DSUB", 0x08, "DSUB", cpu='i8085')
dis_check("8085 SHLX", 0xD9, "SHLX", cpu='i8085')
dis_check("8085 LHLX", 0xED, "LHLX", cpu='i8085')

# 8080 undocumented
dis_check("8080 RET*", 0xD9, "RET", cpu='i8080')
dis_check("8080 JMP*", 0xCB, "JMP", cpu='i8080')

print(f"  Disassembler: {dis_p} passed, {dis_f} failed")

# ============================================================
total_p = passed + emu_p + dis_p
total_f = failed + emu_f + dis_f
print("\n" + "=" * 70)
print(f"CYCLE 1 RESULT: {total_p} passed, {total_f} failed")
print("=" * 70)
if total_f > 0:
    print("\nERRORS:")
    for e in errors:
        print(f"  {e}")
else:
    print("\nALL TESTS PASSED - CYCLE 1 STABLE")
