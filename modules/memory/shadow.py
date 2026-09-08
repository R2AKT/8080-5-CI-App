from .memory_bus import MemoryBus, MemoryRegion, RAMRegion, ROMRegion

class ShadowROMRegion(MemoryRegion):
    """Теневое ПЗУ с переключением.
    
    Режимы переключения:
      MODE_M1        — по N чтениям из ROM (Радио-86РК: 3 чтения = размер JMP)
      MODE_MEM_READ  — по чтению из ячейки памяти
      MODE_MEM_WRITE — по записи в ячейку памяти
      MODE_MEM_RW    — по чтению или записи ячейки памяти
      MODE_IO_READ   — по чтению из IO-порта
      MODE_IO_WRITE  — по записи в IO-порт
      MODE_IO_RW     — по чтению или записи IO-порта
    
    Действия после переключения:
      ACTION_MOVE    — переместить ROM на high_addr
      ACTION_DISABLE — полностью отключить ROM
    
    Состояния:
      STATE_LOW      — ROM виден по low_addr (после сброса)
      STATE_HIGH     — ROM виден по high_addr (после переключения)
      STATE_DISABLED — ROM полностью отключён
    """
    
    # Режимы переключения
    MODE_M1 = "m1"
    MODE_MEM_READ = "mem_read"
    MODE_MEM_WRITE = "mem_write"
    MODE_MEM_RW = "mem_rw"
    MODE_IO_READ = "io_read"
    MODE_IO_WRITE = "io_write"
    MODE_IO_RW = "io_rw"
    
    # Действия после переключения
    ACTION_MOVE = "move"
    ACTION_DISABLE = "disable"
    
    # Состояния
    STATE_LOW = "low"
    STATE_HIGH = "high"
    STATE_DISABLED = "disabled"
    
    def __init__(self, data, low_addr=0x0000, high_addr=0xF800,
                 mode=MODE_M1, action=ACTION_MOVE,
                 trigger_addr=None, trigger_port=None,
                 m1_count=3, name="ShadowROM"):
        """
        Args:
            data: dict {offset: byte} — данные ROM
            low_addr: адрес, по которому ROM виден после сброса
            high_addr: адрес, по которому ROM виден после переключения
            mode: режим переключения (MODE_*)
            action: действие после переключения (ACTION_*)
            trigger_addr: адрес памяти для триггера (для MODE_MEM_*)
            trigger_port: порт IO для триггера (для MODE_IO_*)
            m1_count: количество чтений для переключения (для MODE_M1)
            name: имя региона
        """
        super().__init__(low_addr, low_addr + len(data) - 1, name)
        self.data = dict(data) if data else {}
        self.size = len(self.data)
        self.low_addr = low_addr & 0xFFFF
        self.high_addr = high_addr & 0xFFFF
        self.mode = mode
        self.action = action
        self.trigger_addr = trigger_addr & 0xFFFF if trigger_addr is not None else None
        self.trigger_port = trigger_port & 0xFF if trigger_port is not None else None
        self.m1_count = m1_count
        self.state = self.STATE_LOW
        self._read_counter = 0
    
    # =============================================
    # ПРОВЕРКА СОДЕРЖИМОГО АДРЕСА
    # =============================================
    def contains(self, addr):
        """Проверяет, содержится ли адрес в текущем состоянии ROM"""
        if self.state == self.STATE_LOW:
            return self.low_addr <= addr < self.low_addr + self.size
        elif self.state == self.STATE_HIGH:
            return self.high_addr <= addr < self.high_addr + self.size
        return False  # STATE_DISABLED
    
    # =============================================
    # ЧТЕНИЕ
    # =============================================
    def read(self, addr):
        """Чтение байта из ROM"""
        if self.state == self.STATE_LOW:
            if self.low_addr <= addr < self.low_addr + self.size:
                offset = addr - self.low_addr
                # Режим M1: считаем чтения только для адресов ROM
                if self.mode == self.MODE_M1:
                    self._read_counter += 1
                    if self._read_counter >= self.m1_count:
                        self._do_switch()
                return self.data.get(offset, 0xFF)
            else:
                # Адрес вне ROM: проверяем триггер MEM_READ / MEM_RW
                if self.mode in (self.MODE_MEM_READ, self.MODE_MEM_RW):
                    if self.trigger_addr is not None and addr == self.trigger_addr:
                        self._do_switch()
                return 0xFF
        elif self.state == self.STATE_HIGH:
            if self.high_addr <= addr < self.high_addr + self.size:
                offset = addr - self.high_addr
                return self.data.get(offset, 0xFF)
            return 0xFF
        return 0xFF
    # =============================================
    # ЗАПИСЬ (ROM не пишется, но может быть триггером)
    # =============================================
    def write(self, addr, value):
        """Запись в ROM (игнорируется, но может быть триггером)"""
        if self.state != self.STATE_LOW:
            return
        # Триггер MEM_WRITE / MEM_RW — адрес не обязан принадлежать ROM
        if self.mode in (self.MODE_MEM_WRITE, self.MODE_MEM_RW):
            if self.trigger_addr is not None and addr == self.trigger_addr:
                self._do_switch()
                
    # =============================================
    # ОБРАЩЕНИЕ К IO-ПОРТУ (может быть триггером)
    # =============================================
    def io_access(self, port, is_write):
        """Уведомление об обращении к IO-порту.
        Вызывается из MemoryBus.io_read / io_write.
        """
        if self.state != self.STATE_LOW:
            return
        
        if self.trigger_port is not None and port == self.trigger_port:
            if self.mode == self.MODE_IO_READ and not is_write:
                self._do_switch()
            elif self.mode == self.MODE_IO_WRITE and is_write:
                self._do_switch()
            elif self.mode == self.MODE_IO_RW:
                self._do_switch()
    
    # =============================================
    # ПЕРЕКЛЮЧЕНИЕ
    # =============================================
    def _do_switch(self):
        """Выполнить переключение"""
        if self.action == self.ACTION_MOVE:
            self.state = self.STATE_HIGH
            self.start = self.high_addr
            self.end = self.high_addr + self.size - 1
        elif self.action == self.ACTION_DISABLE:
            self.state = self.STATE_DISABLED
            self.start = 0
            self.end = 0  # Пустой диапазон — регион не содержит ни одного адреса
    
    # =============================================
    # СБРОС
    # =============================================
    def reset(self):
        """Сброс: ROM снова виден по low_addr"""
        self.state = self.STATE_LOW
        self.start = self.low_addr
        self.end = self.low_addr + self.size - 1
        self._read_counter = 0
    
    # =============================================
    # ИНФОРМАЦИЯ О СОСТОЯНИИ
    # =============================================
    def get_state_info(self):
        """Информация о состоянии для отладки"""
        return {
            "state": self.state,
            "mode": self.mode,
            "action": self.action,
            "low_addr": self.low_addr,
            "high_addr": self.high_addr,
            "size": self.size,
            "read_counter": self._read_counter,
            "m1_count": self.m1_count,
        }
