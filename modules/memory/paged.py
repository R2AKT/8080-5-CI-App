from .memory_bus import MemoryBus, MemoryRegion, RAMRegion, ROMRegion

class PagedRegion(MemoryRegion):
    """Страничная память: адресное пространство разбито на страницы,
    каждая страница независимо маппится на физическую страницу.
    
    Переключение страниц:
    - через порты IO (по порту на каждую виртуальную страницу)
    - через адреса памяти (по адресу на каждую виртуальную страницу)
    
    Пример:
    - Адресное пространство 64КБ разбито на 4 страницы по 16КБ
    - 16 физических страниц по 16КБ (всего 256КБ физической памяти)
    - Порты 0x00-0x03 выбирают физические страницы для виртуальных страниц 0-3
    """
    
    def __init__(self, start, end, page_size=16384, num_physical_pages=16,
                 switch_ports=None, switch_addrs=None, name="PagedRAM"):
        """
        Args:
            start, end: окно в адресном пространстве
            page_size: размер страницы в байтах (1024, 4096, 16384)
            num_physical_pages: количество физических страниц
            switch_ports: список портов IO для каждой виртуальной страницы
            switch_addrs: список адресов памяти для каждой виртуальной страницы
        """
        super().__init__(start, end, name)
        self.page_size = page_size
        self.num_virtual_pages = (end - start + 1) // page_size
        self.num_physical_pages = num_physical_pages
        self.switch_ports = switch_ports or []
        self.switch_addrs = switch_addrs or []
        
        # Физические страницы
        self.physical_pages = [{} for _ in range(num_physical_pages)]
        
        # Таблица маппинга: виртуальная страница -> физическая страница
        self.page_table = [i % num_physical_pages for i in range(self.num_virtual_pages)]
    
    def _get_virtual_page(self, addr):
        """Определить виртуальную страницу для адреса"""
        return (addr - self.start) // self.page_size
    
    def _get_page_offset(self, addr):
        """Определить смещение внутри страницы"""
        return (addr - self.start) % self.page_size
    
    def read(self, addr):
        """Чтение из текущей физической страницы"""
        if not self.contains(addr):
            return 0xFF
        vpage = self._get_virtual_page(addr)
        offset = self._get_page_offset(addr)
        ppage = self.page_table[vpage]
        return self.physical_pages[ppage].get(offset, 0x00)
    
    def write(self, addr, value):
        """Запись в текущую физическую страницу, или переключение страницы"""
        if not self.contains(addr):
            return
        
        # Переключение страницы по записи в switch_addr
        if addr in self.switch_addrs:
            vpage = self.switch_addrs.index(addr)
            if vpage < self.num_virtual_pages:
                self.page_table[vpage] = value % self.num_physical_pages
                return
        
        # Обычная запись
        vpage = self._get_virtual_page(addr)
        offset = self._get_page_offset(addr)
        ppage = self.page_table[vpage]
        self.physical_pages[ppage][offset] = value & 0xFF
    
    def io_write(self, port, value):
        """Обработка записи в IO-порт (переключение страницы)"""
        if port in self.switch_ports:
            vpage = self.switch_ports.index(port)
            if vpage < self.num_virtual_pages:
                self.page_table[vpage] = value % self.num_physical_pages
                return True
        return False
    
    def get_state(self):
        """Текущее состояние таблицы маппинга"""
        return {
            "page_table": self.page_table.copy(),
            "num_virtual_pages": self.num_virtual_pages,
            "num_physical_pages": self.num_physical_pages,
            "page_size": self.page_size
        }
    
    def reset(self):
        """Сброс таблицы маппинга"""
        self.page_table = [i % self.num_physical_pages for i in range(self.num_virtual_pages)]
