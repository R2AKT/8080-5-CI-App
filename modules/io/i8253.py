"""
8253 (КР580ВИ53) — Programmable Interval Timer.
Итерация E3: базовые IO-устройства.

3 независимых канала (0, 1, 2).
Каждый канал: вход CLK, выход OUT, вход GATE.
Выходы OUT могут подключаться к IRQ контроллера 8259.

Регистры (4 порта):
  offset 0: Channel 0
  offset 1: Channel 1
  offset 2: Channel 2
  offset 3: Control Word

Режимы:
  Mode 0: Interrupt on Terminal Count
  Mode 1: Hardware Retriggerable One-Shot
  Mode 2: Rate Generator
  Mode 3: Square Wave Generator
  Mode 4: Software Triggered Strobe
  Mode 5: Hardware Triggered Strobe
"""
from .iodevice import IODevice


class I8253Channel:
    """Один канал таймера 8253."""
    
    def __init__(self, channel_num):
        self.channel_num = channel_num
        self.reset()
    
    def reset(self):
        """Сброс канала."""
        self.count = 0          # Загруженное значение счётчика
        self.current = 0        # Текущее значение счётчика
        self.mode = 0           # Режим работы (0-5)
        self.bcd = False        # BCD-счёт (True) или двоичный (False)
        self.access_mode = 0    # 0=Latch, 1=LSB, 2=MSB, 3=LSB then MSB
        self.gate = True        # Вход GATE (по умолчанию активен)
        self.out = False        # Выход OUT
        self.running = False    # Канал запущен
        self.latched = False    # Значение зафиксировано для чтения
        self.latched_value = 0  # Зафиксированное значение
        self.read_state = 0     # 0=LSB, 1=MSB (для чтения LSB then MSB)
        self.write_state = 0    # 0=LSB, 1=MSB (для записи LSB then MSB)
        self.temp_lsb = 0       # Временный LSB при записи LSB then MSB


class I8253(IODevice):
    """8253 PIT — 3 канала таймера."""
    
    def __init__(self, base_port, name="I8253"):
        super().__init__(base_port, 4, name)
        self.channels = [I8253Channel(i) for i in range(3)]
        # Callback для OUT сигналов: on_out(channel, active)
        # Используется для подключения к IRQ контроллеру 8259
        self.on_out = None
        self.on_irq = None
    
    def reset(self):
        """Сброс всех каналов."""
        for ch in self.channels:
            ch.reset()
    
    # =============================================
    # IO READ / WRITE
    # =============================================
    def io_read(self, port):
        """Чтение из порта."""
        offset = port - self.base_port
        if offset < 3:
            return self._read_channel(offset)
        elif offset == 3:
            return 0xFF  # Control Word не читается
        return 0xFF
    
    def io_write(self, port, value):
        """Запись в порт."""
        value &= 0xFF
        offset = port - self.base_port
        if offset < 3:
            self._write_channel(offset, value)
        elif offset == 3:
            self._write_control(value)
    
    # =============================================
    # CONTROL WORD
    # =============================================
    def _write_control(self, cw):
        """Запись Control Word.
        Биты 7-6: выбор канала (00=Ch0, 01=Ch1, 10=Ch2, 11=Read-back)
        Биты 5-4: формат доступа (00=Latch, 01=LSB, 10=MSB, 11=LSB/MSB)
        Биты 3-1: режим (000-101 = Mode 0-5)
        Бит 0: формат счёта (0=binary, 1=BCD)
        """
        ch_num = (cw >> 6) & 0x03
        
        if ch_num == 3:
            # Read-back command (упрощённо — игнорируем)
            return
        
        ch = self.channels[ch_num]
        access = (cw >> 4) & 0x03
        mode = (cw >> 1) & 0x07
        bcd = bool(cw & 0x01)
        
        if access == 0:
            # Counter Latch: фиксируем текущее значение для чтения
            ch.latched = True
            ch.latched_value = ch.current
            ch.read_state = 0
            return
        
        ch.access_mode = access
        ch.mode = mode if mode <= 5 else 0
        ch.bcd = bcd
        ch.running = False
        ch.out = False
        ch.write_state = 0
        ch.read_state = 0
    
    # =============================================
    # ЧТЕНИЕ КАНАЛА
    # =============================================
    def _read_channel(self, ch_num):
        """Чтение значения канала."""
        ch = self.channels[ch_num]
        
        if ch.latched:
            # Чтение зафиксированного значения
            if ch.access_mode == 1:  # LSB only
                ch.latched = False
                return ch.latched_value & 0xFF
            elif ch.access_mode == 2:  # MSB only
                ch.latched = False
                return (ch.latched_value >> 8) & 0xFF
            elif ch.access_mode == 3:  # LSB then MSB
                if ch.read_state == 0:
                    ch.read_state = 1
                    return ch.latched_value & 0xFF
                else:
                    ch.read_state = 0
                    ch.latched = False
                    return (ch.latched_value >> 8) & 0xFF
        
        # Чтение текущего значения
        if ch.access_mode == 1:  # LSB only
            return ch.current & 0xFF
        elif ch.access_mode == 2:  # MSB only
            return (ch.current >> 8) & 0xFF
        elif ch.access_mode == 3:  # LSB then MSB
            if ch.read_state == 0:
                ch.read_state = 1
                return ch.current & 0xFF
            else:
                ch.read_state = 0
                return (ch.current >> 8) & 0xFF
        
        return ch.current & 0xFF
    
    # =============================================
    # ЗАПИСЬ КАНАЛА
    # =============================================
    def _write_channel(self, ch_num, value):
        """Запись значения в канал."""
        ch = self.channels[ch_num]
        
        if ch.access_mode == 1:  # LSB only
            ch.count = value
            self._load_channel(ch)
        elif ch.access_mode == 2:  # MSB only
            ch.count = value << 8
            self._load_channel(ch)
        elif ch.access_mode == 3:  # LSB then MSB
            if ch.write_state == 0:
                ch.temp_lsb = value
                ch.write_state = 1
            else:
                ch.count = (value << 8) | ch.temp_lsb
                ch.write_state = 0
                self._load_channel(ch)
    
    def _load_channel(self, ch):
        """Загрузка значения в канал."""
        if ch.count == 0:
            # 0 означает 65536 (0x10000)
            ch.count = 0x10000
        ch.current = ch.count
        ch.running = True
        # Mode 2, 3: OUT начинается с высокого уровня
        if ch.mode in (2, 3):
            ch.out = True
    
    # =============================================
    # TICK — подсчёт тактов
    # =============================================
    def tick(self, cycles=1):
        """Вызывается каждый такт процессора.
        Уменьшает счётчики активных каналов.
        """
        for _ in range(cycles):
            for ch in self.channels:
                if not ch.running or not ch.gate:
                    continue
                self._tick_channel(ch)
    
    def _tick_channel(self, ch):
        """Один такт для канала."""
        ch.current -= 1
        
        if ch.current <= 0:
            # Достижение нуля
            if ch.mode == 0:
                # Mode 0: Interrupt on Terminal Count
                if not ch.out:
                    ch.out = True
                    if self.on_out:
                        self.on_out(ch.channel_num, True)
                ch.running = False
            elif ch.mode == 1:
                # Mode 1: One-Shot
                ch.out = True
                if self.on_out:
                    self.on_out(ch.channel_num, True)
                ch.running = False
            elif ch.mode == 2:
                # Mode 2: Rate Generator
                ch.out = False
                if self.on_out:
                    self.on_out(ch.channel_num, False)
                ch.current = ch.count
                # OUT восстанавливается на следующем такте
                ch.out = True
                if self.on_out:
                    self.on_out(ch.channel_num, True)
            elif ch.mode == 3:
                # Mode 3: Square Wave Generator
                ch.out = not ch.out
                if self.on_out:
                    self.on_out(ch.channel_num, ch.out)
                ch.current = ch.count
            elif ch.mode == 4:
                # Mode 4: Software Triggered Strobe
                if not ch.out:
                    ch.out = True
                    if self.on_out:
                        self.on_out(ch.channel_num, True)
                ch.running = False
            elif ch.mode == 5:
                # Mode 5: Hardware Triggered Strobe
                ch.out = True
                if self.on_out:
                    self.on_out(ch.channel_num, True)
                ch.running = False
    
    # =============================================
    # GATE / OUT
    # =============================================
    def set_gate(self, ch_num, active):
        """Установить вход GATE канала."""
        if 0 <= ch_num < 3:
            ch = self.channels[ch_num]
            old_gate = ch.gate
            ch.gate = active
            # Mode 1, 5: rising edge GATE запускает канал
            if ch.mode in (1, 5) and not old_gate and active:
                ch.current = ch.count
                ch.running = True
    
    def get_out(self, ch_num):
        """Получить выход OUT канала."""
        if 0 <= ch_num < 3:
            return self.channels[ch_num].out
        return False
    
    # =============================================
    # СОСТОЯНИЕ
    # =============================================
    def get_state(self):
        """Состояние для отладки."""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "channels": [
                {
                    "count": ch.count,
                    "current": ch.current,
                    "mode": ch.mode,
                    "gate": ch.gate,
                    "out": ch.out,
                    "running": ch.running,
                }
                for ch in self.channels
            ]
        }
    
    # =============================================
    # ПРЕРЫВАНИЯ
    # =============================================
    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return getattr(self, 'irq_flag', False)

    def acknowledge_interrupt(self):
        """Подтверждение прерывания"""
        self.irq_flag = False
        if self.on_irq:
            self.on_irq(False)
