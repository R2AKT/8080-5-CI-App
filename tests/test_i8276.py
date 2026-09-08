"""Тест I8276 CRT-контроллера (итерация E5)"""
from modules.memory.memory_bus import MemoryBus, RAMRegion
from modules.io.i8276 import I8276

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
crt = I8276(base_port=0x60)
crt.register_to_bus(bus)

check("Не инициализирован", crt.initialized, False)
check("Дисплей выключен", crt.display_enabled, False)

# Инициализация: записываем 4 параметра
bus.io_write(0x61, I8276.CMD_INITIALIZE)
bus.io_write(0x60, 80)   # chars_per_line
bus.io_write(0x60, 24)   # lines_per_screen
bus.io_write(0x60, 8)    # char_width
bus.io_write(0x60, 16)   # char_height

check("Инициализирован", crt.initialized, True)
check("chars_per_line", crt.chars_per_line, 80)
check("lines_per_screen", crt.lines_per_screen, 24)

# =============================================
# ТЕСТ 2: Запись в видеопамять
# =============================================
print("\nТест 2: Запись в видеопамять")
print("-" * 50)

bus.io_write(0x60, 0x48)  # 'H'
bus.io_write(0x60, 0x45)  # 'E'
bus.io_write(0x60, 0x4C)  # 'L'
bus.io_write(0x60, 0x4C)  # 'L'
bus.io_write(0x60, 0x4F)  # 'O'

check("Символ 0", crt.video_ram.get(0), (0x48, 0x07))
check("Символ 1", crt.video_ram.get(1), (0x45, 0x07))
check("Символ 4", crt.video_ram.get(4), (0x4F, 0x07))
check("video_addr", crt.video_addr, 5)

# =============================================
# ТЕСТ 3: Включение дисплея
# =============================================
print("\nТест 3: Включение дисплея")
print("-" * 50)

bus.io_write(0x61, I8276.CMD_ENABLE_DISPLAY)
check("Дисплей включён", crt.display_enabled, True)

status = bus.io_read(0x61)
check("Status: DISPLAY_ON", bool(status & I8276.STATUS_DISPLAY_ON), True)

bus.io_write(0x61, I8276.CMD_DISABLE_DISPLAY)
check("Дисплей выключен", crt.display_enabled, False)

# =============================================
# ТЕСТ 4: DMA
# =============================================
print("\nТест 4: DMA")
print("-" * 50)

drq_events = []
crt.on_drq = lambda active: drq_events.append(active)

bus.io_write(0x61, I8276.CMD_DMA_ENABLE)
check("DMA включён", crt.dma_enabled, True)
check("DRQ активен", crt.drq_flag, True)
check("DRQ событие", drq_events[-1], True)

crt.dma_acknowledge()
check("DRQ сброшен после ACK", crt.drq_flag, False)

bus.io_write(0x61, I8276.CMD_DMA_DISABLE)
check("DMA выключен", crt.dma_enabled, False)

# =============================================
# ТЕСТ 5: Прерывания (VBLANK)
# =============================================
print("\nТест 5: Прерывания (VBLANK)")
print("-" * 50)

irq_events = []
crt.on_irq = lambda active: irq_events.append(active)

crt.vertical_blank()
check("IRQ активен после VBLANK", crt.irq_flag, True)
check("IRQ событие", irq_events[-1], True)

status = bus.io_read(0x61)
check("Status: VBLANK", bool(status & I8276.STATUS_VBLANK), True)

crt.acknowledge_interrupt()
check("IRQ сброшен", crt.irq_flag, False)

# =============================================
# ТЕСТ 6: Световое перо
# =============================================
print("\nТест 6: Световое перо")
print("-" * 50)

crt.light_pen(10, 5)
check("LPEN X", crt.lpen_x, 10)
check("LPEN Y", crt.lpen_y, 5)
check("LPEN флаг", crt.lpen_flag, True)

status = bus.io_read(0x61)
check("Status: LPEN", bool(status & I8276.STATUS_LPEN), True)

# =============================================
# ТЕСТ 7: set_character / get_character
# =============================================
print("\nТест 7: set_character / get_character")
print("-" * 50)

crt.set_character(0, 1, 0x41, 0x0F)  # 'A' с атрибутом
char, attr = crt.get_character(0, 1)
check("Символ (0,1)", char, 0x41)
check("Атрибут (0,1)", attr, 0x0F)

# =============================================
# ТЕСТ 8: get_display_text
# =============================================
print("\nТест 8: get_display_text")
print("-" * 50)

crt2 = I8276(base_port=0x62)
crt2.chars_per_line = 5
crt2.lines_per_screen = 2
crt2.set_character(0, 0, ord('H'))
crt2.set_character(1, 0, ord('I'))
lines = crt2.get_display_text()
check("Строка 0 начинается с 'HI'", lines[0][:2], "HI")

# =============================================
# ТЕСТ 9: Сброс
# =============================================
print("\nТест 9: Сброс")
print("-" * 50)

crt.reset()
check("После сброса: не инициализирован", crt.initialized, False)
check("После сброса: дисплей выключен", crt.display_enabled, False)
check("После сброса: видеопамять пуста", len(crt.video_ram), 0)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ I8276 ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
