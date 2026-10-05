"""
16550 UART — Universal Asynchronous Receiver/Transmitter с FIFO.
Итерация E5: расширенные IO-устройства.

Регистры (8 портов, base_port + offset):
  offset 0: RBR (чтение) / THR (запись) / DLL (DLAB=1)
  offset 1: IER / DLM (DLAB=1)
  offset 2: IIR (чтение) / FCR (запись)
  offset 3: LCR (Line Control Register)
  offset 4: MCR (Modem Control Register)
  offset 5: LSR (Line Status Register)
  offset 6: MSR (Modem Status Register)
  offset 7: SCR (Scratch Register)

Прерывания:
  Rx Data Available (приоритет 2)
  Tx Holding Register Empty (приоритет 3)
  Rx Line Status (приоритет 1, наивысший)
  Modem Status (приоритет 4, низший)
"""
from .iodevice import IODevice
from collections import deque


class I16550(IODevice):
    """16550 UART — последовательный порт с FIFO"""

    # Биты LSR (Line Status Register)
    LSR_DR   = 0x01  # Data Ready
    LSR_OE   = 0x02  # Overrun Error
    LSR_PE   = 0x04  # Parity Error
    LSR_FE   = 0x08  # Framing Error
    LSR_BI   = 0x10  # Break Interrupt
    LSR_THRE = 0x20  # THR Empty
    LSR_TEMT = 0x40  # Transmitter Empty

    # Биты IER (Interrupt Enable Register)
    IER_RX   = 0x01  # Rx Data Available
    IER_TX   = 0x02  # Tx Holding Register Empty
    IER_LS   = 0x04  # Rx Line Status
    IER_MS   = 0x08  # Modem Status

    # Типы прерываний (IIR)
    INT_NONE = 0x01  # Нет прерываний
    INT_LS   = 0x06  # Rx Line Status (приоритет 1)
    INT_RX   = 0x04  # Rx Data Available (приоритет 2)
    INT_TX   = 0x02  # Tx Holding Register Empty (приоритет 3)
    INT_MS   = 0x00  # Modem Status (приоритет 4)

    def __init__(self, base_port, name="I16550"):
        super().__init__(base_port, 8, name)
        self.reset()
        # Callback для прерываний
        self.on_interrupt = None  # callback(active)
        # Callback для передачи данных внешнему устройству
        self.on_transmit = None   # callback(data)

    def reset(self):
        """Сброс UART"""
        self.rx_fifo = deque(maxlen=16)  # FIFO приёма (16 байт)
        self.tx_fifo = deque(maxlen=16)  # FIFO передачи (16 байт)
        self.ier = 0x00        # Interrupt Enable Register
        self.iir = self.INT_NONE  # Interrupt Identification Register
        self.fcr = 0x00        # FIFO Control Register
        self.lcr = 0x00        # Line Control Register
        self.mcr = 0x00        # Modem Control Register
        self.lsr = self.LSR_THRE | self.LSR_TEMT  # Line Status Register
        self.msr = 0x00        # Modem Status Register
        self.scr = 0x00        # Scratch Register
        self.dll = 0x00        # Divisor Latch Low
        self.dlm = 0x00        # Divisor Latch High
        self.tx_thr = 0x00     # Transmit Holding Register
        self.rx_ready = False  # Есть данные в приёмнике
        self.fifo_enabled = False  # FIFO включены

    @property
    def dlab(self):
        """DLAB бит в LCR"""
        return bool(self.lcr & 0x80)

    # =============================================
    # IO ЧТЕНИЕ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port

        if offset == 0:
            if self.dlab:
                return self.dll
            else:
                # RBR: чтение из FIFO приёма
                if self.rx_fifo:
                    data = self.rx_fifo.popleft()
                    self._update_lsr_after_rx()
                    self._check_interrupts()
                    return data
                return 0x00

        elif offset == 1:
            if self.dlab:
                return self.dlm
            else:
                return self.ier

        elif offset == 2:
            # IIR: чтение идентификации прерывания
            result = self.iir
            # Чтение IIR сбрасывает Tx прерывание
            if self.iir == self.INT_TX:
                self.iir = self.INT_NONE
                self._check_interrupts()
            return result

        elif offset == 3:
            return self.lcr

        elif offset == 4:
            return self.mcr

        elif offset == 5:
            return self.lsr

        elif offset == 6:
            result = self.msr
            self.msr &= 0xF0  # Сбрасываем биты изменения состояния
            return result

        elif offset == 7:
            return self.scr

        return 0xFF

    # =============================================
    # IO ЗАПИСЬ
    # =============================================
    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        value &= 0xFF

        if offset == 0:
            if self.dlab:
                self.dll = value
            else:
                # THR: запись в FIFO передачи
                self.tx_thr = value
                self.lsr &= ~(self.LSR_THRE | self.LSR_TEMT)
                self.tx_fifo.append(value)
                if self.on_transmit:
                    self.on_transmit(value)
                # После передачи THR освобождается
                self.lsr |= self.LSR_THRE | self.LSR_TEMT
                self._check_interrupts()

        elif offset == 1:
            if self.dlab:
                self.dlm = value
            else:
                self.ier = value & 0x0F
                self._check_interrupts()

        elif offset == 2:
            # FCR: FIFO Control Register (только запись)
            self.fcr = value
            if value & 0x01:
                self.fifo_enabled = True
            else:
                self.fifo_enabled = False
            # Биты 1-2: сброс FIFO
            if value & 0x02:
                self.rx_fifo.clear()
            if value & 0x04:
                self.tx_fifo.clear()

        elif offset == 3:
            self.lcr = value

        elif offset == 4:
            self.mcr = value

        elif offset == 5:
            pass  # LSR только чтение

        elif offset == 6:
            pass  # MSR только чтение

        elif offset == 7:
            self.scr = value

    # =============================================
    # ПРИЁМ ДАННЫХ ИЗВНЕ
    # =============================================
    def receive_data(self, data):
        """Приём данных извне (устанавливается извне)"""
        self.rx_fifo.append(data & 0xFF)
        self.lsr |= self.LSR_DR
        self.rx_ready = True
        self._check_interrupts()

    def receive_bytes(self, data_list):
        """Приём нескольких байтов извне"""
        for b in data_list:
            self.receive_data(b)

    # =============================================
    # ПРОВЕРКА ПРЕРЫВАНИЙ
    # =============================================
    def _check_interrupts(self):
        """Проверить и установить активное прерывание по приоритету"""
        # Приоритет: LS > RX > TX > MS
        if (self.ier & self.IER_LS) and (self.lsr & (self.LSR_OE | self.LSR_PE | self.LSR_FE | self.LSR_BI)):
            self.iir = self.INT_LS
        elif (self.ier & self.IER_RX) and self.rx_fifo:
            self.iir = self.INT_RX
        elif (self.ier & self.IER_TX) and (self.lsr & self.LSR_THRE):
            self.iir = self.INT_TX
        elif (self.ier & self.IER_MS) and (self.msr & 0x0F):
            self.iir = self.INT_MS
        else:
            self.iir = self.INT_NONE

        # Уведомляем о прерывании
        if self.on_interrupt:
            self.on_interrupt(self.iir != self.INT_NONE)

    def _update_lsr_after_rx(self):
        """Обновить LSR после чтения из FIFO приёма"""
        if not self.rx_fifo:
            self.lsr &= ~self.LSR_DR
            self.rx_ready = False

    def has_interrupt(self):
        """Есть ли активное прерывание"""
        return self.iir != self.INT_NONE

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        """Состояние для отладки"""
        return {
            "name": self.name,
            "base_port": self.base_port,
            "dlab": self.dlab,
            "dll": f"0x{self.dll:02X}",
            "dlm": f"0x{self.dlm:02X}",
            "ier": f"0x{self.ier:02X}",
            "iir": f"0x{self.iir:02X}",
            "lcr": f"0x{self.lcr:02X}",
            "mcr": f"0x{self.mcr:02X}",
            "lsr": f"0x{self.lsr:02X}",
            "msr": f"0x{self.msr:02X}",
            "scr": f"0x{self.scr:02X}",
            "rx_fifo_size": len(self.rx_fifo),
            "tx_fifo_size": len(self.tx_fifo),
            "fifo_enabled": self.fifo_enabled,
            "has_interrupt": self.has_interrupt(),
        }
