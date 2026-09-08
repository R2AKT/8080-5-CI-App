"""Тест CH376S USB-контроллера (итерация E6)"""
import os
import tempfile
from modules.memory.memory_bus import MemoryBus
from modules.io.ch376s import CH376S

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

def send_filename(usb, bus, name):
    """Отправить имя файла через Data Port"""
    for ch in name.encode('ascii'):
        bus.io_write(usb.base_port, ch)
    bus.io_write(usb.base_port, 0x00)

def read_data_port(usb, bus, count):
    """Прочитать count байт из Data Port"""
    return [bus.io_read(usb.base_port) for _ in range(count)]

# =============================================
# ТЕСТ 1: Инициализация и создание образа диска
# =============================================
print("\nТест 1: Инициализация и создание образа диска")
print("-" * 50)

bus = MemoryBus()
usb = CH376S(base_port=0x276)
usb.register_to_bus(bus)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    usb.set_disk_image(disk_path, size_mb=32)
    check("Образ диска создан", os.path.exists(disk_path), True)
    check("Размер образа (32 МБ)", os.path.getsize(disk_path), 32 * 1024 * 1024)
    check("Диск подключён", usb.disk_connected, True)
    check("Диск не смонтирован", usb.disk_mounted, False)

    # =============================================
    # ТЕСТ 2: Инициализация и монтирование диска
    # =============================================
    print("\nТест 2: Инициализация и монтирование диска")
    print("-" * 50)

    # Команда DISK_INIT
    bus.io_write(0x277, CH376S.CMD_DISK_INIT)
    check("Диск инициализирован", usb.disk_initialized, True)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    # Команда DISK_MOUNT
    bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)
    check("Диск смонтирован", usb.disk_mounted, True)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    # =============================================
    # ТЕСТ 3: Ёмкость диска
    # =============================================
    print("\nТест 3: Ёмкость диска")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_DISK_CAPACITY)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    check("Данные готовы", usb.data_direction, 'read')

    capacity_bytes = []
    for i in range(4):
        capacity_bytes.append(bus.io_read(0x276))
    capacity = capacity_bytes[0] | (capacity_bytes[1] << 8) | \
               (capacity_bytes[2] << 16) | (capacity_bytes[3] << 24)
    check("Ёмкость диска (секторы)", capacity, 65536)

    # =============================================
    # ТЕСТ 4: Запись сектора
    # =============================================
    print("\nТест 4: Запись сектора")
    print("-" * 50)

    # Записываем данные в буфер
    test_data = bytearray([i & 0xFF for i in range(512)])
    for byte in test_data:
        bus.io_write(0x276, byte)

    # Команда DISK_WRITE: LBA=10, count=1
    bus.io_write(0x277, CH376S.CMD_DISK_WRITE)
    bus.io_write(0x276, 10)  # LBA low
    bus.io_write(0x276, 0)   # LBA high
    bus.io_write(0x276, 1)   # count = 1

    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    # Проверяем, что данные записаны на диск
    with open(disk_path, 'rb') as f:
        f.seek(10 * 512)
        disk_data = f.read(512)
    check("Данные записаны на диск", list(disk_data[:10]), list(test_data[:10]))

    # =============================================
    # ТЕСТ 5: Чтение сектора
    # =============================================
    print("\nТест 5: Чтение сектора")
    print("-" * 50)

    # Команда DISK_READ: LBA=10, count=1
    bus.io_write(0x277, CH376S.CMD_DISK_READ)
    bus.io_write(0x276, 10)  # LBA low
    bus.io_write(0x276, 0)   # LBA high
    bus.io_write(0x276, 1)   # count = 1

    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    check("Данные готовы", usb.data_direction, 'read')

    read_data = []
    for i in range(512):
        read_data.append(bus.io_read(0x276))
    check("Данные прочитаны", read_data[:10], list(test_data[:10]))

    # =============================================
    # ТЕСТ 6: Версия чипа
    # =============================================
    print("\nТест 6: Версия чипа")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_GET_IC_VER)
    version = bus.io_read(0x276)
    check("Версия CH376S", version, 0x76)

    # =============================================
    # ТЕСТ 7: Файловые операции
    # =============================================
    print("\nТест 7: Файловые операции")
    print("-" * 50)

    with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
        disk_path = f.name

    try:
        usb.set_disk_image(disk_path, size_mb=32)
        
        # Монтируем диск перед файловыми операциями
        bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)
        
        # Создание файла
        bus.io_write(0x277, CH376S.CMD_FILE_CREATE)
        send_filename(usb, bus, "TEST.TXT")
        check("Статус: OK", usb.status, CH376S.STATUS_OK)
        check("Файл открыт", usb.file_open, True)
        check("Размер файла = 0", usb.file_size, 0)

        idx = usb._fs_find_file("TEST.TXT")
        check("Файл найден в таблице", idx is not None, True)
        
        # Запись в файл
        test_data = bytearray(b"Hello, CH376S!")
        usb.data_buffer = test_data
        usb.data_direction = 'write'
        usb.data_index = len(test_data)

        bus.io_write(0x277, CH376S.CMD_FILE_WRITE)
        bus.io_write(0x276, len(test_data) & 0xFF)
        bus.io_write(0x276, (len(test_data) >> 8) & 0xFF)
        check("Статус: OK", usb.status, CH376S.STATUS_OK)
        check("Позиция после записи", usb.file_pos, len(test_data))

        entry = usb._fs_read_entry(usb.file_index)
        check("Размер файла обновлён", entry['size'], len(test_data))
        
        # Позиционирование в файле
        bus.io_write(0x277, CH376S.CMD_FILE_LOCATE)
        bus.io_write(0x276, 0)
        bus.io_write(0x276, 0)
        bus.io_write(0x276, 0)
        bus.io_write(0x276, 0)
        check("Позиция = 0", usb.file_pos, 0)

        bus.io_write(0x277, CH376S.CMD_FILE_READ)
        bus.io_write(0x276, len(test_data) & 0xFF)
        bus.io_write(0x276, 0)
        check("Данные готовы", usb.data_direction, 'read')

        read_data = read_data_port(usb, bus, len(test_data))
        check("Данные прочитаны", bytes(read_data), bytes(test_data))
        
        # Чтение из файла
        bus.io_write(0x277, CH376S.CMD_FILE_READ)
        bus.io_write(0x276, 0x10)  # Длина данных (16 байт)
        bus.io_write(0x276, 0x00)
        check("Данные готовы", usb.data_direction, 'read')
        
        # Закрытие файла
        bus.io_write(0x277, CH376S.CMD_FILE_CLOSE)
        check("Файл закрыт", usb.file_open, False)
        
    finally:
        if os.path.exists(disk_path):
            os.remove(disk_path)

    # =============================================
    # ТЕСТ 8: Статус диска
    # =============================================
    print("\nТест 8: Статус диска")
    print("-" * 50)

    # Переподключаем и инициализируем диск
    usb.set_disk_image(disk_path, size_mb=32)
    bus.io_write(0x277, CH376S.CMD_DISK_INIT)
    bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)
    
    # Проверка статуса диска
    bus.io_write(0x277, CH376S.CMD_DISK_QUERY)
    check("Данные готовы", usb.data_direction, 'read')
    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    check("Диск подключён", usb.disk_connected, True)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    check("Диск смонтирован", usb.disk_mounted, True)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    # =============================================
    # ТЕСТ 9: Отключение диска
    # =============================================
    print("\nТест 9: Отключение диска")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_DISK_DISCONN)
    check("Диск отключён", usb.disk_connected, False)
    check("Диск не смонтирован", usb.disk_mounted, False)
    check("Диск не инициализирован", usb.disk_initialized, False)

    # =============================================
    # ТЕСТ 10: Перечисление файлов
    # =============================================
    print("\nТест 10: Перечисление файлов")
    print("-" * 50)

    # Переподключаем и инициализируем диск
    usb.set_disk_image(disk_path, size_mb=32)
    bus.io_write(0x277, CH376S.CMD_DISK_INIT)
    bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)

    bus.io_write(0x277, CH376S.CMD_FILE_ENUM)
    check("Данные готовы", usb.data_direction, 'read')

    enum_data = bus.io_read(0x276)
    check("Перечисление файлов", enum_data, 0x00)  # Пустой список

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
    print(" ✅ ВСЕ ТЕСТЫ CH376S ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ E6 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
