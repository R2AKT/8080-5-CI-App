"""
8272 (КР580ВГ72) — контроллер гибких дисков (FDC).
Итерация E5: расширенные IO-устройства.

Возможности:
- Поддержка до 4 дисководов (A, B, C, D)
- FIFO для команд и результатов (16 байт)
- Команды: Read Data, Write Data, Seek, Recalibrate, Sense Status, Specify, Read ID, Format Track
- Прерывания (IRQ) при завершении операций
- DMA-запросы (DRQ) для передачи данных (эмуляция через PIO)
- Эмуляция данных дисков в памяти

Регистры (4 порта):
  offset 0: Digital Output Register (DOR) — запись
  offset 1: Main Status Register (MSR) — чтение
  offset 2: Data Register (FIFO) — чтение/запись
  offset 3: Digital Input Register (DIR) — чтение / Configuration Control Register (CCR) — запись

Формат данных диска:
  {(cylinder, head, sector): [512 байт]}
"""
from .iodevice import IODevice
from collections import deque


class I8272FDD:
    """Один дисковод (Floppy Disk Drive)"""
    
    def __init__(self, drive_num, name="FDD"):
        self.drive_num = drive_num
        self.name = f"{name}-{drive_num}"
        # Данные диска: {(cylinder, head, sector): [512 байт]}
        self.data = {}
        # Текущая позиция головки
        self.cylinder = 0
        self.head = 0
        self.sector = 1
        # Параметры дисковода
        self.max_cylinder = 79   # Количество цилиндров (0-79)
        self.max_head = 1        # Количество головок (0-1)
        self.sectors_per_track = 18  # Секторов на дорожку
        self.sector_size = 512   # Размер сектора в байтах
        # Флаги состояния
        self.ready = True
        self.write_protect = False
        self.track0 = True
        self.two_sided = True
        self.motor_on = False
    
    def read_sector(self, cylinder, head, sector):
        """Чтение сектора"""
        key = (cylinder, head, sector)
        if key in self.data:
            return self.data[key]
        return [0x00] * self.sector_size
    
    def write_sector(self, cylinder, head, sector, data):
        """Запись сектора"""
        if self.write_protect:
            return False
        key = (cylinder, head, sector)
        self.data[key] = list(data[:self.sector_size])
        return True
    
    def get_status(self):
        """Статус дисковода"""
        status = 0
        if not self.ready:
            status |= 0x80  # Not Ready
        if self.write_protect:
            status |= 0x40  # Write Protect
        if self.track0:
            status |= 0x10  # Track 0
        if self.two_sided:
            status |= 0x08  # Two Sided
        return status

    # =============================================
    # РАБОТА С ВНЕШНИМИ ОБРАЗАМИ ДИСКОВ
    # =============================================
    
    # Стандартные форматы дискет
    FORMATS = {
        368640:  (40, 2, 9, 512),   # 5.25" 360 КБ
        737280:  (80, 2, 9, 512),   # 3.5" 720 КБ
        1228800: (80, 2, 15, 512),  # 5.25" 1.2 МБ
        1474560: (80, 2, 18, 512),  # 3.5" 1.44 МБ
    }
    
    def format_disk(self, tracks=None, heads=None, sectors_per_track=None, sector_size=None):
        """Форматирование диска с заданными параметрами.
        Если параметры не указаны, используются текущие."""
        if tracks is not None:
            self.max_cylinder = tracks - 1
        if heads is not None:
            self.max_head = heads - 1
        if sectors_per_track is not None:
            self.sectors_per_track = sectors_per_track
        if sector_size is not None:
            self.sector_size = sector_size
        
        self.data = {}
        for cyl in range(self.max_cylinder + 1):
            for head in range(self.max_head + 1):
                for sec in range(1, self.sectors_per_track + 1):
                    self.data[(cyl, head, sec)] = [0x00] * self.sector_size
    
    def load_from_file(self, path):
        """Загрузка raw-образа диска из файла.
        Формат определяется автоматически по размеру файла.
        Возвращает True при успехе."""
        try:
            with open(path, 'rb') as f:
                raw = f.read()
            
            size = len(raw)
            if size == 0:
                return False
            
            # Определяем формат по размеру
            if size in self.FORMATS:
                tracks, heads, sectors, sec_size = self.FORMATS[size]
                self.max_cylinder = tracks - 1
                self.max_head = heads - 1
                self.sectors_per_track = sectors
                self.sector_size = sec_size
            else:
                # Неизвестный формат — пробуем определить
                # Предполагаем 2 головки, 512 байт на сектор
                sec_size = 512
                if size % sec_size != 0:
                    return False
                total_sectors = size // sec_size
                # Пытаемся угадать геометрию
                heads = 2
                if total_sectors % heads != 0:
                    heads = 1
                track_sectors = total_sectors // heads
                # Ищем подходящее количество дорожек
                tracks = 80
                if track_sectors % tracks != 0:
                    tracks = 40
                if track_sectors % tracks != 0:
                    return False
                sectors = track_sectors // tracks
                
                self.max_cylinder = tracks - 1
                self.max_head = heads - 1
                self.sectors_per_track = sectors
                self.sector_size = sec_size
            
            # Загружаем данные
            self.data = {}
            offset = 0
            for cyl in range(self.max_cylinder + 1):
                for head in range(self.max_head + 1):
                    for sec in range(1, self.sectors_per_track + 1):
                        sector_data = list(raw[offset:offset + self.sector_size])
                        if len(sector_data) < self.sector_size:
                            sector_data.extend([0x00] * (self.sector_size - len(sector_data)))
                        self.data[(cyl, head, sec)] = sector_data
                        offset += self.sector_size
            
            self.ready = True
            return True
        except (OSError, ValueError):
            return False
    
    def save_to_file(self, path):
        """Сохранение raw-образа диска в файл.
        Возвращает True при успехе."""
        try:
            raw = bytearray()
            for cyl in range(self.max_cylinder + 1):
                for head in range(self.max_head + 1):
                    for sec in range(1, self.sectors_per_track + 1):
                        key = (cyl, head, sec)
                        if key in self.data:
                            raw.extend(self.data[key])
                        else:
                            raw.extend([0x00] * self.sector_size)
            
            with open(path, 'wb') as f:
                f.write(raw)
            return True
        except OSError:
            return False
    
    def get_geometry(self):
        """Геометрия диска для отладки"""
        return {
            "tracks": self.max_cylinder + 1,
            "heads": self.max_head + 1,
            "sectors_per_track": self.sectors_per_track,
            "sector_size": self.sector_size,
            "total_sectors": (self.max_cylinder + 1) * (self.max_head + 1) * self.sectors_per_track,
            "total_bytes": (self.max_cylinder + 1) * (self.max_head + 1) * self.sectors_per_track * self.sector_size,
        }

class I8272(IODevice):
    """8272 FDC — контроллер гибких дисков"""
    
    # === Команды ===
    CMD_READ_DATA           = 0x06  # Чтение данных
    CMD_WRITE_DATA          = 0x05  # Запись данных
    CMD_READ_DELETED_DATA   = 0x0C  # Чтение удалённых данных
    CMD_WRITE_DELETED_DATA  = 0x09  # Запись удалённых данных
    CMD_READ_TRACK          = 0x02  # Чтение дорожки
    CMD_READ_ID             = 0x0A  # Чтение ID сектора
    CMD_FORMAT_TRACK        = 0x0D  # Форматирование дорожки
    CMD_SEEK                = 0x0F  # Позиционирование головки
    CMD_RECALIBRATE         = 0x07  # Рекалибровка
    CMD_SENSE_INT_STATUS    = 0x08  # Статус прерывания
    CMD_SENSE_DRIVE_STATUS  = 0x04  # Статус дисковода
    CMD_SPECIFY             = 0x03  # Установка параметров
    CMD_VERSION             = 0x10  # Версия контроллера (8272A)
    
    # === Состояния контроллера ===
    STATE_IDLE      = 0  # Ожидание команды
    STATE_COMMAND   = 1  # Приём параметров команды
    STATE_EXECUTION = 2  # Выполнение команды
    STATE_RESULT    = 3  # Возврат результата
    
    # === Биты Main Status Register ===
    MSR_DRIVE_BUSY_MASK = 0x0F  # Биты 0-3: дисководы заняты
    MSR_BUSY            = 0x10  # Бит 4: контроллер занят
    MSR_NDMA            = 0x20  # Бит 5: Non-DMA mode
    MSR_DIO             = 0x40  # Бит 6: направление передачи (1=чтение из FDC)
    MSR_RQM             = 0x80  # Бит 7: запрос данных
    
    def __init__(self, base_port, name="I8272"):
        super().__init__(base_port, 4, name)
        self.reset()
        # Callback для прерываний
        self.on_irq = None  # callback(active)
        # Callback для DMA-запросов
        self.on_drq = None  # callback(active)
        # Callback для передачи данных (внешний буфер)
        self.on_data_request = None  # callback() -> byte
    
    def reset(self):
        """Сброс контроллера"""
        # FIFO
        self.fifo = deque(maxlen=16)
        # Состояние
        self.state = self.STATE_IDLE
        self.current_command = 0
        self.command_params = []
        self.command_param_count = 0
        self.result_data = []
        self.result_index = 0
        # Дисководы
        self.drives = [I8272FDD(i) for i in range(4)]
        self.selected_drive = 0
        # Флаги
        self.irq_flag = False
        self.drq_flag = False
        self.pending_irq = False
        # Регистры
        self.dor = 0x00  # Digital Output Register
        # Статусы (для Sense Interrupt Status)
        self.status0 = 0x00
        self.status1 = 0x00
        self.status2 = 0x00
        self.status_cylinder = 0
        self.status_head = 0
        self.status_sector = 0
        # Параметры Specify
        self.srt = 0  # Step Rate Time
        self.hut = 0  # Head Unload Time
        self.hlt = 0  # Head Load Time
        self.nd = 0   # Non-DMA mode (1=PIO, 0=DMA)
        # Данные для передачи (PIO mode)
        self.transfer_buffer = []
        self.transfer_index = 0
    
    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # DOR только запись — возврат 0xFF
            return 0xFF
        elif offset == 1:
            # Main Status Register
            return self._get_msr()
        elif offset == 2:
            # Data Register (FIFO)
            return self._read_fifo()
        elif offset == 3:
            # Digital Input Register
            return 0x00
        return 0xFF
    
    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        if offset == 0:
            # Digital Output Register
            self._write_dor(value)
        elif offset == 1:
            # Reserved
            pass
        elif offset == 2:
            # Data Register (FIFO)
            self._write_fifo(value)
        elif offset == 3:
            # Configuration Control Register
            pass
    
    # =============================================
    # MAIN STATUS REGISTER
    # =============================================
    def _get_msr(self):
        """Main Status Register"""
        msr = 0
        # Биты 0-3: дисководы заняты
        if self.state == self.STATE_EXECUTION:
            msr |= (1 << self.selected_drive)
        # Бит 4: контроллер занят
        if self.state in (self.STATE_COMMAND, self.STATE_EXECUTION, self.STATE_RESULT):
            msr |= self.MSR_BUSY
        # Бит 5: Non-DMA mode
        if self.nd:
            msr |= self.MSR_NDMA
        # Бит 6: направление передачи
        if self.state == self.STATE_RESULT:
            msr |= self.MSR_DIO  # Чтение из FDC
        # Бит 7: запрос данных
        if self.state in (self.STATE_COMMAND, self.STATE_RESULT):
            msr |= self.MSR_RQM
        elif self.state == self.STATE_EXECUTION and self.nd:
            msr |= self.MSR_RQM
        return msr
    
    # =============================================
    # DIGITAL OUTPUT REGISTER
    # =============================================
    def _write_dor(self, value):
        """Digital Output Register"""
        old_dor = self.dor
        self.dor = value & 0xFF
        self.selected_drive = value & 0x03
        # Бит 2: Reset (0 = reset, 1 = normal)
        if not (value & 0x04):
            if old_dor & 0x04:  # Был в normal mode, теперь reset
                self.reset()
                return
        # Бит 3: DMA/INT enable
        # Биты 4-7: моторы дисководов
        for i in range(4):
            self.drives[i].motor_on = bool(value & (0x10 << i))
    
    # =============================================
    # FIFO
    # =============================================
    def _read_fifo(self):
        """Чтение из FIFO"""
        if self.state == self.STATE_RESULT and self.result_index < len(self.result_data):
            data = self.result_data[self.result_index]
            self.result_index += 1
            if self.result_index >= len(self.result_data):
                self.state = self.STATE_IDLE
                self.result_data = []
                self.result_index = 0
            return data
        elif self.state == self.STATE_EXECUTION and self.nd:
            # PIO mode: чтение данных с диска
            if self.transfer_index < len(self.transfer_buffer):
                data = self.transfer_buffer[self.transfer_index]
                self.transfer_index += 1
                if self.transfer_index >= len(self.transfer_buffer):
                    self._complete_command()
                return data
        return 0xFF
    
    def _write_fifo(self, value):
        """Запись в FIFO"""
        if self.state == self.STATE_IDLE:
            # Новая команда
            self.current_command = value & 0x1F
            self.command_params = []
            self.command_param_count = self._get_param_count(self.current_command)
            if self.command_param_count == 0:
                self._execute_command()
            else:
                self.state = self.STATE_COMMAND
        elif self.state == self.STATE_COMMAND:
            self.command_params.append(value & 0xFF)
            if len(self.command_params) >= self.command_param_count:
                self._execute_command()
                # Если после выполнения state = EXECUTION, НЕ обрабатываем value как данные
                # (value был последним параметром команды, а не данными)
        elif self.state == self.STATE_EXECUTION and self.nd:
            # PIO mode: запись данных на диск
            if self.transfer_index < len(self.transfer_buffer):
                self.transfer_buffer[self.transfer_index] = value & 0xFF
                self.transfer_index += 1
                if self.transfer_index >= len(self.transfer_buffer):
                    self._complete_command()
    
    # =============================================
    # ПАРАМЕТРЫ КОМАНД
    # =============================================
    def _get_param_count(self, cmd):
        """Количество параметров для команды"""
        if cmd == self.CMD_SPECIFY:
            return 2
        elif cmd == self.CMD_SENSE_DRIVE_STATUS:
            return 1
        elif cmd in (self.CMD_WRITE_DATA, self.CMD_READ_DATA,
                     self.CMD_READ_DELETED_DATA, self.CMD_WRITE_DELETED_DATA,
                     self.CMD_READ_TRACK):
            return 8
        elif cmd == self.CMD_READ_ID:
            return 1
        elif cmd == self.CMD_FORMAT_TRACK:
            return 5
        elif cmd == self.CMD_SEEK:
            return 2
        elif cmd == self.CMD_RECALIBRATE:
            return 1
        elif cmd in (self.CMD_SENSE_INT_STATUS, self.CMD_VERSION):
            return 0
        return 0
    
    # =============================================
    # ВЫПОЛНЕНИЕ КОМАНД
    # =============================================
    def _execute_command(self):
        """Выполнение команды"""
        cmd = self.current_command
        
        if cmd == self.CMD_SPECIFY:
            self._cmd_specify()
        elif cmd == self.CMD_SENSE_DRIVE_STATUS:
            self._cmd_sense_drive_status()
        elif cmd == self.CMD_WRITE_DATA:
            self._cmd_write_data()
        elif cmd == self.CMD_READ_DATA:
            self._cmd_read_data()
        elif cmd == self.CMD_READ_ID:
            self._cmd_read_id()
        elif cmd == self.CMD_SEEK:
            self._cmd_seek()
        elif cmd == self.CMD_RECALIBRATE:
            self._cmd_recalibrate()
        elif cmd == self.CMD_SENSE_INT_STATUS:
            self._cmd_sense_int_status()
        elif cmd == self.CMD_FORMAT_TRACK:
            self._cmd_format_track()
        elif cmd == self.CMD_VERSION:
            self._cmd_version()
        else:
            # Неизвестная команда
            self.state = self.STATE_IDLE
    
    def _cmd_specify(self):
        """Specify: установка параметров"""
        p1 = self.command_params[0]
        p2 = self.command_params[1]
        self.srt = (p1 >> 4) & 0x0F  # Step Rate Time
        self.hut = p1 & 0x0F          # Head Unload Time
        self.hlt = (p2 >> 1) & 0x7F   # Head Load Time
        self.nd = p2 & 0x01           # Non-DMA mode
        self.state = self.STATE_IDLE
    
    def _cmd_sense_drive_status(self):
        """Sense Drive Status: статус дисковода"""
        drive = self.drives[self.selected_drive]
        status = drive.get_status()
        self.result_data = [status]
        self.result_index = 0
        self.state = self.STATE_RESULT
    
    def _cmd_write_data(self):
        """Write Data: запись данных на диск"""
        cylinder = self.command_params[1]
        head = self.command_params[2]
        sector = self.command_params[3]
        sector_size = 128 << (self.command_params[4] & 0x03)
        
        # Подготавливаем буфер для записи
        self.transfer_buffer = [0x00] * sector_size
        self.transfer_index = 0
        self.transfer_cylinder = cylinder
        self.transfer_head = head
        self.transfer_sector = sector
        self.transfer_size = sector_size
        
        if self.nd:
            # PIO mode: ждём данные от CPU
            self.state = self.STATE_EXECUTION
        else:
            # DMA mode: запрашиваем DRQ
            self.drq_flag = True
            if self.on_drq:
                self.on_drq(True)
            self.state = self.STATE_EXECUTION
    
    def _cmd_read_data(self):
        """Read Data: чтение данных с диска"""
        drive = self.drives[self.selected_drive]
        cylinder = self.command_params[1]
        head = self.command_params[2]
        sector = self.command_params[3]
        sector_size = 128 << (self.command_params[4] & 0x03)
        
        # Читаем сектор
        self.transfer_buffer = drive.read_sector(cylinder, head, sector)
        self.transfer_index = 0
        self.transfer_cylinder = cylinder
        self.transfer_head = head
        self.transfer_sector = sector
        self.transfer_size = sector_size
        
        if self.nd:
            # PIO mode: отдаём данные CPU
            self.state = self.STATE_EXECUTION
        else:
            # DMA mode: запрашиваем DRQ
            self.drq_flag = True
            if self.on_drq:
                self.on_drq(True)
            self.state = self.STATE_EXECUTION
    
    def _cmd_read_id(self):
        """Read ID: чтение ID сектора"""
        drive = self.drives[self.selected_drive]
        # Возвращаем ID текущего сектора
        self.result_data = [
            0x00,  # ST0
            0x00,  # ST1
            0x00,  # ST2
            drive.cylinder,
            drive.head,
            drive.sector,
            0x02,  # N (размер сектора: 512 байт)
        ]
        self.result_index = 0
        self.state = self.STATE_RESULT
    
    def _cmd_seek(self):
        """Seek: позиционирование головки"""
        drive = self.drives[self.selected_drive]
        cylinder = self.command_params[1]
        drive.cylinder = cylinder
        drive.track0 = (cylinder == 0)
        # Сохраняем цилиндр для Sense Interrupt Status
        self.status_cylinder = cylinder
        # Генерируем прерывание
        self.pending_irq = True
        self.status0 = 0x20  # Seek End
        self.state = self.STATE_IDLE
    
    def _cmd_recalibrate(self):
        """Recalibrate: рекалибровка на цилиндр 0"""
        drive = self.drives[self.selected_drive]
        drive.cylinder = 0
        drive.track0 = True
        # Сохраняем цилиндр для Sense Interrupt Status
        self.status_cylinder = 0
        # Генерируем прерывание
        self.pending_irq = True
        self.status0 = 0x20  # Seek End
        self.state = self.STATE_IDLE
    
    def _cmd_sense_int_status(self):
        """Sense Interrupt Status: статус прерывания"""
        if self.pending_irq:
            self.result_data = [self.status0, self.status_cylinder]
            self.pending_irq = False
            self.status0 = 0x00
        else:
            # Нет прерывания — возвращаем 0x80 (Invalid Command)
            self.result_data = [0x80]
        self.result_index = 0
        self.state = self.STATE_RESULT
    
    def _cmd_format_track(self):
        """Format Track: форматирование дорожки"""
        drive = self.drives[self.selected_drive]
        cylinder = drive.cylinder
        head = self.command_params[2] if len(self.command_params) > 2 else 0
        
        # Форматируем дорожку
        for sec in range(1, drive.sectors_per_track + 1):
            drive.data[(cylinder, head, sec)] = [0x00] * drive.sector_size
        
        # Генерируем прерывание
        self.pending_irq = True
        self.status0 = 0x00  # Success
        self.state = self.STATE_IDLE
    
    def _cmd_version(self):
        """Version: версия контроллера (только 8272A)"""
        # 0x90 = 8272A, 0x80 = 8272
        self.result_data = [0x90]
        self.result_index = 0
        self.state = self.STATE_RESULT
    
    def _complete_command(self):
        """Завершение команды передачи данных"""
        drive = self.drives[self.selected_drive]
        
        if self.current_command == self.CMD_WRITE_DATA:
            # Записываем буфер на диск
            success = drive.write_sector(
                self.transfer_cylinder,
                self.transfer_head,
                self.transfer_sector,
                self.transfer_buffer
            )
            self.status0 = 0x00 if success else 0x40  # 0x40 = Write Protect
            self.status1 = 0x00
            self.status2 = 0x00
        elif self.current_command == self.CMD_READ_DATA:
            self.status0 = 0x00  # Success
            self.status1 = 0x00
            self.status2 = 0x00
        
        # Сохраняем позицию для результата
        self.status_cylinder = getattr(self, 'transfer_cylinder', 0)
        self.status_head = getattr(self, 'transfer_head', 0)
        self.status_sector = getattr(self, 'transfer_sector', 0)
        
        # Возвращаем результат (7 байт)
        self.result_data = [
            self.status0,  # ST0
            self.status1,  # ST1
            self.status2,  # ST2
            self.status_cylinder,
            self.status_head,
            self.status_sector,
            0x02,  # N (размер сектора)
        ]
        self.result_index = 0
        self.state = self.STATE_RESULT
        
        # Генерируем прерывание
        self.pending_irq = True
        if self.on_irq:
            self.on_irq(True)
        
        # Сбрасываем DRQ
        self.drq_flag = False
        if self.on_drq:
            self.on_drq(False)
    
    # =============================================
    # ПРЕРЫВАНИЯ И DMA
    # =============================================
    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.pending_irq or self.irq_flag
    
    def acknowledge_interrupt(self):
        """Подтверждение прерывания"""
        self.irq_flag = False
        if self.on_irq:
            self.on_irq(False)
    
    def has_drq(self):
        """Есть ли активный DMA-запрос"""
        return self.drq_flag
    
    def dma_acknowledge(self):
        """Подтверждение DMA"""
        self.drq_flag = False
        if self.on_drq:
            self.on_drq(False)
    
    def dma_transfer_complete(self, data=None):
        """Завершение DMA-передачи (вызывается контроллером DMA)"""
        if self.current_command == self.CMD_WRITE_DATA:
            # Данные записаны на диск
            drive = self.drives[self.selected_drive]
            if data:
                drive.write_sector(
                    self.transfer_cylinder,
                    self.transfer_head,
                    self.transfer_sector,
                    data
                )
            self._complete_command()
        elif self.current_command == self.CMD_READ_DATA:
            # Данные прочитаны с диска
            self._complete_command()
    
    # =============================================
    # УТИЛИТЫ ДЛЯ РАБОТЫ С ДИСКАМИ
    # =============================================
    def insert_disk(self, drive_num, disk_data=None):
        """Вставить диск в дисковод"""
        if 0 <= drive_num < 4:
            drive = self.drives[drive_num]
            if disk_data:
                drive.data = disk_data
            else:
                drive.format_disk()
            drive.ready = True
    
    def eject_disk(self, drive_num):
        """Извлечь диск из дисковода"""
        if 0 <= drive_num < 4:
            drive = self.drives[drive_num]
            drive.data = {}
            drive.ready = False
    
    def get_disk_data(self, drive_num):
        """Получить данные диска"""
        if 0 <= drive_num < 4:
            return self.drives[drive_num].data
        return None
    
    # =============================================
    # РАБОТА С ВНЕШНИМИ ОБРАЗАМИ ДИСКОВ
    # =============================================
    
    def load_disk_image(self, drive_num, path):
        """Загрузить образ диска из файла в дисковод.
        Возвращает True при успехе."""
        if 0 <= drive_num < 4:
            return self.drives[drive_num].load_from_file(path)
        return False
    
    def save_disk_image(self, drive_num, path):
        """Сохранить образ диска из дисковода в файл.
        Возвращает True при успехе."""
        if 0 <= drive_num < 4:
            return self.drives[drive_num].save_to_file(path)
        return False
    
    def format_drive(self, drive_num, tracks=80, heads=2, sectors_per_track=18, sector_size=512):
        """Форматировать дисковод с заданными параметрами.
        Возвращает True при успехе."""
        if 0 <= drive_num < 4:
            drive = self.drives[drive_num]
            drive.format_disk(tracks, heads, sectors_per_track, sector_size)
            drive.ready = True
            return True
        return False
    
    def get_drive_geometry(self, drive_num):
        """Геометрия диска в дисководе"""
        if 0 <= drive_num < 4:
            return self.drives[drive_num].get_geometry()
        return None
    
    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "state": self.state,
            "current_command": f"0x{self.current_command:02X}",
            "selected_drive": self.selected_drive,
            "dor": f"0x{self.dor:02X}",
            "msr": f"0x{self._get_msr():02X}",
            "pending_irq": self.pending_irq,
            "drq_flag": self.drq_flag,
            "drives": [
                {
                    "ready": d.ready,
                    "cylinder": d.cylinder,
                    "head": d.head,
                    "write_protect": d.write_protect,
                    "motor_on": d.motor_on,
                }
                for d in self.drives
            ],
        }
