"""
MMIORegion — регион памяти, отражающий обращения в порты устройства.
Вариант Д: конфигурация через регионы + плоский индекс для O(1)-доступа.

Поддерживает:
- Одиночные маппинги: адрес памяти → порт устройства
- Диапазоны: последовательные адреса → последовательные порты
- Нелинейные маппинги: разрозненные адреса → одно устройство

Устройства НЕ меняются — они продолжают работать через io_read/io_write.
"""


class MMIORegion:
    """Регион памяти, делегирующий обращения в порты устройства."""

    def __init__(self, device=None, name="MMIO"):
        self.device = device          # Ссылка на устройство (связывается в system.py)
        self.name = name
        self.mappings = []            # [(addr, port), ...]
        self._device_name = ""        # Имя устройства для отложенной связи

    def add_mapping(self, addr, port):
        """Добавить одиночный маппинг: адрес памяти → порт"""
        self.mappings.append((addr, port))

    def add_range(self, start_addr, start_port, count):
        """Добавить диапазон: count последовательных адресов → портов"""
        for i in range(count):
            self.mappings.append((start_addr + i, start_port + i))

    def set_device_name(self, name):
        """Установить имя устройства для отложенной связи"""
        self._device_name = name

    def build_index(self):
        """Построить плоский индекс {адрес_памяти: порт}"""
        index = {}
        for addr, port in self.mappings:
            index[addr] = port
        return index

    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "device": self._device_name,
            "mappings_count": len(self.mappings),
        }

    def contains(self, addr):
        """Проверка, содержит ли регион адрес.
        Возвращает False — MMIO обрабатывается через _mmio_index,
        а не через общий цикл регионов.
        """
        return False
