"""Тест AM9511 APU (итерация E7)"""
from modules.memory.memory_bus import MemoryBus
from modules.io.am9511 import AM9511

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: Инициализация
# =============================================
print("\nТест 1: Инициализация")
print("-" * 50)

bus = MemoryBus()
apu = AM9511(base_port=0x80)
apu.register_to_bus(bus)

check("Не занят", apu.busy, False)
check("Стек пуст", apu.get_stack(), [0, 0, 0, 0])
status = bus.io_read(0x81)
check("Статус: не занят, END=0", bool(status & AM9511.STATUS_BUSY), False)

# =============================================
# ТЕСТ 2: PUSH / POP через Data Port
# =============================================
print("\nТест 2: PUSH / POP через Data Port")
print("-" * 50)

# PUSH 0x1234 (little-endian: 0x34, 0x12)
bus.io_write(0x80, 0x34)
bus.io_write(0x80, 0x12)
check("TOS = 0x1234", apu._tos(), 0x1234)

# PUSH 0xABCD
bus.io_write(0x80, 0xCD)
bus.io_write(0x80, 0xAB)
check("TOS = 0xABCD", apu._tos(), 0xABCD)
check("NOS = 0x1234", apu._nos(), 0x1234)

# POP через чтение (LSB, MSB)
lsb = bus.io_read(0x80)
check("POP LSB", lsb, 0xCD)
msb = bus.io_read(0x80)
check("POP MSB", msb, 0xAB)
check("TOS после POP", apu._tos(), 0x1234)

# =============================================
# ТЕСТ 3: ADD
# =============================================
print("\nТест 3: ADD")
print("-" * 50)

# Очищаем стек
apu.reset()

# PUSH 0x0010
bus.io_write(0x80, 0x10)
bus.io_write(0x80, 0x00)

# PUSH 0x0020
bus.io_write(0x80, 0x20)
bus.io_write(0x80, 0x00)

# ADD
bus.io_write(0x81, AM9511.CMD_ADD)
# Эмулируем такты для завершения
apu.tick(20)

check("Не занят после ADD", apu.busy, False)
check("END флаг", apu.end_flag, True)
check("Результат 0x0030", apu._tos(), 0x0030)
check("Флаг Zero = 0", apu.flag_zero, False)

# =============================================
# ТЕСТ 4: SUB и флаг Carry (заём)
# =============================================
print("\nТест 4: SUB и флаг Carry")
print("-" * 50)

apu.reset()
# PUSH 5
bus.io_write(0x80, 0x05); bus.io_write(0x80, 0x00)
# PUSH 3
bus.io_write(0x80, 0x03); bus.io_write(0x80, 0x00)

# SUB: 5 - 3 = 2
bus.io_write(0x81, AM9511.CMD_SUB)
apu.tick(20)
check("5 - 3 = 2", apu._tos(), 0x0002)
check("Carry = 0 (нет займа)", apu.flag_carry, False)

# SUB: 3 - 5 = -2 (0xFFFE)
apu.reset()
bus.io_write(0x80, 0x03); bus.io_write(0x80, 0x00)
bus.io_write(0x80, 0x05); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_SUB)
apu.tick(20)
check("3 - 5 = 0xFFFE", apu._tos(), 0xFFFE)
check("Carry = 1 (заём)", apu.flag_carry, True)
check("Sign = 1", apu.flag_sign, True)

# =============================================
# ТЕСТ 5: MUL (32-битный результат)
# =============================================
print("\nТест 5: MUL")
print("-" * 50)

apu.reset()
# PUSH 0x1000
bus.io_write(0x80, 0x00); bus.io_write(0x80, 0x10)
# PUSH 0x0010
bus.io_write(0x80, 0x10); bus.io_write(0x80, 0x00)

# MUL: 0x1000 * 0x0010 = 0x00010000
bus.io_write(0x81, AM9511.CMD_MUL)
apu.tick(40)

check("MUL: TOS (low) = 0x0000", apu._tos(), 0x0000)
check("MUL: NOS (high) = 0x0001", apu._nos(), 0x0001)
check("Carry = 1 (есть старшая часть)", apu.flag_carry, True)

# =============================================
# ТЕСТ 6: DIV и ошибка деления на 0
# =============================================
print("\nТест 6: DIV")
print("-" * 50)

apu.reset()
# PUSH 100
bus.io_write(0x80, 0x64); bus.io_write(0x80, 0x00)
# PUSH 7
bus.io_write(0x80, 0x07); bus.io_write(0x80, 0x00)

# DIV: 100 / 7 = 14 (частное), 2 (остаток)
bus.io_write(0x81, AM9511.CMD_DIV)
apu.tick(40)

check("DIV: TOS (остаток) = 2", apu._tos(), 2)
check("DIV: NOS (частное) = 14", apu._nos(), 14)

# Деление на 0
apu.reset()
bus.io_write(0x80, 0x10); bus.io_write(0x80, 0x00)
bus.io_write(0x80, 0x00); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_DIV)
apu.tick(40)
check("DIV by zero: флаг ошибки", apu.flag_div_err, True)

# =============================================
# ТЕСТ 7: Логические операции (AND, OR, XOR)
# =============================================
print("\nТест 7: Логические операции")
print("-" * 50)

apu.reset()
bus.io_write(0x80, 0xFF); bus.io_write(0x80, 0x00)
bus.io_write(0x80, 0x0F); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_AND)
apu.tick(10)
check("0xFF AND 0x0F = 0x0F", apu._tos(), 0x000F)

apu.reset()
bus.io_write(0x80, 0xF0); bus.io_write(0x80, 0x00)
bus.io_write(0x80, 0x0F); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_OR)
apu.tick(10)
check("0xF0 OR 0x0F = 0xFF", apu._tos(), 0x00FF)

# =============================================
# ТЕСТ 8: Сдвиги (SL, SR)
# =============================================
print("\nТест 8: Сдвиги")
print("-" * 50)

apu.reset()
bus.io_write(0x80, 0x01); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_SL)
apu.tick(10)
check("SL: 0x0001 << 1 = 0x0002", apu._tos(), 0x0002)
check("SL: Carry = 0", apu.flag_carry, False)

# Сдвиг с переносом
apu.reset()
bus.io_write(0x80, 0x00); bus.io_write(0x80, 0x80)  # 0x8000
bus.io_write(0x81, AM9511.CMD_SL)
apu.tick(10)
check("SL: 0x8000 << 1 = 0x0000", apu._tos(), 0x0000)
check("SL: Carry = 1 (бит 15)", apu.flag_carry, True)

# =============================================
# ТЕСТ 9: Режим IRQ
# =============================================
print("\nТест 9: Режим IRQ")
print("-" * 50)

irq_events = []
apu.reset()
apu.sync_mode = AM9511.MODE_IRQ
apu.on_irq = lambda active: irq_events.append(active)

bus.io_write(0x80, 0x01); bus.io_write(0x80, 0x00)
bus.io_write(0x80, 0x02); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_ADD)

check("Занят после команды", apu.busy, True)
check("IRQ не вызван до tick", len(irq_events), 0)

apu.tick(20)
check("Не занят после tick", apu.busy, False)
check("IRQ вызван", len(irq_events) > 0 and irq_events[-1], True)

# =============================================
# ТЕСТ 10: Режим Wait State
# =============================================
print("\nТест 10: Режим Wait State")
print("-" * 50)

wait_events = []
apu.reset()
apu.sync_mode = AM9511.MODE_WAIT
apu.on_wait = lambda active: wait_events.append(active)

bus.io_write(0x80, 0x01); bus.io_write(0x80, 0x00)
bus.io_write(0x81, AM9511.CMD_SL)

check("WAIT активен", len(wait_events) > 0 and wait_events[-1], True)
check("is_busy() = True", apu.is_busy(), True)

apu.tick(10)
check("WAIT снят", wait_events[-1], False)
check("is_busy() = False", apu.is_busy(), False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ AM9511 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
