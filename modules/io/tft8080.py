"""
TFT8080 — TFT-дисплей с 8080-интерфейсом.
Итерация 8: Дисплеи.

Интерфейс (классический 8080):
  8-битная шина данных (D0-D7)
  Выбор регистра/данных: линия адреса A0
    A0=0 → порт индекса (команды/регистра)
    A0=1 → порт данных
  Сигналы RD, WR — аппаратные сигналы шины (эмулируются фактом чтения/записи)
  Сигнал CS — аппаратный сигнал декодера адреса (всё устройство по базовому адресу)

Регистры (2 порта):
  offset 0 (A0=0): Index/Command Register — выбор регистра (команды)
  offset 1 (A0=1): Data Register — данные для выбранного регистра

Команды (упрощённо):
  0x21: Set Column Address
  0x22: Set Row Address
  0x2C: Memory Write
  0x2E: Memory Read
"""
from .iodevice import IODevice
from collections import deque


class TFT8080(IODevice):
    """TFT8080 — графический дисплей с 8080-интерфейсом"""

    # Команды
    CMD_SET_COLUMN = 0x21
    CMD_SET_ROW = 0x22
    CMD_MEM_WRITE = 0x2C
    CMD_MEM_READ = 0x2E

    def __init__(self, base_port, name="TFT8080", width=320, height=240):
        super().__init__(base_port, 2, name)  # 2 порта: индекс и данные
        self.width = width
        self.height = height
        self.reset()
        self.on_display_update = None  # callback(framebuffer)

    def reset(self):
        """Сброс контроллера"""
        self.framebuffer = [0] * (self.width * self.height)  # 16-бит цвет
        self.current_reg = 0x00       # Текущий регистр (команда)
        self.col_addr = 0
        self.row_addr = 0
        self._last_cmd = 0x00
        # Побайтовый буфер для приёма 16-битного пикселя
        self._byte_latch = None       # None = ждём первый байт, иначе хранит первый байт
        self._byte_count = 0          # Счётчик байт в текущем пикселе

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        """Чтение из порта"""
        offset = port - self.base_port
        if offset == 0:
            # Index/Command Register
            return self.current_reg
        elif offset == 1:
            # Data Register (чтение данных)
            return self._read_data()
        return 0xFF

    def io_write(self, port, value):
        """Запись в порт"""
        offset = port - self.base_port
        if offset == 0:
            # Index/Command Register: выбор регистра (команды)
            self.current_reg = value & 0xFF
            self._last_cmd = value & 0xFF
            self._execute_command()
        elif offset == 1:
            # Data Register: данные для текущего регистра
            self._write_data(value & 0xFF)

    # =============================================
    # ЧТЕНИЕ / ЗАПИСЬ ДАННЫХ (порт данных, A0=1)
    # =============================================
    def _read_data(self):
        """Чтение данных из видеопамяти"""
        addr = self.row_addr * self.width + self.col_addr
        if 0 <= addr < len(self.framebuffer):
            val = self.framebuffer[addr]
            # Автоинкремент адреса
            self.col_addr += 1
            if self.col_addr >= self.width:
                self.col_addr = 0
                self.row_addr += 1
                if self.row_addr >= self.height:
                    self.row_addr = 0
            return val & 0xFF
        return 0x00

    def _write_data(self, value):
        """Запись данных в видеопамять (побайтно, 2 байта на пиксель)"""
        if self._byte_count == 0:
            # Первый байт: сохраняем, ждём второй
            self._byte_latch = value
            self._byte_count = 1
        else:
            # Второй байт: формируем 16-битный пиксель
            pixel = (value << 8) | self._byte_latch
            self._byte_latch = None
            self._byte_count = 0

            addr = self.row_addr * self.width + self.col_addr
            if 0 <= addr < len(self.framebuffer):
                self.framebuffer[addr] = pixel & 0xFFFF

            # Автоинкремент адреса после полного пикселя
            self.col_addr += 1
            if self.col_addr >= self.width:
                self.col_addr = 0
                self.row_addr += 1
                if self.row_addr >= self.height:
                    self.row_addr = 0

            self._notify_update()

    # =============================================
    # ВЫПОЛНЕНИЕ КОМАНДЫ
    # =============================================
    def _execute_command(self):
        """Выполнение команды"""
        cmd = self.current_reg

        if cmd == self.CMD_SET_COLUMN:
            # Установка адреса колонки (следующие данные задают адрес)
            self._byte_latch = None
            self._byte_count = 0
        elif cmd == self.CMD_SET_ROW:
            # Установка адреса строки
            self._byte_latch = None
            self._byte_count = 0
        elif cmd == self.CMD_MEM_WRITE:
            # Начало записи в видеопамять
            self._byte_latch = None
            self._byte_count = 0
        elif cmd == self.CMD_MEM_READ:
            # Начало чтения из видеопамяти
            pass

    # =============================================
    # УТИЛИТЫ
    # =============================================
    def _notify_update(self):
        """Уведомление об обновлении дисплея"""
        if self.on_display_update:
            self.on_display_update(list(self.framebuffer))

    def get_framebuffer(self):
        """Получить содержимое видеопамяти"""
        return list(self.framebuffer)

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        return {
            "name": self.name,
            "base_port": self.base_port,
            "width": self.width,
            "height": self.height,
            "col_addr": self.col_addr,
            "row_addr": self.row_addr,
            "current_reg": f"0x{self.current_reg:02X}",
            "last_cmd": f"0x{self._last_cmd:02X}",
        }
