"""
Тесты поддержки Intel 8085.

Проверяют:
- Ассемблер: директивы .8080/.8085/.asm8080/.asm8085/CPU
- Ассемблер: cpu_type-aware мнемоники (SIM, RIM, недокументированные)
- Эмулятор: пересекающиеся опкоды 8080/8085
- Дизассемблер: cpu_type-aware таблица опкодов

Запуск: python tests/test_8085.py
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import Assembler
from i8080_ci.disassembler import I8080Disassembler

passed = 0
failed = 0


def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  \u2705 {name}")
        passed += 1
    else:
        print(f"  \u274c {name}: ожидалось {expected}, получено {actual}")
        failed += 1


def asm(source, cpu=None):
    a = Assembler()
    if cpu:
        a.cpu_type = cpu
    return a.assemble(source)


# ============================================================
# ЧАСТЬ 1: АССЕМБЛЕР — директивы типа процессора
# ============================================================
print("=" * 60)
print(" ЧАСТЬ 1: Ассемблер — директивы CPU")
print("=" * 60)

r = asm(".8085\nSIM")
check(".8085: SIM собирается", r.success, True)
check(".8085: SIM = 0x20", bytes(r.binary), bytes([0x20]))

r = asm(".8085\nRIM")
check(".8085: RIM = 0x30", bytes(r.binary), bytes([0x30]))

r = asm(".asm8085\nSIM")
check(".asm8085: SIM = 0x20", bytes(r.binary), bytes([0x20]))

r = asm("SIM")
check("по умолчанию (i8080): SIM неизвестна", r.success, False)

r = asm("RIM")
check("по умолчанию (i8080): RIM неизвестна", r.success, False)

r = asm(".8080\nNOP*")
check(".8080: NOP* = 0x08", bytes(r.binary), bytes([0x08]))

r = asm("CPU 8085\nSIM")
check("CPU 8085: SIM = 0x20", bytes(r.binary), bytes([0x20]))

# ============================================================
# ЧАСТЬ 2: АССЕМБЛЕР — недокументированные 8085
# ============================================================
print()
print("=" * 60)
print(" ЧАСТЬ 2: Ассемблер — недокументированные 8085")
print("=" * 60)

r = asm(".8085\nDSUB")
check("8085: DSUB = 0x08", bytes(r.binary), bytes([0x08]))

r = asm(".8085\nARHL")
check("8085: ARHL = 0x10", bytes(r.binary), bytes([0x10]))

r = asm(".8085\nSHLX")
check("8085: SHLX = 0xD9", bytes(r.binary), bytes([0xD9]))

r = asm(".8085\nLHLX")
check("8085: LHLX = 0xED", bytes(r.binary), bytes([0xED]))

r = asm(".8085\nLDHI 55H")
check("8085: LDHI 55H = 28 55", bytes(r.binary), bytes([0x28, 0x55]))

r = asm(".8085\nJNK 1234H")
check("8085: JNK 1234H = DD 34 12", bytes(r.binary), bytes([0xDD, 0x34, 0x12]))

# 8085: RET* не должна быть доступна
r = asm(".8085\nRET*")
check("8085: RET* неизвестна", r.success, False)

# 8080: DSUB не должна быть доступна
r = asm("DSUB")
check("8080: DSUB неизвестна", r.success, False)

# ============================================================
# ЧАСТЬ 3: АССЕМБЛЕР — недокументированные 8080
# ============================================================
print()
print("=" * 60)
print(" ЧАСТЬ 3: Ассемблер — недокументированные 8080")
print("=" * 60)

r = asm("RET*")
check("8080: RET* = 0xD9", bytes(r.binary), bytes([0xD9]))

r = asm("CALL* 1234H")
check("8080: CALL* 1234H = DD 34 12", bytes(r.binary), bytes([0xDD, 0x34, 0x12]))

r = asm("JMP* 1234H")
check("8080: JMP* 1234H = CB 34 12", bytes(r.binary), bytes([0xCB, 0x34, 0x12]))

# ============================================================
# ЧАСТЬ 4: ЭМУЛЯТОР — пересекающиеся опкоды
# ============================================================
print()
print("=" * 60)
print(" ЧАСТЬ 4: Эмулятор — пересекающиеся опкоды")
print("=" * 60)

from PySide6.QtWidgets import QApplication
app = QApplication.instance() or QApplication(sys.argv)
from i8080_emulator import I8080Emulator


def make_emu(program, cpu_type="i8080", extra_mem=None):
    memory = {}
    for i, b in enumerate(program):
        memory[i] = b
    if extra_mem:
        memory.update(extra_mem)
    emu = I8080Emulator(memory)
    emu.cpu_type = cpu_type
    return emu


# 8085: SIM
emu = make_emu([0x3E, 0x0F, 0x30], "i8085")
emu.run(10)
check("8085: SIM: irq_enabled_85", emu.irq_enabled_85, True)
check("8085: SIM: irq_mask", emu.irq_mask, 0x07)

# 8085: RIM
emu = make_emu([0x3E, 0x0F, 0x30, 0x20], "i8085")
emu.run(10)
check("8085: RIM: MSE bit", emu.a & 0x08, 0x08)
check("8085: RIM: mask bits", emu.a & 0x07, 0x07)

# 8085: DSUB (HL = HL - BC)
emu = make_emu([0x21, 0x00, 0x01, 0x01, 0x50, 0x00, 0x08, 0x76], "i8085")
emu.run(10)
check("8085: DSUB: HL = 0100-0050 = 00B0", emu.get_reg_pair('HL'), 0x00B0)

# 8085: ARHL (arithmetic right shift)
emu = make_emu([0x21, 0x00, 0x80, 0x10, 0x76], "i8085")
emu.run(10)
check("8085: ARHL: 8000h -> C000h", emu.get_reg_pair('HL'), 0xC000)

# 8085: SHLX ((BC) = HL)
emu = make_emu([0x01, 0x00, 0x40, 0x21, 0x34, 0x12, 0xD9, 0x76], "i8085")
emu.run(10)
check("8085: SHLX: mem[4000]=L", emu.read_byte(0x4000), 0x34)
check("8085: SHLX: mem[4001]=H", emu.read_byte(0x4001), 0x12)

# 8085: LHLX (HL = (BC))
emu = make_emu([0x01, 0x00, 0x40, 0x3E, 0x56, 0x32, 0x00, 0x40,
                0x3E, 0x78, 0x32, 0x01, 0x40, 0xED, 0x76], "i8085")
emu.run(20)
check("8085: LHLX: HL = (BC) = 7856h", emu.get_reg_pair('HL'), 0x7856)

# Пересекающийся опкод 0x08: на 8080 NOP, на 8085 DSUB
emu80 = make_emu([0x21, 0x00, 0x01, 0x01, 0x50, 0x00, 0x08, 0x76], "i8080")
emu80.run(10)
check("8080: 0x08 NOP (HL=0100)", emu80.get_reg_pair('HL'), 0x0100)

emu85 = make_emu([0x21, 0x00, 0x01, 0x01, 0x50, 0x00, 0x08, 0x76], "i8085")
emu85.run(10)
check("8085: 0x08 DSUB (HL=00B0)", emu85.get_reg_pair('HL'), 0x00B0)

# 8080: 0xCB = JMP a16 (недокументированный)
emu = make_emu([0x3E, 0x11, 0x3E, 0x22, 0xCB, 0x02, 0x00, 0x76], "i8080")
emu.run(10)
check("8080: 0xCB JMP (A=22h)", emu.a, 0x22)

# 8080: 0xD9 = RET (недокументированный)
emu = make_emu([0x31, 0x00, 0x50, 0x01, 0x00, 0x40, 0xC5, 0xD9, 0x76],
               "i8080", extra_mem={0x4000: 0x76})
emu.run(10)
check("8080: 0xD9 RET (halted)", emu.halted, True)

# 8080: 0xDD = CALL a16 (недокументированный)
emu = make_emu([0x3E, 0x11, 0xDD, 0x08, 0x00, 0x3E, 0x33, 0x76,
                0x3E, 0x22, 0xC9], "i8080")
emu.run(20)
check("8080: 0xDD CALL then RET (A=33h)", emu.a, 0x33)

# ============================================================
# ЧАСТЬ 5: ДИЗАССЕМБЛЕР — cpu_type-aware таблица
# ============================================================
print()
print("=" * 60)
print(" ЧАСТЬ 5: Дизассемблер — cpu_type-aware")
print("=" * 60)

d80 = I8080Disassembler(cpu_type="i8080")
check("8080 disasm: 0x08 = NOP*", d80.table[0x08][1], "NOP*")
check("8080 disasm: 0x20 = NOP*", d80.table[0x20][1], "NOP*")
check("8080 disasm: 0xD9 = RET*", d80.table[0xD9][1], "RET*")

d85 = I8080Disassembler(cpu_type="i8085")
check("8085 disasm: 0x20 = RIM", d85.table[0x20][1], "RIM")
check("8085 disasm: 0x30 = SIM", d85.table[0x30][1], "SIM")
check("8085 disasm: 0x08 = DSUB", d85.table[0x08][1], "DSUB")
check("8085 disasm: 0xD9 = SHLX", d85.table[0xD9][1], "SHLX")
check("8085 disasm: 0xED = LHLX", d85.table[0xED][1], "LHLX")

# set_cpu_type
d = I8080Disassembler(cpu_type="i8080")
d.set_cpu_type("i8085")
check("disasm set_cpu_type: 0x20 = RIM", d.table[0x20][1], "RIM")
d.set_cpu_type("i8080")
check("disasm set_cpu_type back: 0x20 = NOP*", d.table[0x20][1], "NOP*")

# ============================================================
# РЕЗУЛЬТАТ
# ============================================================
print()
print("=" * 60)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 60)
if failed == 0:
    print(" \u2705 ВСЕ ТЕСТЫ 8085 ПРОЙДЕНЫ!")
else:
    print(" \u274c ЕСТЬ ПРОВАЛЫ")
    sys.exit(1)
