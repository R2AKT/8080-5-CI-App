"""
8276 — CRT-контроллер (контроллер дисплея).
Итерация E5: расширенные IO-устройства.

Возможности:
- Управление символьным дисплеем (до 128×64 символов)
- Программируемые параметры: символы в строке, строки на экране,
  размер символа (пиксели), вертикальный/горизонтальный sync
- Встроенный DMA-запрос (DRQ) для чтения видеопамяти
- Прерывание IRQ: конец кадра (VBLANK), световое перо
- Атрибуты символов: инверсия, подчёркивание, мигание

Регистры (2 порта):
  offset 0 (Data):
    Чтение  — данные видеопамяти / параметры
    Запись  — данные видеопамяти / параметры
  offset 1 (Command/Status):
    Чтение  — Status Register
    Запись  — Command Register
"""
from .iodevice import IODevice
from .chargen import get_char_generator

class I8276(IODevice):
    """8276 — CRT-контроллер"""

    # === Команды (старшие биты Command Register) ===
    CMD_RESET           = 0x00  # 00000000: сброс
    CMD_INITIALIZE      = 0x01  # 00000001: инициализация
    CMD_ENABLE_DISPLAY  = 0x02  # 00000010: включить дисплей
    CMD_DISABLE_DISPLAY = 0x03  # 00000011: выключить дисплей
    CMD_INTERRUPT       = 0x04  # 00000100: запрос прерывания
    CMD_DMA_ENABLE      = 0x05  # 00000101: включить DMA
    CMD_DMA_DISABLE     = 0x06  # 00000110: выключить DMA
    CMD_PRESET_COUNTERS = 0x07  # 00000111: сброс счётчиков
    CMD_READ_LPEN       = 0x08  # 00001000: чтение светового пера

    # === Биты Status Register ===
    STATUS_VBLANK       = 0x80  # Бит 7: конец кадра
    STATUS_LPEN         = 0x40  # Бит 6: световое перо
    STATUS_DMA_REQUEST  = 0x20  # Бит 5: запрос DMA
    STATUS_FIFO_EMPTY   = 0x10  # Бит 4: FIFO пуст
    STATUS_DISPLAY_ON   = 0x08  # Бит 3: дисплей включён
    STATUS_HBLANK       = 0x04  # Бит 2: горизонтальный blank
    STATUS_VERT_COUNT   = 0x02  # Бит 1: счётчик строк
    STATUS_HORZ_COUNT   = 0x01  # Бит 0: счётчик символов

    def __init__(self, base_port, name="I8276"):
        super().__init__(base_port, 2, name)
        self.reset()
        
        # Знакогенератор
        from .chargen import CharGenerator
        self.char_gen = CharGenerator()
        self.font_data = dict(self.char_gen.fonts[8])  # По умолчанию 8×8
        
        # Callback прерывания: on_irq(active)
        self.on_irq = None
        # Callback DMA-запроса: on_drq(active)
        self.on_drq = None
        # Callback обновления дисплея: on_display_update(char, attr, x, y)
        self.on_display_update = None

    def reset(self):
        """Сброс контроллера"""
        # Параметры дисплея (программируемые)
        self.chars_per_line = 80     # Символов в строке (1-80)
        self.lines_per_screen = 24   # Строк на экране (1-64)
        self.char_width = 8          # Ширина символа в пикселях
        self.char_height = 16        # Высота символа в пикселях
        self.cursor_x = 0            # Позиция курсора X
        self.cursor_y = 0            # Позиция курсора Y
        self.cursor_enabled = True   # Курсор виден
        self.cursor_blink = True     # Курсор мигает

        # Видеопамять: {offset: (char, attr)}
        self.video_ram = {}
        self.video_addr = 0          # Текущий адрес видеопамяти

        # Состояние
        self.display_enabled = False
        self.dma_enabled = False
        self.initialized = False

        # Прерывания
        self.irq_flag = False
        self.vblank_flag = False
        self.lpen_flag = False

        # Световое перо
        self.lpen_x = 0
        self.lpen_y = 0

        # DMA
        self.drq_flag = False

        # Параметры инициализации (принимаются последовательно)
        self._init_sequence = []
        self._init_count = 0

    # =============================================
    # IO ЧТЕНИЕ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Чтение видеопамяти
            return self._read_video_ram()
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
            # Запись видеопамяти или параметров инициализации
            self._write_data(value)
        elif offset == 1:
            # Запись Command Register
            self._write_command(value)

    # =============================================
    # ВИДЕОПАМЯТЬ
    # =============================================
    def _read_video_ram(self):
        """Чтение из видеопамяти"""
        if self.video_addr in self.video_ram:
            char, attr = self.video_ram[self.video_addr]
            self.video_addr += 1
            return char
        return 0x00

    def _write_data(self, value):
        """Запись данных (видеопамять или параметры инициализации)"""
        if not self.initialized:
            # Принимаем параметры инициализации
            self._init_sequence.append(value)
            self._init_count += 1
            if self._init_count >= 4:
                self._apply_init_params()
            return
        # Запись в видеопамять
        self.video_ram[self.video_addr] = (value, 0x00)
        self.video_addr += 1
        # Уведомляем об обновлении
        if self.on_display_update:
            x = self.video_addr % self.chars_per_line
            y = self.video_addr // self.chars_per_line
            self.on_display_update(value, 0x00, x, y)

    def _apply_init_params(self):
        """Применить параметры инициализации"""
        if len(self._init_sequence) >= 4:
            self.chars_per_line = self._init_sequence[0] or 80
            self.lines_per_screen = self._init_sequence[1] or 24
            self.char_width = self._init_sequence[2] or 8
            self.char_height = self._init_sequence[3] or 16
        self.initialized = True
        self._init_sequence = []
        self._init_count = 0

    # =============================================
    # КОМАНДЫ
    # =============================================
    def _write_command(self, value):
        """Запись Command Register"""
        if value == self.CMD_RESET:
            self.reset()

        elif value == self.CMD_INITIALIZE:
            self.initialized = False
            self._init_sequence = []
            self._init_count = 0

        elif value == self.CMD_ENABLE_DISPLAY:
            self.display_enabled = True

        elif value == self.CMD_DISABLE_DISPLAY:
            self.display_enabled = False

        elif value == self.CMD_INTERRUPT:
            # Запрос прерывания (от светового пера)
            self.irq_flag = True
            if self.on_irq:
                self.on_irq(True)

        elif value == self.CMD_DMA_ENABLE:
            self.dma_enabled = True
            self.drq_flag = True
            if self.on_drq:
                self.on_drq(True)

        elif value == self.CMD_DMA_DISABLE:
            self.dma_enabled = False
            self.drq_flag = False
            if self.on_drq:
                self.on_drq(False)

        elif value == self.CMD_PRESET_COUNTERS:
            self.video_addr = 0
            self.cursor_x = 0
            self.cursor_y = 0

        elif value == self.CMD_READ_LPEN:
            # Чтение светового пера — данные читаются из порта 0
            pass

    # =============================================
    # STATUS REGISTER
    # =============================================
    def _get_status(self):
        """Получить Status Register"""
        status = 0
        if self.vblank_flag:
            status |= self.STATUS_VBLANK
        if self.lpen_flag:
            status |= self.STATUS_LPEN
        if self.drq_flag:
            status |= self.STATUS_DMA_REQUEST
        if not self.video_ram:
            status |= self.STATUS_FIFO_EMPTY
        if self.display_enabled:
            status |= self.STATUS_DISPLAY_ON
        return status

    # =============================================
    # ВНЕШНИЕ СОБЫТИЯ
    # =============================================
    def vertical_blank(self):
        """Событие конца кадра (VBLANK).
        Вызывается извне (например, по таймеру).
        """
        self.vblank_flag = True
        self.irq_flag = True
        if self.on_irq:
            self.on_irq(True)

    def light_pen(self, x, y):
        """Событие светового пера"""
        self.lpen_x = x
        self.lpen_y = y
        self.lpen_flag = True

    def dma_acknowledge(self):
        """Подтверждение DMA (от контроллера DMA)"""
        self.drq_flag = False
        if self.on_drq:
            self.on_drq(False)

    def acknowledge_interrupt(self):
        """Подтверждение прерывания (сброс флага)"""
        self.irq_flag = False
        self.vblank_flag = False
        self.lpen_flag = False

    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.irq_flag

    def has_drq(self):
        """Есть ли активный DMA-запрос"""
        return self.drq_flag

    # =============================================
    # УТИЛИТЫ ДЛЯ GUI
    # =============================================
    def get_display_text(self):
        """Получить текст дисплея для отображения в GUI"""
        lines = []
        for y in range(self.lines_per_screen):
            line = ""
            for x in range(self.chars_per_line):
                offset = y * self.chars_per_line + x
                if offset in self.video_ram:
                    char, attr = self.video_ram[offset]
                    if 32 <= char <= 126:
                        line += chr(char)
                    else:
                        line += "."
                else:
                    line += " "
            lines.append(line)
        return lines

    def set_character(self, x, y, char, attr=0x00):
        """Установить символ в видеопамять"""
        offset = y * self.chars_per_line + x
        self.video_ram[offset] = (char & 0xFF, attr & 0xFF)

    def get_character(self, x, y):
        """Получить символ из видеопамяти"""
        offset = y * self.chars_per_line + x
        if offset in self.video_ram:
            return self.video_ram[offset]
        return (0x00, 0x00)

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "chars_per_line": self.chars_per_line,
            "lines_per_screen": self.lines_per_screen,
            "char_width": self.char_width,
            "char_height": self.char_height,
            "cursor_x": self.cursor_x,
            "cursor_y": self.cursor_y,
            "display_enabled": self.display_enabled,
            "dma_enabled": self.dma_enabled,
            "initialized": self.initialized,
            "video_addr": self.video_addr,
            "video_ram_size": len(self.video_ram),
            "irq_flag": self.irq_flag,
            "drq_flag": self.drq_flag,
            "status": f"0x{self._get_status():02X}",
        }

    def load_font_from_file(self, path):
        """Загрузить шрифт знакогенератора из raw-файла."""
        return self.char_gen.load_from_file(path)

    def get_char_bitmap(self, code):
        """Код символа → пиксельная карта (через знакогенератор)."""
        h = getattr(self, 'char_height', 8)
        return self.char_gen.get_bitmap(code, h)
