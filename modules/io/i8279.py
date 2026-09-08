"""
8279 (КР580ВВ79) — программируемый контроллер клавиатуры/дисплея.
Итерация E5: расширенные IO-устройства.

Возможности:
- Клавиатура: матричная до 64 клавиш (8x8), FIFO на 8 байт
- Дисплей: RAM на 16 байт (до 16 семисегментных цифр)
- Режимы: 2-клавишный lockout, N-key rollover
- Сканирование: encoded / decoded
- Прерывание IRQ при нажатии клавиши

Регистры (2 порта):
  offset 0 (Data):
    Чтение  — FIFO клавиатуры
    Запись  — RAM дисплея
  offset 1 (Control/Status):
    Чтение  — Status Register
    Запись  — Command Register
"""
from .iodevice import IODevice
from collections import deque


class I8279(IODevice):
    """8279 — контроллер клавиатуры/дисплея"""

    # === Команды (старшие биты Command Register) ===
    CMD_KBD_DISP_MODE   = 0x00  # 000DDKKK: режим клавиатуры/дисплея
    CMD_PROGRAM_CLOCK   = 0x20  # 001PPPPP: программирование частоты
    CMD_READ_FIFO       = 0x40  # 010SSRRR: чтение FIFO/датчиков
    CMD_READ_DISP_RAM   = 0x60  # 011DDRRR: чтение RAM дисплея
    CMD_WRITE_DISP_RAM  = 0x80  # 100DDRRR: запись RAM дисплея
    CMD_CLEAR_DISP      = 0xC0  # 110DDKKK: очистка дисплея
    CMD_CLEAR_KBD       = 0xD0  # 11010KKK: очистка клавиатуры
    CMD_END_INTERRUPT   = 0xE8  # 11101000: конец прерывания
    CMD_SET_INTERRUPT   = 0xF0  # 11110000: установка прерывания

    # === Биты Status Register ===
    STATUS_FIFO_COUNT_MASK = 0xF0  # Биты 7-4: количество в FIFO
    STATUS_SENSOR_ERROR    = 0x08  # Бит 3: S/E
    STATUS_OUT_OF_RANGE    = 0x04  # Бит 2: O
    STATUS_FIFO_FULL       = 0x02  # Бит 1: F
    STATUS_DISP_UNAVAIL    = 0x01  # Бит 0: DU

    def __init__(self, base_port, name="I8279"):
        super().__init__(base_port, 2, name)
        self.reset()
        # Callback прерывания: on_irq(active)
        self.on_irq = None
        # Callback обновления дисплея: on_display_update(display_data)
        self.on_display_update = None

    def reset(self):
        """Сброс контроллера"""
        # Клавиатура
        self.key_fifo = deque(maxlen=8)   # FIFO на 8 байт
        self.key_fifo_clear()
        # Дисплей
        self.display_ram = [0x00] * 16    # RAM дисплея на 16 байт
        self.display_addr = 0             # Текущий адрес записи
        self.display_auto_inc = True      # Автоинкремент адреса
        # Режимы
        self.kbd_mode = 0       # Режим клавиатуры (0-3)
        self.scan_mode = 0      # Режим сканирования (0=encoded, 1=decoded)
        self.disp_mode = 0      # Режим дисплея (0-3)
        self.clock_prescaler = 31  # Делитель частоты (по умолчанию 31)
        # Прерывания
        self.irq_flag = False
        self.irq_enabled = False
        # Флаги статуса
        self.sensor_error = False
        self.out_of_range = False
        # Состояние команды
        self._pending_cmd = None

    # =============================================
    # IO ЧТЕНИЕ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Чтение FIFO клавиатуры
            return self._read_fifo()
        elif offset == 1:
            # Чтение Status Register
            return self._get_status()
        return 0xFF

    # =============================================
    # IO ЗАПИСЬ
    # =============================================
    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        if offset == 0:
            # Запись RAM дисплея
            self._write_display_ram(value)
        elif offset == 1:
            # Запись Command Register
            self._write_command(value)

    # =============================================
    # FIFO КЛАВИАТУРЫ
    # =============================================
    def _read_fifo(self):
        """Чтение из FIFO клавиатуры"""
        if self.key_fifo:
            data = self.key_fifo.popleft()
            # Если FIFO опустел — сбрасываем IRQ
            if not self.key_fifo:
                self.irq_flag = False
            return data
        return 0x00

    def key_fifo_clear(self):
        """Очистка FIFO клавиатуры"""
        self.key_fifo.clear()
        self.irq_flag = False
        self.out_of_range = False

    # =============================================
    # RAM ДИСПЛЕЯ
    # =============================================
    def _write_display_ram(self, value):
        """Запись в RAM дисплея"""
        if 0 <= self.display_addr < 16:
            self.display_ram[self.display_addr] = value & 0xFF
        # Автоинкремент адреса
        if self.display_auto_inc:
            self.display_addr = (self.display_addr + 1) & 0x0F
        # Уведомляем об обновлении дисплея
        if self.on_display_update:
            self.on_display_update(list(self.display_ram))

    def _read_display_ram(self, addr):
        """Чтение из RAM дисплея"""
        if 0 <= addr < 16:
            return self.display_ram[addr]
        return 0x00

    # =============================================
    # КОМАНДЫ
    # =============================================
    def _write_command(self, value):
        """Запись Command Register"""
        cmd_type = value & 0xE0  # Старшие 3 бита определяют команду

        if cmd_type == self.CMD_KBD_DISP_MODE:
            # 000DDKKK: режим клавиатуры/дисплея
            self.kbd_mode = value & 0x03
            self.disp_mode = (value >> 2) & 0x03
            self.scan_mode = (value >> 4) & 0x01

        elif cmd_type == self.CMD_PROGRAM_CLOCK:
            # 001PPPPP: программирование частоты
            self.clock_prescaler = (value & 0x1F) or 31

        elif cmd_type == self.CMD_READ_FIFO:
            # 010SSRRR: чтение FIFO/датчиков
            # Устанавливаем адрес чтения FIFO (обычно игнорируется)
            pass

        elif cmd_type == self.CMD_READ_DISP_RAM:
            # 011DDRRR: чтение RAM дисплея
            self.display_addr = value & 0x0F
            self.display_auto_inc = bool(value & 0x10)

        elif cmd_type == self.CMD_WRITE_DISP_RAM:
            # 100DDRRR: запись RAM дисплея
            self.display_addr = value & 0x0F
            self.display_auto_inc = bool(value & 0x10)

        elif cmd_type == self.CMD_CLEAR_DISP:
            # 110DDKKK: очистка дисплея
            clear_mode = (value >> 2) & 0x03
            if clear_mode == 0:
                # Очистка всех цифр в 00
                self.display_ram = [0x00] * 16
            elif clear_mode == 1:
                # Очистка всех цифр в FF
                self.display_ram = [0xFF] * 16
            elif clear_mode == 2:
                # Очистка всех цифр в 00 (аналогично режиму 0)
                self.display_ram = [0x00] * 16
            # Бит K: очистка клавиатуры
            if value & 0x04:
                self.key_fifo_clear()
            self.display_addr = 0
            if self.on_display_update:
                self.on_display_update(list(self.display_ram))

            elif value == self.CMD_CLEAR_KBD:
                # 11010000: очистка клавиатуры (точное совпадение)
                self.key_fifo_clear()

        elif value == self.CMD_END_INTERRUPT:
            # 11101000: конец прерывания
            self.irq_flag = False
            if self.on_irq:
                self.on_irq(False)

        elif value == self.CMD_SET_INTERRUPT:
            # 11110000: установка прерывания
            self.irq_enabled = True

    # =============================================
    # STATUS REGISTER
    # =============================================
    def _get_status(self):
        """Получить Status Register"""
        status = 0
        # Биты 7-4: количество символов в FIFO
        fifo_count = min(len(self.key_fifo), 8)
        status |= (fifo_count << 4) & self.STATUS_FIFO_COUNT_MASK
        # Бит 3: Sensor Error
        if self.sensor_error:
            status |= self.STATUS_SENSOR_ERROR
        # Бит 2: Out-of-range
        if self.out_of_range:
            status |= self.STATUS_OUT_OF_RANGE
        # Бит 1: FIFO Full
        if len(self.key_fifo) >= 8:
            status |= self.STATUS_FIFO_FULL
        # Бит 0: Display Unavailable
        # DU=1 когда идёт запись в RAM дисплея (упрощённо: всегда 0)
        return status

    # =============================================
    # ВНЕШНИЕ СОБЫТИЯ (клавиатура)
    # =============================================
    def key_press(self, key_data):
        """Внешнее нажатие клавиши.
        key_data: байт с данными клавиши.
        Добавляет в FIFO и генерирует IRQ.
        """
        if len(self.key_fifo) < 8:
            self.key_fifo.append(key_data & 0xFF)
            # Генерируем прерывание
            self.irq_flag = True
            if self.on_irq:
                self.on_irq(True)
        else:
            # FIFO полон — устанавливаем флаг Out-of-range
            self.out_of_range = True

    def key_release(self, key_data):
        """Внешнее отпускание клавиши (для режимов с отслеживанием)"""
        # В большинстве режимов отпускание не генерирует событие
        pass

    def sensor_event(self, sensor_data, error=False):
        """Событие датчика (для режима Sensor Matrix)"""
        if error:
            self.sensor_error = True
            self.irq_flag = True
            if self.on_irq:
                self.on_irq(True)

    # =============================================
    # ПРЕРЫВАНИЯ
    # =============================================
    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.irq_flag

    def acknowledge_interrupt(self):
        """Подтверждение прерывания (сброс флага)"""
        self.irq_flag = False

    # =============================================
    # УТИЛИТЫ ДЛЯ GUI
    # =============================================
    def get_display_data(self):
        """Получить данные дисплея для отображения в GUI"""
        return list(self.display_ram)

    def get_fifo_contents(self):
        """Получить содержимое FIFO клавиатуры"""
        return list(self.key_fifo)

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "kbd_mode": self.kbd_mode,
            "disp_mode": self.disp_mode,
            "scan_mode": self.scan_mode,
            "fifo_count": len(self.key_fifo),
            "fifo_contents": [f"0x{b:02X}" for b in self.key_fifo],
            "display_ram": [f"0x{b:02X}" for b in self.display_ram],
            "display_addr": self.display_addr,
            "irq_flag": self.irq_flag,
            "status": f"0x{self._get_status():02X}",
        }
