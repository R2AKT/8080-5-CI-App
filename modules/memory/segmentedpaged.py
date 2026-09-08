from .memory_bus import MemoryBus, MemoryRegion, RAMRegion, ROMRegion

class SegmentedPagedRegion(MemoryRegion):
    """Сегментно-страничная память: 64КБ разбиты на сегменты,
    внутри каждого сегмента переключение страниц через порты IO.
    Количество портов соответствует количеству сегментов.
    
    Пример:
    - 64КБ разбиты на 4 сегмента по 16КБ
    - Каждый сегмент имеет свой порт IO для переключения страниц
    - Порт 0x00 для сегмента 0 (0x0000-0x3FFF)
    - Порт 0x01 для сегмента 1 (0x4000-0x7FFF)
    - Порт 0x02 для сегмента 2 (0x8000-0xBFFF)
    - Порт 0x03 для сегмента 3 (0xC000-0xFFFF)
    - Запись в порт выбирает физическую страницу для сегмента
    """
    
    def __init__(self, start, end, segment_size=16384, num_physical_pages=16,
                 base_port=0x00, name="SegmentedPagedRAM"):
        """
        Args:
            start, end: окно в адресном пространстве (обычно 0x0000-0xFFFF)
            segment_size: размер сегмента в байтах (обычно 16384)
            num_physical_pages: количество физических страниц
            base_port: базовый порт IO (порты base_port..base_port+num_segments-1)
        """
        super().__init__(start, end, name)
        self.segment_size = segment_size
        self.num_segments = (end - start + 1) // segment_size
        self.num_physical_pages = num_physical_pages
        self.base_port = base_port
        
        # Физические страницы
        self.physical_pages = [{} for _ in range(num_physical_pages)]
        
        # Таблица маппинга: сегмент -> физическая страница
        self.segment_table = [i % num_physical_pages for i in range(self.num_segments)]
    
    def _get_segment(self, addr):
        """Определить сегмент для адреса"""
        return (addr - self.start) // self.segment_size
    
    def _get_segment_offset(self, addr):
        """Определить смещение внутри сегмента"""
        return (addr - self.start) % self.segment_size
    
    def read(self, addr):
        """Чтение из текущей физической страницы сегмента"""
        if not self.contains(addr):
            return 0xFF
        segment = self._get_segment(addr)
        offset = self._get_segment_offset(addr)
        ppage = self.segment_table[segment]
        return self.physical_pages[ppage].get(offset, 0x00)
    
    def write(self, addr, value):
        """Запись в текущую физическую страницу сегмента"""
        if not self.contains(addr):
            return
        segment = self._get_segment(addr)
        offset = self._get_segment_offset(addr)
        ppage = self.segment_table[segment]
        self.physical_pages[ppage][offset] = value & 0xFF
    
    def io_write(self, port, value):
        """Обработка записи в IO-порт (переключение страницы сегмента)"""
        if self.base_port <= port < self.base_port + self.num_segments:
            segment = port - self.base_port
            self.segment_table[segment] = value % self.num_physical_pages
            return True
        return False
    
    def get_state(self):
        """Текущее состояние таблицы сегментов"""
        return {
            "segment_table": self.segment_table.copy(),
            "num_segments": self.num_segments,
            "num_physical_pages": self.num_physical_pages,
            "segment_size": self.segment_size,
            "base_port": self.base_port
        }
    
    def reset(self):
        """Сброс таблицы сегментов"""
        self.segment_table = [i % self.num_physical_pages for i in range(self.num_segments)]
