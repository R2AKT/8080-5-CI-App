"""Тест I8253 PIT (итерация E3)"""
from modules.memory.memory_bus import MemoryBus
from modules.io import I8253

passed = 0
failed = 0

def check(name, actual, expected):
    global passed, failed
    if actual == expected:
        print(f"  ✅ {name}: {actual}")
        passed += 1
    else:
        print(f"  ❌ {name}: ожидалось {expected}, получено {actual}")
        failed += 1

# =============================================
# ТЕСТ 1: Mode 0 — Interrupt on Terminal Count
# =============================================
print("\nТест 1: Mode 0 — Interrupt on Terminal Count")
print("-" * 50)

bus = MemoryBus()
pit = I8253(base_port=0x40)
pit.register_to_bus(bus)

out_signals = []
pit.on_out = lambda ch, active: out_signals.append((ch, active))

# Control Word: Channel 0, LSB only, Mode 0, Binary
bus.io_write(0x43, 0x10)  # 0001 0000
# Загружаем count = 5
bus.io_write(0x40, 5)

check("Канал 0 запущен", pit.channels[0].running, True)
check("OUT = False до завершения", pit.get_out(0), False)

# Тикаем 4 такта — ещё не ноль
pit.tick(4)
check("OUT = False после 4 тактов", pit.get_out(0), False)

# Ещё 1 такт — ноль
pit.tick(1)
check("OUT = True после 5 тактов", pit.get_out(0), True)
check("Канал остановлен", pit.channels[0].running, False)
check("OUT сигнал сгенерирован", len(out_signals), 1)
check("OUT канал 0, active=True", out_signals[0], (0, True))

# =============================================
# ТЕСТ 2: Mode 2 — Rate Generator (периодический)
# =============================================
print("\nТест 2: Mode 2 — Rate Generator")
print("-" * 50)

pit2 = I8253(base_port=0x50)
out_signals2 = []
pit2.on_out = lambda ch, active: out_signals2.append((ch, active))

# Control Word: Channel 0, LSB only, Mode 2, Binary
pit2.io_write(0x53, 0x14)  # 0001 0100
# Загружаем count = 3
pit2.io_write(0x50, 3)

check("OUT = True (Mode 2 стартует с High)", pit2.get_out(0), True)

# Тикаем 3 такта — первый цикл
pit2.tick(3)
check("OUT = True после перезагрузки (Mode 2)", pit2.get_out(0), True)
check("Канал продолжает работать", pit2.channels[0].running, True)

# Ещё 3 такта — второй цикл
pit2.tick(3)
check("Канал всё ещё работает", pit2.channels[0].running, True)

# =============================================
# ТЕСТ 3: Mode 3 — Square Wave Generator
# =============================================
print("\nТест 3: Mode 3 — Square Wave Generator")
print("-" * 50)

pit3 = I8253(base_port=0x60)

# Control Word: Channel 0, LSB only, Mode 3, Binary
pit3.io_write(0x63, 0x16)  # 0001 0110
# Загружаем count = 2
pit3.io_write(0x60, 2)

check("OUT = True (Mode 3 стартует с High)", pit3.get_out(0), True)

# Тикаем 2 такта — OUT инвертируется
pit3.tick(2)
check("OUT = False после 2 тактов (инверсия)", pit3.get_out(0), False)

# Ещё 2 такта — OUT снова инвертируется
pit3.tick(2)
check("OUT = True после 4 тактов (инверсия)", pit3.get_out(0), True)

# =============================================
# ТЕСТ 4: LSB then MSB (16-битная загрузка)
# =============================================
print("\nТест 4: LSB then MSB (16-битная загрузка)")
print("-" * 50)

pit4 = I8253(base_port=0x70)

# Control Word: Channel 0, LSB then MSB, Mode 0, Binary
pit4.io_write(0x73, 0x30)  # 0011 0000
# Загружаем count = 0x0100 (256): LSB=0x00, MSB=0x01
pit4.io_write(0x70, 0x00)  # LSB
pit4.io_write(0x70, 0x01)  # MSB

check("Count = 0x0100", pit4.channels[0].count, 0x0100)
check("Канал запущен", pit4.channels[0].running, True)

# Тикаем 256 тактов
pit4.tick(256)
check("OUT = True после 256 тактов", pit4.get_out(0), True)

# =============================================
# ТЕСТ 5: Чтение зафиксированного значения (Latch)
# =============================================
print("\nТест 5: Counter Latch")
print("-" * 50)

pit5 = I8253(base_port=0x80)

# Загружаем count = 100, Mode 0, LSB only
pit5.io_write(0x83, 0x10)  # Ch0, LSB, Mode 0
pit5.io_write(0x80, 100)

# Тикаем 30 тактов (current = 70)
pit5.tick(30)
check("Current = 70", pit5.channels[0].current, 70)

# Counter Latch
pit5.io_write(0x83, 0x00)  # Latch Ch0
latched = pit5.io_read(0x80)
check("Зафиксированное значение = 70", latched, 70)

# =============================================
# ТЕСТ 6: GATE управление
# =============================================
print("\nТест 6: GATE управление")
print("-" * 50)

pit6 = I8253(base_port=0x90)

# Загружаем count = 10, Mode 0, LSB only
pit6.io_write(0x93, 0x10)
pit6.io_write(0x90, 10)

# GATE = False — канал не считает
pit6.set_gate(0, False)
pit6.tick(5)
check("Канал не считает при GATE=False", pit6.channels[0].current, 10)

# GATE = True — канал считает
pit6.set_gate(0, True)
pit6.tick(5)
check("Канал считает при GATE=True", pit6.channels[0].current, 5)

# =============================================
# ТЕСТ 7: Сброс
# =============================================
print("\nТест 7: Сброс")
print("-" * 50)

pit6.reset()
check("Канал 0 сброшен", pit6.channels[0].running, False)
check("OUT сброшен", pit6.channels[0].out, False)
check("Current сброшен", pit6.channels[0].current, 0)

# =============================================
# ТЕСТ 8: Подключение к шине MemoryBus
# =============================================
print("\nТест 8: Подключение к шине MemoryBus")
print("-" * 50)

bus8 = MemoryBus()
pit8 = I8253(base_port=0x40)
pit8.register_to_bus(bus8)

# Запись через шину
bus8.io_write(0x43, 0x10)  # Control Word
bus8.io_write(0x40, 50)    # Count = 50

check("Count записан через шину", pit8.channels[0].count, 50)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8253 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
