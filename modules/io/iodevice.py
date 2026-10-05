class IODevice:
    """Базовый класс IO-устройства.
    
    Каждое устройство занимает диапазон портов [base_port, base_port + port_count - 1].
    Подключается к MemoryBus через register_io на каждый порт диапазона.
    """
    
    def __init__(self, base_port, port_count, name="IODevice"):
        self.base_port = base_port & 0xFF
        self.port_count = port_count
        self.name = name
    
    def io_read(self, port) -> int:
        """Чтение из порта. Переопределяется подклассами."""
        return 0xFF
    
    def io_write(self, port, value):
        """Запись в порт. Переопределяется подклассами."""
        pass
    
    def reset(self):
        """Сброс устройства. Переопределяется подклассами."""
        pass
    
    def tick(self, cycles=1):
        """Вызывается каждый такт процессора. Переопределяется подклассами.
        Используется для таймеров, счётчиков и т.д.
        """
        pass
    
    def register_to_bus(self, bus):
        """Зарегистрировать устройство на шине (все порты диапазона)."""
        for i in range(self.port_count):
            bus.register_io(self.base_port + i, self)
    
    def unregister_from_bus(self, bus):
        """Удалить устройство с шины."""
        for i in range(self.port_count):
            bus.unregister_io(self.base_port + i)
    
    def get_state(self):
        """Состояние устройства для отладки. Переопределяется подклассами."""
        return {"name": self.name, "base_port": self.base_port}
