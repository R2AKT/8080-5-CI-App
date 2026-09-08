"""
LCD1602 — символьный дисплей 16×2.
Контроллер: HD44780.
Итерация 8: Дисплеи.

Возможности:
- 16 символов × 2 строки
- Память дисплея (DDRAM) на 32 символа
- Память знакогенератора (CGRAM) на 8 символов
- Команды: очистка, курсор, сдвиг, режимы
- Автоинкремент/декремент адреса

Регистры (2 порта):
  offset 0 (Data):    Чтение/запись данных
  offset 1 (Control): Запись команд / чтение статуса

Команды:
  0x01: Clear Display
  0x02: Return Home
  0x04-0x05: Entry Mode Set
  0x08-0x0F: Display On/Off Control
  0x10-0x1F: Cursor/Display Shift
  0x20-0x3F: Function Set
  0x40-0x7F: Set CGRAM Address
  0x80-0xBF: Set DDRAM Address
"""
from .iodevice import IODevice


class LCD1602(IODevice):
    """LCD1602 — символьный дисплей 16×2"""

    # Команды
    CMD_CLEAR = 0x01
    CMD_HOME = 0x02
    CMD_ENTRY_MODE = 0x04       # Бит 1: 1=инкремент, 0=декремент
    CMD_DISPLAY_CTRL = 0x08     # Биты: 4=дисплей, 2=курсор, 1=мигание
    CMD_SHIFT = 0x10            # Биты: 4=дисплей/курсор, 3=направление
    CMD_FUNCTION_SET = 0x20     # Биты: 4=8/4-бит, 3=2 строки, 2=шрифт
    CMD_SET_CGRAM = 0x40
    CMD_SET_DDRAM = 0x80

    # DDRAM адреса для строк 16×2
    LINE_ADDRS = [0x00, 0x40]

    def __init__(self, base_port, name="LCD1602"):
        super().__init__(base_port, 2, name)
        self.cols = 16
        self.rows = 2
        self.reset()
        self.on_display_update = None  # callback(text_lines)

    def reset(self):
        """Сброс контроллера"""
        self.ddram = [0x20] * 128   # Память дисплея
        self.cgram = [0x00] * 64    # Память знакогенератора (8×8)
        self.ddram_addr = 0x00
        self.cgram_addr = 0x00
        self.entry_increment = True
        self.entry_shift = False
        self.display_on = True
        self.cursor_on = False
        self.cursor_blink = False
        self.cursor_x = 0
        self.cursor_y = 0
        self._last_cmd = 0x00

    # =============================================
    # IO ЧТЕНИЕ / ЗАПИСЬ
    # =============================================
    def io_read(self, port):
        offset = port - self.base_port
        if offset == 0:
            return self.ddram[self.ddram_addr & 0x7F]
        elif offset == 1:
            return self._get_status()
        return 0xFF

    def io_write(self, port, value):
        offset = port - self.base_port
        if offset == 0:
            self._write_data(value & 0xFF)
        elif offset == 1:
            self._write_command(value & 0xFF)

    def _get_status(self):
        """Статус: бит 7=занят, биты 0-6=адрес"""
        return (self.ddram_addr & 0x7F) | (0x00 << 7)

    # =============================================
    # КОМАНДЫ
    # =============================================
    def _write_command(self, cmd):
        self._last_cmd = cmd

        if cmd == self.CMD_CLEAR:
            self.ddram = [0x20] * 128
            self.ddram_addr = 0x00
            self.cursor_x = 0
            self.cursor_y = 0
            self._notify_update()

        elif cmd == self.CMD_HOME:
            self.ddram_addr = 0x00
            self.cursor_x = 0
            self.cursor_y = 0

        elif cmd & 0xFC == self.CMD_ENTRY_MODE:
            self.entry_increment = bool(cmd & 0x02)
            self.entry_shift = bool(cmd & 0x01)

        elif cmd & 0xF8 == self.CMD_DISPLAY_CTRL:
            self.display_on = bool(cmd & 0x04)
            self.cursor_on = bool(cmd & 0x02)
            self.cursor_blink = bool(cmd & 0x01)

        elif cmd & 0xF0 == self.CMD_SHIFT:
            # Сдвиг курсора/дисплея (упрощённо)
            direction_right = bool(cmd & 0x04)
            if direction_right:
                self.cursor_x = min(self.cursor_x + 1, self.cols - 1)
            else:
                self.cursor_x = max(self.cursor_x - 1, 0)

        elif cmd & 0xE0 == self.CMD_FUNCTION_SET:
            pass  # Настройки режима (упрощённо)

        elif cmd & 0xC0 == self.CMD_SET_CGRAM:
            self.cgram_addr = cmd & 0x3F

        elif cmd & 0x80 == self.CMD_SET_DDRAM:
            self.ddram_addr = cmd & 0x7F
            self._update_cursor_from_addr()

    def _write_data(self, value):
        """Запись символа в DDRAM"""
        self.ddram[self.ddram_addr & 0x7F] = value & 0xFF

        if self.entry_increment:
            self.ddram_addr = (self.ddram_addr + 1) & 0x7F
        else:
            self.ddram_addr = (self.ddram_addr - 1) & 0x7F

        self._update_cursor_from_addr()
        self._notify_update()

    def _update_cursor_from_addr(self):
        """Обновить позицию курсора из адреса"""
        addr = self.ddram_addr
        if addr >= self.LINE_ADDRS[1]:
            self.cursor_y = 1
            self.cursor_x = (addr - self.LINE_ADDRS[1]) % self.cols
        else:
            self.cursor_y = 0
            self.cursor_x = addr % self.cols

    def _notify_update(self):
        """Уведомление об обновлении дисплея"""
        if self.on_display_update:
            self.on_display_update(self.get_display_text())

    # =============================================
    # УТИЛИТЫ ДЛЯ GUI
    # =============================================
    def get_display_text(self):
        """Получить текст дисплея"""
        lines = []
        for row in range(self.rows):
            line = ""
            base = self.LINE_ADDRS[row] if row < len(self.LINE_ADDRS) else row * 0x40
            for col in range(self.cols):
                ch = self.ddram[(base + col) & 0x7F]
                line += chr(ch) if 32 <= ch <= 126 else "."
            lines.append(line)
        return lines

    # =============================================
    # СОСТОЯНИЕ ДЛЯ ОТЛАДКИ
    # =============================================
    def get_state(self):
        return {
            "name": self.name,
            "base_port": self.base_port,
            "display_on": self.display_on,
            "cursor_on": self.cursor_on,
            "cursor_x": self.cursor_x,
            "cursor_y": self.cursor_y,
            "ddram_addr": f"0x{self.ddram_addr:02X}",
            "display": self.get_display_text(),
        }
