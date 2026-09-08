"""Тест I8279 (итерация E5)"""
from modules.memory.memory_bus import MemoryBus
from modules.io import I8279

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
# ТЕСТ 1: Инициализация
# =============================================
print("\nТест 1: Инициализация")
print("-" * 50)

bus = MemoryBus()
kbd = I8279(base_port=0x60)
kbd.register_to_bus(bus)

check("FIFO пуст", len(kbd.key_fifo), 0)
check("Display RAM инициализирован нулями", kbd.display_ram[0], 0x00)
check("IRQ не активен", kbd.irq_flag, False)

# =============================================
# ТЕСТ 2: Установка режима клавиатуры/дисплея
# =============================================
print("\nТест 2: Установка режима")
print("-" * 50)

# Команда 000DDKKK: режим клавиатуры/дисплея
# D=01 (8 символов), K=10 (N-key rollover)
bus.io_write(0x61, 0x0A)  # 00001010
check("Режим клавиатуры", kbd.kbd_mode, 0x02)
check("Режим дисплея", kbd.disp_mode, 0x02)

# =============================================
# ТЕСТ 3: Запись в RAM дисплея
# =============================================
print("\nТест 3: Запись в RAM дисплея")
print("-" * 50)

# Устанавливаем адрес записи: 100DDRRR
bus.io_write(0x61, 0x90)  # Адрес 0, автоинкремент
# Записываем данные дисплея
bus.io_write(0x60, 0x3F)  # Цифра "0" (семисегментный код)
bus.io_write(0x60, 0x06)  # Цифра "1"
bus.io_write(0x60, 0x5B)  # Цифра "2"

check("Display RAM[0]", kbd.display_ram[0], 0x3F)
check("Display RAM[1]", kbd.display_ram[1], 0x06)
check("Display RAM[2]", kbd.display_ram[2], 0x5B)
check("Адрес после автоинкремента", kbd.display_addr, 3)

# =============================================
# ТЕСТ 4: Нажатие клавиши и IRQ
# =============================================
print("\nТест 4: Нажатие клавиши и IRQ")
print("-" * 50)

irq_events = []
kbd.on_irq = lambda active: irq_events.append(active)

kbd.key_press(0x41)  # Клавиша "A"
check("FIFO содержит 1 элемент", len(kbd.key_fifo), 1)
check("IRQ сгенерирован", kbd.irq_flag, True)
check("IRQ событие отправлено", irq_events[-1], True)

# Читаем статус
status = bus.io_read(0x61)
check("Статус: FIFO count=1", (status >> 4) & 0x0F, 1)

# Читаем FIFO
data = bus.io_read(0x60)
check("Данные из FIFO", data, 0x41)
check("FIFO пуст после чтения", len(kbd.key_fifo), 0)

# =============================================
# ТЕСТ 5: Несколько нажатий клавиш
# =============================================
print("\nТест 5: Несколько нажатий клавиш")
print("-" * 50)

kbd.key_press(0x42)  # "B"
kbd.key_press(0x43)  # "C"
kbd.key_press(0x44)  # "D"

check("FIFO содержит 3 элемента", len(kbd.key_fifo), 3)

# Читаем последовательно
check("FIFO[0]", bus.io_read(0x60), 0x42)
check("FIFO[1]", bus.io_read(0x60), 0x43)
check("FIFO[2]", bus.io_read(0x60), 0x44)

# =============================================
# ТЕСТ 6: Переполнение FIFO
# =============================================
print("\nТест 6: Переполнение FIFO")
print("-" * 50)

for i in range(8):
    kbd.key_press(0x30 + i)

check("FIFO полон", len(kbd.key_fifo), 8)
status = bus.io_read(0x61)
check("Статус: FIFO Full", bool(status & I8279.STATUS_FIFO_FULL), True)

# Ещё одно нажатие — переполнение
kbd.key_press(0xFF)
check("Out-of-range установлен", kbd.out_of_range, True)
check("FIFO не изменился", len(kbd.key_fifo), 8)

# =============================================
# ТЕСТ 7: Очистка клавиатуры
# =============================================
print("\nТест 7: Очистка клавиатуры")
print("-" * 50)

bus.io_write(0x61, I8279.CMD_CLEAR_KBD)  # 11010KKK
check("FIFO очищен", len(kbd.key_fifo), 0)
check("Out-of-range сброшен", kbd.out_of_range, False)

# =============================================
# ТЕСТ 8: Очистка дисплея
# =============================================
print("\nТест 8: Очистка дисплея")
print("-" * 50)

# Заполняем дисплей данными
bus.io_write(0x61, 0x90)
for i in range(16):
    bus.io_write(0x60, 0xFF)

check("Display RAM заполнен", kbd.display_ram[0], 0xFF)

# Очистка дисплея в 00
bus.io_write(0x61, I8279.CMD_CLEAR_DISP)  # 11000000
check("Display RAM очищен в 00", kbd.display_ram[0], 0x00)

# =============================================
# ТЕСТ 9: Конец прерывания
# =============================================
print("\nТест 9: Конец прерывания")
print("-" * 50)

kbd.key_press(0x55)
check("IRQ активен", kbd.irq_flag, True)

bus.io_write(0x61, I8279.CMD_END_INTERRUPT)  # 11101000
check("IRQ сброшен после EOI", kbd.irq_flag, False)

# =============================================
# ТЕСТ 10: Callback обновления дисплея
# =============================================
print("\nТест 10: Callback обновления дисплея")
print("-" * 50)

display_updates = []
kbd.on_display_update = lambda data: display_updates.append(list(data))

bus.io_write(0x61, 0x90)  # Адрес 0, автоинкремент
bus.io_write(0x60, 0x7F)  # Запись в дисплей

check("Callback вызван", len(display_updates) > 0, True)
check("Данные в callback", display_updates[-1][0], 0x7F)

# =============================================
# ТЕСТ 11: Сброс
# =============================================
print("\nТест 11: Сброс")
print("-" * 50)

kbd.key_press(0x99)
bus.io_write(0x61, 0x90)
bus.io_write(0x60, 0xAA)

kbd.reset()
check("FIFO пуст после сброса", len(kbd.key_fifo), 0)
check("Display RAM очищен после сброса", kbd.display_ram[0], 0x00)
check("IRQ не активен после сброса", kbd.irq_flag, False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8279 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
