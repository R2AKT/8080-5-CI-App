from .memory_bus import MemoryBus, MemoryRegion, RAMRegion, ROMRegion

class SegmentedRegion(MemoryRegion):
    """Сегментная память: адресное пространство разбито на сегменты,
    каждый сегмент имеет базовый адрес в физической памяти.
    
    Переключение сегментов:
    - через порт IO (запись в порт выбирает текущий сегмент)
    - через адрес памяти
    
    Пример:
    - Адресное пространство 64КБ
    - Сегментный регистр определяет текущий сегмент
    - Физическая память: 16 сегментов по 64КБ (всего 1МБ)
    - Запись в порт 0x00 выбирает сегмент
    """
    
    def __init__(self, start, end, num_segments=16,
                 switch_port=None, switch_addr=None, name="SegmentedRAM"):
        """
        Args:
            start, end: окно в адресном пространстве
            num_segments: количество сегментов в физической памяти
            switch_port: порт IO для переключения сегмента
            switch_addr: адрес памяти для переключения сегмента
        """
        super().__init__(start, end, name)
        self.num_segments = num_segments
        self.switch_port = switch_port
        self.switch_addr = switch_addr
        
        # Сегменты физической памяти
        self.segments = [{} for _ in range(num_segments)]
        
        # Текущий сегмент
        self.current_segment = 0
    
    def read(self, addr):
        """Чтение из текущего сегмента"""
        if not self.contains(addr):
            return 0xFF
        offset = addr - self.start
        return self.segments[self.current_segment].get(offset, 0x00)
    
    def write(self, addr, value):
        """Запись в текущий сегмент, или переключение сегмента"""
        if not self.contains(addr):
            return
        
        # Переключение сегмента по записи в switch_addr
        if self.switch_addr is not None and addr == self.switch_addr:
            self.current_segment = value % self.num_segments
            return
        
        # Обычная запись
        offset = addr - self.start
        self.segments[self.current_segment][offset] = value & 0xFF
    
    def io_write(self, port, value):
        """Обработка записи в IO-порт (переключение сегмента)"""
        if self.switch_port is not None and port == self.switch_port:
            self.current_segment = value % self.num_segments
            return True
        return False
    
    def get_state(self):
        """Текущее состояние"""
        return {
            "current_segment": self.current_segment,
            "num_segments": self.num_segments
        }
    
    def reset(self):
        """Сброс на сегмент 0"""
        self.current_segment = 0
