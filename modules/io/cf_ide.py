"""
CF IDE — CompactFlash в режиме ATA/IDE.
Итерация E6: Хранение.

Особенности для i8080:
- Шина данных 8 бит (16-битные регистры читаются по 2 байта)
- Режим 8-bit PIO для совместимости
- LBA-адресация (без CHS)

Регистры (8 портов, base_port + offset):
  offset 0: Data (16-bit, читается как 2 байта LSB/MSB)
  offset 1: Error (чтение) / Features (запись)
  offset 2: Sector Count
  offset 3: LBA Low (Sector)
  offset 4: LBA Mid (Cylinder Low)
  offset 5: LBA High (Cylinder High)
  offset 6: Device/Head
  offset 7: Status (чтение) / Command (запись)

Команды:
  0xEC: IDENTIFY DEVICE
  0x20: READ SECTORS (с прерыванием)
  0x21: READ SECTORS (без прерывания)
  0x30: WRITE SECTORS (с прерыванием)
  0x31: WRITE SECTORS (без прерывания)

Статусные биты (Status Register):
  Bit 7: BSY  — занят
  Bit 6: DRDY — готов
  Bit 3: DRQ  — запрос данных
  Bit 0: ERR  — ошибка
"""
from .iodevice import IODevice
import os


class CFIDE(IODevice):
    """CF IDE — CompactFlash в режиме ATA/IDE"""

    # Команды ATA
    CMD_IDENTIFY_DEVICE = 0xEC
    CMD_READ_SECTORS    = 0x20  # с прерыванием
    CMD_READ_SECTORS_NI = 0x21  # без прерывания
    CMD_WRITE_SECTORS   = 0x30  # с прерыванием
    CMD_WRITE_SECTORS_NI = 0x31  # без прерывания

    # Биты статуса
    STATUS_BSY  = 0x80  # Занят
    STATUS_DRDY = 0x40  # Готов
    STATUS_DRQ  = 0x08  # Запрос данных
    STATUS_ERR  = 0x01  # Ошибка

    # Биты ошибок
    ERROR_ABRT = 0x04   # Команда прервана
    ERROR_IDNF = 0x10   # ID не найден

    # Размер сектора
    SECTOR_SIZE = 512

    def __init__(self, base_port, name="CFIDE"):
        super().__init__(base_port, 8, name)
        self.disk_file = None      # Путь к образу диска
        self.disk_size = 0         # Размер диска в байтах
        self.total_sectors = 0     # Общее количество секторов
        self.on_irq = None         # Callback прерывания
        self.reset()

    def reset(self):
        """Сброс контроллера"""
        # Регистры
        self.error_reg = 0x00
        self.features_reg = 0x00
        self.sector_count = 0x01
        self.lba_low = 0x00      # Сектор (LBA bits 0-7)
        self.lba_mid = 0x00      # Цилиндр младший (LBA bits 8-15)
        self.lba_high = 0x00     # Цилиндр старший (LBA bits 16-23)
        self.device_head = 0x00  # Device/Head (LBA bits 24-27 + flags)
        self.status = self.STATUS_DRDY  # Готов
        self.command = 0x00

        # Буфер данных (для чтения/записи секторов)
        self.data_buffer = []
        self.data_index = 0
        self.data_direction = None  # 'read' или 'write'
        self.data_count = 0         # Количество байт для передачи

        # 8-bit mode
        self.eight_bit_mode = False
        
        # === Эмуляция занятости (итерация 10.3) ===
        self.busy = False
        self.busy_cycles = 0
        self._pending_status = self.STATUS_DRDY
        self._pending_irq = False
        self.on_wait = None  # Callback для WAIT-сигнала
        self.emulate_delay = False  # по умолчанию задержка выключена

    # =============================================
    # РАБОТА С ОБРАЗОМ ДИСКА
    # =============================================
    def set_disk_image(self, path, size_mb=32):
        """Установить образ диска.
        Если файл не существует или меньше нужного размера — создаётся пустой образ."""
        self.disk_file = path
        target_size = size_mb * 1024 * 1024
        
        # Создаём файл, если его нет ИЛИ он слишком мал
        need_create = False
        if not os.path.exists(path):
            need_create = True
        elif os.path.getsize(path) < target_size:
            need_create = True
        
        if need_create:
            with open(path, 'wb') as f:
                f.write(b'\x00' * target_size)
        
        self.disk_size = os.path.getsize(path)
        self.total_sectors = self.disk_size // self.SECTOR_SIZE
        self.status = self.STATUS_DRDY

    def _read_sector(self, lba):
        """Чтение сектора с диска"""
        if lba >= self.total_sectors:
            return None
        
        offset = lba * self.SECTOR_SIZE
        try:
            with open(self.disk_file, 'rb') as f:
                f.seek(offset)
                return bytearray(f.read(self.SECTOR_SIZE))
        except OSError:
            return None

    def _write_sector(self, lba, data):
        """Запись сектора на диск"""
        if lba >= self.total_sectors:
            return False
        
        offset = lba * self.SECTOR_SIZE
        try:
            with open(self.disk_file, 'r+b') as f:
                f.seek(offset)
                f.write(data)
            return True
        except OSError:
            return False

    # =============================================
    # ВЫЧИСЛЕНИЕ LBA
    # =============================================
    def _get_lba(self):
        """Получить LBA адрес из регистров"""
        # LBA mode (бит 6 device_head = 1)
        if self.device_head & 0x40:
            lba = (self.lba_low & 0xFF) | \
                  ((self.lba_mid & 0xFF) << 8) | \
                  ((self.lba_high & 0xFF) << 16) | \
                  ((self.device_head & 0x0F) << 24)
            return lba
        else:
            # CHS mode не поддерживаем
            return 0

    # =============================================
    # IO ЧТЕНИЕ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # если устройство занято, возвращаем 0
            if self.busy:
                return 0x00
            if self.data_direction == 'read' and self.data_index < len(self.data_buffer):
                val = self.data_buffer[self.data_index]
                self.data_index += 1
                if self.data_index >= len(self.data_buffer):
                    self._after_sector_read()
                return val
            return 0x00
        elif offset == 1:
            return self.error_reg
        elif offset == 2:
            return self.sector_count
        elif offset == 3:
            return self.lba_low
        elif offset == 4:
            return self.lba_mid
        elif offset == 5:
            return self.lba_high
        elif offset == 6:
            return self.device_head
        elif offset == 7:
            # если устройство занято, возвращаем BSY
            if self.busy:
                return self.STATUS_BSY
            return self.status
        return 0xFF

    # =============================================
    # IO ЗАПИСЬ
    # =============================================
    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        value &= 0xFF

        if offset == 0:
            # Data Register (16-bit, но пишем по байтам)
            if self.data_direction == 'write' and self.data_index < len(self.data_buffer):
                self.data_buffer[self.data_index] = value
                self.data_index += 1
                
                # Если буфер заполнен полностью
                if self.data_index >= len(self.data_buffer):
                    self._complete_write()
            return

        elif offset == 1:
            # Features Register
            self.features_reg = value

        elif offset == 2:
            # Sector Count
            self.sector_count = value

        elif offset == 3:
            # LBA Low
            self.lba_low = value

        elif offset == 4:
            # LBA Mid
            self.lba_mid = value

        elif offset == 5:
            # LBA High
            self.lba_high = value

        elif offset == 6:
            # Device/Head
            self.device_head = value

        elif offset == 7:
            # Command Register
            self.command = value
            self._execute_command()

    # =============================================
    # ВЫПОЛНЕНИЕ КОМАНД
    # =============================================
    def _execute_command(self):
        """Выполнение команды"""
        self.error_reg = 0x00
        self.status = self.STATUS_BSY
         
        if self.command == self.CMD_IDENTIFY_DEVICE:
            self._cmd_identify()
        elif self.command in (self.CMD_READ_SECTORS, self.CMD_READ_SECTORS_NI):
            self._cmd_read_sectors()
        elif self.command in (self.CMD_WRITE_SECTORS, self.CMD_WRITE_SECTORS_NI):
            self._cmd_write_sectors()
        else:
            self.error_reg = self.ERROR_ABRT
            self.status = self.STATUS_DRDY | self.STATUS_ERR
            return
         
        # запуск эмуляции занятости
        if self.error_reg == 0:
            count = self.sector_count if self.sector_count > 0 else 256
            if self.command == self.CMD_IDENTIFY_DEVICE:
                cycles = 30
            else:
                cycles = count * 50  # 50 тактов на сектор
            generate_irq = self.command in (
                self.CMD_IDENTIFY_DEVICE,
                self.CMD_READ_SECTORS,
                self.CMD_WRITE_SECTORS
            )
            self._start_operation(cycles, self.status, generate_irq)

    def _cmd_identify(self):
        """IDENTIFY DEVICE (0xEC)"""
        # Формируем Identify данные (512 байт)
        identify_data = [0x00] * 512

        # Word 0: General configuration
        identify_data[0] = 0x84  # Fixed device, non-removable
        identify_data[1] = 0x8A

        # Words 1-2: Number of logical cylinders (не используется в LBA)
        identify_data[2] = 0x00
        identify_data[3] = 0x00

        # Word 49: Capabilities (LBA supported)
        identify_data[98] = 0x02  # LBA supported
        identify_data[99] = 0x00

        # Words 60-61: Total number of user addressable sectors (LBA)
        identify_data[120] = self.total_sectors & 0xFF
        identify_data[121] = (self.total_sectors >> 8) & 0xFF
        identify_data[122] = (self.total_sectors >> 16) & 0xFF
        identify_data[123] = (self.total_sectors >> 24) & 0xFF

        # Words 27-46: Model number (40 символов, big-endian)
        model = "CF-IDE Emulator                     "
        for i, ch in enumerate(model[:40]):
            identify_data[54 + i] = ord(ch)

        # Words 23-26: Firmware revision (8 символов)
        fw = "1.0     "
        for i, ch in enumerate(fw[:8]):
            identify_data[46 + i] = ord(ch)

        # Words 10-19: Serial number (20 символов)
        serial = "12345678901234567890"
        for i, ch in enumerate(serial[:20]):
            identify_data[20 + i] = ord(ch)

        # Устанавливаем буфер для чтения
        self.data_buffer = identify_data
        self.data_index = 0
        self.data_direction = 'read'
        self.status = self.STATUS_DRDY | self.STATUS_DRQ

    def _cmd_read_sectors(self):
        """READ SECTORS (0x20/0x21)"""
        lba = self._get_lba()
        count = self.sector_count
        if count == 0:
            count = 256
        if lba + count > self.total_sectors:
            self.error_reg = self.ERROR_IDNF
            self.status = self.STATUS_DRDY | self.STATUS_ERR
            return
        sector_data = self._read_sector(lba)
        if sector_data is None:
            self.error_reg = self.ERROR_IDNF
            self.status = self.STATUS_DRDY | self.STATUS_ERR
            return
        self.data_buffer = sector_data
        self.data_index = 0
        self.data_direction = 'read'
        self.data_count = count
        self.status = self.STATUS_DRDY | self.STATUS_DRQ

    def _cmd_write_sectors(self):
        """WRITE SECTORS (0x30/0x31)"""
        lba = self._get_lba()
        count = self.sector_count
        if count == 0:
            count = 256

        # Проверяем границы
        if lba + count > self.total_sectors:
            self.error_reg = self.ERROR_IDNF
            self.status = self.STATUS_DRDY | self.STATUS_ERR
            return

        # Подготавливаем буфер для записи
        self.data_buffer = [0x00] * self.SECTOR_SIZE
        self.data_index = 0
        self.data_direction = 'write'
        self.data_count = count
        self.status = self.STATUS_DRDY | self.STATUS_DRQ

    def _complete_write(self):
        """Завершение записи сектора"""
        lba = self._get_lba()
        self._write_sector(lba, bytes(self.data_buffer))
        self.data_count -= 1
        if self.data_count > 0:
            # Увеличиваем LBA и готовим буфер для следующего сектора
            lba += 1
            self.lba_low = lba & 0xFF
            self.lba_mid = (lba >> 8) & 0xFF
            self.lba_high = (lba >> 16) & 0xFF
            self.sector_count = self.data_count
            self.data_buffer = [0x00] * self.SECTOR_SIZE
            self.data_index = 0
            self.status = self.STATUS_DRDY | self.STATUS_DRQ
        else:
            # Все секторы записаны
            self.data_direction = None
            self.status = self.STATUS_DRDY

        # Прерывание для команды с прерыванием
        if self.command in (self.CMD_WRITE_SECTORS, self.CMD_WRITE_SECTORS_NI) and self.on_irq:
            self.on_irq(True)

    def _after_sector_read(self):
        """После чтения всех байт сектора — загрузить следующий или завершить"""
        self.data_count -= 1
        if self.data_count > 0:
            # Увеличиваем LBA
            lba = self._get_lba() + 1
            self.lba_low = lba & 0xFF
            self.lba_mid = (lba >> 8) & 0xFF
            self.lba_high = (lba >> 16) & 0xFF
            self.sector_count = self.data_count
            # Загружаем следующий сектор
            sector_data = self._read_sector(lba)
            if sector_data is not None:
                self.data_buffer = sector_data
                self.data_index = 0
                self.status = self.STATUS_DRDY | self.STATUS_DRQ
            else:
                self.data_direction = None
                self.status &= ~self.STATUS_DRQ
                self.status |= self.STATUS_DRDY
        else:
            self.data_direction = None
            self.status &= ~self.STATUS_DRQ
            self.status |= self.STATUS_DRDY

    # =============================================
    # ЭМУЛЯЦИЯ ЗАНЯТОСТИ (итерация 10.3)
    # =============================================
    def set_emulate_delay(self, enabled):
        """Включить/выключить эмуляцию задержки операций"""
        self.emulate_delay = enabled

    def _start_operation(self, cycles, final_status=None, generate_irq=True):
        """Запуск операции с задержкой (эмуляция IORDY).
        Если emulate_delay выключен, операция завершается мгновенно."""
        if not self.emulate_delay:
            # Мгновенное выполнение: статус уже установлен командой
            if generate_irq and self.on_irq:
                self.on_irq(True)
            return
        # Сохраняем финальный статус (уже установлен командой)
        self._pending_status = final_status if final_status is not None else self.status
        self._pending_irq = generate_irq
        # Устанавливаем BSY
        self.busy = True
        self.busy_cycles = cycles
        self.status = self.STATUS_BSY
        # Активируем WAIT
        if self.on_wait:
            self.on_wait(True)

    def tick(self, cycles=1):
        """Вызывается каждый такт. Обработка занятости."""
        if not self.busy:
            return
        self.busy_cycles -= cycles
        if self.busy_cycles <= 0:
            self.busy = False
            self.status = self._pending_status
            # Снимаем WAIT
            if self.on_wait:
                self.on_wait(False)
            # Генерируем IRQ по завершении
            if self._pending_irq and self.on_irq:
                self.on_irq(True)
            self._pending_irq = False

    def is_busy(self):
        """Проверка занятости устройства"""
        return self.busy

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "disk_file": self.disk_file,
            "disk_size_mb": self.disk_size // (1024 * 1024),
            "total_sectors": self.total_sectors,
            "lba": self._get_lba(),
            "sector_count": self.sector_count,
            "status": f"0x{self.status:02X}",
            "error": f"0x{self.error_reg:02X}",
            "busy": bool(self.status & self.STATUS_BSY),
            "ready": bool(self.status & self.STATUS_DRDY),
            "data_request": bool(self.status & self.STATUS_DRQ),
            "data_direction": self.data_direction,
            "data_index": self.data_index,
        }
