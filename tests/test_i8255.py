"""Тест I8255 (итерация E3)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
from modules.io import I8255

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
# ТЕСТ 1: Mode 0 — простой ввод/вывод
# =============================================
print("\nТест 1: Mode 0 — простой ввод/вывод")
print("-" * 50)

bus = MemoryBus()
ram = RAMRegion(0x0000, 0xFFFF, name="RAM")
bus.register_memory(ram)
ppi = I8255(base_port=0x00)
ppi.register_to_bus(bus)

# Запись Control Word: все порты на вывод, Mode 0
bus.io_write(0x03, 0x80)  # 1000 0000 — все на вывод
check("Control Word записан", bus.io_read(0x03), 0x80)

# Запись в порт A
bus.io_write(0x00, 0x55)
check("Port A записан", bus.io_read(0x00), 0x55)

# Запись в порт B
bus.io_write(0x01, 0xAA)
check("Port B записан", bus.io_read(0x01), 0xAA)

# Запись в порт C
bus.io_write(0x02, 0x0F)
check("Port C записан", bus.io_read(0x02), 0x0F)

# =============================================
# ТЕСТ 2: BSR — установка/сброс битов порта C
# =============================================
print("\nТест 2: BSR — установка/сброс битов порта C")
print("-" * 50)

bus.io_write(0x03, 0x80)  # Сброс порта C
bus.io_write(0x02, 0x00)

# Установить бит 3 порта C
bus.io_write(0x03, 0x07)  # 0000 0111 — бит 3, установка
check("Бит 3 порта C установлен", bus.io_read(0x02) & 0x08, 0x08)

# Сбросить бит 3 порта C
bus.io_write(0x03, 0x06)  # 0000 0110 — бит 3, сброс
check("Бит 3 порта C сброшен", bus.io_read(0x02) & 0x08, 0x00)

# Установить бит 7 порта C
bus.io_write(0x03, 0x0F)  # 0000 1111 — бит 7, установка
check("Бит 7 порта C установлен", bus.io_read(0x02) & 0x80, 0x80)

# =============================================
# ТЕСТ 3: Mode 1 — стробированный ввод с прерыванием
# =============================================
print("\nТест 3: Mode 1 — стробированный ввод с прерыванием")
print("-" * 50)

interrupts = []
ppi2 = I8255(base_port=0x10)
ppi2.on_interrupt = lambda sig, active: interrupts.append((sig, active))
bus2 = MemoryBus()
ppi2.register_to_bus(bus2)

# Control Word: порт A — ввод, Mode 1
bus2.io_write(0x13, 0xB0)  # 1011 0000 — порт A ввод, Mode 1, остальное Mode 0

# Внешний сигнал на вход порта A
ppi2.set_port_input('A', 0x42)
check("Port A прочитан", bus2.io_read(0x10), 0x42)
check("INTRA сгенерирован", len(interrupts), 1)
check("Сигнал INTRA", interrupts[0][0], 'INTRA')
check("Бит INTRA в порте C", bus2.io_read(0x12) & 0x20, 0x20)

# Подтверждение прерывания
ppi2.acknowledge_interrupt('INTRA')
check("INTRA сброшен", ppi2.intra, False)

# =============================================
# ТЕСТ 4: Сброс
# =============================================
print("\nТест 4: Сброс")
print("-" * 50)

ppi.reset()
check("Port A после сброса", ppi.port_a, 0x00)
check("Port B после сброса", ppi.port_b, 0x00)
check("Port C после сброса", ppi.port_c, 0x00)
check("Control после сброса", ppi.control, 0x9B)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8255 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
