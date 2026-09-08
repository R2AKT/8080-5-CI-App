"""
8257/8237 — контроллеры ПДП (прямого доступа к памяти).
Итерация E4: ПДП.

Различия:
  - 8257 (КР580ВТ57): память ↔ устройство
  - 8237: память ↔ устройство + память ↔ память + программный запуск

Сигналы:
  - HOLD → CPU (запрос захвата шины)
  - HLDA ← CPU (подтверждение захвата)
  - DREQ0-DREQ3 ← устройства (запрос ПДП)
  - DACK0-DACK3 → устройства (подтверждение ПДП)
"""

from .iodevice import IODevice

class I8257(IODevice):
    """8257 (КР580ВТ57) — контроллер ПДП (базовый).
    
    4 канала, память ↔ устройство.
    Режимы:
      MODE_VERIFY — проверка адреса (без передачи данных)
      MODE_WRITE  — память → устройство
      MODE_READ   — устройство → память
    """
    
    # Режимы передачи
    MODE_VERIFY = 0      # Проверка адреса
    MODE_WRITE = 1       # Память → устройство
    MODE_READ = 2        # Устройство → память
    MODE_INVALID = 3     # Запрещён
    
    def __init__(self, base_port, name="I8257"):
        super().__init__(base_port, 16, name)  # 16 портов
        self.reset()
        # Callback для сигналов шины
        self.on_hold_request = None      # Запрос захвата шины
        self.on_hold_release = None      # Освобождение шины
        self.on_transfer_complete = None # Завершение передачи
        # Callback для чтения/записи устройства
        self.on_device_read = None       # Чтение из устройства
        self.on_device_write = None      # Запись в устройство
        # Ссылка на шину памяти (устанавливается извне)
        self.memory_bus = None
    
    def reset(self):
        """Сброс контроллера"""
        # Каналы
        self.channels = [
            {
                "addr": 0,          # Начальный адрес
                "count": 0,         # Счётчик
                "mode": 0,          # Режим передачи
                "auto_init": False, # Автоматическая переинициализация
                "enabled": False,   # Канал активен
                "current_addr": 0,  # Текущий адрес
                "current_count": 0, # Текущий счётчик
            }
            for _ in range(4)
        ]
        # Регистры
        self.mode_register = 0
        self.command_register = 0
        self.request_register = 0
        self.mask_register = 0x0F  # Все каналы замаскированы
        # Состояние
        self.hold_active = False
        self.active_channel = None
        self.transfer_in_progress = False
        # Flip-Flop для 16-битной записи
        self.flip_flop = 0
    
    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из регистра"""
        offset = port - self.base_port
        
        # Порты 0-7: Адреса и счётчики каналов
        if 0 <= offset <= 7:
            channel = offset // 2
            reg_type = offset % 2  # 0=адрес, 1=счётчик
            if reg_type == 0:
                return self.channels[channel]["addr"] & 0xFF
            else:
                return self.channels[channel]["count"] & 0xFF
        
        # Порт 8: Регистр режима (только чтение)
        elif offset == 8:
            return self.mode_register
        
        # Порт 9: Статус (только чтение)
        elif offset == 9:
            return self._get_status()
        
        # Порт 13: Временный регистр (только чтение)
        elif offset == 13:
            return 0x00
        
        return 0xFF
    
    def io_write(self, port, value):
        """Запись в регистр"""
        offset = port - self.base_port
        # Порты 0-7: Адреса и счётчики каналов (16-бит через Flip-Flop)
        if 0 <= offset <= 7:
            channel = offset // 2
            reg_type = offset % 2  # 0=адрес, 1=счётчик
            if reg_type == 0:
                # Адрес канала
                if self.flip_flop == 0:
                    # LSB
                    self.channels[channel]["addr"] = (self.channels[channel]["addr"] & 0xFF00) | (value & 0xFF)
                    self.flip_flop = 1
                else:
                    # MSB
                    self.channels[channel]["addr"] = (self.channels[channel]["addr"] & 0x00FF) | ((value & 0xFF) << 8)
                    self.flip_flop = 0
            else:
                # Счётчик канала
                if self.flip_flop == 0:
                    # LSB
                    self.channels[channel]["count"] = (self.channels[channel]["count"] & 0xFF00) | (value & 0xFF)
                    self.flip_flop = 1
                else:
                    # MSB
                    self.channels[channel]["count"] = (self.channels[channel]["count"] & 0x00FF) | ((value & 0xFF) << 8)
                    self.flip_flop = 0
        # Порт 8: Регистр режима
        elif offset == 8:
            self.mode_register = value & 0xFF
            self._parse_mode_register()
        # Порт 9: Регистр управления
        elif offset == 9:
            self.command_register = value & 0xFF
        # Порт 10: Регистр запросов
        elif offset == 10:
            self.request_register = value & 0xFF
        # Порт 11: Регистр маски (один бит)
        elif offset == 11:
            bit = (value >> 2) & 0x03
            mask = value & 0x01
            if mask:
                self.mask_register |= (1 << bit)
            else:
                self.mask_register &= ~(1 << bit)
        # Порт 12: Сброс Flip-Flop
        elif offset == 12:
            self.flip_flop = 0  # ← ИЗМЕНЕНО: сброс Flip-Flop
        # Порт 13: Сброс контроллера
        elif offset == 13:
            self.reset()
        # Порт 14: Регистр маски (все биты)
        elif offset == 14:
            self.mask_register = value & 0x0F
        # Порт 15: Регистр запросов (все биты)
        elif offset == 15:
            self.request_register = value & 0x0F
        
    def _parse_mode_register(self):
        """Парсинг регистра режима"""
        for i in range(4):
            mode_bits = (self.mode_register >> (i * 2)) & 0x03
            self.channels[i]["mode"] = mode_bits
    
    def _get_status(self):
        """Получить статус контроллера"""
        status = 0
        for i in range(4):
            if self.channels[i]["enabled"]:
                status |= (1 << i)
        return status
    
    # =============================================
    # ЗАПРОС ПДП (от устройств)
    # =============================================
    def request_dma(self, channel):
        """Запрос ПДП от устройства (DREQ)"""
        if 0 <= channel < 4:
            if not (self.mask_register & (1 << channel)):
                self.channels[channel]["enabled"] = True
                self.channels[channel]["current_addr"] = self.channels[channel]["addr"]
                self.channels[channel]["current_count"] = self.channels[channel]["count"]
                # Запрашиваем шину
                if not self.hold_active:
                    self.hold_active = True
                    self.active_channel = channel
                    if self.on_hold_request:
                        self.on_hold_request()
    
    # =============================================
    # ВЫПОЛНЕНИЕ ПЕРЕДАЧИ
    # =============================================
    def tick(self, cycles=1):
        """Вызывается каждый такт. Выполняет передачу данных."""
        if not self.hold_active or self.active_channel is None:
            return
        
        ch = self.channels[self.active_channel]
        if not ch["enabled"]:
            self._release_hold()
            return
        
        # Выполняем передачу
        for _ in range(cycles):
            if ch["current_count"] <= 0:
                # Завершение передачи
                self._complete_transfer(self.active_channel)
                return
            
            addr = ch["current_addr"]
            
            if ch["mode"] == self.MODE_WRITE:
                # Память → устройство
                if self.memory_bus:
                    data = self.memory_bus.read(addr)
                    if self.on_device_write:
                        self.on_device_write(self.active_channel, data)
            elif ch["mode"] == self.MODE_READ:
                # Устройство → память
                if self.on_device_read:
                    data = self.on_device_read(self.active_channel)
                    if self.memory_bus:
                        self.memory_bus.write(addr, data)
            
            ch["current_addr"] += 1
            ch["current_count"] -= 1
    
    def _complete_transfer(self, channel):
        """Завершение передачи данных"""
        ch = self.channels[channel]
        
        if ch["auto_init"]:
            # Автоматическая переинициализация
            ch["current_addr"] = ch["addr"]
            ch["current_count"] = ch["count"]
        else:
            # Канал завершён
            ch["enabled"] = False
            self._release_hold()
        
        if self.on_transfer_complete:
            self.on_transfer_complete(channel)
    
    def _release_hold(self):
        """Освобождение шины"""
        self.hold_active = False
        self.active_channel = None
        if self.on_hold_release:
            self.on_hold_release()

    # =============================================
    # ИНТЕГРАЦИЯ С СИСТЕМОЙ (итерация 10.2)
    # =============================================
    def set_memory_bus(self, bus):
        """Подключить шину памяти к DMA"""
        self.memory_bus = bus

    def is_active(self):
        """Проверка активности передачи"""
        return self.hold_active and self.active_channel is not None
        
    def perform_transfer(self, bus=None):
        """Выполнить передачу до завершения.
        Если bus передан, подключает его."""
        if bus is not None:
            self.memory_bus = bus
        # Выполняем передачу до завершения
        max_iterations = 100000
        iterations = 0
        while self.is_active() and iterations < max_iterations:
            self.tick(cycles=1)
            iterations += 1
        
    # =============================================
    # СОСТОЯНИЕ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "hold_active": self.hold_active,
            "active_channel": self.active_channel,
            "mode_register": f"0x{self.mode_register:02X}",
            "mask_register": f"0x{self.mask_register:02X}",
            "channels": [
                {
                    "addr": f"0x{ch['addr']:02X}",
                    "count": f"0x{ch['count']:02X}",
                    "mode": ch["mode"],
                    "enabled": ch["enabled"],
                }
                for ch in self.channels
            ]
        }


class I8237(I8257):
    """8237 — расширенный контроллер ПДП.
    
    Добавляет к 8257:
    - Память ↔ память (передача из памяти в память)
    - Программный запуск цикла обмена
    """
    
    # Дополнительные режимы
    MODE_MEM_TO_MEM = 4  # Память → память
    
    def __init__(self, base_port, name="I8237"):
        super().__init__(base_port, name)
        # Дополнительные регистры 8237
        self.flip_flop = 0        # Flip-Flop для LSB/MSB
        self.software_request = 0 # Программный запрос
    
    def reset(self):
        """Сброс контроллера"""
        super().reset()
        self.flip_flop = 0
        self.software_request = 0
        self._mem_to_mem_dst = 1  # ← ДОБАВЛЕНО: канал-приёмник по умолчанию

    # =============================================
    # ЗАПРОС ПДП (от устройств)
    # =============================================    
    def request_dma(self, channel):
        """Запрос ПДП от устройства (переопределяется для 8237).
        Инициализирует канал-приёмник для режима память↔память."""
        super().request_dma(channel)
        # Если активен режим память↔память, инициализируем канал-приёмник
        if (self.command_register & 0x01) and channel == 0:
            dst = self._mem_to_mem_dst
            if 0 <= dst < 4:
                self.channels[dst]["enabled"] = True
                self.channels[dst]["current_addr"] = self.channels[dst]["addr"]
                self.channels[dst]["current_count"] = self.channels[dst]["count"]
                 
    # =============================================
    # ПАМЯТЬ ↔ ПАМЯТЬ (только 8237)
    # =============================================
    def request_mem_to_mem(self, src_channel, dst_channel, count):
        """Запрос передачи память → память (только 8237).
        
        Args:
            src_channel: канал источника (читает из памяти)
            dst_channel: канал приёмника (записывает в память)
            count: количество байт для передачи
        """
        if 0 <= src_channel < 4 and 0 <= dst_channel < 4:
            # Настраиваем канал источника на чтение из памяти
            self.channels[src_channel]["mode"] = self.MODE_MEM_TO_MEM
            self.channels[src_channel]["count"] = count
            self.channels[src_channel]["current_count"] = count
            self.channels[src_channel]["current_addr"] = self.channels[src_channel]["addr"]  # ← ДОБАВЛЕНО
            self.channels[src_channel]["enabled"] = True
            # Настраиваем канал приёмника на запись в память
            self.channels[dst_channel]["mode"] = self.MODE_MEM_TO_MEM
            self.channels[dst_channel]["count"] = count
            self.channels[dst_channel]["current_count"] = count
            self.channels[dst_channel]["current_addr"] = self.channels[dst_channel]["addr"]  # ← ДОБАВЛЕНО
            self.channels[dst_channel]["enabled"] = True
            # Запрашиваем шину
            if not self.hold_active:
                self.hold_active = True
                self.active_channel = src_channel
                self._mem_to_mem_dst = dst_channel
                if self.on_hold_request:
                    self.on_hold_request()
    
    def tick(self, cycles=1):
        """Вызывается каждый такт. Выполняет передачу данных."""
        if not self.hold_active or self.active_channel is None:
            return
        ch = self.channels[self.active_channel]
        if not ch["enabled"]:
            self._release_hold()
            return
        # проверяем бит 0 командного регистра ИЛИ режим канала
        if (self.command_register & 0x01) or ch["mode"] == self.MODE_MEM_TO_MEM:
            self._tick_mem_to_mem(cycles)
        else:
            super().tick(cycles)
    
    def _tick_mem_to_mem(self, cycles=1):
        """Передача память ↔ память (только 8237)"""
        src_ch = self.channels[self.active_channel]
        dst_ch = self.channels[self._mem_to_mem_dst]
        for _ in range(cycles):
            # ← ИЗМЕНЕНО: было `<= 0`, стало `< 0`
            if src_ch["current_count"] < 0:
                # Завершение передачи
                src_ch["enabled"] = False
                dst_ch["enabled"] = False
                self._release_hold()
                if self.on_transfer_complete:
                    self.on_transfer_complete(self.active_channel)
                return
            # Читаем из памяти источника
            src_addr = src_ch["current_addr"]
            if self.memory_bus:
                data = self.memory_bus.read(src_addr)
                dst_addr = dst_ch["current_addr"]
                self.memory_bus.write(dst_addr, data)
            src_ch["current_addr"] += 1
            src_ch["current_count"] -= 1
            dst_ch["current_addr"] += 1
            dst_ch["current_count"] -= 1

    # =============================================
    # ПРОГРАММНЫЙ ЗАПУСК ЦИКЛА ОБМЕНА (только 8237)
    # =============================================
    def software_trigger(self, channel):
        """Программный запуск цикла обмена (только 8237)"""
        if 0 <= channel < 4:
            self.software_request |= (1 << channel)
            self.request_dma(channel)
    
    def io_write(self, port, value):
        """Запись в регистр (8237: структура портов реального чипа)"""
        offset = port - self.base_port

        # Порты 0-7: Адреса и счётчики каналов (базовый класс)
        if 0 <= offset <= 7:
            super().io_write(port, value)
            return

        # Порт 8: Командный регистр (бит 0 = память↔память)
        if offset == 8:
            self.command_register = value & 0xFF
            return

        # Порт 9: Регистр запросов (программный запрос)
        if offset == 9:
            channel = value & 0x03      # Биты 0-1: номер канала
            if value & 0x04:            # Бит 2: запрос
                self.software_request |= (1 << channel)
                self.request_dma(channel)
            else:
                self.software_request &= ~(1 << channel)
            return

        # Порт 10: Регистр маски (один бит)
        if offset == 10:
            bit = (value >> 2) & 0x03
            mask = value & 0x01
            if mask:
                self.mask_register |= (1 << bit)
            else:
                self.mask_register &= ~(1 << bit)
            return

        # Порт 11: Регистр режима
        if offset == 11:
            self.mode_register = value & 0xFF
            self._parse_mode_register()
            return

        # Порт 12: Сброс (мастер)
        if offset == 12:
            self.flip_flop = 0
            return

        # Порт 13: Сброс маски (все каналы не замаскированы)
        if offset == 13:
            self.mask_register = 0x00
            return

        # Порт 14: Установка маски (все биты)
        if offset == 14:
            self.mask_register = value & 0x0F
            return

        # Остальное — базовый класс
        super().io_write(port, value)
    
    def get_state(self):
        """Состояние для отладки"""
        state = super().get_state()
        state.update({
            "flip_flop": self.flip_flop,
            "software_request": f"0x{self.software_request:02X}",
        })
        return state