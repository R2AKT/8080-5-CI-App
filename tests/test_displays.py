"""Тест дисплеев (итерация 8)"""
from modules.memory.memory_bus import MemoryBus
from modules.io.lcd1602 import LCD1602
from modules.io.lcd2004 import LCD2004
from modules.io.tft8080 import TFT8080

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
# ТЕСТ 1: Инициализация дисплеев
# =============================================
print("\nТест 1: Инициализация дисплеев")
print("-" * 50)

bus = MemoryBus()
lcd1602 = LCD1602(base_port=0x00)
lcd2004 = LCD2004(base_port=0x10)
tft = TFT8080(base_port=0x20)

lcd1602.register_to_bus(bus)
lcd2004.register_to_bus(bus)
tft.register_to_bus(bus)

check("LCD1602: 16 колонок", lcd1602.cols, 16)
check("LCD1602: 2 строки", lcd1602.rows, 2)
check("LCD2004: 20 колонок", lcd2004.cols, 20)
check("LCD2004: 4 строки", lcd2004.rows, 4)
check("TFT8080: 320 ширина", tft.width, 320)
check("TFT8080: 240 высота", tft.height, 240)

# =============================================
# ТЕСТ 2: Очистка дисплея
# =============================================
print("\nТест 2: Очистка дисплея")
print("-" * 50)

bus.io_write(0x01, LCD1602.CMD_CLEAR)
text = lcd1602.get_display_text()
check("LCD1602: после очистки строка 1 пустая", text[0].strip(), "")
check("LCD1602: после очистки строка 2 пустая", text[1].strip(), "")

# =============================================
# ТЕСТ 3: Запись символов на LCD1602
# =============================================
print("\nТест 3: Запись символов на LCD1602")
print("-" * 50)

bus.io_write(0x01, LCD1602.CMD_SET_DDRAM | 0x00)  # Адрес 0 (строка 1)
bus.io_write(0x00, ord('H'))
bus.io_write(0x00, ord('i'))

text = lcd1602.get_display_text()
check("LCD1602: строка 1 начинается с 'Hi'", text[0][:2], "Hi")

# =============================================
# ТЕСТ 4: Переход на вторую строку
# =============================================
print("\nТест 4: Переход на вторую строку")
print("-" * 50)

bus.io_write(0x01, LCD1602.CMD_SET_DDRAM | 0x40)  # Адрес 0x40 (строка 2)
bus.io_write(0x00, ord('O'))
bus.io_write(0x00, ord('K'))

text = lcd1602.get_display_text()
check("LCD1602: строка 2 начинается с 'OK'", text[1][:2], "OK")

# =============================================
# ТЕСТ 5: Запись на LCD2004
# =============================================
print("\nТест 5: Запись на LCD2004")
print("-" * 50)

bus.io_write(0x11, LCD2004.CMD_SET_DDRAM | 0x00)  # Строка 1
bus.io_write(0x10, ord('L'))
bus.io_write(0x10, ord('C'))
bus.io_write(0x10, ord('D'))

text = lcd2004.get_display_text()
check("LCD2004: строка 1 начинается с 'LCD'", text[0][:3], "LCD")

bus.io_write(0x11, LCD2004.CMD_SET_DDRAM | 0x14)  # Строка 3 (адрес 0x14)
bus.io_write(0x10, ord('X'))

text = lcd2004.get_display_text()
check("LCD2004: строка 3 начинается с 'X'", text[2][0], 'X')

# =============================================
# ТЕСТ 6: Автоинкремент и декремент
# =============================================
print("\nТест 6: Автоинкремент и декремент")
print("-" * 50)

lcd1602.reset()

# Автоинкремент
bus.io_write(0x01, LCD1602.CMD_ENTRY_MODE | 0x02)  # Инкремент
bus.io_write(0x01, LCD1602.CMD_SET_DDRAM | 0x00)
bus.io_write(0x00, ord('A'))
bus.io_write(0x00, ord('B'))
check("LCD1602: автоинкремент (A в 0, B в 1)",
      lcd1602.ddram[0], ord('A'))
check("LCD1602: автоинкремент (второй символ)",
      lcd1602.ddram[1], ord('B'))

# Декремент
lcd1602.reset()
bus.io_write(0x01, LCD1602.CMD_ENTRY_MODE | 0x00)  # Декремент
bus.io_write(0x01, LCD1602.CMD_SET_DDRAM | 0x05)
bus.io_write(0x00, ord('X'))
bus.io_write(0x00, ord('Y'))
check("LCD1602: декремент (адрес 5)",
      lcd1602.ddram[5], ord('X'))
check("LCD1602: декремент (адрес 4)",
      lcd1602.ddram[4], ord('Y'))

# =============================================
# ТЕСТ 7: Запись пикселя на TFT8080
# =============================================
print("\nТест 7: Запись пикселя на TFT8080")
print("-" * 50)

tft.reset()
bus.io_write(0x20, TFT8080.CMD_MEM_WRITE)  # Порт индекса: начало записи
bus.io_write(0x21, 0x34)  # Порт данных: младший байт пикселя
bus.io_write(0x21, 0x12)  # Порт данных: старший байт пикселя

fb = tft.get_framebuffer()
check("TFT8080: пиксель (0,0) записан", fb[0], 0x1234)

# =============================================
# ТЕСТ 8: Автоинкремент адреса на TFT8080
# =============================================
print("\nТест 8: Автоинкремент адреса на TFT8080")
print("-" * 50)

tft.reset()
bus.io_write(0x20, TFT8080.CMD_MEM_WRITE)  # Порт индекса: начало записи
bus.io_write(0x21, 0x01)  # Пиксель (0,0): младший байт
bus.io_write(0x21, 0x00)  # Пиксель (0,0): старший байт
bus.io_write(0x21, 0x02)  # Пиксель (1,0): младший байт
bus.io_write(0x21, 0x00)  # Пиксель (1,0): старший байт

fb = tft.get_framebuffer()
check("TFT8080: пиксель (0,0)", fb[0], 0x0001)
check("TFT8080: пиксель (1,0)", fb[1], 0x0002)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ДИСПЛЕЕВ ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ 8 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
