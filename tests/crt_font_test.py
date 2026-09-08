"""
Тест: записываем текст в видеопамять 8275 с КОИ-7 кириллицей.
Итерация 12.13: используем преобразование из i8275.py.
"""
from modules.io.i8275 import I8275

# Поиск устройства 8275
dev = None
bus = api.system.bus

for d in api.system.devices.values():
    if type(d).__name__ == 'I8275':
        dev = d
        break

if dev is None:
    print("❌ 8275 не найден!")
    raise SystemExit

print(f"✅ 8275: {dev.name} @ 0x{dev.base_port:02X}")
print(f"   video_addr: 0x{dev.display_buffer_addr:04X}")
print(f"   chars_per_line: {dev.chars_per_line}")
print(f"   lines_per_screen: {dev.lines_per_screen}")

# Включаем отображение
dev.display_enabled = True

# Тестовый текст с кириллицей
test_text = "ПРИВЕТ 86РК!"
print(f"\n📝 Тестовый текст: '{test_text}'")

# Преобразуем в коды KOI-7 через метод из i8275.py
codes = I8275.unicode_to_koi7(test_text)
print(f"   Коды KOI-7: {' '.join(f'{c:02X}' for c in codes)}")

# Записываем в видеопамять
addr = dev.display_buffer_addr
for i, code in enumerate(codes):
    bus.write(addr + i * 2, code)      # Символ
    bus.write(addr + i * 2 + 1, 0x00)  # Атрибут (без эффектов)

# Заполняем остальное пробелами
total = dev.chars_per_line * dev.lines_per_screen
for i in range(len(codes), total):
    bus.write(addr + i * 2, 0x20)      # Пробел
    bus.write(addr + i * 2 + 1, 0x00)

# Запускаем обновление через DMA
dev._load_display_buffer()

print(f"\n✅ Записано {len(codes)} символов по адресу 0x{addr:04X}")
print(f"   Буфер: {len(dev.display_buffer)} символов")

# Проверка: читаем обратно через get_display_text
lines = dev.get_display_text()
if lines:
    first_line = lines[0].rstrip()
    print(f"\n🔍 get_display_text() вернул: '{first_line}'")
    if first_line == test_text:
        print("   ✅ Текст совпадает с исходным!")
    else:
        print(f"   ⚠ Отличие: ожидалось '{test_text}'")

print(f"\n📺 Откройте окно CRT из Диспетчера устройств")