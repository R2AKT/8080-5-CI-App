# -*- coding: utf-8 -*-
"""
Интеграционный тест: Ассемблер -> Эмулятор.
Проверяет полный конвейер: ассемблирование исходного кода,
загрузка бинарного кода в эмулятор, выполнение, проверка результатов.

Покрыто: передача данных (MOV/LDA/STA/LHLD/SHLD), стек (PUSH/POP),
управление (JMP/JZ/JNZ/CALL/RET), инкремент/декремент (INR/DCR/INX/DEX).
"""
import os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from assemble8080.assembler import assemble
from i8080_emulator import I8080Emulator

passed = failed = 0

def assemble_and_run(source, pre_mem=None):
    """Ассемблирует source, загружает в эмулятор, выполняет до HLT."""
    res = assemble(source)
    if res.errors:
        return None, res
    mem = dict(pre_mem or {})
    for i, b in enumerate(res.binary):
        mem[res.origin + i] = b
    emu = I8080Emulator(mem)
    emu.set_pc(res.origin)
    n = 0
    while not emu.halted and n < 200:
        emu.step()
        n += 1
    return emu, res

def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  ✅ {name}")
    else:
        failed += 1
        print(f"  ❌ {name} {detail}")

# =============================================
# 1. Передача данных: MOV
# =============================================
print("\n[1] MOV r,r'")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI B, 0x12
    MVI C, 0x34
    MOV A, B
    MOV D, A
    HLT
""")
check("MOV A,B: A=0x12", emu and emu.a == 0x12, f"A=0x{emu.a:02X}" if emu else "err")
check("MOV D,A: D=0x12", emu and emu.d == 0x12, f"D=0x{emu.d:02X}" if emu else "err")

# =============================================
# 2. LDA / STA
# =============================================
print("\n[2] LDA / STA")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x55
    STA 0200H
    LDA 0200H
    HLT
""")
check("STA+LDA: A=0x55", emu and emu.a == 0x55, f"A=0x{emu.a:02X}" if emu else "err")
check("STA: mem[0200]=0x55", emu and emu.memory.get(0x0200) == 0x55)

# =============================================
# 3. LHLD / SHLD
# =============================================
print("\n[3] LHLD / SHLD")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI L, 0x67
    MVI H, 0x12
    SHLD 0300H
    LHLD 0300H
    HLT
""")
check("SHLD+LHLD: HL=0x1267", emu and emu.get_reg_pair('HL') == 0x1267,
      f"HL=0x{emu.get_reg_pair('HL'):04X}" if emu else "err")
check("SHLD: mem[0300]=0x67", emu and emu.memory.get(0x0300) == 0x67)
check("SHLD: mem[0301]=0x12", emu and emu.memory.get(0x0301) == 0x12)

# =============================================
# 4. INR / DCR
# =============================================
print("\n[4] INR / DCR")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI B, 0x09
    INR B
    MVI C, 0x00
    DCR C
    HLT
""")
check("INR B: 09->0A", emu and emu.b == 0x0A, f"B=0x{emu.b:02X}" if emu else "err")
check("DCR C: 00->FF", emu and emu.c == 0xFF, f"C=0x{emu.c:02X}" if emu else "err")

# INR A ставит флаги
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0xFF
    INR A
    HLT
""")
check("INR A: FF->00, Z=1", emu and emu.a == 0x00 and emu.flag_z, 
      f"A=0x{emu.a:02X} Z={emu.flag_z}" if emu else "err")

# =============================================
# 5. INX / DEX
# =============================================
print("\n[5] INX / DEX")
emu, res = assemble_and_run("""
    ORG 0100H
    LXI B, 0x00FF
    INX B
    HLT
""")
check("INX B: 00FF->0100", emu and emu.get_reg_pair('BC') == 0x0100,
      f"BC=0x{emu.get_reg_pair('BC'):04X}" if emu else "err")

emu, res = assemble_and_run("""
    ORG 0100H
    LXI B, 0x0000
    DCX B
    HLT
""")
check("DCX B: 0000->FFFF", emu and emu.get_reg_pair('BC') == 0xFFFF,
      f"BC=0x{emu.get_reg_pair('BC'):04X}" if emu else "err")

# =============================================
# 6. PUSH / POP
# =============================================
print("\n[6] PUSH / POP")
emu, res = assemble_and_run("""
    ORG 0100H
    LXI B, 0x1234
    PUSH B
    LXI B, 0x5678
    POP B
    HLT
""")
check("PUSH+POP: BC=0x1234", emu and emu.get_reg_pair('BC') == 0x1234,
      f"BC=0x{emu.get_reg_pair('BC'):04X}" if emu else "err")

# PUSH PSW / POP PSW
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0xAB
    PUSH PSW
    MVI A, 0x00
    POP PSW
    HLT
""")
check("PUSH PSW+POP PSW: A=0xAB", emu and emu.a == 0xAB, f"A=0x{emu.a:02X}" if emu else "err")

# =============================================
# 7. JMP
# =============================================
print("\n[7] JMP")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x11
    JMP SKIP
    MVI A, 0x22
SKIP:
    MVI A, 0x33
    HLT
""")
check("JMP: A=0x33 (пропустил 0x22)", emu and emu.a == 0x33, f"A=0x{emu.a:02X}" if emu else "err")

# =============================================
# 8. JZ / JNZ
# =============================================
print("\n[8] JZ / JNZ")
# A=0 -> JZ срабатывает
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x00
    JZ TAKEN
    MVI A, 0x11
TAKEN:
    MVI A, 0x22
    HLT
""")
check("JZ (A=0): A=0x22", emu and emu.a == 0x22, f"A=0x{emu.a:02X}" if emu else "err")

# A!=0 -> JZ не срабатывает (JMP отделяет пути, без fall-through)
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x05
    JZ SKIP
    MVI A, 0x11
    JMP END
SKIP:
    MVI A, 0x22
END:
    HLT
""")
check("JZ (A=5): A=0x11 (не прыгнул)", emu and emu.a == 0x11, f"A=0x{emu.a:02X}" if emu else "err")

# JNZ: A!=0 -> срабатывает
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x05
    JNZ TAKEN
    MVI A, 0x11
TAKEN:
    MVI A, 0x22
    HLT
""")
check("JNZ (A=5): A=0x22", emu and emu.a == 0x22, f"A=0x{emu.a:02X}" if emu else "err")

# =============================================
# 9. CALL / RET
# =============================================
print("\n[9] CALL / RET")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI A, 0x00
    CALL SUB
    MVI A, 0x99
    HLT
SUB:
    MVI A, 0x42
    RET
""")
check("CALL+RET: A=0x99", emu and emu.a == 0x99, f"A=0x{emu.a:02X}" if emu else "err")

# =============================================
# 10. Цикл со счётчиком
# =============================================
print("\n[10] Цикл")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI B, 0x05
    MVI A, 0x00
LOOP:
    INR A
    DCR B
    JNZ LOOP
    HLT
""")
check("Цикл 5 раз: A=0x05", emu and emu.a == 0x05, f"A=0x{emu.a:02X}" if emu else "err")

# =============================================
# 11. Сложение в цикле (сумма 1..5 = 15)
# =============================================
print("\n[11] Сумма в цикле")
emu, res = assemble_and_run("""
    ORG 0100H
    MVI B, 0x05
    MVI A, 0x00
    MVI C, 0x01
LOOP:
    ADD C
    INR C
    DCR B
    JNZ LOOP
    HLT
""")
check("Сумма 1..5: A=0x0F", emu and emu.a == 0x0F, f"A=0x{emu.a:02X}" if emu else "err")

print(f"\n{'='*50}")
print(f"РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print(f"{'='*50}")
sys.exit(1 if failed else 0)
