"""
8251 (КР580ВВ51) — USART (Universal Synchronous/Asynchronous Receiver/Transmitter).
Итерация E5: расширенные IO-устройства.

Регистры (2 порта):
  offset 0: Data / Status (чтение), Data / Mode/Command (запись)
  offset 1: Mode Register / Command Register / Status Register

Режимы:
  - Синхронный
  - Асинхронный (1x, 16x, 64x baud rate)

Сигналы прерываний:
  TxRDY — передатчик готов к передаче
  RxRDY — приёмник принял данные
"""
from .iodevice import IODevice


class I8251(IODevice):
    """8251 USART — последовательный порт"""
    
    # Состояния инициализации
    STATE_RESET = 0       # После сброса, ожидание Mode Register
    STATE_MODE = 1        # Mode Register записан, ожидание Command Register
    STATE_READY = 2       # Инициализирован, готов к работе
    
    def __init__(self, base_port, name="I8251"):
        super().__init__(base_port, 2, name)
        self.reset()
        # Callback для прерываний
        self.on_interrupt = None  # callback(signal, active)
        # Callback для передачи данных внешнему устройству
        self.on_transmit = None   # callback(data)
        # Внешние данные для приёма (устанавливаются извне)
        self._rx_queue = []
    
    def reset(self):
        """Сброс USART"""
        self.state = self.STATE_RESET
        self.mode_register = 0
        self.command_register = 0
        self.status_register = 0
        self.tx_data = 0
        self.rx_data = 0
        self.tx_ready = True
        self.rx_ready = False
        self._rx_queue = []
    
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Data Register (чтение)
            self.rx_ready = False
            self.status_register &= ~0x02  # Сбрасываем RxRDY
            return self.rx_data
        elif offset == 1:
            # Status Register (чтение)
            return self._get_status()
        return 0xFF
    
    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        if offset == 0:
            if self.state == self.STATE_READY:
                # Data Register (запись)
                self.tx_data = value
                self.tx_ready = False
                self.status_register &= ~0x01  # Сбрасываем TxRDY
                if self.on_transmit:
                    self.on_transmit(value)
                # После передачи TxRDY восстанавливается
                self.tx_ready = True
                self.status_register |= 0x01
                if self.on_interrupt:
                    self.on_interrupt('TxRDY', True)
            elif self.state == self.STATE_RESET:
                # Mode Register (запись)
                self.mode_register = value
                self.state = self.STATE_MODE
            elif self.state == self.STATE_MODE:
                # Command Register (запись)
                self.command_register = value
                self.state = self.STATE_READY
        elif offset == 1:
            if self.state == self.STATE_RESET:
                # Mode Register (запись)
                self.mode_register = value
                self.state = self.STATE_MODE
            elif self.state == self.STATE_MODE:
                # Command Register (запись)
                self.command_register = value
                self.state = self.STATE_READY
    
    def _get_status(self):
        """Получить статус"""
        status = 0
        if self.tx_ready:
            status |= 0x01  # TxRDY
        if self.rx_ready:
            status |= 0x02  # RxRDY
        return status
    
    def receive_data(self, data):
        """Приём данных извне (устанавливается извне)"""
        self.rx_data = data
        self.rx_ready = True
        self.status_register |= 0x02
        if self.on_interrupt:
            self.on_interrupt('RxRDY', True)
    
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "state": self.state,
            "mode_register": f"0x{self.mode_register:02X}",
            "command_register": f"0x{self.command_register:02X}",
            "status_register": f"0x{self._get_status():02X}",
            "tx_ready": self.tx_ready,
            "rx_ready": self.rx_ready,
        }
