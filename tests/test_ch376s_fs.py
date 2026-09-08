"""Тест CH376S файловых команд — расширенный (итерация E6)"""
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
# ТЕСТ 1: Инициализация диска и ФС
# =============================================
print("\nТест 1: Инициализация диска и ФС")
print("-" * 50)

bus = MemoryBus()
usb = CH376S(base_port=0x276)
usb.register_to_bus(bus)

with tempfile.NamedTemporaryFile(delete=False, suffix='.img') as f:
    disk_path = f.name

try:
    usb.set_disk_image(disk_path, size_mb=4)
    
    # Проверки образа диска
    check("Образ диска создан", os.path.exists(disk_path), True)
    check("Размер образа (4 МБ)", os.path.getsize(disk_path), 4 * 1024 * 1024)
    check("Диск подключён", usb.disk_connected, True)
    check("Диск не смонтирован", usb.disk_mounted, False)
    
    # Инициализация и монтирование
    bus.io_write(0x277, CH376S.CMD_DISK_INIT)
    check("Диск инициализирован", usb.disk_initialized, True)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    
    bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)
    check("Диск смонтирован", usb.disk_mounted, True)
    
    # Проверка ёмкости диска
    bus.io_write(0x277, CH376S.CMD_DISK_CAPACITY)
    check("Данные готовы", usb.data_direction, 'read')
    capacity_bytes = read_data_port(usb, bus, 4)
    capacity = capacity_bytes[0] | (capacity_bytes[1] << 8) | \
               (capacity_bytes[2] << 16) | (capacity_bytes[3] << 24)
    check("Ёмкость диска (секторы)", capacity, 8192)  # 4 МБ / 512
    
    # Проверка версии чипа
    bus.io_write(0x277, CH376S.CMD_GET_IC_VER)
    version = bus.io_read(0x276)
    check("Версия CH376S", version, 0x76)
    
    # Проверка статуса диска
    bus.io_write(0x277, CH376S.CMD_DISK_QUERY)
    check("Данные готовы", usb.data_direction, 'read')
    status_byte = bus.io_read(0x276)
    check("Диск подключён (бит 0)", bool(status_byte & 0x01), True)
    check("Диск смонтирован (бит 1)", bool(status_byte & 0x02), True)
    check("Диск инициализирован (бит 2)", bool(status_byte & 0x04), True)
    
    # Проверка заголовка ФС
    header = usb._fs_read_header()
    check("Заголовок ФС создан", header is not None, True)
    check("Сигнатура ФС", header['table_start'], 1)
    check("Начало данных", header['next_free_sector'], 9)

    # =============================================
    # ТЕСТ 2: Создание файла
    # =============================================
    print("\nТест 2: Создание файла")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_CREATE)
    send_filename(usb, bus, "TEST.TXT")
    check("Статус: OK", usb.status, CH376S.STATUS_OK)
    check("Файл открыт", usb.file_open, True)
    check("Размер файла = 0", usb.file_size, 0)

    idx = usb._fs_find_file("TEST.TXT")
    check("Файл найден в таблице", idx is not None, True)

    # =============================================
    # ТЕСТ 3: Запись данных в файл
    # =============================================
    print("\nТест 3: Запись данных в файл")
    print("-" * 50)

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

    # =============================================
    # ТЕСТ 4: Позиционирование и чтение
    # =============================================
    print("\nТест 4: Позиционирование и чтение")
    print("-" * 50)

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

    # =============================================
    # ТЕСТ 5: Информация о файле (QUERY)
    # =============================================
    print("\nТест 5: Информация о файле")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_QUERY)
    info = read_data_port(usb, bus, 8)
    file_size = info[0] | (info[1] << 8) | (info[2] << 16) | (info[3] << 24)
    check("Размер файла в QUERY", file_size, len(test_data))

    # =============================================
    # ТЕСТ 6: Закрытие и повторное открытие
    # =============================================
    print("\nТест 6: Закрытие и повторное открытие")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_CLOSE)
    check("Файл закрыт", usb.file_open, False)

    bus.io_write(0x277, CH376S.CMD_FILE_OPEN)
    send_filename(usb, bus, "TEST.TXT")
    check("Файл открыт повторно", usb.file_open, True)
    check("Размер после открытия", usb.file_size, len(test_data))

    # =============================================
    # ТЕСТ 7: Перечисление файлов
    # =============================================
    print("\nТест 7: Перечисление файлов")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_CREATE)
    send_filename(usb, bus, "DATA.BIN")
    bus.io_write(0x277, CH376S.CMD_FILE_CLOSE)

    usb.enum_index = 0
    bus.io_write(0x277, CH376S.CMD_FILE_ENUM)
    enum_data = read_data_port(usb, bus, 17)
    enum_name = bytes(enum_data[:13]).split(b'\x00')[0].decode('ascii')
    check("Первый файл в перечислении", enum_name, "TEST.TXT")

    bus.io_write(0x277, CH376S.CMD_FILE_ENUM)
    enum_data = read_data_port(usb, bus, 17)
    enum_name = bytes(enum_data[:13]).split(b'\x00')[0].decode('ascii')
    check("Второй файл в перечислении", enum_name, "DATA.BIN")

    bus.io_write(0x277, CH376S.CMD_FILE_ENUM)
    enum_data = read_data_port(usb, bus, 1)
    check("Больше нет файлов", enum_data[0], 0x00)

    # =============================================
    # ТЕСТ 8: Открытие несуществующего файла
    # =============================================
    print("\nТест 8: Открытие несуществующего файла")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_OPEN)
    send_filename(usb, bus, "NOFILE.TXT")
    check("Статус: файл не найден", usb.status, CH376S.STATUS_FILE_NOT_FOUND)
    check("Файл не открыт", usb.file_open, False)

    # =============================================
    # ТЕСТ 9: Удаление файла
    # =============================================
    print("\nТест 9: Удаление файла")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_ERASE)
    send_filename(usb, bus, "DATA.BIN")
    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    idx = usb._fs_find_file("DATA.BIN")
    check("Файл удалён из таблицы", idx, None)

    # Проверка, что файл больше не открывается
    bus.io_write(0x277, CH376S.CMD_FILE_OPEN)
    send_filename(usb, bus, "DATA.BIN")
    check("Удалённый файл не открывается", usb.status, CH376S.STATUS_FILE_NOT_FOUND)

    # =============================================
    # ТЕСТ 10: Запись большого файла (расширение)
    # =============================================
    print("\nТест 10: Запись большого файла")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_FILE_CREATE)
    send_filename(usb, bus, "BIG.DAT")

    big_data = bytearray([i & 0xFF for i in range(600)])
    usb.data_buffer = big_data
    usb.data_direction = 'write'
    usb.data_index = len(big_data)

    bus.io_write(0x277, CH376S.CMD_FILE_WRITE)
    bus.io_write(0x276, 600 & 0xFF)
    bus.io_write(0x276, (600 >> 8) & 0xFF)
    check("Статус: OK", usb.status, CH376S.STATUS_OK)

    entry = usb._fs_read_entry(usb.file_index)
    check("Размер большого файла", entry['size'], 600)
    check("Выделено >= 2 секторов", entry['allocated'] >= 2, True)

    bus.io_write(0x277, CH376S.CMD_FILE_LOCATE)
    bus.io_write(0x276, 0)
    bus.io_write(0x276, 0)
    bus.io_write(0x276, 0)
    bus.io_write(0x276, 0)

    bus.io_write(0x277, CH376S.CMD_FILE_READ)
    bus.io_write(0x276, 0x58)  # 600 = 0x0258
    bus.io_write(0x276, 0x02)
    read_back = read_data_port(usb, bus, 600)
    check("Данные большого файла прочитаны", bytes(read_back[:10]), bytes(big_data[:10]))

    bus.io_write(0x277, CH376S.CMD_FILE_CLOSE)

    # =============================================
    # ТЕСТ 11: Чтение/запись секторов (низкий уровень)
    # =============================================
    print("\nТест 11: Чтение/запись секторов")
    print("-" * 50)

    # Запись сектора
    test_sector_data = bytearray([i & 0xFF for i in range(512)])
    for byte in test_sector_data:
        bus.io_write(0x276, byte)

    bus.io_write(0x277, CH376S.CMD_DISK_WRITE)
    bus.io_write(0x276, 10)  # LBA low
    bus.io_write(0x276, 0)   # LBA high
    bus.io_write(0x276, 1)   # count = 1
    check("Запись сектора: статус", usb.status, CH376S.STATUS_OK)

    # Проверка данных на диске
    with open(disk_path, 'rb') as f:
        f.seek(10 * 512)
        disk_data = f.read(512)
    check("Данные записаны на диск", list(disk_data[:10]), list(test_sector_data[:10]))

    # Чтение сектора
    bus.io_write(0x277, CH376S.CMD_DISK_READ)
    bus.io_write(0x276, 10)
    bus.io_write(0x276, 0)
    bus.io_write(0x276, 1)
    check("Чтение сектора: статус", usb.status, CH376S.STATUS_OK)

    read_sector = read_data_port(usb, bus, 512)
    check("Сектор прочитан", read_sector[:10], list(test_sector_data[:10]))

    # =============================================
    # ТЕСТ 12: Отключение и переподключение диска
    # =============================================
    print("\nТест 12: Отключение и переподключение")
    print("-" * 50)

    bus.io_write(0x277, CH376S.CMD_DISK_DISCONN)
    check("Диск отключён", usb.disk_connected, False)
    check("Диск не смонтирован", usb.disk_mounted, False)
    check("Диск не инициализирован", usb.disk_initialized, False)

    # Переподключение
    usb.set_disk_image(disk_path, size_mb=4)
    bus.io_write(0x277, CH376S.CMD_DISK_INIT)
    bus.io_write(0x277, CH376S.CMD_DISK_MOUNT)
    check("Диск переподключён", usb.disk_mounted, True)

    # Проверка, что файлы сохранились
    bus.io_write(0x277, CH376S.CMD_FILE_OPEN)
    send_filename(usb, bus, "TEST.TXT")
    check("Файл доступен после переподключения", usb.file_open, True)

    # =============================================
    # ТЕСТ 13: Защита от записи
    # =============================================
    print("\nТест 13: Защита от записи")
    print("-" * 50)

    usb.disk.write_protected = True
    bus.io_write(0x277, CH376S.CMD_FILE_CREATE)
    send_filename(usb, bus, "PROTECT.TXT")
    # При защите от записи создание файла может вернуть ошибку
    check("Статус при защите", usb.status != CH376S.STATUS_OK, True)

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
    print(" ✅ ВСЕ ТЕСТЫ CH376S FS ПРОЙДЕНЫ!")
    print(" 🎉 ИТЕРАЦИЯ E6 ЗАВЕРШЕНА!")
else:
    print(" ❌ Есть проваленные тесты.")
