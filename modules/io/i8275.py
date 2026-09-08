"""
8275 (КР580ВГ75) — программируемый CRT-контроллер.
Итерация E5: расширенные IO-устройства.

Оригинал: Intel 8275. Советский аналог: КР580ВГ75.

Отличия от 8276:
- Один регистр параметров (вместо нескольких)
- Упрощённый набор команд
- Одинарный буфер параметров

Возможности:
- Управление символьным дисплеем (до 80 символов × 16 строк)
- Программируемые параметры: символы в строке, строки на экране,
  высота символа, общее число строк развёртки
- Внешняя видеопамять с доступом через DMA (DRQ/DACK)
- Программируемый курсор (мигающий или неморгающий)
- Атрибуты символов: яркость, подчёркивание, мигание, инверсия
- Прерывания: EOF (End-of-Frame), VBLANK, Light Pen

Регистры (2 порта):
  offset 0 (чтение):  Status Register
  offset 0 (запись):  Parameter 1 Register (P1)
  offset 1 (чтение):  Command Register (текущая команда)
  offset 1 (запись):  Parameter 2 Register (P2) / Command (бит 7=1)

Команды (запись в порт 1 с битом 7 = 1):
  0x80: Stop Display
  0x81: Start Display
  0x82: Reset
  0x83: Load Cursor Position
"""
from .iodevice import IODevice
from .chargen import get_char_generator

class I8275(IODevice):
    """8275 (КР580ВГ75) — CRT-контроллер"""

    # === Команды (бит 7 = 1 в Command Register) ===
    CMD_STOP_DISPLAY  = 0x80  # Остановить отображение
    CMD_START_DISPLAY = 0x81  # Запустить отображение
    CMD_RESET         = 0x82  # Сброс контроллера
    CMD_LOAD_CURSOR   = 0x83  # Загрузить позицию курсора

    # === Биты Status Register ===
    STATUS_VBLANK     = 0x01  # Бит 0: вертикальный blank
    STATUS_LPEN       = 0x02  # Бит 1: световое перо
    STATUS_EOF        = 0x04  # Бит 2: конец кадра
    STATUS_DMA_REQ    = 0x08  # Бит 3: запрос DMA
    STATUS_DISPLAY_ON = 0x10  # Бит 4: отображение активно
    STATUS_CURSOR_ON  = 0x20  # Бит 5: курсор виден
    STATUS_PARAM_ERR  = 0x40  # Бит 6: ошибка параметров
    STATUS_IRQ        = 0x80  # Бит 7: прерывание активно

    # === Биты атрибутов символов ===
    ATTR_BLINK        = 0x01  # Мигание
    ATTR_INVERSE      = 0x02  # Инверсия
    ATTR_UNDERLINE    = 0x04  # Подчёркивание
    ATTR_BRIGHT       = 0x08  # Яркость

    def __init__(self, base_port, name="I8275"):
        super().__init__(base_port, 2, name)
        self.reset()
        
        # Знакогенератор
        from .chargen import CharGenerator
        self.char_gen = CharGenerator()
        self.font_data = dict(self.char_gen.fonts[8])  # По умолчанию 8×8
        self.char_width = 8  # ← ДОБАВЛЕНО: ширина символа (6 для Радио-86РК)
        
        # Callback прерывания: on_irq(active)
        self.on_irq = None
        # Callback DMA-запроса: on_drq(active)
        self.on_drq = None
        # Callback обновления дисплея: on_display_update(video_data)
        self.on_display_update = None
        # Callback чтения видеопамяти через DMA: on_dma_read(addr) -> byte
        self.on_dma_read = None

    def reset(self):
        """Сброс контроллера"""
        # Параметры дисплея (программируемые через P1/P2)
        self.chars_per_line = 80      # Символов в строке (1-80)
        self.lines_per_screen = 16    # Строк на экране (1-16)
        self.char_height = 16         # Высота символа в строках развёртки (1-16)
        self.total_scan_lines = 16    # Полное число строк развёртки на символ
        self.display_buffer_addr = 0x0000  # Стартовый адрес видеопамяти (DMA)

        # Курсор
        self.cursor_x = 0
        self.cursor_y = 0
        self.cursor_enabled = False
        self.cursor_blink = False
        self.cursor_blink_state = False  # Текущее состояние мигания

        # Состояние отображения
        self.display_enabled = False
        self.dma_enabled = True       # DMA используется для обновления экрана
        self.drq_flag = False

        # Прерывания
        self.irq_flag = False
        self.irq_enabled = True
        self.eof_flag = False
        self.vblank_flag = False
        self.lpen_flag = False
        self.param_error = False

        # Световое перо
        self.lpen_x = 0
        self.lpen_y = 0

        # Буфер отображения (символы + атрибуты)
        # Заполняется из внешней видеопамяти через DMA
        self.display_buffer = {}  # {offset: (char, attr)}

        # Внутреннее состояние
        self._current_command = 0x00
        self._param_phase = 0     # Фаза загрузки параметров
        self._temp_p1 = 0
        self._temp_p2 = 0
        self._cursor_load_pending = False
        self._cursor_x_temp = 0

    # =============================================
    # IO ЧТЕНИЕ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Status Register
            return self._get_status()
        elif offset == 1:
            # Текущая команда (для отладки)
            return self._current_command
        return 0xFF

    # =============================================
    # IO ЗАПИСЬ
    # =============================================
    def io_write(self, port, value):
        """Запись в порт"""
        value &= 0xFF
        offset = port - self.base_port
        if offset == 0:
            # Parameter 1 Register
            self._write_p1(value)
        elif offset == 1:
            # Parameter 2 или Command (бит 7)
            if value & 0x80:
                self._write_command(value)
            else:
                self._write_p2(value)

    # =============================================
    # ПАРАМЕТРЫ
    # =============================================
    def _write_p1(self, value):
        """Parameter 1 Register:
        Биты 0-6: characters per line - 1
        Бит 7: reserved
        """
        self._temp_p1 = value
        self._param_phase = 1

    def _write_p2(self, value):
        """Parameter 2 Register:
        Биты 0-3: lines per screen - 1
        Биты 4-7: char height - 1
        """
        self._temp_p2 = value
        self._param_phase = 2
        self._apply_params()

    def _apply_params(self):
        """Применить загруженные параметры"""
        self.chars_per_line = (self._temp_p1 & 0x7F) + 1
        self.lines_per_screen = (self._temp_p2 & 0x0F) + 1
        self.char_height = ((self._temp_p2 >> 4) & 0x0F) + 1
        # Валидация
        if self.chars_per_line > 80:
            self.chars_per_line = 80
            self.param_error = True
        if self.lines_per_screen > 16:
            self.lines_per_screen = 16
            self.param_error = True
        if self.char_height > 16:
            self.char_height = 16
            self.param_error = True
        self._param_phase = 0

    # =============================================
    # КОМАНДЫ
    # =============================================
    def _write_command(self, value):
        """Запись команды (бит 7 = 1)"""
        self._current_command = value
        cmd = value & 0x7F

        if value == self.CMD_STOP_DISPLAY:
            self.display_enabled = False
            self.drq_flag = False
            if self.on_drq:
                self.on_drq(False)

        elif value == self.CMD_START_DISPLAY:
            self.display_enabled = True
            self.param_error = False
            # Запуск DMA для загрузки видеопамяти
            if self.dma_enabled:
                self._start_dma_refresh()

        elif value == self.CMD_RESET:
            self.reset()

        elif value == self.CMD_LOAD_CURSOR:
            # Следующие 2 записи параметров = X и Y курсора
            self._cursor_load_pending = True

        # Обработка загрузки курсора через P1/P2
        if self._cursor_load_pending and self._param_phase == 2:
            self.cursor_x = self._temp_p1 & 0x7F
            self.cursor_y = self._temp_p2 & 0x0F
            self._cursor_load_pending = False

    # =============================================
    # DMA (обновление видеопамяти)
    # =============================================
    def _start_dma_refresh(self):
        """Запуск DMA для загрузки буфера отображения из внешней видеопамяти"""
        self.drq_flag = True
        if self.on_drq:
            self.on_drq(True)
        # Если подключён обработчик чтения видеопамяти — загружаем
        if self.on_dma_read:
            self._load_display_buffer()

    def _load_display_buffer(self):
        """Загрузить буфер отображения через DMA"""
        total_chars = self.chars_per_line * self.lines_per_screen
        addr = self.display_buffer_addr
        self.display_buffer.clear()
        for i in range(total_chars):
            # Читаем символ и атрибут (2 байта на позицию)
            char = self.on_dma_read(addr + i * 2)
            attr = self.on_dma_read(addr + i * 2 + 1)
            self.display_buffer[i] = (char & 0xFF, attr & 0xFF)
        self.drq_flag = False
        if self.on_drq:
            self.on_drq(False)
        # Уведомляем об обновлении
        if self.on_display_update:
            self.on_display_update(dict(self.display_buffer))

    def dma_acknowledge(self):
        """Подтверждение DMA (от контроллера DMA)"""
        self.drq_flag = False
        if self.on_drq:
            self.on_drq(False)

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
        if self.eof_flag:
            status |= self.STATUS_EOF
        if self.drq_flag:
            status |= self.STATUS_DMA_REQ
        if self.display_enabled:
            status |= self.STATUS_DISPLAY_ON
        if self.cursor_enabled:
            status |= self.STATUS_CURSOR_ON
        if self.param_error:
            status |= self.STATUS_PARAM_ERR
        if self.irq_flag:
            status |= self.STATUS_IRQ
        return status

    # =============================================
    # ВНЕШНИЕ СОБЫТИЯ
    # =============================================
    def end_of_frame(self):
        """Событие конца кадра (вызывается извне, например, по таймеру)"""
        self.eof_flag = True
        self.irq_flag = True
        if self.irq_enabled and self.on_irq:
            self.on_irq(True)
        # После EOF запускается новое обновление экрана через DMA
        if self.display_enabled and self.dma_enabled:
            self._start_dma_refresh()

    def vertical_blank(self):
        """Событие вертикального blank"""
        self.vblank_flag = True

    def light_pen(self, x, y):
        """Событие светового пера"""
        self.lpen_x = x
        self.lpen_y = y
        self.lpen_flag = True
        self.irq_flag = True
        if self.irq_enabled and self.on_irq:
            self.on_irq(True)

    def acknowledge_interrupt(self):
        """Подтверждение прерывания (сброс флагов)"""
        self.irq_flag = False
        self.eof_flag = False
        self.vblank_flag = False
        self.lpen_flag = False

    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.irq_flag

    def has_drq(self):
        """Есть ли активный DMA-запрос"""
        return self.drq_flag

    # =============================================
    # КУРСОР И АТРИБУТЫ
    # =============================================
    def set_cursor(self, x, y, enabled=True, blink=False):
        """Установить курсор программно"""
        self.cursor_x = x & 0x7F
        self.cursor_y = y & 0x0F
        self.cursor_enabled = enabled
        self.cursor_blink = blink

    def tick_cursor_blink(self):
        """Вызывается периодически для мигания курсора"""
        if self.cursor_blink and self.cursor_enabled:
            self.cursor_blink_state = not self.cursor_blink_state

    # =============================================
    # УТИЛИТЫ ДЛЯ GUI
    # =============================================
    # Таблица КОИ-7 набор 2 → Unicode (кириллица)
    KOI7_TO_UNICODE = {
        0x60: 'Ю', 0x61: 'А', 0x62: 'Б', 0x63: 'Ц', 0x64: 'Д', 0x65: 'Е',
        0x66: 'Ф', 0x67: 'Г', 0x68: 'Х', 0x69: 'И', 0x6A: 'Й', 0x6B: 'К',
        0x6C: 'Л', 0x6D: 'М', 0x6E: 'Н', 0x6F: 'О', 0x70: 'П', 0x71: 'Я',
        0x72: 'Р', 0x73: 'С', 0x74: 'Т', 0x75: 'У', 0x76: 'Ж', 0x77: 'В',
        0x78: 'Ь', 0x79: 'Ы', 0x7A: 'З', 0x7B: 'Ш', 0x7C: 'Э', 0x7D: 'Щ',
        0x7E: 'Ч', 0x7F: 'Ъ',
    }

    def get_display_text(self):
        """Получить текст дисплея для отображения в GUI"""
        lines = []
        for y in range(self.lines_per_screen):
            line = ""
            for x in range(self.chars_per_line):
                idx = y * self.chars_per_line + x
                if idx in self.display_buffer:
                    char, attr = self.display_buffer[idx]
                    # КОИ-7 кириллица
                    if char in self.KOI7_TO_UNICODE:
                        line += self.KOI7_TO_UNICODE[char]
                    elif 32 <= char <= 126:
                        line += chr(char)
                    else:
                        line += "."
                else:
                    line += " "
            lines.append(line)
        return lines

    # Обратная таблица: Unicode → KOI-7 (генерируется автоматически)
    UNICODE_TO_KOI7 = {v: k for k, v in KOI7_TO_UNICODE.items()}

    @classmethod
    def unicode_to_koi7(cls, text):
        """Преобразовать текст из Unicode в коды KOI-7.
        
        Используется для записи русского текста в видеопамять.
        """
        codes = []
        for ch in text:
            if ch in cls.UNICODE_TO_KOI7:
                codes.append(cls.UNICODE_TO_KOI7[ch])
            elif 32 <= ord(ch) <= 126:
                # ASCII символы (цифры, знаки препинания, латиница)
                codes.append(ord(ch))
            else:
                # Неизвестный символ — заменяем на '?'
                codes.append(0x3F)
        return codes

    def set_character(self, x, y, char, attr=0x00):
        """Установить символ в буфер отображения (для тестов/GUI)"""
        idx = y * self.chars_per_line + x
        self.display_buffer[idx] = (char & 0xFF, attr & 0xFF)

    def get_character(self, x, y):
        """Получить символ из буфера отображения"""
        idx = y * self.chars_per_line + x
        if idx in self.display_buffer:
            return self.display_buffer[idx]
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
            "char_height": self.char_height,
            "display_buffer_addr": f"0x{self.display_buffer_addr:04X}",
            "cursor": f"({self.cursor_x},{self.cursor_y})",
            "cursor_enabled": self.cursor_enabled,
            "cursor_blink": self.cursor_blink,
            "display_enabled": self.display_enabled,
            "drq_flag": self.drq_flag,
            "irq_flag": self.irq_flag,
            "param_error": self.param_error,
            "status": f"0x{self._get_status():02X}",
        }

    def load_font_from_file(self, path, char_width=8, num_chars=256,
                            invert=False, bit_reverse=False):
        """Загрузить шрифт знакогенератора из raw-файла.
        
        Для Радио-86РК: char_width=6, invert=True, bit_reverse=True
        """
        self.char_width = char_width
        return self.char_gen.load_from_file(path, height=8,
                                            width=char_width,
                                            num_chars=num_chars,
                                            invert=invert,
                                            bit_reverse=bit_reverse)

    def get_char_bitmap(self, code):
        """Код символа → пиксельная карта (через знакогенератор)."""
        h = getattr(self, 'char_height', 8)
        return self.char_gen.get_bitmap(code, h)
