"""Тест разделения 8259 / 8259A (итерация E3)"""
from modules.memory.memory_bus import MemoryBus
from modules.io import IODevice, I8259, I8259A

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
# ТЕСТ 1: 8259 — инициализация БЕЗ ICW4
# =============================================
print("\nТест 1: 8259 — без ICW4")
print("-" * 50)

bus = MemoryBus()
pic = I8259(base_port=0x20)
pic.register_to_bus(bus)

# ICW1 с IC4=1 (бит 0), но 8259 должен его ИГНОРИРОВАТЬ
bus.io_write(0x20, 0x13)  # IC4=1, SNGL=1
check("Состояние после ICW1", pic.state, I8259.STATE_ICW2)

bus.io_write(0x21, 0x08)  # ICW2
# SNGL=1, у 8259 нет ICW4 → сразу READY
check("8259 сразу READY после ICW2 (SNGL)", pic.state, I8259.STATE_READY)
check("ICW4 всегда 0 у 8259", pic.icw4, 0x00)

# =============================================
# ТЕСТ 2: 8259 — запрос и вектор
# =============================================
print("\nТест 2: 8259 — запрос IRQ")
print("-" * 50)

pic.request_irq(0)
check("IRR после request_irq(0)", pic.irr, 0x01)
check("has_interrupt", pic.has_interrupt(), True)
vector = pic.get_vector()
check("Вектор IRQ0", vector, 0x08)
check("ISR после acknowledge", pic.isr, 0x01)
pic.end_of_interrupt()
check("ISR после EOI", pic.isr, 0x00)

# =============================================
# ТЕСТ 3: 8259A — инициализация С ICW4
# =============================================
print("\nТест 3: 8259A — с ICW4")
print("-" * 50)

bus2 = MemoryBus()
picA = I8259A(base_port=0x24)
picA.register_to_bus(bus2)

bus2.io_write(0x24, 0x13)  # ICW1: IC4=1, SNGL=1
check("Состояние после ICW1", picA.state, I8259A.STATE_ICW2)

bus2.io_write(0x25, 0x08)  # ICW2
# SNGL=1, но IC4=1 → переходим в ICW4
check("8259A в STATE_ICW4 после ICW2", picA.state, I8259A.STATE_ICW4)

bus2.io_write(0x25, 0x03)  # ICW4: 8086 + Auto-EOI
check("8259A READY после ICW4", picA.state, I8259A.STATE_READY)
check("ICW4 сохранён", picA.icw4, 0x03)
check("Режим 8086", picA.is_8086, True)
check("Auto-EOI включён", picA.auto_eoi, True)

# =============================================
# ТЕСТ 4: 8259A — Auto-EOI
# =============================================
print("\nТест 4: 8259A — Auto-EOI")
print("-" * 50)

picA.request_irq(2)
vector = picA.get_vector()
check("Вектор IRQ2", vector, 0x0A)
check("ISR пуст после Auto-EOI", picA.isr, 0x00)

# =============================================
# ТЕСТ 5: 8259A без IC4 (IC4=0)
# =============================================
print("\nТест 5: 8259A без IC4")
print("-" * 50)

bus3 = MemoryBus()
picA2 = I8259A(base_port=0x28)
picA2.register_to_bus(bus3)

bus3.io_write(0x28, 0x12)  # ICW1: IC4=0, SNGL=1
bus3.io_write(0x29, 0x20)  # ICW2
# IC4=0 → сразу READY, без ICW4
check("8259A READY без ICW4", picA2.state, I8259A.STATE_READY)
check("ICW4 = 0", picA2.icw4, 0x00)
check("Режим 8080", picA2.is_8086, False)

# =============================================
# ТЕСТ 6: 8259 — каскадный режим (с ICW3)
# =============================================
print("\nТест 6: 8259 каскадный режим (ICW3)")
print("-" * 50)

bus4 = MemoryBus()
pic4 = I8259(base_port=0x2C)
pic4.register_to_bus(bus4)

bus4.io_write(0x2C, 0x10)  # ICW1: IC4=0, SNGL=0 (каскад)
bus4.io_write(0x2D, 0x08)  # ICW2
check("Состояние после ICW2 (каскад)", pic4.state, I8259.STATE_ICW3)
bus4.io_write(0x2D, 0x04)  # ICW3
# У 8259 после ICW3 сразу READY (нет ICW4)
check("8259 READY после ICW3", pic4.state, I8259.STATE_READY)
check("ICW3 сохранён", pic4.icw3, 0x04)

# =============================================
# ТЕСТ 7: Наследование
# =============================================
print("\nТест 7: Наследование")
print("-" * 50)

check("I8259A наследует I8259", issubclass(I8259A, I8259), True)
check("I8259 наследует IODevice", issubclass(I8259, IODevice), True)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ 8259/8259A ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
