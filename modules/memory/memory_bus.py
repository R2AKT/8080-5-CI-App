"""
Шина памяти и IO для i8080-5 CI.
Итерация E1: фундамент модульности.

Модули памяти и IO подключаются к шине через register_memory / register_io.
Шина маршрутизирует чтение/запись по адресу (память) или порту (IO).
"""
"""
# Базовый класс IO-устройства для i8080-5 CI.
# Итерация E3: фундамент модульности IO.
# """
class IOBus:
    """Шина IO: порты 0x00-0xFF."""
    def __init__(self) -> None:
        self.ports: dict = {}

    def read(self, port: int) -> int:
        return self.ports.get(port & 0xFF, 0xFF)

    def write(self, port: int, value: int) -> None:
        self.ports[port & 0xFF] = value & 0xFF

class MemoryBus:
    """Шина памяти и IO.
    Маршрутизирует обращения по адресу к соответствующему модулю.
    """
    def __init__(self, size: int = 0x10000) -> None:
        self.size: int = size
        self.memory_regions: list = []
        self.io_devices: dict = {}
        self.io_range_devices = []
        self._unmapped_read = 0xFF
        # === Memory-Mapped IO ===
        self._mmio_regions = []   # Список MMIO-регионов
        self._mmio_index = {}     # Плоский индекс {адрес: (устройство, порт)}

    # =============================================
    # РЕГИСТРАЦИЯ МОДУЛЕЙ
    # =============================================
    def register_memory(self, region: 'MemoryRegion') -> None:
        """Зарегистрировать регион памяти."""
        self.memory_regions.append(region)

    def unregister_memory(self, region: 'MemoryRegion') -> None:
        """Удалить регион памяти"""
        if region in self.memory_regions:
            self.memory_regions.remove(region)

    def register_io(self, port: int, device: 'IODevice') -> None:
        """Зарегистрировать IO-устройство по порту"""
        self.io_devices[port & 0xFF] = device

    def unregister_io(self, port: int) -> None:
        """Удалить IO-устройство"""
        port &= 0xFF
        if port in self.io_devices:
            del self.io_devices[port]

    # =============================================
    # ЧТЕНИЕ / ЗАПИСЬ ПАМЯТИ
    # =============================================
    def read(self, addr: int) -> int:
        """Чтение байта из памяти"""
        addr &= 0xFFFF
        # === MMIO: приоритет над обычной памятью ===
        entry = self._mmio_index.get(addr)
        if entry is not None:
            device, port = entry
            return device.io_read(port)
        # Ленивый импорт для избежания NameError и циклического импорта
        from .shadow import ShadowROMRegion
        # Уведомляем ShadowROM о чтении адресов, НЕ принадлежащих ROM
        for region in self.memory_regions:
            if isinstance(region, ShadowROMRegion) and not region.contains(addr):
                region.read(addr)
        # Читаем из регионов
        for region in self.memory_regions:
            if region.contains(addr):
                return region.read(addr)
        return self._unmapped_read

    def write(self, addr: int, value: int) -> None:
        """Запись байта в память"""
        addr &= 0xFFFF
        # === MMIO: приоритет над обычной памятью ===
        entry = self._mmio_index.get(addr)
        if entry is not None:
            device, port = entry
            device.io_write(port, value)
            return
        # Ленивый импорт для избежания NameError и циклического импорта
        from .shadow import ShadowROMRegion
        # Уведомляем ShadowROM о записи адресов, НЕ принадлежащих ROM
        for region in self.memory_regions:
            if isinstance(region, ShadowROMRegion) and not region.contains(addr):
                region.write(addr, value)
        # Записываем в регионы
        for region in self.memory_regions:
            if region.contains(addr):
                region.write(addr, value)
                return

    def read_word(self, addr: int) -> int:
        """Чтение слова (little-endian)"""
        addr &= 0xFFFF
        low = self.read(addr)
        high = self.read((addr + 1) & 0xFFFF)
        return (high << 8) | low

    def write_word(self, addr: int, value: int) -> None:
        """Запись слова (little-endian)"""
        addr &= 0xFFFF
        self.write(addr, value & 0xFF)
        self.write((addr + 1) & 0xFFFF, (value >> 8) & 0xFF)

    # =============================================
    # ЧТЕНИЕ / ЗАПИСЬ IO
    # =============================================
    def io_read(self, port: int) -> int:
        """Чтение из IO-порта"""
        port &= 0xFF
        # Сначала проверяем регионы памяти (банковые/теневые)
        for region in self.memory_regions:
            if hasattr(region, 'io_read'):
                result = region.io_read(port)
                if result is not None:
                    return result
            if hasattr(region, 'io_access'):
                region.io_access(port, is_write=False)
        # Затем IO-устройства
        if port in self.io_devices:
            return self.io_devices[port].io_read(port)
        return 0xFF

    def io_write(self, port: int, value: int) -> None:
        """Запись в IO-порт"""
        port &= 0xFF
        # Сначала проверяем регионы памяти (банковые/теневые)
        for region in self.memory_regions:
            if hasattr(region, 'io_write'):
                if region.io_write(port, value):
                    return  # Запись обработана регионом
            if hasattr(region, 'io_access'):
                region.io_access(port, is_write=True)
        # Затем IO-устройства
        if port in self.io_devices:
            self.io_devices[port].io_write(port, value)
    
    # =============================================
    # Memory-Mapped IO
    # =============================================
    def add_mmio_region(self, region: object) -> None:
        """Добавить MMIO-регион"""
        self._mmio_regions.append(region)

    def build_mmio_index(self) -> None:
        """Построить плоский индекс для O(1)-доступа.
        Вызывается после связывания устройств с регионами.
        """
        self._mmio_index.clear()
        for region in self._mmio_regions:
            if region.device is None:
                continue
            port_index = region.build_index()
            for addr, port in port_index.items():
                self._mmio_index[addr] = (region.device, port)

    def clear_mmio(self) -> None:
        """Очистить все MMIO-маппинги"""
        self._mmio_regions.clear()
        self._mmio_index.clear()

    # =============================================
    # УТИЛИТЫ
    # =============================================
    def reset(self) -> None:
        """Сброс всех модулей шины"""
        for region in self.memory_regions:
            region.reset()
        for device in self.io_devices.values():
            if hasattr(device, 'reset'):
                device.reset()
    
    def get_memory_map(self) -> list:
        """Вернуть карту памяти для отображения/отладки"""
        # Ленивый импорт для избежания NameError и циклического импорта
        from .banked import BankedRegion
        result = []
        for region in self.memory_regions:
            entry = {
                "name": region.name,
                "start": region.start,
                "end": region.end,
                "size": region.end - region.start + 1,
                "type": type(region).__name__
            }
            # Для банковой памяти добавляем информацию о банках
            if isinstance(region, BankedRegion):
                entry["current_bank"] = region.current_bank
                entry["num_banks"] = region.num_banks
            result.append(entry)
        return result

class MemoryRegion:
    """Базовый регион памяти (абстрактный).
    Подклассы: RAMRegion, ROMRegion, ShadowROM, BankedMemory и т.д.
    """
    def __init__(self, start: int, end: int, name: str = "region") -> None:
        self.start = start & 0xFFFF
        self.end = end & 0xFFFF
        self.name = name

    def contains(self, addr: int) -> bool:
        """Проверяет, принадлежит ли адрес региону"""
        return self.start <= addr <= self.end

    def read(self, addr: int) -> int:
        """Чтение байта. Переопределяется подклассами."""
        return 0xFF

    def write(self, addr: int, value: int) -> None:
        """Запись байта. Переопределяется подклассами."""
        pass

    def reset(self) -> None:
        """Сброс региона (например, при сбросе системы)."""
        pass

class RAMRegion(MemoryRegion):
    """RAM: чтение и запись. Может использовать внешний dict как хранилище."""
    def __init__(self, start: int, end: int, data: dict | None = None, name: str = "RAM") -> None:
        super().__init__(start, end, name)
        self.data = data if data is not None else {}

    def read(self, addr: int) -> int:
        return self.data.get(addr, 0x00)

    def write(self, addr: int, value: int) -> None:
        self.data[addr] = value & 0xFF

    def reset(self) -> None:
        """Очистить RAM"""
        self.data.clear()

class ROMRegion(MemoryRegion):
    """ROM: только чтение. Запись игнорируется."""
    def __init__(self, start: int, end: int, data: dict | None = None, name: str = "ROM") -> None:
        super().__init__(start, end, name)
        self.data = dict(data) if data else {}

    def read(self, addr: int) -> int:
        return self.data.get(addr, 0xFF)

    def write(self, addr: int, value: int) -> None:
        pass  # ROM не пишется

    def reset(self) -> None:
        pass  # ROM не сбрасывается
