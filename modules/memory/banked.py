from .memory_bus import MemoryBus, MemoryRegion, RAMRegion, ROMRegion

class BankedRegion(MemoryRegion):
    """Банковая память: окно в адресном пространстве, через которое
    виден один из банков физической памяти.
    
    Переключение банков:
    - через IO-порт (switch_port) — запись в порт выбирает банк
    - через адрес памяти (switch_addr) — запись по адресу выбирает банк
    
    Пример для Радио-86РК:
    - Окно: 0x0000-0xFFFF (всё адресное пространство)
    - 4 банка по 64 КБ
    - Переключение через порт 0x00
    """
    
    def __init__(self, start, end, num_banks=2, switch_port=None, 
                 switch_addr=None, name="BankedRAM"):
        super().__init__(start, end, name)
        self.window_size = end - start + 1
        self.num_banks = num_banks
        self.switch_port = switch_port      # Порт IO для переключения
        self.switch_addr = switch_addr      # Адрес памяти для переключения
        self.current_bank = 0
        # Банки физической памяти
        self.banks = [{} for _ in range(num_banks)]
        # Флаг: переключение по записи в switch_addr
        self._switch_pending = False
    
    def select_bank(self, bank_num):
        """Переключить банк"""
        bank_num &= 0xFF
        if bank_num < self.num_banks:
            self.current_bank = bank_num
        else:
            # Если банк вне диапазона, берём по модулю
            self.current_bank = bank_num % self.num_banks
    
    def read(self, addr):
        """Чтение из текущего банка"""
        if not self.contains(addr):
            return 0xFF
        offset = addr - self.start
        return self.banks[self.current_bank].get(offset, 0x00)
    
    def write(self, addr, value):
        """Запись в текущий банк, или переключение банка"""
        if not self.contains(addr):
            return
        # Переключение банка по записи в switch_addr
        if self.switch_addr is not None and addr == self.switch_addr:
            self.select_bank(value)
            return
        # Обычная запись в текущий банк
        offset = addr - self.start
        self.banks[self.current_bank][offset] = value & 0xFF
    
    def io_write(self, port, value):
        """Обработка записи в IO-порт (переключение банка)"""
        if self.switch_port is not None and port == self.switch_port:
            self.select_bank(value)
            return True
        return False
    
    def get_state(self):
        """Текущее состояние банков"""
        return {
            "current_bank": self.current_bank,
            "num_banks": self.num_banks,
            "window": f"0x{self.start:04X}-0x{self.end:04X}",
            "switch_port": self.switch_port,
            "switch_addr": self.switch_addr
        }
    
    def reset(self):
        """Сброс на банк 0"""
        self.current_bank = 0

class BankedROMRegion(MemoryRegion):
    """Банковое ПЗУ: окно в адресном пространстве, через которое
    виден один из банков ROM.
    
    Переключение банков:
    - через IO-порт (switch_port) — запись в порт выбирает банк
    - через адрес памяти (switch_addr) — запись по адресу выбирает банк
    
    В отличие от BankedRegion (RAM), данные ROM не изменяются.
    Применение: Вектор-06Ц, Орион-128 и другие системы с банковым ПЗУ.
    """
    
    def __init__(self, start, end, banks=None, switch_port=None,
                 switch_addr=None, name="BankedROM"):
        """
        Args:
            start, end: окно в адресном пространстве
            banks: список банков ROM, каждый банк — dict {offset: byte}
            switch_port: порт IO для переключения банков
            switch_addr: адрес памяти для переключения банков
        """
        super().__init__(start, end, name)
        self.window_size = end - start + 1
        self.banks = banks if banks is not None else []
        self.num_banks = len(self.banks)
        self.switch_port = switch_port
        self.switch_addr = switch_addr
        self.current_bank = 0
    
    def select_bank(self, bank_num):
        """Переключить банк"""
        if self.num_banks == 0:
            return
        bank_num &= 0xFF
        self.current_bank = bank_num % self.num_banks
    
    def read(self, addr):
        """Чтение из текущего банка ROM"""
        if not self.contains(addr):
            return 0xFF
        if self.num_banks == 0:
            return 0xFF
        offset = addr - self.start
        return self.banks[self.current_bank].get(offset, 0xFF)
    
    def write(self, addr, value):
        """Запись игнорируется (ROM), но switch_addr переключает банк.
        Возвращает True, если запись обработана (переключение банка)."""
        if self.switch_addr is not None and addr == self.switch_addr:
            self.select_bank(value)
            return True
        return False  # ROM не пишется
    
    def io_write(self, port, value):
        """Обработка записи в IO-порт (переключение банка)"""
        if self.switch_port is not None and port == self.switch_port:
            self.select_bank(value)
            return True
        return False
    
    def load_bank(self, bank_num, data):
        """Загрузить данные в банк.
        Args:
            bank_num: номер банка
            data: dict {offset: byte} или list байт
        """
        # Расширяем список банков при необходимости
        while len(self.banks) <= bank_num:
            self.banks.append({})
        self.num_banks = len(self.banks)
        # Загружаем данные
        if isinstance(data, (list, tuple, bytes)):
            self.banks[bank_num] = {i: b for i, b in enumerate(data)}
        else:
            self.banks[bank_num] = dict(data)
    
    def get_state(self):
        """Текущее состояние банков"""
        return {
            "current_bank": self.current_bank,
            "num_banks": self.num_banks,
            "window": f"0x{self.start:04X}-0x{self.end:04X}",
            "switch_port": self.switch_port,
            "switch_addr": self.switch_addr
        }
    
    def reset(self):
        """Сброс на банк 0"""
        self.current_bank = 0
