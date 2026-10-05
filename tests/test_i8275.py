"""Тест I8275 CRT-контроллера (итерация E5)"""
from modules.memory.memory_bus import MemoryBus
from modules.io.i8275 import I8275

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
# ТЕСТ 1: Сброс и начальное состояние
# =============================================
print("\nТест 1: Сброс и начальное состояние")
print("-" * 50)

bus = MemoryBus()
crt = I8275(base_port=0x70)
crt.register_to_bus(bus)

check("Дисплей выключен", crt.display_enabled, False)
check("IRQ не активен", crt.irq_flag, False)
check("DRQ не активен", crt.drq_flag, False)

# =============================================
# ТЕСТ 2: Загрузка параметров через P1/P2
# =============================================
print("\nТест 2: Загрузка параметров")
print("-" * 50)

# P1: 79 → 80 символов в строке
bus.io_write(0x70, 79)
# P2: bits 0-3 = 15 → 16 строк, bits 4-7 = 15 → высота символа 16
bus.io_write(0x71, 0xFF)

check("chars_per_line", crt.chars_per_line, 80)
check("lines_per_screen", crt.lines_per_screen, 16)
check("char_height", crt.char_height, 16)

# =============================================
# ТЕСТ 3: Старт отображения с DMA
# =============================================
print("\nТест 3: Старт отображения")
print("-" * 50)

drq_events = []
crt.on_drq = lambda active: drq_events.append(active)

# Команда Start Display
bus.io_write(0x71, I8275.CMD_START_DISPLAY)
check("Дисплей включён", crt.display_enabled, True)
check("DRQ запрошен", len(drq_events) > 0 and drq_events[-1], True)

# =============================================
# ТЕСТ 4: Загрузка видеопамяти через DMA
# =============================================
print("\nТест 4: Загрузка видеопамяти через DMA")
print("-" * 50)

# Эмулируем внешнюю видеопамять
fake_video_mem = {}
for i in range(80 * 16 * 2):
    if i % 2 == 0:
        fake_video_mem[0x1000 + i] = 0x41 + (i // 2) % 26  # A, B, C...
    else:
        fake_video_mem[0x1000 + i] = 0x00  # атрибут

crt.display_buffer_addr = 0x1000
crt.on_dma_read = lambda addr: fake_video_mem.get(addr, 0xFF)
crt._load_display_buffer()

char0, attr0 = crt.get_character(0, 0)
check("Символ (0,0) = 'A'", char0, 0x41)
char1, attr1 = crt.get_character(1, 0)
check("Символ (1,0) = 'B'", char1, 0x42)

# =============================================
# ТЕСТ 5: Курсор
# =============================================
print("\nТест 5: Курсор")
print("-" * 50)

crt.set_cursor(10, 5, enabled=True, blink=True)
check("Курсор X", crt.cursor_x, 10)
check("Курсор Y", crt.cursor_y, 5)
check("Курсор включён", crt.cursor_enabled, True)
check("Курсор мигает", crt.cursor_blink, True)

# Мигание
state_before = crt.cursor_blink_state
crt.tick_cursor_blink()
check("Мигание переключилось", crt.cursor_blink_state, not state_before)

# =============================================
# ТЕСТ 6: Прерывания
# =============================================
print("\nТест 6: Прерывания")
print("-" * 50)

irq_events = []
crt.on_irq = lambda active: irq_events.append(active)

crt.end_of_frame()
check("EOF флаг", crt.eof_flag, True)
check("IRQ активен", crt.irq_flag, True)
check("IRQ событие отправлено", irq_events[-1], True)

crt.acknowledge_interrupt()
check("IRQ сброшен", crt.irq_flag, False)
check("EOF сброшен", crt.eof_flag, False)

# Световое перо
crt.light_pen(20, 7)
check("LPEN X", crt.lpen_x, 20)
check("LPEN Y", crt.lpen_y, 7)
check("LPEN флаг", crt.lpen_flag, True)
check("IRQ от LPEN", crt.irq_flag, True)

# =============================================
# ТЕСТ 7: Остановка отображения
# =============================================
print("\nТест 7: Остановка отображения")
print("-" * 50)

bus.io_write(0x71, I8275.CMD_STOP_DISPLAY)
check("Дисплей выключен", crt.display_enabled, False)

# =============================================
# ТЕСТ 8: get_display_text
# =============================================
print("\nТест 8: get_display_text")
print("-" * 50)

crt2 = I8275(base_port=0x72)
crt2.chars_per_line = 5
crt2.lines_per_screen = 2
crt2.set_character(0, 0, ord('H'))
crt2.set_character(1, 0, ord('I'))
lines = crt2.get_display_text()
check("Строка 0 начинается с 'HI'", lines[0][:2], "HI")

# =============================================
# ТЕСТ 9: Сброс командой
# =============================================
print("\nТест 9: Сброс командой")
print("-" * 50)

crt.display_enabled = True
crt.irq_flag = True
bus.io_write(0x71, I8275.CMD_RESET)
check("После Reset: дисплей выключен", crt.display_enabled, False)
check("После Reset: IRQ сброшен", crt.irq_flag, False)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8275 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
