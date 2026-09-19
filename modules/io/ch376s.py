"""
CH376S — USB-контроллер для работы с USB Mass Storage устройствами.
Итерация E6: Хранение.

Возможности:
- Низкоуровневые операции: чтение/запись секторов, инициализация диска
- Файловые операции: открытие, чтение, запись, закрытие, перечисление
- Файловая система
- Поддержка подключения внешнего файла образа (как в CF IDE)

Регистры (2 порта):
  offset 0: Data Port (чтение/запись данных и параметров)
  offset 1: Command/Status Port (запись команд, чтение статуса)

Команды:
  Диск:
    0x04: DISK_INIT — инициализация диска
    0x05: DISK_MOUNT — монтирование диска
    0x06: DISK_READ — чтение секторов
    0x07: DISK_WRITE — запись секторов
    0x08: DISK_CAPACITY — ёмкость диска
    0x09: DISK_QUERY — статус диска
    0x0A: DISK_CONNECT — подключение диска
    0x0B: DISK_DISCONN — отключение диска
    0x0C: SET_USB_MODE — установка режима USB
  Файлы:
    0x0D: FILE_OPEN — открыть файл
    0x0E: FILE_CLOSE — закрыть файл
    0x0F: FILE_READ — чтение файла
    0x10: FILE_WRITE — запись файла
    0x11: FILE_ENUM — перечисление файлов
    0x12: FILE_CREATE — создать файл
    0x13: FILE_ERASE — удалить файл
    0x14: FILE_QUERY — информация о файле
    0x15: FILE_LOCATE — позиционирование в файле
  Общие:
    0x01: GET_IC_VER — версия чипа
    0x02: GET_STATUS — статус
"""
from .iodevice import IODevice
import os

# =============================================
# КОНСТАНТЫ ФАЙЛОВОЙ СИСТЕМЫ
# =============================================
FS_SIGNATURE = b"CH37"
FS_MAX_FILES = 128
FS_ENTRY_SIZE = 32
FS_HEADER_SECTOR = 0
FS_TABLE_START_SECTOR = 1
FS_TABLE_SECTORS = 8      # 128 записей × 32 байта = 4096 байт = 8 секторов
FS_DATA_START_SECTOR = FS_TABLE_START_SECTOR + FS_TABLE_SECTORS  # сектор 9

class CH376SDiskImage:
    """Эмуляция диска через файл-образ.
    Поддерживает чтение/запись секторов фиксированного размера.
    """
    SECTOR_SIZE = 512  # Стандартный размер сектора

    def __init__(self, image_path, size_mb=32):
        self.image_path = image_path
        self.size_mb = size_mb
        self.size_bytes = size_mb * 1024 * 1024
        self.total_sectors = self.size_bytes // self.SECTOR_SIZE
        self.connected = False
        self.mounted = False
        self.initialized = False
        self.write_protected = False

    def create_image(self):
        """Создать пустой образ диска.
        Если файл существует, но меньше нужного размера — расширяет его."""
        if not os.path.exists(self.image_path):
            with open(self.image_path, 'wb') as f:
                f.write(b'\x00' * self.size_bytes)
            return True
        # Если файл существует, но меньше нужного размера — расширяем
        current_size = os.path.getsize(self.image_path)
        if current_size < self.size_bytes:
            with open(self.image_path, 'r+b') as f:
                f.seek(current_size)
                f.write(b'\x00' * (self.size_bytes - current_size))
            return True
        return current_size == self.size_bytes

    def read_sector(self, lba):
        """Чтение сектора по LBA"""
        if lba >= self.total_sectors:
            return None
        offset = lba * self.SECTOR_SIZE
        try:
            with open(self.image_path, 'rb') as f:
                f.seek(offset)
                data = f.read(self.SECTOR_SIZE)
                if len(data) < self.SECTOR_SIZE:
                    data += b'\x00' * (self.SECTOR_SIZE - len(data))
                return bytearray(data)
        except OSError:
            return None

    def write_sector(self, lba, data):
        """Запись сектора по LBA"""
        if self.write_protected:
            return False
        if lba >= self.total_sectors:
            return False
        offset = lba * self.SECTOR_SIZE
        try:
            with open(self.image_path, 'r+b') as f:
                f.seek(offset)
                f.write(data[:self.SECTOR_SIZE])
            return True
        except OSError:
            return False

    def read_sectors(self, start_lba, count):
        """Чтение нескольких секторов"""
        result = bytearray()
        for i in range(count):
            data = self.read_sector(start_lba + i)
            if data is None:
                return None
            result.extend(data)
        return result

    def write_sectors(self, start_lba, data, count):
        """Запись нескольких секторов"""
        for i in range(count):
            sector_data = data[i * self.SECTOR_SIZE:(i + 1) * self.SECTOR_SIZE]
            if len(sector_data) < self.SECTOR_SIZE:
                sector_data += b'\x00' * (self.SECTOR_SIZE - len(sector_data))
            if not self.write_sector(start_lba + i, sector_data):
                return False
        return True

    def get_capacity(self):
        """Получить ёмкость диска в секторах"""
        return self.total_sectors

    def get_state(self):
        return {
            "image_path": self.image_path,
            "size_mb": self.size_mb,
            "total_sectors": self.total_sectors,
            "connected": self.connected,
            "mounted": self.mounted,
            "initialized": self.initialized,
            "write_protected": self.write_protected,
        }


class CH376SFile:
    """Упрощённая эмуляция файла в файловой системе"""
    def __init__(self, name, start_sector=0, size=0, attributes=0x20):
        self.name = name
        self.start_sector = start_sector
        self.size = size
        self.attributes = attributes
        self.opened = False
        self.file_pos = 0


class CH376S(IODevice):
    """CH376S — USB-контроллер для работы с диском"""

    # === Команды ===
    CMD_GET_IC_VER      = 0x01
    CMD_GET_STATUS      = 0x02
    CMD_WR_OFS_M_DATA   = 0x03
    CMD_DISK_INIT       = 0x04
    CMD_DISK_MOUNT      = 0x05
    CMD_DISK_READ       = 0x06
    CMD_DISK_WRITE      = 0x07
    CMD_DISK_CAPACITY   = 0x08
    CMD_DISK_QUERY      = 0x09
    CMD_DISK_CONNECT    = 0x0A
    CMD_DISK_DISCONN    = 0x0B
    CMD_SET_USB_MODE    = 0x0C
    CMD_FILE_OPEN       = 0x0D
    CMD_FILE_CLOSE      = 0x0E
    CMD_FILE_READ       = 0x0F
    CMD_FILE_WRITE      = 0x10
    CMD_FILE_ENUM       = 0x11
    CMD_FILE_CREATE     = 0x12
    CMD_FILE_ERASE      = 0x13
    CMD_FILE_QUERY      = 0x14
    CMD_FILE_LOCATE     = 0x15

    # === Статусы ===
    STATUS_OK             = 0x00  # Успех
    STATUS_BUSY           = 0x01  # Занят
    STATUS_ERROR          = 0x02  # Ошибка
    STATUS_NO_DISK        = 0x03  # Диск не подключён
    STATUS_WRITE_PROT     = 0x04  # Защита от записи
    STATUS_NOT_READY      = 0x05  # Не готов
    STATUS_FILE_NOT_FOUND = 0x06  # Файл не найден

    # === Режимы диска ===
    DISK_MODE_IDLE      = 0x00
    DISK_MODE_READING   = 0x01
    DISK_MODE_WRITING   = 0x02

    def __init__(self, base_port, name="CH376S"):
        super().__init__(base_port, 2, name)
        self.reset()
        # Callback для прерываний
        self.on_irq = None
        # Callback для передачи данных
        self.on_data_ready = None
        # Образ диска (устанавливается извне)
        self.disk = None

    def reset(self):
        """Сброс контроллера"""
        self.command = 0x00
        self.status = self.STATUS_OK
        self.data_buffer = bytearray()
        self.data_index = 0
        self.data_direction = None  # 'read' или 'write'
        self.pending_command = None
        self.param_buffer = bytearray()
        self.param_count = 0
        self.param_expected = 0
        # Диск
        self.disk = None
        self.disk_connected = False
        self.disk_mounted = False
        self.disk_initialized = False
        # Текущая операция
        self.current_lba = 0
        self.sector_count = 0
        self.disk_mode = self.DISK_MODE_IDLE
        # Файловая система
        self.file_open = False
        self.file_index = None
        self.file_path = ""
        self.file_pos = 0
        self.file_size = 0
        self.enum_index = 0
        self._collecting_filename = False
        # Версия чипа
        self.ic_version = 0x76  # CH376S
        # === Эмуляция занятости ===
        self.busy = False
        self.busy_cycles = 0
        self._pending_status = self.STATUS_OK
        self._pending_irq = False
        self.emulate_delay = False  # По умолчанию задержка

    def set_disk_image(self, path, size_mb=32):
        """Установить образ диска.
        Если файл не существует или пуст — создаётся и инициализируется ФС."""
        self.disk = CH376SDiskImage(path, size_mb)
        need_init = False
         
        if not os.path.exists(path):
            self.disk.create_image()
            need_init = True
        else:
            current_size = os.path.getsize(path)
            target_size = size_mb * 1024 * 1024
            if current_size == 0:
                need_init = True
            if current_size < target_size:
                with open(path, 'r+b') as f:
                    f.seek(current_size)
                    f.write(b'\x00' * (target_size - current_size))
         
        # Инициализация ФС только для нового/пустого образа
        if need_init:
            self._fs_init()
         
        self.disk.connected = True
        self.disk_connected = True
        self.disk_mounted = False
        self.disk_initialized = False
        return True

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Data Port: чтение данных
            if self.busy:
                return 0xFF  # Устройство занято
            return self._read_data()
        elif offset == 1:
            # Status Port: чтение статуса
            if self.busy:
                return self.STATUS_BUSY
            return self.status
        return 0xFF

    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        value &= 0xFF
        if offset == 0:
            # Data Port: запись данных/параметров
            self._write_data(value)
        elif offset == 1:
            # Command Port: запись команды
            self._write_command(value)

    # =============================================
    # ЧТЕНИЕ ДАННЫХ
    # =============================================
    def _read_data(self):
        """Чтение данных из буфера"""
        if self.data_direction == 'read' and self.data_index < len(self.data_buffer):
            val = self.data_buffer[self.data_index]
            self.data_index += 1
            if self.data_index >= len(self.data_buffer):
                self.data_direction = None
                self.data_buffer = bytearray()
                self.data_index = 0
            return val
        return 0xFF

    # =============================================
    # ЗАПИСЬ ДАННЫХ / ПАРАМЕТРОВ
    # =============================================
    def _write_data(self, value):
        """Запись данных/параметров"""
        # Сбор имени файла для файловых команд
        if self._collecting_filename:
            if value == 0x00:
                self._collecting_filename = False
                self._execute_command()
            elif len(self.param_buffer) < 13:
                self.param_buffer.append(value)
            return

        if self.pending_command is not None:
            # Сбор параметров для команды
            self.param_buffer.append(value)
            self.param_count += 1
            if self.param_count >= self.param_expected:
                self._execute_command()
        else:
            # Данные для записи на диск (всегда добавляются в буфер)
            self.data_buffer.append(value)

    # =============================================
    # ЗАПИСЬ КОМАНДЫ
    # =============================================
    def _write_command(self, value):
        """Запись команды"""
        self.command = value
        self.param_buffer = bytearray()
        self.param_count = 0

        # Файловые команды с именем файла
        if value in (self.CMD_FILE_OPEN, self.CMD_FILE_CREATE, self.CMD_FILE_ERASE):
            self._collecting_filename = True
            self.pending_command = value
            self.param_expected = 13
            return

        self.param_expected = self._get_param_count(value)
        if self.param_expected == 0:
            self._execute_command()
        else:
            self.pending_command = value

    def _get_param_count(self, cmd):
        """Количество параметров для команды"""
        if cmd == self.CMD_GET_IC_VER: return 0
        elif cmd == self.CMD_GET_STATUS: return 0
        elif cmd == self.CMD_DISK_INIT: return 0
        elif cmd == self.CMD_DISK_MOUNT: return 0
        elif cmd == self.CMD_DISK_READ: return 3
        elif cmd == self.CMD_DISK_WRITE: return 3
        elif cmd == self.CMD_DISK_CAPACITY: return 0
        elif cmd == self.CMD_DISK_QUERY: return 0
        elif cmd == self.CMD_DISK_CONNECT: return 0
        elif cmd == self.CMD_DISK_DISCONN: return 0
        elif cmd == self.CMD_SET_USB_MODE: return 1
        elif cmd == self.CMD_FILE_OPEN: return 13
        elif cmd == self.CMD_FILE_CLOSE: return 0
        elif cmd == self.CMD_FILE_READ: return 2
        elif cmd == self.CMD_FILE_WRITE: return 2
        elif cmd == self.CMD_FILE_ENUM: return 0
        elif cmd == self.CMD_FILE_CREATE: return 13
        elif cmd == self.CMD_FILE_ERASE: return 13
        elif cmd == self.CMD_FILE_QUERY: return 0
        elif cmd == self.CMD_FILE_LOCATE: return 4
        return 0

    # =============================================
    # ВЫПОЛНЕНИЕ КОМАНД
    # =============================================
    def _execute_command(self):
        """Выполнение команды"""
        cmd = self.pending_command if self.pending_command is not None else self.command
        self.pending_command = None
        self.status = self.STATUS_OK
        
        # Определяем длительность операции (в тактах CPU)
        duration = self._get_operation_duration(cmd)
        generate_irq = self._command_generates_irq(cmd)

        # Выполняем команду (подготовка данных и состояния)
        if cmd == self.CMD_GET_IC_VER:
            self._cmd_get_ic_ver()
        elif cmd == self.CMD_GET_STATUS:
            self._cmd_get_status()
        elif cmd == self.CMD_DISK_INIT:
            self._cmd_disk_init()
        elif cmd == self.CMD_DISK_MOUNT:
            self._cmd_disk_mount()
        elif cmd == self.CMD_DISK_READ:
            self._cmd_disk_read()
        elif cmd == self.CMD_DISK_WRITE:
            self._cmd_disk_write()
        elif cmd == self.CMD_DISK_CAPACITY:
            self._cmd_disk_capacity()
        elif cmd == self.CMD_DISK_QUERY:
            self._cmd_disk_query()
        elif cmd == self.CMD_DISK_CONNECT:
            self._cmd_disk_connect()
        elif cmd == self.CMD_DISK_DISCONN:
            self._cmd_disk_disconn()
        elif cmd == self.CMD_SET_USB_MODE:
            self._cmd_set_usb_mode()
        elif cmd == self.CMD_FILE_OPEN:
            self._cmd_file_open()
        elif cmd == self.CMD_FILE_CLOSE:
            self._cmd_file_close()
        elif cmd == self.CMD_FILE_READ:
            self._cmd_file_read()
        elif cmd == self.CMD_FILE_WRITE:
            self._cmd_file_write()
        elif cmd == self.CMD_FILE_ENUM:
            self._cmd_file_enum()
        elif cmd == self.CMD_FILE_CREATE:
            self._cmd_file_create()
        elif cmd == self.CMD_FILE_ERASE:
            self._cmd_file_erase()
        elif cmd == self.CMD_FILE_QUERY:
            self._cmd_file_query()
        elif cmd == self.CMD_FILE_LOCATE:
            self._cmd_file_locate()
        else:
            self.status = self.STATUS_ERROR
        
        # Запускаем эмуляцию задержки (если включена)
        final_status = self.status
        self._start_operation(duration, final_status, generate_irq)

    # =============================================
    # ФАЙЛОВАЯ СИСТЕМА
    # =============================================
    def _fs_init(self):
        """Инициализация ФС на новом образе"""
        self._fs_write_header({'next_free_sector': FS_DATA_START_SECTOR, 'file_count': 0})
        empty = {'name': '', 'attributes': 0, 'start_sector': 0, 'size': 0, 'allocated': 0, 'index': 0}
        for i in range(FS_MAX_FILES):
            self._fs_write_entry(i, empty)

    def _fs_read_header(self):
        """Чтение заголовка ФС"""
        sector_data = self.disk.read_sector(FS_HEADER_SECTOR)
        if sector_data is None or sector_data[0:4] != FS_SIGNATURE:
            return None
        return {
            'file_count': int.from_bytes(sector_data[4:8], 'little'),
            'table_start': int.from_bytes(sector_data[8:12], 'little'),
            'table_sectors': int.from_bytes(sector_data[12:16], 'little'),
            'data_start': int.from_bytes(sector_data[16:20], 'little'),
            'total_data_sectors': int.from_bytes(sector_data[20:24], 'little'),
            'next_free_sector': int.from_bytes(sector_data[24:28], 'little'),
        }

    def _fs_write_header(self, header):
        """Запись заголовка ФС"""
        sector_data = bytearray(self.disk.SECTOR_SIZE)
        sector_data[0:4] = FS_SIGNATURE
        sector_data[4:8] = header.get('file_count', 0).to_bytes(4, 'little')
        sector_data[8:12] = FS_TABLE_START_SECTOR.to_bytes(4, 'little')
        sector_data[12:16] = FS_TABLE_SECTORS.to_bytes(4, 'little')
        sector_data[16:20] = FS_DATA_START_SECTOR.to_bytes(4, 'little')
        total_sectors = self.disk.total_sectors - FS_DATA_START_SECTOR
        sector_data[20:24] = total_sectors.to_bytes(4, 'little')
        sector_data[24:28] = header.get('next_free_sector', FS_DATA_START_SECTOR).to_bytes(4, 'little')
        return self.disk.write_sector(FS_HEADER_SECTOR, sector_data)

    def _fs_read_entry(self, index):
        """Чтение записи файла из таблицы"""
        if index >= FS_MAX_FILES:
            return None
        sector = FS_TABLE_START_SECTOR + (index // 16)
        offset = (index % 16) * FS_ENTRY_SIZE
        sector_data = self.disk.read_sector(sector)
        if sector_data is None:
            return None
        entry_bytes = sector_data[offset:offset + FS_ENTRY_SIZE]
        name = bytes(entry_bytes[0:13]).split(b'\x00')[0].decode('ascii', errors='ignore')
        return {
            'name': name,
            'attributes': entry_bytes[13],
            'start_sector': int.from_bytes(entry_bytes[14:18], 'little'),
            'size': int.from_bytes(entry_bytes[18:22], 'little'),
            'allocated': int.from_bytes(entry_bytes[22:26], 'little'),
            'index': index
        }

    def _fs_write_entry(self, index, entry):
        """Запись записи файла в таблицу"""
        if index >= FS_MAX_FILES:
            return False
        sector = FS_TABLE_START_SECTOR + (index // 16)
        offset = (index % 16) * FS_ENTRY_SIZE
        sector_data = self.disk.read_sector(sector)
        sector_data = bytearray(sector_data) if sector_data else bytearray(self.disk.SECTOR_SIZE)
        name_bytes = entry['name'].encode('ascii')[:13].ljust(13, b'\x00')
        entry_bytes = bytearray(FS_ENTRY_SIZE)
        entry_bytes[0:13] = name_bytes
        entry_bytes[13] = entry.get('attributes', 0)
        entry_bytes[14:18] = entry.get('start_sector', 0).to_bytes(4, 'little')
        entry_bytes[18:22] = entry.get('size', 0).to_bytes(4, 'little')
        entry_bytes[22:26] = entry.get('allocated', 0).to_bytes(4, 'little')
        sector_data[offset:offset + FS_ENTRY_SIZE] = entry_bytes
        return self.disk.write_sector(sector, sector_data)

    def _fs_find_file(self, name):
        """Поиск файла по имени"""
        for i in range(FS_MAX_FILES):
            entry = self._fs_read_entry(i)
            if entry and entry['name'] == name:
                return i
        return None

    def _fs_find_free_entry(self):
        """Поиск свободной записи в таблице"""
        for i in range(FS_MAX_FILES):
            entry = self._fs_read_entry(i)
            if entry is None or not entry['name']:
                return i
        return None

    def _fs_alloc_sectors(self, count):
        """Выделение секторов для данных файла"""
        header = self._fs_read_header()
        if header is None:
            return None
        next_free = header['next_free_sector']
        for i in range(count):
            sector_data = self.disk.read_sector(next_free + i)
            if sector_data is None or any(b != 0 for b in sector_data):
                return None
        header['next_free_sector'] = next_free + count
        self._fs_write_header(header)
        return next_free

    def _fs_extend_file(self, entry, needed_sectors):
        """Расширение файла до нужного количества секторов"""
        current = entry['allocated']
        additional = needed_sectors - current
        if additional <= 0:
            return True
        start = entry['start_sector'] + current
        for i in range(additional):
            sector_data = self.disk.read_sector(start + i)
            if sector_data is None or any(b != 0 for b in sector_data):
                return False
        entry['allocated'] = needed_sectors
        return self._fs_write_entry(entry['index'], entry)

    def _fs_read_file_data(self, entry, offset, count):
        """Чтение данных файла"""
        result = bytearray()
        remaining = count
        current_offset = offset
        while remaining > 0:
            sector_index = current_offset // self.disk.SECTOR_SIZE
            sector_offset = current_offset % self.disk.SECTOR_SIZE
            sector_num = entry['start_sector'] + sector_index
            sector_data = self.disk.read_sector(sector_num) or bytes(self.disk.SECTOR_SIZE)
            bytes_in_sector = min(remaining, self.disk.SECTOR_SIZE - sector_offset)
            result.extend(sector_data[sector_offset:sector_offset + bytes_in_sector])
            remaining -= bytes_in_sector
            current_offset += bytes_in_sector
        return result

    def _fs_write_file_data(self, entry, offset, data):
        """Запись данных файла"""
        remaining = len(data)
        current_offset = offset
        data_index = 0
        while remaining > 0:
            sector_index = current_offset // self.disk.SECTOR_SIZE
            sector_offset = current_offset % self.disk.SECTOR_SIZE
            sector_num = entry['start_sector'] + sector_index
            sector_data = bytearray(self.disk.read_sector(sector_num) or bytes(self.disk.SECTOR_SIZE))
            bytes_in_sector = min(remaining, self.disk.SECTOR_SIZE - sector_offset)
            sector_data[sector_offset:sector_offset + bytes_in_sector] = data[data_index:data_index + bytes_in_sector]
            if not self.disk.write_sector(sector_num, sector_data):
                return False
            remaining -= bytes_in_sector
            current_offset += bytes_in_sector
            data_index += bytes_in_sector
        return True

    # =============================================
    # ОБЩИЕ КОМАНДЫ
    # =============================================
    def _cmd_get_ic_ver(self):
        """Получить версию чипа"""
        self.data_buffer = bytearray([self.ic_version])
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_get_status(self):
        """Получить статус"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
        elif not self.disk_connected:
            self.status = self.STATUS_NOT_READY
        elif not self.disk_initialized:
            self.status = self.STATUS_NOT_READY
        else:
            self.status = self.STATUS_OK

    # =============================================
    # КОМАНДЫ ДИСКА
    # =============================================
    def _cmd_disk_init(self):
        """Инициализация диска"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
            return
        if not self.disk.connected:
            self.status = self.STATUS_NOT_READY
            return
        self.disk_initialized = True
        self.disk.initialized = True
        self.status = self.STATUS_OK
        # # Генерируем прерывание
        # if self.on_irq:
            # self.on_irq(True)

    def _cmd_disk_mount(self):
        """Монтирование диска"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
            return
        if not self.disk_initialized:
            self.status = self.STATUS_NOT_READY
            return
        self.disk_mounted = True
        self.disk.mounted = True
        self.status = self.STATUS_OK

    def _cmd_disk_read(self):
        """Чтение секторов с диска"""
        if self.disk is None or not self.disk_initialized:
            self.status = self.STATUS_NOT_READY
            return
        if not self.disk_mounted:
            self.status = self.STATUS_NOT_READY
            return
        # Параметры: LBA (2 байта) + count (1 байт)
        lba = self.param_buffer[0] | (self.param_buffer[1] << 8)
        count = self.param_buffer[2]
        if count == 0:
            count = 256  # 0 означает 256 секторов
        # Читаем секторы
        data = self.disk.read_sectors(lba, count)
        if data is None:
            self.status = self.STATUS_ERROR
            return
        self.data_buffer = data
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK
        # # Генерируем прерывание
        # if self.on_irq:
            # self.on_irq(True)

    def _cmd_disk_write(self):
        """Запись секторов на диск"""
        if self.disk is None or not self.disk_initialized:
            self.status = self.STATUS_NOT_READY
            return
        if not self.disk_mounted:
            self.status = self.STATUS_NOT_READY
            return
        if self.disk.write_protected:
            self.status = self.STATUS_WRITE_PROT
            return
        # Параметры: LBA (2 байта) + count (1 байт)
        lba = self.param_buffer[0] | (self.param_buffer[1] << 8)
        count = self.param_buffer[2]
        if count == 0:
           count = 256
        # Проверяем наличие данных в буфере
        required = count * self.disk.SECTOR_SIZE
        if len(self.data_buffer) < required:
            self.status = self.STATUS_ERROR
            return
        # Записываем секторы из буфера данных
        write_data = bytes(self.data_buffer[:required])
        if not self.disk.write_sectors(lba, write_data, count):
            self.status = self.STATUS_ERROR
            return
        # Очищаем буфер после записи
        self.data_buffer = bytearray()
        self.data_index = 0
        self.status = self.STATUS_OK
        # # Генерируем прерывание
        # if self.on_irq:
            # self.on_irq(True)

    def _cmd_disk_capacity(self):
        """Получить ёмкость диска"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
            return
        capacity = self.disk.get_capacity()
        # Возвращаем ёмкость в секторах (4 байта, little-endian)
        self.data_buffer = bytearray([
            capacity & 0xFF,
            (capacity >> 8) & 0xFF,
            (capacity >> 16) & 0xFF,
            (capacity >> 24) & 0xFF
        ])
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_disk_query(self):
        """Запрос статуса диска"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
            return
        # Возвращаем статус диска
        status_byte = 0
        if self.disk.connected:
            status_byte |= 0x01
        if self.disk_mounted:
            status_byte |= 0x02
        if self.disk_initialized:
            status_byte |= 0x04
        if self.disk.write_protected:
            status_byte |= 0x08
        self.data_buffer = bytearray([status_byte])
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_disk_connect(self):
        """Подключение диска"""
        if self.disk is None:
            self.status = self.STATUS_NO_DISK
            return
        self.disk_connected = True
        self.disk.connected = True
        self.status = self.STATUS_OK
        # # Генерируем прерывание
        # if self.on_irq:
            # self.on_irq(True)

    def _cmd_disk_disconn(self):
        """Отключение диска"""
        self.disk_connected = False
        self.disk_mounted = False
        self.disk_initialized = False
        if self.disk:
            self.disk.connected = False
            self.disk.mounted = False
            self.disk.initialized = False
        self.status = self.STATUS_OK

    def _cmd_set_usb_mode(self):
        """Установка режима USB"""
        mode = self.param_buffer[0] if self.param_buffer else 0
        # Упрощённо: просто сохраняем режим
        self.usb_mode = mode
        self.status = self.STATUS_OK

    # =============================================
    # ФАЙЛОВЫЕ КОМАНДЫ (полная эмуляция)
    # =============================================
    def _cmd_file_open(self):
        """FILE_OPEN: открыть файл по имени"""
        name = bytes(self.param_buffer).split(b'\x00')[0].decode('ascii', errors='ignore')
        entry_index = self._fs_find_file(name)
        if entry_index is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        self.file_open = True
        self.file_index = entry_index
        self.file_pos = 0
        entry = self._fs_read_entry(entry_index)
        self.file_size = entry['size'] if entry else 0
        self.status = self.STATUS_OK

    def _cmd_file_close(self):
        """FILE_CLOSE: закрыть файл"""
        self.file_open = False
        self.file_index = None
        self.status = self.STATUS_OK

    def _cmd_file_read(self):
        """FILE_READ: чтение из файла"""
        if not self.file_open:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        count = self.param_buffer[0] | (self.param_buffer[1] << 8)
        entry = self._fs_read_entry(self.file_index)
        if entry is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        remaining = entry['size'] - self.file_pos
        count = min(count, max(0, remaining))
        if count <= 0:
            self.data_buffer = bytearray()
            self.data_index = 0
            self.data_direction = 'read'
            self.status = self.STATUS_OK
            return
        data = self._fs_read_file_data(entry, self.file_pos, count)
        self.file_pos += count
        self.data_buffer = data
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_file_write(self):
        """FILE_WRITE: запись в файл"""
        if not self.file_open:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        count = self.param_buffer[0] | (self.param_buffer[1] << 8)
        entry = self._fs_read_entry(self.file_index)
        if entry is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        # Расширение при необходимости
        needed_sectors = (self.file_pos + count + self.disk.SECTOR_SIZE - 1) // self.disk.SECTOR_SIZE
        if needed_sectors > entry['allocated']:
            if not self._fs_extend_file(entry, needed_sectors):
                self.status = self.STATUS_WRITE_PROT
                return
            entry = self._fs_read_entry(self.file_index)
        write_data = bytes(self.data_buffer[:count])
        if not self._fs_write_file_data(entry, self.file_pos, write_data):
            self.status = self.STATUS_ERROR
            return
        self.file_pos += count
        if self.file_pos > entry['size']:
            entry['size'] = self.file_pos
            self._fs_write_entry(self.file_index, entry)
            self.file_size = entry['size']
        self.status = self.STATUS_OK

    def _cmd_file_enum(self):
        """FILE_ENUM: перечисление файлов (по одному за вызов)"""
        if not self.disk_mounted:
            self.status = self.STATUS_NOT_READY
            return
        while self.enum_index < FS_MAX_FILES:
            entry = self._fs_read_entry(self.enum_index)
            self.enum_index += 1
            if entry and entry['name']:
                name_bytes = entry['name'].encode('ascii')[:13]
                size_bytes = entry['size'].to_bytes(4, 'little')
                self.data_buffer = bytearray(name_bytes.ljust(13, b'\x00')) + size_bytes
                self.data_index = 0
                self.data_direction = 'read'
                self.status = self.STATUS_OK
                return
        # Больше нет файлов
        self.data_buffer = bytearray([0x00])
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_file_create(self):
        """FILE_CREATE: создать файл"""
        name = bytes(self.param_buffer).split(b'\x00')[0].decode('ascii', errors='ignore')
        if self._fs_find_file(name) is not None:
            self.status = self.STATUS_ERROR
            return
        entry_index = self._fs_find_free_entry()
        if entry_index is None:
            self.status = self.STATUS_ERROR
            return
        initial_sectors = 1
        start_sector = self._fs_alloc_sectors(initial_sectors)
        if start_sector is None:
            self.status = self.STATUS_ERROR
            return
        entry = {
            'name': name, 'attributes': 0, 'start_sector': start_sector,
            'size': 0, 'allocated': initial_sectors, 'index': entry_index
        }
        if not self._fs_write_entry(entry_index, entry):
            self.status = self.STATUS_ERROR
            return
        self.file_open = True
        self.file_index = entry_index
        self.file_pos = 0
        self.file_size = 0
        self.status = self.STATUS_OK

    def _cmd_file_erase(self):
        """FILE_ERASE: удалить файл"""
        name = bytes(self.param_buffer).split(b'\x00')[0].decode('ascii', errors='ignore')
        entry_index = self._fs_find_file(name)
        if entry_index is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        entry = self._fs_read_entry(entry_index)
        if entry:
            for i in range(entry['allocated']):
                self.disk.write_sector(entry['start_sector'] + i, bytes(self.disk.SECTOR_SIZE))
        empty = {'name': '', 'attributes': 0, 'start_sector': 0, 'size': 0, 'allocated': 0, 'index': entry_index}
        self._fs_write_entry(entry_index, empty)
        if self.file_index == entry_index:
            self.file_open = False
            self.file_index = None
        self.status = self.STATUS_OK

    def _cmd_file_query(self):
        """FILE_QUERY: информация об открытом файле"""
        if not self.file_open:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        entry = self._fs_read_entry(self.file_index)
        if entry is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        self.data_buffer = bytearray(
            entry['size'].to_bytes(4, 'little') +
            self.file_pos.to_bytes(4, 'little') +
            bytes([entry['attributes'], 0, 0, 0])
        )
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_OK

    def _cmd_file_locate(self):
        """FILE_LOCATE: позиционирование в файле"""
        if not self.file_open:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        pos = (self.param_buffer[0] | (self.param_buffer[1] << 8) |
               (self.param_buffer[2] << 16) | (self.param_buffer[3] << 24))
        entry = self._fs_read_entry(self.file_index)
        if entry is None:
            self.status = self.STATUS_FILE_NOT_FOUND
            return
        self.file_pos = min(pos, entry['size'])
        self.status = self.STATUS_OK

    # =============================================
    # УТИЛИТЫ
    # =============================================
    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.status == self.STATUS_OK and self.data_direction == 'read'

    def acknowledge_interrupt(self):
        """Подтверждение прерывания"""
        if self.on_irq:
            self.on_irq(False)

    # =============================================
    # ЭМУЛЯЦИЯ ЗАНЯТОСТИ (итерация 10.3)
    # =============================================
    def set_emulate_delay(self, enabled):
        """Включить/выключить эмуляцию задержки операций"""
        self.emulate_delay = enabled

    def _start_operation(self, cycles, final_status=None, generate_irq=False):
        """Запуск операции с задержкой.
        Если emulate_delay выключен, операция завершается мгновенно."""
        if not self.emulate_delay:
            # Мгновенное выполнение: статус уже установлен командой
            if generate_irq and self.on_irq:
                self.on_irq(True)
            return
        self.busy = True
        self.busy_cycles = cycles
        self._pending_status = final_status if final_status is not None else self.status
        self._pending_irq = generate_irq

    def tick(self, cycles=1):
        """Вызывается каждый такт. Обработка занятости."""
        if not self.busy:
            return
        self.busy_cycles -= cycles
        if self.busy_cycles <= 0:
            self.busy = False
            self.status = self._pending_status
            if self._pending_irq and self.on_irq:
                self.on_irq(True)
            self._pending_irq = False

    def is_busy(self):
        """Проверка занятости устройства"""
        return self.busy

    def _get_operation_duration(self, cmd):
        """Длительность операции в тактах CPU"""
        if cmd == self.CMD_DISK_INIT:
            return 100  # Инициализация USB
        elif cmd == self.CMD_DISK_MOUNT:
            return 50   # Монтирование ФС
        elif cmd in (self.CMD_DISK_READ, self.CMD_DISK_WRITE):
            return 50   # На сектор
        elif cmd in (self.CMD_FILE_OPEN, self.CMD_FILE_CREATE,
                     self.CMD_FILE_READ, self.CMD_FILE_WRITE,
                     self.CMD_FILE_ERASE, self.CMD_FILE_LOCATE):
            return 20   # Файловые операции
        elif cmd in (self.CMD_GET_IC_VER, self.CMD_GET_STATUS,
                     self.CMD_DISK_CAPACITY, self.CMD_DISK_QUERY):
            return 1    # Мгновенные операции
        return 1

    def _command_generates_irq(self, cmd):
        """Генерирует ли команда прерывание по завершении"""
        return cmd in (
            self.CMD_DISK_INIT, self.CMD_DISK_READ, self.CMD_DISK_WRITE,
            self.CMD_DISK_CONNECT
        )

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        state = {
            "name": self.name,
            "base_port": self.base_port,
            "command": f"0x{self.command:02X}",
            "status": f"0x{self.status:02X}",
            "disk_connected": self.disk_connected,
            "disk_mounted": self.disk_mounted,
            "disk_initialized": self.disk_initialized,
            "file_open": self.file_open,
            "file_pos": self.file_pos,
            "data_direction": self.data_direction,
            "data_index": self.data_index,
            "data_buffer_len": len(self.data_buffer),
        }
        if self.disk:
            state["disk"] = self.disk.get_state()
        return state
