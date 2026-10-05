"""
8255 (КР580ВВ55) — Programmable Peripheral Interface.
Итерация E3: базовые IO-устройства.

Регистры (4 порта):
  offset 0: Port A
  offset 1: Port B
  offset 2: Port C
  offset 3: Control Word (бит 7 = 1) / BSR (бит 7 = 0)

Режимы:
  Mode 0: простой ввод/вывод
  Mode 1: стробированный ввод/вывод (INTRA/INTRB)
  Mode 2: двунаправленный стробированный (только порт A)

Сигналы прерываний:
  INTRA — прерывание порта A (Mode 1/2)
  INTRB — прерывание порта B (Mode 1)
"""
from .iodevice import IODevice


class I8255(IODevice):
    """8255 PPI — 3 порта по 8 бит."""
    
    # Режимы работы
    MODE_0 = 0  # Простой ввод/вывод
    MODE_1 = 1  # Стробированный ввод/вывод
    MODE_2 = 2  # Двунаправленный стробированный (только порт A)
    
    def __init__(self, base_port, name="I8255"):
        super().__init__(base_port, 4, name)
        self.reset()
        # Callback для прерываний: вызывается при INTRA/INTRB
        self.on_interrupt = None  # callback(port_name, active)
    
    def reset(self):
        """Сброс: все порты на ввод, Mode 0."""
        self.port_a = 0x00
        self.port_b = 0x00
        self.port_c = 0x00
        self.control = 0x9B  # Все порты на ввод, Mode 0
        # Направления портов (True = ввод, False = вывод)
        self.dir_a = True
        self.dir_b = True
        self.dir_cu = True   # Port C upper (биты 4-7)
        self.dir_cl = True   # Port C lower (биты 0-3)
        # Режимы
        self.mode_a = self.MODE_0
        self.mode_b = self.MODE_0
        # Строб-сигналы для Mode 1/2 (эмуляция)
        self.strobe_a = False
        self.strobe_b = False
        # Флаги прерываний
        self.intra = False
        self.intrb = False
        # Внешние данные для входных портов (подаются извне: клавиатура, переключатели)
        self.external_input = [0xFF, 0xFF, 0xFF]  # Port A, B, C
        # Callback при изменении выходных портов: on_port_change(port_num, value)
        self.on_port_change = None
    
    def io_read(self, port):
        """Чтение из порта с учётом режима"""
        offset = port - self.base_port
        ctrl = self.control
        
        if offset == 0:  # Port A
            a_mode_bits = (ctrl >> 5) & 0x03
            if a_mode_bits >= 2:
                # Режим 2: двунаправленный — чтение возвращает входные данные
                return self.external_input[0]
            elif (ctrl >> 4) & 1:  # Режим 0/1, вход
                return self.external_input[0]
            else:  # Режим 0/1, выход
                return self.port_a
        elif offset == 1:  # Port B
            if ctrl & 1:  # D0: 1=вход, 0=выход
                return self.external_input[1]
            else:  # Выход
                return self.port_b
        elif offset == 2:  # Port C
            result = 0
            # Нижняя половина (биты 0-3)
            if ctrl & 1:  # Вход
                result |= (self.external_input[2] & 0x0F)
            else:  # Выход
                result |= (self.port_c & 0x0F)
            # Верхняя половина (биты 4-7)
            if (ctrl >> 3) & 1:  # Вход
                result |= (self.external_input[2] & 0xF0)
            else:  # Выход
                result |= (self.port_c & 0xF0)
            return result
        elif offset == 3:  # Control
            return self.control
        return 0xFF

    def io_write(self, port, value):
        """Запись в порт."""
        value &= 0xFF
        offset = port - self.base_port
        if offset == 0:
            self.port_a = value
            if self.on_port_change:
                self.on_port_change(0, value)
            self._check_interrupt_a()
        elif offset == 1:
            self.port_b = value
            if self.on_port_change:
                self.on_port_change(1, value)
            self._check_interrupt_b()
        elif offset == 2:
            self.port_c = value
            if self.on_port_change:
                self.on_port_change(2, value)
        elif offset == 3:
            if value & 0x80:
                self.control = value
                self._write_control(value)
            else:
                self._bit_set_reset(value)

    def _write_control(self, value):
        """Запись в Control Word / BSR."""
        self.control = value
        if value & 0x80:
            # Control Word (бит 7 = 1)
            self._parse_control_word(value)
        else:
            # BSR — Bit Set/Reset для порта C (бит 7 = 0)
            self._bit_set_reset(value)
    
    def _parse_control_word(self, cw):
        """Парсинг Control Word.
        Бит 7: 1 = Control Word
        Бит 6-5: Mode A (00=Mode0, 01=Mode1, 1x=Mode2)
        Бит 4: Port A direction (1=ввод, 0=вывод)
        Бит 3: Port C upper direction (1=ввод, 0=вывод)
        Бит 2: Mode B (0=Mode0, 1=Mode1)
        Бит 1: Port B direction (1=ввод, 0=вывод)
        Бит 0: Port C lower direction (1=ввод, 0=вывод)
        """
        # Mode A
        mode_a_bits = (cw >> 5) & 0x03
        if mode_a_bits == 0:
            self.mode_a = self.MODE_0
        elif mode_a_bits == 1:
            self.mode_a = self.MODE_1
        else:
            self.mode_a = self.MODE_2
        
        self.dir_a = bool(cw & 0x10)
        self.dir_cu = bool(cw & 0x08)
        
        # Mode B
        self.mode_b = self.MODE_1 if (cw & 0x04) else self.MODE_0
        self.dir_b = bool(cw & 0x02)
        self.dir_cl = bool(cw & 0x01)
        
        # Сброс портов при записи Control Word
        self.port_a = 0x00
        self.port_b = 0x00
        self.port_c = 0x00
        self.intra = False
        self.intrb = False
    
    def _bit_set_reset(self, value):
        """BSR — установка/сброс бита порта C.
        Бит 3-1: номер бита (0-7)
        Бит 0: 1 = установка, 0 = сброс
        """
        bit = (value >> 1) & 0x07
        if value & 0x01:
            self.port_c |= (1 << bit)
        else:
            self.port_c &= ~(1 << bit)
    
    def set_port_input(self, port_name, value):
        """Внешний сигнал на вход порта (для эмуляции внешних устройств).
        port_name: 'A', 'B', 'C'
        
        Устанавливает external_input — то, что ио_read вернёт
        при чтении порта в режиме входа.
        """
        value &= 0xFF
        if port_name == 'A':
            self.external_input[0] = value
            self._check_interrupt_a()
        elif port_name == 'B':
            self.external_input[1] = value
            self._check_interrupt_b()
        elif port_name == 'C':
            self.external_input[2] = value
    
    def _check_interrupt_a(self):
        """Проверка прерывания порта A (Mode 1/2)."""
        if self.mode_a in (self.MODE_1, self.MODE_2) and self.dir_a:
            # В Mode 1/2 при вводе данных генерируется INTRA
            if not self.intra:
                self.intra = True
                # Устанавливаем бит 5 порта C (INTRA)
                self.port_c |= 0x20
                if self.on_interrupt:
                    self.on_interrupt('INTRA', True)
    
    def _check_interrupt_b(self):
        """Проверка прерывания порта B (Mode 1)."""
        if self.mode_b == self.MODE_1 and self.dir_b:
            if not self.intrb:
                self.intrb = True
                # Устанавливаем бит 1 порта C (INTRB)
                self.port_c |= 0x02
                if self.on_interrupt:
                    self.on_interrupt('INTRB', True)
    
    def acknowledge_interrupt(self, signal):
        """Подтверждение прерывания (сброс флага)."""
        if signal == 'INTRA':
            self.intra = False
            self.port_c &= ~0x20
        elif signal == 'INTRB':
            self.intrb = False
            self.port_c &= ~0x02
    
    def get_state(self):
        """Состояние для отладки."""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "port_a": f"0x{self.port_a:02X}",
            "port_b": f"0x{self.port_b:02X}",
            "port_c": f"0x{self.port_c:02X}",
            "control": f"0x{self.control:02X}",
            "mode_a": self.mode_a,
            "mode_b": self.mode_b,
            "dir_a": self.dir_a,
            "dir_b": self.dir_b,
            "dir_cu": self.dir_cu,
            "dir_cl": self.dir_cl,
            "intra": self.intra,
            "intrb": self.intrb,
        }

    def set_external_input(self, port_num, value):
        """Установить внешние данные для входного порта.
        
        Вызывается из виджета GPIO или модуля клавиатуры.
        """
        if 0 <= port_num <= 2:
            self.external_input[port_num] = value & 0xFF

    def get_port_direction(self):
        """Получить направление портов: (a_in, b_in, c_low_in, c_high_in)
        
        Определяется из управляющего слова (биты контрольного слова 8255):
        - Бит 4: порт A (1=вход, 0=выход)
        - Бит 3: порт C верхняя половина (1=вход, 0=выход)
        - Бит 1: порт B (1=вход, 0=выход)
        - Бит 0: порт C нижняя половина (1=вход, 0=выход)
        """
        ctrl = self.control
        a_in = bool((ctrl >> 4) & 1)
        b_in = bool((ctrl >> 1) & 1)
        c_low_in = bool(ctrl & 1)
        c_high_in = bool((ctrl >> 3) & 1)
        return (a_in, b_in, c_low_in, c_high_in)

    def get_port_modes(self):
        """Получить режимы и направления портов.
        
        Возвращает словарь с режимами и направлениями:
        - a_mode: 0, 1 или 2 (режим порта A)
        - a_direction: 'in', 'out' или 'bidir'
        - b_mode: 0 или 1
        - b_direction: 'in' или 'out'
        - c_low_direction, c_high_direction: 'in' или 'out'
        """
        ctrl = self.control
        
        # === Порт A (биты 6-5: режим) ===
        a_mode_bits = (ctrl >> 5) & 0x03
        if a_mode_bits <= 1:  # Режим 0 или 1
            a_mode = a_mode_bits
            a_direction = 'in' if (ctrl >> 4) & 1 else 'out'
        else:  # Биты 6-5 = 1x → режим 2 (двунаправленный)
            a_mode = 2
            a_direction = 'bidir'
        
        # === Порт B (бит 2: режим) ===
        b_mode = 1 if (ctrl >> 2) & 1 else 0
        b_direction = 'in' if (ctrl >> 1) & 1 else 'out'
        
        # === Порт C (бит 3: верх, бит 0: низ) ===
        c_high_direction = 'in' if (ctrl >> 3) & 1 else 'out'
        c_low_direction = 'in' if ctrl & 1 else 'out'
        
        return {
            'a_mode': a_mode,
            'a_direction': a_direction,
            'b_mode': b_mode,
            'b_direction': b_direction,
            'c_low_direction': c_low_direction,
            'c_high_direction': c_high_direction,
        }
