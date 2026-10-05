"""
Тест всех типов дисплеев.
Запуск: вкладка "Скрипты" → "Выполнить скрипт".

Тестируемые устройства:
- LCD1602  — символьный дисплей 16×2
- LCD2004  — символьный дисплей 20×4
- TFT8080  — графический дисплей 320×240 (16-бит цвет)
- I8275    — CRT-контроллер (до 80×16 символов)
- I8276    — CRT-контроллер (до 128×64 символов)
"""
import time

# =============================================
# ПРОВЕРКА ДОСТУПА К СИСТЕМЕ
# =============================================
if not hasattr(api, 'system'):
    print("ОШИБКА: у api нет атрибута system!")
    print("Добавьте в AutomationAPI.__init__: self.system = main_window.system")
    raise RuntimeError("api.system не найден")

# =============================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================
def find_device(type_name, *names):
    """Ищет устройство по имени класса или именам экземпляров."""
    # Сначала по точным именам
    for name in names:
        dev = api.system.get_device(name)
        if dev:
            return dev
    # Затем по имени класса
    for dev in api.system.devices.values():
        if type(dev).__name__ == type_name:
            return dev
    return None

def dump_char_bitmap(char_gen, char_code, height=8):
    """Выводит битмап символа в консоль."""
    bm = char_gen.get_bitmap(char_code, height)
    print(f"  Битмап 0x{char_code:02X} ({chr(char_code) if 32 <= char_code < 127 else '?'}):")
    for row in bm:
        line = "   "
        for b in range(8):
            line += "█" if row & (0x01 << b) else " "
        print(line)

def print_lines(lines, label="Строки"):
    """Выводит строки дисплея."""
    for i, ln in enumerate(lines):
        stripped = ln.rstrip()
        if stripped:
            print(f"  {label} {i+1}: [{stripped}]")

# =============================================
# ТЕСТ LCD1602
# =============================================
def test_lcd1602():
    print("\n" + "=" * 55)
    print("  ТЕСТ LCD1602")
    print("=" * 55)
    dev = find_device("LCD1602", "LCD1602", "LCD16x2", "lcd1602")
    if dev is None:
        print("  ⚠ Устройство не найдено")
        return False

    print(f"  Найден: {dev.name} @ 0x{dev.base_port:02X}")

    # Очистка дисплея
    dev.io_write(dev.base_port + 1, 0x01)
    time.sleep(0.01)

    # Вывод на строку 1
    text1 = "HELLO 8080!"
    for ch in text1[:16]:
        dev.io_write(dev.base_port, ord(ch))

    # Переход на строку 2
    dev.io_write(dev.base_port + 1, 0x80 | 0x40)
    time.sleep(0.001)

    # Вывод на строку 2
    text2 = "i8080-5 CI"
    for ch in text2[:16]:
        dev.io_write(dev.base_port, ord(ch))

    # Проверка
    lines = dev.get_display_text()
    print_lines(lines)

    ok = "HELLO 8080!" in lines[0] and "i8080-5 CI" in lines[1]
    print(f"  Результат: {'✅' if ok else '❌'}")
    return ok

# =============================================
# ТЕСТ LCD2004
# =============================================
def test_lcd2004():
    print("\n" + "=" * 55)
    print("  ТЕСТ LCD2004")
    print("=" * 55)
    dev = find_device("LCD2004", "LCD2004", "LCD20x4", "lcd2004")
    if dev is None:
        print("  ⚠ Устройство не найдено")
        return False

    print(f"  Найден: {dev.name} @ 0x{dev.base_port:02X}")

    # Очистка дисплея
    dev.io_write(dev.base_port + 1, 0x01)
    time.sleep(0.01)

    # Адреса строк для 20×4
    line_addrs = [0x00, 0x40, 0x14, 0x54]
    texts = ["LINE 1: HELLO", "LINE 2: 8080", "LINE 3: TEST", "LINE 4: DONE"]

    for i, text in enumerate(texts):
        dev.io_write(dev.base_port + 1, 0x80 | line_addrs[i])
        time.sleep(0.001)
        for ch in text[:20]:
            dev.io_write(dev.base_port, ord(ch))

    # Проверка
    lines = dev.get_display_text()
    print_lines(lines)

    ok = all(texts[i] in lines[i] for i in range(4))
    print(f"  Результат: {'✅' if ok else '❌'}")
    return ok

# =============================================
# ТЕСТ TFT8080
# =============================================
def test_tft8080():
    print("\n" + "=" * 55)
    print("  ТЕСТ TFT8080")
    print("=" * 55)
    dev = find_device("TFT8080", "TFT8080", "TFT320x240", "tft8080")
    if dev is None:
        print("  ⚠ Устройство не найдено")
        return False

    print(f"  Найден: {dev.name} @ 0x{dev.base_port:02X}")

    w = dev.width
    h = dev.height
    print(f"  Разрешение: {w}×{h}")

    # Установка курсора в начало
    dev.io_write(dev.base_port, 0x21)      # Set Column
    dev.io_write(dev.base_port + 1, 0)
    dev.io_write(dev.base_port, 0x22)      # Set Row
    dev.io_write(dev.base_port + 1, 0)

    # Начало записи в видеопамять
    dev.io_write(dev.base_port, 0x2C)      # Memory Write

    # Заполнение градиентом (красный → синий по X, зелёный по Y)
    for y in range(h):
        for x in range(w):
            r = (x * 31) // w
            g = (y * 63) // h
            b = ((w - x) * 31) // w
            color = (r << 11) | (g << 5) | b
            dev.io_write(dev.base_port + 1, color & 0xFF)
            dev.io_write(dev.base_port + 1, (color >> 8) & 0xFF)

    # Проверка
    filled = sum(1 for p in dev.framebuffer if p != 0)
    total = w * h
    px0 = dev.framebuffer[0]
    px_mid = dev.framebuffer[total // 2]
    px_end = dev.framebuffer[total - 1]

    print(f"  Заполнено пикселей: {filled} / {total}")
    print(f"  Пиксель (0,0):     0x{px0:04X}")
    print(f"  Пиксель (центр):   0x{px_mid:04X}")
    print(f"  Пиксель (конец):   0x{px_end:04X}")

    ok = filled == total
    print(f"  Результат: {'✅' if ok else '❌'}")
    return ok

# =============================================
# ТЕСТ 8275
# =============================================
def test_8275():
    print("\n" + "=" * 55)
    print("  ТЕСТ 8275")
    print("=" * 55)
    dev = find_device("I8275", "I8275", "CRT8275", "crt8275")
    if dev is None:
        print("  ⚠ Устройство не найдено")
        return False

    print(f"  Найден: {dev.name} @ 0x{dev.base_port:02X}")

    # Инициализация параметров:
    # P1: chars_per_line - 1 = 79 (80 символов)
    # P2: char_height-1 << 4 | lines-1 = 0x0F (16 строк, высота 1)
    dev.io_write(dev.base_port, 79)
    dev.io_write(dev.base_port + 1, 0xFF)

    # Старт дисплея
    dev.io_write(dev.base_port + 1, 0x81)

    # Запись текста через set_character (эмуляция видеопамяти)
    text1 = "8275 CRT TEST"
    for i, ch in enumerate(text1):
        dev.set_character(i, 0, ord(ch), 0x00)

    text2 = "HELLO WORLD!"
    for i, ch in enumerate(text2):
        dev.set_character(i, 1, ord(ch), 0x00)

    # Текст с атрибутами (яркость + подчёркивание)
    text3 = "ATTR TEST"
    for i, ch in enumerate(text3):
        dev.set_character(i, 2, ord(ch), 0x08 | 0x04)  # BRIGHT | UNDERLINE

    # Проверка
    lines = dev.get_display_text()
    print_lines(lines)

    # Проверка знакогенератора
    if hasattr(dev, 'char_gen'):
        print("\n  Знакогенератор:")
        dump_char_bitmap(dev.char_gen, ord('A'), 8)

    ok = "8275 CRT TEST" in lines[0] and "HELLO WORLD!" in lines[1]
    print(f"\n  Результат: {'✅' if ok else '❌'}")
    return ok

# =============================================
# ТЕСТ 8276
# =============================================
def test_8276():
    print("\n" + "=" * 55)
    print("  ТЕСТ 8276")
    print("=" * 55)
    dev = find_device("I8276", "I8276", "Matrix8276", "crt8276")
    if dev is None:
        print("  ⚠ Устройство не найдено")
        return False

    print(f"  Найден: {dev.name} @ 0x{dev.base_port:02X}")

    # Инициализация
    dev.io_write(dev.base_port + 1, 0x01)  # INITIALIZE
    time.sleep(0.001)

    # Параметры инициализации (4 записи в порт данных)
    dev.io_write(dev.base_port, 79)   # chars_per_line = 80
    dev.io_write(dev.base_port, 23)   # lines_per_screen = 24
    dev.io_write(dev.base_port, 8)    # char_width = 8
    dev.io_write(dev.base_port, 16)   # char_height = 16

    # Включение дисплея
    dev.io_write(dev.base_port + 1, 0x02)  # ENABLE_DISPLAY

    # Запись текста через set_character (эмуляция видеопамяти)
    text1 = "8276 TEST"
    for i, ch in enumerate(text1):
        dev.set_character(i, 0, ord(ch), 0x00)

    text2 = "HELLO WORLD!"
    for i, ch in enumerate(text2):
        dev.set_character(i, 1, ord(ch), 0x00)

    # Текст с атрибутами (инверсия)
    text3 = "INVERSE"
    for i, ch in enumerate(text3):
        dev.set_character(i, 2, ord(ch), 0x02)  # INVERSE

    # Проверка
    lines = dev.get_display_text()
    print_lines(lines)

    # Проверка знакогенератора
    if hasattr(dev, 'char_gen'):
        print("\n  Знакогенератор:")
        dump_char_bitmap(dev.char_gen, ord('A'), 8)

    ok = "8276 TEST" in lines[0] and "HELLO WORLD!" in lines[1]
    print(f"\n  Результат: {'✅' if ok else '❌'}")
    return ok

# =============================================
# ЗАПУСК ВСЕХ ТЕСТОВ
# =============================================
print("=" * 55)
print("  УСТРОЙСТВА В СИСТЕМЕ")
print("=" * 55)
devices = api.system.list_devices()
print(f"Найдено устройств: {len(devices)}")
for d in devices:
    print(f"  [{d['type']}] {d['name']} @ {d['base_port']}")

results = {}
results['LCD1602'] = test_lcd1602()
results['LCD2004'] = test_lcd2004()
results['TFT8080'] = test_tft8080()
results['I8275']   = test_8275()
results['I8276']   = test_8276()

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 55)
print("  ИТОГИ ТЕСТОВ ДИСПЛЕЕВ")
print("=" * 55)
passed = sum(1 for v in results.values() if v)
total = len(results)
for name, ok in results.items():
    print(f"  {name:10s}: {'✅' if ok else '❌'}")
print(f"\n  Пройдено: {passed} / {total}")
if passed == total:
    print("  ✅ ВСЕ ТЕСТЫ ДИСПЛЕЕВ ПРОЙДЕНЫ!")
else:
    print("  ❌ Есть проваленные тесты.")
