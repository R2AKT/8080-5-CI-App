"""Тест опкодов 0x20 и 0x30 на 8080 и 8085"""
import sys
sys.path.insert(0, '.')
from i8080_emulator import I8080Emulator

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ? {name}")
        passed += 1
    else:
        print(f"  ? {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# === Тест 1: 8080 — опкод 0x20 как NOP ===
print("\nТест 1: 8080 — опкод 0x20 как NOP")
print("-" * 50)
mem = {0x0000: 0x20, 0x0001: 0x76}  # 0x20 (NOP), HLT
emu = I8080Emulator(mem)
emu.cpu_type = "i8080"
emu.sp = 0xFFFE
emu.int_enabled = False
emu.reset()
emu.step()
check("8080: опкод 0x20 как NOP (PC=0x0001)", emu.pc, 0x0001)

# === Тест 2: 8085 — опкод 0x20 как SIM ===
print("\nТест 2: 8085 — опкод 0x20 как SIM")
print("-" * 50)
mem = {0x0000: 0x3E, 0x0001: 0x0B, 0x0002: 0x20, 0x0003: 0x76}  # MVI A,0x0B; SIM; HLT
emu2 = I8080Emulator(mem)
emu2.cpu_type = "i8085"
emu2.sp = 0xFFFE
emu2.int_enabled = False
emu2.reset()
emu2.step()  # MVI A, 0x0B
emu2.step()  # SIM
check("8085: SIM выполнен", emu2.irq_enabled_85, True)
check("8085: маска прерываний = 0x03", emu2.irq_mask, 0x03)

# === Тест 3: 8080 — опкод 0x30 как NOP ===
print("\nТест 3: 8080 — опкод 0x30 как NOP")
print("-" * 50)
mem = {0x0000: 0x30, 0x0001: 0x76}  # 0x30 (NOP), HLT
emu3 = I8080Emulator(mem)
emu3.cpu_type = "i8080"
emu3.sp = 0xFFFE
emu3.int_enabled = False
emu3.reset()
emu3.step()
check("8080: опкод 0x30 как NOP (PC=0x0001)", emu3.pc, 0x0001)

# === Тест 4: 8085 — опкод 0x30 как RIM ===
print("\nТест 4: 8085 — опкод 0x30 как RIM")
print("-" * 50)
mem = {0x0000: 0x30, 0x0001: 0x76}  # RIM; HLT
emu4 = I8080Emulator(mem)
emu4.cpu_type = "i8085"
emu4.sp = 0xFFFE
emu4.int_enabled = False
emu4.reset()
emu4.sid = 1  # Устанавливаем SID
emu4.irq_mask = 0x05  # Маска: 7.5 и 5.5
emu4.irq_enabled_85 = True
emu4.step()  # RIM
check("8085: RIM выполнен (A содержит маску)", emu4.a & 0x08, 0x08)  # Бит 3: MSE
check("8085: A содержит SID", emu4.a & 0x80, 0x80)  # Бит 7: SID

# === Итог ===
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)