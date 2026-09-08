"""Тест I8272 — работа с внешними образами дисков"""
import os
import tempfile
from modules.memory.memory_bus import MemoryBus
from modules.io.i8272 import I8272

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
# ТЕСТ 1: Форматирование дисковода
# =============================================
print("\nТест 1: Форматирование дисковода")
print("-" * 50)

bus = MemoryBus()
fdc = I8272(base_port=0xF0)
fdc.register_to_bus(bus)

# Форматируем как 1.44 МБ
fdc.format_drive(0, tracks=80, heads=2, sectors_per_track=18, sector_size=512)

geo = fdc.get_drive_geometry(0)
check("Дорожек", geo["tracks"], 80)
check("Головок", geo["heads"], 2)
check("Секторов на дорожку", geo["sectors_per_track"], 18)
check("Размер сектора", geo["sector_size"], 512)
check("Всего секторов", geo["total_sectors"], 2880)
check("Всего байт (1.44 МБ)", geo["total_bytes"], 1474560)

# =============================================
# ТЕСТ 2: Запись и чтение сектора
# =============================================
print("\nТест 2: Запись и чтение сектора")
print("-" * 50)

drive = fdc.drives[0]
test_data = [i & 0xFF for i in range(512)]
drive.write_sector(0, 0, 1, test_data)

read_data = drive.read_sector(0, 0, 1)
check("Сектор записан и прочитан", read_data[:10], test_data[:10])

# =============================================
# ТЕСТ 3: Сохранение образа в файл
# =============================================
print("\nТест 3: Сохранение образа в файл")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    img_path = f.name

try:
    save_ok = fdc.save_disk_image(0, img_path)
    check("Образ сохранён", save_ok, True)
    
    file_size = os.path.getsize(img_path)
    check("Размер файла (1.44 МБ)", file_size, 1474560)
finally:
    if os.path.exists(img_path):
        os.remove(img_path)

# =============================================
# ТЕСТ 4: Загрузка образа из файла
# =============================================
print("\nТест 4: Загрузка образа из файла")
print("-" * 50)

# Создаём тестовый raw-образ 720 КБ (80 дорожек, 2 головки, 9 секторов)
with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    img_path = f.name
    # Записываем 737280 байт с паттерном
    data = bytearray()
    for i in range(737280):
        data.append(i & 0xFF)
    f.write(data)

try:
    load_ok = fdc.load_disk_image(1, img_path)
    check("Образ загружен", load_ok, True)
    
    geo = fdc.get_drive_geometry(1)
    check("Дорожек (720 КБ)", geo["tracks"], 80)
    check("Головок (720 КБ)", geo["heads"], 2)
    check("Секторов на дорожку (720 КБ)", geo["sectors_per_track"], 9)
    check("Всего байт (720 КБ)", geo["total_bytes"], 737280)
    
    # Проверяем данные первого сектора
    drive1 = fdc.drives[1]
    sector_data = drive1.read_sector(0, 0, 1)
    check("Первый байт первого сектора", sector_data[0], 0x00)
    check("Второй байт первого сектора", sector_data[1], 0x01)
    
    # Проверяем данные второго сектора (смещение 512)
    sector2 = drive1.read_sector(0, 0, 2)
    check("Первый байт второго сектора", sector2[0], 0x00)  # 512 & 0xFF = 0
    check("Второй байт второго сектора", sector2[1], 0x01)  # 513 & 0xFF = 1
finally:
    if os.path.exists(img_path):
        os.remove(img_path)

# =============================================
# ТЕСТ 5: Запись через контроллер + сохранение
# =============================================
print("\nТест 5: Запись через контроллер + сохранение")
print("-" * 50)

# Форматируем дисковод 2 как 720 КБ
fdc.format_drive(2, tracks=80, heads=2, sectors_per_track=9, sector_size=512)

# Вставляем "диск" и записываем данные через PIO
fdc.insert_disk(2)

# Записываем данные в сектор (0,0,1) через команду Write Data
fdc.drives[2].cylinder = 0
fdc.drives[2].head = 0

# Устанавливаем ND=1 (PIO mode) через Specify
bus.io_write(0xF0, 0x04 | 0x02)  # DOR: выбрать дисковод 2, normal mode
bus.io_write(0xF2, 0x03)  # Specify
bus.io_write(0xF2, 0x31)  # SRT=3, HUT=1
bus.io_write(0xF2, 0x21)  # HLT=16, ND=1 (PIO)

# Команда Write Data
bus.io_write(0xF2, 0x05)  # Write Data
bus.io_write(0xF2, 0x02)  # Параметр: дисковод 2
bus.io_write(0xF2, 0x00)  # Цилиндр 0
bus.io_write(0xF2, 0x00)  # Головка 0
bus.io_write(0xF2, 0x01)  # Сектор 1
bus.io_write(0xF2, 0x02)  # N=2 (512 байт)
bus.io_write(0xF2, 0x09)  # Последний сектор
bus.io_write(0xF2, 0x1B)  # GPL
bus.io_write(0xF2, 0xFF)  # DTL

# Записываем 512 байт данных
for i in range(512):
    bus.io_write(0xF2, (0xA0 + i) & 0xFF)

# Читаем результат (7 байт)
for i in range(7):
    bus.io_read(0xF2)

# Проверяем, что данные записаны
sector = fdc.drives[2].read_sector(0, 0, 1)
check("Данные записаны через контроллер (байт 0)", sector[0], 0xA0)
check("Данные записаны через контроллер (байт 1)", sector[1], 0xA1)

# Сохраняем в файл
with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    img_path = f.name

try:
    save_ok = fdc.save_disk_image(2, img_path)
    check("Образ дисковод 2 сохранён", save_ok, True)
    
    file_size = os.path.getsize(img_path)
    check("Размер файла (720 КБ)", file_size, 737280)
finally:
    if os.path.exists(img_path):
        os.remove(img_path)

# =============================================
# ТЕСТ 6: Автоопределение формата
# =============================================
print("\nТест 6: Автоопределение формата")
print("-" * 50)

# Создаём raw-образ 360 КБ (40 дорожек, 2 головки, 9 секторов)
with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    img_path = f.name
    f.write(bytes(368640))

try:
    load_ok = fdc.load_disk_image(3, img_path)
    check("Образ 360 КБ загружен", load_ok, True)
    
    geo = fdc.get_drive_geometry(3)
    check("Дорожек (360 КБ)", geo["tracks"], 40)
    check("Головок (360 КБ)", geo["heads"], 2)
    check("Секторов (360 КБ)", geo["sectors_per_track"], 9)
finally:
    if os.path.exists(img_path):
        os.remove(img_path)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ ОБРАЗОВ ДИСКОВ ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
