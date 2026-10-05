"""Тест CF IDE (итерация E6)"""
import os
import tempfile
from modules.memory.memory_bus import MemoryBus
from modules.io.cf_ide import CFIDE

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
# ТЕСТ 1: Инициализация и создание образа диска
# =============================================
print("\nТест 1: Инициализация и создание образа диска")
print("-" * 50)

bus = MemoryBus()
ide = CFIDE(base_port=0x1F0)
ide.register_to_bus(bus)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=32)
    check("Образ диска создан", os.path.exists(disk_path), True)
    check("Размер образа (32 МБ)", ide.disk_size, 32 * 1024 * 1024)
    check("Всего секторов", ide.total_sectors, 65536)
    check("Статус: DRDY", bool(ide.status & CFIDE.STATUS_DRDY), True)
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ТЕСТ 2: IDENTIFY DEVICE
# =============================================
print("\nТест 2: IDENTIFY DEVICE")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=32)

    # Отправляем команду IDENTIFY DEVICE
    bus.io_write(0x1F7, CFIDE.CMD_IDENTIFY_DEVICE)

    # Проверяем статус
    check("Статус: DRQ", bool(ide.status & CFIDE.STATUS_DRQ), True)

    # Читаем 512 байт данных
    identify_data = []
    for i in range(512):
        identify_data.append(bus.io_read(0x1F0))

    # Проверяем количество секторов (words 60-61)
    sectors = identify_data[120] | (identify_data[121] << 8) | \
              (identify_data[122] << 16) | (identify_data[123] << 24)
    check("Секторов в IDENTIFY", sectors, 65536)

    # Проверяем модель (words 27-46, big-endian)
    model = "".join([chr(identify_data[54 + i]) for i in range(20)])
    check("Модель в IDENTIFY", model.startswith("CF-IDE"), True)

    # Проверяем, что DRQ сброшен после чтения
    check("Статус: DRQ сброшен", bool(ide.status & CFIDE.STATUS_DRQ), False)
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ТЕСТ 3: Запись сектора
# =============================================
print("\nТест 3: Запись сектора")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=32)

    # Устанавливаем LBA = 100
    bus.io_write(0x1F3, 100)      # LBA Low
    bus.io_write(0x1F4, 0)        # LBA Mid
    bus.io_write(0x1F5, 0)        # LBA High
    bus.io_write(0x1F6, 0x40)     # Device/Head (LBA mode)

    # Счётчик секторов = 1
    bus.io_write(0x1F2, 1)

    # Команда WRITE SECTORS
    bus.io_write(0x1F7, CFIDE.CMD_WRITE_SECTORS)

    check("Статус: DRQ для записи", bool(ide.status & CFIDE.STATUS_DRQ), True)

    # Записываем 512 байт данных
    test_data = [i & 0xFF for i in range(512)]
    for byte in test_data:
        bus.io_write(0x1F0, byte)

    check("Статус: DRQ сброшен после записи", bool(ide.status & CFIDE.STATUS_DRQ), False)

    # Проверяем, что данные записаны на диск
    with open(disk_path, 'rb') as f:
        f.seek(100 * 512)
        disk_data = f.read(512)
    
    check("Данные записаны на диск", list(disk_data[:10]), test_data[:10])
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ТЕСТ 4: Чтение сектора
# =============================================
print("\nТест 4: Чтение сектора")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=32)

    # Записываем тестовые данные напрямую в файл
    test_data = bytearray([0xA0 + (i % 60) for i in range(512)])
    with open(disk_path, 'r+b') as f:
        f.seek(200 * 512)
        f.write(test_data)

    # Устанавливаем LBA = 200
    bus.io_write(0x1F3, 200)      # LBA Low
    bus.io_write(0x1F4, 0)        # LBA Mid
    bus.io_write(0x1F5, 0)        # LBA High
    bus.io_write(0x1F6, 0x40)     # Device/Head (LBA mode)

    # Счётчик секторов = 1
    bus.io_write(0x1F2, 1)

    # Команда READ SECTORS
    bus.io_write(0x1F7, CFIDE.CMD_READ_SECTORS)

    check("Статус: DRQ для чтения", bool(ide.status & CFIDE.STATUS_DRQ), True)

    # Читаем 512 байт данных
    read_data = []
    for i in range(512):
        read_data.append(bus.io_read(0x1F0))

    check("Данные прочитаны правильно", read_data[:10], list(test_data[:10]))
    check("Статус: DRQ сброшен после чтения", bool(ide.status & CFIDE.STATUS_DRQ), False)
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ТЕСТ 5: Чтение нескольких секторов
# =============================================
print("\nТест 5: Чтение нескольких секторов")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=32)

    # Записываем данные в 3 последовательных сектора (LBA 300-302)
    with open(disk_path, 'r+b') as f:
        for sec in range(3):
            f.seek((300 + sec) * 512)
            data = bytearray([sec] * 512)
            f.write(data)

    # Устанавливаем LBA = 300
    bus.io_write(0x1F3, 300 & 0xFF)         # LBA Low = 44
    bus.io_write(0x1F4, (300 >> 8) & 0xFF)  # LBA Mid = 1
    bus.io_write(0x1F5, 0)        # LBA High
    bus.io_write(0x1F6, 0x40)     # Device/Head (LBA mode)

    # Счётчик секторов = 3
    bus.io_write(0x1F2, 3)

    # Команда READ SECTORS
    bus.io_write(0x1F7, CFIDE.CMD_READ_SECTORS)

    # Читаем первый сектор
    read_data = []
    for i in range(512):
        read_data.append(bus.io_read(0x1F0))

    check("Первый сектор прочитан", read_data[0], 0x00)

    # Проверяем, что LBA увеличился
    check("LBA увеличен до 301", ide.lba_low, 301 & 0xFF)

    # Читаем второй сектор
    read_data2 = []
    for i in range(512):
        read_data2.append(bus.io_read(0x1F0))

    check("Второй сектор прочитан", read_data2[0], 0x01)
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ТЕСТ 6: Обработка ошибок (выход за границы)
# =============================================
print("\nТест 6: Обработка ошибок")
print("-" * 50)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    ide.set_disk_image(disk_path, size_mb=1)  # Маленький диск

    # Устанавливаем LBA за пределами диска
    bus.io_write(0x1F3, 0xFF)     # LBA Low
    bus.io_write(0x1F4, 0xFF)     # LBA Mid
    bus.io_write(0x1F5, 0xFF)     # LBA High
    bus.io_write(0x1F6, 0x4F)     # Device/Head (LBA mode + bits 24-27)

    bus.io_write(0x1F2, 1)

    # Команда READ SECTORS
    bus.io_write(0x1F7, CFIDE.CMD_READ_SECTORS)

    check("Статус: ERR", bool(ide.status & CFIDE.STATUS_ERR), True)
    check("Ошибка: IDNF", bool(ide.error_reg & CFIDE.ERROR_IDNF), True)
finally:
    if os.path.exists(disk_path):
        os.remove(disk_path)

# =============================================
# ИТОГИ
# =============================================
print("\n" + "=" * 50)
print(f" РЕЗУЛЬТАТ: {passed} пройдено, {failed} провалено")
print("=" * 50)
if failed == 0:
    print(" ✅ ВСЕ ТЕСТЫ CF IDE ПРОЙДЕНЫ!")
else:
    print(" ❌ Есть проваленные тесты.")
